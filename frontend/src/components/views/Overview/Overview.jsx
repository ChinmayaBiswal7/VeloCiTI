import KPIRow from "./KPIRow";
import CityGrid from "./CityGrid";
import AlertTicker from "./AlertTicker";
import "./Overview.css";

export default function Overview({ intersections, stats, onCellClick }) {
  return (
    <div className="overview">
      <KPIRow stats={stats} />
      <CityGrid intersections={intersections} onCellClick={onCellClick} />
      <AlertTicker intersections={intersections} />
    </div>
  );
}
