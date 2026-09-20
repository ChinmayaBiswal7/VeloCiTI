import { useState, useEffect, useRef } from "react";
import { getInterpolatedDetections } from "../../../services/trafficVisionEngine";
import "./CCTVModal.css";

const CAMERA_FEEDS = {
  North: { video: "/videos/cam_angle_1.mp4", name: "North Arterial Express (CAM-01)" },
  East:  { video: "/videos/cam_angle_2.mp4", name: "East Junction Stream (CAM-02)" },
  South: { video: "/videos/road_traffic_1.mp4", name: "South Arterial Highway (CAM-03)" },
  West:  { video: "/videos/traffic_feed.mp4",  name: "West Emergency Corridor (CAM-04)" },
};

export default function CCTVModal({ intersection, initialDirection = "North", onClose }) {
  const [activeDir, setActiveDir] = useState(initialDirection);
  const [showAiBoxes, setShowAiBoxes] = useState(true);
  const [timeString, setTimeString] = useState("");
  const [activeDetections, setActiveDetections] = useState([]);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const reqAnimRef = useRef(null);

  const activeLane = intersection.lanes.find(l => l.direction === activeDir) || intersection.lanes[0];

  // 1. Clock timer
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeString(now.toLocaleTimeString("en-IN", { hour12: false }) + "." + String(now.getMilliseconds()).padStart(3, "0"));
    };
    updateTime();
    const id = setInterval(updateTime, 100);
    return () => clearInterval(id);
  }, []);

  // 2. High-Precision YOLOv8 / VisDrone & ANPR Vision Detection Loop
  useEffect(() => {
    let isRunning = true;

    const renderVisionFrame = () => {
      if (!isRunning) return;

      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (video && canvas) {
        const ctx = canvas.getContext("2d");
        const w = video.videoWidth || video.clientWidth || 800;
        const h = video.videoHeight || video.clientHeight || 440;
        canvas.width = w;
        canvas.height = h;

        ctx.clearRect(0, 0, w, h);

        if (showAiBoxes) {
          const currentTime = video.currentTime || 0;
          const detections = getInterpolatedDetections(activeDir, currentTime, w, h);
          setActiveDetections(detections);

          detections.forEach(det => {
            const [x, y, width, height] = det.bbox;
            const scorePct = Math.round(det.confidence * 100);
            const boxColor = det.color || "#e6926f";

            // Main Label: ID + Class + Speed + Plate
            const mainLabel = `[${det.id}] ${det.class} (${scorePct}%) | ${det.speed} km/h`;
            const plateLabel = `ANPR: ${det.plate}`;

            // 1. Semi-transparent fill
            ctx.fillStyle = boxColor === "#e6926f" ? "rgba(217,119,87, 0.09)" : boxColor === "#dba53a" ? "rgba(219,165,58, 0.09)" : boxColor === "#63a375" ? "rgba(99,163,117, 0.09)" : "rgba(217,119,87, 0.09)";
            ctx.fillRect(x, y, width, height);

            // 2. Thin bounding box
            ctx.strokeStyle = boxColor;
            ctx.lineWidth = 1.5;
            ctx.strokeRect(x, y, width, height);

            // 3. Tactical corner brackets
            const bracketSize = Math.min(16, width / 3, height / 3);
            ctx.lineWidth = 3.5;
            ctx.strokeStyle = boxColor;

            // Top-left
            ctx.beginPath();
            ctx.moveTo(x, y + bracketSize);
            ctx.lineTo(x, y);
            ctx.lineTo(x + bracketSize, y);
            ctx.stroke();

            // Top-right
            ctx.beginPath();
            ctx.moveTo(x + width - bracketSize, y);
            ctx.lineTo(x + width, y);
            ctx.lineTo(x + width, y + bracketSize);
            ctx.stroke();

            // Bottom-left
            ctx.beginPath();
            ctx.moveTo(x, y + height - bracketSize);
            ctx.lineTo(x, y + height);
            ctx.lineTo(x + bracketSize, y + height);
            ctx.stroke();

            // Bottom-right
            ctx.beginPath();
            ctx.moveTo(x + width - bracketSize, y + height);
            ctx.lineTo(x + width, y + height);
            ctx.lineTo(x + width, y + height - bracketSize);
            ctx.stroke();

            // 4. Center radar crosshair
            const cx = x + width / 2;
            const cy = y + height / 2;
            ctx.lineWidth = 1;
            ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
            ctx.beginPath();
            ctx.moveTo(cx - 5, cy);
            ctx.lineTo(cx + 5, cy);
            ctx.moveTo(cx, cy - 5);
            ctx.lineTo(cx, cy + 5);
            ctx.stroke();

            // 5. Header Label Badge (Category + Confidence + Speed)
            ctx.font = "bold 11px Inter, monospace";
            const textWidth = ctx.measureText(mainLabel).width;
            ctx.fillStyle = boxColor;
            ctx.fillRect(x, Math.max(0, y - 20), textWidth + 10, 20);

            ctx.fillStyle = "#000000";
            ctx.fillText(mainLabel, x + 5, Math.max(14, y - 5));

            // 6. Sub-badge for ANPR Number Plate
            if (det.plate && det.plate !== "CROSSWALK") {
              ctx.font = "bold 10px Inter, monospace";
              const plateWidth = ctx.measureText(plateLabel).width;
              ctx.fillStyle = "rgba(31,30,29, 0.9)";
              ctx.fillRect(x, Math.min(h - 18, y + height + 2), plateWidth + 8, 16);

              ctx.strokeStyle = boxColor;
              ctx.lineWidth = 1;
              ctx.strokeRect(x, Math.min(h - 18, y + height + 2), plateWidth + 8, 16);

              ctx.fillStyle = boxColor;
              ctx.fillText(plateLabel, x + 4, Math.min(h - 6, y + height + 14));
            }
          });
        } else {
          setActiveDetections([]);
        }
      }

      reqAnimRef.current = requestAnimationFrame(renderVisionFrame);
    };

    reqAnimRef.current = requestAnimationFrame(renderVisionFrame);

    return () => {
      isRunning = false;
      if (reqAnimRef.current) cancelAnimationFrame(reqAnimRef.current);
    };
  }, [showAiBoxes, activeDir]);

  const currentFeed = CAMERA_FEEDS[activeDir] || CAMERA_FEEDS.North;
  const camNumber = activeDir === "North" ? "CAM-01" : activeDir === "East" ? "CAM-02" : activeDir === "South" ? "CAM-03" : "CAM-04";

  return (
    <div className="cctv-modal-backdrop" onClick={onClose}>
      <div className="cctv-modal-box" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="cctv-header">
          <div className="cctv-header-title">
            <i className="fas fa-video" style={{ color: "#d97757" }} />
            <span>HQ LIVE CCTV STREAM &mdash; {intersection.name}</span>
            <div className="cctv-model-badge">
              <i className="fas fa-microchip" /> YOLOv8-TRAFFIC + ANPR OCR ENGINE
            </div>
            <div className="cctv-live-tag">
              <div className="cctv-live-dot" /> LIVE 1080P
            </div>
          </div>
          <button className="cctv-close-btn" onClick={onClose} title="Close feed">
            <i className="fas fa-times" />
          </button>
        </div>

        {/* Camera Selector Tabs (4 Distinct Feeds) */}
        <div className="cctv-cam-tabs">
          {["North", "East", "South", "West"].map(dir => (
            <button
              key={dir}
              className={`cctv-tab-btn ${activeDir === dir ? "active" : ""}`}
              onClick={() => setActiveDir(dir)}
            >
              <i className="fas fa-camera" />
              <span>{dir} ({dir === "North" ? "CAM-01" : dir === "East" ? "CAM-02" : dir === "South" ? "CAM-03" : "CAM-04"})</span>
            </button>
          ))}
        </div>

        {/* Video Stage + Real-Time YOLO Canvas Overlay */}
        <div className="cctv-video-stage">
          <video
            ref={videoRef}
            key={currentFeed.video}
            className="cctv-video-el"
            src={currentFeed.video}
            autoPlay
            loop
            muted
            playsInline
          />

          <canvas ref={canvasRef} className="cctv-canvas-overlay" />

          {/* OSD Top Bar */}
          <div className="cctv-osd-top">
            <div className="cctv-osd-badge">
              {camNumber} // {intersection.name.toUpperCase()} [{activeDir.toUpperCase()} - {currentFeed.name.toUpperCase()}]
            </div>
            <div className="cctv-osd-badge" style={{ color: "#e5534b" }}>
              REC &#9679; {timeString} IST
            </div>
          </div>

          {/* OSD Bottom Bar */}
          <div className="cctv-osd-bottom">
            <div className="cctv-osd-badge">
              LANE QUEUE: {activeLane.vehicleCount} VEHICLES | AVG VELOCITY: {activeLane.averageSpeed} KM/H | SIGNAL: {activeLane.light.toUpperCase()}
            </div>
            <div className="cctv-osd-badge" style={{ color: "#e6926f" }}>
              YOLOv8 + ANPR: {activeDetections.length} ACTIVE TARGETS LOCKED (&gt;90% OCR ACCURACY)
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="cctv-footer">
          <div className="cctv-footer-info">
            <span><strong>FPS:</strong> 30.00</span>
            <span><strong>Model:</strong> YOLOv8-Traffic (VisDrone + Indian Road Dataset)</span>
            <span>
              <strong>Signal:</strong>{" "}
              <strong style={{ color: activeLane.light === "green" ? "#63a375" : activeLane.light === "yellow" ? "#dba53a" : "#e5534b" }}>
                {activeLane.light.toUpperCase()}
              </strong>
            </span>
          </div>

          <div className="cctv-footer-actions">
            <button
              className={`cctv-action-btn ${showAiBoxes ? "active" : ""}`}
              onClick={() => setShowAiBoxes(!showAiBoxes)}
            >
              <i className="fas fa-draw-polygon" /> AI Detection Overlay: {showAiBoxes ? "ON" : "OFF"}
            </button>
            <button
              className="cctv-action-btn"
              onClick={() => alert(`Snapshot & ANPR Log captured for ${intersection.name} - ${activeDir} Corridor (${currentFeed.name}).`)}
            >
              <i className="fas fa-camera" /> Snapshot
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
