import { useState, useEffect, useCallback } from "react";
import { initIntersections } from "../data/intersections";

function runAI(intersections) {
  return intersections.map(int => {
    const updatedLanes = int.lanes.map(lane => {
      if (lane.manualActive) return lane;
      return { ...lane, vehicleCount: Math.floor(Math.random()*115)+5, averageSpeed: Math.floor(Math.random()*58)+10 };
    });
    const autoLanes = updatedLanes.filter(l => !l.manualActive);
    let finalLanes = updatedLanes;
    if (autoLanes.length > 0) {
      const maxVC = Math.max(...autoLanes.map(l => l.vehicleCount));
      const avgVC = autoLanes.reduce((s,l) => s+l.vehicleCount,0) / autoLanes.length;
      finalLanes = updatedLanes.map(lane => {
        if (lane.manualActive) return lane;
        let light = "red";
        if (lane.vehicleCount === maxVC) light = "green";
        else if (lane.vehicleCount > avgVC * 0.7) light = "yellow";
        return { ...lane, light };
      });
    }
    const totalVehicles = finalLanes.reduce((s,l) => s+l.vehicleCount, 0);
    const avgSpeed = Math.round(finalLanes.reduce((s,l) => s+l.averageSpeed,0) / finalLanes.length);
    const congestionPct = Math.min(100, Math.round((totalVehicles/(120*4))*100*2.5));
    const status = totalVehicles > 280 ? "critical" : totalVehicles > 130 ? "medium" : "low";
    return { ...int, lanes:finalLanes, vehicleCount:totalVehicles, averageSpeed:avgSpeed, congestionPct, status };
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
