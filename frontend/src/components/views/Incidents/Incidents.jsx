import { useState } from "react";
import "./Incidents.css";

export default function Incidents({ intersections }) {
  const critical = intersections.filter(i => i.status === "critical");
  const medium = intersections.filter(i => i.status === "medium");

  const [appliedRecs, setAppliedRecs] = useState({});
  const [dismissedRecs, setDismissedRecs] = useState({});

  const handleApply = (id) => setAppliedRecs(prev => ({ ...prev, [id]: true }));
  const handleDismiss = (id) => setDismissedRecs(prev => ({ ...prev, [id]: true }));

  const activeIncidents = [
    ...critical.slice(0, 4).map(i => ({
      id: i.id,
      location: i.name,
      desc: `Severe queue buildup with ${i.vehicleCount} vehicles. Average clearance speed reduced to ${i.averageSpeed} km/h.`,
      severity: "critical",
      time: "Live",
    })),
    ...medium.slice(0, 3).map(i => ({
      id: i.id,
      location: i.name,
      desc: `Moderate traffic flow with ${i.vehicleCount} vehicles. Approaching saturation threshold.`,
      severity: "medium",
      time: "4 mins ago",
    })),
  ];

  const logEntries = [
    { time: "20:42", location: "Jaydev Vihar", event: "Green phase dynamically extended by 18s", type: "optimized" },
    { time: "20:38", location: "Rasulgarh", event: "Critical congestion alert triggered (>280 vehicles)", type: "active" },
    { time: "20:35", location: "Master Canteen", event: "Manual override activated by operator", type: "active" },
    { time: "20:29", location: "Patia Square", event: "Coordinated green-wave corridor synchronized with KIIT Sq", type: "optimized" },
    { time: "20:21", location: "Vani Vihar", event: "Bottleneck dissipated. Traffic returning to nominal flow", type: "resolved" },
    { time: "20:15", location: "Acharya Vihar", event: "Autonomous adaptive cycle interval updated to 45s", type: "optimized" },
    { time: "20:04", location: "Khandagiri", event: "Evening peak surge managed — 0 emergency vehicle delays", type: "resolved" },
  ];

  return (
    <div className="incidents-view">
      <div className="incidents-grid">
        <div className="incidents-card">
          <div className="inc-panel-title"><i className="fas fa-robot" />AI Real-Time Dispatch Recommendations</div>
          {critical.slice(0, 3).length === 0 ? (
            <div style={{ color: "var(--green)", fontSize: "0.75rem", padding: "12px 0" }}>
              <i className="fas fa-check-circle" style={{ marginRight: "6px" }} />
              All major intersections operating within optimal parameters.
            </div>
          ) : (
            critical.slice(0, 3).map(item => {
              if (dismissedRecs[item.id]) return null;
              const isApplied = appliedRecs[item.id];
              const busiestLane = item.lanes.reduce((max, l) => l.vehicleCount > max.vehicleCount ? l : max, item.lanes[0]);
              return (
                <div key={item.id} className="ai-rec-card">
                  <div className="ai-rec-header">
                    <span className="ai-rec-loc">{item.name}</span>
                    <span className="ai-rec-tag">Priority AI Action</span>
                  </div>
                  <div className="ai-rec-desc">
                    Allocate +20s green light priority to <strong>{busiestLane.direction} bound</strong> traffic to prevent arterial gridlock.
                  </div>
                  <div className="ai-rec-actions">
                    <button
                      className="btn-apply-rec"
                      onClick={() => handleApply(item.id)}
                      disabled={isApplied}
                      style={isApplied ? { opacity: 0.6, cursor: "default" } : {}}
                    >
                      {isApplied ? "Applied ✓" : "Apply Recommendation"}
                    </button>
                    <button className="btn-dismiss-rec" onClick={() => handleDismiss(item.id)}>
                      Dismiss
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="incidents-card">
          <div className="inc-panel-title"><i className="fas fa-exclamation-triangle" />Active Traffic Incidents & Alerts</div>
          <div className="active-inc-list">
            {activeIncidents.length === 0 ? (
              <div style={{ color: "var(--green)", fontSize: "0.75rem" }}>No active incidents reported.</div>
            ) : (
              activeIncidents.map(inc => (
                <div key={inc.id} className="active-inc-item">
                  <div className={`inc-dot ${inc.severity}`} />
                  <div className="inc-info">
                    <div className="inc-loc-row">
                      <span className="inc-loc-name">{inc.location}</span>
                      <span className="inc-time-lbl">{inc.time}</span>
                    </div>
                    <div className="inc-desc-text">{inc.desc}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="incidents-card full-width">
          <div className="inc-panel-title"><i className="fas fa-history" />Traffic Command Operations Log (Last 24 Hours)</div>
          <table className="activity-log-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Location</th>
                <th>Event Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logEntries.map((log, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, color: "var(--text)" }}>{log.time}</td>
                  <td style={{ color: "var(--blue)" }}>{log.location}</td>
                  <td>{log.event}</td>
                  <td>
                    <span className={`log-status-pill ${log.type}`}>{log.type}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
