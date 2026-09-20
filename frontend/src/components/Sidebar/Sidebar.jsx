import "./Sidebar.css";

const NAV = [
  { id:"overview",  icon:"fa-th",             label:"Matrix Grid" },
  { id:"map",       icon:"fa-map-marked-alt", label:"Live GIS Map" },
  { id:"emergency", icon:"fa-ambulance",      label:"Green Corridor" },
  { id:"analytics", icon:"fa-chart-line",     label:"Analytics" },
  { id:"incidents", icon:"fa-bell",           label:"Incidents" },
  { id:"livegrid",  icon:"fa-satellite-dish", label:"Live Grid" },
  { id:"cityflow",  icon:"fa-microchip",      label:"City Flow Model" },
  { id:"webcam",    icon:"fa-video",          label:"Live Webcam" },
];

export default function Sidebar({ currentView, onNav, time, date, stats }) {
  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <img className="brand-logo" src="/velociti-logo.jpg" alt="VeloCiTI logo" width="36" height="36" />
        <div>
          <div className="sb-logo-name">Velo<span>CiTI</span></div>
          <div className="sb-logo-ver">Traffic HQ v2.0</div>
        </div>
      </div>

      <div className="sb-status">
        <div className="sb-status-dot" />
        System Online
        <span className="sb-firebase-badge" title="Firebase Real-Time Data Sync Active">
          <i className="fas fa-fire" style={{ color: "#dba53a", marginRight: "4px" }} />
          Firebase Live
        </span>
      </div>

      <nav className="sb-nav">
        {NAV.map(n => (
          <button key={n.id} className={`sb-nav-btn${currentView===n.id?" active":""}`} onClick={() => onNav(n.id)}>
            <i className={`fas ${n.icon}`} />
            <span>{n.label}</span>
            {n.id === "incidents" && stats.criticalCount > 0 && (
              <span className="sb-badge">{stats.criticalCount}</span>
            )}
          </button>
        ))}
      </nav>

      <div className="sb-section">
        <div className="sb-stats">
          <div className="sb-stat-row">
            <span className="sb-stat-label">Active nodes</span>
            <span className="sb-stat-val blue">{stats.totalNodes}</span>
          </div>
          <div className="sb-stat-row">
            <span className="sb-stat-label">Critical</span>
            <span className="sb-stat-val red">{stats.criticalCount}</span>
          </div>
          <div className="sb-stat-row">
            <span className="sb-stat-label">Moderate</span>
            <span className="sb-stat-val amber">{stats.mediumCount}</span>
          </div>
          <div className="sb-stat-row">
            <span className="sb-stat-label">Clear</span>
            <span className="sb-stat-val green">{stats.clearCount}</span>
          </div>
        </div>

        <div className="sb-clock">
          <div className="sb-clock-time">{time}</div>
          <div className="sb-clock-date">{date}</div>
          <div className="sb-clock-city">Bhubaneswar, India</div>
        </div>
      </div>
    </aside>
  );
}
