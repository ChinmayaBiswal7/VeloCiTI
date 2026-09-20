import "./TrafficFlow.css";

export default function TrafficFlow({ intersection }) {
  const getLane = (dir) => intersection.lanes.find(l => l.direction === dir) || { vehicleCount: 0, light: "red" };
  const north = getLane("North");
  const east  = getLane("East");
  const south = getLane("South");
  const west  = getLane("West");

  return (
    <div className="flow-panel">
      <div className="panel-title"><i className="fas fa-arrows-alt" />Directional Flow</div>
      <div className="flow-compass">
        <div className="flow-arm north">
          <span className="flow-dir">N</span>
          <span className="flow-val">{north.vehicleCount}</span>
          <div className={`flow-light ${north.light}`} />
        </div>
        <div className="flow-arm east">
          <span className="flow-dir">E</span>
          <span className="flow-val">{east.vehicleCount}</span>
          <div className={`flow-light ${east.light}`} />
        </div>
        <div className="flow-arm south">
          <div className={`flow-light ${south.light}`} />
          <span className="flow-val">{south.vehicleCount}</span>
          <span className="flow-dir">S</span>
        </div>
        <div className="flow-arm west">
          <span className="flow-dir">W</span>
          <span className="flow-val">{west.vehicleCount}</span>
          <div className={`flow-light ${west.light}`} />
        </div>
        <div className="flow-center">
          <i className="fas fa-crosshairs" />
        </div>
      </div>
    </div>
  );
}
