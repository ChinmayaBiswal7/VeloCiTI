import { useState } from "react";
import GridCell from "./GridCell";
import "./CityGrid.css";

export default function CityGrid({ intersections, onCellClick }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filteredIntersections = intersections.filter(int => {
    const matchesSearch = int.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || int.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="city-grid-wrap">
      <div className="city-grid-header">
        <div className="city-grid-title">
          <i className="fas fa-th" />
          Bhubaneswar Intersection Matrix ({filteredIntersections.length} nodes)
        </div>

        <div className="grid-controls">
          <div className="search-input-wrap">
            <i className="fas fa-search" />
            <input
              type="text"
              className="grid-search-input"
              placeholder="Search intersection..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            <button
              className={`filter-btn ${statusFilter === "all" ? "active" : ""}`}
              onClick={() => setStatusFilter("all")}
            >
              All
            </button>
            <button
              className={`filter-btn ${statusFilter === "critical" ? "active" : ""}`}
              onClick={() => setStatusFilter("critical")}
              style={statusFilter === "critical" ? { color: "var(--red)" } : {}}
            >
              Critical
            </button>
            <button
              className={`filter-btn ${statusFilter === "medium" ? "active" : ""}`}
              onClick={() => setStatusFilter("medium")}
              style={statusFilter === "medium" ? { color: "var(--amber)" } : {}}
            >
              Moderate
            </button>
            <button
              className={`filter-btn ${statusFilter === "low" ? "active" : ""}`}
              onClick={() => setStatusFilter("low")}
              style={statusFilter === "low" ? { color: "var(--green)" } : {}}
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <div className="city-grid">
        {filteredIntersections.length === 0 ? (
          <div className="no-results-msg">
            <i className="fas fa-search" style={{ fontSize: "1.5rem" }} />
            <span>No matching intersections found for &ldquo;{searchTerm}&rdquo;</span>
          </div>
        ) : (
          filteredIntersections.map(int => (
            <GridCell key={int.id} intersection={int} onClick={onCellClick} />
          ))
        )}
      </div>
    </div>
  );
}
