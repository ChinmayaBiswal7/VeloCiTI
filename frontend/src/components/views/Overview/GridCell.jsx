import "./GridCell.css";

export default function GridCell({ intersection, onClick }) {
  const { name, status, averageSpeed, congestionPct, density } = intersection;
  const displayDensity = congestionPct !== undefined ? congestionPct : Math.round((density || 0) * 100);

  return (
    <div
      className={`grid-cell ${status}`}
      onClick={() => onClick(intersection)}
      title={`${name}: ${displayDensity}% Density, ${averageSpeed} km/h`}
    >
      <div className="cell-name">{name}</div>
      <div className="cell-data-row">
        <span className={`cell-count ${status}`}>
          {displayDensity}<span className="cell-unit">%</span>
        </span>
        <span className="cell-speed">{averageSpeed} km/h</span>
      </div>
      <div className="cell-bar">
        <div className={`cell-bar-fill ${status}`} style={{ width: `${displayDensity}%` }} />
      </div>
    </div>
  );
}
