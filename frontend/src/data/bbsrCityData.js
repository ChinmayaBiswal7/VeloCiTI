/**
 * bbsrCityData.js — Bhubaneswar Real GIS Network & Live Emergency Fleet
 * ======================================================================
 * 46 Real Major Intersections across Bhubaneswar with accurate coordinates,
 * Arterial Road Network segments, and Live Emergency Vehicle Fleet for real-time tracking.
 */

// ── 46 Real Major Bhubaneswar Intersections ─────────────────────────────────
export const BBSR_INTERSECTIONS = [
  // ── NH-16 Primary Arterial ──
  { id: 'KHANDG',     name: 'Khandagiri Square',          lat: 20.2575, lon: 85.7865, zone: 'heritage',   zoneName: 'Heritage Corridor' },
  { id: 'FIRE_STN',   name: 'Fire Station Square',        lat: 20.2710, lon: 85.7950, zone: 'transport',  zoneName: 'Emergency Hub' },
  { id: 'BARAMN',     name: 'Baramunda Bus Terminal',     lat: 20.2768, lon: 85.7995, zone: 'transport',  zoneName: 'Inter-State Transit' },
  { id: 'CRPF',       name: 'CRPF Square',                lat: 20.2872, lon: 85.8115, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'NAYAPALLI',  name: 'Nayapalli / Behera Sahi',    lat: 20.2930, lon: 85.8150, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'JAYADEV',    name: 'Jayadev Vihar (NH-16)',      lat: 20.3005, lon: 85.8228, zone: 'commercial', zoneName: 'Major Commercial Junction' },
  { id: 'ACHARYA',    name: 'Acharya Vihar (NH-16)',      lat: 20.3015, lon: 85.8315, zone: 'edu',        zoneName: 'University Sector' },
  { id: 'VANI',       name: 'Vani Vihar (NH-16)',         lat: 20.2985, lon: 85.8415, zone: 'edu',        zoneName: 'Utkal University' },
  { id: 'RASUL',      name: 'Rasulgarh Square (NH-16)',   lat: 20.2936, lon: 85.8647, zone: 'commercial', zoneName: 'Industrial / Commercial Gateway' },
  { id: 'PALASUNI',   name: 'Palasuni Square (NH-16)',    lat: 20.3040, lon: 85.8710, zone: 'commercial', zoneName: 'Highway Hub' },
  { id: 'MANCHES',    name: 'Mancheswar Industrial',      lat: 20.3120, lon: 85.8750, zone: 'commercial', zoneName: 'Industrial Zone' },

  // ── Nandankanan Road (Northern IT & University Corridor) ──
  { id: 'XAVIER',     name: 'Xavier Square (XIMB)',       lat: 20.3125, lon: 85.8198, zone: 'it',          zoneName: 'Institutional IT Zone' },
  { id: 'CS_PUR',     name: 'Chandrasekharpur BDA',       lat: 20.3175, lon: 85.8160, zone: 'residential',zoneName: 'BDA Residential Zone' },
  { id: 'KALINGA',    name: 'Kalinga Hospital Square',    lat: 20.3205, lon: 85.8215, zone: 'medical',    zoneName: 'Super-Specialty Medical Zone' },
  { id: 'DAMANA',     name: 'Damana Square',              lat: 20.3340, lon: 85.8185, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'SAILASHREE', name: 'Sailashree Vihar Chowk',     lat: 20.3440, lon: 85.8150, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'PATIA',      name: 'Patia Chowk',                lat: 20.3540, lon: 85.8170, zone: 'it',          zoneName: 'IT & Student Corridor' },
  { id: 'KIIT',       name: 'KIIT Square',                lat: 20.3565, lon: 85.8165, zone: 'it',          zoneName: 'KIIT Campus Hub' },
  { id: 'INFOCITY',   name: 'Infocity Square',            lat: 20.3585, lon: 85.8085, zone: 'it',          zoneName: 'Infocity Tech Hub' },
  { id: 'CHANDAKA',   name: 'Chandaka Square',            lat: 20.3650, lon: 85.7950, zone: 'it',          zoneName: 'Outer Tech Corridor' },

  // ── Western Infill: Delta, Siripur, OUAT, Gopabandhu ──
  { id: 'DELTA',      name: 'Delta Square',               lat: 20.2740, lon: 85.8105, zone: 'residential',zoneName: 'Residential Infill' },
  { id: 'GOPABANDHU', name: 'Gopabandhu Square',          lat: 20.2700, lon: 85.8210, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'SIRIPUR',    name: 'Siripur / OUAT Square',      lat: 20.2645, lon: 85.8155, zone: 'edu',        zoneName: 'OUAT Agricultural University' },

  // ── Power Grid & Bidyut Marg ──
  { id: 'POWER',      name: 'Power House Square',         lat: 20.2910, lon: 85.8235, zone: 'govt',       zoneName: 'Power & Utilities Sector' },
  { id: 'RAJ_BHAWAN', name: 'Raj Bhawan (Governor House)',lat: 20.2830, lon: 85.8285, zone: 'govt',       zoneName: 'Governor Estate & VIP Sector' },

  // ── Central Spine: Sachivalaya Marg & Rajpath ──
  { id: 'AG',         name: 'AG Square (State Capital)',  lat: 20.2745, lon: 85.8322, zone: 'govt',       zoneName: 'State Secretariat & AG' },
  { id: 'CAPITAL',    name: 'Capital Hospital Square',    lat: 20.2625, lon: 85.8280, zone: 'medical',    zoneName: 'Primary Government Hospital' },
  { id: 'MAST',       name: 'Master Canteen (Station)',   lat: 20.2678, lon: 85.8436, zone: 'transport',  zoneName: 'Bhubaneswar Central Railway Station' },
  { id: 'RAM',        name: 'Ram Mandir Square',          lat: 20.2800, lon: 85.8443, zone: 'commercial', zoneName: 'Janpath Commercial Center' },
  { id: 'RUPALI',     name: 'Rupali Square',              lat: 20.2893, lon: 85.8427, zone: 'commercial', zoneName: 'College Commercial Zone' },
  { id: 'SAHEED',     name: 'Saheed Nagar Square',        lat: 20.2910, lon: 85.8520, zone: 'commercial', zoneName: 'Commercial & Banking Zone' },

  // ── Eastern Secondary Arterials ──
  { id: 'VSS',        name: 'VSS Nagar Square',           lat: 20.3050, lon: 85.8550, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'SAINIK',     name: 'Sainik School Square',       lat: 20.3160, lon: 85.8360, zone: 'edu',        zoneName: 'Educational Sector' },
  { id: 'BOMIKHAL',   name: 'Bomikhal Flyover',           lat: 20.2820, lon: 85.8560, zone: 'commercial', zoneName: 'Cuttack Road Flyover' },
  { id: 'LAXMI',      name: 'Laxmisagar Square',          lat: 20.2720, lon: 85.8500, zone: 'residential',zoneName: 'Residential Sector' },
  { id: 'KALPANA',    name: 'Kalpana Square',             lat: 20.2546, lon: 85.8437, zone: 'heritage',   zoneName: 'Museum & Heritage Gateway' },
  { id: 'RAJMAHAL',   name: 'Rajmahal Square',            lat: 20.2638, lon: 85.8396, zone: 'commercial', zoneName: 'Rajmahal Commercial Center' },
  { id: 'SISHU',      name: 'Sishu Bhawan Square',        lat: 20.2585, lon: 85.8350, zone: 'medical',    zoneName: 'Pediatric Healthcare Hub' },

  // ── South & Old Town Heritage Network ──
  { id: 'RAVI',       name: 'Ravi Talkies Square',        lat: 20.2470, lon: 85.8415, zone: 'residential',zoneName: 'Puri Trunk Road' },
  { id: 'LINGARAJ',   name: 'Lingaraj Temple Square',     lat: 20.2382, lon: 85.8335, zone: 'heritage',   zoneName: 'Ancient Old Town Heritage' },
  { id: 'AIRPORT',    name: 'Airport Square',             lat: 20.2525, lon: 85.8178, zone: 'transport',  zoneName: 'Biju Patnaik Airport Terminal' },
  { id: 'POKHAR',     name: 'Pokhariput Square',          lat: 20.2460, lon: 85.8170, zone: 'residential',zoneName: 'Aerodrome Residential' },
  { id: 'SUNDARPADA', name: 'Sundarpada Square',          lat: 20.2330, lon: 85.8110, zone: 'residential',zoneName: 'Southern Infill' },
  { id: 'ITER',       name: 'ITER / Gandamunda Square',   lat: 20.2505, lon: 85.8050, zone: 'edu',        zoneName: 'ITER Engineering Campus' },
  { id: 'JAGAMARA',   name: 'Jagamara Square',            lat: 20.2530, lon: 85.7970, zone: 'residential',zoneName: 'Residential Corridor' },
  { id: 'GHATIKIA',   name: 'Ghatikia / Kalinga Studio',  lat: 20.2490, lon: 85.7830, zone: 'residential',zoneName: 'Film Studio Residential' },
];

export const BBSR_INTERSECTION_MAP = Object.fromEntries(
  BBSR_INTERSECTIONS.map(item => [item.id, item])
);

// ── Arterial Road Network Lines ─────────────────────────────────────────────
export const BBSR_ROAD_SEGMENTS = [
  // 1. NH-16 Main Arterial Highway Corridor
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

  // 3. Western Infill Arterials
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

  // 5. Sachivalaya Marg & Rajpath
  { from: 'ACHARYA',   to: 'AG',         type: 'sh', waypoints: [[20.2890, 85.8320]] },
  { from: 'AG',        to: 'CAPITAL',    type: 'sh', waypoints: [] },
  { from: 'AG',        to: 'MAST',       type: 'sh', waypoints: [] },

  // 6. Janpath Commercial Corridor
  { from: 'VANI',      to: 'RUPALI',     type: 'sh', waypoints: [] },
  { from: 'RUPALI',    to: 'RAM',        type: 'sh', waypoints: [] },
  { from: 'RAM',       to: 'MAST',       type: 'sh', waypoints: [] },
  { from: 'MAST',      to: 'RAJMAHAL',   type: 'sh', waypoints: [] },
  { from: 'RAJMAHAL',  to: 'SISHU',      type: 'sh', waypoints: [] },
  { from: 'SISHU',     to: 'AIRPORT',    type: 'sh', waypoints: [[20.2540, 85.8260]] },
  { from: 'CAPITAL',   to: 'SISHU',      type: 'city', waypoints: [] },

  // 7. Eastern Network
  { from: 'KALINGA',   to: 'SAINIK',     type: 'city', waypoints: [] },
  { from: 'SAINIK',    to: 'ACHARYA',    type: 'city', waypoints: [] },
  { from: 'SAINIK',    to: 'VSS',        type: 'city', waypoints: [] },
  { from: 'VSS',       to: 'MANCHES',    type: 'city', waypoints: [] },
  { from: 'VANI',      to: 'SAHEED',     type: 'city', waypoints: [] },
  { from: 'SAHEED',    to: 'BOMIKHAL',   type: 'city', waypoints: [] },
  { from: 'RUPALI',    to: 'SAHEED',     type: 'city', waypoints: [] },

  // 8. Cuttack-Puri Road
  { from: 'RASUL',     to: 'BOMIKHAL',   type: 'sh', waypoints: [[20.2880, 85.8600]] },
  { from: 'BOMIKHAL',  to: 'LAXMI',      type: 'sh', waypoints: [] },
  { from: 'LAXMI',     to: 'KALPANA',    type: 'sh', waypoints: [] },
  { from: 'KALPANA',   to: 'RAVI',       type: 'sh', waypoints: [[20.2510, 85.8425]] },
  { from: 'RAVI',      to: 'LINGARAJ',   type: 'sh', waypoints: [] },
  { from: 'RAJMAHAL',  to: 'KALPANA',    type: 'city', waypoints: [] },
  { from: 'RAM',       to: 'LAXMI',      type: 'city', waypoints: [] },

  // 9. South Arterial Ring
  { from: 'KHANDG',    to: 'GHATIKIA',   type: 'city', waypoints: [] },
  { from: 'GHATIKIA',  to: 'JAGAMARA',   type: 'city', waypoints: [] },
  { from: 'KHANDG',    to: 'JAGAMARA',   type: 'city', waypoints: [] },
  { from: 'JAGAMARA',  to: 'ITER',       type: 'city', waypoints: [] },
  { from: 'ITER',      to: 'POKHAR',     type: 'city', waypoints: [] },
  { from: 'POKHAR',    to: 'SUNDARPADA', type: 'city', waypoints: [] },
  { from: 'SUNDARPADA',to: 'LINGARAJ',   type: 'city', waypoints: [] },
  { from: 'POKHAR',    to: 'AIRPORT',    type: 'city', waypoints: [] },
  { from: 'AIRPORT',   to: 'LINGARAJ',   type: 'city', waypoints: [] },

  // 10. Outer Connector
  { from: 'CHANDAKA',  to: 'PATIA',      type: 'city', waypoints: [[20.3620, 85.8050]] },
];

export const ZONE_COLORS = {
  heritage:    '#dba53a',
  commercial:  '#e6926f',
  govt:        '#8fbf9d',
  medical:     '#e6926f',
  it:          '#8fbf9d',
  residential: '#b5b1a4',
  transport:   '#e0913a',
  edu:         '#e6926f',
};

// ── Live Emergency Vehicles Active on Network ───────────────────────────────
export const LIVE_EMERGENCY_FLEET = [
  {
    id: "AMB-108",
    callsign: "AMB-108 [Capital Trauma]",
    type: "ambulance",
    icon: "🚑",
    origin: "Capital Hospital Square",
    destination: "Airport Square",
    startNode: "CAPITAL",
    endNode: "AIRPORT",
    routeNodeIds: ["CAPITAL", "SISHU", "AIRPORT"],
    color: "#e5534b",
    speedKmh: 52,
    initialProgress: 24,
    status: "Active Emergency",
    statusBadge: "CRITICAL TRANSIT",
    driver: "Paramedic S. Mohapatra",
    priority: "Level-1 Critical",
    etaSec: 18,
  },
  {
    id: "AMB-102",
    callsign: "AMB-102 [Kalinga Cardiac]",
    type: "ambulance",
    icon: "🚑",
    origin: "Kalinga Hospital Square",
    destination: "Capital Hospital Square",
    startNode: "KALINGA",
    endNode: "CAPITAL",
    routeNodeIds: ["KALINGA", "CS_PUR", "XAVIER", "JAYADEV", "POWER", "RAJ_BHAWAN", "AG", "CAPITAL"],
    color: "#d97757",
    speedKmh: 56,
    initialProgress: 48,
    status: "En Route Hospital",
    statusBadge: "EN ROUTE",
    driver: "Paramedic R. Jena",
    priority: "Level-1 Critical",
    etaSec: 32,
  },
  {
    id: "AMB-104",
    callsign: "AMB-104 [AIIMS Trauma Unit]",
    type: "ambulance",
    icon: "🚑",
    origin: "Khandagiri Square",
    destination: "Capital Hospital Square",
    startNode: "KHANDG",
    endNode: "CAPITAL",
    routeNodeIds: ["KHANDG", "FIRE_STN", "DELTA", "SIRIPUR", "CAPITAL"],
    color: "#e6926f",
    speedKmh: 46,
    initialProgress: 65,
    status: "Patient Onboard",
    statusBadge: "ACTIVE TRANSIT",
    driver: "Paramedic P. Das",
    priority: "Level-2 Urgent",
    etaSec: 24,
  },
  {
    id: "AMB-106",
    callsign: "AMB-106 [KIIT Quick Response]",
    type: "ambulance",
    icon: "🚑",
    origin: "Infocity Square",
    destination: "Kalinga Hospital Square",
    startNode: "INFOCITY",
    endNode: "KALINGA",
    routeNodeIds: ["INFOCITY", "KIIT", "PATIA", "SAILASHREE", "DAMANA", "KALINGA"],
    color: "#63a375",
    speedKmh: 44,
    initialProgress: 15,
    status: "Patrol & Ready",
    statusBadge: "ACTIVE PATROL",
    driver: "Paramedic A. Pradhan",
    priority: "Standby Readiness",
    etaSec: 28,
  },
  {
    id: "FIRE-01",
    callsign: "FIRE-01 [Central Rescue]",
    type: "fire",
    icon: "🚒",
    origin: "Kalpana Square",
    destination: "Master Canteen (Station)",
    startNode: "KALPANA",
    endNode: "MAST",
    routeNodeIds: ["KALPANA", "RAJMAHAL", "MAST"],
    color: "#e0913a",
    speedKmh: 50,
    initialProgress: 72,
    status: "Incident Dispatch",
    statusBadge: "ALARM-1 DISPATCH",
    driver: "Commander M. Nayak",
    priority: "Structural Rescue",
    etaSec: 15,
  }
];

// Helper to assemble waypoint coordinates for an emergency route
export function getFleetRouteCoords(routeNodeIds) {
  const coords = [];
  routeNodeIds.forEach((nid) => {
    const junc = BBSR_INTERSECTION_MAP[nid];
    if (junc) {
      coords.push([junc.lat, junc.lon]);
    }
  });
  return coords;
}

// Build smooth high-density road geometry with intermediate segment waypoints
export function getFleetDetailedRoute(routeNodeIds) {
  const waypoints = [];
  for (let i = 0; i < routeNodeIds.length; i++) {
    const fromId = routeNodeIds[i];
    const fromJunc = BBSR_INTERSECTION_MAP[fromId];
    if (fromJunc) {
      waypoints.push([fromJunc.lat, fromJunc.lon]);
    }

    if (i < routeNodeIds.length - 1) {
      const toId = routeNodeIds[i + 1];
      const seg = BBSR_ROAD_SEGMENTS.find(
        (s) => (s.from === fromId && s.to === toId) || (s.from === toId && s.to === fromId)
      );
      if (seg && seg.waypoints && seg.waypoints.length > 0) {
        if (seg.from === fromId) {
          waypoints.push(...seg.waypoints);
        } else {
          waypoints.push(...[...seg.waypoints].reverse());
        }
      }
    }
  }

  if (waypoints.length < 2) {
    return { denseCoords: waypoints, distanceMeters: 500, distanceKm: "0.5" };
  }

  const denseCoords = [];
  let totalDistMeters = 0;

  for (let i = 0; i < waypoints.length - 1; i++) {
    const p1 = waypoints[i];
    const p2 = waypoints[i + 1];

    const R = 6371000;
    const dLat = ((p2[0] - p1[0]) * Math.PI) / 180;
    const dLon = ((p2[1] - p1[1]) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((p1[0] * Math.PI) / 180) *
        Math.cos((p2[0] * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const dist = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    totalDistMeters += dist;

    // Sub-segment density: ~20 meters per point for silky smooth movement
    const steps = Math.max(12, Math.floor(dist / 20));
    for (let s = 0; s <= steps; s++) {
      if (i > 0 && s === 0) continue;
      const t = s / steps;
      const lat = p1[0] + (p2[0] - p1[0]) * t;
      const lon = p1[1] + (p2[1] - p1[1]) * t;
      denseCoords.push([lat, lon]);
    }
  }

  return {
    denseCoords: denseCoords.length > 0 ? denseCoords : waypoints,
    distanceMeters: Math.round(totalDistMeters),
    distanceKm: (totalDistMeters / 1000).toFixed(1),
  };
}

