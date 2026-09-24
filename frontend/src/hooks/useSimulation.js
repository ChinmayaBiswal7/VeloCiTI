import { useState, useEffect, useCallback } from "react";
import { initIntersections } from "../data/intersections";

function runAI(intersections) {
  return intersections.map((int, idx) => {
    // Generate organic, fluctuating live traffic per lane
    // Real city traffic mostly flows with green/yellow and occasional peak red choke points
    const updatedLanes = int.lanes.map((lane, lIdx) => {
      if (lane.manualActive) return lane;
      // Lane vehicle count varies dynamically with some temporal wave
      const base = 25 + ((idx * 7 + lIdx * 11 + Math.floor(Date.now() / 3000)) % 45);
      const jitter = Math.floor(Math.random() * 26) - 10;
      const vehicleCount = Math.max(5, Math.min(110, base + jitter));
      const averageSpeed = Math.max(15, Math.min(60, Math.round(55 - (vehicleCount * 0.35) + (Math.random() * 8))));
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
        if (lane.vehicleCount > avgVC * 1.35) {
          // Only high load triggers red
          light = "red";
        } else if (lane.vehicleCount > avgVC * 0.95 || lane.vehicleCount === maxVC) {
          // Moderate load triggers yellow/phasing
          light = "yellow";
        } else {
          // Normal flow stays green
          light = "green";
        }
        return { ...lane, light };
      });
    }

    const totalVehicles = finalLanes.reduce((s, l) => s + l.vehicleCount, 0);
    const avgSpeed = Math.round(finalLanes.reduce((s, l) => s + l.averageSpeed, 0) / finalLanes.length);
    // Realistic congestion percentage (mostly 20% - 65%, rare spikes to 75%+)
    const congestionPct = Math.min(95, Math.max(12, Math.round((totalVehicles / (90 * 4)) * 100)));
    // Distribution: mostly low (green) & medium (yellow), rarely critical (red)
    const status = congestionPct > 72 ? "critical" : congestionPct > 40 ? "medium" : "low";

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
