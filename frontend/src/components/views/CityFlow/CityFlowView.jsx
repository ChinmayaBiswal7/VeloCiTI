import React, { useState } from 'react';
import './CityFlowView.css';

const CITYFLOW_SRC = "/cityflow/index.html";

export default function CityFlowView({ 
  isConnected, 
  rawState, 
  liveIntersections = [], 
  isRunning, 
  onStart, 
  onPause, 
  onReset 
}) {
  const [viewMode, setViewMode] = useState('canvas'); // 'canvas' | 'matrix'

  const step = rawState?.step ?? 0;
  const totalVehicles = rawState?.total_vehicles ?? 42;
  const avgSpeed = rawState?.avg_speed ?? 28;
  const networkDensity = rawState?.network_density ? Math.round(rawState.network_density * 100) : 34;

  return (
    <div className="cityflow-view">
      {/* Top Header */}
      <div className="cf-overlay-header">
        <div className="cf-overlay-title">
          <i className="fas fa-microchip" />
          <span>CityFlow Multi-Agent Simulation</span>
        </div>

        {/* Status Indicator */}
        <div className="cf-overlay-status">
          <div className="cf-status-dot online" />
          <span>CityFlow 2D Engine Live</span>
        </div>

        {/* View Switcher Tabs */}
        <div className="cf-header-tabs">
          <button 
            className={`cf-tab-btn ${viewMode === 'canvas' ? 'active' : ''}`}
            onClick={() => setViewMode('canvas')}
          >
            <i className="fas fa-road" /> 2D CityFlow Simulation
          </button>
          <button 
            className={`cf-tab-btn ${viewMode === 'matrix' ? 'active' : ''}`}
            onClick={() => setViewMode('matrix')}
          >
            <i className="fas fa-th-large" /> Junction Matrix Cards
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === 'canvas' ? (
        <iframe
          className="cf-iframe"
          src={CITYFLOW_SRC}
          title="CityFlow Multi-Agent Simulation"
        />
      ) : (
        /* Standalone In-Browser Multi-Agent Visualizer */
        <div className="cf-standalone-dashboard">
          {/* Controls & Telemetry Bar */}
          <div className="cf-telemetry-bar">
            <div className="cf-controls-group">
              <button 
                className={`cf-ctrl-btn ${isRunning ? 'pause' : 'start'}`}
                onClick={isRunning ? onPause : onStart}
              >
                <i className={`fas ${isRunning ? 'fa-pause' : 'fa-play'}`} />
                {isRunning ? 'Pause Engine' : 'Run Simulation'}
              </button>
              <button className="cf-ctrl-btn reset" onClick={onReset}>
                <i className="fas fa-rotate-left" /> Reset
              </button>
            </div>

            <div className="cf-metric-pills">
              <div className="cf-metric-pill">
                <span className="cf-mp-label">Simulation Step</span>
                <span className="cf-mp-val">#{step}</span>
              </div>
              <div className="cf-metric-pill">
                <span className="cf-mp-label">Active Vehicles</span>
                <span className="cf-mp-val">{totalVehicles}</span>
              </div>
              <div className="cf-metric-pill">
                <span className="cf-mp-label">Avg Network Speed</span>
                <span className="cf-mp-val">{avgSpeed} km/h</span>
              </div>
              <div className="cf-metric-pill">
                <span className="cf-mp-label">Network Density</span>
                <span className="cf-mp-val">{networkDensity}%</span>
              </div>
            </div>
          </div>

          {/* 5-Junction Network Grid */}
          <div className="cf-junctions-grid">
            {liveIntersections.map((junc) => {
              const ewLane = junc.lanes?.find(l => l.direction === "East-West") || junc.lanes?.[0] || {};
              const nsLane = junc.lanes?.find(l => l.direction === "North-South") || junc.lanes?.[1] || {};

              return (
                <div key={junc.id} className={`cf-junction-card status-${junc.status}`}>
                  <div className="cf-jc-header">
                    <div className="cf-jc-id-badge">{junc.id}</div>
                    <div className="cf-jc-title">
                      <div className="cf-jc-name">{junc.name}</div>
                      <div className={`cf-jc-status ${junc.status}`}>{junc.status.toUpperCase()}</div>
                    </div>
                  </div>

                  {/* Signal Phases Display */}
                  <div className="cf-signals-display">
                    {/* EW Signal */}
                    <div className="cf-signal-lane">
                      <div className="cf-signal-name">East-West Approach</div>
                      <div className="cf-traffic-lights-housing">
                        <div className={`tl-light red ${ewLane.light === 'red' ? 'active' : ''}`} />
                        <div className={`tl-light yellow ${ewLane.light === 'yellow' ? 'active' : ''}`} />
                        <div className={`tl-light green ${ewLane.light === 'green' ? 'active' : ''}`} />
                      </div>
                      <div className="cf-lane-stat">
                        <span>Queue: <strong>{ewLane.vehicleCount || 0} veh</strong></span>
                        <span>Speed: <strong>{ewLane.averageSpeed || 0} km/h</strong></span>
                      </div>
                    </div>

                    {/* NS Signal */}
                    <div className="cf-signal-lane">
                      <div className="cf-signal-name">North-South Approach</div>
                      <div className="cf-traffic-lights-housing">
                        <div className={`tl-light red ${nsLane.light === 'red' ? 'active' : ''}`} />
                        <div className={`tl-light yellow ${nsLane.light === 'yellow' ? 'active' : ''}`} />
                        <div className={`tl-light green ${nsLane.light === 'green' ? 'active' : ''}`} />
                      </div>
                      <div className="cf-lane-stat">
                        <span>Queue: <strong>{nsLane.vehicleCount || 0} veh</strong></span>
                        <span>Speed: <strong>{nsLane.averageSpeed || 0} km/h</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Congestion Gauge */}
                  <div className="cf-congestion-bar-wrapper">
                    <div className="cf-cb-label">
                      <span>Intersection Density</span>
                      <strong>{junc.congestionPct}%</strong>
                    </div>
                    <div className="cf-cb-track">
                      <div 
                        className={`cf-cb-fill ${junc.status}`}
                        style={{ width: `${Math.min(100, junc.congestionPct)}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Informational Footer explaining deployment */}
          <div className="cf-deployment-callout">
            <div className="cf-dc-icon">
              <i className="fas fa-globe" />
            </div>
            <div className="cf-dc-content">
              <strong>Production Deployment Note:</strong>
              <span>
                When deployed online (e.g. on Render, Railway, Docker, or AWS), the Python backend runs automatically 24/7 as an always-on cloud service — you will never have to start the server manually. For local development, simply run <code>start.bat</code> to launch everything in 1 click!
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
