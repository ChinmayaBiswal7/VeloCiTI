"""
alerts.py - Blacklist checking and route anomaly detection
Called every time a new detection is inserted into the database.
"""

from datetime import datetime, timedelta
import database as db


# -----------------------------------------------------------------------
# Check a new detection against the blacklist and recent trajectory
# -----------------------------------------------------------------------
def check_detection(plate, camera_id, timestamp_str):
    """
    Call this immediately after every new detection is stored.
    Generates alerts if:
      1. The plate is on the blacklist.
      2. The plate appeared at two cameras faster than physically possible
         (suggesting plate cloning / data error) — route anomaly.
    """
    plate = plate.upper().replace(" ", "")
    alerts_generated = []

    # --- 1. Blacklist check ---
    bl = db.is_blacklisted(plate)
    if bl:
        msg = f"Blacklisted vehicle [{plate}] detected at {camera_id}. Reason: {bl['reason']}"
        db.insert_alert(plate, camera_id, timestamp_str, "BLACKLIST", msg)
        alerts_generated.append({"type": "BLACKLIST", "message": msg})
        try:
            import firebase_sync
            firebase_sync.push_alert(plate, "BLACKLIST_HIT", camera_id, timestamp_str, msg)
        except Exception:
            pass

    # --- 2. Route anomaly: same plate at two cameras within unrealistic time ---
    trajectory = db.get_trajectory(plate)
    if len(trajectory) >= 2:
        # Look at the last two observations
        prev = trajectory[-2]
        curr = trajectory[-1]
        try:
            t_prev = datetime.fromisoformat(prev["timestamp"])
            t_curr = datetime.fromisoformat(curr["timestamp"])
            delta_minutes = abs((t_curr - t_prev).total_seconds()) / 60

            # If two different cameras saw the same plate in < 1 min, flag it
            if delta_minutes < 1 and prev["camera_id"] != curr["camera_id"]:
                msg = (
                    f"Anomaly: [{plate}] appeared at {prev['camera_id']} and "
                    f"{curr['camera_id']} within {delta_minutes:.1f} minutes — possible plate clone."
                )
                db.insert_alert(plate, camera_id, timestamp_str, "ANOMALY", msg)
                alerts_generated.append({"type": "ANOMALY", "message": msg})
        except Exception:
            pass

    return alerts_generated


# -----------------------------------------------------------------------
# Seed a few demo blacklist entries (called once at startup)
# -----------------------------------------------------------------------
DEMO_BLACKLIST = [
    ("OD05XX9999", "Stolen vehicle"),
    ("MH12DE1234", "Wanted in robbery case"),
    ("KA01AB1111", "Unpaid challans > 50"),
]

def seed_demo_blacklist():
    for plate, reason in DEMO_BLACKLIST:
        db.add_to_blacklist(plate, reason)
    print(f"Demo blacklist seeded with {len(DEMO_BLACKLIST)} entries.")
