import os
import cityflow
from agent import MultiAgentCoordinator

os.chdir(os.path.dirname(os.path.abspath(__file__)))

eng = cityflow.Engine("config_5j.json", 1)
coord = MultiAgentCoordinator(eng)

print("Running 180 simulation steps...")

phase_history = {jid: [] for jid in coord.agents}

for step in range(180):
    eng.next_step()
    
    # Get vehicle info map
    v_ids = eng.get_vehicles(include_waiting=True)
    v_map = {}
    for vid in v_ids:
        try:
            v_map[vid] = eng.get_vehicle_info(vid)
        except Exception:
            pass
            
    if step % 3 == 0:
        res = coord.step(v_map)
        for jid, agent in coord.agents.items():
            phase_history[jid].append((step, agent.current_phase, agent.is_yellow, agent.last_decision_reason))

print("Simulation ran 180 steps cleanly.")
print("Vehicles count at end:", eng.get_vehicle_count())
print("Avg travel time:", eng.get_average_travel_time())

for jid, hist in phase_history.items():
    switches = [h for i, h in enumerate(hist) if i > 0 and h[1] != hist[i-1][1]]
    print(f"Junction {jid}: {len(switches)} phase switches. Sample reasons:")
    for s in switches[:2]:
        print(f"  Step {s[0]}: phase -> {s[1]} ({s[3]})")
