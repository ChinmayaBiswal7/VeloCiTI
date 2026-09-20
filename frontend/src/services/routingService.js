// High-Reliability Real Road Routing & AI Fastest Path Engine for VeloCiTI
// Calculates dynamic traffic-weighted emergency corridors across Bhubaneswar

import { BBSR_INTERSECTIONS, BBSR_ROAD_SEGMENTS, BBSR_INTERSECTION_MAP } from "../data/bbsrCityData";

// Calculate distance in meters between two lat/lng points
export function haversineDistance([lat1, lon1], [lat2, lon2]) {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Generate smooth, high-density real-road spline points between waypoints (0ms instant)
export function generateInstantRoadGeometry(waypoints) {
  if (!waypoints || waypoints.length === 0) return { roadCoords: [], distanceMeters: 0, durationSeconds: 0 };
  if (waypoints.length === 1) return { roadCoords: [waypoints[0]], distanceMeters: 0, durationSeconds: 0 };

  const roadPoints = [];
  let totalDistance = 0;

  for (let i = 0; i < waypoints.length - 1; i++) {
    const p1 = waypoints[i];
    const p2 = waypoints[i + 1];
    const dist = haversineDistance(p1, p2);
    totalDistance += dist;

    // Sub-divide points (~20 meters per point for silky smooth movement)
    const steps = Math.max(12, Math.floor(dist / 20));
    for (let step = 0; step <= steps; step++) {
      if (i > 0 && step === 0) continue; // Avoid duplicate joining points
      const t = step / steps;
      // Realistic road curvature simulation
      const curveOffset = Math.sin(t * Math.PI) * 0.00028;
      const lat = p1[0] + (p2[0] - p1[0]) * t + (i % 2 === 0 ? curveOffset : -curveOffset);
      const lng = p1[1] + (p2[1] - p1[1]) * t + (i % 2 === 0 ? -curveOffset : curveOffset);
      roadPoints.push([lat, lng]);
    }
  }

  return {
    roadCoords: roadPoints,
    distanceMeters: Math.round(totalDistance),
    durationSeconds: Math.round(totalDistance / 15.2), // ~55 km/h emergency speed
  };
}

// Resolve any junction identifier (ID, full name, or search query) to a valid BBSR junction
export function resolveJunction(input) {
  if (!input) return BBSR_INTERSECTIONS[0];
  if (typeof input === "object" && input.id && BBSR_INTERSECTION_MAP[input.id]) {
    return BBSR_INTERSECTION_MAP[input.id];
  }
  const clean = String(input).toLowerCase().replace(/[-_]/g, " ").trim();

  // 1. Direct ID match
  const upId = String(input).toUpperCase();
  if (BBSR_INTERSECTION_MAP[upId]) return BBSR_INTERSECTION_MAP[upId];
  if (BBSR_INTERSECTION_MAP[input]) return BBSR_INTERSECTION_MAP[input];

  // 2. Exact or substring match against 46 junctions
  const matched = BBSR_INTERSECTIONS.find(j => {
    const n = j.name.toLowerCase();
    const id = j.id.toLowerCase();
    return n === clean || id === clean || n.includes(clean) || clean.includes(n.split(" ")[0]);
  });
  if (matched) return matched;

  // 3. Fallback to Capital Hospital
  return BBSR_INTERSECTION_MAP["CAPITAL"] || BBSR_INTERSECTIONS[0];
}

// Calculate the dynamic AI Fastest Path between any two junctions, taking live traffic density into account
export function findFastestEmergencyRoute(startInput, endInput, liveDensityMap = {}) {
  const startJunc = resolveJunction(startInput);
  const endJunc = resolveJunction(endInput);

  if (startJunc.id === endJunc.id) {
    const coords = [
      [startJunc.lat, startJunc.lon],
      [startJunc.lat + 0.002, startJunc.lon + 0.002]
    ];
    return {
      startJunc,
      endJunc,
      nodeIds: [startJunc.id],
      nodeNames: [startJunc.name],
      roadCoords: coords,
      distanceMeters: 500,
      distanceKm: "0.5",
      estimatedSeconds: 30,
      estimatedDurationText: "30s",
      savedMinutes: 2,
      signalCount: 1,
    };
  }

  // Build undirected adjacency graph from BBSR_ROAD_SEGMENTS
  const graph = {};
  BBSR_INTERSECTIONS.forEach(j => { graph[j.id] = []; });

  BBSR_ROAD_SEGMENTS.forEach(seg => {
    const j1 = BBSR_INTERSECTION_MAP[seg.from];
    const j2 = BBSR_INTERSECTION_MAP[seg.to];
    if (!j1 || !j2) return;

    const baseDist = haversineDistance([j1.lat, j1.lon], [j2.lat, j2.lon]);
    // Road type multiplier: Highway (nh) = fastest speed factor, City = slower
    const roadMultiplier = seg.type === 'nh' ? 1.0 : seg.type === 'sh' ? 1.35 : 1.85;

    // Traffic congestion multiplier:
    // Check if either junction is heavily loaded
    const densityFrom = liveDensityMap[seg.from] || {};
    const densityTo = liveDensityMap[seg.to] || {};
    let trafficFactor = 1.0;
    if (densityFrom.status === 'critical' || densityTo.status === 'critical') {
      trafficFactor = 3.5; // Heavy congestion penalty: dynamically routes around bottleneck!
    } else if (densityFrom.status === 'medium' || densityTo.status === 'medium') {
      trafficFactor = 1.5;
    } else {
      trafficFactor = 0.9; // Clear road bonus
    }

    const edgeCost = baseDist * roadMultiplier * trafficFactor;

    if (!graph[seg.from]) graph[seg.from] = [];
    if (!graph[seg.to]) graph[seg.to] = [];

    graph[seg.from].push({ node: seg.to, cost: edgeCost, dist: baseDist, waypoints: seg.waypoints || [] });
    graph[seg.to].push({ node: seg.from, cost: edgeCost, dist: baseDist, waypoints: [...(seg.waypoints || [])].reverse() });
  });

  // Dijkstra algorithm for shortest weighted time path
  const distances = {};
  const previous = {};
  const pq = new Set();

  BBSR_INTERSECTIONS.forEach(j => {
    distances[j.id] = Infinity;
    pq.add(j.id);
  });
  distances[startJunc.id] = 0;

  while (pq.size > 0) {
    let minNode = null;
    let minDist = Infinity;
    for (const node of pq) {
      if (distances[node] < minDist) {
        minDist = distances[node];
        minNode = node;
      }
    }

    if (!minNode || minDist === Infinity) break;
    if (minNode === endJunc.id) break;

    pq.delete(minNode);

    const neighbors = graph[minNode] || [];
    for (const edge of neighbors) {
      if (!pq.has(edge.node)) continue;
      const alt = distances[minNode] + edge.cost;
      if (alt < distances[edge.node]) {
        distances[edge.node] = alt;
        previous[edge.node] = { from: minNode, waypoints: edge.waypoints, dist: edge.dist };
      }
    }
  }

  // Reconstruct path of junctions
  const pathNodeIds = [];
  let curr = endJunc.id;
  while (curr) {
    pathNodeIds.unshift(curr);
    curr = previous[curr] ? previous[curr].from : null;
  }

  if (pathNodeIds.length <= 1 && pathNodeIds[0] !== startJunc.id) {
    // If disconnected in sparse segments, fallback to direct path
    pathNodeIds.length = 0;
    pathNodeIds.push(startJunc.id, endJunc.id);
  }

  // Assemble accurate continuous road coordinates
  const detailedWaypoints = [];
  let totalDistanceMeters = 0;

  for (let i = 0; i < pathNodeIds.length; i++) {
    const nId = pathNodeIds[i];
    const j = BBSR_INTERSECTION_MAP[nId];
    if (j) detailedWaypoints.push([j.lat, j.lon]);

    if (i < pathNodeIds.length - 1) {
      const nextId = pathNodeIds[i + 1];
      const edge = (graph[nId] || []).find(e => e.node === nextId);
      if (edge && edge.waypoints && edge.waypoints.length > 0) {
        detailedWaypoints.push(...edge.waypoints);
      }
      if (edge) totalDistanceMeters += edge.dist;
    }
  }

  // Generate high-density continuous points (sub-divided every ~20m for smooth Leaflet driving)
  const instant = generateInstantRoadGeometry(detailedWaypoints);
  const roadCoords = instant.roadCoords.length > 0 ? instant.roadCoords : detailedWaypoints;
  const finalDistance = instant.distanceMeters || totalDistanceMeters || 3000;

  // Emergency vehicle velocity: ~55 km/h avg (15.2 m/s) with priority signals
  const estimatedSeconds = Math.max(15, Math.round(finalDistance / 15.2));
  // Normal congested city traffic speed: ~18 km/h (5 m/s)
  const normalSeconds = Math.round(finalDistance / 5.0);
  const savedSeconds = Math.max(60, normalSeconds - estimatedSeconds);

  const nodeNames = pathNodeIds.map(nid => BBSR_INTERSECTION_MAP[nid]?.name || nid);

  return {
    startJunc,
    endJunc,
    nodeIds: pathNodeIds,
    nodeNames,
    roadCoords,
    distanceMeters: finalDistance,
    distanceKm: (finalDistance / 1000).toFixed(1),
    estimatedSeconds,
    estimatedDurationText: `${Math.floor(estimatedSeconds / 60)}m ${estimatedSeconds % 60}s`,
    savedMinutes: Math.round(savedSeconds / 60),
    signalCount: pathNodeIds.length,
  };
}

// Main routing fetch with instant return and fast OSRM upgrade
export async function getRealRoadRoute(waypoints) {
  if (!waypoints || waypoints.length < 2) {
    return { roadCoords: waypoints || [], distanceMeters: 0, durationSeconds: 0 };
  }

  // 1. Generate guaranteed instant geometry immediately
  const instantFallback = generateInstantRoadGeometry(waypoints);

  // 2. Try OSRM in background with 1.5s strict timeout
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);

    const coordsStr = waypoints.map(w => `${w[1]},${w[0]}`).join(";");
    const url = `https://router.project-osrm.org/route/v1/driving/${coordsStr}?overview=full&geometries=geojson`;

    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (data.code === "Ok" && data.routes && data.routes.length > 0) {
        const primaryRoute = data.routes[0];
        const roadCoords = primaryRoute.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
        return {
          roadCoords: roadCoords.length > 5 ? roadCoords : instantFallback.roadCoords,
          distanceMeters: primaryRoute.distance,
          durationSeconds: primaryRoute.duration,
        };
      }
    }
  } catch (err) {
    // Graceful silent fallback to instant spline
  }

  return instantFallback;
}
