"""
webcam_pipeline.py - Live webcam, uploaded-image and uploaded-video ANPR + vehicle intelligence.

  live burst : 24 frames/second from the browser -> BoT-SORT tracking -> IQA + Random Forest gate
               -> restoration + OCR on the best frames -> weighted consensus voting
  image      : stills -> vehicle detection -> plate check -> "plated" or "no plate" card
  video      : the same burst pipeline for every second of an uploaded clip, then cards per vehicle
"""

import math
import os
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

VEHICLE_CLASSES = {2: "Car", 3: "Motorbike", 5: "Bus", 7: "Truck"}
OCR_FRAMES_PER_TRACK = 4
DETECTOR_READS_PER_TRACK = 2  # detector-first reads are slow, so only the best frames of a track get one
RF_THRESHOLD = 0.42
MIN_PLATE_CONF = 0.6  # a plate read below this is shown as unreliable, never as a confirmed plate
FRAMES_PER_SECOND = 24
MAX_PROFILED_TRACKS = 12
MAX_IMAGES_PER_REQUEST = 8
MAX_VEHICLES_PER_IMAGE = 8
MAX_JOBS_KEPT = 10

_ctx = {}
_lock = threading.Lock()  # serialises model / OCR use across live, image and video work
_live_state = {}
_video_jobs = {}
_image_model = {"model": None}


def _modules():
    import anpr
    import enhancer
    import ml_selector
    import quality
    import vehicle_profiler
    import vehicle_reid
    return SimpleNamespace(anpr=anpr, enhancer=enhancer, ml=ml_selector, quality=quality,
                           prof=vehicle_profiler, reid=vehicle_reid)


def _yolo(weights_name):
    from ultralytics import YOLO
    path = os.path.join(_ctx["prototype_dir"], weights_name)
    return YOLO(path if os.path.exists(path) else weights_name)


def _get_image_model():
    if _image_model["model"] is None:
        _image_model["model"] = _yolo("yolov8s.pt")
    return _image_model["model"]


def _new_track_state():
    return {"plate": None, "conf": 0.0, "details": {}, "ocr_tries": 0, "plate_color": "WHITE",
            "category": "Private Vehicle", "logged": None, "ghost_id": None,
            "cls": 2, "bbox": None, "frames_seen": 0, "rf_best": 0.0}


def _standardize(frame):
    h, w = frame.shape[:2]
    if w > 960:
        return cv2.resize(frame, (960, int(h * 960.0 / w)), interpolation=cv2.INTER_AREA)
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
            results = model.track(frame, persist=True, tracker="botsort.yaml", conf=0.18, verbose=False)
        except Exception as e:
            print(f"[Webcam Pipeline] tracking note: {e}")
            continue
        frames_tracked += 1
        boxes = results[0].boxes if results else None
        if boxes is None or len(boxes) == 0:
            continue
        for box in boxes:
            cls = int(box.cls)
            if cls not in VEHICLE_CLASSES or box.id is None:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(fw, x2), min(fh, y2)
            if (x2 - x1) < 60 or (y2 - y1) < 50:
                continue
            tid = int(box.id[0])
            last_seen[tid] = {"bbox": [x1, y1, x2, y2], "cls": cls}
            veh_crop = frame[y1:y2, x1:x2]
            if veh_crop.size == 0:
                continue
            vh, vw = veh_crop.shape[:2]
            if vw < 280 or vh < 120:
                s = max(280.0 / max(1, vw), 120.0 / max(1, vh))
                veh_crop = cv2.resize(veh_crop, None, fx=s, fy=s, interpolation=cv2.INTER_LANCZOS4)
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
        vtype = VEHICLE_CLASSES[cls]
        st = state.setdefault(tid, _new_track_state())
        st["cls"], st["bbox"] = cls, last_seen[tid]["bbox"]
        st["frames_seen"] += len(cands)
        accepted = sorted((c for c in cands if c["accepted"]), key=lambda c: c["rf"], reverse=True)
        rf_accepted += len(accepted)
        rf_deferred += len(cands) - len(accepted)

        best = accepted[0] if accepted else max(cands, key=lambda c: c["rf"])
        if crops_out is not None and best["rf"] >= st["rf_best"]:
            crops_out[tid] = best["veh_crop"]
        st["rf_best"] = max(st["rf_best"], best["rf"])

        detector_budget = DETECTOR_READS_PER_TRACK
        for c in accepted[:OCR_FRAMES_PER_TRACK]:
            plate_found, avg_conf, plate_crop = None, 0.0, c["plate_region"]
            if c["plate_region"] is not None:
                restored = m.enhancer.restore_image(c["plate_region"], c["telemetry"])
                plate_found, avg_conf = m.anpr.multi_pass_ocr_on_plate(restored, max_passes=2)
            if not _plate_ok(plate_found, avg_conf) and detector_budget > 0:
                detector_budget -= 1
                d_text, d_conf, d_crop = _detect_and_read(m, c["veh_crop"])
                if d_text:
                    plate_found, avg_conf, plate_crop = d_text, d_conf, d_crop
            if not plate_found:
                restored = m.enhancer.restore_image(c["veh_crop"], c["telemetry"])
                plate_found, avg_conf = m.anpr.multi_pass_ocr_on_plate(restored, max_passes=2)
            ocr_runs += 1
            st["ocr_tries"] += 1
            if plate_found and avg_conf >= 0.45:
                crop_f = plate_crop if plate_crop is not None else c["veh_crop"]
                plate, conf, details = fusion.add_frame_observation(
                    tid, crop_f, plate_found, avg_conf, c["telemetry"])
                st["plate"], st["conf"], st["details"] = plate, conf, details
                st["plate_color"], st["category"] = m.anpr.classify_plate_color_and_category(crop_f)

        details = st["details"]
        violation = "NONE"
        label = st["plate"]
        if st["plate"]:
            gate = details.get("quality_gate_status", "CONFIRMED_CONSENSUS")
            status = "CONFIRMED" if gate == "CONFIRMED_CONSENSUS" else "BUFFERING"
        elif st["ocr_tries"] >= 3:
            status = "NO_PLATE"
            violation = "MISSING_OR_COVERED_PLATE"
            if not st["ghost_id"] and accepted:
                try:
                    prof = m.prof.extract_vehicle_profile(accepted[0]["veh_crop"], vehicle_type=vtype)
                    ghost = m.reid.match_or_create_ghost(
                        prof, camera_id=camera_id, timestamp=timestamp, image_path="", speed_kmph=0.0)
                    st["ghost_id"] = ghost["ghost_id"]
                except Exception as e:
                    print(f"[Webcam Pipeline] ghost profiling note: {e}")
            if st["ghost_id"]:
                label = f"{st['ghost_id']} (NO PLATE)"
        elif not accepted:
            status = "DEFERRED_LOW_FIDELITY"
        else:
            status = "SEARCHING"

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
    s = min(1.0, 1280.0 / max(h, w))
    img = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1.0 else crop
    reader = m.anpr.get_ocr()
    if reader is None:
        return []
    try:
        results = reader.readtext(img, detail=1, paragraph=False,
                                  allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -")
    except Exception:
        return []
    items = []
    for box, text, conf in results:
        xs, ys = [pt[0] / s for pt in box], [pt[1] / s for pt in box]
        items.append((text, float(conf), (min(xs), min(ys), max(xs), max(ys))))
    items.sort(key=lambda it: it[2][0])

    found = []

    def consider(text, conf, box):
        plate = m.anpr.extract_indian_plate_from_string(text) or m.anpr.post_process(text)
        if plate and vi.plate_format_valid(plate):
            found.append({"plate": vi.clean_plate(plate), "conf": conf, "box": box})

    for text, conf, box in items:
        consider(text, conf, box)
    # HSRP plates are often detected as two boxes on one line, e.g. "TN87" + "C5106"
    for (t1, c1, b1), (t2, c2, b2) in zip(items, items[1:]):
        hh = max(b1[3] - b1[1], b2[3] - b2[1])
        same_line = abs((b1[1] + b1[3]) - (b2[1] + b2[3])) / 2 < 0.6 * hh
        if same_line and 0 <= b2[0] - b1[2] < 1.5 * hh:
            consider(f"{t1} {t2}", (c1 + c2) / 2, (b1[0], min(b1[1], b2[1]), b2[2], max(b1[3], b2[3])))
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
    """Map a raw OCR string onto the plate structure LL DD L{1,3} DDDD, repairing look-alike characters
    slot by slot (0/O, 1/I, 5/S, 8/B...). Returns None when it cannot be made to fit."""
    raw = re.sub(r"[^A-Z0-9]", "", raw.upper())
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
    if plate[:2] not in m.anpr.INDIAN_STATES:
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
    """Frame enhancement for the plate finder: the crop as is, then denoised, then (if small) denoised and
    upscaled 2x. Later variants are only tried when the earlier ones find no plate-like text."""
    yield crop
    den = cv2.fastNlMeansDenoisingColored(crop, None, 7, 7, 7, 21)
    yield den
    if max(crop.shape[:2]) < 900:
        yield cv2.resize(den, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)


def _detect_and_read(m, crop, multi_view=False):
    """Detector-first read of one vehicle crop. Returns (plate, confidence, plate_crop) or (None, 0.0, None).
    The detected box is cropped and restored; with multi_view the plate is read at many scales/contrasts and
    voted, otherwise it is read once more and confidence is boosted only when both reads agree."""
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
    A second, upscaled pass over the glass area finds people the full-image pass missed."""
    people = list(known)
    h, w = crop.shape[:2]
    area = crop if cls_name == "Motorbike" else crop[: max(1, int(h * 0.62))]
    scale = max(1.0, 640.0 / max(area.shape[:2]))
    up = cv2.resize(area, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale > 1 else area
    res = image_model.predict(up, classes=[0], conf=0.25, verbose=False)[0]
    for b in res.boxes:
        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
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
                 known_people=(), deep=True, track_id=None, existing_ghost_id=None, already_logged=False):
    db, al = _ctx["db"], _ctx["al"]
    timestamp = datetime.now().isoformat(timespec="seconds")
    cls_name = VEHICLE_CLASSES.get(cls_id, "Car")
    valid = bool(plate and plate["text"] and plate["confidence"] >= MIN_PLATE_CONF and vi.plate_format_valid(plate["text"]))
    status = "PLATED" if valid else ("UNREADABLE" if plate and plate["text"] else "NO_PLATE")

    attrs = vi.vehicle_attributes(crop if deep else None, cls_name)
    profile = m.prof.extract_vehicle_profile(crop, vehicle_type=cls_name)
    people = _people_in_crop(image_model, crop, cls_name, known_people) if deep else []
    snap_url = _save_snapshot(crop, "webcam")

    card = {
        "id": card_id, "source": source, "track_id": track_id, "bbox": bbox, "camera_id": camera_id,
        "timestamp": timestamp, "vehicle_type": attrs["refined_type"] or cls_name, "yolo_type": cls_name,
        "is_emergency": attrs["is_emergency"], "plate_status": status,
        "crop_b64": vi.to_b64(crop, 360), "image_path": snap_url,
        "visual": {
            "attributes_available": attrs["available"],
            "body_type": attrs["body_type"] or profile.get("body_subtype", ""),
            "color": profile.get("dominant_color", "").replace("_", " ").title(),
            "secondary_color": profile.get("secondary_color", "").replace("_", " ").title(),
            "make_model": attrs["make_model"],
            "damage": attrs["damage"],
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
    if max(h0, w0) > 1280:
        s = 1280.0 / max(h0, w0)
        frame = cv2.resize(frame, (int(w0 * s), int(h0 * s)), interpolation=cv2.INTER_AREA)
    fh, fw = frame.shape[:2]

    res = image_model.predict(frame, conf=0.18, verbose=False)[0]
    vehicles, persons = [], []
    for b in res.boxes:
        cls = int(b.cls)
        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
        if cls in VEHICLE_CLASSES and (x2 - x1) >= 40 and (y2 - y1) >= 40:
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
        card = _finish_card(m, source="image", card_id=f"{filename}#{i + 1}", crop=crop, bbox=[x1, y1, x2, y2],
                            cls_id=cls, plate=plate, camera_id=camera_id, image_model=image_model,
                            known_people=known)
        cards.append(card)
        color = STATUS_COLORS[card["plate_status"]]
        label = f"#{i + 1} {card['vehicle_type']} " + (card["plate"]["text"] if card["plate_status"] == "PLATED" else "NO PLATE")
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
    palette = {"CONFIRMED": (94, 197, 34), "BUFFERING": (11, 158, 245), "SEARCHING": (11, 158, 245),
               "DEFERRED_LOW_FIDELITY": (139, 116, 100), "NO_PLATE": (68, 68, 239)}
    for t in tracks:
        x1, y1, x2, y2 = t["bbox"]
        color = palette.get(t["status"], (11, 158, 245))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"#{t['track_id'] % 100000} {t['vehicle_type']} {t['plate'] or ''}".strip()
        cv2.putText(out, label, (x1 + 3, max(12, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return out


def _light_track(t):
    return {k: t[k] for k in ("track_id", "plate", "confidence", "vehicle_type", "status", "rf_quality_score")}


def _video_worker(job_id, path, camera_id, max_seconds):
    job = _video_jobs[job_id]
    started = time.time()
    cap = None
    try:
        m = _modules()
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        seconds_total = max(1, min(max_seconds, int(math.ceil(total / fps)) if total > 0 else max_seconds))
        job.update(status="running", fps=round(fps, 1), duration_s=round(total / fps, 1) if total > 0 else None,
                   seconds_total=seconds_total, stage="Loading models")

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
            take = min(FRAMES_PER_SECOND, n)
            picks = {start + int(round(k * (n - 1) / max(1, take - 1))) for k in range(take)}
            frames = []
            while frame_i < end:
                ok, f = cap.read()
                if not ok:
                    break
                if frame_i in picks:
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

        # Finalize: one card per tracked vehicle; the most informative tracks get the full CLIP profile.
        job.update(stage="Building vehicle cards", progress=88)
        ordered = sorted(crops, key=lambda tid: (bool(state[tid]["plate"]), state[tid]["frames_seen"]), reverse=True)
        image_model = _get_image_model()
        cards = []
        for rank, tid in enumerate(ordered):
            st = state[tid]
            plate = {"text": st["plate"] or "", "confidence": st["conf"], "color": st["plate_color"],
                     "category": st["category"], "region_found": True, "rf_quality_score": st["rf_best"],
                     "condition": st["details"].get("environmental_condition", "NORMAL")}
            with _lock:
                card = _finish_card(m, source="video", card_id=f"video#{tid}", crop=crops[tid], bbox=st["bbox"],
                                    cls_id=st["cls"], plate=plate, camera_id=camera_id, image_model=image_model,
                                    deep=rank < MAX_PROFILED_TRACKS, track_id=tid,
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


def register_webcam_routes(app, *, db, al, get_yolo_model, prototype_dir, snapshot_dir):
    _ctx.update(db=db, al=al, get_yolo_model=get_yolo_model, prototype_dir=prototype_dir,
                snapshot_dir=snapshot_dir)

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
        with _lock:
            _live_state.clear()
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
