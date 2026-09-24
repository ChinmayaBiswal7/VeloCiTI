import { useState, useEffect, useCallback } from "react";
import { initIntersections } from "../data/intersections";

function runAI(intersections) {
  const now = Date.now();
  return intersections.map((int, idx) => {
    // Generate organic, fluctuating live traffic per lane
    // Mostly smooth traffic with values oscillating in healthy 25% - 55% ranges
    const updatedLanes = int.lanes.map((lane, lIdx) => {
      if (lane.manualActive) return lane;
      // Realistic lane distribution
      const wave = Math.sin((now / 4000) + (idx * 0.7) + (lIdx * 1.2));
      const base = 18 + Math.floor(((idx * 13 + lIdx * 7) % 22));
      const jitter = Math.floor(wave * 12);
      const vehicleCount = Math.max(4, Math.min(55, base + jitter));
      const averageSpeed = Math.max(28, Math.min(58, Math.round(52 - (vehicleCount * 0.38))));
      return { ...lane, vehicleCount, averageSpeed };
    });

    const autoLanes = updatedLanes.filter(l => !l.manualActive);
    let finalLanes = updatedLanes;
    if (autoLanes.length > 0) {
      const maxVC = Math.max(...autoLanes.map(l => l.vehicleCount));
      const avgVC = autoLanes.reduce((s, l) => s + l.vehicleCount, 0) / autoLanes.length;
      finalLanes = updatedLanes.map(lane => {
        if (lane.manualActive) return lane;
        let light = "green";
        if (lane.vehicleCount > avgVC * 1.45) {
          light = "red";
        } else if (lane.vehicleCount > avgVC * 1.05 || lane.vehicleCount === maxVC) {
          light = "yellow";
        } else {
          light = "green";
        }
        return { ...lane, light };
      });
    }

    const totalVehicles = finalLanes.reduce((s, l) => s + l.vehicleCount, 0);
    const avgSpeed = Math.round(finalLanes.reduce((s, l) => s + l.averageSpeed, 0) / finalLanes.length);
    
    // User requirement: almost all nodes around 35% - 60% (mostly green and yellow), only few exceed it
    const dynamicOffset = ((idx * 17 + Math.floor(now / 3500)) % 100);
    let congestionPct;
    if (dynamicOffset > 93) {
      // Rare critical node (only ~6-7 nodes)
      congestionPct = 74 + (dynamicOffset % 14); // 74% - 87%
    } else if (dynamicOffset > 60) {
      // Moderate yellow nodes (approx 30% of nodes: 50% - 64%)
      congestionPct = 50 + (dynamicOffset % 15);
    } else {
      // Majority green smooth flow nodes (approx 60% of nodes: 28% - 48%)
      congestionPct = 28 + (dynamicOffset % 21);
    }

    // Status: mostly low (green) & medium (yellow), only rare critical (red)
    const status = congestionPct >= 72 ? "critical" : congestionPct >= 50 ? "medium" : "low";

    return { ...int, lanes: finalLanes, vehicleCount: totalVehicles, averageSpeed: avgSpeed, congestionPct, status };
  });
}

export function useSimulation() {
  const [intersections, setIntersections] = useState(() => runAI(initIntersections()));

  useEffect(() => {
    const id = setInterval(() => setIntersections(prev => runAI(prev)), 3000);
    return () => clearInterval(id);
  }, []);

  const updateLane = useCallback((intersectionId, direction, light) => {
    setIntersections(prev => prev.map(int => {
      if (int.id !== intersectionId) return int;
      return { ...int, lanes: int.lanes.map(l => l.direction===direction ? {...l, light, manualActive:true} : l) };
    }));
  }, []);

  const revertLane = useCallback((intersectionId, direction) => {
    setIntersections(prev => prev.map(int => {
      if (int.id !== intersectionId) return int;
      return { ...int, lanes: int.lanes.map(l => l.direction===direction ? {...l, light:"red", manualActive:false} : l) };
    }));
  }, []);

  const revertAll = useCallback((intersectionId) => {
    setIntersections(prev => prev.map(int => {
      if (int.id !== intersectionId) return int;
      return { ...int, lanes: int.lanes.map(l => ({...l, light:"red", manualActive:false})) };
    }));
  }, []);

  const stats = {
    avgCongestion: Math.round(intersections.reduce((s,i) => s+i.congestionPct,0) / intersections.length),
    avgSpeed: Math.round(intersections.reduce((s,i) => s+i.averageSpeed,0) / intersections.length),
    criticalCount: intersections.filter(i => i.status==="critical").length,
    mediumCount: intersections.filter(i => i.status==="medium").length,
    clearCount: intersections.filter(i => i.status==="low").length,
    totalNodes: intersections.length,
  };

  return { intersections, stats, updateLane, revertLane, revertAll };
}
