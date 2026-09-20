"""
run_camera.py - Dedicated Standalone Live Edge Camera ANPR Node
Runs YOLOv8 vehicle detection + Spatio-Temporal OCR Fusion on Webcam / CCTV stream.
Displays the real-time AI computer vision window on desktop and streams detections
to the Central Vehicle Intelligence Server (http://127.0.0.1:5000).

Usage:
    python run_camera.py
    python run_camera.py --cam 0
    python run_camera.py --video path/to/video.mp4
"""

import cv2
import time
import argparse
import os
import requests
from datetime import datetime
from ultralytics import YOLO
import anpr as anpr_module
import database as db
import alerts as al

SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:5050/api/detection")
CAMERA_ID = "CAM_LIVE"

CAMERA_NAME = "Live CCTV Edge Node (Webcam)"

def main():
    parser = argparse.ArgumentParser(description="Live CCTV Edge ANPR Node")
    parser.add_argument("--cam", type=int, default=0, help="Camera index (default 0)")
    parser.add_argument("--video", type=str, default=None, help="Optional video file path")
    args = parser.parse_args()

    source = args.video if args.video else args.cam
    print("========================================================")
    print("  [+] Starting Live CCTV Edge ANPR Camera Node")
    print(f"  [*] Camera ID: {CAMERA_ID} ({CAMERA_NAME})")
    print(f"  [*] Video Source: {source}")
    print("  [*] Model: YOLOv8s + Spatio-Temporal Sequence Fusion")
    print("  [*] Press 'q' or 'ESC' in the camera window to exit")
    print("========================================================")

    # Register camera in database
    db.upsert_camera(CAMERA_ID, CAMERA_NAME, "Station Road", 20.2640, 85.8354, "Central")

    # Load YOLO model
    print("Loading YOLOv8s model...")
    model = YOLO("yolov8s.pt")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[!] Error: Could not open camera source {source}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    window_name = "LIVE CCTV ANPR NODE - Edge AI Tracking"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 720, 520)

    prev_time = time.time()
    last_detected_plate = ""
    detection_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            if args.video:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break

        cur_time = time.time()
        fps = 1.0 / max(0.001, (cur_time - prev_time))
        prev_time = cur_time

        timestamp = datetime.now().isoformat(timespec="seconds")

        # 1. Run YOLO Tracking
        results = model.track(frame, persist=True, tracker="botsort.yaml", conf=0.45, verbose=False)

        # 2. Extract plates + Multi-Frame Temporal Fusion
        plates = anpr_module.detect_plates_in_frame(frame, results)

        for p in plates:
            plate = p["plate"]
            conf = p["confidence"]
            vtype = p["vehicle_type"]

            # Save detection to DB & trigger alerts
            snap_name = f"{plate}_{CAMERA_ID}_{timestamp.replace(':', '').replace('-', '').replace('T', '_')}.jpg"
            snap_path = os.path.join("data", "snapshots", snap_name)
            os.makedirs("data/snapshots", exist_ok=True)
            cv2.imwrite(snap_path, frame)

            snap_url = f"/api/snapshot/{snap_name}"

            db.insert_detection(
                plate=plate, camera_id=CAMERA_ID, timestamp=timestamp,
                confidence=conf, speed_kmph=0.0,
                vehicle_type=vtype, image_path=snap_url
            )
            al.check_detection(plate, CAMERA_ID, timestamp)

            last_detected_plate = f"{plate} ({conf*100:.0f}%)"
            detection_count += 1
            print(f"  [+] DETECTED: {plate} | Conf: {conf*100:.1f}% | Type: {vtype} -> Synced to Central Server")

        # 3. Draw Pro-Grade CCTV HUD
        annotated = anpr_module.annotate_frame(frame, plates, last_sync_plate=last_detected_plate)

        # Show FPS and Total Plates counter in top right
        fps_text = f"FPS: {fps:.1f} | Plates: {detection_count}"
        cv2.putText(annotated, fps_text, (annotated.shape[1] - 190, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (148, 163, 184), 1)

        cv2.imshow(window_name, annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[*] Live ANPR node stopped.")

if __name__ == "__main__":
    db.init_db()
    main()
