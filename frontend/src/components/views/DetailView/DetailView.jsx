import { useState } from "react";
import SignalStatus from "./SignalStatus";
import LaneBreakdown from "./LaneBreakdown";
import ManualOverride from "./ManualOverride";
import TrafficFlow from "./TrafficFlow";
import AIPanel from "./AIPanel";
import DetailRadar from "./DetailRadar";
import CCTVModal from "./CCTVModal";
import "./DetailView.css";

export default function DetailView({ intersection, onBack, onUpdateLane, onRevertLane, onRevertAll, backLabel }) {
  const [cctvState, setCctvState] = useState({ isOpen: false, direction: "North" });

  const statusLabel = intersection.status === "critical" ? "Critical Congestion" : intersection.status === "medium" ? "Moderate Traffic" : "Clear Traffic";

  const handleOpenCCTV = (dir = "North") => {
    setCctvState({ isOpen: true, direction: dir });
  };

  const handleCloseCCTV = () => {
    setCctvState({ isOpen: false, direction: "North" });
  };

  return (
    <div className="detail-view">
      <div className="dv-header">
        <div className="dv-header-left">
          <button className="dv-back-btn" onClick={onBack}>
            <i className="fas fa-arrow-left" /> {backLabel || "Back to Matrix"}
          </button>
          <div>
            <div className="dv-title">{intersection.name}</div>
          </div>
          <span className={`dv-badge ${intersection.status}`}>{statusLabel}</span>
          <button
            className="dv-cctv-header-btn"
            onClick={() => handleOpenCCTV("North")}
            title="Launch Live CCTV Camera Matrix"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              background: "rgba(217,119,87, 0.15)",
              border: "1px solid rgba(217,119,87, 0.35)",
              color: "#d97757",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <i className="fas fa-video" /> Live CCTV Feed
          </button>
        </div>

        <div className="dv-stats">
          <div className="dv-stat-item">
            <span className="dv-stat-val">{intersection.congestionPct}%</span>
            <span className="dv-stat-lbl">Density</span>
          </div>
          <div className="dv-stat-item">
            <span className="dv-stat-val">{intersection.averageSpeed}</span>
            <span className="dv-stat-lbl">km/h</span>
          </div>
          <div className="dv-stat-item">
            <span className="dv-stat-val">{intersection.vehicleCount}</span>
            <span className="dv-stat-lbl">Queued</span>
          </div>
        </div>
      </div>

      <div className="dv-body">
        <div className="dv-col">
          <SignalStatus intersection={intersection} />
          <AIPanel intersection={intersection} />
        </div>

        <div className="dv-col">
          <LaneBreakdown intersection={intersection} onOpenCCTV={handleOpenCCTV} />
          <ManualOverride
            intersection={intersection}
            onUpdateLane={onUpdateLane}
            onRevertLane={onRevertLane}
            onRevertAll={onRevertAll}
          />
        </div>

        <div className="dv-col">
          <DetailRadar intersection={intersection} />
          <TrafficFlow intersection={intersection} />
        </div>
      </div>

      {/* Live CCTV Video Modal */}
      {cctvState.isOpen && (
        <CCTVModal
          intersection={intersection}
          initialDirection={cctvState.direction}
          onClose={handleCloseCCTV}
        />
      )}
    </div>
  );
}
