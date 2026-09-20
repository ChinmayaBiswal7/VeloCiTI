import "./KPIRow.css";

export default function KPIRow({ stats }) {
  const congColor = stats.avgCongestion > 70 ? "red" : stats.avgCongestion > 40 ? "amber" : "green";
  return (
    <div className="kpi-row">
      <div className="kpi-card">
        <div className="kpi-icon blue"><i className="fas fa-crosshairs" /></div>
        <div>
          <div className="kpi-num">{stats.totalNodes}</div>
          <div className="kpi-label">Total Nodes</div>
          <div className="kpi-sub">30 unique intersections</div>
        </div>
      </div>
      <div className="kpi-card">
        <div className={`kpi-icon ${congColor}`}><i className="fas fa-traffic-light" /></div>
        <div>
          <div className="kpi-num">{stats.avgCongestion}%</div>
          <div className="kpi-label">City Congestion</div>
          <div className="kpi-sub">{stats.criticalCount} critical nodes</div>
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-icon blue"><i className="fas fa-tachometer-alt" /></div>
        <div>
          <div className="kpi-num">{stats.avgSpeed}</div>
          <div className="kpi-label">Avg Speed (km/h)</div>
          <div className="kpi-sub">City-wide average</div>
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-icon green"><i className="fas fa-check-circle" /></div>
        <div>
          <div className="kpi-num">{stats.clearCount}</div>
          <div className="kpi-label">Clear Nodes</div>
          <div className="kpi-sub">{stats.mediumCount} moderate</div>
        </div>
      </div>
    </div>
  );
}
