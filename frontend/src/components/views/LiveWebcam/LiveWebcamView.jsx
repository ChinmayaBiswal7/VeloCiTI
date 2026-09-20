import { useState, useRef, useEffect, useMemo } from "react";
import {
  Chart,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import ImageAnalysisPanel from "./ImageAnalysisPanel";
import VideoAnalysisPanel from "./VideoAnalysisPanel";
import "./LiveWebcamView.css";
import "./AnalysisPanels.css";

Chart.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const FRAMES_PER_BURST = 24;
const BURST_MS = 1000;
const MAX_FRAME_WIDTH = 960;

const VEHICLE_TYPE_COLORS = {
  Car: "#d97757",
  Motorbike: "#63a375",
  Bus: "#dba53a",
  Truck: "#e5534b",
};

const STATUS_META = {
  CONFIRMED: { label: "Confirmed", color: "#63a375" },
  BUFFERING: { label: "Buffering", color: "#dba53a" },
  SEARCHING: { label: "Reading", color: "#dba53a" },
  DEFERRED_LOW_FIDELITY: { label: "RF deferred", color: "#7c786c" },
  NO_PLATE: { label: "No plate", color: "#e5534b" },
};

const EMPTY_TOTALS = { bursts: 0, framesSent: 0, tracked: 0, rfAccepted: 0, rfDeferred: 0, ocrRuns: 0 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const MODES = [
  { id: "live", icon: "fa-video", label: "Live Camera" },
  { id: "image", icon: "fa-image", label: "Image Analysis" },
  { id: "video", icon: "fa-film", label: "Video Analysis" },
];

export default function LiveWebcamView() {
  const [mode, setMode] = useState("live");
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [isActive, setIsActive] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState("Camera standby");
  const [liveTracks, setLiveTracks] = useState([]);
  const [tracks, setTracks] = useState({});
  const [pipeline, setPipeline] = useState(null);
  const [totals, setTotals] = useState(EMPTY_TOTALS);
  const [sessionStart, setSessionStart] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const captureCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const runningRef = useRef(false);
  const lastFrameSizeRef = useRef({ w: MAX_FRAME_WIDTH, h: 540 });

  useEffect(() => {
    refreshDevices();
    return () => stopWebcam();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!sessionStart) return;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - sessionStart) / 1000)), 1000);
    return () => clearInterval(t);
  }, [sessionStart]);

  async function refreshDevices() {
    try {
      if (!navigator.mediaDevices?.enumerateDevices) return;
      const all = await navigator.mediaDevices.enumerateDevices();
      const cams = all.filter((d) => d.kind === "videoinput");
      setDevices(cams);
      setSelectedDeviceId((cur) => cur || cams[0]?.deviceId || "");
    } catch {
      // device labels just won't populate until camera permission is granted
    }
  }

  async function startWebcam() {
    setError(null);
    setIsStarting(true);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("This browser does not support camera access (getUserMedia).");
      }
      const size = { width: { ideal: 1280 }, height: { ideal: 720 } };
      const stream = await navigator.mediaDevices.getUserMedia({
        video: selectedDeviceId ? { deviceId: { exact: selectedDeviceId }, ...size } : size,
        audio: false,
      });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      await refreshDevices();
      setIsActive(true);
      setSessionStart(Date.now());
      runningRef.current = true;
      runLoop();
    } catch (e) {
      setError(e.message || "Could not access the camera. Check browser permissions.");
    } finally {
      setIsStarting(false);
    }
  }

  function stopWebcam() {
    runningRef.current = false;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setIsActive(false);
    setSessionStart(null);
    setLiveTracks([]);
    setStatusMsg("Camera standby");
  }

  // Phase 1: divide each second into 24 frames, downsampled to <=960px width
  async function captureBurst() {
    const video = videoRef.current;
    const canvas = captureCanvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;
    const vw = video.videoWidth || MAX_FRAME_WIDTH;
    const vh = video.videoHeight || 540;
    const scale = Math.min(1, MAX_FRAME_WIDTH / vw);
    canvas.width = Math.round(vw * scale);
    canvas.height = Math.round(vh * scale);
    const ctx = canvas.getContext("2d");
    const blobs = [];
    const t0 = performance.now();
    for (let i = 0; i < FRAMES_PER_BURST; i++) {
      const wait = t0 + i * (BURST_MS / FRAMES_PER_BURST) - performance.now();
      if (wait > 0) await sleep(wait);
      if (!runningRef.current) return null;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      blobs.push(new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.75)));
    }
    return (await Promise.all(blobs)).filter(Boolean);
  }

  async function runLoop() {
    while (runningRef.current) {
      setStatusMsg(`Capturing ${FRAMES_PER_BURST}-frame burst (1s)…`);
      const blobs = await captureBurst();
      if (!blobs || !runningRef.current) break;

      setStatusMsg("Analyzing: track → quality gate → OCR → voting…");
      try {
        const fd = new FormData();
        blobs.forEach((b, i) => fd.append("frames", b, `f${i}.jpg`));
        const res = await fetch("/api/webcam/analyze_burst", { method: "POST", body: fd });
        const data = await res.json();
        if (!runningRef.current) break;

        if (!data.success) {
          setError(data.error || "Analysis failed on the server.");
          await sleep(1500);
          continue;
        }
        setError(null);
        applyBurstResult(data);
      } catch {
        setError("Cannot reach the analysis backend (is the Python server running on port 5000?).");
        await sleep(2000);
      }
    }
  }

  function applyBurstResult(data) {
    const p = data.pipeline;
    lastFrameSizeRef.current = { w: data.frame_width, h: data.frame_height };
    setPipeline(p);
    setLiveTracks(data.tracks);
    setTotals((t) => ({
      bursts: t.bursts + 1,
      framesSent: t.framesSent + p.frames_received,
      tracked: t.tracked + p.frames_tracked,
      rfAccepted: t.rfAccepted + p.rf_accepted,
      rfDeferred: t.rfDeferred + p.rf_deferred,
      ocrRuns: t.ocrRuns + p.ocr_runs,
    }));
    setTracks((prev) => {
      const next = { ...prev };
      for (const t of data.tracks) next[t.track_id] = t;
      return next;
    });
    setStatusMsg(`Live — ${p.elapsed_ms} ms per ${p.frames_received}-frame burst`);
  }

  // Draw the latest burst's tracked vehicles, scaled from analyzed-frame size to displayed size
  useEffect(() => {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay) return;
    const dw = video.clientWidth;
    const dh = video.clientHeight;
    if (!dw || !dh) return;
    overlay.width = dw;
    overlay.height = dh;
    const ctx = overlay.getContext("2d");
    ctx.clearRect(0, 0, dw, dh);

    const { w: fw, h: fh } = lastFrameSizeRef.current;
    for (const t of liveTracks) {
      if (!t.bbox) continue;
      const [x1, y1, x2, y2] = t.bbox;
      const bx = (x1 / fw) * dw, by = (y1 / fh) * dh;
      const bw = ((x2 - x1) / fw) * dw, bh = ((y2 - y1) / fh) * dh;
      const color = (STATUS_META[t.status] || STATUS_META.SEARCHING).color;
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, bw, bh);
      const label = `#${t.track_id % 100000} ${t.vehicle_type} · ${t.plate || (STATUS_META[t.status] || {}).label}`;
      ctx.font = "600 12px 'Segoe UI', sans-serif";
      const textW = ctx.measureText(label).width;
      ctx.fillStyle = color;
      ctx.fillRect(bx, Math.max(0, by - 18), textW + 10, 18);
      ctx.fillStyle = "#1f1e1d";
      ctx.fillText(label, bx + 5, Math.max(12, by - 5));
    }
  }, [liveTracks]);

  async function resetSession() {
    setTracks({});
    setLiveTracks([]);
    setPipeline(null);
    setTotals(EMPTY_TOTALS);
    if (isActive) setSessionStart(Date.now());
    try {
      await fetch("/api/webcam/reset", { method: "POST" });
    } catch {
      // backend offline — local state is already cleared
    }
  }

  const trackList = useMemo(() => Object.values(tracks).sort((a, b) => b.timestamp.localeCompare(a.timestamp)), [tracks]);
  const countsByType = useMemo(() => {
    const c = {};
    for (const t of trackList) c[t.vehicle_type] = (c[t.vehicle_type] || 0) + 1;
    return c;
  }, [trackList]);
  const confirmed = trackList.filter((t) => t.status === "CONFIRMED").length;
  const elapsedLabel = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;

  const chartData = {
    labels: Object.keys(countsByType),
    datasets: [
      {
        label: "Unique vehicles",
        data: Object.values(countsByType),
        backgroundColor: Object.keys(countsByType).map((t) => VEHICLE_TYPE_COLORS[t] || "#7c786c"),
        borderRadius: 4,
      },
    ],
  };
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { display: false }, ticks: { color: "#b5b1a4", font: { size: 10 } } },
      y: { grid: { color: "rgba(63,61,57,0.3)" }, ticks: { color: "#b5b1a4", font: { size: 10 }, precision: 0 }, beginAtZero: true },
    },
    plugins: { legend: { display: false } },
  };

  const gated = totals.rfAccepted + totals.rfDeferred;
  const stages = [
    { n: 1, name: "Frame ingestion", detail: `${FRAMES_PER_BURST} frames/sec, ≤${MAX_FRAME_WIDTH}px`, value: totals.framesSent, max: totals.framesSent },
    { n: 2, name: "YOLOv8 + BoT-SORT tracking", detail: `${trackList.length} unique vehicles`, value: totals.tracked, max: totals.framesSent },
    { n: 3, name: "IQA + Random Forest gate", detail: `${totals.rfAccepted} accepted / ${totals.rfDeferred} deferred (≥0.42)`, value: totals.rfAccepted, max: gated },
    { n: 4, name: "Restoration + EasyOCR", detail: `${totals.ocrRuns} OCR runs (best frames only)`, value: totals.ocrRuns, max: Math.max(totals.rfAccepted, 1) },
    { n: 5, name: "Consensus voting + RTO syntax", detail: `${confirmed} plates confirmed`, value: confirmed, max: Math.max(trackList.length, 1) },
  ];

  function changeMode(next) {
    if (next !== "live") stopWebcam();
    setMode(next);
  }

  return (
    <div className="lw-view">
      <div className="lw-tabs">
        {MODES.map((m) => (
          <button key={m.id} className={`lw-tab ${mode === m.id ? "active" : ""}`} onClick={() => changeMode(m.id)}>
            <i className={`fas ${m.icon}`} /> {m.label}
          </button>
        ))}
      </div>
      {mode === "image" && <ImageAnalysisPanel />}
      {mode === "video" && <VideoAnalysisPanel />}
      {mode === "live" && (
      <div className="lw-main">
        <div className="lw-video-card">
          <div className="lw-video-head">
            <div className="lw-video-title">
              <i className="fas fa-video" /> Live Webcam Feed
            </div>
            <div className={`lw-status-pill ${isActive ? "on" : "off"}`}>
              <span className="lw-dot" /> {statusMsg}
            </div>
          </div>

          <div className="lw-video-frame">
            <video ref={videoRef} className="lw-video" muted playsInline />
            <canvas ref={overlayRef} className="lw-overlay" />
            {!isActive && (
              <div className="lw-placeholder">
                <i className="fas fa-camera" />
                <p>Select a camera and click Start. Every second is split into 24 frames for multi-frame ANPR.</p>
              </div>
            )}
          </div>
          <canvas ref={captureCanvasRef} style={{ display: "none" }} />

          <div className="lw-controls">
            <select
              className="lw-select"
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              disabled={isActive}
            >
              {devices.length === 0 && <option value="">No camera detected</option>}
              {devices.map((d, i) => (
                <option key={d.deviceId || i} value={d.deviceId}>
                  {d.label || `Camera ${i + 1}`}
                </option>
              ))}
            </select>

            {!isActive ? (
              <button className="lw-btn lw-btn-primary" onClick={startWebcam} disabled={isStarting}>
                <i className="fas fa-play" /> {isStarting ? "Starting…" : "Start Webcam"}
              </button>
            ) : (
              <button className="lw-btn lw-btn-danger" onClick={stopWebcam}>
                <i className="fas fa-stop" /> Stop Webcam
              </button>
            )}

            <button className="lw-btn" onClick={resetSession} title="Clear session analytics and tracker state">
              <i className="fas fa-rotate-left" /> Reset
            </button>
          </div>

          {error && (
            <div className="lw-error">
              <i className="fas fa-triangle-exclamation" /> {error}
            </div>
          )}

          <div className="lw-card lw-pipeline">
            <div className="lw-card-title">
              Multi-frame ANPR pipeline (session totals{pipeline ? ` · last burst ${pipeline.elapsed_ms} ms` : ""})
            </div>
            {stages.map((s) => (
              <div className="lw-stage" key={s.n}>
                <div className="lw-stage-head">
                  <span className="lw-stage-name"><b>{s.n}</b> {s.name}</span>
                  <span className="lw-stage-detail">{s.detail}</span>
                </div>
                <div className="lw-stage-bar">
                  <div className="lw-stage-fill" style={{ width: `${s.max ? Math.min(100, (s.value / s.max) * 100) : 0}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lw-analytics">
          <div className="lw-stats-row">
            <div className="lw-stat">
              <span className="lw-stat-val">{trackList.length}</span>
              <span className="lw-stat-label">Vehicles Tracked</span>
            </div>
            <div className="lw-stat">
              <span className="lw-stat-val">{confirmed}</span>
              <span className="lw-stat-label">Plates Confirmed</span>
            </div>
            <div className="lw-stat">
              <span className="lw-stat-val">{totals.bursts}</span>
              <span className="lw-stat-label">Bursts (×{FRAMES_PER_BURST})</span>
            </div>
            <div className="lw-stat">
              <span className="lw-stat-val">{elapsedLabel}</span>
              <span className="lw-stat-label">Session Time</span>
            </div>
          </div>

          <div className="lw-card">
            <div className="lw-card-title">Vehicle Type Breakdown</div>
            <div className="lw-chart-box">
              {Object.keys(countsByType).length ? (
                <Bar data={chartData} options={chartOptions} />
              ) : (
                <div className="lw-empty">No vehicles tracked yet</div>
              )}
            </div>
          </div>

          <div className="lw-card lw-card-grow">
            <div className="lw-card-title">Tracked Vehicles</div>
            <div className="lw-table-wrap">
              {trackList.length === 0 ? (
                <div className="lw-empty">Vehicles appear here as they are tracked and read</div>
              ) : (
                <table className="lw-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Plate</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>RF</th>
                      <th>Conf.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trackList.map((t) => {
                      const meta = STATUS_META[t.status] || STATUS_META.SEARCHING;
                      return (
                        <tr key={t.track_id} className={t.violation !== "NONE" ? "lw-row-alert" : ""}>
                          <td>#{t.track_id % 100000}</td>
                          <td>{t.plate || "—"}</td>
                          <td>{t.vehicle_type}</td>
                          <td><span className="lw-chip" style={{ color: meta.color, borderColor: meta.color }}>{meta.label}</span></td>
                          <td>{t.rf_quality_score.toFixed(2)}</td>
                          <td>{t.plate ? `${Math.round(t.confidence * 100)}%` : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
