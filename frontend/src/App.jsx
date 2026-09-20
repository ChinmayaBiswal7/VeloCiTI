import { useState, useCallback, useEffect, useMemo } from "react";
import { useSimulation } from "./hooks/useSimulation";
import { useLiveSimulation } from "./hooks/useLiveSimulation";
import { useClock } from "./hooks/useClock";
import Sidebar from "./components/Sidebar/Sidebar";
import TopBar from "./components/TopBar/TopBar";
import Overview from "./components/views/Overview/Overview";
import DetailView from "./components/views/DetailView/DetailView";
import MapView from "./components/views/MapView/MapView";
import EmergencyCorridor from "./components/views/Emergency/EmergencyCorridor";
import Analytics from "./components/views/Analytics/Analytics";
import Incidents from "./components/views/Incidents/Incidents";
import LiveGrid from "./components/views/LiveGrid/LiveGrid";
import CityFlowView from "./components/views/CityFlow/CityFlowView";
import LiveWebcamView from "./components/views/LiveWebcam/LiveWebcamView";
import LoadingScreen from "./components/common/LoadingScreen/LoadingScreen";
import LoginScreen from "./components/common/Login/LoginScreen";
import PortalSelector from "./components/PortalSelector/PortalSelector";
import VehicleTrackingView from "./components/views/VehicleTracking/VehicleTrackingView";
import { getCurrentUser, logout as authLogout } from "./services/authService";
import { BBSR_INTERSECTIONS, BBSR_INTERSECTION_MAP } from "./data/bbsrCityData";

import {
  broadcastCorridorToFirebase,
  subscribeToCorridor,
  syncSignalOverrideToFirebase,
  revertSignalOverrideInFirebase,
  subscribeToSignalOverrides,
} from "./services/firebase";
import "./App.css";

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => getCurrentUser());
  const [activePortal, setActivePortal] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("portal");
    if (p === "traffic" || p === "tracking") return p;
    return null; // Show PortalSelector by default after login
  });
  const [view, setView] = useState("overview");

  const [selectedId, setSelectedId] = useState(null);
  const [returnView, setReturnView] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [corridor, setCorridor] = useState({
    isActive: false,
    origin: "Capital Hospital",
    destination: "Bhubaneswar Airport",
    vehicleType: "ambulance",
    nodes: [],
    progress: 0,
  });

  const { intersections, stats, updateLane, revertLane, revertAll } = useSimulation();
  const { time, date } = useClock();

  // Live simulation hook — polls CityFlow backend when live grid or cityflow view is active
  const liveActive = view === "livegrid" || view === "cityflow" || view === "livedetail";
  const {
    liveIntersections, liveStats, isConnected, isRunning, rawState,
    startSim, pauseSim, resetSim
  } = useLiveSimulation(liveActive);

  // Smooth transit timer when corridor is active (~25s transit across city with 50ms silky smooth updates)
  useEffect(() => {
    let timer = null;
    if (corridor.isActive) {
      timer = setInterval(() => {
        setCorridor(prev => {
          if (!prev.isActive) return prev;
          if (prev.progress >= 100) {
            clearInterval(timer);
            // Keep at 100% arrived state for 30 seconds or until user manually dismisses
            setTimeout(() => {
              setCorridor(c => (c.progress >= 100 ? { ...c, isActive: false, progress: 0 } : c));
            }, 30000);
            return { ...prev, progress: 100 };
          }
          return { ...prev, progress: Math.min(100, +(prev.progress + 0.2).toFixed(2)) };
        });
      }, 50);
    }
    return () => clearInterval(timer);
  }, [corridor.isActive]);

  // Robust intersection resolution so inspecting from Map or Matrix NEVER renders blank
  const selectedIntersection = useMemo(() => {
    if (!selectedId) return null;

    // 1. Direct ID match in matrix intersections
    let matched = intersections.find(i => i.id === selectedId);
    if (matched) return matched;

    // 2. Direct ID match in liveIntersections
    matched = liveIntersections.find(i => i.id === selectedId);
    if (matched) return matched;

    // 3. Name match in intersections (case-insensitive)
    matched = intersections.find(i => i.name.toLowerCase() === selectedId.toLowerCase());
    if (matched) return matched;

    // 4. Loose substring match
    const clean = selectedId.toLowerCase().replace(/[-_]/g, " ").trim();
    matched = intersections.find(i => {
      const n = i.name.toLowerCase();
      return n.includes(clean) || clean.includes(n) || clean.split(" ")[0] === n.split(" ")[0];
    });
    if (matched) return matched;

    // 5. Look up in BBSR map data
    const bbsrNode = BBSR_INTERSECTION_MAP[selectedId] || BBSR_INTERSECTIONS.find(j => j.id === selectedId || j.name.toLowerCase().includes(clean));
    if (bbsrNode) {
      const bName = bbsrNode.name.toLowerCase();
      matched = intersections.find(i => {
        const n = i.name.toLowerCase();
        return bName.includes(n) || n.includes(bName) || bName.split(" ")[0] === n.split(" ")[0];
      });
      if (matched) return { ...matched, name: bbsrNode.name, coords: [bbsrNode.lat, bbsrNode.lon] };

      // Synthesize full 4-lane node so DetailView is 100% interactive
      const status = bbsrNode.zone === "heritage" ? "critical" : "medium";
      const vehicleCount = status === "critical" ? 220 : 135;
      const averageSpeed = status === "critical" ? 22 : 42;
      const congestionPct = status === "critical" ? 82 : 48;

      return {
        id: bbsrNode.id,
        name: bbsrNode.name,
        gridIndex: 0,
        status,
        vehicleCount,
        averageSpeed,
        congestionPct,
        coords: [bbsrNode.lat, bbsrNode.lon],
        lanes: [
          { direction: "North", vehicleCount: Math.round(vehicleCount * 0.28), averageSpeed, light: status === "critical" ? "red" : "green", manualActive: false },
          { direction: "East",  vehicleCount: Math.round(vehicleCount * 0.32), averageSpeed: Math.max(12, averageSpeed - 4), light: status === "critical" ? "red" : "green", manualActive: false },
          { direction: "South", vehicleCount: Math.round(vehicleCount * 0.22), averageSpeed: averageSpeed + 3, light: status === "medium" ? "yellow" : "red", manualActive: false },
          { direction: "West",  vehicleCount: Math.round(vehicleCount * 0.18), averageSpeed: averageSpeed + 5, light: "red", manualActive: false },
        ]
      };
    }

    return intersections[0] || null;
  }, [intersections, liveIntersections, selectedId]);

  const selectedLiveIntersection = liveIntersections.find(i => i.id === selectedId) || null;

  function handleCellClick(int, source = "overview") {
    if (!int) return;
    setReturnView(source);
    const targetId = typeof int === "string" ? int : (int.id || int.name);
    setSelectedId(targetId);
    setView("detail");
  }

  function handleLiveCellClick(int) {
    if (!int) return;
    setReturnView("livegrid");
    setSelectedId(int.id);
    setView("livedetail");
  }

  function handleBack() {
    setView(returnView || "overview");
    setSelectedId(null);
  }

  function handleLiveBack() {
    setView("livegrid");
    setSelectedId(null);
  }

  function handleNav(v) {
    setView(v);
    if (v !== "detail" && v !== "livedetail") {
      setSelectedId(null);
    }
  }

  // Subscribe to real-time Green Corridor broadcasts from Firebase
  useEffect(() => {
    // Clear any stale corridor state on initial mount so user is never greeted by an auto-running corridor
    broadcastCorridorToFirebase({ isActive: false, progress: 0, updatedAt: Date.now() });

    const unsub = subscribeToCorridor((remoteCorridor) => {
      if (remoteCorridor && typeof remoteCorridor === "object") {
        const isFresh = remoteCorridor.updatedAt && (Date.now() - remoteCorridor.updatedAt < 10000);
        if (remoteCorridor.isActive && isFresh && (remoteCorridor.progress || 0) < 100) {
          setCorridor(prev => ({
            ...prev,
            ...remoteCorridor,
          }));
        } else if (remoteCorridor.isActive === false) {
          setCorridor(prev => ({ ...prev, isActive: false, progress: 0 }));
        }
      }
    });
    return () => unsub?.();
  }, []);

  // Subscribe to real-time manual signal overrides from Firebase
  useEffect(() => {
    const unsub = subscribeToSignalOverrides((signalsMap) => {
      if (signalsMap && typeof signalsMap === "object") {
        Object.entries(signalsMap).forEach(([intId, directions]) => {
          if (typeof directions === "object") {
            Object.entries(directions).forEach(([dir, data]) => {
              if (data && data.manualActive && data.light) {
                updateLane(intId, dir, data.light);
              }
            });
          }
        });
      }
    });
    return () => unsub?.();
  }, [updateLane]);

  const handleStartCorridor = useCallback((config) => {
    const fullConfig = {
      ...config,
      isActive: true,
      progress: 0,
    };
    setCorridor(fullConfig);
    broadcastCorridorToFirebase(fullConfig);
    setView("map");
  }, []);

  const handleCancelCorridor = useCallback(() => {
    setCorridor(prev => ({ ...prev, isActive: false, progress: 0 }));
    broadcastCorridorToFirebase({ isActive: false, progress: 0 });
  }, []);

  const handleUpdateLaneWithFirebase = useCallback((intId, dir, light) => {
    updateLane(intId, dir, light);
    syncSignalOverrideToFirebase(intId, dir, light);
  }, [updateLane]);

  const handleRevertLaneWithFirebase = useCallback((intId, dir) => {
    revertLane(intId, dir);
    revertSignalOverrideInFirebase(intId, dir);
  }, [revertLane]);

  const handleLoadingComplete = useCallback(() => {
    setLoading(false);
  }, []);

  if (loading) return <LoadingScreen onComplete={handleLoadingComplete} />;

  if (!currentUser) {
    return <LoginScreen onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  function handleLogout() {
    authLogout();
    setCurrentUser(null);
    setActivePortal(null);
  }

  // If no portal selected yet, show Command Hub Portal Selection screen
  if (!activePortal) {
    return (
      <PortalSelector
        currentUser={currentUser}
        onSelectPortal={(portal) => setActivePortal(portal)}
        onLogout={handleLogout}
      />
    );
  }

  // If Vehicle Tracking selected, render dedicated Citywide ANPR & Journey tracking view
  if (activePortal === "tracking") {
    return (
      <VehicleTrackingView
        currentUser={currentUser}
        onSwitchToTraffic={() => setActivePortal("traffic")}
        onOpenHub={() => setActivePortal(null)}
        onLogout={handleLogout}
      />
    );
  }

  // Use live stats for sidebar when on live views
  const activeStats = (view === "livegrid" || view === "livedetail") ? liveStats : stats;

  return (
    <div className="app">
      <Sidebar currentView={view} onNav={handleNav} time={time} date={date} stats={activeStats} />
      <div className="app-main">
        <TopBar 
          currentView={view} 
          intersection={view === "livedetail" ? (selectedLiveIntersection || selectedIntersection) : selectedIntersection} 
          stats={activeStats} 
          currentUser={currentUser}
          onLogout={handleLogout}
          onSwitchToTracking={() => setActivePortal("tracking")}
          onOpenHub={() => setActivePortal(null)}
        />

        <div className="app-content">
          {view === "overview" && <Overview intersections={intersections} stats={stats} onCellClick={(int) => handleCellClick(int, "overview")} />}
          {view === "map" && (
            <MapView
              intersections={intersections}
              onSelectIntersection={(int) => handleCellClick(int, "map")}
              corridor={corridor}
              onCancelCorridor={handleCancelCorridor}
            />
          )}
          {view === "emergency" && (
            <EmergencyCorridor
              intersections={intersections}
              corridor={corridor}
              onStartCorridor={handleStartCorridor}
              onCancelCorridor={handleCancelCorridor}
            />
          )}
          {view === "detail" && (
            <DetailView
              intersection={selectedIntersection || intersections[0]}
              onBack={handleBack}
              backLabel={returnView === "map" ? "Back to Live Map" : "Back to Matrix"}
              onUpdateLane={handleUpdateLaneWithFirebase}
              onRevertLane={handleRevertLaneWithFirebase}
              onRevertAll={revertAll}
            />
          )}
          {view === "livedetail" && (
            <DetailView
              intersection={selectedLiveIntersection || selectedIntersection || liveIntersections[0]}
              onBack={handleLiveBack}
              backLabel="Back to Live Grid"
              onUpdateLane={() => {}}
              onRevertLane={() => {}}
              onRevertAll={() => {}}
            />
          )}
          {view === "analytics" && <Analytics intersections={intersections} />}
          {view === "incidents" && <Incidents intersections={intersections} />}
          {view === "livegrid" && (
            <LiveGrid
              intersections={liveIntersections}
              stats={liveStats}
              isConnected={isConnected}
              isRunning={isRunning}
              rawState={rawState}
              onCellClick={handleLiveCellClick}
              onStart={startSim}
              onPause={pauseSim}
              onReset={resetSim}
            />
          )}
          {view === "cityflow" && (
            <CityFlowView 
              isConnected={isConnected} 
              rawState={rawState}
              liveIntersections={liveIntersections}
              isRunning={isRunning}
              onStart={startSim}
              onPause={pauseSim}
              onReset={resetSim}
            />
          )}
          {view === "webcam" && <LiveWebcamView />}
        </div>
      </div>
    </div>
  );
}
