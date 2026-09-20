"""
conditioner.py - AI Video Conditioning & Edge Stream Preprocessing Layer
Architecture:
- Ingests raw 24-30 FPS CCTV stream in real time.
- Tier 1 (Lightweight Stream Filtering):
  * Scene-Level Weather & Environmental Hysteresis (Rain, Fog, Dust, Night).
  * Frame-Level Optical Telemetry (Sharpness, Glare, Motion Blur, Contrast).
  * Random Forest Quality Decision Gating (100 Trees Ensemble).
  * Multi-Object Tracking & Vehicle Grouping (Tracklet Rolling Buffer).
- Tier 2 (Targeted Event Dispatch):
  * Dynamically filters out 80-90% redundant / low-quality frames.
  * Emits only the Top 3-5 highest-fidelity candidate crops per vehicle to the Deep ANPR Engine.
  * Near real-time rolling window execution (No artificial batch latency).
"""

import cv2
import numpy as np
import time
from collections import defaultdict, deque
import quality
import ml_selector


class VehicleTracklet:
    """Maintains a rolling candidate buffer for a single tracked vehicle."""
    def __init__(self, track_id, max_buffer_size=10):
        self.track_id = track_id
        self.max_buffer_size = max_buffer_size
        self.observations = []
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.is_dispatched = False

    def add_observation(self, raw_crop, bbox, telemetry, rf_eval):
        self.last_seen = time.time()
        q_score = rf_eval.get("rf_quality_score", 0.5)
        
        obs = {
            "crop": raw_crop,
            "bbox": bbox,
            "telemetry": telemetry,
            "rf_eval": rf_eval,
            "quality_score": q_score,
            "timestamp": time.time()
        }
        self.observations.append(obs)
        if len(self.observations) > self.max_buffer_size:
            # Keep highest quality frames in rolling window
            self.observations.sort(key=lambda x: x["quality_score"], reverse=True)
            self.observations = self.observations[:self.max_buffer_size]

    def get_top_k_candidates(self, k=4):
        """Returns the Top-K highest quality frames ranked by the Random Forest model."""
        if not self.observations:
            return []
        sorted_obs = sorted(self.observations, key=lambda x: x["quality_score"], reverse=True)
        return sorted_obs[:k]

    def is_ready_for_anpr(self, min_good_frames=2, min_quality=0.55):
        """Determines if sufficient high-fidelity observations exist to execute ANPR immediately."""
        good_frames = [o for o in self.observations if o["quality_score"] >= min_quality]
        return len(good_frames) >= min_good_frames or len(self.observations) >= 5


class AIVideoConditioner:
    """
    AI Video Conditioning Layer:
    Sits directly between the raw CCTV stream and the ANPR inference engine.
    """
    def __init__(self, target_fps=30):
        self.target_fps = target_fps
        self.active_tracklets = {}
        self.stream_telemetry = {
            "total_frames_ingested": 0,
            "frames_filtered_out": 0,
            "frames_sent_to_anpr": 0,
            "compute_saved_pct": "0%",
            "active_tracks_count": 0,
            "dominant_scene": "NORMAL",
            "fps_realtime": 30.0
        }
        self.last_fps_time = time.time()
        self.fps_frame_counter = 0

    def process_stream_frame(self, frame, yolo_results=None):
        """
        Lightweight conditioning pass executed on every incoming video frame (<3ms):
        1. Evaluates scene environmental telemetry & RF quality gating.
        2. Assigns vehicle detections to persistent tracklets.
        3. Filters out unpromising/corrupt frames.
        4. Emits vehicles that have collected sufficient high-quality observations.
        """
        t_start = time.perf_counter()
        self.stream_telemetry["total_frames_ingested"] += 1
        self.fps_frame_counter += 1

        # Real-time FPS calculation
        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.stream_telemetry["fps_realtime"] = round(self.fps_frame_counter / (now - self.last_fps_time), 1)
            self.fps_frame_counter = 0
            self.last_fps_time = now

        if frame is None or frame.size == 0:
            return [], self.stream_telemetry

        # 1. Scene-Level Environmental Assessment with Hysteresis
        scene_telemetry = quality.assess_image_quality(frame, is_scene_frame=True)
        self.stream_telemetry["dominant_scene"] = scene_telemetry.get("scene_condition", "NORMAL")

        # 2. Extract tracked vehicle bounding boxes from YOLO results
        dispatched_vehicles = []
        current_seen_tracks = set()

        if yolo_results and yolo_results[0].boxes is not None and len(yolo_results[0].boxes) > 0:
            boxes = yolo_results[0].boxes
            vehicle_classes = {2: "Car", 3: "Motorbike", 5: "Bus", 7: "Truck", 67: "Vehicle Display"}

            for box in boxes:
                cls = int(box.cls)
                if cls not in vehicle_classes and cls != 0:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                track_id = int(box.id[0]) if box.id is not None else (abs(hash((x1, y1))) % 10000)
                current_seen_tracks.add(track_id)

                # Crop vehicle region
                vx1, vx2 = max(0, x1), min(frame.shape[1], x2)
                vy1, vy2 = max(0, y1), min(frame.shape[0], y2)
                veh_crop = frame[vy1:vy2, vx1:vx2]
                if veh_crop.size == 0:
                    continue

                # 3. Lightweight Frame-Level IQA & Random Forest Gating
                crop_telemetry = quality.assess_image_quality(veh_crop, is_scene_frame=False)
                rf_eval = ml_selector.evaluate_frame_candidate(veh_crop, crop_telemetry)

                # Get or create vehicle tracklet
                if track_id not in self.active_tracklets:
                    self.active_tracklets[track_id] = VehicleTracklet(track_id)

                tracklet = self.active_tracklets[track_id]

                # If frame is acceptable by Random Forest, buffer it
                if rf_eval.get("is_acceptable_for_ocr", True) or rf_eval.get("rf_quality_score", 0) >= 0.40:
                    tracklet.add_observation(veh_crop, (vx1, vy1, vx2, vy2), crop_telemetry, rf_eval)
                    self.stream_telemetry["frames_sent_to_anpr"] += 1
                else:
                    self.stream_telemetry["frames_filtered_out"] += 1

                # Check if tracklet is ready for ANPR dispatch
                if not tracklet.is_dispatched and tracklet.is_ready_for_anpr():
                    top_candidates = tracklet.get_top_k_candidates(k=4)
                    if top_candidates:
                        dispatched_vehicles.append({
                            "track_id": track_id,
                            "vehicle_type": vehicle_classes.get(cls, "Car"),
                            "top_candidates": top_candidates,
                            "best_candidate": top_candidates[0],
                            "scene_telemetry": scene_telemetry
                        })
                        tracklet.is_dispatched = True

        else:
            # No vehicles detected in frame -> filtered out completely
            self.stream_telemetry["frames_filtered_out"] += 1

        # 4. Clean up stale tracklets that left camera FOV (>3 seconds inactive)
        stale_tracks = [t_id for t_id, t in self.active_tracklets.items() if now - t.last_seen > 3.0]
        for t_id in stale_tracks:
            # If not yet dispatched and has any observations, dispatch final candidate
            t = self.active_tracklets[t_id]
            if not t.is_dispatched and len(t.observations) > 0:
                top_candidates = t.get_top_k_candidates(k=3)
                if top_candidates:
                    dispatched_vehicles.append({
                        "track_id": t_id,
                        "vehicle_type": "Car",
                        "top_candidates": top_candidates,
                        "best_candidate": top_candidates[0],
                        "scene_telemetry": scene_telemetry
                    })
            del self.active_tracklets[t_id]

        # Calculate compute saved %
        total = max(1, self.stream_telemetry["total_frames_ingested"])
        saved = self.stream_telemetry["frames_filtered_out"]
        self.stream_telemetry["compute_saved_pct"] = f"{round((saved / total) * 100, 1)}%"
        self.stream_telemetry["active_tracks_count"] = len(self.active_tracklets)

        return dispatched_vehicles, self.stream_telemetry

    def flush_remaining_tracklets(self):
        """Flushes and dispatches all buffered tracklets at stream EOF."""
        dispatched = []
        for t_id, t in self.active_tracklets.items():
            if not t.is_dispatched and len(t.observations) > 0:
                top_candidates = t.get_top_k_candidates(k=4)
                if top_candidates:
                    dispatched.append({
                        "track_id": t_id,
                        "vehicle_type": "Car",
                        "top_candidates": top_candidates,
                        "best_candidate": top_candidates[0],
                        "scene_telemetry": {"scene_condition": self.stream_telemetry.get("dominant_scene", "NORMAL")}
                    })
                    t.is_dispatched = True
        return dispatched



_global_video_conditioner = AIVideoConditioner()

def get_video_conditioner():
    """Global fast accessor for the AI Video Conditioning Layer."""
    return _global_video_conditioner
