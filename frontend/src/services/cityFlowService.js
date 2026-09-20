const CITYFLOW_API = import.meta.env.VITE_CITYFLOW_API || '/api';

const JUNCTION_NAMES = {
  J1: "Junction J1 — West Entry",
  J2: "Junction J2 — North Hub",
  J3: "Junction J3 — Central Cross",
  J4: "Junction J4 — East Corridor",
  J5: "Junction J5 — South Ring",
};

const JUNCTION_COORDS = {
  J1: [20.2920, 85.8180],
  J2: [20.3010, 85.8250],
  J3: [20.2961, 85.8245],
  J4: [20.2900, 85.8320],
  J5: [20.2850, 85.8240],
};

// Client-side autonomous simulation engine state (used when Python server is offline or hosted serverless)
let clientSimStep = 0;
let clientSimRunning = true;

export function generateClientSimulatedState() {
  if (clientSimRunning) {
    clientSimStep++;
  }
  const step = clientSimStep;
  const junctions = ["J1", "J2", "J3", "J4", "J5"];
  const agents = {};
  const tl_phases = {};

  junctions.forEach((jid, idx) => {
    const phasePeriod = 24 + idx * 4;
    const phaseIdx = Math.floor(step / phasePeriod) % 2;
    const isYellow = (step % phasePeriod) > (phasePeriod - 3);

    const ewQueue = Math.max(0, Math.round(5 + 4 * Math.sin((step + idx * 8) * 0.1)));
    const nsQueue = Math.max(0, Math.round(4 + 3 * Math.cos((step + idx * 6) * 0.12)));
    const ewSpeed = Math.max(2.5, 9.5 - ewQueue * 0.6);
    const nsSpeed = Math.max(2.5, 9.0 - nsQueue * 0.5);

    const ewDensity = Math.min(0.95, (ewQueue * 0.12) + 0.1);
    const nsDensity = Math.min(0.95, (nsQueue * 0.12) + 0.1);
    const overallDensity = (ewDensity + nsDensity) / 2;

    tl_phases[jid] = {
      phase_idx: phaseIdx,
      is_yellow: isYellow,
      name: isYellow ? "YELLOW PHASING" : (phaseIdx === 0 ? "EW GREEN" : "NS GREEN"),
    };

    agents[jid] = {
      overall_density: overallDensity,
      total_queue: ewQueue + nsQueue,
      is_yellow: isYellow,
      local_obs: {
        EW: {
          density: ewDensity,
          queue_length: ewQueue,
          average_speed: ewSpeed,
          congestion_score: ewDensity,
          waiting_time: ewQueue * 3.5,
          status: ewDensity > 0.7 ? "CRITICAL" : ewDensity > 0.4 ? "MEDIUM" : "LOW",
        },
        NS: {
          density: nsDensity,
          queue_length: nsQueue,
          average_speed: nsSpeed,
          congestion_score: nsDensity,
          waiting_time: nsQueue * 3.5,
          status: nsDensity > 0.7 ? "CRITICAL" : nsDensity > 0.4 ? "MEDIUM" : "LOW",
        },
      },
    };
  });

  return {
    step,
    running: clientSimRunning,
    total_vehicles: 38 + Math.round(12 * Math.sin(step * 0.05)),
    avg_travel_time: +(16.4 + 2 * Math.sin(step * 0.04)).toFixed(1),
    avg_speed: +(8.2 + 1.2 * Math.cos(step * 0.05)).toFixed(1),
    network_density: +((Object.values(agents).reduce((s, a) => s + a.overall_density, 0) / 5)).toFixed(2),
    total_waiting: Object.values(agents).reduce((s, a) => s + a.total_queue, 0),
    agents,
    tl_phases,
    isClientFallback: true,
  };
}

export function setClientSimRunning(running) {
  clientSimRunning = running;
}

export function resetClientSim() {
  clientSimStep = 0;
  clientSimRunning = true;
}

export async function fetchState() {
  const res = await fetch(`${CITYFLOW_API}/state`);
  if (!res.ok) throw new Error(`CityFlow API error: ${res.status}`);
  return res.json();
}

export async function sendControl(cmd, extra = {}) {
  await fetch(`${CITYFLOW_API}/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd, ...extra }),
  });
}

export function startSimulation() { return sendControl('start'); }
export function pauseSimulation() { return sendControl('pause'); }
export function resetSimulation() { return sendControl('reset'); }

export function transformState(raw) {
  if (!raw || !raw.agents) return [];
  const junctions = Object.keys(JUNCTION_NAMES);

  return junctions.map((jid, idx) => {
    const agent = raw.agents[jid];
    const phase = raw.tl_phases?.[jid];

    if (!agent) {
      return {
        id: jid,
        name: JUNCTION_NAMES[jid],
        gridIndex: idx,
        status: "low",
        vehicleCount: 0,
        averageSpeed: 0,
        congestionPct: 0,
        coords: JUNCTION_COORDS[jid],
        lanes: [
          { direction: "East-West", vehicleCount: 0, averageSpeed: 0, light: "red", manualActive: false },
          { direction: "North-South", vehicleCount: 0, averageSpeed: 0, light: "red", manualActive: false },
        ],
      };
    }

    const obs = agent.local_obs || {};
    const ew = obs.EW || { density: 0, queue_length: 0, average_speed: 0, congestion_score: 0, waiting_time: 0, status: "LOW" };
    const ns = obs.NS || { density: 0, queue_length: 0, average_speed: 0, congestion_score: 0, waiting_time: 0, status: "LOW" };

    const density = agent.overall_density || 0;
    const status = density > 0.7 ? "critical" : density > 0.4 ? "medium" : "low";
    const totalQueue = agent.total_queue || 0;
    const avgSpeedMs = ((ew.average_speed || 0) + (ns.average_speed || 0)) / 2;
    const avgSpeedKmh = Math.round(avgSpeedMs * 3.6);
    const congestionPct = Math.round(density * 100);

    // Determine signal lights
    const isYellow = phase?.is_yellow || agent.is_yellow;
    const isEWGreen = (phase?.phase_idx ?? 0) === 0;
    let ewLight, nsLight;
    if (isYellow) {
      ewLight = "yellow";
      nsLight = "yellow";
    } else if (isEWGreen) {
      ewLight = "green";
      nsLight = "red";
    } else {
      ewLight = "red";
      nsLight = "green";
    }

    return {
      id: jid,
      name: JUNCTION_NAMES[jid],
      gridIndex: idx,
      status,
      vehicleCount: totalQueue,
      averageSpeed: avgSpeedKmh,
      congestionPct,
      coords: JUNCTION_COORDS[jid],
      lanes: [
        {
          direction: "East-West",
          vehicleCount: ew.queue_length || 0,
          averageSpeed: Math.round((ew.average_speed || 0) * 3.6),
          light: ewLight,
          manualActive: false,
        },
        {
          direction: "North-South",
          vehicleCount: ns.queue_length || 0,
          averageSpeed: Math.round((ns.average_speed || 0) * 3.6),
          light: nsLight,
          manualActive: false,
        },
      ],
    };
  });
}

export function computeLiveStats(intersections) {
  if (!intersections || intersections.length === 0) {
    return { avgCongestion: 0, avgSpeed: 0, criticalCount: 0, mediumCount: 0, clearCount: 0, totalNodes: 5 };
  }
  const n = intersections.length;
  return {
    avgCongestion: Math.round(intersections.reduce((s, i) => s + i.congestionPct, 0) / n),
    avgSpeed: Math.round(intersections.reduce((s, i) => s + i.averageSpeed, 0) / n),
    criticalCount: intersections.filter(i => i.status === "critical").length,
    mediumCount: intersections.filter(i => i.status === "medium").length,
    clearCount: intersections.filter(i => i.status === "low").length,
    totalNodes: n,
  };
}
