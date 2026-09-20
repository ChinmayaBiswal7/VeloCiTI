import { useState, useEffect } from "react";
import "./SignalStatus.css";

export default function SignalStatus({ intersection }) {
  const [countdown, setCountdown] = useState(30);
  useEffect(() => {
    setCountdown(30);
    const id = setInterval(() => setCountdown(c => c <= 1 ? 30 : c - 1), 1000);
    return () => clearInterval(id);
  }, [intersection.id]);

  const greenLanes = intersection.lanes.filter(l => l.light === "green").map(l => l.direction);
  const hasGreen   = greenLanes.length > 0;
  const hasYellow  = intersection.lanes.some(l => l.light === "yellow");
  const phase = hasGreen ? `${greenLanes.join(" + ")} Green` : hasYellow ? "Yield" : "All Red";

  return (
    <div className="signal-panel">
      <div className="panel-title"><i className="fas fa-traffic-light" />Signal Status</div>
      <div className="signal-body">
        <div className="signal-pole">
          <div className="signal-housing">
            <div className={`signal-light ${!hasGreen && !hasYellow ? "red-on" : ""}`} />
            <div className={`signal-light ${hasYellow && !hasGreen ? "amber-on" : ""}`} />
            <div className={`signal-light ${hasGreen ? "green-on" : ""}`} />
          </div>
          <div className="signal-post" />
        </div>
        <div className="signal-meta">
          <div className="signal-phase">{phase}</div>
          <div className="signal-countdown">{countdown}s</div>
          <div className="signal-bar">
            <div className="signal-bar-fill" style={{ width:`${(countdown/30)*100}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
