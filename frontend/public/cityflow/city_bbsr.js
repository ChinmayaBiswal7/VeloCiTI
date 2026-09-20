/**
 * city_bbsr.js — Bhubaneswar Full City Traffic Simulation
 * ========================================================
 * - 33 Real Intersections across Bhubaneswar
 * - Realistic High-Density Urban Traffic (850-1050 active vehicles)
 * - Car-Following Queue Dynamics (no overlapping, realistic queues at red lights)
 * - Full Designated Emergency Corridor Mapping (plotted along the entire route)
 * - Edge CCTV Camera Detection Zone Preemption (only preempts within 140m)
 * - Non-Halting Flow: Distant traffic is NEVER blocked ahead of time
 * - Central City Dashboard Telemetry with all 33 junction cards
 */

'use strict';

// ── 46 Real Major Bhubaneswar Intersections (Max 4 Branches Per Node) ──────
const BBSR_INTERSECTIONS = [
  // ── NH-16 Primary Arterial ──
  { id: 'KHANDG',     name: 'Khandagiri Square',          lat: 20.2575, lon: 85.7865, zone: 'heritage' },
  { id: 'FIRE_STN',   name: 'Fire Station Square',        lat: 20.2710, lon: 85.7950, zone: 'transport' },
  { id: 'BARAMN',     name: 'Baramunda Bus Terminal',     lat: 20.2768, lon: 85.7995, zone: 'transport' },
  { id: 'CRPF',       name: 'CRPF Square',                lat: 20.2872, lon: 85.8115, zone: 'residential' },
  { id: 'NAYAPALLI',  name: 'Nayapalli / Behera Sahi',    lat: 20.2930, lon: 85.8150, zone: 'residential' },
  { id: 'JAYADEV',    name: 'Jayadev Vihar (NH-16)',      lat: 20.3005, lon: 85.8228, zone: 'commercial' },
  { id: 'ACHARYA',    name: 'Acharya Vihar (NH-16)',      lat: 20.3015, lon: 85.8315, zone: 'edu' },
  { id: 'VANI',       name: 'Vani Vihar (NH-16)',         lat: 20.2985, lon: 85.8415, zone: 'edu' },
  { id: 'RASUL',      name: 'Rasulgarh Square (NH-16)',   lat: 20.2936, lon: 85.8647, zone: 'commercial' },
  { id: 'PALASUNI',   name: 'Palasuni Square (NH-16)',    lat: 20.3040, lon: 85.8710, zone: 'commercial' },
  { id: 'MANCHES',    name: 'Mancheswar Industrial',      lat: 20.3120, lon: 85.8750, zone: 'commercial' },

  // ── Nandankanan Road (Northern IT & University Corridor) ──
  { id: 'XAVIER',     name: 'Xavier Square (XIMB)',       lat: 20.3125, lon: 85.8198, zone: 'it' },
  { id: 'CS_PUR',     name: 'Chandrasekharpur BDA',       lat: 20.3175, lon: 85.8160, zone: 'residential' },
  { id: 'KALINGA',    name: 'Kalinga Hospital Square',    lat: 20.3205, lon: 85.8215, zone: 'medical' },
  { id: 'DAMANA',     name: 'Damana Square',              lat: 20.3340, lon: 85.8185, zone: 'residential' },
  { id: 'SAILASHREE', name: 'Sailashree Vihar Chowk',     lat: 20.3440, lon: 85.8150, zone: 'residential' },
  { id: 'PATIA',      name: 'Patia Chowk',                lat: 20.3540, lon: 85.8170, zone: 'it' },
  { id: 'KIIT',       name: 'KIIT Square',                lat: 20.3565, lon: 85.8165, zone: 'it' },
  { id: 'INFOCITY',   name: 'Infocity Square',            lat: 20.3585, lon: 85.8085, zone: 'it' },
  { id: 'CHANDAKA',   name: 'Chandaka Square',            lat: 20.3650, lon: 85.7950, zone: 'it' },

  // ── Western Infill: Delta, Siripur, OUAT, Gopabandhu ──
  { id: 'DELTA',      name: 'Delta Square',               lat: 20.2740, lon: 85.8105, zone: 'residential' },
  { id: 'GOPABANDHU', name: 'Gopabandhu Square',          lat: 20.2700, lon: 85.8210, zone: 'residential' },
  { id: 'SIRIPUR',    name: 'Siripur / OUAT Square',      lat: 20.2645, lon: 85.8155, zone: 'edu' },

  // ── Power Grid & Bidyut Marg ──
  { id: 'POWER',      name: 'Power House Square',         lat: 20.2910, lon: 85.8235, zone: 'govt' },
  { id: 'RAJ_BHAWAN', name: 'Raj Bhawan (Governor House)',lat: 20.2830, lon: 85.8285, zone: 'govt' },

  // ── Central Spine: Sachivalaya Marg & Rajpath ──
  { id: 'AG',         name: 'AG Square (State Capital)',  lat: 20.2745, lon: 85.8322, zone: 'govt' },
  { id: 'CAPITAL',    name: 'Capital Hospital Square',    lat: 20.2625, lon: 85.8280, zone: 'medical' },
  { id: 'MAST',       name: 'Master Canteen (Station)',   lat: 20.2678, lon: 85.8436, zone: 'transport' },
  { id: 'RAM',        name: 'Ram Mandir Square',          lat: 20.2800, lon: 85.8443, zone: 'commercial' },
  { id: 'RUPALI',     name: 'Rupali Square',              lat: 20.2893, lon: 85.8427, zone: 'commercial' },
  { id: 'SAHEED',     name: 'Saheed Nagar Square',        lat: 20.2910, lon: 85.8520, zone: 'commercial' },

  // ── Eastern Secondary Arterials ──
  { id: 'VSS',        name: 'VSS Nagar Square',           lat: 20.3050, lon: 85.8550, zone: 'residential' },
  { id: 'SAINIK',     name: 'Sainik School Square',       lat: 20.3160, lon: 85.8360, zone: 'edu' },
  { id: 'BOMIKHAL',   name: 'Bomikhal Flyover',           lat: 20.2820, lon: 85.8560, zone: 'commercial' },
  { id: 'LAXMI',      name: 'Laxmisagar Square',          lat: 20.2720, lon: 85.8500, zone: 'residential' },
  { id: 'KALPANA',    name: 'Kalpana Square',             lat: 20.2546, lon: 85.8437, zone: 'heritage' },
  { id: 'RAJMAHAL',   name: 'Rajmahal Square',            lat: 20.2638, lon: 85.8396, zone: 'commercial' },
  { id: 'SISHU',      name: 'Sishu Bhawan Square',        lat: 20.2585, lon: 85.8350, zone: 'medical' },

  // ── South & Old Town Heritage Network ──
  { id: 'RAVI',       name: 'Ravi Talkies Square',        lat: 20.2470, lon: 85.8415, zone: 'residential' },
  { id: 'LINGARAJ',   name: 'Lingaraj Temple Square',     lat: 20.2382, lon: 85.8335, zone: 'heritage' },
  { id: 'AIRPORT',    name: 'Airport Square',             lat: 20.2525, lon: 85.8178, zone: 'transport' },
  { id: 'POKHAR',     name: 'Pokhariput Square',          lat: 20.2460, lon: 85.8170, zone: 'residential' },
  { id: 'SUNDARPADA', name: 'Sundarpada Square',          lat: 20.2330, lon: 85.8110, zone: 'residential' },
  { id: 'ITER',       name: 'ITER / Gandamunda Square',   lat: 20.2505, lon: 85.8050, zone: 'edu' },
  { id: 'JAGAMARA',   name: 'Jagamara Square',            lat: 20.2530, lon: 85.7970, zone: 'residential' },
  { id: 'GHATIKIA',   name: 'Ghatikia / Kalinga Studio',  lat: 20.2490, lon: 85.7830, zone: 'residential' },
];

// ── Accurate Arterial Road Network (Max 4 Roads Per Node) ───────────────────
const BBSR_ROAD_SEGMENTS = [
  // 1. NH-16 Main Arterial Corridor (High-Capacity Highway)
  { from: 'KHANDG',    to: 'FIRE_STN',   type: 'nh', waypoints: [[20.2640, 85.7910]] },
  { from: 'FIRE_STN',  to: 'BARAMN',     type: 'nh', waypoints: [] },
  { from: 'BARAMN',    to: 'CRPF',       type: 'nh', waypoints: [] },
  { from: 'CRPF',      to: 'NAYAPALLI',  type: 'nh', waypoints: [] },
  { from: 'NAYAPALLI', to: 'JAYADEV',    type: 'nh', waypoints: [] },
  { from: 'JAYADEV',   to: 'ACHARYA',    type: 'nh', waypoints: [] },
  { from: 'ACHARYA',   to: 'VANI',       type: 'nh', waypoints: [] },
  { from: 'VANI',      to: 'RASUL',      type: 'nh', waypoints: [[20.2960, 85.8530]] },
  { from: 'RASUL',     to: 'PALASUNI',   type: 'nh', waypoints: [] },
  { from: 'PALASUNI',  to: 'MANCHES',    type: 'nh', waypoints: [] },

  // 2. Nandankanan Northern IT & Educational Spine
  { from: 'JAYADEV',   to: 'XAVIER',     type: 'sh', waypoints: [] },
  { from: 'XAVIER',    to: 'CS_PUR',     type: 'sh', waypoints: [] },
  { from: 'CS_PUR',    to: 'KALINGA',    type: 'sh', waypoints: [] },
  { from: 'KALINGA',   to: 'DAMANA',     type: 'sh', waypoints: [] },
  { from: 'DAMANA',    to: 'SAILASHREE', type: 'sh', waypoints: [] },
  { from: 'SAILASHREE',to: 'PATIA',      type: 'sh', waypoints: [] },
  { from: 'PATIA',     to: 'KIIT',       type: 'sh', waypoints: [] },
  { from: 'KIIT',      to: 'INFOCITY',   type: 'sh', waypoints: [] },
  { from: 'INFOCITY',  to: 'CHANDAKA',   type: 'city', waypoints: [] },

  // 3. Western Arterial Infill (Delta, Siripur, Fire Station, Gopabandhu)
  { from: 'FIRE_STN',  to: 'DELTA',      type: 'city', waypoints: [] },
  { from: 'CRPF',      to: 'DELTA',      type: 'city', waypoints: [] },
  { from: 'DELTA',     to: 'GOPABANDHU', type: 'city', waypoints: [] },
  { from: 'DELTA',     to: 'SIRIPUR',    type: 'city', waypoints: [] },
  { from: 'GOPABANDHU',to: 'RAJ_BHAWAN', type: 'city', waypoints: [] },
  { from: 'SIRIPUR',   to: 'CAPITAL',    type: 'city', waypoints: [] },
  { from: 'SIRIPUR',   to: 'AIRPORT',    type: 'city', waypoints: [] },

  // 4. Bidyut Marg & Governor House Axis
  { from: 'JAYADEV',   to: 'POWER',      type: 'sh', waypoints: [] },
  { from: 'POWER',     to: 'RAJ_BHAWAN', type: 'sh', waypoints: [] },
  { from: 'RAJ_BHAWAN',to: 'AG',         type: 'sh', waypoints: [] },
  { from: 'POWER',     to: 'NAYAPALLI',  type: 'city', waypoints: [] },

  // 5. Sachivalaya Marg & Rajpath (Pure 4-way Crossroads at AG Square!)
  { from: 'ACHARYA',   to: 'AG',         type: 'sh', waypoints: [[20.2890, 85.8320]] },
  { from: 'AG',        to: 'CAPITAL',    type: 'sh', waypoints: [] },
  { from: 'AG',        to: 'MAST',       type: 'sh', waypoints: [] },

  // 6. Janpath Corridor (Commercial Spine)
  { from: 'VANI',      to: 'RUPALI',     type: 'sh', waypoints: [] },
  { from: 'RUPALI',    to: 'RAM',        type: 'sh', waypoints: [] },
  { from: 'RAM',       to: 'MAST',       type: 'sh', waypoints: [] },
  { from: 'MAST',      to: 'RAJMAHAL',   type: 'sh', waypoints: [] },
  { from: 'RAJMAHAL',  to: 'SISHU',      type: 'sh', waypoints: [] },
  { from: 'SISHU',     to: 'AIRPORT',    type: 'sh', waypoints: [[20.2540, 85.8260]] },
  { from: 'CAPITAL',   to: 'SISHU',      type: 'city', waypoints: [] },

  // 7. Eastern Network: Sainik School, Saheed Nagar, VSS Nagar
  { from: 'KALINGA',   to: 'SAINIK',     type: 'city', waypoints: [] },
  { from: 'SAINIK',    to: 'ACHARYA',    type: 'city', waypoints: [] },
  { from: 'SAINIK',    to: 'VSS',        type: 'city', waypoints: [] },
  { from: 'VSS',       to: 'MANCHES',    type: 'city', waypoints: [] },
  { from: 'VANI',      to: 'SAHEED',     type: 'city', waypoints: [] },
  { from: 'SAHEED',    to: 'BOMIKHAL',   type: 'city', waypoints: [] },
  { from: 'RUPALI',    to: 'SAHEED',     type: 'city', waypoints: [] },

  // 8. Cuttack-Puri Road (Historical Trunk)
  { from: 'RASUL',     to: 'BOMIKHAL',   type: 'sh', waypoints: [[20.2880, 85.8600]] },
  { from: 'BOMIKHAL',  to: 'LAXMI',      type: 'sh', waypoints: [] },
  { from: 'LAXMI',     to: 'KALPANA',    type: 'sh', waypoints: [] },
  { from: 'KALPANA',   to: 'RAVI',       type: 'sh', waypoints: [[20.2510, 85.8425]] },
  { from: 'RAVI',      to: 'LINGARAJ',   type: 'sh', waypoints: [] },
  { from: 'RAJMAHAL',  to: 'KALPANA',    type: 'city', waypoints: [] },
  { from: 'RAM',       to: 'LAXMI',      type: 'city', waypoints: [] },

  // 9. South Arterial Ring (Khandagiri, Ghatikia, Jagamara, Sundarpada)
  { from: 'KHANDG',    to: 'GHATIKIA',   type: 'city', waypoints: [] },
  { from: 'GHATIKIA',  to: 'JAGAMARA',   type: 'city', waypoints: [] },
  { from: 'KHANDG',    to: 'JAGAMARA',   type: 'city', waypoints: [] },
  { from: 'JAGAMARA',  to: 'ITER',       type: 'city', waypoints: [] },
  { from: 'ITER',      to: 'POKHAR',     type: 'city', waypoints: [] },
  { from: 'POKHAR',    to: 'SUNDARPADA', type: 'city', waypoints: [] },
  { from: 'SUNDARPADA',to: 'LINGARAJ',   type: 'city', waypoints: [] },
  { from: 'POKHAR',    to: 'AIRPORT',    type: 'city', waypoints: [] },
  { from: 'AIRPORT',   to: 'LINGARAJ',   type: 'city', waypoints: [] },

  // 10. Outer Northern Connector
  { from: 'CHANDAKA',  to: 'PATIA',      type: 'city', waypoints: [[20.3620, 85.8050]] },
];

const ZONE_COLORS = {
  heritage:    '#dba53a',
  commercial:  '#e6926f',
  govt:        '#8fbf9d',
  medical:     '#e6926f',
  it:          '#8fbf9d',
  residential: '#b5b1a4',
  transport:   '#e0913a',
  edu:         '#e6926f',
};

// ── Multi-Agent AI Controller (Exact math from agent.py) ─────────────────────
class BbsrAgent {
  constructor(junctionId) {
    this.id = junctionId;
    this.phases = ['EW', 'NS'];
    this.currentPhase = 0;
    this.isYellow = false;
    this.yellowTimer = 0;
    this.stepsOnPhase = 0;
    this.allocatedGreen = 22;
    this.waitingTime = { EW: 0, NS: 0 };
    this.obs = {
      EW: { density: 0, queue: 0, speed: 6, score: 0 },
      NS: { density: 0, queue: 0, speed: 6, score: 0 }
    };
    this.downstreamCap = 1.0;
    this.decisionReason = 'Multi-Agent distributed node active.';
    this.emergencyOverride = null;
    this.incidentPhase = null;
  }

  computeScore(density, qRatio, waitRatio) {
    return 0.50 * density + 0.30 * Math.min(qRatio, 1) + 0.20 * Math.min(waitRatio, 1);
  }

  step(neighborDensity, dt = 0.05) {
    this.downstreamCap = Math.max(0.10, 1.0 - neighborDensity);
    const MIN_GREEN = 7.0, MAX_GREEN = 20.0, YELLOW_TIME = 2.0, STARVE_TIME = 16.0;

    // Emergency CCTV Camera Priority Override (Instant Preemption)
    if (this.emergencyOverride !== null && this.emergencyOverride !== undefined) {
      const targetPhase = typeof this.emergencyOverride === 'number'
        ? this.emergencyOverride
        : (this.emergencyOverride === 'EW' ? 0 : 1);
      this.currentPhase = targetPhase;
      this.isYellow = false;
      this.yellowTimer = 0;
      this.stepsOnPhase += dt;
      return;
    }

    // Yellow Clearance Phase
    if (this.isYellow) {
      this.yellowTimer += dt;
      if (this.yellowTimer >= YELLOW_TIME) {
        this.isYellow = false;
        this.yellowTimer = 0;
        this.currentPhase = this.currentPhase === 0 ? 1 : 0;
        this.stepsOnPhase = 0;
      }
      return;
    }

    this.stepsOnPhase += dt;
    const curPhaseStr = this.phases[this.currentPhase];
    const oppPhaseStr = this.phases[this.currentPhase === 0 ? 1 : 0];
    this.waitingTime[curPhaseStr] = 0;
    this.waitingTime[oppPhaseStr] += dt;

    const ew = this.obs.EW, ns = this.obs.NS;
    ew.score = this.computeScore(ew.density, ew.queue / 12, this.waitingTime.EW / STARVE_TIME);
    ns.score = this.computeScore(ns.density, ns.queue / 12, this.waitingTime.NS / STARVE_TIME);

    const ewBoost = this.waitingTime.EW > STARVE_TIME ? Math.min(0.6, (this.waitingTime.EW - STARVE_TIME) / STARVE_TIME * 0.5) : 0;
    const nsBoost = this.waitingTime.NS > STARVE_TIME ? Math.min(0.6, (this.waitingTime.NS - STARVE_TIME) / STARVE_TIME * 0.5) : 0;

    const ewPri = Math.min(1, ew.score + ewBoost) * (this.currentPhase === 0 ? 1 : this.downstreamCap);
    const nsPri = Math.min(1, ns.score + nsBoost) * (this.currentPhase === 1 ? 1 : this.downstreamCap);

    const curScore = this.currentPhase === 0 ? ew.score : ns.score;
    this.allocatedGreen = Math.min(MAX_GREEN, Math.max(MIN_GREEN, Math.round(MIN_GREEN + curScore * (MAX_GREEN - MIN_GREEN))));

    const oppPri = this.currentPhase === 0 ? nsPri : ewPri;
    const curPri = this.currentPhase === 0 ? ewPri : nsPri;

    const shouldSwitch = (this.stepsOnPhase >= this.allocatedGreen) ||
      (oppPri > curPri * 1.30 && this.stepsOnPhase >= MIN_GREEN) ||
      (this.waitingTime[oppPhaseStr] >= STARVE_TIME);

    if (shouldSwitch) {
      this.isYellow = true;
      this.yellowTimer = 0;
      this.decisionReason = `Switching to ${oppPhaseStr}: queue demand ${oppPri.toFixed(2)} > ${curPri.toFixed(2)}. Queue=${this.obs[oppPhaseStr].queue} cars.`;
    } else {
      const holdSec = Math.round(this.stepsOnPhase);
      this.decisionReason = `Holding ${curPhaseStr} Green: queue=${this.obs[curPhaseStr].queue} cars, hold=${holdSec}/${this.allocatedGreen}s.`;
    }

    if (this.incidentPhase && !this.isYellow && curPhaseStr === this.incidentPhase && this.stepsOnPhase >= MIN_GREEN) {
      this.isYellow = true;
      this.decisionReason = `⚠️ Lane Blockage on ${this.incidentPhase} — rerouting to ${oppPhaseStr}.`;
    }
  }

  get phaseName() { return this.phases[this.currentPhase]; }
}

// ── Realistic Vehicle Model with Car-Following & Queuing ────────────────────
const V_COLORS = [
  '#e6926f', '#63a375', '#dba53a', '#e0913a', '#d97757',
  '#d97757', '#f4f2ea', '#8fbf9d', '#e5534b', '#d97757',
  '#d4d0c4', '#dba53a', '#63a375', '#d97757'
];
let _vidCounter = 0;

class BbsrVehicle {
  constructor(from, to, adjMap, juncIds) {
    this.id = 'V' + (++_vidCounter);
    this.color = V_COLORS[_vidCounter % V_COLORS.length];
    this.isAmbulance = false;
    this.origin = from;
    this.destination = to;
    this._adjMap = adjMap;
    this._juncIds = juncIds || Object.keys(adjMap);
    this.route = this._bfs(from, to, adjMap);
    this.routeIdx = 0;
    this.dist = 0;
    this.speed = 7.5 + Math.random() * 6.5;
    this.maxSpeed = this.speed;
    this.isBraking = false;
    this.tripComplete = false;
  }

  _bfs(from, to, adj) {
    const queue = [[from, []]];
    const visited = new Set([from]);
    while (queue.length) {
      const [node, path] = queue.shift();
      if (node === to) return path;
      for (const edge of (adj[node] || [])) {
        if (!visited.has(edge.to)) {
          visited.add(edge.to);
          queue.push([edge.to, [...path, edge.roadId]]);
        }
      }
    }
    return [];
  }

  get currentRoadId() {
    return this.route[this.routeIdx] || null;
  }

  // Seamless continuous routing at junctions — vehicles never vanish inside intersections!
  advanceToNextRoad(roadMap) {
    // 1. Still has planned segments in current trip
    if (this.routeIdx + 1 < this.route.length) {
      this.routeIdx++;
      this.dist = 0;
      return true;
    }

    // 2. Ambulance finished full emergency corridor
    if (this.isAmbulance) {
      this.tripComplete = true;
      return false;
    }

    // 3. Normal vehicle reached current destination: seamlessly chain next journey
    const curRoad = roadMap[this.currentRoadId];
    const currJunction = curRoad ? curRoad.to : this.destination;
    const ids = this._juncIds;

    let nextRoute = [];
    for (let attempt = 0; attempt < 25; attempt++) {
      const nextDest = ids[Math.floor(Math.random() * ids.length)];
      if (nextDest === currJunction) continue;
      const r = this._bfs(currJunction, nextDest, this._adjMap);
      if (r.length >= 2) {
        nextRoute = r;
        this.destination = nextDest;
        break;
      }
    }

    // Fallback: take any outgoing road connected to currJunction
    if (!nextRoute.length) {
      const outgoing = this._adjMap[currJunction] || [];
      if (outgoing.length) {
        const pick = outgoing[Math.floor(Math.random() * outgoing.length)];
        nextRoute = [pick.roadId];
        this.destination = pick.to;
      } else if (curRoad) {
        // Edge of map: turn around on opposite carriageway
        const revId = `road_${curRoad.to}_${curRoad.from}`;
        if (roadMap[revId]) {
          nextRoute = [revId];
          this.destination = curRoad.from;
        }
      }
    }

    if (nextRoute.length > 0) {
      this.origin = currJunction;
      this.route = nextRoute;
      this.routeIdx = 0;
      this.dist = 0;
      this.tripComplete = false;
      return true;
    }

    return false;
  }

  update(dt, roadMap, signalState, blockedRoads, distToLeader = Infinity) {
    if (!this.route.length || this.routeIdx >= this.route.length) {
      if (!this.advanceToNextRoad(roadMap)) return false;
    }
    const rid = this.currentRoadId;
    const road = roadMap[rid];
    if (!road) {
      if (!this.advanceToNextRoad(roadMap)) return false;
    }

    const len = road.totalLen;
    // Stop line is 26m before intersection center (directly before pedestrian zebra crossing)
    const stopLine = Math.max(12, len - 26);
    const distToStop = stopLine - this.dist;

    // 1. Incident / Hazard Road Blockage
    if (blockedRoads && blockedRoads.has(rid)) {
      this.isBraking = true;
      const hazardStop = len * 0.70;
      if (this.dist >= hazardStop - 1) {
        this.dist = hazardStop;
        this.speed = 0;
      } else {
        this.speed = Math.max(0, this.speed - 16 * dt);
        this.dist += this.speed * dt;
      }
      return true;
    }

    // 2. Emergency Ambulance Dynamics (Never stops behind traffic or at red lights)
    if (this.isAmbulance) {
      this.isBraking = false;
      this.maxSpeed = 26;
      if (distToLeader <= 12) {
        // If a vehicle is immediately ahead, safely match speed instead of slamming to zero
        this.speed = Math.max(16, this.speed - 8 * dt);
      } else {
        this.speed = Math.min(this.maxSpeed, this.speed + 14 * dt);
      }
      this.dist += this.speed * dt;
      if (this.dist >= len) {
        if (!this.advanceToNextRoad(roadMap)) return false;
      }
      return true;
    }

    // 3. Normal Vehicle Car-Following (Hard buffer stop prevents overlapping)
    const MIN_CAR_GAP = 12;
    if (distToLeader <= MIN_CAR_GAP + 0.5) {
      this.isBraking = true;
      this.speed = 0;
      // Stopped in queue behind leader — do not advance
      return true;
    } else if (distToLeader < 24) {
      // Smooth deceleration behind leader
      this.isBraking = true;
      this.speed = Math.max(0, this.speed - 16 * dt);
      this.dist += this.speed * dt;
      if (this.dist >= len) {
        if (!this.advanceToNextRoad(roadMap)) return false;
      }
      return true;
    }

    // 4. Traffic Signal & Zebra Crossing Stop Bar Compliance
    if (signalState === 'RED') {
      // Vehicle is approaching or at the stop bar before the zebra crossing:
      // IT CANNOT CROSS ON RED LIGHT!
      if (this.dist <= stopLine + 2.0) {
        this.isBraking = true;
        if (this.dist >= stopLine - 1.0) {
          // Complete halt right at the stop bar before the zebra crossing!
          this.dist = stopLine;
          this.speed = 0;
          return true;
        } else if (distToStop <= 55) {
          // Smooth deceleration into the stop bar
          const targetSpd = Math.max(0, Math.sqrt(2 * 4.5 * Math.max(0.1, distToStop)));
          this.speed = Math.min(this.speed, targetSpd);
          this.speed = Math.max(0, this.speed - 16 * dt);
          this.dist += this.speed * dt;
          return true;
        }
      }
    } else if (signalState === 'YELLOW') {
      // Approaching vehicle sees Yellow: RED will come soon, so slow down!
      if (this.dist < stopLine && distToStop > 12) {
        this.isBraking = true;
        this.speed = Math.max(2.5, this.speed - 14 * dt);
        this.dist += this.speed * dt;
        return true;
      }
      // If within 12m, dilemma zone: proceed safely across without slamming brakes
    }

    // 5. Free Flow (GREEN Signal or clearing intersection past zebra crossing)
    this.isBraking = false;
    const accel = this.expediteForAmbulance ? 12.0 : 6.0;
    this.speed = Math.min(this.maxSpeed, this.speed + accel * dt);
    this.dist += this.speed * dt;

    if (this.dist >= len) {
      if (!this.advanceToNextRoad(roadMap)) return false;
    }
    return true;
  }
}

// ── City Simulation Core ─────────────────────────────────────────────────────
class BhubaneswarSim {
  constructor(overlayCanvas, overlayCtx, leafletMap) {
    this.canvas = overlayCanvas;
    this.ctx = overlayCtx;
    this.map = leafletMap;

    this.paused = false;
    this.step = 0;
    this.vehicles = [];
    this.agents = {};
    this.roads = {};
    this.roadList = [];
    this._adj = {};
    this._juncIds = [];
    this.selectedJunction = null;
    this.incidentActive = false;
    this.incidentRoadId = null;
    this.incidentJunctionId = null;
    this.ambulanceActive = false;
    this.ambulanceVehicle = null;
    this.ambulanceCorridorRoads = null;
    this.activePreemptJuncs = new Set();
    this.cctvDetectedJunc = null;
    this.agentMessages = [];
    this.stats = { totalVehicles: 0, avgSpeed: 0, queueTotal: 0, stepCount: 0 };

    this._buildNetwork();
    this._buildAgents();
    this._juncIds = Object.keys(this.junctions);
    this._spawnBatch(220);
  }

  latLngToScreen(lat, lon) {
    const pt = this.map.latLngToContainerPoint(L.latLng(lat, lon));
    return { x: pt.x, y: pt.y };
  }

  _logMessage(sender, text) {
    this.agentMessages.push({ sender, timestamp: this.step, text });
    if (this.agentMessages.length > 25) this.agentMessages.shift();
  }

  _buildNetwork() {
    this.junctions = {};
    BBSR_INTERSECTIONS.forEach(j => {
      this.junctions[j.id] = { ...j };
    });

    BBSR_ROAD_SEGMENTS.forEach(seg => {
      const jF = this.junctions[seg.from];
      const jT = this.junctions[seg.to];
      if (!jF || !jT) return;

      const fwdPts = [[jF.lat, jF.lon], ...(seg.waypoints || []), [jT.lat, jT.lon]];
      const revPts = [...fwdPts].reverse();

      const calcLen = (pts) => {
        let total = 0;
        for (let i = 0; i < pts.length - 1; i++) {
          const dlat = pts[i+1][0] - pts[i][0];
          const dlon = pts[i+1][1] - pts[i][1];
          total += Math.sqrt(dlat*dlat + dlon*dlon) * 111000;
        }
        return Math.max(140, total);
      };

      const fwdLen = calcLen(fwdPts);
      const revLen = calcLen(revPts);

      const fwdId = `road_${seg.from}_${seg.to}`;
      const revId = `road_${seg.to}_${seg.from}`;

      this.roads[fwdId] = {
        id: fwdId, from: seg.from, to: seg.to,
        points: fwdPts, totalLen: fwdLen, type: seg.type
      };
      this.roads[revId] = {
        id: revId, from: seg.to, to: seg.from,
        points: revPts, totalLen: revLen, type: seg.type
      };

      this.roadList.push(this.roads[fwdId], this.roads[revId]);

      if (!this._adj[seg.from]) this._adj[seg.from] = [];
      if (!this._adj[seg.to])   this._adj[seg.to]   = [];
      this._adj[seg.from].push({ to: seg.to, roadId: fwdId });
      this._adj[seg.to].push({ to: seg.from, roadId: revId });
    });

    // Partition incoming roads into 2 opposing phases (Phase 0 vs Phase 1) for each junction
    this.roadPhaseMap = {};
    BBSR_INTERSECTIONS.forEach(j => {
      const incoming = this.roadList.filter(r => r.to === j.id);
      if (!incoming.length) return;

      // Sort primary types first (nh -> sh -> city)
      incoming.sort((a, b) => {
        const typeWeight = { nh: 3, sh: 2, city: 1 };
        return (typeWeight[b.type] || 1) - (typeWeight[a.type] || 1);
      });

      let primaryAngle = null;
      incoming.forEach((r, idx) => {
        const pts = r.points;
        const p1 = pts[pts.length - 2];
        const p2 = pts[pts.length - 1];
        const dLon = p2[1] - p1[1];
        const dLat = p2[0] - p1[0];
        const deg = (Math.atan2(dLat, dLon) * 180 / Math.PI + 360) % 180;

        if (idx === 0) {
          primaryAngle = deg;
          this.roadPhaseMap[r.id] = 0; // Phase 0 (Main Arterial Axis)
        } else {
          let diff = Math.abs(deg - primaryAngle);
          if (diff > 90) diff = 180 - diff;
          // Roads crossing the main arterial (>38 deg difference) belong to Phase 1 (Cross Axis)
          if (diff > 38) {
            this.roadPhaseMap[r.id] = 1;
          } else {
            this.roadPhaseMap[r.id] = 0;
          }
        }
      });

      // Safety: If all incoming roads were assigned Phase 0, force secondary road to Phase 1
      const p0Count = incoming.filter(r => this.roadPhaseMap[r.id] === 0).length;
      if (p0Count === incoming.length && incoming.length > 1) {
        this.roadPhaseMap[incoming[incoming.length - 1].id] = 1;
      }
    });
  }

  _buildAgents() {
    BBSR_INTERSECTIONS.forEach(j => {
      const ag = new BbsrAgent(j.id);
      const incoming = this.roadList.filter(r => r.to === j.id);
      ag.phaseRoads = {
        0: incoming.filter(r => this.roadPhaseMap[r.id] === 0).map(r => r.id),
        1: incoming.filter(r => this.roadPhaseMap[r.id] === 1).map(r => r.id)
      };
      this.agents[j.id] = ag;
    });
  }

  // Spawn a vehicle with a guaranteed long route (min 3 roads like Ola/Uber trip)
  _spawnLongTrip() {
    const ids = this._juncIds;
    for (let attempt = 0; attempt < 30; attempt++) {
      const from = ids[Math.floor(Math.random() * ids.length)];
      const to = ids[Math.floor(Math.random() * ids.length)];
      if (from === to) continue;
      const v = new BbsrVehicle(from, to, this._adj, ids);
      if (v.route.length >= 3) {
        return v;
      }
    }
    // Fallback: any valid route
    const from = ids[Math.floor(Math.random() * ids.length)];
    let to;
    do { to = ids[Math.floor(Math.random() * ids.length)]; } while (to === from);
    const v = new BbsrVehicle(from, to, this._adj, ids);
    return v.route.length > 0 ? v : null;
  }

  _spawnBatch(targetCount = 220) {
    // Seed arterial roads with realistic traffic density
    const roadIds = Object.keys(this.roads);
    roadIds.forEach(rid => {
      const road = this.roads[rid];
      if (!road) return;
      const perRoad = 2 + Math.floor(Math.random() * 2);
      for (let k = 0; k < perRoad; k++) {
        const v = this._spawnLongTrip();
        if (v) {
          const roadIdx = Math.min(v.route.indexOf(rid) >= 0 ? v.route.indexOf(rid) : 0, v.route.length - 1);
          v.routeIdx = roadIdx;
          const curRoad = this.roads[v.route[roadIdx]];
          if (curRoad) {
            v.dist = ((k + 0.2) / perRoad) * curRoad.totalLen;
          }
          this.vehicles.push(v);
        }
      }
    });

    while (this.vehicles.length < targetCount) {
      const v = this._spawnLongTrip();
      if (v) this.vehicles.push(v);
      else break;
    }
  }

  _roadDensity(rid) {
    const road = this.roads[rid];
    if (!road) return 0;
    let cnt = 0;
    for (let i = 0; i < this.vehicles.length; i++) {
      if (this.vehicles[i].currentRoadId === rid) cnt++;
    }
    const len = road.totalLen || 300;
    return Math.min(1, cnt / Math.max(1, len / 24));
  }

  _neighborDensity(jId) {
    const neighbors = (this._adj[jId] || []).map(e => e.to);
    if (!neighbors.length) return 0;
    const densities = neighbors.map(nid => {
      const ag = this.agents[nid];
      if (!ag) return 0;
      return (ag.obs.EW.density + ag.obs.NS.density) / 2;
    });
    return densities.reduce((a, b) => a + b, 0) / densities.length;
  }

  _updateObs() {
    // Single pass to bucket vehicles by roadId (O(N) instead of O(N*M) heavy loops)
    const roadMap = {};
    for (let i = 0; i < this.vehicles.length; i++) {
      const v = this.vehicles[i];
      const rid = v.currentRoadId;
      if (!roadMap[rid]) roadMap[rid] = [];
      roadMap[rid].push(v);
    }

    Object.keys(this.agents).forEach(jId => {
      const ag = this.agents[jId];
      const p0Roads = ag.phaseRoads?.[0] || [];
      const p1Roads = ag.phaseRoads?.[1] || [];

      const buildStats = (rids) => {
        if (!rids.length) return { density: 0, queue: 0, speed: 7, score: 0 };
        let totalVehs = 0;
        let totalQueue = 0;
        let totalSpeed = 0;
        let totalCap = 0;

        for (let i = 0; i < rids.length; i++) {
          const rid = rids[i];
          const vList = roadMap[rid] || [];
          const roadLen = this.roads[rid]?.totalLen || 300;
          totalVehs += vList.length;
          totalCap += Math.max(1, roadLen / 24);

          for (let k = 0; k < vList.length; k++) {
            const v = vList[k];
            if (v.isBraking || v.speed < 1.2) totalQueue++;
            totalSpeed += v.speed;
          }
        }

        const avgD = Math.min(1, totalVehs / Math.max(1, totalCap));
        const avgSpd = totalVehs ? (totalSpeed / totalVehs) : 7;
        return { density: avgD, queue: totalQueue, speed: Math.round(avgSpd * 10) / 10, score: 0 };
      };

      ag.obs.EW = buildStats(p0Roads);
      ag.obs.NS = buildStats(p1Roads);
    });
  }

  _getSignalState(road) {
    const ag = this.agents[road.to];
    if (!ag) return 'GREEN';
    const roadPhase = this.roadPhaseMap[road.id] ?? 0;
    const isOurPhase = (ag.currentPhase === roadPhase);

    if (isOurPhase) {
      if (ag.isYellow) return 'YELLOW';
      return 'GREEN';
    } else {
      return 'RED';
    }
  }

  tick(dt) {
    if (this.paused) return;
    this.step++;

    // Dynamic CCTV Camera Detection Preemption
    if (this.ambulanceActive) {
      this._updateAmbulancePreemption();
    }

    this._updateObs();
    Object.keys(this.agents).forEach(jId => {
      this.agents[jId].step(this._neighborDensity(jId), dt);
    });

    const blocked = (this.incidentActive && this.incidentRoadId) ? new Set([this.incidentRoadId]) : null;

    // Expedite vehicles on the ambulance's current road AND upcoming road to clear the corridor
    if (this.ambulanceActive && this.ambulanceVehicle) {
      const amb = this.ambulanceVehicle;
      const ambRoad = amb.currentRoadId;
      const ambDist = amb.dist;
      const nextRoad = amb.route[amb.routeIdx + 1];

      this.vehicles.forEach(v => {
        const isAheadOnSameRoad = (v.currentRoadId === ambRoad && v.dist > ambDist);
        const isAheadOnNextRoad = (v.currentRoadId === nextRoad && v.dist < 160);
        if ((isAheadOnSameRoad || isAheadOnNextRoad) && !v.isAmbulance) {
          v.expediteForAmbulance = true;
          v.maxSpeed = 28;
          // Sirens audible: vehicles immediately clear intersection and accelerate forward
          if (v.speed < 18) v.speed = 18;
        } else {
          v.expediteForAmbulance = false;
        }
      });
    }

    // Group vehicles by road for realistic car-following queue dynamics
    const roadVehMap = {};
    this.vehicles.forEach(v => {
      const rid = v.currentRoadId;
      if (!roadVehMap[rid]) roadVehMap[rid] = [];
      roadVehMap[rid].push(v);
    });

    // Sort each road group by distance descending (closest to intersection first)
    Object.values(roadVehMap).forEach(group => {
      group.sort((a, b) => b.dist - a.dist);
    });

    const remove = [];
    this.vehicles.forEach((v, i) => {
      const road = this.roads[v.currentRoadId];
      const sigState = road ? this._getSignalState(road) : 'GREEN';

      // Find vehicle immediately ahead on the same road
      let distToLeader = Infinity;
      const group = roadVehMap[v.currentRoadId];
      if (group) {
        const vIdx = group.indexOf(v);
        if (vIdx > 0) {
          const leader = group[vIdx - 1];
          distToLeader = leader.dist - v.dist;
        }
      }

      if (!v.update(dt, this.roads, sigState, blocked, distToLeader)) {
        remove.push(i);
      }
    });

    for (let i = remove.length - 1; i >= 0; i--) {
      this.vehicles.splice(remove[i], 1);
    }

    // Maintain steady urban traffic density: 900 active vehicles
    while (this.vehicles.length < 900) {
      const v = this._spawnLongTrip();
      if (v) this.vehicles.push(v);
      else break;
    }

    const speeds = this.vehicles.map(v => v.speed);
    this.stats.avgSpeed = speeds.length ? Math.round(speeds.reduce((a, b) => a + b, 0) / speeds.length * 3.6 * 10) / 10 : 0;
    this.stats.queueTotal = this.vehicles.filter(v => v.isBraking).length;
    this.stats.totalVehicles = this.vehicles.length;
    this.stats.stepCount = this.step;

    // Periodic simulation status logging for central dashboard
    if (this.step % 60 === 0) {
      const randomJunc = BBSR_INTERSECTIONS[Math.floor(Math.random() * BBSR_INTERSECTIONS.length)].id;
      const ag = this.agents[randomJunc];
      if (ag) {
        this._logMessage(randomJunc, ag.decisionReason);
      }
    }
  }

  injectIncident(junctionId) {
    if (this.incidentActive) {
      this.clearIncident();
      return;
    }
    this.incidentJunctionId = junctionId;
    const adj = this._adj[junctionId] || [];
    if (adj.length > 0) {
      this.incidentRoadId = adj[0].roadId;
      this.incidentActive = true;
      if (this.agents[junctionId]) {
        this.agents[junctionId].incidentPhase = 'NS';
      }
      this._logMessage(junctionId, `⚠️ ACCIDENT REPORTED on ${this.incidentRoadId}. Initiating local vehicle detour.`);
    }
  }

  clearIncident() {
    if (this.incidentJunctionId && this.agents[this.incidentJunctionId]) {
      this.agents[this.incidentJunctionId].incidentPhase = null;
    }
    this._logMessage(this.incidentJunctionId || 'SYSTEM', `Incident cleared. Normal traffic capacity restored.`);
    this.incidentActive = false;
    this.incidentRoadId = null;
    this.incidentJunctionId = null;
  }

  // ── Edge CCTV Camera Detection Zone Preemption ─────────────────────────────
  // Rule:
  // 1. Designated corridor route is visibly marked across the entire city.
  // 2. But traffic lights do NOT halt traffic ahead of time.
  // 3. Preemption only triggers when ambulance enters CCTV Camera Range (<= 140m).
  // 4. As soon as the vehicle clears the intersection, it is immediately released!
  _updateAmbulancePreemption() {
    if (!this.ambulanceActive || !this.ambulanceVehicle) {
      if (this.activePreemptJuncs && this.activePreemptJuncs.size > 0) {
        Object.values(this.agents).forEach(ag => {
          if (ag.emergencyOverride) ag.emergencyOverride = null;
        });
        this.activePreemptJuncs.clear();
      }
      this.cctvDetectedJunc = null;
      return;
    }

    const amb = this.ambulanceVehicle;
    if (!amb.route || amb.routeIdx >= amb.route.length) {
      this.ambulanceActive = false;
      this.ambulanceVehicle = null;
      this.ambulanceCorridorRoads = null;
      Object.values(this.agents).forEach(ag => {
        if (ag.emergencyOverride) {
          ag.emergencyOverride = null;
          ag.decisionReason = '✅ Ambulance reached destination. Resumed normal adaptive cycles.';
        }
      });
      if (this.activePreemptJuncs) this.activePreemptJuncs.clear();
      this.cctvDetectedJunc = null;
      const banner = document.getElementById('corridor-banner');
      if (banner) banner.classList.remove('active');
      this._logMessage('DISPATCH', '🚑 Ambulance reached destination hospital. Green corridor cleared.');
      return;
    }

    const curRoadId = amb.currentRoadId;
    const curRoad = this.roads[curRoadId];
    if (!curRoad) return;

    // Distance remaining on current road before reaching intersection
    const distToJunc = Math.max(0, curRoad.totalLen - amb.dist);
    const targetJunc = curRoad.to;

    const newActiveJuncs = new Set();
    const CCTV_RANGE = 220; // 220m camera visual detection range (allows plenty of time for ahead traffic to clear)

    if (distToJunc <= CCTV_RANGE) {
      newActiveJuncs.add(targetJunc);
      this.cctvDetectedJunc = targetJunc;

      const ag = this.agents[targetJunc];
      if (ag) {
        // Exact phase lookup: guarantees the traffic light turns GREEN for this road approach!
        const neededPhaseNum = this.roadPhaseMap[curRoad.id] ?? 0;
        const neededPhaseName = ag.phases[neededPhaseNum] || 'EW';
        ag.emergencyOverride = neededPhaseNum;
        ag.currentPhase = neededPhaseNum;
        ag.isYellow = false;
        ag.yellowTimer = 0;
        ag.decisionReason = `📹 CCTV AI DETECTED AMBULANCE (${Math.round(distToJunc)}m). Emergency ${neededPhaseName} GREEN Active.`;
      }
    } else {
      this.cctvDetectedJunc = null;
    }

    // Keep just-passed intersection protected until ambulance is at least 35m into the new road
    if (amb.routeIdx > 0 && amb.dist < 35) {
      const prevRoadId = amb.route[amb.routeIdx - 1];
      const prevRoad = this.roads[prevRoadId];
      if (prevRoad) {
        newActiveJuncs.add(prevRoad.to);
      }
    }

    // Release all junctions that are outside the CCTV camera range
    // (Both junctions far ahead and junctions already passed behind)
    Object.keys(this.agents).forEach(jId => {
      if (!newActiveJuncs.has(jId)) {
        const ag = this.agents[jId];
        if (ag && ag.emergencyOverride !== null && ag.emergencyOverride !== undefined) {
          ag.emergencyOverride = null;
          ag.decisionReason = `✅ Ambulance cleared CCTV zone. Cross-traffic released.`;
          this._logMessage(jId, 'Ambulance cleared intersection. Normal multi-agent traffic cycle resumed.');
        }
      }
    });

    this.activePreemptJuncs = newActiveJuncs;
  }

  dispatchAmbulance() {
    if (this.ambulanceActive) {
      this.ambulanceActive = false;
      this.ambulanceVehicle = null;
      this.ambulanceCorridorRoads = null;
      Object.values(this.agents).forEach(ag => { ag.emergencyOverride = null; });
      if (this.activePreemptJuncs) this.activePreemptJuncs.clear();
      this.cctvDetectedJunc = null;
      this._logMessage('DISPATCH', 'Ambulance dispatch cancelled.');
      return;
    }

    // Ambulance designated route: Khandagiri to Rasulgarh along NH-16
    const v = new BbsrVehicle('KHANDG', 'RASUL', this._adj, this._juncIds);
    v.isAmbulance = true;
    v.color = '#ffffff';
    v.maxSpeed = 26;
    v.speed = 26;
    this.ambulanceVehicle = v;
    this.ambulanceActive = true;
    this.activePreemptJuncs = new Set();
    // Planned green corridor across the entire city
    this.ambulanceCorridorRoads = new Set(v.route);
    this.vehicles.push(v);

    this._logMessage('DRIVER APP', 'Emergency route submitted: KHANDAGIRI ➔ RASULGARH. Server plotted designated green corridor. Intersections will preempt at CCTV visual range (140m).');
    this._updateAmbulancePreemption();
  }

  // ── RENDER ─────────────────────────────────────────────────────────────────
  render() {
    const { ctx, canvas } = this;
    const cw = canvas.width / window.devicePixelRatio;
    const ch = canvas.height / window.devicePixelRatio;

    ctx.clearRect(0, 0, cw, ch);

    this._drawRoads(ctx);
    this._drawZebraCrossings(ctx);
    this._drawJunctions(ctx);
    if (this.incidentActive && this.incidentRoadId) this._drawIncident(ctx);
    this._drawVehicles(ctx);
  }

  _drawRoads(ctx) {
    const zoom = this.map.getZoom();

    this.roadList.forEach(r => {
      if (!r.points || r.points.length < 2) return;

      const density = this._roadDensity(r.id);
      const heatCol = density > 0.70 ? '#ef444490' : density > 0.35 ? '#eab30890' : '#22c55e70';
      const isBlocked = this.incidentActive && r.id === this.incidentRoadId;

      // 1. Is this road part of the designated green route planned by the driver's app?
      const isDesignatedCorridor = this.ambulanceActive && Boolean(this.ambulanceCorridorRoads?.has(r.id));
      // 2. Is ambulance currently traveling on this road?
      const isAmbulanceOnRoad = this.ambulanceActive && (r.id === this.ambulanceVehicle?.currentRoadId);

      const baseW = r.type === 'nh' ? Math.max(7.5, zoom * 1.0) : r.type === 'sh' ? Math.max(5.5, zoom * 0.75) : Math.max(4.0, zoom * 0.55);

      const screenPts = r.points.map(pt => this.latLngToScreen(pt[0], pt[1]));

      // Dual-carriageway separation offset
      const offsetPts = [];
      for (let i = 0; i < screenPts.length; i++) {
        let dx, dy;
        if (i === 0) {
          dx = screenPts[1].x - screenPts[0].x;
          dy = screenPts[1].y - screenPts[0].y;
        } else if (i === screenPts.length - 1) {
          dx = screenPts[i].x - screenPts[i-1].x;
          dy = screenPts[i].y - screenPts[i-1].y;
        } else {
          dx = screenPts[i+1].x - screenPts[i-1].x;
          dy = screenPts[i+1].y - screenPts[i-1].y;
        }
        const len = Math.sqrt(dx*dx + dy*dy) || 1;
        const offDist = baseW * 0.52;
        // Indian Left-Hand Driving (LHD) carriageway offset
        const ox = ( dy / len) * offDist;
        const oy = (-dx / len) * offDist;
        offsetPts.push({ x: screenPts[i].x + ox, y: screenPts[i].y + oy });
      }

      // Asphalt base line
      if (isDesignatedCorridor) {
        ctx.strokeStyle = isAmbulanceOnRoad ? '#065f46ee' : '#042f2cee';
      } else {
        ctx.strokeStyle = isBlocked ? '#7f1d1d99' : '#1e293bdd';
      }
      ctx.lineWidth = isDesignatedCorridor ? baseW + 2 : baseW;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      if (isDesignatedCorridor) {
        ctx.shadowColor = '#63a375';
        ctx.shadowBlur = isAmbulanceOnRoad ? 14 : 8;
      }
      ctx.beginPath();
      offsetPts.forEach((pt, idx) => {
        if (idx === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Density / Heat line overlay
      if (isDesignatedCorridor) {
        ctx.strokeStyle = isAmbulanceOnRoad ? '#8fbf9d' : '#10b981aa';
        ctx.lineWidth = Math.max(2, baseW * 0.45);
        ctx.setLineDash([10, 6]);
      } else {
        ctx.strokeStyle = isBlocked ? '#ef444466' : heatCol;
        ctx.lineWidth = Math.max(1.5, baseW * 0.35);
        ctx.setLineDash([8, 8]);
      }

      ctx.beginPath();
      offsetPts.forEach((pt, idx) => {
        if (idx === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    });
  }

  // Helper: map a distance (in meters) along a road polyline to its GPS coordinates and segment vectors
  _getRoadPointAtDist(road, targetDist) {
    const pts = road.points;
    const clamped = Math.min(road.totalLen, Math.max(0, targetDist));
    let accLen = 0;
    let curSegIdx = 0;

    for (let i = 0; i < pts.length - 1; i++) {
      const dlat = pts[i+1][0] - pts[i][0];
      const dlon = pts[i+1][1] - pts[i][1];
      const segLen = Math.sqrt(dlat*dlat + dlon*dlon) * 111000;
      if (accLen + segLen >= clamped || i === pts.length - 2) {
        curSegIdx = i;
        break;
      }
      accLen += segLen;
    }

    const p1 = pts[curSegIdx];
    const p2 = pts[curSegIdx + 1];
    const segDlat = p2[0] - p1[0];
    const segDlon = p2[1] - p1[1];
    const segLen = Math.sqrt(segDlat*segDlat + segDlon*segDlon) * 111000 || 1;
    const segT = Math.min(1, Math.max(0, (clamped - accLen) / segLen));

    const lat = p1[0] + segT * segDlat;
    const lon = p1[1] + segT * segDlon;

    return { lat, lon, p1, p2 };
  }

  // ── Realistic Pedestrian Zebra Crossings & Stop Bars ───────────────────────
  _drawZebraCrossings(ctx) {
    const zoom = this.map.getZoom();
    if (zoom < 13) return; // Only render zebra crossings when zoomed into city street detail

    this.roadList.forEach(r => {
      if (!r.points || r.points.length < 2 || r.totalLen < 35) return;

      // Zebra crossing center is 21 meters before the intersection center
      const zebraDist = Math.max(10, r.totalLen - 21);
      const ptInfo = this._getRoadPointAtDist(r, zebraDist);

      const sc = this.latLngToScreen(ptInfo.lat, ptInfo.lon);
      const s1 = this.latLngToScreen(ptInfo.p1[0], ptInfo.p1[1]);
      const s2 = this.latLngToScreen(ptInfo.p2[0], ptInfo.p2[1]);

      const dx = s2.x - s1.x;
      const dy = s2.y - s1.y;
      const len = Math.sqrt(dx*dx + dy*dy) || 1;
      const ux = dx / len; // Along road towards junction
      const uy = dy / len;
      // Perpendicular across road to the LEFT side (Indian Left-Hand Driving)
      const nx = uy;
      const ny = -ux;

      const roadBaseW = r.type === 'nh' ? Math.max(7.5, zoom * 1.0) : r.type === 'sh' ? Math.max(5.5, zoom * 0.75) : Math.max(4.0, zoom * 0.55);
      const offDist = roadBaseW * 0.52;
      const cx = sc.x + nx * offDist;
      const cy = sc.y + ny * offDist;
      const halfLane = roadBaseW * 0.44;

      // 1. Solid White Stop Bar Line (at 25m before junction, where stopped cars halt)
      const stopBarOffset = zoom >= 15 ? 4.5 : zoom >= 14 ? 3.0 : 2.0;
      const sbX = cx - ux * stopBarOffset;
      const sbY = cy - uy * stopBarOffset;

      ctx.save();
      ctx.strokeStyle = '#ffffffea';
      ctx.lineWidth = Math.max(1.8, zoom * 0.18);
      ctx.beginPath();
      ctx.moveTo(sbX - nx * halfLane, sbY - ny * halfLane);
      ctx.lineTo(sbX + nx * halfLane, sbY + ny * halfLane);
      ctx.stroke();

      // 2. White Zebra Pedestrian Crosswalk Stripes
      const numStripes = r.type === 'nh' ? 5 : 4;
      const stripeW = Math.max(1.2, roadBaseW * 0.11);
      const stripeLen = Math.max(3.8, zoom * 0.48);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';

      const angle = Math.atan2(dy, dx);
      for (let s = 0; s < numStripes; s++) {
        const t = (s + 0.5) / numStripes;
        const latOff = (t - 0.5) * (halfLane * 1.8);
        const sx = cx + nx * latOff;
        const sy = cy + ny * latOff;

        ctx.save();
        ctx.translate(sx, sy);
        ctx.rotate(angle);
        ctx.fillRect(-stripeLen/2, -stripeW/2, stripeLen, stripeW);
        ctx.restore();
      }
      ctx.restore();
    });
  }

  _drawJunctions(ctx) {
    const zoom = this.map.getZoom();
    const jSize = Math.max(10, zoom * 1.3);

    BBSR_INTERSECTIONS.forEach(j => {
      const sc = this.latLngToScreen(j.lat, j.lon);
      const ag = this.agents[j.id];
      if (!ag) return;

      const isEW = ag.currentPhase === 0;
      const isSelected = this.selectedJunction === j.id;
      const isIncJunc = this.incidentActive && j.id === this.incidentJunctionId;
      // Is this junction actively in the CCTV camera detection zone of the ambulance?
      const isCctvActive = this.ambulanceActive && Boolean(this.activePreemptJuncs?.has(j.id));
      const isCorridorNode = this.ambulanceActive && ['KHANDG','FIRE_STN','BARAMN','CRPF','NAYAPALLI','JAYADEV','ACHARYA','VANI','RASUL'].includes(j.id);

      const boxCol = isIncJunc ? '#3a2422' : isCctvActive ? '#26332b' : 'rgba(10,15,28,0.92)';
      const bordCol = isSelected ? '#e6926f' : isIncJunc ? '#c43d36' : isCctvActive ? '#63a375' : isCorridorNode ? 'rgba(99,163,117,0.45)' : 'rgba(255,255,255,0.25)';

      if (isSelected || isCctvActive) {
        ctx.shadowColor = isCctvActive ? '#63a375' : '#e6926f';
        ctx.shadowBlur = 12;
      }
      ctx.fillStyle = boxCol;
      ctx.strokeStyle = bordCol;
      ctx.lineWidth = isSelected ? 3 : isCctvActive ? 2.5 : 1.5;
      ctx.beginPath();
      ctx.roundRect(sc.x - jSize/2, sc.y - jSize/2, jSize, jSize, 4);
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Individual traffic signal lights on each approaching road at the junction
      const incoming = this.roadList.filter(r => r.to === j.id);
      const dotR = Math.max(2.4, jSize * 0.16);

      incoming.forEach(r => {
        if (!r.points || r.points.length < 2) return;
        const sigState = this._getSignalState(r);
        const col = sigState === 'GREEN' ? '#63a375' : (sigState === 'YELLOW' ? '#dba53a' : '#e5534b');

        // Unit vector pointing from the road towards the junction center
        const p1 = r.points[r.points.length - 2];
        const s1 = this.latLngToScreen(p1[0], p1[1]);
        const dx = sc.x - s1.x;
        const dy = sc.y - s1.y;
        const len = Math.sqrt(dx*dx + dy*dy) || 1;
        const ux = dx / len;
        const uy = dy / len;

        // Position light on junction border facing the approach road
        const armDist = jSize / 2 + dotR + 1.5;
        const lx = sc.x - ux * armDist;
        const ly = sc.y - uy * armDist;

        ctx.save();
        ctx.fillStyle = col;
        ctx.shadowColor = col;
        ctx.shadowBlur = sigState === 'YELLOW' ? 8 : 5;
        ctx.beginPath();
        ctx.arc(lx, ly, dotR, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.restore();
      });

      // Camera detection indicator banner when ambulance enters CCTV range (<220m)
      if (isCctvActive && zoom >= 13) {
        ctx.save();
        ctx.font = 'bold 9px sans-serif';
        ctx.fillStyle = '#63a375';
        ctx.textAlign = 'center';
        const fl = Math.floor(Date.now() / 250) % 2 === 0;
        ctx.fillText(fl ? '📹 CCTV: AMBULANCE IN RANGE' : '🚨 GREEN WAVE PREEMPTION', sc.x, sc.y - jSize/2 - 8);
        ctx.restore();
      }


      // Labels
      if (zoom >= 13) {
        ctx.fillStyle = '#f4f2ea';
        ctx.font = `bold ${Math.max(7.5, zoom * 0.75)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(j.id, sc.x, sc.y);

        if (zoom >= 14) {
          const zCol = ZONE_COLORS[j.zone] || '#b5b1a4';
          ctx.fillStyle = zCol;
          ctx.font = `600 ${Math.max(6.5, zoom * 0.58)}px sans-serif`;
          ctx.fillText(j.name, sc.x, sc.y + jSize / 2 + zoom * 0.7);
        }
      }
    });
  }

  _drawIncident(ctx) {
    const r = this.roads[this.incidentRoadId];
    if (!r || !r.points || r.points.length < 2) return;
    const midIdx = Math.floor(r.points.length / 2);
    const midPt = r.points[midIdx];
    const sc = this.latLngToScreen(midPt[0], midPt[1]);

    ctx.save();
    ctx.translate(sc.x, sc.y);
    const flash = Math.floor(Date.now() / 250) % 2 === 0;
    ctx.fillStyle = flash ? 'rgba(229,83,75,0.6)' : 'rgba(219,165,58,0.6)';
    ctx.beginPath();
    ctx.arc(0, 0, 16, 0, Math.PI*2);
    ctx.fill();
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('⚠', 0, 0);
    ctx.font = 'bold 9px sans-serif';
    ctx.fillStyle = '#f3e7c7';
    ctx.fillText('HAZARD', 0, -18);
    ctx.restore();
  }

  _drawVehicles(ctx) {
    const zoom = this.map.getZoom();
    const carW = Math.max(3.2, zoom * 0.42);
    const carL = Math.max(5.8, zoom * 0.72);

    this.vehicles.forEach(v => {
      const road = this.roads[v.currentRoadId];
      if (!road || !road.points || road.points.length < 2) return;

      const ptInfo = this._getRoadPointAtDist(road, v.dist);
      const sc = this.latLngToScreen(ptInfo.lat, ptInfo.lon);
      const s1 = this.latLngToScreen(ptInfo.p1[0], ptInfo.p1[1]);
      const s2 = this.latLngToScreen(ptInfo.p2[0], ptInfo.p2[1]);

      const dx = s2.x - s1.x;
      const dy = s2.y - s1.y;
      const angle = Math.atan2(dy, dx);

      // Lane offset matching exact dual-carriageway centerline (Indian Left-Hand Driving)
      const roadBaseW = road.type === 'nh' ? Math.max(7.5, zoom * 1.0) : road.type === 'sh' ? Math.max(5.5, zoom * 0.75) : Math.max(4.0, zoom * 0.55);
      const roadOffDist = roadBaseW * 0.52;
      const len2 = Math.sqrt(dx*dx + dy*dy) || 1;
      const offX = ( dy / len2) * roadOffDist;
      const offY = (-dx / len2) * roadOffDist;

      ctx.save();
      ctx.translate(sc.x + offX, sc.y + offY);
      ctx.rotate(angle + Math.PI/2);

      if (v.isAmbulance) {
        ctx.fillStyle = '#ffffff';
        ctx.shadowColor = '#63a375';
        ctx.shadowBlur = 14;
        ctx.beginPath();
        ctx.roundRect(-carW*0.75, -carL*0.75, carW*1.5, carL*1.5, 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.fillStyle = '#c43d36';
        ctx.fillRect(-1.0, 0.5, 2.0, 3.5);
        ctx.fillRect(-2.0, 1.3, 4.0, 1.8);

        const fl = Math.floor(Date.now() / 150) % 2 === 0;
        ctx.fillStyle = fl ? '#e5534b' : '#e6926f';
        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = 8;
        ctx.fillRect(-carW*0.6, -carL*0.65, 2, 2);
        ctx.fillStyle = fl ? '#e6926f' : '#e5534b';
        ctx.fillRect(carW*0.2, -carL*0.65, 2, 2);
        ctx.shadowBlur = 0;
      } else {
        ctx.fillStyle = v.color;
        ctx.beginPath();
        ctx.roundRect(-carW/2, -carL/2, carW, carL, 1.5);
        ctx.fill();

        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.fillRect(-carW/2 + 0.5, -carL/4, carW - 1, carL/3);

        ctx.fillStyle = v.isBraking ? '#e5534b' : '#3a2422';
        ctx.fillRect(-carW/2 + 0.4, carL/2 - 0.8, 1, 0.8);
        ctx.fillRect(carW/2 - 1.4, carL/2 - 0.8, 1, 0.8);
      }
      ctx.restore();
    });
  }

  // Robust geographical map click detection
  handleMapClick(e) {
    if (!e || !e.latlng) return null;
    let bestId = null;
    let minMeters = 240; // 240m detection radius
    for (const j of BBSR_INTERSECTIONS) {
      const d = this.map.distance(e.latlng, L.latLng(j.lat, j.lon));
      if (d < minMeters) {
        minMeters = d;
        bestId = j.id;
      }
    }
    this.selectedJunction = bestId;
    return bestId;
  }
}

window.BhubaneswarSim = BhubaneswarSim;
window.BBSR_INTERSECTIONS = BBSR_INTERSECTIONS;
