export const INTERSECTION_COORDS = {
  "Jaydev Vihar": [20.3015, 85.8239],
  "Vani Vihar": [20.3032, 85.8360],
  "Master Canteen": [20.2678, 85.8436],
  "Acharya Vihar": [20.3005, 85.8300],
  "Rasulgarh": [20.2917, 85.8647],
  "Kalinga Hospital": [20.3168, 85.8198],
  "Patia Square": [20.3541, 85.8176],
  "Dhauli Square": [20.2030, 85.8568],
  "Sishupalgarh": [20.2443, 85.8576],
  "Khandagiri": [20.2602, 85.7877],
  "Chandrasekharpur": [20.3298, 85.8188],
  "Infocity Square": [20.3582, 85.8115],
  "KIIT Square": [20.3524, 85.8174],
  "Nandankanan": [20.3953, 85.8258],
  "Damana": [20.3408, 85.8195],
  "Palasuni": [20.3012, 85.8745],
  "Bomikhal": [20.2842, 85.8510],
  "Laxmi Sagar": [20.2748, 85.8525],
  "Saheed Nagar": [20.2890, 85.8438],
  "Cuttack Road": [20.2642, 85.8515],
  "Gajapati Nagar": [20.3075, 85.8270],
  "Nayapalli": [20.2952, 85.8162],
  "Bhubaneswar Airport": [20.2520, 85.8178],
  "Capital Hospital": [20.2690, 85.8285],
  "Madhusudan Nagar": [20.2895, 85.8340],
  "Forest Park": [20.2570, 85.8335],
  "Baramunda": [20.2778, 85.7950],
  "Sikharchandi": [20.3645, 85.8210],
  "Mancheswar": [20.3205, 85.8530],
  "Patrapada": [20.2465, 85.7650]
};

export const INTERSECTION_NAMES = Object.keys(INTERSECTION_COORDS);

function makeLanes() {
  return [
    { direction:"North", vehicleCount:0, averageSpeed:0, light:"green", manualActive:false },
    { direction:"East",  vehicleCount:0, averageSpeed:0, light:"red",   manualActive:false },
    { direction:"South", vehicleCount:0, averageSpeed:0, light:"green", manualActive:false },
    { direction:"West",  vehicleCount:0, averageSpeed:0, light:"red",   manualActive:false },
  ];
}

export function initIntersections() {
  return Array.from({ length: 100 }, (_, i) => {
    const name = INTERSECTION_NAMES[i % INTERSECTION_NAMES.length];
    const coords = INTERSECTION_COORDS[name] || [20.2961, 85.8245];
    return {
      id: `${name}-${i+1}`,
      name,
      gridIndex: i,
      status: "low",
      vehicleCount: 0,
      averageSpeed: 0,
      congestionPct: 0,
      coords,
      lanes: makeLanes()
    };
  });
}
