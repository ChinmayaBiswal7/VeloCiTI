import React from "react";
import "./PortalSelector.css";

export default function PortalSelector({ onSelectPortal, currentUser, onLogout }) {
  return (
    <div className="portal-container">
      {/* Ambient background effects */}
      <div className="portal-ambient-glow top-left" />
      <div className="portal-ambient-glow bottom-right" />
      <div className="portal-grid-overlay" />

      {/* Top Header */}
      <header className="portal-header">
        <div className="portal-brand">
          <img className="brand-logo" src="/velociti-logo.jpg" alt="VeloCiTI logo" width="46" height="46" />
          <div>
            <h1 className="portal-title">VeloCiTI Command Nexus</h1>
            <p className="portal-subtitle">Bhubaneswar Smart City Integrated Traffic & Security Grid</p>
          </div>
        </div>

        <div className="portal-user-section">
          {onLogout && (
            <button className="portal-logout-btn" onClick={onLogout} title="Sign out of system">
              <i className="fas fa-arrow-right-from-bracket" />
              <span>Lock Terminal</span>
            </button>
          )}
        </div>
      </header>


      {/* Main Module Selection Area */}
      <main className="portal-main">
        <div className="portal-intro">
          <div className="portal-pill-badge">
            <span className="portal-pulse-dot" />
            CENTRAL FIREBASE CLOUD CONNECTED • VELOCITI
          </div>
          <h2 className="portal-headline">Select Operational Command Module</h2>
          <p className="portal-lead">
            Access authorized mission portals. Dynamic signals and vehicle tracking both stream
            synchronously to the central cloud database without isolated silos.
          </p>
        </div>

        <div className="portal-cards-grid">
          {/* Card 1: Traffic Management */}
          <div className="portal-card" onClick={() => onSelectPortal("traffic")}>
            <div className="portal-card-glow traffic-glow" />
            <div className="portal-card-header">
              <div className="portal-card-icon-box traffic-icon">
                <i className="fas fa-traffic-light" />
              </div>
              <span className="portal-card-tag active-tag">ADAPTIVE CONTROL</span>
            </div>

            <div className="portal-card-body">
              <h3 className="portal-card-title">VeloCiTI AI Urban Traffic Management</h3>
              <p className="portal-card-desc">
                Real-time adaptive signal control across 100 Bhubaneswar junctions, emergency green corridors,
                incident management, and CityFlow multi-agent microsimulation.
              </p>

              <div className="portal-features-list">
                <div className="portal-feature-item">
                  <i className="fas fa-bolt text-amber" />
                  <span>4-Lane Realtime Adaptive Signal Timing</span>
                </div>
                <div className="portal-feature-item">
                  <i className="fas fa-ambulance text-red" />
                  <span>Emergency Green Corridor Priority Pre-emption</span>
                </div>
                <div className="portal-feature-item">
                  <i className="fas fa-brain text-blue" />
                  <span>CityFlow 2D Multi-Agent Traffic Engine</span>
                </div>
                <div className="portal-feature-item">
                  <i className="fas fa-map-marked-alt text-emerald" />
                  <span>GIS Heatmap & Automated Incident Dispatch</span>
                </div>
              </div>
            </div>

            <div className="portal-card-footer">
              <button className="portal-launch-btn traffic-btn">
                <span>Launch Traffic Command</span>
                <i className="fas fa-arrow-right" />
              </button>
            </div>
          </div>

          {/* Card 2: Vehicle Tracking */}
          <div className="portal-card" onClick={() => onSelectPortal("tracking")}>
            <div className="portal-card-glow tracking-glow" />
            <div className="portal-card-header">
              <div className="portal-card-icon-box tracking-icon">
                <i className="fas fa-satellite" />
              </div>
              <span className="portal-card-tag central-db-tag">CENTRAL DB FUSION</span>
            </div>

            <div className="portal-card-body">
              <h3 className="portal-card-title">Citywide ANPR & Vehicle Journey Tracking</h3>
              <p className="portal-card-desc">
                Centralized multi-camera intelligence. Replaces disconnected junction databases with
                a central Firebase cloud database sorting sightings chronologically for journey reconstruction.
              </p>

              <div className="portal-features-list">
                <div className="portal-feature-item">
                  <i className="fas fa-database text-sky" />
                  <span>Unified Central Cloud Database (8 CCTV Junctions)</span>
                </div>
                <div className="portal-feature-item">
                  <i className="fas fa-route text-indigo" />
                  <span>Chronological Plate OCR & Journey Map Timeline</span>
                </div>
                <div className="portal-feature-item">
                  <i className="fas fa-ghost text-purple" />
                  <span>Plate-Less Ghost Vehicle Visual Re-Identification</span>
                </div>
                <div className="portal-feature-item">
                  <i className="fas fa-id-card text-emerald" />
                  <span>MoRTH Vahan RTO Ownership & Stolen Hotlist</span>
                </div>
              </div>
            </div>

            <div className="portal-card-footer">
              <button className="portal-launch-btn tracking-btn">
                <span>Launch Vehicle Tracking</span>
                <i className="fas fa-arrow-right" />
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Footer Status Bar */}
      <footer className="portal-footer">
        <div className="portal-footer-item">
          <i className="fas fa-cloud text-sky" />
          <span>Cloud Backbone: <strong>Firebase Firestore</strong></span>
        </div>
        <div className="portal-footer-divider" />
        <div className="portal-footer-item">
          <i className="fas fa-video text-emerald" />
          <span>CCTV Nodes: <strong>CAM_01 to CAM_08 Streaming</strong></span>
        </div>
        <div className="portal-footer-divider" />
        <div className="portal-footer-item">
          <i className="fas fa-shield-halved text-amber" />
          <span>Deployment: <strong>Live on Render (Zero Local Saves)</strong></span>
        </div>
      </footer>
    </div>
  );
}
