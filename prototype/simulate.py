"""
simulate.py - Multi-camera simulation for hackathon demo
Generates realistic vehicle detections streaming into the central database.
Run this alongside server.py to see a live city-wide traffic picture.

Usage:
    python simulate.py
"""

import time
import random
import string
from datetime import datetime
import database as db
import alerts as al

# -----------------------------------------------------------------------
# Demo cameras: 8 cameras across Bhubaneswar (real coordinates)
# -----------------------------------------------------------------------
CAMERAS = [
    ("CAM_01", "Bhubaneswar Railway Station",  "Station Road",          20.2640, 85.8354, "Central"),
    ("CAM_02", "Master Canteen Square",         "MG Road",               20.2683, 85.8316, "Central"),
    ("CAM_03", "Vani Vihar",                    "Vani Vihar Road",       20.2961, 85.8245, "North"),
    ("CAM_04", "Patia Square",                  "NH-16",                 20.3516, 85.8189, "North"),
    ("CAM_05", "Infocity Entrance",             "Infocity Road",         20.3587, 85.8149, "North"),
    ("CAM_06", "Rasulgarh Overbridge",          "Ring Road",             20.2795, 85.8702, "East"),
    ("CAM_07", "Jaydev Vihar Square",           "Jaydev Vihar Road",     20.3051, 85.8148, "West"),
    ("CAM_08", "Khandagiri Square",             "NH-57",                 20.2524, 85.7796, "West"),
]

# Predefined routes: lists of camera IDs a vehicle passes through
ROUTES = [
    ["CAM_01", "CAM_02", "CAM_03", "CAM_04", "CAM_05"],   # Station → Patia
    ["CAM_08", "CAM_07", "CAM_03", "CAM_02"],              # Khandagiri → Central
    ["CAM_01", "CAM_06", "CAM_04"],                        # Station → Rasulgarh → Patia
    ["CAM_05", "CAM_04", "CAM_03", "CAM_02", "CAM_01"],   # Patia → Station (reverse)
    ["CAM_02", "CAM_07", "CAM_08"],                        # Central → Khandagiri
    ["CAM_03", "CAM_06"],                                  # Short hop
]

VEHICLE_TYPES = ["Car", "Motorbike", "Bus", "Truck"]
DIRECTIONS    = ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]
STATES        = ["OD", "MH", "KA", "DL", "TN", "AP", "WB", "GJ"]


def random_plate():
    state = random.choice(STATES)
    dist  = str(random.randint(1, 39)).zfill(2)
    alpha = "".join(random.choices(string.ascii_uppercase, k=random.choice([2, 3])))
    num   = str(random.randint(1000, 9999))
    return f"{state}{dist}{alpha}{num}"


def seed_cameras():
    for cam_id, name, road, lat, lon, area in CAMERAS:
        db.upsert_camera(cam_id, name, road, lat, lon, area)
    print(f"Seeded {len(CAMERAS)} demo cameras.")


import os
import cv2
import numpy as np

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def generate_plate_snapshot(plate, cam_id, timestamp, vtype, speed, cam_name="Camera Node", conf=0.95):
    """
    Generates a full 640x360 CCTV Camera Scene Snapshot showing:
    - Road & Lane markings
    - Vehicle in perspective on road
    - YOLO AI detection bounding box with confidence
    - Plate bounding box with character recognition
    - CCTV OSD Header (Cam ID, Location, Timestamp, REC dot)
    - Radar Speed Meter
    """
    try:
        h, w = 360, 640
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Asphalt road background with gradient
        for y in range(h):
            shade = int(35 + (y / h) * 30)
            img[y, :] = (shade, shade, shade)

        # Road perspective lanes
        cv2.line(img, (int(w * 0.3), 0), (0, h), (75, 75, 75), 3)
        cv2.line(img, (int(w * 0.7), 0), (w, h), (75, 75, 75), 3)
        # Dashed center line
        for y in range(40, h, 40):
            cv2.line(img, (w // 2, y), (w // 2, y + 22), (210, 210, 210), 3)

        # Draw vehicle chassis in perspective
        vx1, vy1, vx2, vy2 = int(w * 0.28), int(h * 0.30), int(w * 0.72), int(h * 0.82)
        is_ghost = "GHOST" in plate or "NO PLATE" in plate or "UNREADABLE" in plate

        if is_ghost:
            if "SLV" in plate or "SILVER" in plate:
                car_color = (180, 185, 195)
            elif "RED" in plate:
                car_color = (35, 35, 190)
            elif "BLK" in plate or "BLACK" in plate:
                car_color = (25, 25, 30)
            else:
                car_color = (140, 140, 140)
        else:
            car_color = (60, 75, 95) if vtype == "Car" else (45, 80, 50) if vtype == "Truck" else (90, 50, 45)

        cv2.rectangle(img, (vx1, vy1), (vx2, vy2), car_color, -1)
        cv2.rectangle(img, (vx1, vy1), (vx2, vy2), (25, 30, 40), 2)

        # Windshield / glass
        gw1, gw2 = vx1 + 25, vx2 - 25
        cv2.rectangle(img, (gw1, vy1 + 15), (gw2, vy1 + int((vy2 - vy1) * 0.35)), (25, 25, 30), -1)

        # Headlights / Taillights
        cv2.rectangle(img, (vx1 + 10, vy2 - 40), (vx1 + 35, vy2 - 20), (0, 0, 220), -1)
        cv2.rectangle(img, (vx2 - 35, vy2 - 40), (vx2 - 10, vy2 - 20), (0, 0, 220), -1)

        # License Plate / Missing Plate Bumper
        px1, py1, px2, py2 = int(w * 0.40), vy2 - 36, int(w * 0.60), vy2 - 8
        if is_ghost:
            # Covered / missing plate area (greyed out with hatched marks)
            cv2.rectangle(img, (px1, py1), (px2, py2), (50, 50, 60), -1)
            cv2.rectangle(img, (px1, py1), (px2, py2), (0, 0, 255), 2)
            cv2.putText(img, "[ NO PLATE ]", (px1 + 8, py2 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1)
        else:
            is_commercial = vtype in ("Truck", "Bus")
            bg_col = (18, 210, 245) if is_commercial else (240, 240, 240)
            cv2.rectangle(img, (px1, py1), (px2, py2), bg_col, -1)
            cv2.rectangle(img, (px1, py1), (px2, py2), (10, 10, 10), 2)

            # Blue IND strip
            cv2.rectangle(img, (px1 + 2, py1 + 2), (px1 + 14, py2 - 2), (160, 45, 20), -1)
            # Formatted plate string
            disp_p = f"{plate[:2]} {plate[2:4]} {plate[4:]}" if len(plate) >= 8 else plate
            cv2.putText(img, disp_p, (px1 + 18, py2 - 8), cv2.FONT_HERSHEY_DUPLEX, 0.48, (10, 10, 10), 1)

        # YOLO AI Bounding Box (Vehicle)
        box_col = (0, 0, 255) if is_ghost else (0, 255, 0)
        cv2.rectangle(img, (vx1 - 8, vy1 - 8), (vx2 + 8, vy2 + 8), box_col, 2)
        # YOLO Label Badge
        tag = f"⚠️ {vtype} (PLATE HIDDEN)" if is_ghost else f"{vtype} {conf:.2f}"
        cv2.rectangle(img, (vx1 - 8, vy1 - 28), (vx1 + 160 if is_ghost else vx1 + 120, vy1 - 8), box_col, -1)
        text_col = (255, 255, 255) if is_ghost else (0, 0, 0)
        cv2.putText(img, tag, (vx1 - 4, vy1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42 if is_ghost else 0.50, text_col, 1 if is_ghost else 2)

        # Plate Crop Bounding Box (Red for violation, Orange for standard)
        cv2.rectangle(img, (px1 - 3, py1 - 3), (px2 + 3, py2 + 3), (0, 0, 255) if is_ghost else (0, 165, 255), 2)


        # CCTV OSD Header Top Bar
        cv2.rectangle(img, (0, 0), (w, 32), (10, 10, 10), -1)
        osd = f"CCTV [{cam_id}] {cam_name} | {timestamp} | REC"
        cv2.putText(img, osd, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 220, 220), 1)
        cv2.circle(img, (w - 20, 16), 6, (0, 0, 255), -1)  # Red REC indicator

        # Speed radar tag on bottom-left
        cv2.rectangle(img, (10, h - 36), (155, h - 10), (15, 23, 42), -1)
        cv2.rectangle(img, (10, h - 36), (155, h - 10), (56, 189, 248), 1)
        cv2.putText(img, f"SPEED: {speed} km/h", (16, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (56, 189, 248), 1)

        clean_ts = timestamp.replace(":", "").replace("-", "").replace("T", "_")
        filename = f"{plate}_{cam_id}_{clean_ts}.jpg"
        filepath = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(filepath, img)
        return f"/api/snapshot/{filename}"
    except Exception as e:
        return ""


def run_simulation(interval_sec=2, duration_sec=None, verbose=True):
    """
    Continuously generate realistic sequential vehicle detections.
    Each active vehicle moves camera-by-camera along real traffic corridors.
    """
    seed_cameras()
    al.seed_demo_blacklist()

    # Pre-generate 35 vehicles with assigned vehicle types
    vehicles = {}
    for _ in range(35):
        p = random_plate()
        vehicles[p] = {
            "type": random.choice(VEHICLE_TYPES),
            "route": random.choice(ROUTES),
            "step": 0,
        }

    # Add blacklisted demo vehicles with realistic long corridors
    blacklisted = {
        "OD05XX9999": {"type": "Car", "route": ["CAM_01", "CAM_02", "CAM_07", "CAM_03", "CAM_04", "CAM_05"], "step": 0},
        "MH12DE1234": {"type": "Truck", "route": ["CAM_08", "CAM_07", "CAM_03", "CAM_06"], "step": 0},
        "KA01AB1111": {"type": "Motorbike", "route": ["CAM_05", "CAM_04", "CAM_03", "CAM_02", "CAM_01"], "step": 0},
    }
    vehicles.update(blacklisted)

    # Add plate-less suspect Ghost Vehicles for cross-camera Re-ID tracking
    ghosts = {
        "GHOST-SLV-SED-8492": {
            "type": "Car",
            "subtype": "Sedan (Low Stance / Long Profile)",
            "color": "Silver Grey",
            "hex": "#94A3B8",
            "route": ["CAM_01", "CAM_06", "CAM_04", "CAM_05"],
            "step": 0
        },
        "GHOST-RED-SUV-1049": {
            "type": "Car",
            "subtype": "SUV / Compact Crossover",
            "color": "Red",
            "hex": "#DC2626",
            "route": ["CAM_08", "CAM_07", "CAM_03", "CAM_02"],
            "step": 0
        },
        "GHOST-BLK-SED-9210": {
            "type": "Car",
            "subtype": "Sedan (Low Stance / Long Profile)",
            "color": "Black",
            "hex": "#0F172A",
            "route": ["CAM_05", "CAM_04", "CAM_03", "CAM_01"],
            "step": 0
        }
    }
    vehicles.update(ghosts)

    if verbose:
        print(f"Simulation running with realistic sequential journeys & snapshot capture. Press Ctrl+C to stop.")
    start = time.time()
    cycle = 0

    while True:
        # Pick 2-3 vehicles to advance along their route this tick
        active_plates = random.sample(list(vehicles.keys()), k=min(3, len(vehicles)))

        # Regularly advance featured vehicles
        if cycle % 3 == 0 and "OD05XX9999" not in active_plates:
            active_plates.append("OD05XX9999")
        if cycle % 4 == 0 and "GHOST-SLV-SED-8492" not in active_plates:
            active_plates.append("GHOST-SLV-SED-8492")

        for plate in active_plates:
            v_data = vehicles[plate]
            route = v_data["route"]
            step = v_data["step"]

            cam_id = route[step]
            cam_info = next((c for c in CAMERAS if c[0] == cam_id), None)

            ts = datetime.now().isoformat(timespec="seconds")
            speed = round(random.uniform(28, 65), 1)
            conf = round(random.uniform(0.85, 0.99), 3)
            vtype = v_data["type"]
            is_ghost = plate.startswith("GHOST")

            # Compute direction towards next camera if available
            direction = "N" if "04" in cam_id or "05" in cam_id else ("S" if "01" in cam_id else "NE")
            lat = cam_info[3] + random.uniform(-0.0003, 0.0003) if cam_info else None
            lon = cam_info[4] + random.uniform(-0.0003, 0.0003) if cam_info else None

            # Generate real camera evidence snapshot image
            cam_name_str = cam_info[1] if cam_info else "City Camera"
            snap_url = generate_plate_snapshot(plate, cam_id, ts, vtype, speed, cam_name_str, conf)

            if is_ghost:
                g_col = v_data.get("color", "Silver Grey")
                g_hex = v_data.get("hex", "#94A3B8")
                g_sub = v_data.get("subtype", "Sedan")
                v_prof = {
                    "vehicle_type": vtype,
                    "body_subtype": g_sub,
                    "dominant_color": g_col,
                    "secondary_color": "Dark Roof / Tinted Glass",
                    "color_hex": g_hex,
                    "aspect_ratio": 1.62,
                    "visual_embedding": "[]",
                    "profile_summary": f"{g_col} {g_sub}"
                }
                import vehicle_reid
                reid_res = vehicle_reid.match_or_create_ghost(v_prof, cam_id, ts, snap_url, speed)
                disp_plate = f"{reid_res['ghost_id']} (NO PLATE)"

                db.insert_detection(
                    plate=disp_plate, camera_id=cam_id, timestamp=ts,
                    confidence=conf, speed_kmph=speed,
                    lat=lat, lon=lon, direction=direction, vehicle_type=vtype,
                    image_path=snap_url, plate_color="GREY", category="Violation / Missing Plate",
                    violation="MISSING_OR_COVERED_PLATE"
                )
                try:
                    import firebase_sync
                    firebase_sync.push_detection(
                        plate=disp_plate, camera_id=cam_id, timestamp=ts,
                        confidence=conf, speed_kmph=speed,
                        vehicle_type=vtype, image_path=snap_url,
                        plate_color="GREY", category="Violation / Missing Plate",
                        violation="MISSING_OR_COVERED_PLATE"
                    )
                    firebase_sync.push_unplated_dossier(reid_res.get("profile") or v_prof)
                except Exception:
                    pass
            else:
                db.insert_detection(
                    plate=plate, camera_id=cam_id, timestamp=ts,
                    confidence=conf, speed_kmph=speed,
                    lat=lat, lon=lon, direction=direction, vehicle_type=vtype,
                    image_path=snap_url
                )
                try:
                    import firebase_sync
                    firebase_sync.push_detection(
                        plate=plate, camera_id=cam_id, timestamp=ts,
                        confidence=conf, speed_kmph=speed,
                        vehicle_type=vtype, image_path=snap_url,
                        plate_color="WHITE", category="Private Vehicle",
                        violation="NONE"
                    )
                except Exception:
                    pass


            generated_alerts = al.check_detection(plate, cam_id, ts)
            if verbose:
                if generated_alerts:
                    for a in generated_alerts:
                        print(f"  ALERT [{a['type']}]: {a['message']}")
                else:
                    print(f"  Detection: {plate} @ {cam_id} ({cam_info[1] if cam_info else ''}) | {speed} km/h")

            # Advance to next camera along the route
            v_data["step"] += 1
            if v_data["step"] >= len(route):
                # Journey complete! Reverse route or pick new corridor
                v_data["step"] = 0
                v_data["route"] = list(reversed(route)) if random.random() < 0.6 else random.choice(ROUTES)

        cycle += 1
        if duration_sec and (time.time() - start) > duration_sec:
            if verbose:
                print("Simulation complete.")
            break
        time.sleep(interval_sec)


if __name__ == "__main__":
    db.init_db()
    run_simulation(interval_sec=1)
