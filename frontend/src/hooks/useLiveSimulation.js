import { useState, useEffect, useCallback, useRef } from "react";
import { 
  fetchState, 
  transformState, 
  computeLiveStats, 
  startSimulation, 
  pauseSimulation, 
  resetSimulation,
  generateClientSimulatedState,
  setClientSimRunning,
  resetClientSim
} from "../services/cityFlowService";

const EMPTY_STATS = { avgCongestion: 0, avgSpeed: 0, criticalCount: 0, mediumCount: 0, clearCount: 0, totalNodes: 5 };

export function useLiveSimulation(active) {
  const [liveIntersections, setLiveIntersections] = useState([]);
  const [liveStats, setLiveStats] = useState(EMPTY_STATS);
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [rawState, setRawState] = useState(null);
  const intervalRef = useRef(null);
  const isFallbackRef = useRef(false);

  useEffect(() => {
    if (!active) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    async function poll() {
      try {
        const raw = await fetchState();
        const ints = transformState(raw);
        const stats = computeLiveStats(ints);
        setRawState(raw);
        setLiveIntersections(ints);
        setLiveStats(stats);
        setIsConnected(true);
        setIsRunning(!!raw.running);
        isFallbackRef.current = false;
      } catch {
        // When Python backend is offline or during static hosting, fall back to autonomous in-browser engine
        const fallbackRaw = generateClientSimulatedState();
        const ints = transformState(fallbackRaw);
        const stats = computeLiveStats(ints);
        setRawState(fallbackRaw);
        setLiveIntersections(ints);
        setLiveStats(stats);
        setIsConnected(false);
        setIsRunning(fallbackRaw.running);
        isFallbackRef.current = true;
      }
    }

    // Initial poll immediately
    poll();
    intervalRef.current = setInterval(poll, 500);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active]);

  const startSim = useCallback(async () => {
    setIsRunning(true);
    setClientSimRunning(true);
    try { 
      await startSimulation(); 
    } catch { }
  }, []);

  const pauseSim = useCallback(async () => {
    setIsRunning(false);
    setClientSimRunning(false);
    try { 
      await pauseSimulation(); 
    } catch { }
  }, []);

  const resetSim = useCallback(async () => {
    setIsRunning(true);
    setClientSimRunning(true);
    resetClientSim();
    try { 
      await resetSimulation(); 
    } catch { }
  }, []);

  return { liveIntersections, liveStats, isConnected, isRunning, rawState, startSim, pauseSim, resetSim };
}
