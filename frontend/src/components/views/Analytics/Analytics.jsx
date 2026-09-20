import { useState } from "react";
import {
  Chart,
  ArcElement,
  LineElement,
  BarElement,
  PointElement,
  RadialLinearScale,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import { Line, Doughnut, Bar } from "react-chartjs-2";
import { INTERSECTION_NAMES } from "../../../data/intersections";
import "./Analytics.css";

// Register chart components explicitly — ensures it works on any machine regardless of import order
Chart.register(
  ArcElement, LineElement, BarElement, PointElement,
  RadialLinearScale, CategoryScale, LinearScale,
  Filler, Tooltip, Legend
);

export default function Analytics({ intersections }) {
  const [selectedName, setSelectedName] = useState(INTERSECTION_NAMES[0]);
  const activeIntersection = intersections.find(i => i.name === selectedName) || intersections[0];

  // 1. Timeline Chart (24h)
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const peakHours = [8, 9, 10, 17, 18, 19, 20];
  const timelineData = {
    labels: hours,
    datasets: [
      {
        label: "Congestion Load %",
        data: hours.map((_, i) => peakHours.includes(i) ? 65 + Math.floor(Math.random() * 25) : 15 + Math.floor(Math.random() * 30)),
        borderColor: "#d97757",
        backgroundColor: "rgba(217,119,87, 0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 2.5,
        pointBackgroundColor: "#d97757",
        borderWidth: 2,
      },
    ],
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { color: "rgba(63,61,57, 0.3)" }, ticks: { color: "#7c786c", font: { size: 9 } } },
      y: { grid: { color: "rgba(63,61,57, 0.3)" }, ticks: { color: "#7c786c", font: { size: 9 } }, max: 100, beginAtZero: true },
    },
    plugins: { legend: { display: false } },
  };

  // 2. Vehicle Mix (Donut)
  const donutData = {
    labels: ["Cars", "Two-Wheelers", "Buses/Trucks"],
    datasets: [
      {
        data: [52, 28, 20],
        backgroundColor: ["#d97757", "#63a375", "#dba53a"],
        borderColor: "#292826",
        borderWidth: 2,
      },
    ],
  };
  const donutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "70%",
    plugins: { legend: { display: false } },
  };

  // 3. Top Critical Zones
  const sortedCritical = [...intersections].sort((a, b) => b.vehicleCount - a.vehicleCount).slice(0, 5);
  const maxCriticalCount = sortedCritical[0]?.vehicleCount || 1;

  // 4. Lane Bar Chart
  const laneBarData = {
    labels: activeIntersection.lanes.map(l => l.direction),
    datasets: [
      {
        label: "Vehicles",
        data: activeIntersection.lanes.map(l => l.vehicleCount),
        backgroundColor: ["#d97757", "#63a375", "#dba53a", "#e5534b"],
        borderRadius: 4,
      },
    ],
  };
  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { display: false }, ticks: { color: "#b5b1a4", font: { size: 10 } } },
      y: { grid: { color: "rgba(63,61,57, 0.3)" }, ticks: { color: "#7c786c", font: { size: 9 } }, beginAtZero: true },
    },
    plugins: { legend: { display: false } },
  };

  return (
    <div className="analytics-view">
      <div className="analytics-grid">
        <div className="analytics-card full-width">
          <div className="card-header">
            <div className="card-title"><i className="fas fa-chart-line" />24-Hour City-Wide Congestion Trend</div>
          </div>
          <div className="chart-container-220">
            <Line data={timelineData} options={lineOptions} />
          </div>
        </div>

        <div className="analytics-card">
          <div className="card-header">
            <div className="card-title"><i className="fas fa-chart-pie" />Vehicle Fleet Distribution</div>
          </div>
          <div className="chart-container-180">
            <Doughnut data={donutData} options={donutOptions} />
          </div>
          <div className="donut-legend">
            <div className="donut-leg-item"><div className="donut-dot" style={{ background:"#d97757" }} />Cars (52%)</div>
            <div className="donut-leg-item"><div className="donut-dot" style={{ background:"#63a375" }} />2-Wheelers (28%)</div>
            <div className="donut-leg-item"><div className="donut-dot" style={{ background:"#dba53a" }} />Heavy (20%)</div>
          </div>
        </div>

        <div className="analytics-card">
          <div className="card-header">
            <div className="card-title"><i className="fas fa-fire-alt" />Top High-Density Bottlenecks</div>
          </div>
          <div className="critical-list">
            {sortedCritical.map((item, idx) => (
              <div key={item.id} className="crit-row">
                <span className="crit-rank">#{idx + 1}</span>
                <span className="crit-name">{item.name}</span>
                <div className="crit-bar-bg">
                  <div className="crit-bar-fill" style={{ width: `${Math.round((item.vehicleCount / maxCriticalCount) * 100)}%` }} />
                </div>
                <span className="crit-val">{item.vehicleCount} veh</span>
              </div>
            ))}
          </div>
        </div>

        <div className="analytics-card full-width">
          <div className="card-header">
            <div className="card-title"><i className="fas fa-chart-bar" />Directional Volume by Intersection</div>
            <select
              className="analytics-select"
              value={selectedName}
              onChange={(e) => setSelectedName(e.target.value)}
            >
              {INTERSECTION_NAMES.map(name => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
          <div className="chart-container-180">
            <Bar data={laneBarData} options={barOptions} />
          </div>
        </div>
      </div>
    </div>
  );
}
