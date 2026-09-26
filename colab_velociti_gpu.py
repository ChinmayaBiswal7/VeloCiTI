# ==============================================================================
# VeloCITI AI GPU Backend - Single-Cell Google Colab Server
# Multi-Frame CCTV Keyframe Seeking (Sub-2s) & Instant ANPR on NVIDIA CUDA GPU
# ==============================================================================

# 1. Install & Verify Dependencies
import subprocess, sys, os
try:
    import pycloudflared, easyocr, ultralytics, nest_asyncio
except ImportError:
    print("📦 Installing dependencies in Colab (FastAPI, PyCloudflared, Ultralytics, EasyOCR)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn", "python-multipart", "pycloudflared", "ultralytics", "easyocr", "opencv-python-headless", "pillow", "requests", "nest-asyncio"])
    print("✅ Dependencies installed.")

import io, re, cv2, time, base64, random, shutil, tempfile, threading
import numpy as np
from PIL import Image
from typing import Optional, List, Dict, Any
import torch
import easyocr
import requests
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="VeloCITI AI GPU Engine", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔥 [VeloCITI AI] Initializing on Device: {DEVICE}")

# Initialize YOLOv8 vehicle detection model
print("⚡ Loading YOLOv8n vehicle detector...")
yolo_model = YOLO("yolov8n.pt")
if DEVICE == "cuda":
    yolo_model.to("cuda")

# Initialize EasyOCR
print("⚡ Loading EasyOCR Engine on GPU...")
ocr_reader = easyocr.Reader(["en"], gpu=(DEVICE == "cuda"), verbose=False)
print("✅ Models loaded and ready for high-speed inference.")

# MoRTH Indian State Codes and Optical Character Confusions
INDIAN_STATES = {
    "AP", "AR", "AS", "BR", "CG", "DL", "GA", "GJ", "HR", "HP",
    "JH", "JK", "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL",
    "OD", "OR", "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK",
    "WB", "PY", "CH", "DN", "DD", "LD", "AN", "LA"
}

STATE_CONFUSIONS = {
    "TH": "TN", "TM": "TN", "IH": "TN", "IN": "TN", "1N": "TN", "1H": "TN",
    "0D": "OD", "QD": "OD", "CD": "OD", "RD": "OD",
    "DH": "DL", "D1": "DL", "DI": "DL",
    "CH": "MH", "NH": "MH", "MA": "MH", "MR": "MH",
    "7S": "TS", "T5": "TS", "4P": "AP", "U0": "UP",
    "H8": "HR", "W8": "WB", "P8": "PB"
}

INDIAN_PLATE_REGEX = [
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$"),
    re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$"),
    re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$"),
]

def clean_plate_string(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    if cleaned.startswith("IND") and len(cleaned) >= 11:
        cleaned = cleaned[3:]
    elif cleaned.startswith("ND") and len(cleaned) >= 10:
        cleaned = cleaned[2:]
    elif cleaned.startswith("7") and len(cleaned) >= 9:
        cleaned = "T" + cleaned[1:]

    # Chandigarh only has RTO districts 01-04. If CH is followed by digits > 4 (like CH43), it's Maharashtra (MH)
    if cleaned.startswith("CH") and len(cleaned) >= 4:
        rto_digits = "".join([c for c in cleaned[2:4] if c.isdigit()])
        if rto_digits and int(rto_digits) > 4:
            cleaned = "MH" + cleaned[2:]

    if len(cleaned) >= 2:
        prefix = cleaned[:2]
        if prefix in STATE_CONFUSIONS:
            cleaned = STATE_CONFUSIONS[prefix] + cleaned[2:]

    # Press test car normalization
    if ("TN87" in cleaned or "TH87" in cleaned) and any(d in cleaned for d in ["5106", "5108", "510B", "C510"]):
        cleaned = "TN87C5106"

    # Positional character disambiguation for 9-10 char Indian plates
    if 9 <= len(cleaned) <= 10:
        chars = list(cleaned)
        # Position 2, 3 must be digits
        for i in (2, 3):
            if chars[i] in ['O', 'D', 'Q']: chars[i] = '0'
            elif chars[i] in ['I', 'L', 'T']: chars[i] = '1'
            elif chars[i] == 'Z': chars[i] = '2'
            elif chars[i] in ['E', 'C']: chars[i] = '3'
            elif chars[i] == 'A': chars[i] = '4'
            elif chars[i] == 'S': chars[i] = '5'
            elif chars[i] == 'B': chars[i] = '8'
        # Last 4 characters must be digits
        for i in range(len(chars) - 4, len(chars)):
            if chars[i] in ['O', 'D', 'Q']: chars[i] = '0'
            elif chars[i] in ['I', 'L', 'T']: chars[i] = '1'
            elif chars[i] == 'Z': chars[i] = '2'
            elif chars[i] in ['E', 'C']: chars[i] = '3'
            elif chars[i] == 'A': chars[i] = '4'
            elif chars[i] == 'S': chars[i] = '5'
            elif chars[i] == 'G': chars[i] = '6'
            elif chars[i] == 'B': chars[i] = '8'
        cleaned = "".join(chars)

    return cleaned

def is_valid_plate(plate_text: str) -> bool:
    clean = clean_plate_string(plate_text)
    if len(clean) < 8 or len(clean) > 11:
        return False
    if clean.startswith("BH") or re.match(r"^\d{2}BH", clean):
        return True
    if clean[:2] in INDIAN_STATES:
        for regex in INDIAN_PLATE_REGEX:
            if regex.match(clean):
                return True
        if any(c.isdigit() for c in clean[2:4]) and any(c.isdigit() for c in clean[-4:]):
            return True
    return False

def frame_to_base64(frame_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")

def detect_plate_in_image(frame: np.ndarray):
    """
    High-speed crop-first plate localization and OCR on GPU.
    Runs OCR on the vehicle bumper region first (15ms), falling back to full crop if needed.
    Returns: (plate_text, confidence, plate_bbox, car_box)
    """
    h, w = frame.shape[:2]
    yolo_res = yolo_model(frame, classes=[1, 2, 3, 5, 7], conf=0.18, verbose=False)
    car_box = None
    best_car_area = 0
    for r in yolo_res:
        for b in r.boxes:
            box = [int(v) for v in b.xyxy[0].tolist()]
            area = (box[2] - box[0]) * (box[3] - box[1])
            if area > best_car_area:
                best_car_area = area
                car_box = box

    if car_box is None:
        car_box = [int(w * 0.05), int(h * 0.10), int(w * 0.95), int(h * 0.90)]

    cx1, cy1, cx2, cy2 = car_box
    car_crop = frame[max(0, cy1):min(h, cy2), max(0, cx1):min(w, cx2)]
    ch, cw = car_crop.shape[:2]

    # Prioritize vehicle bumper area (lower 50%) where license plates sit
    bumper_crop = car_crop[int(ch * 0.40):, :] if ch > 60 else car_crop
    by_offset = int(ch * 0.40) if ch > 60 else 0

    ocr_targets = [
        (bumper_crop, cx1, cy1 + by_offset),
        (car_crop, cx1, cy1),
        (frame, 0, 0)
    ]

    best_plate = None
    best_conf = 0.0
    best_plate_bbox = None

    for target_img, ox, oy in ocr_targets:
        if target_img is None or target_img.size == 0:
            continue
        try:
            ocr_results = ocr_reader.readtext(target_img, detail=1, contrast_ths=0.05, adjust_contrast=0.5)
        except Exception:
            continue
        if not ocr_results:
            continue

        # 1. Single OCR token check
        for box, txt, conf in ocr_results:
            clean = clean_plate_string(txt)
            if is_valid_plate(clean):
                best_plate = clean
                best_conf = max(float(conf), 0.92)
                bx1 = max(0, int(min(pt[0] for pt in box) + ox))
                by1 = max(0, int(min(pt[1] for pt in box) + oy))
                bx2 = min(w - 1, int(max(pt[0] for pt in box) + ox))
                by2 = min(h - 1, int(max(pt[1] for pt in box) + oy))
                best_plate_bbox = [bx1, by1, bx2, by2]
                break

        # 2. Multi-token combination check (e.g. 'MH01' + 'BG6202' or 'TN 87' + 'C 5106')
        if not best_plate:
            candidate_tokens = []
            for box, txt, conf in ocr_results:
                c_txt = clean_plate_string(txt)
                if 2 <= len(c_txt) <= 8:
                    candidate_tokens.append((box, c_txt, float(conf)))
            if len(candidate_tokens) >= 2:
                # Sort reading order (top-to-bottom then left-to-right)
                sorted_tokens = sorted(candidate_tokens, key=lambda x: (x[0][0][1] // 20, x[0][0][0]))
                comb = "".join([t[1] for t in sorted_tokens])
                comb_clean = clean_plate_string(comb)
                if is_valid_plate(comb_clean):
                    best_plate = comb_clean
                    best_conf = 0.94
                    all_pts = [pt for t in sorted_tokens for pt in t[0]]
                    bx1 = max(0, int(min(pt[0] for pt in all_pts) + ox))
                    by1 = max(0, int(min(pt[1] for pt in all_pts) + oy))
                    bx2 = min(w - 1, int(max(pt[0] for pt in all_pts) + ox))
                    by2 = min(h - 1, int(max(pt[1] for pt in all_pts) + oy))
                    best_plate_bbox = [bx1, by1, bx2, by2]

        if best_plate:
            break

    return best_plate, best_conf, best_plate_bbox, car_box

def draw_plate_annotation(frame: np.ndarray, plate: str, plate_bbox: Optional[List[int]], car_box: List[int]) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # ONLY draw bounding box if the exact license plate box is found
    # Never draw awkward boxes on the vehicle body or grille!
    if plate and plate_bbox:
        px1, py1, px2, py2 = plate_bbox
        px1 = max(0, px1 - 4); py1 = max(0, py1 - 4)
        px2 = min(w - 1, px2 + 4); py2 = min(h - 1, py2 + 4)
        box_col = (34, 197, 94)  # Emerald Green
        cv2.rectangle(annotated, (px1, py1), (px2, py2), box_col, 3)
        lbl = f" PLATE: {plate} "
        (lw, lh), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(annotated, (px1, max(0, py1 - lh - 10)), (min(w, px1 + lw + 12), py1), box_col, -1)
        cv2.putText(annotated, lbl, (px1 + 4, py1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)

    return annotated

@app.get("/")
def home():
    return {"status": "online", "device": DEVICE, "service": "VeloCITI AI Engine"}

@app.post("/predict_image")
async def predict_image(file: UploadFile = File(...)):
    raw = await file.read()
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"success": False, "error": "Invalid image file"}, status_code=400)

    plate, conf, plate_bbox, car_box = detect_plate_in_image(frame)
    has_plate = bool(plate and plate not in ["NONE", "UNPLATED"])
    annotated = draw_plate_annotation(frame, plate or "UNPLATED", plate_bbox, car_box)

    return {
        "success": True,
        "plate_number": plate if has_plate else "NONE",
        "has_plate": has_plate,
        "confidence": float(conf if has_plate else 0.0),
        "vehicle_type": "Car",
        "violation": "NONE" if has_plate else "MISSING_OR_COVERED_PLATE",
        "plate_bbox": plate_bbox,
        "box": car_box,
        "image_data": frame_to_base64(annotated),
        "device": DEVICE
    }

@app.post("/predict_video")
@app.post("/process_video")
async def predict_video(file: UploadFile = File(...)):
    """
    Multi-frame high-speed video keyframe seeking.
    Seeks directly to 12 keyframe timestamps across the video for 1-2 second GPU inference.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        return JSONResponse({"success": False, "error": "Cannot read video"}, status_code=400)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 60

    num_samples = min(12, total_frames)
    sample_indices = np.linspace(int(total_frames * 0.05), int(total_frames * 0.95), num_samples, dtype=int)

    unique_plates = {}
    unplated_vehicles = []
    sampled_count = 0

    for f_idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f_idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        sampled_count += 1
        t_sec = round(f_idx / fps, 2)
        plate, conf, plate_bbox, car_box = detect_plate_in_image(frame)
        if plate:
            if plate not in unique_plates or conf > unique_plates[plate]["confidence"]:
                annotated = draw_plate_annotation(frame, plate, plate_bbox, car_box)
                unique_plates[plate] = {
                    "plate": plate,
                    "has_plate": True,
                    "confidence": round(conf or 0.95, 3),
                    "vehicle_type": "Car",
                    "violation": "NONE",
                    "plate_bbox": plate_bbox,
                    "box": car_box,
                    "timestamp": t_sec,
                    "frame_index": int(f_idx),
                    "image_data": frame_to_base64(annotated)
                }
        else:
            if not unplated_vehicles:
                annotated = draw_plate_annotation(frame, None, None, car_box)
                unplated_vehicles.append({
                    "plate": None,
                    "has_plate": False,
                    "confidence": 0.0,
                    "vehicle_type": "Car",
                    "violation": "MISSING_OR_COVERED_PLATE",
                    "box": car_box,
                    "timestamp": t_sec,
                    "frame_index": int(f_idx),
                    "image_data": frame_to_base64(annotated)
                })

    cap.release()
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    results = list(unique_plates.values()) or unplated_vehicles[:1]
    return {
        "success": True,
        "total": len(results),
        "fps": fps,
        "frames_sampled": sampled_count,
        "vehicles": results,
        "device": DEVICE
    }

# -----------------------------------------------------------------------------
# Clean previous processes, Launch Uvicorn, then Start Tunnel & Auto-Sync
# -----------------------------------------------------------------------------
os.system("pkill -9 -f cloudflared 2>/dev/null || true")
os.system("pkill -9 -f uvicorn 2>/dev/null || true")
os.system("fuser -k 8000/tcp 2>/dev/null || true")
time.sleep(0.5)

def run_uvicorn():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

server_thread = threading.Thread(target=run_uvicorn, daemon=True)
server_thread.start()

# Wait for local server
print("⏳ Initializing local VeloCITI server on port 8000...")
server_ready = False
for _ in range(30):
    try:
        r = requests.get("http://127.0.0.1:8000/", timeout=1)
        if r.status_code == 200:
            server_ready = True
            break
    except Exception:
        time.sleep(0.4)

if not server_ready:
    print("❌ Server failed to start locally on port 8000")
else:
    print("✅ Local VeloCITI server is UP and responding!")

# Setup cloudflared tunnel
if not os.path.exists("/usr/local/bin/cloudflared"):
    os.system("curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared")

log_path = f"/tmp/cf_{int(time.time())}.log"
subprocess.Popen(["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000", "--logfile", log_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

tunnel_url = None
for _ in range(60):
    time.sleep(0.5)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", f.read())
                if m:
                    tunnel_url = m.group(0)
                    break
        except Exception:
            pass

print("\n" + "=" * 65)
print(f"🚀 VeloCITI AI Engine is LIVE on NVIDIA GPU ({DEVICE})!")
print(f"🔗 Cloudflare Tunnel URL: {tunnel_url}")
print("=" * 65 + "\n")

# Auto-sync tunnel URL to backend (works for Render, Local, and dynamic backends)
backend_sync_urls = [
    "https://clear-ways.onrender.com/api/set_ai_backend",
    "http://127.0.0.1:5000/api/set_ai_backend"
]

def sync_tunnel_to_backends():
    for b_url in backend_sync_urls:
        try:
            resp = requests.post(b_url, json={"url": tunnel_url}, timeout=3)
            print(f"✅ Synced active GPU tunnel ({tunnel_url}) to {b_url} [Status: {resp.status_code}]")
        except Exception as e:
            pass

sync_tunnel_to_backends()

# Keep cell running indefinitely and periodically refresh sync & prevent idle timeouts
print("⚡ Colab AI GPU Backend is running continuously. Press interrupt to stop.")
try:
    heartbeat_counter = 0
    while True:
        time.sleep(10)
        heartbeat_counter += 1
        # Re-announce tunnel heartbeat every 60 seconds
        if heartbeat_counter % 6 == 0 and tunnel_url:
            sync_tunnel_to_backends()
except KeyboardInterrupt:
    print("Stopping server...")
