"""
server_standalone.py — Standalone CityFlow-compatible Server (No C++ dependency)
=================================================================================
Generates realistic simulated multi-agent traffic data matching the CityFlow API.
Use this when the cityflow C++ module is not available.
"""

import json
import math
import os
import random
import threading
import time
from typing import Dict, Any, List, Optional

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)
app.config["JSON_SORT_KEYS"] = False


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# ── Mount ANPR Vehicle Tracking & Firebase Cloud Engine ──
try:
    from tracking_api import register_tracking_routes
    register_tracking_routes(app)
except Exception as _track_err:
    print(f"[Server] Note: could not mount tracking routes: {_track_err}")




# ── Junction & Road Network Definition (matches roadnet_5j.json) ──
JUNCTIONS = ["J1", "J2", "J3", "J4", "J5"]
JUNCTION_POSITIONS = {
    "J1": {"x": 100, "y": 300},
    "J2": {"x": 300, "y": 500},
    "J3": {"x": 300, "y": 300},
    "J4": {"x": 500, "y": 300},
    "J5": {"x": 300, "y": 100},
}
ROADS = [
    "road_VW1_J1", "road_J1_VW1", "road_J1_J3", "road_J3_J1",
    "road_VN2_J2", "road_J2_VN2", "road_J2_J3", "road_J3_J2",
    "road_J3_J4", "road_J4_J3", "road_VE4_J4", "road_J4_VE4",
    "road_VS5_J5", "road_J5_VS5", "road_J5_J3", "road_J3_J5",
]

PHASE_NAMES = ["EW GREEN", "NS GREEN"]

# Control flags
ctrl = {
    "paused": False,
    "step_delay": 0.10,
}

# Simulation state
sim_state: Dict[str, Any] = {
    "step": 0,
    "running": False,
    "total_vehicles": 0,
    "avg_travel_time": 0.0,
    "avg_speed": 0.0,
    "network_density": 0.0,
    "total_waiting": 0,
    "vehicles": [],
    "lane_vehicles": {},
    "lane_waiting": {},
    "tl_phases": {},
    "agents": {},
    "agent_messages": [],
    "active_incidents": [],
    "ambulance": {"active": False},
}
state_lock = threading.Lock()


class SimulatedAgent:
    """Simulates a traffic agent for one junction."""

    def __init__(self, jid):
        self.jid = jid
        self.current_phase = 0
        self.is_yellow = False
        self.steps_on_phase = 0
        self.allocated_green = random.randint(20, 45)
        self.yellow_duration = 3
        self.yellow_counter = 0
        # Lane observations
        self.ew_density = random.uniform(0.1, 0.5)
        self.ns_density = random.uniform(0.1, 0.5)
        self.ew_queue = random.randint(0, 8)
        self.ns_queue = random.randint(0, 8)
        self.ew_speed = random.uniform(4.0, 12.0)
        self.ns_speed = random.uniform(4.0, 12.0)
        self.emergency_override = None
        self.decision_reason = "Initializing adaptive control..."

    def set_emergency(self, phase_name):
        self.emergency_override = phase_name
        if phase_name == "EW":
            self.current_phase = 0
            self.is_yellow = False
            self.steps_on_phase = 0
            self.decision_reason = "🚨 EMERGENCY PREEMPTION: Holding EW GREEN for Ambulance Corridor"
        elif phase_name == "NS":
            self.current_phase = 1
            self.is_yellow = False
            self.steps_on_phase = 0
            self.decision_reason = "🚨 EMERGENCY PREEMPTION: Holding NS GREEN for Ambulance Corridor"

    def step(self):
        self.steps_on_phase += 1

        # If emergency corridor is active on this junction, keep holding green
        if self.emergency_override:
            self.is_yellow = False
            target_phase = 0 if self.emergency_override == "EW" else 1
            self.current_phase = target_phase
            self.decision_reason = f"🚨 EMERGENCY PREEMPTION: Holding {self.emergency_override} GREEN for Ambulance Corridor"
            return

        # Vary traffic realistically
        self.ew_density = max(0.0, min(1.0, self.ew_density + random.uniform(-0.08, 0.08)))
        self.ns_density = max(0.0, min(1.0, self.ns_density + random.uniform(-0.08, 0.08)))
        self.ew_queue = max(0, self.ew_queue + random.randint(-2, 3))
        self.ns_queue = max(0, self.ns_queue + random.randint(-2, 3))
        self.ew_speed = max(1.0, min(15.0, self.ew_speed + random.uniform(-1.5, 1.5)))
        self.ns_speed = max(1.0, min(15.0, self.ns_speed + random.uniform(-1.5, 1.5)))

        if self.is_yellow:
            self.yellow_counter += 1
            if self.yellow_counter >= self.yellow_duration:
                self.is_yellow = False
                self.yellow_counter = 0
                self.current_phase = 1 - self.current_phase
                self.steps_on_phase = 0
                self.allocated_green = random.randint(20, 45)
                phase_name = PHASE_NAMES[self.current_phase]
                self.decision_reason = f"Switched to {phase_name} — adaptive green allocation: {self.allocated_green}s"
        else:
            if self.steps_on_phase >= self.allocated_green:
                self.is_yellow = True
                self.yellow_counter = 0
                ew_score = self.ew_density * 0.6 + (self.ew_queue / 15) * 0.4
                ns_score = self.ns_density * 0.6 + (self.ns_queue / 15) * 0.4
                self.decision_reason = f"EW score={ew_score:.2f} vs NS score={ns_score:.2f} — yellow clearance initiated"

    def get_state(self):
        overall_density = (self.ew_density + self.ns_density) / 2
        total_queue = self.ew_queue + self.ns_queue
        ew_cong = self.ew_density * 0.6 + (self.ew_queue / 15) * 0.4
        ns_cong = self.ns_density * 0.6 + (self.ns_queue / 15) * 0.4

        def status(d):
            return "HIGH" if d > 0.7 else "MEDIUM" if d > 0.4 else "LOW"

        return {
            "junction_id": self.jid,
            "current_phase": PHASE_NAMES[self.current_phase].split()[0],
            "is_yellow": self.is_yellow,
            "steps_on_phase": self.steps_on_phase,
            "allocated_green": self.allocated_green,
            "overall_density": round(overall_density, 3),
            "total_queue": total_queue,
            "available_capacity": round(1.0 - overall_density, 3),
            "local_obs": {
                "EW": {
                    "density": round(self.ew_density, 3),
                    "queue_length": self.ew_queue,
                    "average_speed": round(self.ew_speed, 1),
                    "congestion_score": round(ew_cong, 3),
                    "waiting_time": random.randint(2, 20),
                    "status": status(self.ew_density),
                },
                "NS": {
                    "density": round(self.ns_density, 3),
                    "queue_length": self.ns_queue,
                    "average_speed": round(self.ns_speed, 1),
                    "congestion_score": round(ns_cong, 3),
                    "waiting_time": random.randint(2, 20),
                    "status": status(self.ns_density),
                },
            },
            "decision_reason": self.decision_reason,
        }


# Initialize agents
agents: Dict[str, SimulatedAgent] = {jid: SimulatedAgent(jid) for jid in JUNCTIONS}
message_history = []

# Road topology and lengths (from roadnet_5j.json)
ROAD_LENGTHS = {
    "road_VW1_J1": 200.0, "road_J1_VW1": 200.0,
    "road_J1_J3": 200.0, "road_J3_J1": 200.0,
    "road_VN1_J1": 200.0, "road_J1_VN1": 200.0,
    "road_VS1_J1": 200.0, "road_J1_VS1": 200.0,
    "road_VN2_J2": 200.0, "road_J2_VN2": 200.0,
    "road_J2_J3": 200.0, "road_J3_J2": 200.0,
    "road_VW2_J2": 200.0, "road_J2_VW2": 200.0,
    "road_VE2_J2": 200.0, "road_J2_VE2": 200.0,
    "road_J3_J4": 200.0, "road_J4_J3": 200.0,
    "road_J3_J5": 200.0, "road_J5_J3": 200.0,
    "road_VE4_J4": 200.0, "road_J4_VE4": 200.0,
    "road_VN4_J4": 200.0, "road_J4_VN4": 200.0,
    "road_VS4_J4": 200.0, "road_J4_VS4": 200.0,
    "road_VS5_J5": 200.0, "road_J5_VS5": 200.0,
    "road_VW5_J5": 200.0, "road_J5_VW5": 200.0,
    "road_VE5_J5": 200.0, "road_J5_VE5": 200.0,
}

# Incoming junction and approach phase for each road
ROAD_JUNCTION_PHASE = {
    "road_VW1_J1": ("J1", "EW"),
    "road_J3_J1": ("J1", "EW"),
    "road_VN1_J1": ("J1", "NS"),
    "road_VS1_J1": ("J1", "NS"),
    "road_VW2_J2": ("J2", "EW"),
    "road_VE2_J2": ("J2", "EW"),
    "road_VN2_J2": ("J2", "NS"),
    "road_J3_J2": ("J2", "NS"),
    "road_J1_J3": ("J3", "EW"),
    "road_J4_J3": ("J3", "EW"),
    "road_J2_J3": ("J3", "NS"),
    "road_J5_J3": ("J3", "NS"),
    "road_J3_J4": ("J4", "EW"),
    "road_VE4_J4": ("J4", "EW"),
    "road_VN4_J4": ("J4", "NS"),
    "road_VS4_J4": ("J4", "NS"),
    "road_VW5_J5": ("J5", "EW"),
    "road_VE5_J5": ("J5", "EW"),
    "road_J3_J5": ("J5", "NS"),
    "road_VS5_J5": ("J5", "NS"),
}

# Realistic multi-junction routes (from flow_5j.json)
ROUTES = [
    ["road_VW1_J1", "road_J1_J3", "road_J3_J4", "road_J4_VE4"],
    ["road_VE4_J4", "road_J4_J3", "road_J3_J1", "road_J1_VW1"],
    ["road_VN2_J2", "road_J2_J3", "road_J3_J5", "road_J5_VS5"],
    ["road_VS5_J5", "road_J5_J3", "road_J3_J2", "road_J2_VN2"],
    ["road_VN1_J1", "road_J1_VS1"],
    ["road_VS1_J1", "road_J1_VN1"],
    ["road_VW2_J2", "road_J2_VE2"],
    ["road_VE2_J2", "road_J2_VW2"],
    ["road_VN4_J4", "road_J4_VS4"],
    ["road_VS4_J4", "road_J4_VN4"],
    ["road_VW5_J5", "road_J5_VE5"],
    ["road_VE5_J5", "road_J5_VW5"],
]


class ContinuousVehicle:
    def __init__(self, vid, route):
        self.vid = vid
        self.route = list(route)
        self.route_idx = 0
        self.dist = random.uniform(0.0, 50.0)
        self.speed = random.uniform(5.0, 9.0)
        self.target_speed = random.uniform(10.0, 14.5)
        self.is_waiting = False

    @property
    def road(self):
        return self.route[self.route_idx]

    def update(self, dt, leader_dist):
        road_len = ROAD_LENGTHS.get(self.road, 200.0)
        stop_line = road_len - 18.0

        # Check signal state at the downstream intersection
        signal_red = False
        if self.road in ROAD_JUNCTION_PHASE:
            jid, phase_name = ROAD_JUNCTION_PHASE[self.road]
            agent = agents.get(jid)
            if agent:
                if agent.is_yellow:
                    signal_red = True
                else:
                    curr_phase_name = PHASE_NAMES[agent.current_phase].split()[0]
                    if curr_phase_name != phase_name:
                        signal_red = True

        # Smooth Deceleration & Car-Following Physics (No stop-and-go jitter)
        dist_to_stop = stop_line - self.dist
        signal_stopping = signal_red and (0.0 < dist_to_stop < 55.0)

        min_gap = 12.0
        desired_gap = 22.0

        if leader_dist is not None and leader_dist < desired_gap:
            if leader_dist <= min_gap:
                self.speed = max(0.0, self.speed - 12.0 * dt)
                self.is_waiting = (self.speed < 0.3)
            else:
                target_spd = self.target_speed * ((leader_dist - min_gap) / (desired_gap - min_gap))
                if self.speed > target_spd:
                    self.speed = max(target_spd, self.speed - 5.0 * dt)
                else:
                    self.speed = min(target_spd, self.speed + 3.0 * dt)
                self.is_waiting = False
        elif signal_stopping:
            if dist_to_stop <= 2.0:
                self.dist = min(self.dist, stop_line)
                self.speed = 0.0
                self.is_waiting = True
            else:
                brake_rate = max(2.5, min(8.5, (self.speed * self.speed) / (2.0 * max(1.5, dist_to_stop))))
                self.speed = max(0.0, self.speed - brake_rate * dt)
                self.is_waiting = (self.speed < 0.3)
        else:
            self.is_waiting = False
            self.speed = min(self.target_speed, self.speed + 4.5 * dt)

        self.dist += self.speed * dt

        # Transition to next road in route seamlessly
        if self.dist >= road_len:
            excess = self.dist - road_len
            self.route_idx += 1
            if self.route_idx >= len(self.route):
                return False  # Completed trip
            self.dist = excess

        return True


# Persistent vehicle fleet
vehicle_fleet: List[ContinuousVehicle] = []
veh_counter = 0


def _init_vehicle_fleet():
    global veh_counter
    while len(vehicle_fleet) < 28:
        veh_counter += 1
        route = random.choice(ROUTES)
        v = ContinuousVehicle(f"v_{veh_counter}", route)
        v.dist = random.uniform(10.0, 160.0)
        vehicle_fleet.append(v)


_init_vehicle_fleet()


def _update_vehicle_fleet(dt):
    global veh_counter

    # Group vehicles by road to calculate distances to leader
    road_groups: Dict[str, List[ContinuousVehicle]] = {}
    for v in vehicle_fleet:
        road_groups.setdefault(v.road, []).append(v)

    # Sort descending by distance along the road
    for rlist in road_groups.values():
        rlist.sort(key=lambda x: x.dist, reverse=True)

    # Update each vehicle
    survivors = []
    for rlist in road_groups.values():
        for i, v in enumerate(rlist):
            leader_dist = (rlist[i - 1].dist - v.dist) if i > 0 else None
            if v.update(dt, leader_dist):
                survivors.append(v)

    vehicle_fleet.clear()
    vehicle_fleet.extend(survivors)

    # Spawn replacement vehicles to maintain realistic traffic volume
    while len(vehicle_fleet) < 28:
        veh_counter += 1
        route = random.choice(ROUTES)
        v = ContinuousVehicle(f"v_{veh_counter}", route)
        v.dist = random.uniform(2.0, 30.0)
        vehicle_fleet.append(v)


def _refresh_state():
    # Convert active vehicle fleet to API payload
    vehicles = []
    speeds = []
    lane_vehs = {}
    lane_wait = {}

    for v in vehicle_fleet:
        spd_kmh = round(v.speed * 3.6, 1)
        speeds.append(spd_kmh)
        vehicles.append({
            "id": v.vid,
            "speed": str(round(v.speed, 2)),
            "distance": str(round(v.dist, 2)),
            "road": v.road,
            "running": "1" if v.speed >= 0.5 else "0",
        })
        key = f"{v.road}_0"
        lane_vehs[key] = lane_vehs.get(key, 0) + 1
        if v.is_waiting:
            lane_wait[key] = lane_wait.get(key, 0) + 1

    total_waiting = sum(lane_wait.values())
    avg_spd = round(sum(speeds) / len(speeds), 1) if speeds else 0.0

    total_capacity = len(ROADS) * 2 * 14.0
    net_density = round(len(vehicles) / total_capacity * 100, 1) if total_capacity else 0.0

    agent_states = {}
    tl_phases = {}
    for jid, agent in agents.items():
        agent_states[jid] = agent.get_state()
        tl_phases[jid] = {
            "phase_idx": agent.current_phase,
            "phase_name": PHASE_NAMES[agent.current_phase],
            "is_yellow": agent.is_yellow,
        }

    with state_lock:
        sim_state.update({
            "running": not ctrl["paused"],
            "total_vehicles": len(vehicles),
            "avg_travel_time": round(random.uniform(22.0, 38.0), 1),
            "avg_speed": avg_spd,
            "network_density": net_density,
            "total_waiting": total_waiting,
            "vehicles": vehicles,
            "lane_vehicles": lane_vehs,
            "lane_waiting": lane_wait,
            "tl_phases": tl_phases,
            "agents": agent_states,
            "agent_messages": message_history[-15:],
            "active_incidents": list(active_incidents.values()),
            "ambulance": dict(ambulance_state),
        })


active_incidents: Dict[str, Any] = {}
ambulance_state = {
    "active": False,
    "progress_m": 0.0,
    "speed": 7.5,
    "route_roads": ["road_VW1_J1", "road_J1_J3", "road_J3_J4", "road_J4_VE4"],
    "current_road": "road_VW1_J1",
    "road_dist": 0.0,
    "corridor": "EW"
}


def _update_ambulance():
    if not ambulance_state["active"]:
        return

    ambulance_state["progress_m"] += ambulance_state["speed"]
    prog = ambulance_state["progress_m"]

    # Total route: VW1->J1 (200m), J1->J3 (200m), J3->J4 (200m), J4->VE4 (200m) = 800m
    if prog < 200:
        ambulance_state["current_road"] = "road_VW1_J1"
        ambulance_state["road_dist"] = prog
        agents["J1"].set_emergency("EW")
        agents["J3"].set_emergency("EW")
    elif prog < 400:
        ambulance_state["current_road"] = "road_J1_J3"
        ambulance_state["road_dist"] = prog - 200
        agents["J1"].set_emergency(None)
        agents["J3"].set_emergency("EW")
        agents["J4"].set_emergency("EW")
    elif prog < 600:
        ambulance_state["current_road"] = "road_J3_J4"
        ambulance_state["road_dist"] = prog - 400
        agents["J3"].set_emergency(None)
        agents["J4"].set_emergency("EW")
    elif prog < 800:
        ambulance_state["current_road"] = "road_J4_VE4"
        ambulance_state["road_dist"] = prog - 600
        agents["J4"].set_emergency(None)
    else:
        # Ambulance completed route
        ambulance_state["active"] = False
        ambulance_state["progress_m"] = 0.0
        ambulance_state["current_road"] = "road_VW1_J1"
        ambulance_state["road_dist"] = 0.0
        for agent in agents.values():
            agent.set_emergency(None)


def _sim_worker():
    while True:
        try:
            if not ctrl["paused"]:
                sim_state["step"] += 1

                dt = max(0.08, float(ctrl.get("step_delay", 0.10)))
                _update_ambulance()
                _update_vehicle_fleet(dt)

                for agent in agents.values():
                    agent.step()

                # Periodic agent messages
                if sim_state["step"] % 5 == 0:
                    sender = random.choice(JUNCTIONS)
                    agent = agents[sender]
                    message_history.append({
                        "sender": sender,
                        "timestamp": sim_state["step"],
                        "decision_reason": agent.decision_reason,
                    })
                    if len(message_history) > 50:
                        message_history.pop(0)

                _refresh_state()
        except Exception as e:
            print(f"[CityFlow Worker] Exception during step: {e}", flush=True)

        time.sleep(ctrl["step_delay"])


# Initial state population and background thread launch (runs under Gunicorn & Standalone)
_refresh_state()
_sim_thread = threading.Thread(target=_sim_worker, daemon=True)
_sim_thread.start()


REACT_DIST = os.environ.get(
    "REACT_DIST_DIR",
    os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))
)


# ── Routes ──

@app.route("/cityflow-sim")
def cityflow_sim():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if path.startswith("api/"):
        return jsonify({"error": "Endpoint not found"}), 404

    if os.path.exists(REACT_DIST):
        target = os.path.join(REACT_DIST, path)
        if path and os.path.exists(target) and not os.path.isdir(target):
            return send_from_directory(REACT_DIST, path)
        return send_from_directory(REACT_DIST, "index.html")

    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/state")
def get_state():
    with state_lock:
        return jsonify(dict(sim_state))


@app.route("/api/roadnet")
def get_roadnet():
    path = os.path.join(BASE_DIR, "roadnet_5j.json")
    with open(path) as f:
        return jsonify(json.load(f))


@app.route("/api/control", methods=["POST"])
def control():
    data = request.get_json() or {}
    cmd = data.get("cmd")

    if cmd == "start":
        ctrl["paused"] = False
        with state_lock:
            sim_state["running"] = True
        _refresh_state()
    elif cmd == "pause":
        ctrl["paused"] = True
        with state_lock:
            sim_state["running"] = False
        _refresh_state()
    elif cmd == "step":
        ctrl["paused"] = True
        sim_state["step"] += 1
        for agent in agents.values():
            agent.step()
        _update_ambulance()
        _update_vehicle_fleet(0.1)
        _refresh_state()
    elif cmd == "reset":
        ctrl["paused"] = False
        sim_state["step"] = 0
        for jid in JUNCTIONS:
            agents[jid] = SimulatedAgent(jid)
        message_history.clear()
        active_incidents.clear()
        ambulance_state["active"] = False
        ambulance_state["progress_m"] = 0.0
        ambulance_state["current_road"] = "road_VW1_J1"
        ambulance_state["road_dist"] = 0.0
        vehicle_fleet.clear()
        _init_vehicle_fleet()
        _refresh_state()
    elif cmd == "speed":
        ctrl["step_delay"] = float(data.get("value", 0.10))

    with state_lock:
        return jsonify({"ok": True, "state": dict(sim_state)})


@app.route("/api/incident", methods=["POST"])
def handle_incident():
    data = request.get_json() or {}
    junction = data.get("junction", "J3")
    road = data.get("road", "road_J3_J2")
    itype = data.get("type", "ACCIDENT")
    active = data.get("active", True)

    if active:
        active_incidents[junction] = {
            "junction": junction,
            "road": road,
            "type": itype,
            "active": True,
        }
    else:
        active_incidents.pop(junction, None)

    _refresh_state()
    return jsonify({"ok": True, "incidents": list(active_incidents.values())})


@app.route("/api/ambulance", methods=["POST"])
def handle_ambulance():
    ambulance_state["active"] = not ambulance_state.get("active", False)
    if ambulance_state["active"]:
        ambulance_state["progress_m"] = 0.0
        ambulance_state["current_road"] = "road_VW1_J1"
        ambulance_state["road_dist"] = 0.0
        agents["J1"].set_emergency("EW")
        agents["J3"].set_emergency("EW")
    else:
        ambulance_state["progress_m"] = 0.0
        ambulance_state["current_road"] = "road_VW1_J1"
        ambulance_state["road_dist"] = 0.0
        for agent in agents.values():
            agent.set_emergency(None)
    _refresh_state()
    return jsonify({"ok": True, "ambulance": ambulance_state})


@app.route("/api/override", methods=["POST"])
def handle_override():
    data = request.get_json() or {}
    junction = data.get("junction")
    phase = int(data.get("phase", 0))

    if junction in agents:
        agent = agents[junction]
        agent.current_phase = phase
        agent.is_yellow = False
        agent.steps_on_phase = 0
        agent.decision_reason = f"👤 Manual override — forced {PHASE_NAMES[phase]}"
        _refresh_state()
        return jsonify({"ok": True})

    return jsonify({"ok": False}), 400


if __name__ == "__main__":
    print("=" * 60)
    print("  CityFlow Standalone Server (Simulated Mode)")
    print("  Running at: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
