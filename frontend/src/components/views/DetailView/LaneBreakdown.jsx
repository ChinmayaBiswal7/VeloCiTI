import "./LaneBreakdown.css";

export default function LaneBreakdown({ intersection, onOpenCCTV }) {
  return (
    <div className="lane-panel">
      <div className="panel-title"><i className="fas fa-road" />Lane Breakdown & CCTV Feeds</div>
      <div className="lanes-grid">
        {intersection.lanes.map(lane => {
          const pct = Math.min(100, Math.round((lane.vehicleCount / 115) * 100));
          return (
            <div key={lane.direction} className={`lane-card ${lane.light}`}>
              <div className="lane-head">
                <span className="lane-dir">{lane.direction}</span>
                <div className={`lane-light-dot ${lane.light}`} />
              </div>
              <div className="lane-vehicles">{lane.vehicleCount}</div>
              <div className="lane-speed">{lane.averageSpeed} km/h</div>
              <div className="lane-bar">
                <div className={`lane-bar-fill ${lane.light}`} style={{ width:`${pct}%` }} />
              </div>
              <div className="lane-foot">
                <div className={`lane-badge ${lane.manualActive ? "manual" : ""}`}>
                  <i className={`fas ${lane.manualActive ? "fa-hand-pointer" : "fa-robot"}`} />
                  {lane.manualActive ? "Manual" : "AI Control"}
                </div>
                <button
                  className="lane-cctv-btn"
                  onClick={() => onOpenCCTV?.(lane.direction)}
                  title={`Open Live CCTV Feed for ${lane.direction} corridor`}
                >
                  <i className="fas fa-video" /> CCTV
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
