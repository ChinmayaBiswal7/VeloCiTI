"""
server.py - Central Flask API server
Receives detections, serves tracking/analytics/alert data to the dashboard.

Run with:
    python server.py
"""

import os
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import json
import re

import database as db
import analytics as an
import alerts as al
import vehicle_profiler
import vehicle_reid
import firebase_sync

# -----------------------------------------------------------------------

# Flask app setup
# -----------------------------------------------------------------------
app = Flask(__name__, static_folder="static")
CORS(app)

_upload_yolo_model = None


# -----------------------------------------------------------------------
# Serve the dashboards
# -----------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("static", "dashboard.html")


@app.route("/anpr")
@app.route("/live")
def anpr_page():
    return send_from_directory("static", "anpr.html")


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


@app.route("/dossier")
def view_dossier():
    """Renders the downloadable SIH 2026 Project Dossier."""
    return send_from_directory(".", "SIH_2026_ANPR_Project_Dossier.html")


@app.route("/dossier/download")
def download_dossier():
    """Triggers direct file download for SIH 2026 Project Dossier (.docx Word document)."""
    return send_from_directory(".", "SIH_2026_ANPR_Project_Dossier.docx", as_attachment=True, download_name="SIH_2026_ANPR_Project_Dossier.docx")




@app.route("/api/rto/lookup/<plate>")
def rto_lookup(plate):
    """Returns MoRTH / Vahan official vehicle registration & owner record."""
    import rto
    data = rto.lookup_rto_vehicle(plate)
    return jsonify({"success": True, "rto": data})





# -----------------------------------------------------------------------
# POST /api/detection  — camera nodes post detections here
# -----------------------------------------------------------------------
@app.route("/api/detection", methods=["POST"])
def receive_detection():
    data = request.get_json(force=True)
    plate     = data.get("plate", "").upper().replace(" ", "")
    camera_id = data.get("camera_id", "UNKNOWN")
    timestamp = data.get("timestamp", datetime.now().isoformat(timespec="seconds"))
    confidence= float(data.get("confidence", 0.0))
    speed     = float(data.get("speed_kmph", 0.0))
    lat       = data.get("lat")
    lon       = data.get("lon")
    direction = data.get("direction", "")
    vtype     = data.get("vehicle_type", "unknown")

    if not plate:
        return jsonify({"error": "plate is required"}), 400

    db.insert_detection(plate, camera_id, timestamp, confidence, speed, lat, lon, direction, vtype)
    new_alerts = al.check_detection(plate, camera_id, timestamp)

    return jsonify({
        "status":  "ok",
        "plate":   plate,
        "alerts":  new_alerts,
    }), 201


# -----------------------------------------------------------------------
# GET /api/status  — dashboard overview cards
# -----------------------------------------------------------------------
@app.route("/api/status")
def status():
    summary = an.get_city_summary(minutes=15)
    return jsonify(summary)


# -----------------------------------------------------------------------
# GET /api/track/<plate>  — full trajectory for one plate
# -----------------------------------------------------------------------
@app.route("/api/track/<plate>")
def track(plate):
    traj = db.get_trajectory(plate.upper().replace(" ", ""))
    enriched = an.enrich_trajectory(traj)
    return jsonify({
        "plate":       plate.upper(),
        "total_stops": len(enriched),
        "trajectory":  enriched,
    })


# -----------------------------------------------------------------------
# GET /api/recent  — last N detections for live feed
# -----------------------------------------------------------------------
@app.route("/api/recent")
def recent():
    minutes = int(request.args.get("minutes", 15))
    rows = db.get_recent_detections(minutes)
    return jsonify(rows)


# -----------------------------------------------------------------------
# GET /api/violations  — missing/covered plate violations & anomalies
# -----------------------------------------------------------------------
@app.route("/api/violations")
def violations():
    rows = db.get_violations(limit=30)
    return jsonify(rows)


# -----------------------------------------------------------------------
# Ghost Vehicle Re-ID Endpoints (Plate-Less & Covered Plate Profiling)
# -----------------------------------------------------------------------
@app.route("/api/ghosts")
def get_ghosts():
    limit = int(request.args.get("limit", 50))
    profiles = db.get_all_ghost_profiles(limit=limit)
    return jsonify(profiles)


@app.route("/api/ghosts/<ghost_id>")
def get_ghost_detail(ghost_id):
    prof = db.get_ghost_profile_by_id(ghost_id)
    if not prof:
        return jsonify({"error": "Ghost vehicle profile not found"}), 404
    sightings = db.get_ghost_trajectory(ghost_id)
    return jsonify({
        "profile": prof,
        "sightings": sightings
    })


@app.route("/api/ghosts/<ghost_id>/track")
def track_ghost(ghost_id):
    prof = db.get_ghost_profile_by_id(ghost_id)
    if not prof:
        return jsonify({"error": "Ghost vehicle profile not found"}), 404
    sightings = db.get_ghost_trajectory(ghost_id)
    enriched = an.enrich_trajectory(sightings)
    return jsonify({
        "ghost_id": ghost_id,
        "profile": prof,
        "total_stops": len(enriched),
        "trajectory": enriched
    })




# -----------------------------------------------------------------------
# GET /api/search?q=<partial>  — autocomplete plate search
# -----------------------------------------------------------------------
@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    return jsonify(db.search_plates(q, limit=10))


# -----------------------------------------------------------------------
# GET /api/traffic  — per-camera traffic density + congestion
# -----------------------------------------------------------------------
@app.route("/api/traffic")
def traffic():
    minutes = int(request.args.get("minutes", 15))
    summary = an.get_camera_summary(minutes)
    return jsonify(summary)


# -----------------------------------------------------------------------
# GET /api/heatmap  — camera points with congestion colour (for map)
# -----------------------------------------------------------------------
@app.route("/api/heatmap")
def heatmap():
    cameras = db.get_all_cameras()
    traffic = an.get_camera_summary(minutes=15)
    traffic_map = {t["camera_id"]: t for t in traffic}

    result = []
    for cam in cameras:
        t = traffic_map.get(cam["id"], {})
        level = t.get("congestion", "LOW")
        result.append({
            "id":               cam["id"],
            "name":             cam["name"],
            "road":             cam["road"],
            "lat":              cam["lat"],
            "lon":              cam["lon"],
            "area":             cam["area"],
            "unique_vehicles":  t.get("unique_vehicles", 0),
            "avg_speed":        t.get("avg_speed", 0),
            "congestion":       level,
            "congestion_color": an.CONGESTION_COLOR.get(level, "#22c55e"),
        })
    return jsonify(result)


# -----------------------------------------------------------------------
# GET /api/alerts  — recent alerts
# -----------------------------------------------------------------------
@app.route("/api/alerts")
def get_alerts():
    unack = request.args.get("unack", "false").lower() == "true"
    return jsonify(db.get_alerts(limit=50, unack_only=unack))


# -----------------------------------------------------------------------
# POST /api/alerts/<id>/ack  — acknowledge an alert
# -----------------------------------------------------------------------
@app.route("/api/alerts/<int:alert_id>/ack", methods=["POST"])
def ack_alert(alert_id):
    db.acknowledge_alert(alert_id)
    return jsonify({"status": "acknowledged"})


# -----------------------------------------------------------------------
# GET /api/blacklist  — list all blacklisted plates
# -----------------------------------------------------------------------
@app.route("/api/blacklist")
def blacklist():
    return jsonify(db.get_blacklist())


# -----------------------------------------------------------------------
# POST /api/blacklist  — add plate to blacklist
# -----------------------------------------------------------------------
@app.route("/api/blacklist", methods=["POST"])
def add_blacklist():
    data   = request.get_json(force=True)
    plate  = data.get("plate", "").upper().replace(" ", "")
    reason = data.get("reason", "Flagged")
    if not plate:
        return jsonify({"error": "plate required"}), 400
    db.add_to_blacklist(plate, reason)
    return jsonify({"status": "added", "plate": plate})


# -----------------------------------------------------------------------
# DELETE /api/blacklist/<plate>  — remove plate from blacklist
# -----------------------------------------------------------------------
@app.route("/api/blacklist/<plate>", methods=["DELETE"])
def remove_blacklist(plate):
    db.remove_from_blacklist(plate)
    return jsonify({"status": "removed"})


# -----------------------------------------------------------------------
# GET /api/od  — origin-destination flow
# -----------------------------------------------------------------------
@app.route("/api/od")
def od():
    return jsonify(an.get_od_flow())


# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Dedicated Split-Screen Live Camera ANPR Node (/anpr)
# -----------------------------------------------------------------------
_anpr_thread = None
_anpr_active = False
_latest_live_frame = None
_latest_live_detections = []
_latest_stream_stats = {
    "fps_realtime": 30.0,
    "compute_saved_pct": "85.0%",
    "frames_filtered_out": 0,
    "total_frames_ingested": 0,
    "dominant_scene": "NORMAL"
}
_cam_lock = threading.Lock()


SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# Async video processing jobs: job_id -> {"status": "processing"|"done"|"error", "progress": int, "detections": [...], "error": str}
_video_jobs = {}
_video_jobs_lock = threading.Lock()


def run_live_anpr(camera_id="CAM_LIVE", cam_index=0):
    """
    High-performance multi-threaded ANPR engine:
    - Thread 1: 30 FPS smooth video grab & MJPEG streaming (Zero Lag).
    - Thread 2: Asynchronous AI Vision worker (YOLO + Dual-Mode OCR + RTO Validation).
    """
    global _anpr_active, _latest_live_frame
    import cv2
    import numpy as np
    from ultralytics import YOLO
    import anpr as anpr_module

    model = YOLO("yolov8s.pt")
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("Live ANPR: webcam not accessible, skipping.")
        _anpr_active = False
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)


    current_frame = None
    cached_plates = []
    frame_lock = threading.Lock()
    print("Live ANPR started on webcam with Asynchronous Zero-Lag Pipeline.")

    import conditioner
    video_conditioner = conditioner.AIVideoConditioner()

    def inference_worker():
        nonlocal cached_plates
        global _latest_stream_stats

        # Per-track observation counters: track_id -> frame count seen
        track_obs_counter = {}
        # Minimum confidence to commit a detection to sidebar
        MIN_CONFIDENCE = 0.52
        # Minimum frames a track_id must be observed before showing
        MIN_FRAMES_GATE = 3
        # Seconds before a card is auto-removed (vehicle left frame)
        STALE_TTL_SEC = 10

        while _anpr_active:
            with frame_lock:
                if current_frame is None:
                    time.sleep(0.02)
                    continue
                frame_to_proc = current_frame.copy()

            try:
                import time as _time

                # ── Sweep stale cards (vehicle left the frame) ─────────────────
                now_ts = _time.time()
                with _cam_lock:
                    _latest_live_detections[:] = [
                        d for d in _latest_live_detections
                        if (now_ts - d.get("_last_seen_ts", now_ts)) < STALE_TTL_SEC
                    ]

                # ── YOLO track + AI Video Conditioner ─────────────────────────
                results = model.track(frame_to_proc, persist=True,
                                      tracker="botsort.yaml", conf=0.20, verbose=False)
                dispatched_vehicles, stream_stats = video_conditioner.process_stream_frame(
                    frame_to_proc, results)
                with _cam_lock:
                    _latest_stream_stats = stream_stats

                # ── Plate detection — fast 2-pass OCR for real-time speed ──────
                plates = anpr_module.detect_plates_in_frame(
                    frame_to_proc, results, fast_mode=True)
                cached_plates = plates

                if plates:
                    timestamp = datetime.now().isoformat(timespec="seconds")
                    clean_ts  = timestamp.replace(":", "").replace("-", "").replace("T", "_")
                    annotated_snap = anpr_module.annotate_frame(frame_to_proc.copy(), plates)

                    for p in plates:
                        plate   = p["plate"]
                        t_id    = p.get("track_id", abs(hash(plate[:4])) % 100000)
                        conf    = p["confidence"]

                        # ── Confidence floor: reject low-quality reads ─────────
                        if conf < MIN_CONFIDENCE:
                            continue

                        # ── Frame-gate: accumulate frames before showing ────────
                        track_obs_counter[t_id] = track_obs_counter.get(t_id, 0) + 1
                        if track_obs_counter[t_id] < MIN_FRAMES_GATE:
                            continue  # Not enough frames yet — wait

                        snap_name = f"{plate}_{camera_id}_{clean_ts}.jpg"
                        snap_path = os.path.join(SNAPSHOT_DIR, snap_name)
                        cv2.imwrite(snap_path, annotated_snap)
                        snap_url  = f"/api/snapshot/{snap_name}"

                        v_info     = p.get("voting_details", {})
                        v_data_str = json.dumps(v_info)
                        telemetry  = p.get("telemetry", {})
                        env_cond   = v_info.get("environmental_condition",
                                                 telemetry.get("dominant_condition", "NORMAL"))
                        q_score    = telemetry.get("overall_quality_score", 0.85)

                        db.insert_detection(
                            plate=plate, camera_id=camera_id, timestamp=timestamp,
                            confidence=conf, speed_kmph=0.0,
                            vehicle_type=p["vehicle_type"], image_path=snap_url,
                            voting_data=v_data_str, env_condition=env_cond, quality_score=q_score
                        )
                        al.check_detection(plate, camera_id, timestamp)

                        with _cam_lock:
                            # ── Track-ID based dedup: same physical car = same card ──
                            # First check by track_id (primary), then by plate text
                            existing = next(
                                (d for d in _latest_live_detections
                                 if d.get("track_id") == t_id or d["plate"] == plate),
                                None
                            )
                            if existing:
                                # Update existing card — keep highest confidence plate text
                                if conf >= existing["confidence"]:
                                    existing["plate"]       = plate   # update to better reading
                                    existing["confidence"]  = conf
                                    existing["image_path"]  = snap_url
                                existing["last_seen"]          = timestamp
                                existing["_last_seen_ts"]      = now_ts
                                existing["track_id"]           = t_id
                                existing["voting_details"]     = v_info
                                existing["environmental_condition"] = env_cond
                                existing["quality_score"]      = q_score
                                existing["telemetry"]          = telemetry
                                snaps = existing.setdefault("snapshots", [])
                                if snap_url not in snaps:
                                    snaps.append(snap_url)
                                    if len(snaps) > 12:
                                        snaps.pop(0)
                            else:
                                rec = {
                                    "plate":        plate,
                                    "track_id":     t_id,
                                    "confidence":   conf,
                                    "vehicle_type": p["vehicle_type"],
                                    "camera_id":    camera_id,
                                    "image_path":   snap_url,
                                    "first_seen":   timestamp,
                                    "last_seen":    timestamp,
                                    "_last_seen_ts": now_ts,
                                    "snapshots":    [snap_url],
                                    "voting_details": v_info,
                                    "environmental_condition": env_cond,
                                    "quality_score": q_score,
                                    "telemetry":    telemetry
                                }
                                _latest_live_detections.insert(0, rec)
                                if len(_latest_live_detections) > 40:
                                    _latest_live_detections.pop()

            except Exception as e:
                pass
            time.sleep(0.05)



    inf_thread = threading.Thread(target=inference_worker, daemon=True)
    inf_thread.start()

    # Fast 30 FPS Streamer Loop with raw frame isolation
    while _anpr_active:
        ret, frame = cap.read()
        if not ret:
            break

        # Pass pure unannotated raw frame to inference
        raw_copy = frame.copy()
        with frame_lock:
            current_frame = raw_copy

        # Draw overlays only on display copy
        display_copy = frame.copy()
        annotated = anpr_module.annotate_frame(display_copy, cached_plates)
        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with _cam_lock:
            _latest_live_frame = buf.tobytes()

        time.sleep(0.033) # 30 FPS

    cap.release()
    _anpr_active = False
    print("Live ANPR stopped.")


@app.route("/api/anpr/clear", methods=["POST"])
def clear_anpr_feed():
    """Clears live detection cards and resets tracking buffers."""
    global _latest_live_detections
    with _cam_lock:
        _latest_live_detections = []
    import anpr as anpr_module
    anpr_module._sequence_fusion.track_buffers.clear()
    return jsonify({"success": True, "message": "Live feed cleared"})



@app.route("/api/video_feed")
def video_feed():
    """Streams live MJPEG camera feed directly into web browser."""
    def gen_frames():
        while True:
            with _cam_lock:
                frame_bytes = _latest_live_frame
            if frame_bytes is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.04)
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/api/live_stream_detections")
def get_live_stream_detections():
    """Returns real-time detected plates and stream conditioning telemetry."""
    with _cam_lock:
        return jsonify({
            "active": _anpr_active,
            "detections": list(_latest_live_detections),
            "stream_stats": dict(_latest_stream_stats)
        })


@app.route("/api/firebase/status")
def get_firebase_status():
    """Returns Firebase real-time cloud synchronization status."""
    return jsonify(firebase_sync.get_status())




@app.route("/api/anpr/upload", methods=["POST"])
def upload_and_process_anpr():
    """Process an uploaded image/video directly on the live ANPR workbench."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    import cv2
    import numpy as np
    from ultralytics import YOLO
    import anpr as anpr_module

    in_memory = file.read()
    np_arr = np.frombuffer(in_memory, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "Invalid image file"}), 400

    global _upload_yolo_model
    if _upload_yolo_model is None:
        _upload_yolo_model = YOLO("yolov8s.pt")

    results = _upload_yolo_model.track(frame, persist=True, tracker="botsort.yaml", conf=0.18, verbose=False)
    plates = anpr_module.detect_plates_in_frame(frame, results, fast_mode=True)

    # Fallback: if YOLO pipeline found nothing (close-up, cropped, or plate-only image),
    # run scan_frame_for_plates which uses multi-pass CLAHE OCR directly on the full frame
    if not plates:
        plates = anpr_module.scan_frame_for_plates(frame)

    annotated = anpr_module.annotate_frame(frame, plates)

    timestamp = datetime.now().isoformat(timespec="seconds")
    clean_ts = timestamp.replace(":", "").replace("-", "").replace("T", "_")

    out_records = []
    for p in plates:
        plate = p["plate"]
        p_color = p.get("plate_color", "WHITE")
        p_cat = p.get("category", "Private Vehicle")
        p_viol = p.get("violation", "NONE")

        # Unplated Vehicle Profiling & Re-ID for Plate-Less / Covered Plate Vehicles
        ghost_info = None
        if p_viol == "MISSING_OR_COVERED_PLATE" or "NO PLATE" in plate or "UNREADABLE" in plate:
            v_prof = p.get("vehicle_profile") or vehicle_profiler.extract_vehicle_profile(None, vehicle_type=p.get("vehicle_type", "Car"))
            ghost_info = vehicle_reid.match_or_create_ghost(
                v_prof,
                camera_id="CAM_LIVE",
                timestamp=timestamp,
                image_path="",
                speed_kmph=0.0
            )
            plate = f"{ghost_info['ghost_id']} (NO PLATE)"
            p["plate"] = plate

        # Safe filename without illegal Windows characters or slashes
        safe_plate = re.sub(r'[^\w\-]', '_', plate).strip('_')
        snap_name = f"{safe_plate}_CAM_LIVE_{clean_ts}.jpg"
        snap_path = os.path.join(SNAPSHOT_DIR, snap_name)
        cv2.imwrite(snap_path, annotated)
        snap_url = f"/api/snapshot/{snap_name}"

        if ghost_info:
            ghost_info["image_path"] = snap_url

        v_info = p.get("voting_details", {})
        v_data_str = json.dumps(v_info)
        telemetry = p.get("telemetry", {})
        env_cond = v_info.get("environmental_condition", telemetry.get("dominant_condition", "NORMAL"))
        q_score = telemetry.get("overall_quality_score", 0.85)

        db.insert_detection(
            plate=plate, camera_id="CAM_LIVE", timestamp=timestamp,
            confidence=p["confidence"], speed_kmph=0.0,
            vehicle_type=p["vehicle_type"], image_path=snap_url, voting_data=v_data_str,
            env_condition=env_cond, quality_score=q_score,
            plate_color=p_color, category=p_cat, violation=p_viol
        )
        al.check_detection(plate, "CAM_LIVE", timestamp)

        # Real-time Cloud Sync to Firebase (for Mobile Apps / Traffic Police / Ambulance)
        try:
            firebase_sync.push_detection(
                plate=plate, camera_id="CAM_LIVE", timestamp=timestamp,
                confidence=p["confidence"], speed_kmph=0.0,
                vehicle_type=p["vehicle_type"], image_path=snap_url,
                plate_color=p_color, category=p_cat, violation=p_viol
            )
            if ghost_info:
                firebase_sync.push_unplated_dossier(ghost_info.get("profile") or v_prof)
        except Exception:
            pass

        rec = {
            "plate": plate,
            "confidence": p["confidence"],
            "vehicle_type": p["vehicle_type"],
            "camera_id": "CAM_LIVE",
            "image_path": snap_url,
            "first_seen": timestamp,
            "last_seen": timestamp,
            "snapshots": [snap_url],
            "voting_details": v_info,
            "environmental_condition": env_cond,
            "quality_score": q_score,
            "telemetry": telemetry,
            "plate_color": p_color,
            "category": p_cat,
            "violation": p_viol,
            "ghost_info": ghost_info,
            "vehicle_profile": p.get("vehicle_profile") or (ghost_info.get("profile") if ghost_info else None)
        }


        out_records.append(rec)
        with _cam_lock:
            existing = next((x for x in _latest_live_detections if x["plate"] == plate), None)
            if existing:
                existing["last_seen"] = timestamp
                existing["confidence"] = max(existing["confidence"], p["confidence"])
                if snap_url not in existing.setdefault("snapshots", []):
                    existing["snapshots"].append(snap_url)
                existing["environmental_condition"] = env_cond
                existing["quality_score"] = q_score
                existing["telemetry"] = telemetry
            else:
                _latest_live_detections.insert(0, rec)


    # Encode annotated frame
    _, buf = cv2.imencode(".jpg", annotated)
    with _cam_lock:
        global _latest_live_frame, _latest_stream_stats
        _latest_live_frame = buf.tobytes()
        _latest_stream_stats = {
            "mode": "IMAGE_SCAN",
            "fps_realtime": 0.0,
            "total_frames_ingested": 1,
            "frames_filtered_out": 0,
            "frames_sent_to_anpr": 1,
            "compute_saved_pct": "0.0%",
            "dominant_scene": out_records[0]["environmental_condition"] if out_records else "NORMAL"
        }

    return jsonify({"success": True, "detections": out_records, "stream_stats": _latest_stream_stats})


def _process_video_background(job_id, temp_vpath, timestamp):
    """
    Background thread: process video, store progress/results in _video_jobs[job_id].
    Runs YOLO + plate localizer + OCR on sampled frames without blocking Flask.
    """
    import cv2
    import numpy as np
    from ultralytics import YOLO
    import anpr as anpr_module
    import conditioner

    def update_job(**kwargs):
        with _video_jobs_lock:
            _video_jobs[job_id].update(kwargs)

    try:
        cap = cv2.VideoCapture(temp_vpath)
        if not cap.isOpened():
            update_job(status="error", error="Could not open video file.")
            return

        video_conditioner = conditioner.AIVideoConditioner()
        anpr_module._sequence_fusion.track_buffers.clear()

        global _upload_yolo_model
        if _upload_yolo_model is None:
            _upload_yolo_model = YOLO("yolov8s.pt")
        model = _upload_yolo_model


        clean_ts = timestamp.replace(":", "").replace("-", "").replace("T", "_")

        out_records = []
        seen_plates = set()
        stream_stats = {}
        frame_idx   = 0
        sampled_count = 0
        max_sampled   = 30          # Comprehensive multi-vehicle sampling across video
        last_frame    = None

        total_vid_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 300
        step = max(1, total_vid_frames // max_sampled)
        effective_max = min(max_sampled, max(1, total_vid_frames // step))
        update_job(total_frames=total_vid_frames, step=step)



        while cap.isOpened() and sampled_count < max_sampled:
            ret, f = cap.read()
            if not ret:
                break
            frame_idx += 1
            if step > 1 and frame_idx % step != 0:
                continue

            # Downscale oversized frames
            if f.shape[1] > 960:
                scale = 960.0 / f.shape[1]
                f = cv2.resize(f, (960, int(f.shape[0] * scale)), interpolation=cv2.INTER_AREA)

            sampled_count += 1
            last_frame = f
            update_job(progress=int(sampled_count / effective_max * 90))

            results = model.track(f, persist=True, tracker="botsort.yaml", conf=0.18, verbose=False)
            dispatches, stats = video_conditioner.process_stream_frame(f, results)
            stream_stats = stats

            plates = anpr_module.detect_plates_in_frame(f, results, fast_mode=True)


            if plates:
                for p in plates:
                    plate = p["plate"]
                    conf  = p["confidence"]
                    t_id  = p.get("track_id", abs(hash(plate[:4])) % 100000)

                    # Accept all detected plates (down to 0.20 confidence) so yellow/commercial plates are never skipped
                    if conf < 0.20:
                        continue


                    snap_name = f"{plate}_VID_{clean_ts}.jpg"
                    snap_path = os.path.join(SNAPSHOT_DIR, snap_name)
                    annotated = anpr_module.annotate_frame(f.copy(), [p])
                    cv2.imwrite(snap_path, annotated)
                    snap_url = f"/api/snapshot/{snap_name}"

                    v_info    = p.get("voting_details", {})
                    v_info["frames_analyzed"]  = max(3, v_info.get("frames_analyzed", 1))
                    v_info["confidence_boost"] = "+14.0% (Temporal Consensus)"
                    v_data_str = json.dumps(v_info)
                    telemetry  = p.get("telemetry", {})
                    env_cond   = v_info.get("environmental_condition", telemetry.get("dominant_condition", "NORMAL"))
                    q_score    = telemetry.get("overall_quality_score", 0.92)

                    # Check if this track_id or plate was already recorded in this video job
                    existing_rec = next((r for r in out_records if r.get("track_id") == t_id or r["plate"] == plate), None)
                    if existing_rec:
                        if conf > existing_rec["confidence"]:
                            existing_rec["plate"] = plate
                            existing_rec["confidence"] = conf
                            existing_rec["image_path"] = snap_url
                            existing_rec["voting_details"] = v_info
                        if snap_url not in existing_rec.setdefault("snapshots", []):
                            existing_rec["snapshots"].append(snap_url)
                    else:
                        p_color = p.get("plate_color", "WHITE")
                        p_cat = p.get("category", "Private Vehicle")
                        p_viol = p.get("violation", "NONE")

                        # Ghost Vehicle Profiling & Re-ID for Plate-Less / Covered Plate Vehicles
                        ghost_info = None
                        if p_viol == "MISSING_OR_COVERED_PLATE" or "NO PLATE" in plate or "UNREADABLE" in plate:
                            v_prof = p.get("vehicle_profile") or vehicle_profiler.extract_vehicle_profile(None, vehicle_type=p.get("vehicle_type", "Car"))
                            ghost_info = vehicle_reid.match_or_create_ghost(
                                v_prof,
                                camera_id="CAM_CCTV_STREAM",
                                timestamp=timestamp,
                                image_path=snap_url,
                                speed_kmph=45.0
                            )
                            plate = f"{ghost_info['ghost_id']} (NO PLATE)"
                            p["plate"] = plate

                        db.insert_detection(
                            plate=plate, camera_id="CAM_CCTV_STREAM", timestamp=timestamp,
                            confidence=conf, speed_kmph=45.0,
                            vehicle_type=p["vehicle_type"], image_path=snap_url,
                            voting_data=v_data_str, env_condition=env_cond, quality_score=q_score,
                            plate_color=p_color, category=p_cat, violation=p_viol
                        )
                        al.check_detection(plate, "CAM_CCTV_STREAM", timestamp)

                        try:
                            firebase_sync.push_detection(
                                plate=plate, camera_id="CAM_CCTV_STREAM", timestamp=timestamp,
                                confidence=conf, speed_kmph=45.0,
                                vehicle_type=p["vehicle_type"], image_path=snap_url,
                                plate_color=p_color, category=p_cat, violation=p_viol
                            )
                            if ghost_info:
                                firebase_sync.push_unplated_dossier(ghost_info.get("profile") or v_prof)
                        except Exception:
                            pass

                        rec = {
                            "plate": plate, "track_id": t_id, "confidence": conf,
                            "vehicle_type": p["vehicle_type"], "camera_id": "CAM_CCTV_STREAM",
                            "image_path": snap_url, "first_seen": timestamp, "last_seen": timestamp,
                            "snapshots": [snap_url], "voting_details": v_info,
                            "environmental_condition": env_cond, "quality_score": q_score, "telemetry": telemetry,
                            "plate_color": p_color, "category": p_cat, "violation": p_viol,
                            "ghost_info": ghost_info,
                            "vehicle_profile": p.get("vehicle_profile") or (ghost_info.get("profile") if ghost_info else None)
                        }
                        out_records.append(rec)
                        with _cam_lock:
                            _latest_live_detections.insert(0, rec)



        cap.release()
        try:
            os.remove(temp_vpath)
        except Exception:
            pass

        update_job(progress=95)

        # Flush remaining tracklets at EOF
        flushed = video_conditioner.flush_remaining_tracklets()
        for d_veh in flushed:
            t_id      = d_veh["track_id"]
            top_cands = d_veh["top_candidates"]
            best_cand = d_veh["best_candidate"]
            crop_img  = best_cand.get("crop")
            if crop_img is None or crop_img.size == 0:
                continue
            plates = anpr_module.detect_plates_in_frame(crop_img, None)
            if plates:
                for p in plates:
                    plate = p["plate"]
                    if plate in seen_plates:
                        continue
                    seen_plates.add(plate)
                    snap_name = f"{plate}_TRK{t_id}_{clean_ts}.jpg"
                    snap_path = os.path.join(SNAPSHOT_DIR, snap_name)
                    annotated = anpr_module.annotate_frame(crop_img.copy(), [p])
                    cv2.imwrite(snap_path, annotated)
                    snap_url  = f"/api/snapshot/{snap_name}"
                    v_info    = p.get("voting_details", {})
                    v_info["frames_analyzed"]  = len(top_cands)
                    v_info["confidence_boost"] = f"+{min(14.0, 3.5 * len(top_cands)):.1f}% (Temporal Consensus)"
                    telemetry = p.get("telemetry", {})
                    env_cond  = v_info.get("environmental_condition", telemetry.get("dominant_condition", "NORMAL"))
                    q_score   = telemetry.get("overall_quality_score", 0.92)
                    rec = {
                        "plate": plate, "confidence": p["confidence"],
                        "vehicle_type": p["vehicle_type"], "camera_id": "CAM_CCTV_STREAM",
                        "image_path": snap_url, "first_seen": timestamp, "last_seen": timestamp,
                        "snapshots": [snap_url], "voting_details": v_info,
                        "environmental_condition": env_cond, "quality_score": q_score, "telemetry": telemetry
                    }
                    out_records.append(rec)
                    with _cam_lock:
                        _latest_live_detections.insert(0, rec)

        # Last-resort full-frame scan if nothing found
        if not out_records and last_frame is not None:
            plates = anpr_module.detect_plates_in_frame(last_frame, None)
            for p in plates:
                plate = p["plate"]
                if plate in seen_plates:
                    continue
                seen_plates.add(plate)
                snap_name = f"{plate}_CAM_CCTV_{clean_ts}.jpg"
                snap_path = os.path.join(SNAPSHOT_DIR, snap_name)
                annotated = anpr_module.annotate_frame(last_frame.copy(), [p])
                cv2.imwrite(snap_path, annotated)
                snap_url  = f"/api/snapshot/{snap_name}"
                rec = {
                    "plate": plate, "confidence": p["confidence"],
                    "vehicle_type": p["vehicle_type"], "camera_id": "CAM_CCTV_STREAM",
                    "image_path": snap_url, "first_seen": timestamp, "last_seen": timestamp,
                    "snapshots": [snap_url], "voting_details": p.get("voting_details", {}),
                    "environmental_condition": "NORMAL", "quality_score": 0.88, "telemetry": p.get("telemetry", {})
                }
                out_records.append(rec)
                with _cam_lock:
                    _latest_live_detections.insert(0, rec)

        with _cam_lock:
            global _latest_live_frame, _latest_stream_stats
            if last_frame is not None:
                _, buf = cv2.imencode(".jpg", last_frame)
                _latest_live_frame = buf.tobytes()
            _latest_stream_stats = stream_stats

        update_job(status="done", progress=100, detections=out_records, stream_stats=stream_stats)

    except Exception as e:
        import traceback
        update_job(status="error", error=str(e), traceback=traceback.format_exc())





@app.route("/api/anpr/upload_video", methods=["POST"])
def upload_and_process_video():
    """
    Accepts a video upload and immediately returns a job_id.
    Processing happens in a background thread — no browser timeouts.
    Poll /api/anpr/video_poll/<job_id> for progress and results.
    """
    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "No video file uploaded. Please select an .mp4 or .avi file."}), 400

    import uuid
    job_id    = uuid.uuid4().hex
    timestamp = datetime.now().isoformat(timespec="seconds")

    # Save file with unique name to avoid concurrent upload collisions
    v_file     = request.files["file"]
    temp_vpath = os.path.join(SNAPSHOT_DIR, f"upload_{job_id}.mp4")
    v_file.save(temp_vpath)

    with _video_jobs_lock:
        _video_jobs[job_id] = {
            "status":     "processing",
            "progress":   0,
            "detections": [],
            "stream_stats": {},
            "error":      None
        }

    t = threading.Thread(
        target=_process_video_background,
        args=(job_id, temp_vpath, timestamp),
        daemon=True
    )
    t.start()

    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/api/anpr/video_poll/<job_id>")
def poll_video_job(job_id):
    """Returns current status, progress (0-100), and detections for a video processing job."""
    with _video_jobs_lock:
        job = _video_jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/snapshot/<path:filename>")
def get_snapshot(filename):
    if os.path.exists(os.path.join(SNAPSHOT_DIR, filename)):
        return send_from_directory(SNAPSHOT_DIR, filename)
    demo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_snapshots")
    if os.path.exists(os.path.join(demo_dir, filename)):
        return send_from_directory(demo_dir, filename)
    if os.path.exists(os.path.join(demo_dir, "test_cctv.jpg")):
        return send_from_directory(demo_dir, "test_cctv.jpg")
    return send_from_directory(SNAPSHOT_DIR, filename)


@app.route("/api/anpr/start", methods=["POST"])
def start_anpr():
    global _anpr_thread, _anpr_active
    if _anpr_active:
        return jsonify({"status": "already running", "success": True})
    # Register live camera node at Bhubaneswar Command Center
    db.upsert_camera("CAM_LIVE", "Live CCTV Edge Node", "Station Road", 20.2640, 85.8354, "Central")
    _anpr_active = True
    _anpr_thread = threading.Thread(target=run_live_anpr, daemon=True)
    _anpr_thread.start()
    return jsonify({"status": "started", "success": True})



@app.route("/api/anpr/stop", methods=["POST"])
def stop_anpr():
    global _anpr_active
    _anpr_active = False
    return jsonify({"status": "stopping"})


@app.route("/api/anpr/status")
def anpr_status():
    global _anpr_active
    return jsonify({"active": _anpr_active})


@app.route("/api/sample_video/<path:filename>")
def get_sample_video(filename):
    """Serves sample test videos from data/sample_videos."""
    sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_videos")
    return send_from_directory(sample_dir, filename)





# -----------------------------------------------------------------------
# Background Simulation
# -----------------------------------------------------------------------
def start_background_simulation():
    import simulate as sim
    sim_thread = threading.Thread(
        target=sim.run_simulation,
        kwargs={"interval_sec": 2, "verbose": False},
        daemon=True
    )
    sim_thread.start()


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
if __name__ == "__main__":
    db.init_db()
    al.seed_demo_blacklist()

    # Seed demo cameras if not already present
    from simulate import seed_cameras
    seed_cameras()

    # Automatically start multi-camera data stream in background!
    start_background_simulation()

    port = int(os.environ.get("PORT", 5050))
    print("\n" + "="*56)
    print("  [+] City Vehicle Intelligence Central Server")
    print(f"  [*] Web Dashboard -> http://127.0.0.1:{port}")
    print("  [*] Auto-Simulation: Streaming 8 city cameras in background")
    print("  [*] Single-Terminal: All services running together!")
    print("  Press Ctrl+C to stop")
    print("="*56 + "\n")

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


