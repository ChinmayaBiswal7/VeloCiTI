"""
firebase_sync.py - Real-Time Firebase Cloud Synchronization Engine
Streams ANPR detections, unplated suspect targets, traffic police blacklist alerts,
and junction congestion telemetry to Google Firebase (Firestore & Realtime DB).
Enables external client apps (Traffic Police Mobile App, Ambulance Priority App, PCR Vans)
to consume live smart-city traffic intelligence via real-time listeners.
"""

import os
import sys
import json
import time
import queue
import threading
from datetime import datetime

# Global status tracking
_firebase_initialized = False
_firebase_mode = "NONE" # "FIRESTORE", "RTDB", or "NONE"
_firestore_db = None
_rtdb_root = None
_sync_queue = queue.Queue(maxsize=1000)
_worker_thread = None
_stats = {
    "synced_detections": 0,
    "synced_unplated": 0,
    "synced_alerts": 0,
    "synced_junctions": 0,
    "last_sync_ts": None,
    "status": "DISCONNECTED",
    "error_message": None
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "firebase_config.json")
DEFAULT_KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")


def load_config():
    """Loads Firebase configuration or defaults."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "enabled": True,
        "service_account_file": "serviceAccountKey.json",
        "database_url": "",
        "use_firestore": True,
        "use_rtdb": True
    }


def to_firestore_value(val):
    if isinstance(val, bool):
        return {"booleanValue": val}
    elif isinstance(val, int):
        return {"integerValue": str(val)}
    elif isinstance(val, float):
        return {"doubleValue": float(val)}
    elif isinstance(val, dict):
        return {"mapValue": {"fields": {k: to_firestore_value(v) for k, v in val.items()}}}
    elif isinstance(val, list):
        return {"arrayValue": {"values": [to_firestore_value(v) for v in val]}}
    else:
        return {"stringValue": str(val)}


def from_firestore_value(field_val):
    """Recursively unpacks a Firestore REST field value into native Python."""
    if not isinstance(field_val, dict):
        return field_val
    if "stringValue" in field_val:
        return field_val["stringValue"]
    if "integerValue" in field_val:
        return int(field_val["integerValue"])
    if "doubleValue" in field_val:
        return float(field_val["doubleValue"])
    if "booleanValue" in field_val:
        return bool(field_val["booleanValue"])
    if "arrayValue" in field_val:
        return [from_firestore_value(x) for x in field_val["arrayValue"].get("values", [])]
    if "mapValue" in field_val:
        return {k: from_firestore_value(v) for k, v in field_val["mapValue"].get("fields", {}).items()}
    if "nullValue" in field_val:
        return None
    return str(field_val)


def from_firestore_doc(doc):
    """Converts a full Firestore document payload into a Python dict."""
    if not doc or not isinstance(doc, dict):
        return {}
    fields = doc.get("fields", {})
    return {k: from_firestore_value(v) for k, v in fields.items()}


CAMERAS_INFO = {
    "CAM_01": {"name": "Bhubaneswar Railway Station", "road": "Station Road", "lat": 20.2640, "lon": 85.8354, "area": "Central"},
    "CAM_02": {"name": "Master Canteen Square", "road": "MG Road", "lat": 20.2683, "lon": 85.8316, "area": "Central"},
    "CAM_03": {"name": "Vani Vihar", "road": "Vani Vihar Road", "lat": 20.2961, "lon": 85.8245, "area": "North"},
    "CAM_04": {"name": "Patia Square", "road": "NH-16", "lat": 20.3516, "lon": 85.8189, "area": "North"},
    "CAM_05": {"name": "Infocity Entrance", "road": "Infocity Road", "lat": 20.3587, "lon": 85.8149, "area": "North"},
    "CAM_06": {"name": "Rasulgarh Overbridge", "road": "Ring Road", "lat": 20.2795, "lon": 85.8702, "area": "East"},
    "CAM_07": {"name": "Jaydev Vihar Square", "road": "Jaydev Vihar Road", "lat": 20.3051, "lon": 85.8148, "area": "West"},
    "CAM_08": {"name": "Khandagiri Square", "road": "NH-57", "lat": 20.2524, "lon": 85.7796, "area": "West"},
}


def _rest_write_firestore(collection, doc_id, payload):
    """Fallback writer using Google Cloud Firestore REST API with Web API Key."""
    import requests
    config = load_config()
    proj = config.get("projectId", "your-firebase-project")
    key = config.get("apiKey", "")
    if not proj or not key:
        return False
    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{collection}/{doc_id}?key={key}"
    fields = {k: to_firestore_value(v) for k, v in payload.items()}
    try:
        r = requests.patch(url, json={"fields": fields}, timeout=4)
        return r.status_code in (200, 201)
    except Exception:
        return False


def _rest_get_firestore(collection, doc_id):
    """Fetches a document from Firestore REST API."""
    import requests
    config = load_config()
    proj = config.get("projectId", "your-firebase-project")
    key = config.get("apiKey", "")
    if not proj or not key:
        return None
    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{collection}/{doc_id}?key={key}"
    try:
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            return from_firestore_doc(r.json())
    except Exception:
        pass
    return None


def _rest_list_firestore(collection, page_size=40):
    """Lists documents in a collection via Firestore REST API."""
    import requests
    config = load_config()
    proj = config.get("projectId", "your-firebase-project")
    key = config.get("apiKey", "")
    if not proj or not key:
        return []
    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{collection}?pageSize={page_size}&key={key}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            docs = data.get("documents", [])
            return [from_firestore_doc(d) for d in docs]
    except Exception:
        pass
    return []



def init_firebase():
    """Initializes Firebase Admin SDK or falls back to Web REST API."""
    global _firebase_initialized, _firebase_mode, _firestore_db, _rtdb_root, _stats
    
    config = load_config()
    if not config.get("enabled", True):
        _stats["status"] = "DISABLED_IN_CONFIG"
        return False

    key_filename = config.get("service_account_file", "serviceAccountKey.json")
    key_path = os.path.join(os.path.dirname(__file__), key_filename)

    # 1. First priority: Full Firebase Admin SDK if serviceAccountKey.json is provided
    if os.path.exists(key_path):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore, db as rtdb

            if not firebase_admin._apps:
                cred = credentials.Certificate(key_path)
                opts = {}
                if config.get("database_url"):
                    opts["databaseURL"] = config["database_url"]
                firebase_admin.initialize_app(cred, opts)

            try:
                _firestore_db = firestore.client()
                _firebase_mode = "FIRESTORE_ADMIN"
            except Exception as fe:
                print(f"[Firebase] Firestore init note: {fe}")

            if config.get("database_url"):
                try:
                    _rtdb_root = rtdb.reference()
                    _firebase_mode = "DUAL_ADMIN" if _firestore_db else "RTDB_ADMIN"
                except Exception as re:
                    print(f"[Firebase] RTDB init note: {re}")

            _firebase_initialized = True
            _stats["status"] = "ONLINE_CONNECTED"
            _stats["error_message"] = None
            print(f"[Firebase] Connected using Admin SDK! (Mode: {_firebase_mode})")
            return True

        except Exception as e:
            print(f"[Firebase] Admin SDK init error: {e}")

    # 2. Seamless Fallback: REST API using Web apiKey and projectId (e.g. your-firebase-project)
    if config.get("projectId") and config.get("apiKey"):
        _firebase_initialized = True
        _firebase_mode = "FIRESTORE_REST"
        _stats["status"] = f"ONLINE_REST ({config.get('projectId')})"
        _stats["error_message"] = None
        print(f"[Firebase] Configured for Project '{config.get('projectId')}' via REST API (Mode: {_firebase_mode})")
        return True

    _stats["status"] = "AWAITING_CREDENTIALS"
    _stats["error_message"] = f"Neither '{key_filename}' nor Web apiKey configured."
    return False


def _firebase_worker():
    """Background daemon thread to send telemetry without blocking main ANPR pipeline."""
    global _stats
    while True:
        try:
            item = _sync_queue.get()
            if item is None:
                break
            
            action_type = item.get("type")
            data = item.get("data")

            if not _firebase_initialized:
                # Try auto-reconnect if user dropped serviceAccountKey.json
                if not init_firebase():
                    _sync_queue.task_done()
                    continue

            ts_str = datetime.now().isoformat(timespec="seconds")
            _stats["last_sync_ts"] = ts_str

            if action_type == "DETECTION":
                _sync_detection_internal(data)
                _stats["synced_detections"] += 1

            elif action_type == "UNPLATED":
                _sync_unplated_internal(data)
                _stats["synced_unplated"] += 1

            elif action_type == "ALERT":
                _sync_alert_internal(data)
                _stats["synced_alerts"] += 1

            elif action_type == "JUNCTION":
                _sync_junction_internal(data)
                _stats["synced_junctions"] += 1

            _sync_queue.task_done()
        except Exception as err:
            _stats["error_message"] = str(err)
            time.sleep(0.5)


# In-memory fast cache of vehicle journeys to prevent redundant network round-trips
_vehicle_cache = {}

def _sync_detection_internal(det):
    """
    Pushes detection record to Firebase:
    1. Main Central Collection ('live_detections'): Real-time ingestion stream of all cameras.
    2. Separate Number Plate Section ('vehicle_plates'): Groups and sorts sightings chronologically per vehicle.
    """
    raw_plate = det.get("plate", "UNKNOWN").strip().upper()
    clean_plate = raw_plate.replace(" ", "").replace("/", "_")
    cam_id = det.get("camera_id", "CAM_01")
    cam_meta = CAMERAS_INFO.get(cam_id, {})
    cam_name = cam_meta.get("name", cam_id)
    road = cam_meta.get("road", "Main Arterial")
    lat = float(det.get("lat") or cam_meta.get("lat", 20.2961))
    lon = float(det.get("lon") or cam_meta.get("lon", 85.8245))
    timestamp = det.get("timestamp", datetime.now().isoformat())
    speed_kmph = float(det.get("speed_kmph", 40.0))
    conf = float(det.get("confidence", 0.90))
    vtype = det.get("vehicle_type", "Car")
    img_path = det.get("image_path", "")
    p_color = det.get("plate_color", "WHITE")
    cat = det.get("category", "Private Vehicle")
    viol = det.get("violation", "NONE")
    now_iso = datetime.now().isoformat()

    doc_id = f"{clean_plate}_{int(time.time() * 1000)}"

    # ── 1. Push to Central Sightings Collection ('live_detections') ─────
    raw_payload = {
        "plate": raw_plate,
        "clean_plate": clean_plate,
        "confidence": conf,
        "vehicle_type": vtype,
        "camera_id": cam_id,
        "camera_name": cam_name,
        "road": road,
        "lat": lat,
        "lon": lon,
        "timestamp": timestamp,
        "speed_kmph": speed_kmph,
        "image_path": img_path,
        "plate_color": p_color,
        "category": cat,
        "violation": viol,
        "last_updated": now_iso
    }

    if _firestore_db:
        _firestore_db.collection("live_detections").document(doc_id).set(raw_payload)
    elif _firebase_mode == "FIRESTORE_REST":
        _rest_write_firestore("live_detections", doc_id, raw_payload)

    if _rtdb_root:
        _rtdb_root.child("live_detections").child(doc_id).set(raw_payload)

    # ── 2. Push to Dedicated Per-Plate Section ('vehicle_plates') ─────────
    # Maintain existing sightings array and sort chronologically
    sighting_entry = {
        "camera_id": cam_id,
        "camera_name": cam_name,
        "road": road,
        "lat": lat,
        "lon": lon,
        "timestamp": timestamp,
        "speed_kmph": speed_kmph,
        "confidence": conf,
        "image_path": img_path,
        "violation": viol
    }

    existing_plate_doc = _vehicle_cache.get(clean_plate)
    if existing_plate_doc is None:
        if _firestore_db:
            try:
                snap = _firestore_db.collection("vehicle_plates").document(clean_plate).get()
                if snap.exists:
                    existing_plate_doc = snap.to_dict()
            except Exception:
                pass
        elif _firebase_mode == "FIRESTORE_REST":
            existing_plate_doc = _rest_get_firestore("vehicle_plates", clean_plate)

    sightings_list = []
    if existing_plate_doc and "sightings" in existing_plate_doc:
        sightings_list = list(existing_plate_doc["sightings"])

    # Append and sort by timestamp
    sightings_list.append(sighting_entry)
    sightings_list.sort(key=lambda x: str(x.get("timestamp", "")))
    if len(sightings_list) > 30:
        sightings_list = sightings_list[-30:] # Keep last 30 sightings

    is_blacklisted = "STOLEN" in viol or "WANTED" in viol or clean_plate in ("OD05XX9999", "MH12DE1234", "KA01AB1111")
    plate_payload = {
        "plate": raw_plate,
        "clean_plate": clean_plate,
        "vehicle_type": vtype,
        "category": cat,
        "plate_color": p_color,
        "latest_camera": cam_id,
        "latest_camera_name": cam_name,
        "latest_timestamp": timestamp,
        "latest_speed_kmph": speed_kmph,
        "latest_image_path": img_path,
        "total_sightings": len(sightings_list),
        "is_blacklisted": is_blacklisted,
        "status": "HOTLIST_WANTED" if is_blacklisted else "ACTIVE_IN_TRANSIT",
        "last_updated": now_iso,
        "sightings": sightings_list
    }

    _vehicle_cache[clean_plate] = plate_payload

    if _firestore_db:
        _firestore_db.collection("vehicle_plates").document(clean_plate).set(plate_payload)
    elif _firebase_mode == "FIRESTORE_REST":
        _rest_write_firestore("vehicle_plates", clean_plate, plate_payload)

    if _rtdb_root:
        _rtdb_root.child("vehicle_plates").child(clean_plate).set(plate_payload)



def _sync_unplated_internal(ghost):
    """Pushes unplated vehicle dossier to Firebase (for Traffic Police & PCR apps)."""
    target_id = ghost.get("ghost_id", "UNPLATED_TARGET")
    clean_id = target_id.replace("/", "_").replace(" ", "_")

    payload = {
        "target_id": target_id,
        "vehicle_type": ghost.get("vehicle_type", "Car"),
        "body_subtype": ghost.get("body_subtype", "SUV / Crossover"),
        "dominant_color": ghost.get("dominant_color", "White"),
        "secondary_color": ghost.get("secondary_color", ""),
        "color_hex": ghost.get("color_hex", "#F8FAFC"),
        "estimated_make": ghost.get("estimated_make", "Unknown"),
        "estimated_model": ghost.get("estimated_model", "Unknown"),
        "make_confidence": float(ghost.get("make_confidence", 0.90)),
        "distinguishing_features": ghost.get("distinguishing_features", ""),
        "first_seen_ts": ghost.get("first_seen_ts", ""),
        "last_seen_ts": ghost.get("last_seen_ts", datetime.now().isoformat()),
        "first_camera": ghost.get("first_camera", ""),
        "last_camera": ghost.get("last_camera", ""),
        "total_sightings": int(ghost.get("total_sightings", 1)),
        "best_image_path": ghost.get("best_image_path", ""),
        "status": "ACTIVE_INTERCEPT_ALERT",
        "last_updated": datetime.now().isoformat()
    }

    if _firestore_db:
        _firestore_db.collection("unplated_alerts").document(clean_id).set(payload)
    elif _firebase_mode == "FIRESTORE_REST":
        _rest_write_firestore("unplated_alerts", clean_id, payload)

    if _rtdb_root:
        _rtdb_root.child("unplated_alerts").child(clean_id).set(payload)


def _sync_alert_internal(alert):
    """Pushes high-priority alerts (Stolen / Blacklisted / Red Light Jump)."""
    alert_id = f"ALERT_{int(time.time() * 1000)}"
    payload = {
        "plate": alert.get("plate"),
        "alert_type": alert.get("alert_type", "BLACKLIST_HIT"),
        "camera_id": alert.get("camera_id", ""),
        "timestamp": alert.get("timestamp", datetime.now().isoformat()),
        "message": alert.get("message", "High Priority Vehicle Alert"),
        "status": "OPEN",
        "acknowledged": False
    }

    if _firestore_db:
        _firestore_db.collection("blacklist_alerts").document(alert_id).set(payload)
    elif _firebase_mode == "FIRESTORE_REST":
        _rest_write_firestore("blacklist_alerts", alert_id, payload)

    if _rtdb_root:
        _rtdb_root.child("blacklist_alerts").child(alert_id).set(payload)


def _sync_junction_internal(junc):
    """Pushes junction congestion telemetry (for Ambulance Green Corridor)."""
    cam_id = junc.get("camera_id", "CAM_01")
    payload = {
        "camera_id": cam_id,
        "name": junc.get("name", "City Junction"),
        "road": junc.get("road", ""),
        "latitude": float(junc.get("latitude", 20.2961)),
        "longitude": float(junc.get("longitude", 85.8245)),
        "congestion_level": junc.get("congestion_level", "NORMAL"),
        "vehicles_per_min": int(junc.get("vehicles_per_min", 24)),
        "green_corridor_active": bool(junc.get("green_corridor_active", False)),
        "last_updated": datetime.now().isoformat()
    }

    if _firestore_db:
        _firestore_db.collection("traffic_junctions").document(cam_id).set(payload)
    elif _firebase_mode == "FIRESTORE_REST":
        _rest_write_firestore("traffic_junctions", cam_id, payload)

    if _rtdb_root:
        _rtdb_root.child("traffic_junctions").child(cam_id).set(payload)


# -------------------------------------------------------------------------
# Public API Methods (Non-blocking: pushes onto background queue)
# -------------------------------------------------------------------------

def push_detection(plate, camera_id, timestamp, confidence=0.9, speed_kmph=40.0,
                   vehicle_type="Car", image_path="", plate_color="WHITE",
                   category="Private Vehicle", violation="NONE"):
    """Queue a vehicle detection for Firebase sync."""
    data = {
        "plate": plate,
        "camera_id": camera_id,
        "timestamp": timestamp,
        "confidence": confidence,
        "speed_kmph": speed_kmph,
        "vehicle_type": vehicle_type,
        "image_path": image_path,
        "plate_color": plate_color,
        "category": category,
        "violation": violation
    }
    try:
        _sync_queue.put_nowait({"type": "DETECTION", "data": data})
    except queue.Full:
        pass


def push_unplated_dossier(ghost_profile):
    """Queue an unplated vehicle profile for Firebase sync."""
    if not ghost_profile:
        return
    try:
        _sync_queue.put_nowait({"type": "UNPLATED", "data": ghost_profile})
    except queue.Full:
        pass


def push_alert(plate, alert_type, camera_id, timestamp, message=""):
    """Queue a blacklist/stolen vehicle alert for Firebase sync."""
    data = {
        "plate": plate,
        "alert_type": alert_type,
        "camera_id": camera_id,
        "timestamp": timestamp,
        "message": message
    }
    try:
        _sync_queue.put_nowait({"type": "ALERT", "data": data})
    except queue.Full:
        pass


def push_junction_status(camera_id, name, road, lat, lon, congestion_level="NORMAL",
                         vehicles_per_min=20, green_corridor_active=False):
    """Queue junction telemetry for Firebase sync (Ambulance Route Clearance)."""
    data = {
        "camera_id": camera_id,
        "name": name,
        "road": road,
        "latitude": lat,
        "longitude": lon,
        "congestion_level": congestion_level,
        "vehicles_per_min": vehicles_per_min,
        "green_corridor_active": green_corridor_active
    }
    try:
        _sync_queue.put_nowait({"type": "JUNCTION", "data": data})
    except queue.Full:
        pass


def fetch_vehicle_plate(plate):
    """Retrieves full vehicle journey timeline from Firebase Firestore."""
    clean = plate.strip().upper().replace(" ", "").replace("/", "_")
    if clean in _vehicle_cache:
        return _vehicle_cache[clean]
    if _firestore_db:
        try:
            snap = _firestore_db.collection("vehicle_plates").document(clean).get()
            if snap.exists:
                d = snap.to_dict()
                _vehicle_cache[clean] = d
                return d
        except Exception:
            pass
    elif _firebase_mode == "FIRESTORE_REST":
        d = _rest_get_firestore("vehicle_plates", clean)
        if d:
            _vehicle_cache[clean] = d
            return d
    return None


def list_vehicle_plates(limit=30):
    """Lists recent vehicles and their sighting counts from Firebase."""
    if _firestore_db:
        try:
            snaps = _firestore_db.collection("vehicle_plates").limit(limit).stream()
            return [s.to_dict() for s in snaps]
        except Exception:
            pass
    elif _firebase_mode == "FIRESTORE_REST":
        docs = _rest_list_firestore("vehicle_plates", page_size=limit)
        if docs:
            return docs
    return list(_vehicle_cache.values())[:limit]


def seed_demo_journeys():
    """
    Seeds rich multi-camera journeys across Bhubaneswar for demo vehicles in Firebase.
    Demonstrates central cloud database connecting all disparate junction cameras.
    """
    demo_journeys = [
        {
            "plate": "OD05XX9999",
            "type": "Car",
            "category": "Private Vehicle",
            "route": [
                ("CAM_01", "18:20:10", 42.0, 0.96),
                ("CAM_02", "18:28:45", 38.5, 0.94),
                ("CAM_07", "18:41:20", 48.0, 0.97),
                ("CAM_03", "18:52:10", 44.0, 0.95),
                ("CAM_04", "19:08:30", 52.0, 0.98),
                ("CAM_05", "19:18:00", 35.0, 0.99),
            ],
            "violation": "STOLEN_VEHICLE_ALERT",
            "is_blacklisted": True
        },
        {
            "plate": "MH12DE1234",
            "type": "Truck",
            "category": "Commercial Goods",
            "route": [
                ("CAM_08", "17:40:00", 32.0, 0.92),
                ("CAM_07", "17:58:30", 36.0, 0.95),
                ("CAM_03", "18:15:10", 30.0, 0.91),
                ("CAM_06", "18:34:00", 41.0, 0.93),
            ],
            "violation": "WANTED_ROBBERY_CASE",
            "is_blacklisted": True
        },
        {
            "plate": "KA01AB1111",
            "type": "Motorbike",
            "category": "Two Wheeler",
            "route": [
                ("CAM_05", "18:45:00", 55.0, 0.94),
                ("CAM_04", "18:53:20", 49.0, 0.96),
                ("CAM_03", "19:02:10", 45.0, 0.93),
                ("CAM_02", "19:14:40", 40.0, 0.95),
                ("CAM_01", "19:22:00", 38.0, 0.97),
            ],
            "violation": "UNPAID_CHALLANS_EXCEEDED",
            "is_blacklisted": True
        },
        {
            "plate": "OD02BA4455",
            "type": "Car",
            "category": "Private Vehicle",
            "route": [
                ("CAM_01", "18:50:00", 46.0, 0.98),
                ("CAM_02", "18:59:15", 42.0, 0.97),
                ("CAM_07", "19:10:00", 50.0, 0.96),
                ("CAM_03", "19:19:30", 47.0, 0.99),
            ],
            "violation": "NONE",
            "is_blacklisted": False
        },
        {
            "plate": "OD02Z1008",
            "type": "Bus",
            "category": "Public Transit",
            "route": [
                ("CAM_08", "18:10:00", 35.0, 0.97),
                ("CAM_07", "18:29:00", 32.0, 0.96),
                ("CAM_02", "18:48:30", 28.0, 0.95),
                ("CAM_01", "19:01:10", 25.0, 0.98),
            ],
            "violation": "NONE",
            "is_blacklisted": False
        }
    ]

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    for v in demo_journeys:
        clean_p = v["plate"].replace(" ", "").replace("/", "_")
        sightings = []
        for cam_id, t_str, spd, cf in v["route"]:
            ts = f"{date_prefix}T{t_str}"
            cam_info = CAMERAS_INFO.get(cam_id, {})
            sightings.append({
                "camera_id": cam_id,
                "camera_name": cam_info.get("name", cam_id),
                "road": cam_info.get("road", "Main Corridor"),
                "lat": cam_info.get("lat", 20.2961),
                "lon": cam_info.get("lon", 85.8245),
                "timestamp": ts,
                "speed_kmph": spd,
                "confidence": cf,
                "image_path": f"/api/snapshot/{clean_p}_{cam_id}.jpg",
                "violation": v["violation"]
            })
            # Also queue as raw detection
            push_detection(
                plate=v["plate"],
                camera_id=cam_id,
                timestamp=ts,
                confidence=cf,
                speed_kmph=spd,
                vehicle_type=v["type"],
                image_path=f"/api/snapshot/{clean_p}_{cam_id}.jpg",
                plate_color="YELLOW" if v["category"] in ("Commercial Goods", "Public Transit") else "WHITE",
                category=v["category"],
                violation=v["violation"]
            )

        # Seed junction telemetry for all 8 cameras
        for c_id, c_data in CAMERAS_INFO.items():
            push_junction_status(
                camera_id=c_id,
                name=c_data["name"],
                road=c_data["road"],
                lat=c_data["lat"],
                lon=c_data["lon"],
                congestion_level="MODERATE" if "02" in c_id or "03" in c_id else "LOW",
                vehicles_per_min=32 if "02" in c_id else 18
            )

    print(f"[Firebase] Seeded {len(demo_journeys)} multi-camera demo vehicle journeys into Firebase.")


def get_status():
    """Returns real-time sync telemetry for dashboard status indicators."""
    return {
        "connected": _firebase_initialized,
        "mode": _firebase_mode,
        "stats": dict(_stats),
        "queue_size": _sync_queue.qsize()
    }


def start_worker():
    """Starts the background sync worker thread."""
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        init_firebase()
        _worker_thread = threading.Thread(target=_firebase_worker, daemon=True, name="FirebaseSyncWorker")
        _worker_thread.start()
        print("[Firebase] Background Sync Worker Thread started.")
        # Auto seed demo journeys on startup so Firebase is immediately populated
        threading.Thread(target=seed_demo_journeys, daemon=True).start()


start_worker()

