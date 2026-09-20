import "./AIPanel.css";

export default function AIPanel({ intersection }) {
  const maxLane = intersection.lanes.reduce((prev, curr) => curr.vehicleCount > prev.vehicleCount ? curr : prev, intersection.lanes[0]);
  const confidence = 85 + Math.floor((intersection.vehicleCount % 12));
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (confidence / 100) * circumference;

  let recommendation = `Extend green phase on ${maxLane.direction} corridor by 15s to clear volume.`;
  if (intersection.status === "critical") {
    recommendation = `High congestion detected. AI recommending priority green-wave on ${maxLane.direction} bound traffic.`;
  } else if (intersection.status === "low") {
    recommendation = "Traffic moving smoothly. AI maintains standard cycle times with minimal delay.";
  }

  return (
    <div className="ai-panel">
      <div className="panel-title"><i className="fas fa-brain" />AI Optimization</div>
      <div className="ai-score-box">
        <div className="ai-ring-container">
          <svg className="ai-ring-svg" viewBox="0 0 80 80">
            <circle className="ai-ring-bg" cx="40" cy="40" r={radius} />
            <circle
              className="ai-ring-val"
              cx="40"
              cy="40"
              r={radius}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
            />
          </svg>
          <div className="ai-score-text">{confidence}%</div>
        </div>
        <div className="ai-meta">
          <span className="ai-meta-label">Optimization Confidence</span>
          <span className="ai-meta-status"><i className="fas fa-check-circle" style={{marginRight:"4px"}} />Active & Synced</span>
        </div>
      </div>
      <div className="ai-rec-box">
        <i className="fas fa-lightbulb" />
        <span>{recommendation}</span>
      </div>
    </div>
  );
}
