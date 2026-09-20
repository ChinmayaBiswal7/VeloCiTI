import "./AlertTicker.css";

export default function AlertTicker({ intersections }) {
  const critical = intersections.filter(i => i.status === "critical");
  const medium   = intersections.filter(i => i.status === "medium");
  const items = [
    ...critical.slice(0,6).map(i => ({ text:`[CRITICAL] ${i.name} — ${i.vehicleCount} veh | ${i.averageSpeed} km/h`, cls:"crit" })),
    ...medium.slice(0,4).map(i =>   ({ text:`[MODERATE] ${i.name} — ${i.vehicleCount} veh`, cls:"warn" })),
    { text:"[OK] AI signal optimization active across all 100 nodes", cls:"ok" },
    { text:`[SYS] All sensors nominal — ${new Date().toLocaleTimeString("en-IN", {hour12:false})}`, cls:"" },
  ];
  const doubled = [...items, ...items];
  return (
    <div className="ticker">
      <div className="ticker-live"><div className="ticker-live-dot" />LIVE</div>
      <div className="ticker-scroll">
        <div className="ticker-inner">
          {doubled.map((item, i) => (
            <span key={i} className={`ticker-item ${item.cls}`}>{item.text}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
