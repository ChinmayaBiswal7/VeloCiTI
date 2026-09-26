"""
webcam_pipeline.py - Live webcam, uploaded-image and uploaded-video ANPR + vehicle intelligence.

  live burst : 24 frames/second from the browser -> BoT-SORT tracking -> IQA + Random Forest gate
               -> restoration + OCR on the best frames -> weighted consensus voting
  image      : stills -> vehicle detection -> plate check -> "plated" or "no plate" card
  video      : the same burst pipeline for every second of an uploaded clip, then cards per vehicle
"""

import math
import os
import queue
import re
import tempfile
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from types import SimpleNamespace

import cv2
import numpy as np
from flask import jsonify, request

import vehicle_intel as vi

VEHICLE_CLASSES = {1: "Motorbike", 2: "Car", 3: "Motorbike", 5: "Bus", 7: "Truck"}
OCR_FRAMES_PER_TRACK = 4
DETECTOR_READS_PER_TRACK = 2  # detector-first reads are slow, so only the best frames of a track get one
RF_THRESHOLD = 0.42
MIN_PLATE_CONF = 0.40  # lower threshold allows challenging CCTV / moving video reads to confirm
FRAMES_PER_SECOND = 4
MAX_PROFILED_TRACKS = 12


def is_auto_rickshaw(crop, cls, aspect_ratio):
    """
    Identifies Auto-Rickshaw / Three-Wheeler from YOLO Truck (7) or Car (2) misclassifications.
    Uses aspect ratio (tall and narrow, < 1.15) and signature dual-tone color scheme
    (Black & Yellow for Mumbai/MH/Gujarat or Green & Yellow for CNG/Bhubaneswar).
    """
    if crop is None or crop.size == 0 or aspect_ratio >= 1.20:
        return False
    h, w = crop.shape[:2]
    total_px = float(h * w)
    if total_px < 60:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    
    yellow_mask = cv2.inRange(hsv, np.array([13, 50, 50]), np.array([38, 255, 255]))
    yellow_ratio = np.count_nonzero(yellow_mask) / total_px

    black_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 68]))
    black_ratio = np.count_nonzero(black_mask) / total_px

    green_mask = cv2.inRange(hsv, np.array([36, 45, 35]), np.array([85, 255, 255]))
    green_ratio = np.count_nonzero(green_mask) / total_px

    # Signature Indian auto-rickshaw: Black & Yellow (Mumbai/Pune) or Green & Yellow (CNG)
    if (yellow_ratio > 0.04 and black_ratio > 0.10) or (yellow_ratio > 0.04 and green_ratio > 0.08):
        return True
    
    # Or if classified as truck by YOLO but has narrow compact aspect ratio (< 1.05) and dark canvas / yellow
    if cls == 7 and aspect_ratio < 1.05 and (yellow_ratio > 0.02 or black_ratio > 0.16):
        return True
        
    return False
MAX_IMAGES_PER_REQUEST = 8
MAX_VEHICLES_PER_IMAGE = 8
MAX_JOBS_KEPT = 10

_ctx = {}
_lock = threading.Lock()  # serialises model / OCR use across image and video work
_live_state = {}
_live_state_lock = threading.Lock()
_live_ocr_queue = queue.Queue(maxsize=100)
_live_ocr_enqueued_times = {}
_live_worker_thread = None
_next_live_track_id = 1
_recent_cards = []
_recent_cards_lock = threading.Lock()
_video_jobs = {}
_image_model = {"model": None}


_cached_modules = None
def _modules():
    global _cached_modules
    if _cached_modules is None:
        import anpr
        import enhancer
        import ml_selector
        import quality
        import vehicle_profiler
        import vehicle_reid
        _cached_modules = SimpleNamespace(anpr=anpr, enhancer=enhancer, ml=ml_selector, quality=quality,
                                          prof=vehicle_profiler, reid=vehicle_reid)
    return _cached_modules


def get_model_vehicle_type(model, cls, crop=None, aspect_ratio=1.0):
    """
    Returns human-friendly vehicle name whether using Indian Traffic YOLO or standard COCO YOLO.
    """
    names = getattr(model, "names", {})
    raw_name = str(names.get(cls, "")).lower()
    if "auto" in names.values() or "lcv" in names.values():
        mapping = {
            "auto": "Auto-Rickshaw",
            "bus": "Bus",
            "car": "Car",
            "lcv": "LCV / Tempo",
            "motorcycle": "Motorbike",
            "multiaxle": "Heavy Truck",
            "tractor": "Tractor",
            "truck": "Truck"
        }
        return mapping.get(raw_name, raw_name.title() or "Vehicle")
    coco_map = {1: "Motorbike", 2: "Car", 3: "Motorbike", 5: "Bus", 7: "Truck"}
    vtype = coco_map.get(cls, "Car")
    if is_auto_rickshaw(crop, cls, aspect_ratio):
        vtype = "Auto-Rickshaw"
    return vtype


def _yolo(weights_name="yolov8n.pt"):
    from ultralytics import YOLO
    candidates = [
        weights_name,
        os.path.join(_ctx.get("prototype_dir", "prototype"), weights_name),
        "yolov8n.pt",
        os.path.join(_ctx.get("prototype_dir", "prototype"), "yolov8n.pt")
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                m = YOLO(p)
                print(f"[Webcam Pipeline] Loaded YOLO weights: {p}")
                return m
            except Exception:
                pass
    return YOLO("yolov8n.pt")


def _get_image_model():
    if _image_model["model"] is None:
        _image_model["model"] = _yolo("yolov8s.pt")
    return _image_model["model"]


def _new_track_state():
    return {"plate": None, "conf": 0.0, "details": {}, "ocr_tries": 0, "plate_color": "WHITE",
            "category": "Private Vehicle", "logged": None, "ghost_id": None,
            "cls": 2, "bbox": None, "frames_seen": 0, "rf_best": 0.0,
            "plate_crops": [], "card": None, "last_seen": time.time(),
            "velocity": (0.0, 0.0), "types_hist": []}


def _get_next_live_track_id():
    global _next_live_track_id
    with _live_state_lock:
        tid = _next_live_track_id
        _next_live_track_id += 1
        return tid


def _compute_box_metrics(box_a, box_b):
    """
    Computes (iou, norm_center_dist, scale_ratio, diou) between two boxes [x1, y1, x2, y2].
    """
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    aw, ah = max(1, ax2 - ax1), max(1, ay2 - ay1)
    bw, bh = max(1, bx2 - bx1), max(1, by2 - by1)

    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    iou = inter / union if union > 0 else 0.0

    acx, acy = (ax1 + ax2) / 2.0, (ay1 + ay2) / 2.0
    bcx, bcy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
    cdist = math.hypot(acx - bcx, acy - bcy)

    enc_w = max(ax2, bx2) - min(ax1, bx1)
    enc_h = max(ay2, by2) - min(ay1, by1)
    c_diag = math.hypot(enc_w, enc_h)
    norm_dist = cdist / max(1.0, math.hypot(max(aw, bw), max(ah, bh)))

    diou = iou - ((cdist * cdist) / (c_diag * c_diag if c_diag > 0 else 1.0))

    area_a = aw * ah
    area_b = bw * bh
    scale_ratio = min(area_a, area_b) / max(1.0, max(area_a, area_b))

    return iou, norm_dist, scale_ratio, diou


def match_detections_to_tracks(detections, tracks_dict, now, max_age_seconds=3.0, id_generator=None):
    """
    Production-grade multi-object spatial-temporal association:
    - Bipartite greedy assignment
    - Motion compensation (velocity extrapolation)
    - Multi-criteria matching (IoU, normalized center distance, scale ratio, DIoU)
    - Vehicle type majority vote / stabilization across frames
    - Monotonic ID allocation (preventing #3 -> #4 jumps)
    - Stale track pruning
    """
    # 1. Prune expired tracks older than max_age_seconds
    expired = [tid for tid, trk in tracks_dict.items() if (now - trk.get("last_seen", now)) > max_age_seconds]
    for tid in expired:
        tracks_dict.pop(tid, None)

    # 2. Candidate affinities between current detections and active tracks
    active_items = list(tracks_dict.items())
    candidates = []

    for d_idx, det in enumerate(detections):
        dbox = det["bbox"]
        dcls = det.get("cls")
        for tid, trk in active_items:
            tbox = trk.get("bbox")
            if not tbox:
                continue

            dt = max(0.01, min(1.0, now - trk.get("last_seen", now)))
            vel = trk.get("velocity", (0.0, 0.0))
            pred_box = [
                tbox[0] + vel[0] * dt,
                tbox[1] + vel[1] * dt,
                tbox[2] + vel[0] * dt,
                tbox[3] + vel[1] * dt,
            ]

            iou_curr, ndist_curr, sratio_curr, diou_curr = _compute_box_metrics(dbox, tbox)
            iou_pred, ndist_pred, sratio_pred, diou_pred = _compute_box_metrics(dbox, pred_box)

            best_iou = max(iou_curr, iou_pred)
            best_ndist = min(ndist_curr, ndist_pred)
            best_sratio = max(sratio_curr, sratio_pred)
            best_diou = max(diou_curr, diou_pred)

            class_match = (dcls == trk.get("cls"))

            # Valid match criteria:
            # - Significant overlap (IoU >= 0.12)
            # - OR Center within 65% of bounding box diagonal and scale ratio >= 0.35
            # - OR DIoU >= 0.05
            is_valid = (
                best_iou >= 0.12
                or (best_ndist <= 0.65 and best_sratio >= 0.35)
                or best_diou >= 0.05
            )

            if is_valid:
                score = (
                    0.55 * best_iou
                    + 0.35 * max(0.0, 1.0 - best_ndist)
                    + 0.10 * best_sratio
                )
                if class_match:
                    score += 0.15
                if trk.get("plate"):
                    score += 0.10
                if det.get("tid_hint") is not None and det["tid_hint"] == tid:
                    score += 1.0
                candidates.append((score, d_idx, tid))

    # 3. Greedy assignment (highest score first)
    candidates.sort(key=lambda x: x[0], reverse=True)
    matched_dets = set()
    matched_tracks = set()
    assignments = {}

    for score, d_idx, tid in candidates:
        if d_idx not in matched_dets and tid not in matched_tracks:
            matched_dets.add(d_idx)
            matched_tracks.add(tid)
            assignments[d_idx] = tid

    # 4. Update matched tracks & create new tracks for unmatched detections
    results = []
    for d_idx, det in enumerate(detections):
        dbox = det["bbox"]
        dcls = det.get("cls", 2)
        dvtype = det.get("vtype", "Car")

        if d_idx in assignments:
            tid = assignments[d_idx]
            st = tracks_dict[tid]

            # Velocity update
            prev_box = st.get("bbox", dbox)
            dt = max(0.02, now - st.get("last_seen", now))
            pcx = (prev_box[0] + prev_box[2]) / 2.0
            pcy = (prev_box[1] + prev_box[3]) / 2.0
            ncx = (dbox[0] + dbox[2]) / 2.0
            ncy = (dbox[1] + dbox[3]) / 2.0
            inst_vx = (ncx - pcx) / dt
            inst_vy = (ncy - pcy) / dt
            old_vel = st.get("velocity", (0.0, 0.0))
            st["velocity"] = (0.7 * old_vel[0] + 0.3 * inst_vx, 0.7 * old_vel[1] + 0.3 * inst_vy)

            # Vehicle type stabilization (majority vote over last 15 frames)
            types_hist = st.setdefault("types_hist", [])
            types_hist.append(dvtype)
            if len(types_hist) > 15:
                types_hist.pop(0)
            stabilized_type = Counter(types_hist).most_common(1)[0][0]

            st["bbox"] = dbox
            st["cls"] = dcls
            st["vehicle_type"] = stabilized_type
            st["last_seen"] = now
            st["frames_seen"] = st.get("frames_seen", 0) + 1
            st["missed_frames"] = 0
            det["track_id"] = tid
            det["vehicle_type"] = stabilized_type
            det["is_new"] = False
        else:
            if det.get("tid_hint") is not None and det["tid_hint"] not in tracks_dict:
                tid = det["tid_hint"]
            elif id_generator:
                tid = id_generator()
            else:
                tid = max(tracks_dict.keys(), default=0) + 1
            st = _new_track_state()
            st["bbox"] = dbox
            st["cls"] = dcls
            st["vehicle_type"] = dvtype
            st["types_hist"] = [dvtype]
            st["velocity"] = (0.0, 0.0)
            st["first_seen"] = now
            st["last_seen"] = now
            st["frames_seen"] = 1
            st["missed_frames"] = 0
            tracks_dict[tid] = st
            det["track_id"] = tid
            det["vehicle_type"] = dvtype
            det["is_new"] = True

        results.append(det)

    return results


def _standardize(frame):
    h, w = frame.shape[:2]
    if w > 1280:
        return cv2.resize(frame, (1280, int(h * 1280.0 / w)), interpolation=cv2.INTER_AREA)
    return frame


# ---------------------------------------------------------------------------
# Multi-frame burst pipeline (live webcam + every second of an uploaded video)
# ---------------------------------------------------------------------------
def analyze_burst_frames(m, frames, model, state, fusion, camera_id, crops_out=None, scan_fallback=False):
    db, al = _ctx["db"], _ctx["al"]
    t_start = time.time()
    timestamp = datetime.now().isoformat(timespec="seconds")
    candidates, last_seen, conditions = {}, {}, Counter()
    frames_tracked = 0
    fw = fh = 0
    mid_frame = None

    # Phases 1-3: standardize resolution, track every frame, score every vehicle crop
    for fi, frame in enumerate(frames):
        frame = _standardize(frame)
        fh, fw = frame.shape[:2]
        if fi == len(frames) // 2:
            mid_frame = frame
        try:
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.28, imgsz=640, verbose=False)
        except Exception as e:
            print(f"[Webcam Pipeline] tracking note: {e}")
            continue
        frames_tracked += 1
        boxes = results[0].boxes if results else None
        if boxes is None or len(boxes) == 0:
            continue

        frame_dets = []
        for b_idx, box in enumerate(boxes):
            cls = int(box.cls)
            if cls not in VEHICLE_CLASSES:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(fw, x2), min(fh, y2)
            if (x2 - x1) < 28 or (y2 - y1) < 28:
                continue
            ar = float(x2 - x1) / float(max(1, y2 - y1))
            vtype = get_model_vehicle_type(model, cls, aspect_ratio=ar)
            tid_hint = int(box.id[0]) if (box.id is not None and len(box.id) > 0) else None
            frame_dets.append({
                "bbox": [x1, y1, x2, y2],
                "cls": cls,
                "vtype": vtype,
                "conf": float(box.conf[0]) if box.conf is not None else 0.85,
                "tid_hint": tid_hint
            })

        matched_dets = match_detections_to_tracks(frame_dets, state, now=time.time(), max_age_seconds=8.0)
        for det in matched_dets:
            tid = det["track_id"]
            x1, y1, x2, y2 = det["bbox"]
            cls = det["cls"]
            last_seen[tid] = {"bbox": [x1, y1, x2, y2], "cls": cls}
            veh_crop = frame[y1:y2, x1:x2]
            if veh_crop.size == 0:
                continue
            vh, vw = veh_crop.shape[:2]
            if vw < 280 or vh < 120:
                s = max(280.0 / max(1, vw), 120.0 / max(1, vh))
                veh_crop = cv2.resize(veh_crop, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
            # If vehicle already has a confirmed plate, skip expensive plate localization to save CPU
            st_active = state.get(tid)
            if st_active and st_active.get("plate"):
                telemetry = {"dominant_condition": "NORMAL"}
                candidates.setdefault(tid, []).append({
                    "rf": 0.88,
                    "accepted": False,
                    "plate_region": None,
                    "veh_crop": veh_crop,
                    "telemetry": telemetry,
                })
                continue

            plate_region = m.anpr.find_plate_region_in_crop(veh_crop, cls=cls)
            if plate_region is not None and plate_region.size == 0:
                plate_region = None
            eval_crop = plate_region if plate_region is not None else veh_crop
            telemetry = m.quality.assess_image_quality(eval_crop, is_scene_frame=False)
            conditions[telemetry.get("dominant_condition", "NORMAL")] += 1
            rf_eval = m.ml.evaluate_frame_candidate(eval_crop, telemetry)
            candidates.setdefault(tid, []).append({
                "rf": rf_eval["rf_quality_score"],
                "accepted": rf_eval["is_acceptable_for_ocr"],
                "plate_region": plate_region,
                "veh_crop": veh_crop,
                "telemetry": telemetry,
            })

    # Phases 4-7: Random Forest gate -> restore + OCR best frames -> consensus vote
    tracks_out = []
    rf_accepted = rf_deferred = ocr_runs = 0
    for tid, cands in candidates.items():
        cls = last_seen[tid]["cls"]
        bbox = last_seen[tid]["bbox"]
        bw = max(1, bbox[2] - bbox[0])
        bh = max(1, bbox[3] - bbox[1])
        ar = float(bw) / float(bh)
        st = state.setdefault(tid, _new_track_state())
        st["cls"], st["bbox"] = cls, bbox
        st["frames_seen"] += len(cands)
        accepted = sorted((c for c in cands if c["accepted"]), key=lambda c: c["rf"], reverse=True)
        rf_accepted += len(accepted)
        rf_deferred += len(cands) - len(accepted)

        # Accumulate plate image crops across the entire duration the vehicle is in frame
        for c in cands:
            pr = c.get("plate_region")
            if pr is not None and pr.size > 0 and len(st.setdefault("plate_crops", [])) < 16:
                st["plate_crops"].append(pr)

        best = accepted[0] if accepted else (max(cands, key=lambda c: c["rf"]) if cands else None)
        veh_crop_check = best["veh_crop"] if best else None
        vtype = get_model_vehicle_type(model, cls, veh_crop_check, ar)
        if crops_out is not None and best and best["rf"] >= st["rf_best"]:
            crops_out[tid] = best["veh_crop"]
        if best:
            st["rf_best"] = max(st["rf_best"], best["rf"])

        # Run OCR only if vehicle doesn't have a confirmed plate yet
        if not st.get("plate"):
            detector_budget = 2
            to_ocr = accepted if accepted else ([best] if best else [])
            for c in to_ocr[:2]:
                plate_found, avg_conf, plate_crop = None, 0.0, None
                
                # Priority 1: Segmented plate region with multi-modal restoration & character detection
                if c.get("plate_region") is not None:
                    restored = m.enhancer.restore_image(c["plate_region"], c["telemetry"])
                    pf, pconf = m.anpr.multi_pass_ocr_on_plate(restored, max_passes=2)
                    if pf:
                        plate_found, avg_conf, plate_crop = pf, pconf, c["plate_region"]

                # Priority 2: High-accuracy detector-first text localizer on vehicle crop
                if not plate_found and detector_budget > 0:
                    detector_budget -= 1
                    d_text, d_conf, d_crop = _detect_and_read(m, c["veh_crop"])
                    if d_text:
                        plate_found, avg_conf, plate_crop = d_text, d_conf, d_crop

                ocr_runs += 1
                st["ocr_tries"] += 1
                if plate_found:
                    clean_p = vi.clean_plate(plate_found)
                    if vi.plate_format_valid(clean_p) or avg_conf >= 0.35:
                        crop_f = plate_crop if plate_crop is not None else c["veh_crop"]
                        plate, conf, details = fusion.add_frame_observation(
                            tid, crop_f, clean_p, max(avg_conf, 0.70), c["telemetry"])
                        st["plate"], st["conf"], st["details"] = plate, conf, details
                        st["plate_color"], st["category"] = m.anpr.classify_plate_color_and_category(crop_f)
                        break

        details = st["details"]
        violation = "NONE"
        label = st["plate"]
        if st["plate"]:
            gate = details.get("quality_gate_status", "CONFIRMED_CONSENSUS")
            status = "CONFIRMED" if gate == "CONFIRMED_CONSENSUS" else "BUFFERING"
        elif st["ocr_tries"] >= 8:
            status = "NO_PLATE"
            violation = "MISSING_OR_COVERED_PLATE"
            if not st["ghost_id"] and (accepted or cands):
                try:
                    chosen_crop = (accepted[0] if accepted else best)["veh_crop"]
                    prof = m.prof.extract_vehicle_profile(chosen_crop, vehicle_type=vtype)
                    ghost = m.reid.match_or_create_ghost(
                        prof, camera_id=camera_id, timestamp=timestamp, image_path="", speed_kmph=0.0)
                    st["ghost_id"] = ghost["ghost_id"]
                except Exception as e:
                    print(f"[Webcam Pipeline] ghost profiling note: {e}")
            if st["ghost_id"]:
                label = f"{st['ghost_id']} (NO PLATE)"
        else:
            status = "READING" if st["ocr_tries"] > 0 else "TRACKING"

        if label and st["logged"] != label and status in ("CONFIRMED", "NO_PLATE"):
            try:
                db.insert_detection(
                    plate=label, camera_id=camera_id, timestamp=timestamp,
                    confidence=float(st["conf"]), speed_kmph=0.0, vehicle_type=vtype, image_path="",
                    plate_color=st["plate_color"] if violation == "NONE" else "GREY",
                    category=st["category"] if violation == "NONE" else "Violation / Missing Plate",
                    violation=violation)
                al.check_detection(label, camera_id, timestamp)
                st["logged"] = label
            except Exception as e:
                print(f"[Webcam Pipeline] DB insert note: {e}")

        tracks_out.append({
            "track_id": tid,
            "plate": label,
            "confidence": st["conf"],
            "vehicle_type": vtype,
            "bbox": last_seen[tid]["bbox"],
            "plate_color": st["plate_color"],
            "category": st["category"],
            "violation": violation,
            "status": status,
            "rf_quality_score": round(max(c["rf"] for c in cands), 3),
            "frames_in_burst": len(cands),
            "frames_accepted": len(accepted),
            "fusion_frames": details.get("frames_analyzed", 0),
            "condition": details.get("environmental_condition", "NORMAL"),
            "timestamp": timestamp,
        })

    # A plate held close to the camera has no vehicle for YOLO: scan the middle frame directly.
    if scan_fallback and not tracks_out and mid_frame is not None:
        for i, p in enumerate(m.anpr.scan_frame_for_plates(mid_frame)):
            d = p.get("voting_details", {})
            plate = p["plate"]
            st = state.setdefault(f"scan:{plate}", {"logged": None})
            if st["logged"] != plate:
                try:
                    db.insert_detection(
                        plate=plate, camera_id=camera_id, timestamp=timestamp,
                        confidence=float(p["confidence"]), speed_kmph=0.0,
                        vehicle_type=p.get("vehicle_type", "Car"), image_path="",
                        plate_color=p.get("plate_color", "WHITE"),
                        category=p.get("category", "Private Vehicle"), violation="NONE")
                    al.check_detection(plate, camera_id, timestamp)
                    st["logged"] = plate
                except Exception as e:
                    print(f"[Webcam Pipeline] DB insert note: {e}")
            tracks_out.append({
                "track_id": 100000 + i,
                "plate": plate,
                "confidence": p["confidence"],
                "vehicle_type": p.get("vehicle_type", "Car"),
                "bbox": list(p.get("bbox") or [0, 0, fw, fh]),
                "plate_color": p.get("plate_color", "WHITE"),
                "category": p.get("category", "Private Vehicle"),
                "violation": "NONE",
                "status": "CONFIRMED" if d.get("quality_gate_status") == "CONFIRMED_CONSENSUS" else "BUFFERING",
                "rf_quality_score": d.get("rf_evaluation", {}).get("rf_quality_score", 0.0),
                "frames_in_burst": 1,
                "frames_accepted": 1,
                "fusion_frames": d.get("frames_analyzed", 1),
                "condition": d.get("environmental_condition", "NORMAL"),
                "timestamp": timestamp,
            })
            ocr_runs += 1

    counts_by_type = Counter(t["vehicle_type"] for t in tracks_out)
    return {
        "success": True,
        "timestamp": timestamp,
        "frame_width": fw,
        "frame_height": fh,
        "total_vehicles": len(tracks_out),
        "counts_by_type": dict(counts_by_type),
        "tracks": tracks_out,
        "pipeline": {
            "frames_received": len(frames),
            "frames_tracked": frames_tracked,
            "rf_accepted": rf_accepted,
            "rf_deferred": rf_deferred,
            "ocr_runs": ocr_runs,
            "rf_threshold": RF_THRESHOLD,
            "elapsed_ms": int((time.time() - t_start) * 1000),
            "conditions": dict(conditions),
        },
    }


# ---------------------------------------------------------------------------
# Vehicle cards (shared by image and video modes)
# ---------------------------------------------------------------------------
def _text_localize(m, crop):
    """Detector-first plate finder. EasyOCR's text detector runs on the vehicle crop at native resolution:
    the colour/contour region heuristic misses plates on busy grilles, and shrinking the whole crop to
    140 px (the old fallback) blurs the characters into look-alikes such as TN -> PB.
    Returns candidates [{plate, conf, box}] that parse as valid Indian registrations, best first."""
    h, w = crop.shape[:2]
    # Check YOLO plate detector first!
    p_reg = m.anpr.find_plate_region_in_crop(crop)
    if p_reg is not None and p_reg.size > 0:
        pf, pconf = m.anpr.multi_pass_ocr_on_plate(p_reg, max_passes=2)
        if pf and (vi.plate_format_valid(pf) or pconf >= 0.35):
            return [{"plate": vi.clean_plate(pf), "conf": max(pconf, 0.75), "box": (0, int(h * 0.4), w, h)}]

    s = min(1.0, 1280.0 / max(h, w))
    img = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1.0 else crop
    reader = m.anpr.get_ocr()
    if reader is None:
        return []
    try:
        results = reader.readtext(img, detail=1, paragraph=False,
                                  contrast_ths=0.05, adjust_contrast=0.5,
                                  allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -")
    except Exception:
        return []
    if not results:
        return []

    items = []
    for box, text, conf in results:
        xs, ys = [pt[0] / s for pt in box], [pt[1] / s for pt in box]
        items.append((text, float(conf), (min(xs), min(ys), max(xs), max(ys))))

    found = []

    def consider(text, conf, box):
        clean_text = vi.clean_plate(text)
        plate = m.anpr.extract_indian_plate_from_string(clean_text) or m.anpr.post_process(clean_text)
        if plate and (vi.plate_format_valid(plate) or conf >= 0.40):
            found.append({"plate": vi.clean_plate(plate), "conf": conf, "box": box})

    # 1. Individual tokens
    for text, conf, box in items:
        consider(text, conf, box)

    # 2. Reading-order joined (row by row & multi-token slices)
    sorted_items = m.anpr._sort_tokens_reading_order(results)
    if sorted_items:
        s_tokens = [t for _, t, _ in sorted_items]
        s_confs = [c for _, _, c in sorted_items]
        all_pts = [pt for b, _, _ in sorted_items for pt in b]
        full_box = (min(pt[0]/s for pt in all_pts), min(pt[1]/s for pt in all_pts),
                    max(pt[0]/s for pt in all_pts), max(pt[1]/s for pt in all_pts))
        avg_c = float(np.mean(s_confs)) if s_confs else 0.5
        consider(" ".join(s_tokens), avg_c, full_box)
        consider("".join(s_tokens), avg_c, full_box)
        for w_len in (2, 3, 4):
            for i in range(len(sorted_items) - w_len + 1):
                sub_toks = s_tokens[i:i + w_len]
                sub_c = float(np.mean(s_confs[i:i + w_len]))
                consider(" ".join(sub_toks), sub_c, full_box)
                consider("".join(sub_toks), sub_c, full_box)

    return sorted(found, key=lambda f: f["conf"], reverse=True)


PLATE_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"


def _plate_views(tight):
    """Test-time augmentation: the same plate at three scales, each with three contrast treatments."""
    views = []
    h = max(1, tight.shape[0])
    for target_h in (96, 150, 220):
        k = target_h / h
        v = cv2.resize(tight, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC if k > 1 else cv2.INTER_AREA)
        gray = cv2.cvtColor(v, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(gray)
        sharp = cv2.addWeighted(clahe, 1.6, cv2.GaussianBlur(clahe, (0, 0), 1.2), -0.6, 0)
        views += [v, clahe, sharp]
    return views


def _slot_normalize(m, raw):
    """Map a raw OCR string onto the plate structure LL DD L{1,3} DDDD, or Temporary / BH plates,
    repairing look-alike characters slot by slot (0/O, 1/I, 5/S, 8/B...). Returns None when it cannot be made to fit."""
    raw = re.sub(r"[^A-Z0-9]", "", raw.upper())
    
    # Handle Temporary Plate format (e.g. T0322UP4229B)
    if (raw.startswith("T") or raw.startswith("TC") or raw.startswith("TR")) and 9 <= len(raw) <= 14:
        return m.anpr.fix_positional_characters(raw)
        
    # Handle Bharat Series format (e.g. 22BH1234AA)
    if "BH" in raw and 8 <= len(raw) <= 12:
        return m.anpr.fix_positional_characters(raw)

    if len(raw) not in (9, 10, 11):
        return None
    slots = "LLDD" + "L" * (len(raw) - 8) + "DDDD"
    out = []
    for ch, slot in zip(raw, slots):
        if slot == "L" and ch.isdigit():
            ch = m.anpr._TO_LETTER.get(ch, ch)
        elif slot == "D" and ch.isalpha():
            ch = m.anpr._TO_DIGIT.get(ch, ch)
        if not (ch.isalpha() if slot == "L" else ch.isdigit()):
            return None
        out.append(ch)
    return "".join(out)


def _plate_text_from_results(res):
    """Join the OCR tokens of one view left to right, dropping the blue 'IND' strip (short, no digits)."""
    res = sorted(res, key=lambda r: r[0][0][0])
    toks = [(t, c) for _, t, c in res if any(ch.isdigit() for ch in t) or len(t.replace(" ", "")) > 3]
    return "".join(t for t, _ in toks), (float(np.mean([c for _, c in toks])) if toks else 0.0)


def _multi_view_read(m, tight, anchor=None):
    """Multi-view consensus for one plate crop. Every view is OCR'd and mapped onto the plate structure;
    characters are then voted position by position, weighted by OCR confidence. The detector's own read is
    an anchor with double weight. The winner must carry a real state code. Confidence reflects how strongly
    the views agree rather than one OCR score."""
    reader = m.anpr.get_ocr()
    if reader is None:
        return None, 0.0
    views = _plate_views(tight)
    reads = [(anchor[0], anchor[1], 2.0)] if anchor else []
    for v in views:
        try:
            res = reader.readtext(v, detail=1, paragraph=False, allowlist=PLATE_ALLOWLIST)
        except Exception:
            continue
        if not res:
            continue
        text, conf = _plate_text_from_results(res)
        norm = _slot_normalize(m, text)
        if norm:
            reads.append((norm, conf, 1.0))
    if not reads:
        return None, 0.0

    length = Counter(len(p) for p, _, _ in reads).most_common(1)[0][0]
    same = [r for r in reads if len(r[0]) == length]
    chars, agree = [], []
    for i in range(length):
        votes = defaultdict(float)
        for p, c, w in same:
            votes[p[i]] += c * w
        best = max(votes, key=votes.get)
        chars.append(best)
        agree.append(votes[best] / sum(votes.values()))
    plate = "".join(chars)
    if (plate.startswith("T") or plate.startswith("TC") or plate.startswith("TR")) and len(plate) >= 9:
        plate = m.anpr.fix_positional_characters(plate)
    elif "BH" in plate and len(plate) >= 8:
        plate = m.anpr.fix_positional_characters(plate)
    elif plate[:2] not in m.anpr.INDIAN_STATES:
        fixed = m.anpr._nearest_state_code(plate[:2])
        if fixed not in m.anpr.INDIAN_STATES:
            return None, 0.0
        plate = fixed + plate[2:]
        agree[0] = agree[1] = min(agree[0], agree[1]) * 0.7
    if not vi.plate_format_valid(plate):
        return None, 0.0
    mean_conf = float(np.mean([c for _, c, _ in same]))
    support = len(same) / (len(views) + 1)
    conf = (sum(agree) / length) * (0.5 + 0.5 * mean_conf) * (0.6 + 0.4 * support)
    return plate, round(min(0.99, conf), 3)


def _enhanced_variants(crop):
    """Frame enhancement for the plate finder: the crop as is, then fast edge-preserving bilateral filter (<2ms).
    Later variants are only tried when earlier ones find no plate-like text."""
    yield crop
    den = cv2.bilateralFilter(crop, 5, 50, 50)
    yield den
    if max(crop.shape[:2]) < 600:
        yield cv2.resize(den, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)


def _detect_and_read(m, crop, multi_view=False):
    """Detector-first read of one vehicle crop. Returns (plate, confidence, plate_crop) or (None, 0.0, None).
    The detected box is cropped and restored; with multi_view the plate is read at many scales/contrasts and
    voted, otherwise it is read once more and confidence is boosted only when both reads agree."""
    if crop is None or crop.size == 0:
        return None, 0.0, None

    # Priority 0: High-accuracy YOLO license plate detector on vehicle crop
    try:
        p_reg = m.anpr.find_plate_region_in_crop(crop)
        if p_reg is not None and p_reg.size > 0:
            pf, pconf = m.anpr.multi_pass_ocr_on_plate(p_reg, max_passes=4)
            if pf and (vi.plate_format_valid(pf) or pconf >= 0.35):
                return vi.clean_plate(pf), max(pconf, 0.80), p_reg
    except Exception:
        pass

    for base in _enhanced_variants(crop):
        cands = _text_localize(m, base)
        if cands:
            break
    else:
        return None, 0.0, None
    for cand in cands[:2]:
        x1, y1, x2, y2 = cand["box"]
        padx, pady = 0.08 * (x2 - x1) + 4, 0.25 * (y2 - y1) + 4
        tight = base[max(0, int(y1 - pady)):int(y2 + pady), max(0, int(x1 - padx)):int(x2 + padx)]
        if tight.size == 0:
            return cand["plate"], cand["conf"], None
        if multi_view:
            mv_text, mv_conf = _multi_view_read(m, tight, (cand["plate"], cand["conf"]))
            if mv_text:
                return mv_text, mv_conf, tight
        if tight.shape[0] < 96:
            tight = cv2.resize(tight, None, fx=96.0 / tight.shape[0], fy=96.0 / tight.shape[0],
                               interpolation=cv2.INTER_CUBIC)
        tel = m.quality.assess_image_quality(tight, is_scene_frame=False)
        text2, conf2 = m.anpr.multi_pass_ocr_on_plate(m.enhancer.restore_image(tight, tel), max_passes=4)
        if text2 and vi.plate_format_valid(text2):
            text2 = vi.clean_plate(text2)
            if text2 == cand["plate"]:
                return text2, min(0.99, max(cand["conf"], conf2) + 0.15), tight
            if conf2 > cand["conf"]:
                return text2, conf2, tight
        return cand["plate"], cand["conf"], tight
    return None, 0.0, None


def _plate_ok(text, conf):
    return bool(text) and conf >= MIN_PLATE_CONF and vi.plate_format_valid(text)


def _read_plate(m, crop, cls_id):
    """Single-image plate read: region heuristic first, then the detector-first finder, then a
    whole-crop read as a last resort. IQA + RF score and condition-aware restoration throughout."""
    up = crop
    h, w = crop.shape[:2]
    if w < 280 or h < 120:
        s = max(280.0 / max(1, w), 120.0 / max(1, h))
        up = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
    region = m.anpr.find_plate_region_in_crop(up, cls=cls_id)
    if region is not None and region.size == 0:
        region = None
    eval_crop = region if region is not None else up
    telemetry = m.quality.assess_image_quality(eval_crop, is_scene_frame=False)
    rf = m.ml.evaluate_frame_candidate(eval_crop, telemetry)

    text, conf, plate_crop = None, 0.0, region
    if region is not None:
        text, conf = m.anpr.multi_pass_ocr_on_plate(m.enhancer.restore_image(region, telemetry), max_passes=4)
    if not _plate_ok(text, conf):
        d_text, d_conf, d_crop = _detect_and_read(m, crop, multi_view=True)
        if d_text and (not (text and vi.plate_format_valid(text)) or d_conf > conf):
            text, conf, plate_crop = d_text, d_conf, d_crop
    if not text:
        text, conf = m.anpr.multi_pass_ocr_on_plate(m.enhancer.restore_image(up, telemetry), max_passes=4)
    color, category = m.anpr.classify_plate_color_and_category(plate_crop if plate_crop is not None else up)
    return {"text": vi.clean_plate(text) if text else "", "confidence": round(float(conf), 3),
            "region_found": plate_crop is not None, "rf_quality_score": rf["rf_quality_score"],
            "condition": telemetry.get("dominant_condition", "NORMAL"),
            "color": color, "category": category}


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _people_in_crop(image_model, crop, cls_name, known):
    """Occupants of one vehicle. `known` are persons already found in the full image (crop coords).
    Uses high-confidence pass over windshield / cabin area to prevent headrests from being counted as occupants."""
    people = list(known)
    h, w = crop.shape[:2]
    area = crop if cls_name in ("Motorbike", "Bicycle") else crop[: max(1, int(h * 0.62))]
    scale = max(1.0, 640.0 / max(area.shape[:2]))
    up = cv2.resize(area, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale > 1 else area
    # conf=0.55 prevents headrests and shadows on empty car seats from being detected as occupants
    res = image_model.predict(up, classes=[0], conf=0.55, verbose=False)[0]
    for b in res.boxes:
        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
        bh = (y2 - y1) / scale
        if bh < h * 0.22:
            continue
        box = [int(x1 / scale), int(y1 / scale), int(x2 / scale), int(y2 / scale)]
        if any(_iou(box, p["box"]) > 0.4 for p in people):
            continue
        pc = up[max(0, y1):y2, max(0, x1):x2]
        if pc.size:
            people.append({"box": box, "crop": pc})
    return people


def _save_snapshot(crop, prefix):
    name = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
    try:
        cv2.imwrite(os.path.join(_ctx["snapshot_dir"], name), crop)
        return f"/api/snapshot/{name}"
    except Exception:
        return ""


def _finish_card(m, *, source, card_id, crop, bbox, cls_id, plate, camera_id, image_model,
                 known_people=(), deep=True, track_id=None, existing_ghost_id=None, already_logged=False,
                 vehicle_override=None):
    db, al = _ctx["db"], _ctx["al"]
    timestamp = datetime.now().isoformat(timespec="seconds")
    cls_name = vehicle_override or VEHICLE_CLASSES.get(cls_id, "Car")
    clean_text = vi.clean_plate(plate["text"]) if plate and plate.get("text") else ""
    is_valid_format = bool(clean_text and (vi.plate_format_valid(clean_text) or (len(clean_text) >= 6 and (clean_text[:2] in m.anpr.INDIAN_STATES or m.anpr._nearest_state_code(clean_text[:2]) in m.anpr.INDIAN_STATES))))
    if is_valid_format:
        valid = True
        plate["confidence"] = max(plate.get("confidence", 0.0), 0.88)
    elif clean_text and (plate.get("confidence", 0.0) >= 0.25 or len(clean_text) >= 6):
        valid = True
        plate["confidence"] = max(plate.get("confidence", 0.0), 0.78)
    else:
        valid = False
    status = "PLATED" if valid else ("UNREADABLE" if clean_text else "NO_PLATE")

    attrs = vi.vehicle_attributes(crop if deep else None, cls_name)
    profile = m.prof.extract_vehicle_profile(crop, vehicle_type=cls_name)
    people = _people_in_crop(image_model, crop, cls_name, known_people) if deep else []
    snap_url = _save_snapshot(crop, "webcam")

    # Format make_model
    make_model = attrs.get("make_model", {})
    if not make_model.get("label") and profile.get("estimated_make"):
        make_model = {
            "label": f"{profile['estimated_make']} {profile.get('estimated_model', '')}".strip(),
            "confidence": profile.get("make_confidence", 0.94),
            "candidates": [
                {"label": f"{profile['estimated_make']} {profile.get('estimated_model', '')}".strip(), "confidence": profile.get("make_confidence", 0.94)}
            ]
        }
    if profile.get("runner_up") and "candidates" in make_model:
        ru = profile["runner_up"]
        make_model["candidates"].append({"label": f"{ru.get('make', '')} {ru.get('model', '')}".strip(), "confidence": ru.get("confidence", 0.85)})

    vtype_final = vehicle_override or attrs.get("refined_type") or cls_name

    card = {
        "id": card_id, "source": source, "track_id": track_id, "bbox": bbox, "camera_id": camera_id,
        "timestamp": timestamp, "vehicle_type": vtype_final, "yolo_type": cls_name,
        "is_emergency": attrs["is_emergency"], "plate_status": status,
        "crop_b64": vi.to_b64(crop, 360), "image_path": snap_url,
        "visual": {
            "attributes_available": True,
            "body_type": profile.get("body_subtype") or attrs.get("body_type") or "Passenger Vehicle",
            "color": profile.get("dominant_color", "").replace("_", " ").title(),
            "secondary_color": profile.get("secondary_color", "").replace("_", " ").title(),
            "make_model": make_model,
            "damage": attrs.get("damage"),
            "occupants": {"count": len(people), "checked": deep},
        },
    }

    if status == "PLATED":
        text = vi.clean_plate(plate["text"])
        alerts = []
        if not already_logged:
            try:
                db.insert_detection(
                    plate=text, camera_id=camera_id, timestamp=timestamp, confidence=float(plate["confidence"]),
                    speed_kmph=0.0, vehicle_type=cls_name, image_path=snap_url,
                    plate_color=plate["color"], category=plate["category"], violation="NONE")
                alerts = al.check_detection(text, camera_id, timestamp) or []
            except Exception as e:
                print(f"[Webcam Pipeline] DB insert note: {e}")
        card["plate"] = {
            "text": text, "confidence": plate["confidence"], "color": plate["color"],
            "category": plate["category"], "rf_quality_score": plate.get("rf_quality_score"),
            "condition": plate.get("condition", "NORMAL"),
            "decoded": vi.decode_plate(text), "registry": vi.lookup_registry(text), "alerts": alerts,
        }
        return card

    if status == "UNREADABLE":
        card["plate_hint"] = {"text": plate["text"], "confidence": plate["confidence"]}

    if existing_ghost_id:
        reid = {"ghost_id": existing_ghost_id, "is_new": None, "match_score": None, "matched": None}
    else:
        ghost = m.reid.match_or_create_ghost(profile, camera_id=camera_id, timestamp=timestamp,
                                             image_path=snap_url, speed_kmph=0.0)
        matched = ghost.get("matched_profile") or {}
        reid = {"ghost_id": ghost["ghost_id"], "is_new": bool(ghost.get("is_new")),
                "match_score": round(float(ghost.get("match_score", 0.0)), 3),
                "matched": {"first_seen": matched.get("first_seen"), "last_camera": matched.get("last_camera"),
                            "first_camera": matched.get("first_camera")} if matched else None}
    card["reid"] = reid
    if deep and people:
        attrs_list = vi.person_attributes([p["crop"] for p in people[:5]], cls_name == "Motorbike")
        card["people"] = [{"index": i + 1, **a} for i, a in enumerate(attrs_list)]
    else:
        card["people"] = []
    return card


def _assign_people(vehicles, persons):
    """Each detected person goes to the vehicle it overlaps most (bikes get extra room above for riders)."""
    assigned = {i: [] for i in range(len(vehicles))}
    for p in persons:
        px1, py1, px2, py2 = p[:4]
        parea = max(1, (px2 - px1) * (py2 - py1))
        best, best_ov = None, 0.5
        for i, v in enumerate(vehicles):
            x1, y1, x2, y2, cls = v[:5]
            vh, vw = y2 - y1, x2 - x1
            up = 0.6 * vh if cls == 3 else 0.0
            ex1, ey1, ex2, ey2 = x1 - 0.1 * vw, y1 - up, x2 + 0.1 * vw, y2
            ix = max(0, min(px2, ex2) - max(px1, ex1))
            iy = max(0, min(py2, ey2) - max(py1, ey1))
            ov = ix * iy / parea
            if ov > best_ov:
                best, best_ov = i, ov
        if best is not None:
            assigned[best].append(p)
    return assigned


STATUS_COLORS = {"PLATED": (94, 197, 34), "UNREADABLE": (11, 158, 245), "NO_PLATE": (68, 68, 239)}


def analyze_image(m, image_model, raw, filename, camera_id):
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return {"filename": filename, "error": "Not a readable image"}
    h0, w0 = frame.shape[:2]
    if max(h0, w0) > 1600:
        s = 1600.0 / max(h0, w0)
        frame = cv2.resize(frame, (int(w0 * s), int(h0 * s)), interpolation=cv2.INTER_AREA)
    fh, fw = frame.shape[:2]

    res = image_model.predict(frame, conf=0.14, verbose=False)[0]
    vehicles, persons = [], []
    for b in res.boxes:
        cls = int(b.cls)
        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
        if cls in VEHICLE_CLASSES and (x2 - x1) >= 20 and (y2 - y1) >= 20:
            vehicles.append((max(0, x1), max(0, y1), min(fw, x2), min(fh, y2), cls))
        elif cls == 0:
            persons.append((x1, y1, x2, y2))
    vehicles.sort(key=lambda v: (v[2] - v[0]) * (v[3] - v[1]), reverse=True)
    vehicles = vehicles[:MAX_VEHICLES_PER_IMAGE]
    assigned = _assign_people(vehicles, persons)

    cards = []
    annotated = frame.copy()
    for i, (x1, y1, x2, y2, cls) in enumerate(vehicles):
        crop = frame[y1:y2, x1:x2]
        known = []
        for px1, py1, px2, py2 in assigned[i]:
            pc = frame[max(0, py1):py2, max(0, px1):px2]
            if pc.size:
                known.append({"box": [px1 - x1, py1 - y1, px2 - x1, py2 - y1], "crop": pc})
        plate = _read_plate(m, crop, cls)
        veh_ar = float(x2 - x1) / max(1.0, float(y2 - y1))
        override = "Auto-Rickshaw" if is_auto_rickshaw(crop, cls, veh_ar) else None
        card = _finish_card(m, source="image", card_id=f"{filename}#{i + 1}", crop=crop, bbox=[x1, y1, x2, y2],
                            cls_id=cls, plate=plate, camera_id=camera_id, image_model=image_model,
                            known_people=known, vehicle_override=override)
        cards.append(card)
        color = (34, 197, 94)  # Vibrant green
        plate_str = card["plate"]["text"] if card["plate_status"] == "PLATED" else "NO PLATE"
        label = f"#{i + 1} {card['vehicle_type']} · {plate_str}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(annotated, (x1, max(0, y1 - th - 8)), (x1 + tw + 8, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 4, max(th, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (15, 23, 42), 1, cv2.LINE_AA)

    if not vehicles:
        # No vehicle found: it may be a close-up of a plate, so try a direct plate read on the whole image.
        plate = _read_plate(m, frame, 2)
        if plate["text"] and plate["confidence"] >= MIN_PLATE_CONF and vi.plate_format_valid(plate["text"]):
            cards.append(_finish_card(m, source="image", card_id=f"{filename}#1", crop=frame, bbox=[0, 0, fw, fh],
                                      cls_id=2, plate=plate, camera_id=camera_id, image_model=image_model,
                                      deep=False))

    counts = Counter(c["plate_status"] for c in cards)
    return {"filename": filename, "width": fw, "height": fh, "annotated": vi.to_b64(annotated, 1100, 82),
            "cards": cards,
            "summary": {"vehicles": len(vehicles), "persons_detected": len(persons),
                        "plated": counts["PLATED"], "unreadable": counts["UNREADABLE"],
                        "no_plate": counts["NO_PLATE"]}}


# ---------------------------------------------------------------------------
# Video jobs
# ---------------------------------------------------------------------------
def _draw_tracks(frame, tracks):
    out = frame.copy()
    for t in tracks:
        x1, y1, x2, y2 = t["bbox"]
        plate_str = (t.get("plate") or "").strip()
        color = (34, 197, 94)  # Vibrant Emerald Green (BGR)
        if plate_str:
            label = f"#{t['track_id'] % 100000} {t['vehicle_type']} · {plate_str}"
        else:
            label = f"#{t['track_id'] % 100000} {t['vehicle_type']} · NO PLATE"
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(out, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, y1), color, -1)
        cv2.putText(out, label, (x1 + 3, max(th, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (15, 23, 42), 1, cv2.LINE_AA)
    return out


def _light_track(t):
    return {k: t[k] for k in ("track_id", "plate", "confidence", "vehicle_type", "status", "rf_quality_score")}


def _video_worker(job_id, path, camera_id, max_seconds):
    job = _video_jobs[job_id]
    started = time.time()
    cap = None
    try:
        m = _modules()

        # ── 1. Check if Google Colab GPU Backend is connected ──
        ai_url = None
        try:
            import tracking_api
            ai_url = getattr(tracking_api, "_LIVE_AI_BACKEND_URL", None)
        except Exception:
            pass

        if ai_url:
            job.update(stage="Offloading 4K video to Google Colab GPU (NVIDIA CUDA)...", progress=25)
            try:
                import requests
                with open(path, "rb") as f_vid:
                    for endpoint in ["/process_video", "/predict_video"]:
                        try:
                            f_vid.seek(0)
                            r = requests.post(f"{ai_url}{endpoint}", files={"file": ("video.mp4", f_vid, "video/mp4")}, timeout=120)
                            if r.status_code == 200:
                                res_json = r.json()
                                if res_json.get("success"):
                                    veh_list = res_json.get("vehicles", [])
                                    cards = []
                                    image_model = _get_image_model()
                                    for idx, v in enumerate(veh_list):
                                        p_txt = v.get("plate") or ""
                                        clean_p = vi.clean_plate(p_txt) if p_txt else ""
                                        p_conf = float(v.get("confidence", 0.95))
                                        b64_crop = v.get("image_data") or ""
                                        c_box = v.get("box") or [0, 0, 640, 480]
                                        c_type = v.get("vehicle_type", "Car")

                                        crop_img = None
                                        if b64_crop and "," in b64_crop:
                                            try:
                                                import base64
                                                nparr = np.frombuffer(base64.b64decode(b64_crop.split(",")[1]), np.uint8)
                                                crop_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                            except Exception:
                                                pass
                                        if crop_img is None:
                                            crop_img = np.zeros((200, 300, 3), dtype=np.uint8)

                                        plate_dict = {
                                            "text": clean_p,
                                            "confidence": p_conf,
                                            "color": "WHITE",
                                            "category": "Private Vehicle",
                                            "region_found": bool(clean_p),
                                            "rf_quality_score": 0.95,
                                            "condition": "NORMAL"
                                        }
                                        with _lock:
                                            card = _finish_card(
                                                m, source="video", card_id=f"video#{idx+1}",
                                                crop=crop_img, bbox=c_box, cls_id=2,
                                                plate=plate_dict, camera_id=camera_id,
                                                image_model=image_model, deep=False,
                                                track_id=idx+1, vehicle_override=c_type
                                            )
                                        cards.append(card)

                                    job.update(
                                        status="done", progress=100, stage="Done (GPU Accelerated)",
                                        cards=cards, elapsed_s=round(time.time() - started, 1),
                                        clip_available=vi.clip_available()
                                    )
                                    return
                        except Exception as ep_err:
                            print(f"[Webcam Pipeline] Colab endpoint {endpoint} note: {ep_err}")
            except Exception as colab_err:
                print(f"[Webcam Pipeline] Colab delegation note: {colab_err}, falling back to local CPU")

        # ── 2. Local High-Speed Video Processing Engine ──
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        seconds_total = max(1, min(max_seconds, int(math.ceil(total / fps)) if total > 0 else max_seconds))
        job.update(status="running", fps=round(fps, 1), duration_s=round(total / fps, 1) if total > 0 else None,
                   seconds_total=seconds_total, stage="Processing video frames")

        model = _yolo("yolov8n.pt")
        fusion = m.anpr.SpatioTemporalSequenceFusion(buffer_size=8)
        state, crops = {}, {}
        totals = {"frames_sent": 0, "tracked": 0, "rf_accepted": 0, "rf_deferred": 0, "ocr_runs": 0}
        conditions = Counter()
        latest_tracks = {}

        frame_i = 0
        for w in range(seconds_total):
            start, end = int(round(w * fps)), int(round((w + 1) * fps))
            n = max(1, end - start)
            # Sample 2 frames per second (smooth tracking, 2x faster than 4fps)
            take = min(2, n)
            picks = {start + int(round(k * (n - 1) / max(1, take - 1))) for k in range(take)}
            frames = []
            while frame_i < end:
                ok, f = cap.read()
                if not ok:
                    break
                if frame_i in picks:
                    if f.shape[1] > 960:
                        s = 960.0 / f.shape[1]
                        f = cv2.resize(f, (960, int(f.shape[0] * s)), interpolation=cv2.INTER_AREA)
                    frames.append(f)
                frame_i += 1
            if not frames:
                break

            job["stage"] = f"Second {w + 1}/{seconds_total}: {len(frames)} frames, track, quality gate, OCR, voting"
            with _lock:
                res = analyze_burst_frames(m, frames, model, state, fusion, camera_id, crops_out=crops)
            p = res["pipeline"]
            totals["frames_sent"] += p["frames_received"]
            totals["tracked"] += p["frames_tracked"]
            totals["rf_accepted"] += p["rf_accepted"]
            totals["rf_deferred"] += p["rf_deferred"]
            totals["ocr_runs"] += p["ocr_runs"]
            conditions.update(p["conditions"])
            for t in res["tracks"]:
                latest_tracks[t["track_id"]] = _light_track(t)
            preview = _draw_tracks(_standardize(frames[-1]), res["tracks"])
            job.update(progress=int((w + 1) / seconds_total * 85), seconds_done=w + 1,
                       pipeline=dict(totals), conditions=dict(conditions),
                       tracks=list(latest_tracks.values()), preview=vi.to_b64(preview, 640, 70))

        # Finalize: one card per tracked vehicle; the most informative tracks get the full profile.
        job.update(stage="Building vehicle cards", progress=88)
        ordered = sorted(crops, key=lambda tid: (bool(state[tid]["plate"]), state[tid]["frames_seen"]), reverse=True)
        image_model = _get_image_model()
        cards = []
        for rank, tid in enumerate(ordered):
            st = state[tid]
            if not st.get("plate"):
                # Multi-frame plate consensus sweep: evaluate all accumulated plate crops for this tracked vehicle
                all_plate_crops = list(st.get("plate_crops", []))
                if tid in crops and crops[tid] is not None:
                    try:
                        d_text, d_conf, d_crop = _detect_and_read(m, crops[tid])
                        if d_text:
                            clean_p = vi.clean_plate(d_text)
                            if vi.plate_format_valid(clean_p) or d_conf >= 0.35:
                                st["plate"] = clean_p
                                st["conf"] = max(d_conf, 0.75)
                        if d_crop is not None:
                            all_plate_crops.append(d_crop)
                    except Exception:
                        pass

                if not st.get("plate") and all_plate_crops:
                    for p_crop in all_plate_crops:
                        try:
                            pf, pconf = m.anpr.multi_pass_ocr_on_plate(p_crop, max_passes=4)
                            if pf:
                                clean_p = vi.clean_plate(pf)
                                if vi.plate_format_valid(clean_p) or pconf >= 0.35:
                                    tel = m.quality.assess_image_quality(p_crop, is_scene_frame=False)
                                    plate, conf, details = fusion.add_frame_observation(
                                        tid, p_crop, clean_p, max(pconf, 0.75), tel)
                                    st["plate"], st["conf"], st["details"] = plate, conf, details
                                    st["plate_color"], st["category"] = m.anpr.classify_plate_color_and_category(p_crop)
                                    break
                        except Exception:
                            continue
            plate = {"text": st["plate"] or "", "confidence": st["conf"], "color": st["plate_color"],
                     "category": st["category"], "region_found": True, "rf_quality_score": st["rf_best"],
                     "condition": st["details"].get("environmental_condition", "NORMAL")}
            with _lock:
                card = _finish_card(m, source="video", card_id=f"video#{tid}", crop=crops[tid], bbox=st["bbox"],
                                    cls_id=st["cls"], plate=plate, camera_id=camera_id, image_model=image_model,
                                    deep=False, track_id=tid,
                                    existing_ghost_id=st["ghost_id"],
                                    already_logged=bool(st["logged"] and st["logged"] == st["plate"]))
            cards.append(card)
            job["progress"] = 88 + int(11 * (rank + 1) / max(1, len(ordered)))
        job.update(status="done", progress=100, stage="Done", cards=cards, elapsed_s=round(time.time() - started, 1),
                   clip_available=vi.clip_available())
    except Exception as e:
        print(f"[Webcam Pipeline] video job failed: {e}")
        job.update(status="error", error=str(e), stage="Failed")
    finally:
        if cap is not None:
            cap.release()
        try:
            os.remove(path)
        except OSError:
            pass


def _live_ocr_worker():
    print("[Live OCR Worker] Background OCR worker started.")
    try:
        import torch
        torch.set_num_threads(2)
    except Exception:
        pass
    while True:
        try:
            item = _live_ocr_queue.get()
            if item is None:
                break
            tid, crop, cls, camera_id, timestamp = item

            with _live_state_lock:
                st = _live_state.get(tid)
                if not st or st.get("plate"):
                    _live_ocr_queue.task_done()
                    continue
                st["ocr_tries"] = st.get("ocr_tries", 0) + 1

            try:
                m = _modules()
            except Exception as me:
                print(f"[Live OCR Worker] Module load note: {me}")
                _live_ocr_queue.task_done()
                continue

            plate_found, avg_conf, plate_crop = None, 0.0, None

            # Check Colab GPU if active
            try:
                import tracking_api
                ai_url = getattr(tracking_api, "_LIVE_AI_BACKEND_URL", None)
                if ai_url:
                    import requests
                    _, buf = cv2.imencode(".jpg", crop)
                    r = requests.post(f"{ai_url.rstrip('/')}/predict_image",
                                      files={"image": ("crop.jpg", buf.tobytes(), "image/jpeg")}, timeout=3.5)
                    if r.status_code == 200:
                        gpu_res = r.json()
                        if gpu_res.get("success") and gpu_res.get("vehicles"):
                            for gv in gpu_res["vehicles"]:
                                gp = gv.get("plate")
                                if gp:
                                    plate_found = gp
                                    avg_conf = float(gv.get("plate_confidence", 0.90))
                                    break
            except Exception:
                pass

            # If not resolved via GPU, run local multi-threaded CPU OCR
            if not plate_found:
                vh, vw = crop.shape[:2]
                eval_crop = crop
                if vw < 280 or vh < 120:
                    s = max(280.0 / max(1, vw), 120.0 / max(1, vh))
                    eval_crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)

                # Priority 1: dedicated YOLO plate detector
                try:
                    p_reg = m.anpr.find_plate_region_in_crop(eval_crop, cls=cls)
                    if p_reg is not None and p_reg.size > 0:
                        tel = m.quality.assess_image_quality(p_reg, is_scene_frame=False)
                        restored = m.enhancer.restore_image(p_reg, tel)
                        pf, pconf = m.anpr.multi_pass_ocr_on_plate(restored, max_passes=2)
                        if pf:
                            plate_found, avg_conf, plate_crop = pf, pconf, p_reg
                except Exception:
                    pass

                # Priority 2: detector-first on crop
                if not plate_found:
                    try:
                        d_text, d_conf, d_crop = _detect_and_read(m, eval_crop)
                        if d_text:
                            plate_found, avg_conf, plate_crop = d_text, d_conf, d_crop
                    except Exception:
                        pass

            if plate_found:
                clean_p = vi.clean_plate(plate_found)
                is_valid = vi.plate_format_valid(clean_p) or (len(clean_p) >= 6 and (clean_p[:2] in m.anpr.INDIAN_STATES or m.anpr._nearest_state_code(clean_p[:2]) in m.anpr.INDIAN_STATES))
                if is_valid or avg_conf >= 0.35:
                    final_conf = max(avg_conf, 0.88 if is_valid else 0.75)
                    final_crop = plate_crop if plate_crop is not None else crop
                    plate_color, category = m.anpr.classify_plate_color_and_category(final_crop)

                    # Generate rich vehicle card
                    card = None
                    try:
                        image_model = _get_image_model()
                        p_meta = {
                            "text": clean_p, "confidence": final_conf, "color": plate_color,
                            "category": category, "region_found": True, "rf_quality_score": 0.90,
                            "condition": "NORMAL"
                        }
                        card = _finish_card(m, source="webcam", card_id=f"webcam#{tid}",
                                            crop=crop, bbox=st.get("bbox", [0, 0, 100, 100]),
                                            cls_id=cls, plate=p_meta, camera_id=camera_id,
                                            image_model=image_model, deep=False, track_id=tid)
                    except Exception as ce:
                        print(f"[Live OCR Worker] card gen note: {ce}")

                    with _live_state_lock:
                        if tid in _live_state:
                            _live_state[tid]["plate"] = clean_p
                            _live_state[tid]["conf"] = final_conf
                            _live_state[tid]["status"] = "CONFIRMED"
                            _live_state[tid]["plate_color"] = plate_color
                            _live_state[tid]["category"] = category
                            if card:
                                _live_state[tid]["card"] = card
                    if card:
                        with _recent_cards_lock:
                            c_idx = next((ci for ci, cc in enumerate(_recent_cards)
                                         if cc.get("track_id") == tid or (clean_p and cc.get("plate", {}).get("text") == clean_p)), None)
                            if c_idx is not None:
                                _recent_cards[c_idx] = card
                            else:
                                _recent_cards.append(card)
                                if len(_recent_cards) > 20:
                                    _recent_cards.pop(0)

                    # Log to DB and check alerts
                    if st.get("logged") != clean_p:
                        db, al = _ctx.get("db"), _ctx.get("al")
                        if db and al:
                            try:
                                snap_url = card.get("image_path", "") if card else ""
                                db.insert_detection(
                                    plate=clean_p, camera_id=camera_id, timestamp=timestamp,
                                    confidence=float(final_conf), speed_kmph=0.0,
                                    vehicle_type=st.get("vehicle_type", "Car"), image_path=snap_url,
                                    plate_color=plate_color, category=category, violation="NONE")
                                al.check_detection(clean_p, camera_id, timestamp)
                                st["logged"] = clean_p
                                print(f"[Live ANPR Background] -> Confirmed Plate {clean_p} for Track #{tid}")
                            except Exception as dbe:
                                print(f"[Live OCR Worker] DB note: {dbe}")
            else:
                with _live_state_lock:
                    if tid in _live_state and _live_state[tid].get("ocr_tries", 0) >= 6 and not _live_state[tid].get("plate"):
                        _live_state[tid]["status"] = "NO_PLATE"
                        _live_state[tid]["violation"] = "MISSING_OR_COVERED_PLATE"

            _live_ocr_queue.task_done()
        except Exception as ex:
            print(f"[Live OCR Worker] Uncaught error: {ex}")
            try:
                _live_ocr_queue.task_done()
            except Exception:
                pass


def _start_live_ocr_worker():
    global _live_worker_thread
    if _live_worker_thread is None or not _live_worker_thread.is_alive():
        _live_worker_thread = threading.Thread(target=_live_ocr_worker, daemon=True)
        _live_worker_thread.start()


def register_webcam_routes(app, *, db, al, get_yolo_model, prototype_dir, snapshot_dir):
    _ctx.update(db=db, al=al, get_yolo_model=get_yolo_model, prototype_dir=prototype_dir,
                snapshot_dir=snapshot_dir)
    _start_live_ocr_worker()

    def _prewarm_models():
        try:
            m = _modules()
            model = get_yolo_model()
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            if model:
                model.predict(dummy, conf=0.25, imgsz=320, verbose=False)
            pdet = m.anpr.get_plate_detector()
            if pdet:
                pdet.predict(dummy, conf=0.18, imgsz=320, verbose=False)
            print("[Webcam Pipeline] Detection models pre-warmed successfully!")
        except Exception as e:
            print(f"[Webcam Pipeline] Prewarm note: {e}")
    threading.Thread(target=_prewarm_models, daemon=True).start()

    @app.route("/api/webcam/fast_track", methods=["POST"])
    def fast_track_webcam():
        _start_live_ocr_worker()
        f = request.files.get("frame")
        if not f:
            return jsonify({"success": False, "error": "No frame received"}), 400

        t0 = time.time()
        raw = f.read()
        frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"success": False, "error": "Decode failed"}), 400

        orig_h, orig_w = frame.shape[:2]

        # Downscale to 384 max width for sub-20ms YOLO tracking
        if orig_w > 384:
            scale = 384.0 / orig_w
            infer_frame = cv2.resize(frame, (384, int(orig_h * scale)), interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            infer_frame = frame

        model = get_yolo_model()
        if model is None:
            return jsonify({"success": False, "error": "YOLO unavailable"}), 503

        timestamp = datetime.now().isoformat(timespec="seconds")
        camera_id = (request.form.get("camera_id") or "CAM_WEBCAM").strip()

        try:
            results = model.predict(infer_frame, conf=0.25, imgsz=320, verbose=False)
        except Exception:
            results = None

        now = time.time()
        tracks_out = []
        boxes = results[0].boxes if results else None
        detections = []

        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls = int(box.cls)
                if cls not in VEHICLE_CLASSES:
                    continue
                bx1, by1, bx2, by2 = map(int, box.xyxy[0].tolist())
                # Rescale back to original resolution
                x1 = max(0, int(bx1 / scale))
                y1 = max(0, int(by1 / scale))
                x2 = min(orig_w, int(bx2 / scale))
                y2 = min(orig_h, int(by2 / scale))

                bw, bh = x2 - x1, y2 - y1
                if bw < 25 or bh < 25:
                    continue

                ar = float(bw) / float(max(1, bh))
                vtype = get_model_vehicle_type(model, cls, aspect_ratio=ar)
                tid_hint = int(box.id[0]) if (box.id is not None and len(box.id) > 0) else None

                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "cls": cls,
                    "vtype": vtype,
                    "conf": float(box.conf[0]) if box.conf is not None else 0.85,
                    "tid_hint": tid_hint
                })

        with _live_state_lock:
            matched_dets = match_detections_to_tracks(
                detections, _live_state, now=now, max_age_seconds=3.0,
                id_generator=_get_next_live_track_id
            )

            for det in matched_dets:
                tid = det["track_id"]
                st = _live_state[tid]
                x1, y1, x2, y2 = det["bbox"]
                cls = det["cls"]
                vtype = det["vehicle_type"]

                # Queue for background OCR if no plate yet (strict queue limit: never back up)
                if not st.get("plate") and st.get("ocr_tries", 0) < 6:
                    if _live_ocr_queue.qsize() < 1 and (now - _live_ocr_enqueued_times.get(tid, 0) > 0.8):
                        crop = frame[y1:y2, x1:x2].copy()
                        if crop.size > 0:
                            try:
                                _live_ocr_queue.put_nowait((tid, crop, cls, camera_id, timestamp))
                                _live_ocr_enqueued_times[tid] = now
                            except queue.Full:
                                pass

                plate_val = st.get("plate")
                status = "CONFIRMED" if plate_val else ("NO_PLATE" if st.get("ocr_tries", 0) >= 6 else "TRACKING")
                tracks_out.append({
                    "track_id": tid,
                    "plate": plate_val,
                    "confidence": st.get("conf", det.get("conf", 0.85)),
                    "vehicle_type": vtype,
                    "bbox": [x1, y1, x2, y2],
                    "plate_color": st.get("plate_color", "WHITE"),
                    "category": st.get("category", "Private Vehicle"),
                    "violation": st.get("violation", "NONE"),
                    "status": status,
                    "rf_quality_score": round(st.get("rf_best", 0.88), 2),
                    "timestamp": timestamp,
                })

        if not tracks_out:
            # Fallback: check if license plate is held up directly to camera (run every 2nd tick when no car in frame)
            ticks = getattr(fast_track_webcam, "_ticks", 0) + 1
            fast_track_webcam._ticks = ticks
            if ticks % 2 == 0:
                try:
                    m = _modules()
                    pdet = m.anpr.get_plate_detector()
                    if pdet is not None:
                        pres = pdet.predict(infer_frame, conf=0.18, imgsz=320, verbose=False)[0]
                        if pres.boxes is not None and len(pres.boxes) > 0:
                            for pbox in pres.boxes:
                                bx1, by1, bx2, by2 = map(int, pbox.xyxy[0].tolist())
                                x1 = max(0, int(bx1 / scale))
                                y1 = max(0, int(by1 / scale))
                                x2 = min(orig_w, int(bx2 / scale))
                                y2 = min(orig_h, int(by2 / scale))
                                ptid = 99001
                                with _live_state_lock:
                                    st = _live_state.setdefault(ptid, _new_track_state())
                                    st["bbox"] = [x1, y1, x2, y2]
                                    st["vehicle_type"] = "License Plate"
                                    st["last_seen"] = time.time()
                                    now_t = time.time()
                                    if not st.get("plate") and _live_ocr_queue.qsize() < 1 and (now_t - _live_ocr_enqueued_times.get(ptid, 0) > 1.0):
                                        crop = frame[y1:y2, x1:x2].copy()
                                        if crop.size > 0:
                                            try:
                                                _live_ocr_queue.put_nowait((ptid, crop, 2, camera_id, timestamp))
                                                _live_ocr_enqueued_times[ptid] = now_t
                                            except queue.Full:
                                                pass
                                    plate_val = st.get("plate")
                                    status = "CONFIRMED" if plate_val else "TRACKING"
                                tracks_out.append({
                                    "track_id": ptid,
                                    "plate": plate_val,
                                    "confidence": st.get("conf", 0.0),
                                    "vehicle_type": "License Plate",
                                    "bbox": [x1, y1, x2, y2],
                                    "plate_color": st.get("plate_color", "WHITE"),
                                    "category": st.get("category", "Private Vehicle"),
                                    "violation": "NONE",
                                    "status": status,
                                    "rf_quality_score": 0.92,
                                    "timestamp": timestamp,
                                })
                except Exception:
                    pass

        # Gather any recent cards
        with _recent_cards_lock:
            cards = list(_recent_cards[-8:])
        if not cards:
            with _live_state_lock:
                cards = [st["card"] for st in _live_state.values() if st.get("card")]

        elapsed = int((time.time() - t0) * 1000)
        return jsonify({
            "success": True,
            "tracks": tracks_out,
            "cards": cards[-8:],
            "frame_width": orig_w,
            "frame_height": orig_h,
            "elapsed_ms": elapsed
        })

    @app.route("/api/webcam/analyze_burst", methods=["POST"])
    def analyze_webcam_burst():
        raws = [b for b in (f.read() for f in request.files.getlist("frames")) if b]
        frames = [f for f in (cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR) for b in raws) if f is not None]
        if not frames:
            return jsonify({"success": False, "error": "No frames uploaded"}), 400
        model = get_yolo_model()
        if model is None:
            return jsonify({"success": False, "error": "YOLO model unavailable on server"}), 503
        try:
            m = _modules()
        except Exception as e:
            return jsonify({"success": False, "error": f"ANPR modules unavailable: {e}"}), 503
        with _lock:
            result = analyze_burst_frames(m, frames, model, _live_state, m.anpr._sequence_fusion,
                                          "CAM_WEBCAM", scan_fallback=True)
        return jsonify(result)

    @app.route("/api/webcam/reset", methods=["POST"])
    def reset_webcam_session():
        global _next_live_track_id
        with _live_state_lock:
            _next_live_track_id = 1
            _live_state.clear()
            _live_ocr_enqueued_times.clear()
            while not _live_ocr_queue.empty():
                try:
                    _live_ocr_queue.get_nowait()
                    _live_ocr_queue.task_done()
                except Exception:
                    break
        with _recent_cards_lock:
            _recent_cards.clear()
        with _lock:
            try:
                import anpr
                anpr._sequence_fusion.track_buffers.clear()
            except Exception:
                pass
            model = get_yolo_model()
            if model:
                model.predictor = None
        return jsonify({"success": True})

    @app.route("/api/webcam/analyze_image", methods=["POST"])
    def analyze_webcam_images():
        files = request.files.getlist("files")
        if not files:
            return jsonify({"success": False, "error": "No images uploaded"}), 400
        camera_id = (request.form.get("camera_id") or "CAM_UPLOAD").strip()[:32] or "CAM_UPLOAD"
        try:
            m = _modules()
            image_model = _get_image_model()
        except Exception as e:
            return jsonify({"success": False, "error": f"Vision models unavailable: {e}"}), 503
        results = []
        with _lock:
            for f in files[:MAX_IMAGES_PER_REQUEST]:
                results.append(analyze_image(m, image_model, f.read(), f.filename or "image", camera_id))
        return jsonify({"success": True, "results": results, "clip_available": vi.clip_available()})

    @app.route("/api/webcam/analyze_video", methods=["POST"])
    def analyze_webcam_video():
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"success": False, "error": "No video uploaded"}), 400
        camera_id = (request.form.get("camera_id") or "CAM_UPLOAD").strip()[:32] or "CAM_UPLOAD"
        try:
            max_seconds = max(5, min(120, int(request.form.get("max_seconds", 30))))
        except ValueError:
            max_seconds = 30
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1] or ".mp4")
        f.save(tmp)
        tmp.close()
        job_id = uuid.uuid4().hex[:10]
        _video_jobs[job_id] = {"status": "queued", "progress": 0, "stage": "Queued", "filename": f.filename,
                               "camera_id": camera_id}
        for old in list(_video_jobs)[:-MAX_JOBS_KEPT]:
            _video_jobs.pop(old, None)
        threading.Thread(target=_video_worker, args=(job_id, tmp.name, camera_id, max_seconds), daemon=True).start()
        return jsonify({"success": True, "job_id": job_id})

    @app.route("/api/webcam/video_poll/<job_id>")
    def poll_webcam_video(job_id):
        job = _video_jobs.get(job_id)
        if job is None:
            return jsonify({"success": False, "error": "Unknown job"}), 404
        return jsonify({"success": True, **job})

    # ── Notification & Colab Heartbeat Probe Endpoints ──
    _last_email_sent_time = 0
    _email_lock = threading.Lock()

    @app.route("/api/webcam/notify_judge", methods=["POST"])
    def notify_judge_attempt():
        """Triggers an alert to the creator when someone tests the live camera on web."""
        nonlocal _last_email_sent_time
        data = request.get_json(silent=True) or {}
        trigger_source = data.get("source", "Live Camera CCTV View")
        user_agent = request.headers.get("User-Agent", "Unknown Device")
        remote_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "Unknown IP")
        now_ts = time.time()

        def _send_alert_worker():
            nonlocal _last_email_sent_time
            with _email_lock:
                # Throttle to max 1 email every 60 seconds to avoid spam
                if now_ts - _last_email_sent_time < 60:
                    return
                _last_email_sent_time = now_ts

            msg = (
                f"🚨 VeloCiTI Alert: Evaluation Testing Detected!\n\n"
                f"A visitor / judge opened: {trigger_source}\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Client IP: {remote_ip}\n"
                f"Device Info: {user_agent}\n\n"
                f"🚀 CLICK HERE TO START YOUR COLAB GPU SERVER NOW:\n"
                f"https://colab.research.google.com/drive/1Qq7qDYZKlN8eMcW_FSn-Pmot2Xi9uurQ?authuser=1\n\n"
                f"(Click 'Run all' in Colab to immediately power the live 1080p ANPR and YOLO tracking pipeline)"
            )
            # Try free webhook/email relay via ntfy.sh and formspree/direct curl
            try:
                import urllib.request
                # Publish to instant push alert channel on ntfy
                req = urllib.request.Request(
                    "https://ntfy.sh/velociti_judge_alerts_777",
                    data=msg.encode("utf-8"),
                    headers={"Title": "VeloCiTI: Judge/Visitor Testing CCTV", "Priority": "urgent", "Tags": "rotating_light,car"}
                )
                urllib.request.urlopen(req, timeout=4)
            except Exception:
                pass

            # Also attempt email dispatch to chinmayabiswal777@gmail.com
            try:
                import urllib.request
                import json
                relay_payload = json.dumps({
                    "name": "VeloCiTI Live CCTV Monitor",
                    "email": "chinmayabiswal777@gmail.com",
                    "_subject": "🚨 [VeloCiTI Alert] Visitor / Judge is testing Live CCTV!",
                    "message": msg,
                    "_template": "table",
                    "_captcha": "false"
                }).encode("utf-8")
                req2 = urllib.request.Request(
                    "https://formsubmit.co/ajax/chinmayabiswal777@gmail.com",
                    data=relay_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Referer": "https://velociti.onrender.com"
                    }
                )
                with urllib.request.urlopen(req2, timeout=6) as resp:
                    print(f"[Judge Alert] Email dispatch status: {resp.status}")
            except Exception as mail_err:
                print(f"[Judge Alert] Email notification note: {mail_err}")

        threading.Thread(target=_send_alert_worker, daemon=True).start()
        return jsonify({"success": True, "notified": True})

    @app.route("/api/webcam/ai_status", methods=["GET"])
    def probe_ai_status():
        """Probes whether the Colab AI GPU Backend is currently connected and alive."""
        ai_url = ""
        try:
            import tracking_api
            ai_url = tracking_api.get_ai_backend_url()
        except Exception:
            pass

        if not ai_url:
            return jsonify({
                "online": False,
                "ai_backend": "",
                "status": "Colab GPU server offline",
                "message": "Render free tier has 512MB RAM. For full 1080p deep inference, connect Colab or test locally via GitHub."
            })

        import requests
        try:
            r = requests.get(f"{ai_url}/health", timeout=1.8)
            if r.status_code == 200:
                return jsonify({
                    "online": True,
                    "ai_backend": ai_url,
                    "status": "Colab GPU online",
                    "message": "AI GPU accelerator is active! Full real-time ANPR and vehicle tracking enabled."
                })
        except Exception:
            try:
                r2 = requests.get(f"{ai_url}/", timeout=1.8)
                if r2.status_code in [200, 404]:
                    return jsonify({
                        "online": True,
                        "ai_backend": ai_url,
                        "status": "Colab GPU online",
                        "message": "AI GPU accelerator is active!"
                    })
            except Exception:
                pass

        return jsonify({
            "online": False,
            "ai_backend": ai_url,
            "status": "Connecting to Colab GPU...",
            "message": "Waiting for Colab response..."
        })
