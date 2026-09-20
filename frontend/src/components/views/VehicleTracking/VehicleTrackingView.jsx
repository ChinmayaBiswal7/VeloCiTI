import React, { useState, useEffect } from "react";
import "./VehicleTrackingView.css";

export default function VehicleTrackingView({ onSwitchToTraffic, onLogout }) {
  const [activeTab, setActiveTab] = useState("map"); // "map" | "firebase"
  const [targetPlate, setTargetPlate] = useState("");
  const [firebaseData, setFirebaseData] = useState({
    status: null,
    plates: [],
    loading: false,
    lastRefreshed: null
  });

  function handleTrackPlate(plate) {
    if (!plate) return;
    setTargetPlate(plate);
    setActiveTab("map");
  }

  // Fetch live Central Firebase data when the Firebase tab is selected
  useEffect(() => {
    if (activeTab === "firebase") {
      fetchFirebaseData();
    }
  }, [activeTab]);

  async function fetchFirebaseData() {
    setFirebaseData(prev => ({ ...prev, loading: true }));
    try {
      const [statRes, platesRes] = await Promise.all([
        fetch("/api/firebase/status").then(r => r.json()).catch(() => null),
        fetch("/api/firebase/plates?limit=25").then(r => r.json()).catch(() => null)
      ]);
      setFirebaseData({
        status: statRes,
        plates: platesRes?.plates || [],
        loading: false,
        lastRefreshed: new Date().toLocaleTimeString()
      });
    } catch {
      setFirebaseData(prev => ({ ...prev, loading: false }));
    }
  }

  async function handleSeedCloud() {
    try {
      await fetch("/api/firebase/seed", { method: "POST" });
      setTimeout(fetchFirebaseData, 1200);
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="vt-container">
      {/* Top Header Navigation */}
      <header className="vt-topbar">
        <div className="vt-left">
          <div className="vt-logo-icon">
            <i className="fas fa-satellite-dish" />
          </div>
          <div>
            <div className="vt-title-row">
              <h1 className="vt-title">Citywide ANPR Vehicle Intelligence</h1>
            </div>
            <p className="vt-sub">Bhubaneswar Multi-Camera Cross-Junction Journey Reconstruction & Re-ID</p>
          </div>
        </div>

        {/* View Tabs */}
        <div className="vt-tabs">
          <button
            className={`vt-tab-btn ${activeTab === "map" ? "active" : ""}`}
            onClick={() => setActiveTab("map")}
          >
            <i className="fas fa-map-location-dot" />
            <span>Tracking Map</span>
          </button>
          <button
            className={`vt-tab-btn ${activeTab === "firebase" ? "active" : ""}`}
            onClick={() => setActiveTab("firebase")}
          >
            <i className="fas fa-database" />
            <span>Central Cloud DB</span>
          </button>
        </div>

        {/* Action Switchers */}
        <div className="vt-actions">
          {onSwitchToTraffic && (
            <button className="vt-btn vt-traffic-btn" onClick={onSwitchToTraffic} title="Direct Switch to Urban Traffic Management">
              <i className="fas fa-traffic-light" />
              <span>Traffic Command</span>
            </button>
          )}

          {onLogout && (
            <button className="vt-btn vt-logout-btn" onClick={onLogout} title="Sign Out">
              <i className="fas fa-arrow-right-from-bracket" />
            </button>
          )}
        </div>
      </header>


      {/* Tab Viewports */}
      <div className="vt-viewport">
        {activeTab === "map" && (
          <iframe
            key={targetPlate}
            src={`/vehicle-tracking/dashboard.html${targetPlate ? `?track=${encodeURIComponent(targetPlate)}` : ''}`}
            title="Citywide ANPR Vehicle Tracking Dashboard"
            className="vt-iframe"
          />
        )}

        {activeTab === "firebase" && (
          <div className="vt-firebase-view">
            {/* Architecture Banner */}
            <div className="vt-fb-card vt-arch-card">
              <div className="vt-arch-head">
                <div>
                  <h2 className="vt-fb-h2">
                    <i className="fas fa-server text-sky" /> Central Cloud Database Innovation
                  </h2>
                  <p className="vt-fb-p">
                    Traditional traffic systems use siloed, disconnected databases at individual junctions with no cross-camera tracking.
                    Our architecture streams every camera sighting from across all 46 city junctions into a <strong>single central Firebase Firestore database</strong>.
                    Sightings are aggregated into a dedicated Number Plate collection, sorted chronologically to recreate complete citywide vehicle routes.
                  </p>
                </div>
                <button className="vt-btn vt-seed-btn" onClick={handleSeedCloud} disabled={firebaseData.loading}>
                  <i className="fas fa-arrows-rotate" />
                  <span>Sync Cloud Journeys</span>
                </button>
              </div>

              <div className="vt-telemetry-strip">
                <div className="vt-tele-item">
                  <span className="vt-tele-lbl">PROJECT ID</span>
                  <span className="vt-tele-val text-sky">VeloCiTI</span>
                </div>
                <div className="vt-tele-item">
                  <span className="vt-tele-lbl">BACKBONE MODE</span>
                  <span className="vt-tele-val text-emerald">
                    {firebaseData.status?.mode || "FIRESTORE_REST"}
                  </span>
                </div>
                <div className="vt-tele-item">
                  <span className="vt-tele-lbl">JUNCTION NODES</span>
                  <span className="vt-tele-val text-amber">46 Connected Intersections</span>
                </div>
                <div className="vt-tele-item">
                  <span className="vt-tele-lbl">SYNC STATUS</span>
                  <span className="vt-tele-val text-emerald">
                    <span className="vt-pulse-dot inline" />
                    LIVE STREAMING
                  </span>
                </div>
                <div className="vt-tele-item">
                  <span className="vt-tele-lbl">LAST REFRESH</span>
                  <span className="vt-tele-val text-slate">{firebaseData.lastRefreshed || "Just now"}</span>
                </div>
              </div>
            </div>

            {/* Dedicated Number Plate Section */}
            <div className="vt-fb-section-head">
              <h3 className="vt-fb-h3">
                <i className="fas fa-id-card text-emerald" /> Dedicated Vehicle Plate Registry (Firebase: `vehicle_plates`)
              </h3>
              <span className="vt-count-pill">{firebaseData.plates.length} Tracked Vehicles</span>
            </div>

            {firebaseData.loading && firebaseData.plates.length === 0 ? (
              <div className="vt-loading-card">
                <i className="fas fa-spinner fa-spin" />
                <span>Streaming live records from Firebase Firestore...</span>
              </div>
            ) : (
              <div className="vt-plates-grid">
                {firebaseData.plates.map((p, idx) => {
                  const isBlacklist = p.is_blacklisted || p.status === "HOTLIST_WANTED";
                  const sightings = p.sightings || [];
                  return (
                    <div key={idx} className={`vt-plate-card ${isBlacklist ? "blacklisted" : ""}`}>
                      <div className="vt-plate-head">
                        <div className="vt-plate-pill">
                          <span className="vt-ind">IND</span>
                          <span className="vt-plate-num">{p.plate}</span>
                        </div>
                        <span className={`vt-status-badge ${isBlacklist ? "badge-danger" : "badge-safe"}`}>
                          {isBlacklist ? "HOTLIST WANTED" : "IN TRANSIT"}
                        </span>
                      </div>

                      <div className="vt-plate-meta">
                        <div className="vt-meta-row">
                          <span className="lbl">Vehicle Type:</span>
                          <span className="val">{p.vehicle_type || "Car"} ({p.category || "Private"})</span>
                        </div>
                        <div className="vt-meta-row">
                          <span className="lbl">Latest Camera:</span>
                          <span className="val text-sky">{p.latest_camera_name || p.latest_camera || "CAM_01"}</span>
                        </div>
                        <div className="vt-meta-row">
                          <span className="lbl">Total Sightings:</span>
                          <span className="val text-amber">{p.total_sightings || sightings.length} camera passes</span>
                        </div>
                        <div className="vt-meta-row">
                          <span className="lbl">Last Sighted:</span>
                          <span className="val text-slate">{p.latest_timestamp || "Active"}</span>
                        </div>
                      </div>

                      {/* Chronological Timeline */}
                      <div className="vt-journey-timeline">
                        <span className="vt-timeline-title">Chronological Multi-Camera Timeline:</span>
                        <div className="vt-tl-nodes">
                          {sightings.map((s, sIdx) => (
                            <div key={sIdx} className="vt-tl-node">
                              <span className="vt-tl-dot" />
                              <div className="vt-tl-info">
                                <span className="vt-tl-cam">{s.camera_id}: {s.camera_name}</span>
                                <span className="vt-tl-ts">{s.timestamp?.split("T")[1] || s.timestamp} • {s.speed_kmph} km/h</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <button 
                        className="vt-btn" 
                        style={{ width: "100%", marginTop: "12px", background: "#c4643f", color: "#fff", justifyContent: "center", borderRadius: "6px", padding: "8px", fontWeight: 700, fontSize: "0.82rem" }}
                        onClick={() => handleTrackPlate(p.plate)}
                      >
                        <i className="fas fa-route" />
                        <span>Track Route on Live Map &rarr;</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
