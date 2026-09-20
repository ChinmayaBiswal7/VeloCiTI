import { useState, useEffect, useMemo, useRef } from "react";
import { VehicleCardGrid, VehicleCardModal } from "./VehicleCards";
import "./AnalysisPanels.css";

export default function ImageAnalysisPanel() {
  const [files, setFiles] = useState([]);
  const [cameraId, setCameraId] = useState("CAM_UPLOAD_1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);
  const [clipAvailable, setClipAvailable] = useState(true);
  const [openCard, setOpenCard] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  function addFiles(list) {
    const imgs = Array.from(list).filter((f) => f.type.startsWith("image/"));
    if (imgs.length) setFiles(imgs.slice(0, 8));
  }

  async function analyze() {
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      fd.append("camera_id", cameraId);
      const res = await fetch("/api/webcam/analyze_image", { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Analysis failed");
      setResults(data.results);
      setClipAvailable(data.clip_available);
      const all = data.results.flatMap((r) => r.cards || []);
      if (all.length === 1) setOpenCard(all[0]);
    } catch (e) {
      setError(e.message || "Could not reach the analysis backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ap-panel">
      <div className="ap-top">
        <div
          className={`ap-drop ${dragging ? "drag" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
        >
          <i className="fas fa-cloud-arrow-up" />
          <p>Drop vehicle images here or click to choose (up to 8)</p>
          <input ref={inputRef} type="file" accept="image/*" multiple hidden onChange={(e) => addFiles(e.target.files)} />
        </div>

        <div className="ap-side">
          <label className="ap-field">
            <span>Camera ID</span>
            <input value={cameraId} onChange={(e) => setCameraId(e.target.value)} maxLength={32} />
          </label>
          <p className="ap-hint">
            Use a different camera ID for each upload to see the same unplated vehicle re-identified across cameras.
          </p>
          <button className="lw-btn lw-btn-primary" disabled={!files.length || loading} onClick={analyze}>
            <i className="fas fa-magnifying-glass" /> {loading ? "Analyzing…" : `Analyze ${files.length || ""} image${files.length === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>

      {files.length > 0 && (
        <div className="ap-thumbs">
          {files.map((f, i) => (
            <img key={f.name + i} src={previews[i]} alt={f.name} title={f.name} />
          ))}
        </div>
      )}

      {loading && <div className="ap-note">Detecting vehicles, reading plates and profiling. The first image loads the models and can take a minute.</div>}
      {error && <div className="lw-error"><i className="fas fa-triangle-exclamation" /> {error}</div>}
      {results.length > 0 && !clipAvailable && (
        <div className="ap-note">The CLIP attribute model is not installed, so make/model, damage and clothing are blank.</div>
      )}

      {results.map((r) => (
        <div className="ap-result" key={r.filename}>
          {r.error ? (
            <div className="lw-error">{r.filename}: {r.error}</div>
          ) : (
            <>
              <div className="ap-result-head">
                <b>{r.filename}</b>
                <span>{r.summary.vehicles} vehicles</span>
                <span className="vc-chip vc-chip-ok">{r.summary.plated} plated</span>
                <span className="vc-chip vc-chip-bad">{r.summary.no_plate + r.summary.unreadable} no plate</span>
                <span>{r.summary.persons_detected} people in scene</span>
              </div>
              <div className="ap-result-body">
                <img className="ap-annotated" src={r.annotated} alt="Annotated" />
                <VehicleCardGrid cards={r.cards} onOpen={setOpenCard} />
              </div>
            </>
          )}
        </div>
      ))}

      {openCard && <VehicleCardModal card={openCard} onClose={() => setOpenCard(null)} />}
    </div>
  );
}
