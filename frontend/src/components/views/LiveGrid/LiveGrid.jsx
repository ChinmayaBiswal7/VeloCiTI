import GridCell from "../Overview/GridCell";
import "./LiveGrid.css";

export default function LiveGrid({ intersections, stats, isConnected, isRunning, rawState, onCellClick, onStart, onPause, onReset }) {
  const messages = rawState?.agent_messages || [];

  return (
    <div className="live-grid">
      {/* Header */}
      <div className="lg-header">
        <div className="lg-title">
          <i className="fas fa-satellite-dish" />
          Live Traffic Grid
        </div>
        <div className="lg-badges">
          <div className={`lg-status-badge ${isConnected ? "connected" : "disconnected"}`}>
            <div className="lg-status-dot" />
            {isConnected ? "CONNECTED" : "DISCONNECTED"}
          </div>
          <div className="lg-engine-badge">CityFlow Engine</div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="lg-kpi-row">
        <div className="lg-kpi-card">
          <div className="lg-kpi-icon blue"><i className="fas fa-clock" /></div>
          <div>
            <div className="lg-kpi-num">{rawState?.step || 0}</div>
            <div className="lg-kpi-label">Sim Step</div>
          </div>
        </div>
        <div className="lg-kpi-card">
          <div className="lg-kpi-icon green"><i className="fas fa-car" /></div>
          <div>
            <div className="lg-kpi-num">{rawState?.total_vehicles || 0}</div>
            <div className="lg-kpi-label">Active Vehicles</div>
          </div>
        </div>
        <div className="lg-kpi-card">
          <div className="lg-kpi-icon amber"><i className="fas fa-hourglass-half" /></div>
          <div>
            <div className="lg-kpi-num">{rawState?.total_waiting || 0}</div>
            <div className="lg-kpi-label">Queued Cars</div>
          </div>
        </div>
        <div className="lg-kpi-card">
          <div className="lg-kpi-icon blue"><i className="fas fa-tachometer-alt" /></div>
          <div>
            <div className="lg-kpi-num">{stats.avgSpeed}</div>
            <div className="lg-kpi-label">Avg Speed (km/h)</div>
          </div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="lg-controls">
        <button className={`lg-ctrl-btn ${isRunning ? "active-start" : ""}`} onClick={onStart}>
          <i className="fas fa-play" /> Start
        </button>
        <button className={`lg-ctrl-btn ${!isRunning && isConnected ? "active-pause" : ""}`} onClick={onPause}>
          <i className="fas fa-pause" /> Pause
        </button>
        <button className="lg-ctrl-btn" onClick={onReset}>
          <i className="fas fa-undo" /> Reset
        </button>
        <div className="lg-ctrl-info">
          {isConnected ? (
            <span className="lg-running-tag">{isRunning ? "● Simulation Running" : "◯ Simulation Paused"}</span>
          ) : (
            <span className="lg-offline-tag">⚠ CityFlow server not detected</span>
          )}
        </div>
      </div>

      {/* Junction Grid */}
      <div className="lg-junction-wrap">
        <div className="lg-junction-title">
          <i className="fas fa-th" />
          Active Junction Nodes ({intersections.length})
        </div>
        {intersections.length === 0 ? (
          <div className="lg-placeholder">
            <i className="fas fa-spinner fa-pulse" />
            <span>Waiting for CityFlow data…</span>
            <span className="lg-placeholder-sub">Start the CityFlow server and click Start</span>
          </div>
        ) : (
          <div className="lg-junction-grid">
            {intersections.map(int => (
              <GridCell key={int.id} intersection={int} onClick={onCellClick} />
            ))}
          </div>
        )}
      </div>

      {/* Agent Messages */}
      <div className="lg-messages">
        <div className="lg-messages-title">
          <i className="fas fa-comments" /> Multi-Agent Communication Log
        </div>
        {messages.length === 0 ? (
          <div className="lg-no-msg">No agent messages yet — start the simulation</div>
        ) : (
          <div className="lg-msg-list">
            {messages.slice(-6).map((m, i) => (
              <div key={i} className="lg-msg">
                <span className="sender">[{m.sender}]</span>{" "}
                <span className="step">(Step {m.timestamp}):</span>{" "}
                <span className="reason">{m.decision_reason}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
