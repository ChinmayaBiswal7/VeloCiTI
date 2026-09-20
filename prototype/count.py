import cv2
import numpy as np
import threading
import os
import signal
from flask import Flask, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import time

# --- Global Variables ---
last_vehicle_count = 0
last_avg_speed = 0
stop_threads = False
last_positions = {}   # track_id -> (x, y, timestamp)

# --- Flask Server Setup ---
app = Flask(__name__)
CORS(app)

@app.route('/data', methods=['GET'])
def get_vehicle_data():
    global last_vehicle_count, last_avg_speed
    return jsonify({
        'vehicle_count': last_vehicle_count,
        'avg_speed_kmph': round(last_avg_speed, 2)
    })

def run_server():
    try:
        port = int(os.environ.get("PORT", 5050))
        app.run(port=port, debug=False, use_reloader=False)
    except Exception as e:

        print(f"❌ Flask error: {e}")

# --- Flask Shutdown Helper ---
def shutdown_flask():
    os.kill(os.getpid(), signal.SIGINT)

# --- Video Processing ---
def run_video_processing():
    global last_vehicle_count, last_avg_speed, stop_threads, last_positions

    # Load YOLO model (choose best for your device: yolov8s.pt for CPU, yolov8m/l/x.pt for GPU)
    model = YOLO("yolov8s.pt")  # ⚡ faster on CPU; use yolov8x.pt if you have GPU
    # model.to("cuda")  # uncomment if you have CUDA GPU

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not open webcam.")
        stop_threads = True
        shutdown_flask()
        return

    # Set resolution (adjust if laggy)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    vehicle_classes = {2: "Car", 3: "Motorbike", 5: "Bus", 7: "Truck"}
    pixels_per_meter = 50  # ⚠️ calibration constant (adjust for your camera setup)

    while not stop_threads:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = time.time()
        results = model.track(frame, persist=True, tracker="botsort.yaml", conf=0.5)

        vehicle_count = 0
        speeds = []

        if results and results[0].boxes is not None:
            annotated_frame = results[0].plot()
            for box in results[0].boxes:
                cls = int(box.cls)
                track_id = int(box.id) if box.id is not None else None

                if track_id is not None and cls in vehicle_classes:
                    vehicle_count += 1

                    # Get vehicle center
                    x, y, w, h = box.xywh[0].tolist()
                    center = (int(x), int(y))

                    if track_id in last_positions:
                        old_x, old_y, old_time = last_positions[track_id]

                        # Pixel distance
                        pixel_dist = np.sqrt((center[0] - old_x) ** 2 + (center[1] - old_y) ** 2)

                        # Time difference
                        dt = timestamp - old_time
                        if dt > 0:
                            # Convert to meters (approx.)
                            dist_m = pixel_dist / pixels_per_meter

                            # Speed in km/h
                            speed_kmph = (dist_m / dt) * 3.6
                            speeds.append(speed_kmph)

                            # Display speed on frame
                            cv2.putText(
                                annotated_frame,
                                f"{speed_kmph:.1f} km/h",
                                (center[0], center[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (255, 255, 0),
                                2
                            )

                    # Update last position
                    last_positions[track_id] = (center[0], center[1], timestamp)
        else:
            annotated_frame = frame

        # Update global variables
        last_vehicle_count = vehicle_count
        last_avg_speed = np.mean(speeds) if speeds else 0

        # Display frame
        cv2.putText(
            annotated_frame,
            f"Vehicles: {last_vehicle_count} | Avg Speed: {last_avg_speed:.1f} km/h",
            (30, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )
        cv2.imshow("Vehicle Tracking + Speed", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_threads = True
            break

    cap.release()
    cv2.destroyAllWindows()
    shutdown_flask()

# --- Main Execution ---
if __name__ == "__main__":
    video_thread = threading.Thread(target=run_video_processing)
    server_thread = threading.Thread(target=run_server)

    video_thread.start()
    server_thread.start()

    video_thread.join()
    server_thread.join()

    print("✅ Program stopped.")
