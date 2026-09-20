import { useState, useMemo } from "react";
import { BBSR_INTERSECTIONS, BBSR_INTERSECTION_MAP, ZONE_COLORS } from "../../../data/bbsrCityData";
import { findFastestEmergencyRoute, resolveJunction } from "../../../services/routingService";
import "./EmergencyCorridor.css";

export default function EmergencyCorridor({ intersections, corridor, onStartCorridor, onCancelCorridor }) {
  const [originId, setOriginId] = useState("CAPITAL");
  const [destId, setDestId] = useState("AIRPORT");
  const [vehicleType, setVehicleType] = useState("ambulance");

  // Build live density map from simulation data for AI congestion weighting
  const liveDensityMap = useMemo(() => {
    const map = {};
    if (Array.isArray(intersections)) {
      intersections.forEach(i => {
        map[i.id] = i;
        if (i.name) map[i.name] = i;
      });
    }
    return map;
  }, [intersections]);

  // Dynamically calculate the AI Fastest Path between origin and destination taking live traffic into account
  const routeData = useMemo(() => {
    return findFastestEmergencyRoute(originId, destId, liveDensityMap);
  }, [originId, destId, liveDensityMap]);

  const isActive = corridor?.isActive;
  const progress = corridor?.progress || 0;

  const handleSwap = () => {
    if (isActive) return;
    setOriginId(destId);
    setDestId(originId);
  };

  const handleActivate = () => {
    onStartCorridor({
      origin: routeData.startJunc.name,
      originId: routeData.startJunc.id,
      destination: routeData.endJunc.name,
      destinationId: routeData.endJunc.id,
      vehicleType,
      nodes: routeData.nodeIds,
      nodeNames: routeData.nodeNames,
      roadCoords: routeData.roadCoords,
      distanceKm: routeData.distanceKm,
      distanceMeters: routeData.distanceMeters,
      estimatedSeconds: routeData.estimatedSeconds,
      savedMinutes: routeData.savedMinutes,
      signalCount: routeData.signalCount,
    });
  };

  const activeNodes = isActive && corridor?.nodes?.length > 0 ? corridor.nodes : routeData.nodeIds;
  const currentActiveIndex = Math.min(
    activeNodes.length - 1,
    Math.floor((progress / 100) * activeNodes.length)
  );

  return (
    <div className="emergency-view">
      {/* Header Banner */}
      <div className="em-header-banner">
        <div className="em-title-box">
          <div className="em-icon-badge">
            <i className={`fas ${vehicleType === "ambulance" ? "fa-ambulance" : vehicleType === "fire" ? "fa-fire-extinguisher" : "fa-shield-alt"}`} />
          </div>
          <div>
            <div className="em-title">VeloCiTI Dynamic Green Corridor</div>
            <div className="em-sub">Autonomous AI Signal Pre-emption & Smartphone-Based Fast Route Engine</div>
          </div>
        </div>
        {isActive ? (
          <div className="corridor-live-badge">
            <i className="fas fa-satellite-dish" /> CORRIDOR ACTIVE — GREEN WAVE OVERRIDE LIVE
          </div>
        ) : (
          <div className="corridor-standby-badge">
            <i className="fas fa-shield-virus" /> AI ROUTING ENGINE READY
          </div>
        )}
      </div>

      <div className="em-grid">
        {/* Left Column: Corridor Parameters & Route Selection */}
        <div className="em-card">
          <div className="em-card-title">
            <i className="fas fa-sliders-h" /> Corridor Parameters & Dispatch
          </div>

          {/* Emergency Vehicle Selector */}
          <div className="em-form-group">
            <span className="em-label">Emergency Unit Category</span>
            <div className="em-type-grid">
              <button
                className={`em-type-btn ${vehicleType === "ambulance" ? "active" : ""}`}
                onClick={() => setVehicleType("ambulance")}
                disabled={isActive}
              >
                <i className="fas fa-ambulance" style={{ fontSize: "1.1rem" }} />
                <span>Ambulance (108)</span>
              </button>
              <button
                className={`em-type-btn ${vehicleType === "fire" ? "active" : ""}`}
                onClick={() => setVehicleType("fire")}
                disabled={isActive}
              >
                <i className="fas fa-fire-truck" style={{ fontSize: "1.1rem" }} />
                <span>Fire Rescue</span>
              </button>
              <button
                className={`em-type-btn ${vehicleType === "vip" ? "active" : ""}`}
                onClick={() => setVehicleType("vip")}
                disabled={isActive}
              >
                <i className="fas fa-shield-alt" style={{ fontSize: "1.1rem" }} />
                <span>VIP Escort</span>
              </button>
            </div>
          </div>

          {/* Origin Dropdown */}
          <div className="em-form-group">
            <div className="em-label-row">
              <span className="em-label">Origin (Dispatch Station / Current Location)</span>
              <span className="em-badge-phone"><i className="fas fa-mobile-alt" /> Driver GPS Link</span>
            </div>
            <select
              className="em-select"
              value={originId}
              onChange={(e) => setOriginId(e.target.value)}
              disabled={isActive}
            >
              <optgroup label="🏥 Major Medical & Healthcare Hubs">
                {BBSR_INTERSECTIONS.filter(j => j.zone === 'medical' || j.id === 'CAPITAL' || j.id === 'KALINGA' || j.id === 'SISHU').map(j => (
                  <option key={j.id} value={j.id}>{j.name} ({j.zoneName})</option>
                ))}
              </optgroup>
              <optgroup label="✈️ Transit & Transportation Hubs">
                {BBSR_INTERSECTIONS.filter(j => j.zone === 'transport' || j.id === 'AIRPORT' || j.id === 'MAST' || j.id === 'BARAMN').map(j => (
                  <option key={j.id} value={j.id}>{j.name}</option>
                ))}
              </optgroup>
              <optgroup label="🏙️ All City Intersections (46 BBSR Nodes)">
                {BBSR_INTERSECTIONS.map(j => (
                  <option key={j.id} value={j.id}>{j.name}</option>
                ))}
              </optgroup>
            </select>
          </div>

          {/* Swap Button */}
          <div className="em-swap-row">
            <button
              className="em-swap-btn"
              onClick={handleSwap}
              disabled={isActive}
              title="Reverse Origin & Destination"
            >
              <i className="fas fa-arrows-alt-v" /> Swap Direction
            </button>
          </div>

          {/* Destination Dropdown */}
          <div className="em-form-group">
            <span className="em-label">Destination (Emergency Facility / Hospital)</span>
            <select
              className="em-select"
              value={destId}
              onChange={(e) => setDestId(e.target.value)}
              disabled={isActive}
            >
              <optgroup label="🏥 Major Medical & Healthcare Hubs">
                {BBSR_INTERSECTIONS.filter(j => j.zone === 'medical' || j.id === 'CAPITAL' || j.id === 'KALINGA' || j.id === 'SISHU').map(j => (
                  <option key={j.id} value={j.id}>{j.name} ({j.zoneName})</option>
                ))}
              </optgroup>
              <optgroup label="✈️ Transit & Commercial">
                {BBSR_INTERSECTIONS.filter(j => j.zone === 'transport' || j.zone === 'commercial').map(j => (
                  <option key={j.id} value={j.id}>{j.name}</option>
                ))}
              </optgroup>
              <optgroup label="🏙️ All City Intersections (46 BBSR Nodes)">
                {BBSR_INTERSECTIONS.map(j => (
                  <option key={j.id} value={j.id}>{j.name}</option>
                ))}
              </optgroup>
            </select>
          </div>

          {/* AI Fastest Route Preview Summary Card */}
          <div className="ai-route-preview-card">
            <div className="arp-header">
              <div className="arp-title">
                <i className="fas fa-bolt" style={{ color: "#dba53a" }} />
                <span>AI Dynamic Fastest Path (Calculated Live)</span>
              </div>
              <span className="arp-badge-optimal">OPTIMAL ROUTE</span>
            </div>

            <div className="arp-stats-grid">
              <div className="arp-stat">
                <span className="arp-label">Route Distance</span>
                <strong className="arp-val">{routeData.distanceKm} km</strong>
              </div>
              <div className="arp-stat">
                <span className="arp-label">Priority ETA</span>
                <strong className="arp-val text-green">{routeData.estimatedDurationText}</strong>
              </div>
              <div className="arp-stat">
                <span className="arp-label">Time Saved vs Traffic</span>
                <strong className="arp-val text-blue">~{routeData.savedMinutes} min saved</strong>
              </div>
              <div className="arp-stat">
                <span className="arp-label">Signals Preempted</span>
                <strong className="arp-val text-amber">{routeData.signalCount} Junctions</strong>
              </div>
            </div>

            <div className="arp-gps-tag">
              <i className="fas fa-crosshairs" />
              <span>Driver Smartphone GNSS Tracking: Connected (±3.2m accuracy, no extra hardware needed)</span>
            </div>
          </div>

          {/* Action Trigger Button */}
          <div style={{ marginTop: "auto", paddingTop: "8px" }}>
            {!isActive ? (
              <button className="btn-activate-corridor" onClick={handleActivate}>
                <i className="fas fa-play" /> ACTIVATE GREEN CORRIDOR & DISPATCH
              </button>
            ) : (
              <button className="btn-deactivate-corridor" onClick={onCancelCorridor}>
                <i className="fas fa-power-off" /> Stand Down (Deactivate Corridor)
              </button>
            )}
          </div>
        </div>

        {/* Right Column: Route Steps & Live Preemption Progress */}
        <div className="em-card">
          <div className="em-card-title">
            <i className="fas fa-route" /> Corridor Signal Synchronization & Live Progress
          </div>

          <div className="corridor-status-box">
            <div className="corridor-status-header">
              <div>
                <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text)" }}>
                  {routeData.startJunc.name} &rarr; {routeData.endJunc.name}
                </span>
                <div style={{ fontSize: "0.68rem", color: "var(--text3)", marginTop: "2px" }}>
                  Autonomous Green Wave clearing {routeData.signalCount} consecutive intersections
                </div>
              </div>
              <span style={{ fontSize: "0.75rem", color: isActive ? "var(--green)" : "var(--text3)", fontWeight: 700 }}>
                {isActive ? `${progress}% In Transit` : "Standby (Ready)"}
              </span>
            </div>

            <div className="corridor-progress-track">
              <div
                className="corridor-progress-bar"
                style={{
                  width: `${progress}%`,
                  background: isActive ? "#d97757" : "var(--surface2)",
                  boxShadow: isActive ? "0 0 12px rgba(99,163,117, 0.6)" : "none",
                }}
              />
            </div>
          </div>

          {/* Checkpoints / Junctions along the path */}
          <div className="route-steps-scroll">
            {routeData.nodeIds.map((nodeId, index) => {
              const junc = BBSR_INTERSECTION_MAP[nodeId] || resolveJunction(nodeId);
              const isCleared = isActive && index <= currentActiveIndex;
              const isCurrent = isActive && index === currentActiveIndex;

              return (
                <div
                  key={nodeId}
                  className={`route-step-row ${isCleared ? "active-clearing" : ""} ${isCurrent ? "current-node" : ""}`}
                >
                  <div className="step-number">
                    {isCleared ? <i className="fas fa-check" /> : index + 1}
                  </div>
                  <div className="step-info">
                    <div className="step-names">
                      <span className="step-name">{junc.name}</span>
                      <span className="step-zone" style={{ color: ZONE_COLORS[junc.zone] || "var(--text3)" }}>
                        {junc.zoneName || (junc.zone && junc.zone.toUpperCase()) || "URBAN ROAD"}
                      </span>
                    </div>
                    <div className="step-signal">
                      <span className={`signal-light-pill ${isActive ? (isCleared ? "green" : "preempt") : "auto"}`}>
                        <i className="fas fa-traffic-light" />
                        {isActive
                          ? (isCleared ? "CLEARED / GREEN" : "PREEMPTING GREEN")
                          : "AI ADAPTIVE"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Prototype Guidance Note */}
          <div className="prototype-guidance-box">
            <i className="fas fa-info-circle" style={{ color: "var(--blue)" }} />
            <span>
              <strong>Ambulance Navigation Prototype:</strong> When activated, this corridor uses dynamic Dijkstra shortest-path calculations against live Bhubaneswar traffic density. Signals along the path are pre-empted in real-time.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
