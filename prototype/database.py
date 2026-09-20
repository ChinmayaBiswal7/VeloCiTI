"""
database.py - Central SQLite database for City Vehicle Intelligence System
Stores every camera detection, camera metadata, blacklist, and alerts.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "traffic.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


DEFAULT_CAMERAS = [
    # NH-16 Primary Arterial
    ("CAM_KHANDG", "Khandagiri Square", "NH-16", 20.2575, 85.7865, "West"),
    ("CAM_FIRE_STN", "Fire Station Square", "NH-16", 20.2710, 85.7950, "West"),
    ("CAM_BARAMN", "Baramunda Bus Terminal", "NH-16", 20.2768, 85.7995, "West"),
    ("CAM_CRPF", "CRPF Square", "NH-16", 20.2872, 85.8115, "Central"),
    ("CAM_NAYAPALLI", "Nayapalli / Behera Sahi", "NH-16", 20.2930, 85.8150, "Central"),
    ("CAM_JAYADEV", "Jayadev Vihar (NH-16)", "NH-16", 20.3005, 85.8228, "North"),
    ("CAM_ACHARYA", "Acharya Vihar (NH-16)", "NH-16", 20.3015, 85.8315, "North"),
    ("CAM_VANI", "Vani Vihar (NH-16)", "NH-16", 20.2985, 85.8415, "North"),
    ("CAM_RASUL", "Rasulgarh Square (NH-16)", "NH-16", 20.2936, 85.8647, "East"),
    ("CAM_PALASUNI", "Palasuni Square (NH-16)", "NH-16", 20.3040, 85.8710, "East"),
    ("CAM_MANCHES", "Mancheswar Industrial", "Industrial Rd", 20.3120, 85.8750, "East"),

    # Nandankanan Road (Northern IT & University Corridor)
    ("CAM_XAVIER", "Xavier Square (XIMB)", "Nandankanan Rd", 20.3125, 85.8198, "North"),
    ("CAM_CS_PUR", "Chandrasekharpur BDA", "Nandankanan Rd", 20.3175, 85.8160, "North"),
    ("CAM_KALINGA", "Kalinga Hospital Square", "Nandankanan Rd", 20.3205, 85.8215, "North"),
    ("CAM_DAMANA", "Damana Square", "Nandankanan Rd", 20.3340, 85.8185, "North"),
    ("CAM_SAILASHREE", "Sailashree Vihar Chowk", "Nandankanan Rd", 20.3440, 85.8150, "North"),
    ("CAM_PATIA", "Patia Chowk", "Nandankanan Rd", 20.3540, 85.8170, "North"),
    ("CAM_KIIT", "KIIT Square", "KIIT Road", 20.3565, 85.8165, "North"),
    ("CAM_INFOCITY", "Infocity Square", "Infocity Rd", 20.3585, 85.8085, "North"),
    ("CAM_CHANDAKA", "Chandaka Square", "Chandaka Rd", 20.3650, 85.7950, "North"),

    # Western Infill
    ("CAM_DELTA", "Delta Square", "Gopabandhu Marg", 20.2740, 85.8105, "West"),
    ("CAM_GOPABANDHU", "Gopabandhu Square", "OUAT Rd", 20.2700, 85.8210, "West"),
    ("CAM_SIRIPUR", "Siripur / OUAT Square", "OUAT Campus", 20.2645, 85.8155, "West"),

    # Power Grid & Bidyut Marg
    ("CAM_POWER", "Power House Square", "Bidyut Marg", 20.2910, 85.8235, "Central"),
    ("CAM_RAJ_BHAWAN", "Raj Bhawan (Governor House)", "Rajpath", 20.2830, 85.8285, "Central"),

    # Central Spine: Sachivalaya Marg & Rajpath
    ("CAM_AG", "AG Square (State Capital)", "Sachivalaya Marg", 20.2745, 85.8322, "Central"),
    ("CAM_CAPITAL", "Capital Hospital Square", "Hospital Rd", 20.2625, 85.8280, "Central"),
    ("CAM_MAST", "Master Canteen (Station)", "Janpath", 20.2678, 85.8436, "Central"),
    ("CAM_RAM", "Ram Mandir Square", "Janpath", 20.2800, 85.8443, "Central"),
    ("CAM_RUPALI", "Rupali Square", "Janpath", 20.2893, 85.8427, "Central"),
    ("CAM_SAHEED", "Saheed Nagar Square", "Janpath", 20.2910, 85.8520, "Central"),

    # Eastern Secondary Arterials
    ("CAM_VSS", "VSS Nagar Square", "VSS Marg", 20.3050, 85.8550, "East"),
    ("CAM_SAINIK", "Sainik School Square", "Sainik School Rd", 20.3160, 85.8360, "North"),
    ("CAM_BOMIKHAL", "Bomikhal Flyover", "Cuttack-Puri Rd", 20.2820, 85.8560, "East"),
    ("CAM_LAXMI", "Laxmisagar Square", "Cuttack Rd", 20.2720, 85.8500, "East"),
    ("CAM_KALPANA", "Kalpana Square", "Cuttack-Puri Rd", 20.2546, 85.8437, "South"),
    ("CAM_RAJMAHAL", "Rajmahal Square", "Bidyut Marg", 20.2638, 85.8396, "Central"),
    ("CAM_SISHU", "Sishu Bhawan Square", "Hospital Rd", 20.2585, 85.8350, "South"),

    # South & Old Town Heritage Network
    ("CAM_RAVI", "Ravi Talkies Square", "Puri Trunk Rd", 20.2470, 85.8415, "South"),
    ("CAM_LINGARAJ", "Lingaraj Temple Square", "Old Town Heritage", 20.2382, 85.8335, "South"),
    ("CAM_AIRPORT", "Airport Square", "Airport Rd", 20.2525, 85.8178, "South"),
    ("CAM_POKHAR", "Pokhariput Square", "Anand Marg", 20.2460, 85.8170, "South"),
    ("CAM_SUNDARPADA", "Sundarpada Square", "Sundarpada Main Rd", 20.2330, 85.8110, "South"),
    ("CAM_ITER", "ITER / Gandamunda Square", "Jagamara Rd", 20.2505, 85.8050, "West"),
    ("CAM_JAGAMARA", "Jagamara Square", "Khandagiri-Jagamara", 20.2530, 85.7970, "West"),
    ("CAM_GHATIKIA", "Ghatikia / Kalinga Studio", "Studio Rd", 20.2490, 85.7830, "West"),

    # Default numbered cameras
    ("CAM_01", "Patia Chowk", "Nandankanan Road", 20.3540, 85.8170, "North"),
    ("CAM_02", "Jayadev Vihar", "NH-16", 20.3005, 85.8228, "North"),
    ("CAM_03", "Vani Vihar", "NH-16", 20.2985, 85.8415, "North"),
    ("CAM_04", "Acharya Vihar", "NH-16", 20.3015, 85.8315, "North"),
    ("CAM_05", "Master Canteen (Station)", "Janpath", 20.2678, 85.8436, "Central"),
    ("CAM_06", "Kalpana Square", "Cuttack-Puri Road", 20.2546, 85.8437, "South"),
    ("CAM_07", "Ravi Talkies Square", "Puri Trunk Road", 20.2470, 85.8415, "South"),
    ("CAM_08", "Khandagiri Square", "NH-16", 20.2575, 85.7865, "West"),
    ("CAM_LIVE", "Live CCTV Edge Node", "Station Road", 20.2640, 85.8354, "Central"),
]


def init_db():
    """Create all tables if they don't exist. Called once at startup."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id    TEXT PRIMARY KEY,
            name  TEXT NOT NULL,
            road  TEXT,
            lat   REAL,
            lon   REAL,
            area  TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            plate        TEXT    NOT NULL,
            camera_id    TEXT    NOT NULL,
            timestamp    TEXT    NOT NULL,
            confidence   REAL    DEFAULT 0.0,
            speed_kmph   REAL    DEFAULT 0.0,
            lat          REAL,
            lon          REAL,
            direction    TEXT,
            vehicle_type TEXT    DEFAULT 'unknown',
            image_path   TEXT    DEFAULT '',
            voting_data  TEXT    DEFAULT ''
        )
    """)
    try:
        c.execute("ALTER TABLE detections ADD COLUMN image_path TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN voting_data TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN env_condition TEXT DEFAULT 'NORMAL'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN quality_score REAL DEFAULT 0.85")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN plate_color TEXT DEFAULT 'WHITE'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN category TEXT DEFAULT 'Private Vehicle'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN violation TEXT DEFAULT 'NONE'")
    except sqlite3.OperationalError:
        pass


    c.execute("CREATE INDEX IF NOT EXISTS idx_plate ON detections(plate)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ts    ON detections(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cam   ON detections(camera_id)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            plate  TEXT PRIMARY KEY,
            reason TEXT DEFAULT 'Flagged'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            plate        TEXT    NOT NULL,
            camera_id    TEXT,
            timestamp    TEXT    NOT NULL,
            alert_type   TEXT    NOT NULL,
            message      TEXT,
            acknowledged INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ghost_profiles (
            ghost_id         TEXT PRIMARY KEY,
            vehicle_type     TEXT NOT NULL,
            body_subtype     TEXT NOT NULL,
            dominant_color   TEXT NOT NULL,
            secondary_color  TEXT DEFAULT '',
            color_hex        TEXT DEFAULT '#64748B',
            aspect_ratio     REAL DEFAULT 1.0,
            visual_embedding TEXT DEFAULT '[]',
            first_seen_ts    TEXT NOT NULL,
            last_seen_ts     TEXT NOT NULL,
            first_camera     TEXT NOT NULL,
            last_camera      TEXT NOT NULL,
            total_sightings  INTEGER DEFAULT 1,
            best_image_path  TEXT DEFAULT '',
            status           TEXT DEFAULT 'ACTIVE_TRACKING',
            estimated_make   TEXT DEFAULT '',
            estimated_model  TEXT DEFAULT '',
            make_confidence  REAL DEFAULT 0.0,
            distinguishing_features TEXT DEFAULT '',
            runner_up        TEXT DEFAULT ''
        )
    """)

    for col, col_type in [
        ("estimated_make", "TEXT DEFAULT ''"),
        ("estimated_model", "TEXT DEFAULT ''"),
        ("make_confidence", "REAL DEFAULT 0.0"),
        ("distinguishing_features", "TEXT DEFAULT ''"),
        ("runner_up", "TEXT DEFAULT ''")
    ]:
        try:
            c.execute(f"ALTER TABLE ghost_profiles ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS ghost_sightings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ghost_id    TEXT NOT NULL,
            camera_id   TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            image_path  TEXT DEFAULT '',
            match_score REAL DEFAULT 1.0,
            speed_kmph  REAL DEFAULT 0.0
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_ghost_id ON ghost_sightings(ghost_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ghost_ts ON ghost_sightings(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ghost_prof_ts ON ghost_profiles(last_seen_ts)")

    for cam in DEFAULT_CAMERAS:
        c.execute("INSERT OR REPLACE INTO cameras (id, name, road, lat, lon, area) VALUES (?,?,?,?,?,?)", cam)

    # Seed demo unplated ghost suspect profiles if none exist
    existing_ghosts = c.execute("SELECT COUNT(*) FROM ghost_profiles").fetchone()[0]
    if existing_ghosts == 0:
        demo_ghosts = [
            ("GHOST_01", "Car", "Sedan", "Silver", "Tinted Glass", "#94A3B8", 1.6, "[]", "2026-09-17T18:10:00", "2026-09-17T19:25:00", "CAM_PATIA", "CAM_JAYADEV", 3, "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706871/ghost_01_sedan.jpg", "ACTIVE_TRACKING", "Hyundai", "Verna", 0.91, "Missing front plate & dark side tint", "Honda City"),
            ("GHOST_02", "SUV", "SUV", "Black", "Black Grille", "#1E293B", 1.4, "[]", "2026-09-17T17:45:00", "2026-09-17T19:10:00", "CAM_KHANDG", "CAM_FIRE_STN", 2, "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706873/ghost_02_suv.jpg", "ACTIVE_TRACKING", "Mahindra", "Scorpio-N", 0.88, "Completely removed front/rear plates", "Tata Harrier"),
            ("GHOST_03", "Car", "Hatchback", "White", "Mud Splatter", "#F8FAFC", 1.5, "[]", "2026-09-17T18:30:00", "2026-09-17T19:35:00", "CAM_RASUL", "CAM_MAST", 3, "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706877/ghost_03_hatch.jpg", "ACTIVE_TRACKING", "Maruti", "Swift", 0.86, "Deliberately mud-covered number plate", "Hyundai i20"),
            ("GHOST_04", "Motorbike", "Sports", "Red", "Black Decals", "#EF4444", 1.2, "[]", "2026-09-17T18:50:00", "2026-09-17T19:40:00", "CAM_KIIT", "CAM_INFOCITY", 2, "https://res.cloudinary.com/me4hfkhj/image/upload/v1789706880/ghost_04_bike.jpg", "ACTIVE_TRACKING", "Yamaha", "R15", 0.94, "Folded tail plate bracket", "KTM RC"),
        ]
        for g in demo_ghosts:
            c.execute("""
                INSERT OR IGNORE INTO ghost_profiles
                (ghost_id, vehicle_type, body_subtype, dominant_color, secondary_color,
                 color_hex, aspect_ratio, visual_embedding, first_seen_ts, last_seen_ts,
                 first_camera, last_camera, total_sightings, best_image_path, status,
                 estimated_make, estimated_model, make_confidence, distinguishing_features, runner_up)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, g)
            c.execute("""
                INSERT OR IGNORE INTO ghost_sightings (ghost_id, camera_id, timestamp, image_path, match_score, speed_kmph)
                VALUES (?,?,?,?,?,?)
            """, (g[0], g[10], g[8], g[13], 0.98, 48.0))
            c.execute("""
                INSERT OR IGNORE INTO ghost_sightings (ghost_id, camera_id, timestamp, image_path, match_score, speed_kmph)
                VALUES (?,?,?,?,?,?)
            """, (g[0], g[11], g[9], g[13], 0.94, 52.0))

    conn.commit()
    conn.close()
    print("Database initialised with 46 Bhubaneswar Smart City cameras and suspect profiles:", DB_PATH)


CAM_FALLBACKS = {
    c[0]: {"name": c[1], "road": c[2], "lat": c[3], "lon": c[4], "area": c[5]}
    for c in DEFAULT_CAMERAS
}

# --- Camera helpers ---

def upsert_camera(cam_id, name, road, lat, lon, area=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO cameras (id, name, road, lat, lon, area) VALUES (?,?,?,?,?,?)",
        (cam_id, name, road, lat, lon, area)
    )
    conn.commit(); conn.close()


def get_all_cameras():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    conn.close()
    res = [dict(r) for r in rows]
    if not res:
        for c_id, c_info in CAM_FALLBACKS.items():
            res.append({"id": c_id, "name": c_info["name"], "road": c_info["road"], "lat": c_info["lat"], "lon": c_info["lon"], "area": c_info["area"]})
    return res


# --- Detection helpers ---

def insert_detection(plate, camera_id, timestamp, confidence=0.0,
                     speed_kmph=0.0, lat=None, lon=None,
                     direction="", vehicle_type="unknown", image_path="", voting_data="",
                     env_condition="NORMAL", quality_score=0.85,
                     plate_color="WHITE", category="Private Vehicle", violation="NONE"):
    # Ensure coordinates are set from camera metadata if not provided
    cam_meta = CAM_FALLBACKS.get(camera_id, {})
    if lat is None:
        lat = cam_meta.get("lat")
    if lon is None:
        lon = cam_meta.get("lon")

    conn = get_conn()
    conn.execute("""
        INSERT INTO detections
            (plate, camera_id, timestamp, confidence, speed_kmph, lat, lon, direction, vehicle_type, image_path, voting_data, env_condition, quality_score, plate_color, category, violation)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (plate, camera_id, timestamp, confidence, speed_kmph, lat, lon, direction, vehicle_type, image_path, voting_data, env_condition, quality_score, plate_color, category, violation))
    conn.commit(); conn.close()

    # Automatically stream to Central Firebase Cloud Database (No local saves requirement)
    try:
        import firebase_sync
        firebase_sync.push_detection(
            plate=plate, camera_id=camera_id, timestamp=timestamp,
            confidence=confidence, speed_kmph=speed_kmph,
            vehicle_type=vehicle_type, image_path=image_path,
            plate_color=plate_color, category=category, violation=violation
        )
    except Exception:
        pass


def get_trajectory(plate):
    clean_p = plate.upper().replace(" ", "")
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.name as camera_name, c.road, c.area, c.lat as cam_lat, c.lon as cam_lon
        FROM detections d
        LEFT JOIN cameras c ON c.id = d.camera_id
        WHERE d.plate = ?
        ORDER BY d.timestamp ASC
    """, (clean_p,)).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        cid = item.get("camera_id", "CAM_01")
        meta = CAM_FALLBACKS.get(cid, {})
        if not item.get("cam_lat") or not item.get("cam_lon"):
            item["cam_lat"] = item.get("lat") or meta.get("lat", 20.2961)
            item["cam_lon"] = item.get("lon") or meta.get("lon", 85.8245)
        if not item.get("camera_name"):
            item["camera_name"] = meta.get("name", cid)
        if not item.get("road"):
            item["road"] = meta.get("road", "Main Road")
        results.append(item)

    # Cloud fallback: if local container has no history, pull full journey from Firebase Firestore
    if not results:
        try:
            import firebase_sync
            fb_doc = firebase_sync.fetch_vehicle_plate(clean_p)
            if fb_doc and "sightings" in fb_doc:
                for s in fb_doc["sightings"]:
                    cid = s.get("camera_id", "CAM_01")
                    meta = CAM_FALLBACKS.get(cid, {})
                    results.append({
                        "plate": clean_p,
                        "camera_id": cid,
                        "camera_name": s.get("camera_name") or meta.get("name", cid),
                        "road": s.get("road") or meta.get("road", "Main Road"),
                        "area": meta.get("area", "Bhubaneswar"),
                        "cam_lat": float(s.get("lat") or meta.get("lat", 20.2961)),
                        "cam_lon": float(s.get("lon") or meta.get("lon", 85.8245)),
                        "timestamp": s.get("timestamp", ""),
                        "speed_kmph": float(s.get("speed_kmph", 40.0)),
                        "confidence": float(s.get("confidence", 0.95)),
                        "image_path": s.get("image_path", ""),
                        "vehicle_type": fb_doc.get("vehicle_type", "Car"),
                        "violation": s.get("violation", "NONE")
                    })
        except Exception:
            pass

    return results




def get_violations(limit=30):
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.name as camera_name, c.road, c.area
        FROM detections d
        LEFT JOIN cameras c ON d.camera_id = c.id
        WHERE d.violation != 'NONE' OR d.plate LIKE '%NO PLATE%' OR d.plate LIKE '%UNREADABLE%'
        ORDER BY d.timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_detections(minutes=15, limit=60):
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.name as camera_name, c.road
        FROM detections d
        LEFT JOIN cameras c ON c.id = d.camera_id
        WHERE d.timestamp >= datetime('now', ?, 'localtime')
        ORDER BY d.timestamp DESC
    """, (f"-{minutes} minutes",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_camera_traffic(minutes=15):
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.camera_id,
               c.name AS camera_name, c.road, c.lat, c.lon, c.area,
               COUNT(DISTINCT d.plate)                                   AS unique_vehicles,
               COUNT(*)                                                   AS total_detections,
               COALESCE(AVG(CASE WHEN d.speed_kmph > 0 THEN d.speed_kmph END), 0) AS avg_speed
        FROM detections d
        LEFT JOIN cameras c ON c.id = d.camera_id
        WHERE d.timestamp >= datetime('now', ?, 'localtime')
        GROUP BY d.camera_id
        ORDER BY unique_vehicles DESC
    """, (f"-{minutes} minutes",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_today():
    conn = get_conn()
    row = conn.execute("""
        SELECT COUNT(DISTINCT plate) AS unique_plates,
               COUNT(*)              AS total_detections
        FROM detections
        WHERE timestamp >= date('now', 'localtime')
    """).fetchone()
    conn.close()
    return dict(row)


def get_od_patterns(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        WITH numbered AS (
            SELECT plate, camera_id, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY plate ORDER BY timestamp) AS rn
            FROM detections
        )
        SELECT a.camera_id AS origin,
               b.camera_id AS destination,
               COUNT(*)    AS trips
        FROM numbered a
        JOIN numbered b ON a.plate = b.plate AND b.rn = a.rn + 1
        GROUP BY origin, destination
        ORDER BY trips DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


COMMON_DEMO_PLATES = [
    "OD05XX9999", "OD02BA4455", "OD01AF2024", "OD33K9876",
    "OD02AY1122", "OD07TR5432", "OD14KL9988", "OD05BB7788",
    "MH12DE1234", "DL10AB1234", "KA01AB1111", "WB02CD4567"
]

def search_plates(query, limit=20):
    clean_q = query.strip().upper().replace(" ", "")
    if not clean_q:
        return []
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT plate FROM detections
        WHERE plate LIKE ?
        ORDER BY plate LIMIT ?
    """, (f"%{clean_q}%", limit)).fetchall()
    results = [r["plate"] for r in rows]

    # Search blacklist
    try:
        bl_rows = conn.execute("SELECT DISTINCT plate FROM blacklist WHERE plate LIKE ? LIMIT ?", (f"%{clean_q}%", limit)).fetchall()
        for br in bl_rows:
            if br["plate"] not in results:
                results.append(br["plate"])
    except Exception:
        pass
    conn.close()

    # Search Central Firebase vehicle plates
    if len(results) < limit:
        try:
            import firebase_sync
            fb_plates = firebase_sync.list_vehicle_plates(limit=30)
            for p_doc in fb_plates:
                p_str = p_doc.get("plate", "")
                if clean_q in p_str.replace(" ", "") and p_str not in results:
                    results.append(p_str)
                    if len(results) >= limit:
                        break
        except Exception:
            pass

    # Include matching realistic demo plates if results are few
    if len(results) < limit:
        for dp in COMMON_DEMO_PLATES:
            if clean_q in dp and dp not in results:
                results.append(dp)
            if len(results) >= limit:
                break

    return results[:limit]



# --- Blacklist helpers ---

def add_to_blacklist(plate, reason="Flagged"):
    p = plate.upper().replace(" ", "")
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO blacklist (plate, reason) VALUES (?,?)", (p, reason))
    conn.commit(); conn.close()


def remove_from_blacklist(plate):
    p = plate.upper().replace(" ", "")
    conn = get_conn()
    conn.execute("DELETE FROM blacklist WHERE plate=?", (p,))
    conn.commit(); conn.close()


def get_blacklist():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM blacklist ORDER BY plate").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_blacklisted(plate):
    p = plate.upper().replace(" ", "")
    conn = get_conn()
    row = conn.execute("SELECT reason FROM blacklist WHERE plate=?", (p,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Alert helpers ---

def insert_alert(plate, camera_id, timestamp, alert_type, message):
    conn = get_conn()
    conn.execute("""
        INSERT INTO alerts (plate, camera_id, timestamp, alert_type, message)
        VALUES (?,?,?,?,?)
    """, (plate, camera_id, timestamp, alert_type, message))
    conn.commit(); conn.close()


def get_alerts(limit=50, unack_only=False):
    conn = get_conn()
    where = "WHERE acknowledged=0" if unack_only else ""
    rows = conn.execute(
        f"SELECT * FROM alerts {where} ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id):
    conn = get_conn()
    conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
    conn.commit(); conn.close()


# --- Ghost / Plate-less Vehicle Re-ID helpers ---

def upsert_ghost_profile(ghost_id, vehicle_type, body_subtype, dominant_color,
                         secondary_color="", color_hex="#64748B", aspect_ratio=1.0,
                         visual_embedding="[]", first_seen_ts="", last_seen_ts="",
                         first_camera="", last_camera="", total_sightings=1,
                         best_image_path="", status="ACTIVE_TRACKING",
                         estimated_make="", estimated_model="", make_confidence=0.0,
                         distinguishing_features="", runner_up=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ghost_profiles
            (ghost_id, vehicle_type, body_subtype, dominant_color, secondary_color,
             color_hex, aspect_ratio, visual_embedding, first_seen_ts, last_seen_ts,
             first_camera, last_camera, total_sightings, best_image_path, status,
             estimated_make, estimated_model, make_confidence, distinguishing_features, runner_up)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(ghost_id) DO UPDATE SET
            last_seen_ts = excluded.last_seen_ts,
            last_camera = excluded.last_camera,
            total_sightings = ghost_profiles.total_sightings + 1,
            best_image_path = CASE WHEN excluded.best_image_path != '' THEN excluded.best_image_path ELSE ghost_profiles.best_image_path END,
            estimated_make = CASE WHEN excluded.estimated_make != '' THEN excluded.estimated_make ELSE ghost_profiles.estimated_make END,
            estimated_model = CASE WHEN excluded.estimated_model != '' THEN excluded.estimated_model ELSE ghost_profiles.estimated_model END,
            make_confidence = CASE WHEN excluded.make_confidence > 0 THEN excluded.make_confidence ELSE ghost_profiles.make_confidence END,
            distinguishing_features = CASE WHEN excluded.distinguishing_features != '' THEN excluded.distinguishing_features ELSE ghost_profiles.distinguishing_features END,
            runner_up = CASE WHEN excluded.runner_up != '' THEN excluded.runner_up ELSE ghost_profiles.runner_up END
    """, (ghost_id, vehicle_type, body_subtype, dominant_color, secondary_color,
          color_hex, aspect_ratio, visual_embedding, first_seen_ts, last_seen_ts,
          first_camera, last_camera, total_sightings, best_image_path, status,
          estimated_make, estimated_model, make_confidence, distinguishing_features, runner_up))
    conn.commit(); conn.close()


def update_ghost_last_seen(ghost_id, last_seen_ts, last_camera, new_image_path=""):
    conn = get_conn()
    conn.execute("""
        UPDATE ghost_profiles
        SET last_seen_ts = ?,
            last_camera = ?,
            total_sightings = total_sightings + 1,
            best_image_path = CASE WHEN ? != '' THEN ? ELSE best_image_path END
        WHERE ghost_id = ?
    """, (last_seen_ts, last_camera, new_image_path, new_image_path, ghost_id))
    conn.commit(); conn.close()


def insert_ghost_sighting(ghost_id, camera_id, timestamp, image_path="", match_score=1.0, speed_kmph=0.0):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ghost_sightings
            (ghost_id, camera_id, timestamp, image_path, match_score, speed_kmph)
        VALUES (?,?,?,?,?,?)
    """, (ghost_id, camera_id, timestamp, image_path, match_score, speed_kmph))
    conn.commit(); conn.close()


def get_all_ghost_profiles(limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM ghost_profiles
        ORDER BY last_seen_ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ghost_profile_by_id(ghost_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM ghost_profiles WHERE ghost_id=?", (ghost_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_ghost_candidates(limit=40):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM ghost_profiles
        ORDER BY last_seen_ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ghost_trajectory(ghost_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, c.name as camera_name, c.road, c.lat, c.lon, c.area
        FROM ghost_sightings s
        LEFT JOIN cameras c ON s.camera_id = c.id
        WHERE s.ghost_id = ?
        ORDER BY s.timestamp ASC
    """, (ghost_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_live_db():
    """Clears temporary/live upload detections and unplated records so every upload has completely fresh data."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM detections WHERE camera_id IN ('CAM_LIVE', 'CAM_CCTV_STREAM')")
        conn.execute("DELETE FROM ghost_sightings WHERE camera_id IN ('CAM_LIVE', 'CAM_CCTV_STREAM')")
        conn.execute("DELETE FROM ghost_profiles WHERE ghost_id LIKE 'UNPLATED-%'")
        conn.commit()
    except Exception as e:
        print(f"[DB] clear_live_db note: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()


