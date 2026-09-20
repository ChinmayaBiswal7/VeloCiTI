"""
analytics.py - Traffic analytics calculations
Reads from the database and returns structured analytics data.
"""

import math
import database as db


# -----------------------------------------------------------------------
# Congestion level classifier
# -----------------------------------------------------------------------
def congestion_level(unique_vehicles_per_15min):
    if unique_vehicles_per_15min >= 80:
        return "SEVERE"
    elif unique_vehicles_per_15min >= 40:
        return "HIGH"
    elif unique_vehicles_per_15min >= 15:
        return "MODERATE"
    else:
        return "LOW"


CONGESTION_COLOR = {
    "SEVERE":   "#dc2626",   # red
    "HIGH":     "#f97316",   # orange
    "MODERATE": "#eab308",   # yellow
    "LOW":      "#22c55e",   # green
}


# -----------------------------------------------------------------------
# Per-camera traffic summary (used by heatmap tab)
# -----------------------------------------------------------------------
def get_camera_summary(minutes=15):
    rows = db.get_camera_traffic(minutes)
    result = []
    for r in rows:
        level = congestion_level(r["unique_vehicles"])
        result.append({
            **r,
            "congestion":       level,
            "congestion_color": CONGESTION_COLOR[level],
            "avg_speed":        round(r["avg_speed"] or 0, 1),
        })
    return result


# -----------------------------------------------------------------------
# City-wide summary stats (used by overview cards)
# -----------------------------------------------------------------------
def get_city_summary(minutes=15):
    today   = db.get_total_today()
    cameras = db.get_all_cameras()
    traffic = db.get_camera_traffic(minutes)
    alerts  = db.get_alerts(unack_only=True)

    congested = sum(
        1 for r in traffic
        if congestion_level(r["unique_vehicles"]) in ("HIGH", "SEVERE")
    )

    active_cams = len(traffic)           # cameras that saw traffic in last 15 min
    total_cams  = len(cameras)

    return {
        "vehicles_today":      today["unique_plates"],
        "detections_today":    today["total_detections"],
        "total_cameras":       total_cams,
        "active_cameras":      active_cams,
        "congested_roads":     congested,
        "active_alerts":       len(alerts),
    }


# -----------------------------------------------------------------------
# Speed between two cameras (using haversine distance)
# -----------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def enrich_trajectory(trajectory):
    """
    Add inter-camera speed estimates to a trajectory list.
    Each entry gets a `travel_minutes` and `est_speed_kmph` field.
    """
    enriched = []
    for i, entry in enumerate(trajectory):
        e = dict(entry)
        if i == 0:
            e["travel_minutes"] = 0
            e["est_speed_kmph"] = 0
        else:
            prev = trajectory[i - 1]
            try:
                from datetime import datetime
                t0 = datetime.fromisoformat(prev["timestamp"])
                t1 = datetime.fromisoformat(e["timestamp"])
                minutes = (t1 - t0).total_seconds() / 60
                e["travel_minutes"] = round(minutes, 1)

                # If both cameras have GPS coords, compute real speed
                if (prev.get("cam_lat") and e.get("cam_lat") and minutes > 0):
                    dist_km = haversine_km(
                        prev["cam_lat"], prev["cam_lon"],
                        e["cam_lat"], e["cam_lon"]
                    )
                    e["est_speed_kmph"] = round((dist_km / minutes) * 60, 1)
                else:
                    e["est_speed_kmph"] = 0
            except Exception:
                e["travel_minutes"] = 0
                e["est_speed_kmph"] = 0
        enriched.append(e)
    return enriched


# -----------------------------------------------------------------------
# Origin-Destination flow data
# -----------------------------------------------------------------------
def get_od_flow():
    return db.get_od_patterns(limit=15)
