import { useState, useEffect, useRef } from "react";
import { VehicleCardGrid, VehicleCardModal } from "./VehicleCards";
import "./AnalysisPanels.css";

const STEPS = [
  "Split each second into 24 frames",
  "YOLOv8 + BoT-SORT tracking",
  "Sharpness + weather quality check",
  "Random Forest / decision-tree gate",
  "Restore, OCR and consensus vote",
];

const TRACK_STATUS = {
  CONFIRMED: { label: "Confirmed", tone: "ok" },
  BUFFERING: { label: "Buffering", tone: "warn" },
  SEARCHING: { label: "Reading", tone: "warn" },
  DEFERRED_LOW_FIDELITY: { label: "RF deferred", tone: "mute" },
  NO_PLATE: { label: "No plate", tone: "bad" },
};

export default function VideoAnalysisPanel() {
  const [file, setFile] = useState(null);
  const [cameraId, setCameraId] = useState("CAM_UPLOAD_1");
  const [maxSeconds, setMaxSeconds] = useState(30);
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);
  const [openCard, setOpenCard] = useState(null);
  const timer = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => () => clearInterval(timer.current), []);

  const running = job && (job.status === "queued" || job.status === "running");

  async function start() {
    setError(null);
    setJob(null);
    setStarting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("camera_id", cameraId);
      fd.append("max_seconds", String(maxSeconds));
      const res = await fetch("/api/webcam/analyze_video", { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Could not start the analysis");
      setJob({ status: "queued", progress: 0, stage: "Queued" });
      clearInterval(timer.current);
      timer.current = setInterval(() => poll(data.job_id), 1500);
    } catch (e) {
      setError(e.message || "Could not reach the analysis backend.");
    } finally {
      setStarting(false);
    }
  }

  async function poll(jobId) {
    try {
      const res = await fetch(`/api/webcam/video_poll/${jobId}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      setJob(data);
      if (data.status === "done" || data.status === "error") clearInterval(timer.current);
      if (data.status === "error") setError(data.error || "Video analysis failed");
    } catch (e) {
      clearInterval(timer.current);
      setError(e.message || "Lost contact with the analysis backend.");
    }
  }

  const p = job?.pipeline;
  const conditions = Object.entries(job?.conditions || {}).sort((a, b) => b[1] - a[1]);
  const tracks = job?.tracks || [];

  return (
    <div className="ap-panel">
      <div className="ap-top">
        <div className="ap-drop" onClick={() => inputRef.current?.click()}>
          <i className="fas fa-film" />
          <p>{file ? file.name : "Click to choose a video (mp4, avi, mov)"}</p>
          <input ref={inputRef} type="file" accept="video/*" hidden onChange={(e) => setFile(e.target.files[0] || null)} />
        </div>
        <div className="ap-side">
          <label className="ap-field">
            <span>Camera ID</span>
            <input value={cameraId} onChange={(e) => setCameraId(e.target.value)} maxLength={32} />
          </label>
          <label className="ap-field">
            <span>Analyze the first</span>
            <select value={maxSeconds} onChange={(e) => setMaxSeconds(Number(e.target.value))}>
              <option value={15}>15 seconds</option>
              <option value={30}>30 seconds</option>
              <option value={60}>60 seconds</option>
              <option value={120}>120 seconds</option>
            </select>
          </label>
          <button className="lw-btn lw-btn-primary" disabled={!file || running || starting} onClick={start}>
            <i className="fas fa-play" /> {running || starting ? "Processing…" : "Analyze video"}
          </button>
        </div>
      </div>

      <div className="ap-steps">
        {STEPS.map((s, i) => (
          <div key={s} className="ap-step"><b>{i + 1}</b> {s}</div>
        ))}
      </div>

      {error && <div className="lw-error"><i className="fas fa-triangle-exclamation" /> {error}</div>}

      {job && (
        <div className="ap-progress">
          <div className="ap-bar"><div className="ap-bar-fill" style={{ width: `${job.progress || 0}%` }} /></div>
          <span>{job.progress || 0}% · {job.stage}</span>
        </div>
      )}

      {job && (
        <div className="ap-video-grid">
          <div className="lw-card">
            <div className="lw-card-title">Latest analyzed second</div>
            {job.preview ? <img className="ap-annotated" src={job.preview} alt="Preview" /> : <div className="ap-empty">Waiting for the first second…</div>}
          </div>

          <div className="lw-card">
            <div className="lw-card-title">Pipeline totals{job.duration_s ? ` · ${job.duration_s}s video at ${job.fps} fps` : ""}</div>
            <div className="ap-stats">
              <div><b>{p?.frames_sent ?? 0}</b><span>Frames sent</span></div>
              <div><b>{p?.tracked ?? 0}</b><span>Tracked</span></div>
              <div><b>{p?.rf_accepted ?? 0}</b><span>RF accepted</span></div>
              <div><b>{p?.rf_deferred ?? 0}</b><span>RF deferred</span></div>
              <div><b>{p?.ocr_runs ?? 0}</b><span>OCR runs</span></div>
              <div><b>{tracks.length}</b><span>Vehicles</span></div>
            </div>
            <div className="lw-card-title ap-mt">Scene conditions seen (weather and optics)</div>
            <div className="ap-cond">
              {conditions.length ? conditions.map(([k, v]) => <span key={k} className="vc-chip vc-chip-warn">{k} · {v}</span>) : <span className="ap-empty-inline">None yet</span>}
            </div>
          </div>
        </div>
      )}

      {tracks.length > 0 && job?.status !== "done" && (
        <div className="lw-card">
          <div className="lw-card-title">Tracked vehicles (live)</div>
          <table className="lw-table">
            <thead><tr><th>ID</th><th>Plate</th><th>Type</th><th>Status</th><th>RF</th></tr></thead>
            <tbody>
              {tracks.map((t) => {
                const m = TRACK_STATUS[t.status] || TRACK_STATUS.SEARCHING;
                return (
                  <tr key={t.track_id}>
                    <td>#{t.track_id % 100000}</td>
                    <td>{t.plate || "—"}</td>
                    <td>{t.vehicle_type}</td>
                    <td><span className={`vc-chip vc-chip-${m.tone}`}>{m.label}</span></td>
                    <td>{t.rf_quality_score.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {job?.status === "done" && (
        <div className="ap-result">
          <div className="ap-result-head">
            <b>Vehicle cards</b>
            <span>{job.cards.length} vehicles in {job.elapsed_s}s</span>
            {!job.clip_available && <span className="vc-chip vc-chip-warn">CLIP model missing: attributes blank</span>}
          </div>
          <VehicleCardGrid cards={job.cards} onOpen={setOpenCard} />
        </div>
      )}

      {openCard && <VehicleCardModal card={openCard} onClose={() => setOpenCard(null)} />}
    </div>
  );
}
