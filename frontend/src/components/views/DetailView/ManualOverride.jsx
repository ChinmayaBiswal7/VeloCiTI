import "./ManualOverride.css";

export default function ManualOverride({ intersection, onUpdateLane, onRevertLane, onRevertAll }) {
  return (
    <div className="override-panel">
      <div className="panel-title">
        <span><i className="fas fa-hand-pointer" style={{marginRight:"6px"}} />Manual Override</span>
        <span className="override-tag">Operator Control</span>
      </div>
      <div className="override-grid">
        {intersection.lanes.map(lane => (
          <div key={lane.direction} className="ov-card">
            <div className="ov-dir">{lane.direction}</div>
            <div className="ov-lights">
              {["red","yellow","green"].map(color => (
                <button key={color} className={`ov-btn ${color[0]} ${lane.light===color?"active":"inactive"}`}
                  onClick={() => onUpdateLane(intersection.id, lane.direction, color)} />
              ))}
            </div>
            <div className="ov-status-row" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <span className={`ov-status ${lane.manualActive?"manual":""}`}>
                {lane.manualActive ? "Manual" : "AI"}
              </span>
              <button className="ov-revert" disabled={!lane.manualActive}
                onClick={() => onRevertLane(intersection.id, lane.direction)}>
                Revert
              </button>
            </div>
          </div>
        ))}
      </div>
      <button className="revert-all-btn" onClick={() => onRevertAll(intersection.id)}>
        <i className="fas fa-robot" /> Revert All to AI
      </button>
    </div>
  );
}
