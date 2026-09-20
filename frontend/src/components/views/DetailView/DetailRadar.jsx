import { Radar } from "react-chartjs-2";
import "./DetailRadar.css";

export default function DetailRadar({ intersection }) {
  const data = {
    labels: ["North", "East", "South", "West"],
    datasets: [
      {
        label: "Vehicles",
        data: intersection.lanes.map(l => l.vehicleCount),
        backgroundColor: "rgba(217,119,87, 0.2)",
        borderColor: "rgba(217,119,87, 0.9)",
        pointBackgroundColor: "#d97757",
        pointBorderColor: "#ffffff",
        borderWidth: 2,
        pointRadius: 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: "rgba(63,61,57, 0.5)" },
        grid: { color: "rgba(63,61,57, 0.4)" },
        pointLabels: { color: "#b5b1a4", font: { size: 10, family: "Inter" } },
        ticks: { display: false },
        beginAtZero: true,
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#1f1e1d",
        borderColor: "#3f3d39",
        borderWidth: 1,
        titleColor: "#f4f2ea",
        bodyColor: "#b5b1a4",
      }
    },
  };

  return (
    <div className="radar-panel">
      <div className="panel-title"><i className="fas fa-chart-area" />Lane Distribution</div>
      <div className="radar-chart-container">
        <Radar data={data} options={options} />
      </div>
    </div>
  );
}
