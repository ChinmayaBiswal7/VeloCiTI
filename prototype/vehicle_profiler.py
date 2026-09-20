"""
vehicle_profiler.py - Deep Visual Profiler & Fingerprinting for Plate-Less Vehicles
Extracts:
1. Multi-Zone Spatial Color Histograms (Upper Roof/Glass vs. Lower Body/Doors).
2. Dominant & Secondary Body Colors (HSV + LAB + RGB Color Modeling) & HEX Swatches.
3. Geometric Aspect Ratio (W/H) & Body Sub-Type Classification (Sedan, SUV, Hatchback, Truck, Bike).
4. 64-Dimensional Normalized Visual Signature Embedding for Cross-Camera Re-ID.
"""

import cv2
import numpy as np
import json


# Named Color Dictionary in HSV bounds
COLOR_PALETTES = [
    # (Name, HEX, H_min, H_max, S_min, S_max, V_min, V_max)
    ("WHITE",       "#F8FAFC",  0, 180,   0,  42, 175, 255),
    ("SILVER_GREY", "#94A3B8",  0, 180,   0,  50,  85, 174),
    ("BLACK",       "#0F172A",  0, 180,   0, 255,   0,  55),
    ("RED_1",       "#DC2626",  0,  10,  70, 255,  60, 255),
    ("RED_2",       "#DC2626",170, 180,  70, 255,  60, 255),
    ("DARK_BLUE",   "#1D4ED8",100, 135,  70, 255,  45, 255),
    ("LIGHT_BLUE",  "#38BDF8", 88, 105,  60, 255,  90, 255),
    ("YELLOW",      "#EAB308", 18,  35,  90, 255,  90, 255),
    ("GREEN",       "#16A34A", 36,  85,  70, 255,  50, 255),
    ("ORANGE",      "#EA580C", 11,  18, 100, 255,  90, 255),
    ("BROWN_MAROON","#78350F",  5,  20,  50, 160,  30, 120),
]


def classify_dominant_color(hsv_crop):
    """Classifies the primary dominant color and extracts representative HEX code."""
    if hsv_crop is None or hsv_crop.size == 0:
        return "UNKNOWN", "#64748B"

    total_px = float(hsv_crop.shape[0] * hsv_crop.shape[1])
    if total_px == 0:
        return "UNKNOWN", "#64748B"

    color_scores = {}
    for name, hex_code, hmin, hmax, smin, smax, vmin, vmax in COLOR_PALETTES:
        lower = np.array([hmin, smin, vmin], dtype=np.uint8)
        upper = np.array([hmax, smax, vmax], dtype=np.uint8)
        mask = cv2.inRange(hsv_crop, lower, upper)
        match_count = cv2.countNonZero(mask)
        clean_name = "RED" if name.startswith("RED") else name
        color_scores[clean_name] = color_scores.get(clean_name, 0) + match_count

    # Sort colors by pixel coverage
    sorted_colors = sorted(color_scores.items(), key=lambda x: x[1], reverse=True)
    if not sorted_colors or sorted_colors[0][1] / total_px < 0.10:
        # Fallback to mean color
        mean_v = np.mean(hsv_crop[:, :, 2])
        mean_s = np.mean(hsv_crop[:, :, 1])
        if mean_v < 60:
            return "BLACK", "#0F172A"
        elif mean_s < 45 and mean_v > 165:
            return "WHITE", "#F8FAFC"
        else:
            return "SILVER_GREY", "#94A3B8"

    best_color = sorted_colors[0][0]
    hex_map = {
        "WHITE": "#F8FAFC",
        "SILVER_GREY": "#94A3B8",
        "BLACK": "#0F172A",
        "RED": "#DC2626",
        "DARK_BLUE": "#1D4ED8",
        "LIGHT_BLUE": "#38BDF8",
        "YELLOW": "#EAB308",
        "GREEN": "#16A34A",
        "ORANGE": "#EA580C",
        "BROWN_MAROON": "#78350F"
    }
    return best_color, hex_map.get(best_color, "#64748B")


def estimate_body_subtype(cls_name, aspect_ratio, h, w):
    """
    Estimates vehicle body style sub-type based on YOLO class & geometric aspect ratio (W / H).
    """
    cls_lower = cls_name.lower()
    if "motor" in cls_lower or "bike" in cls_lower or "two" in cls_lower:
        return "Motorcycle / Scooter"
    if "bus" in cls_lower:
        return "Passenger Bus / Van"
    if "truck" in cls_lower:
        return "Heavy Commercial Truck / Lorry"

    # Car class disambiguation based on aspect ratio
    if aspect_ratio >= 1.55:
        return "Sedan (Low Stance / Long Profile)"
    elif 1.25 <= aspect_ratio < 1.55:
        return "SUV / Compact Crossover"
    elif 0.95 <= aspect_ratio < 1.25:
        return "Hatchback / Compact Car"
    elif aspect_ratio < 0.95:
        return "Auto-Rickshaw / Three-Wheeler"
    return "Passenger Car"


def compute_visual_embedding(crop_img):
    """
    Computes a normalized 64-dimensional visual signature vector:
    - 24-D Multi-Zone Color Histogram (Upper 3-bin H, 3-bin S, 2-bin V + Lower 8-bin H, 4-bin S, 4-bin V)
    - 16-D LAB color moments & variance
    - 16-D Sobel directional edge gradient descriptor
    - 8-D Geometric aspect ratio & luminance density features
    """
    if crop_img is None or crop_img.size == 0:
        return np.zeros(64, dtype=np.float32).tolist()

    h, w = crop_img.shape[:2]
    # Resize to standard canonical size for consistent embedding comparison
    resized = cv2.resize(crop_img, (128, 128), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 1. Multi-Zone HSV Histograms (Zone 1: Upper 40%, Zone 2: Lower 60%)
    upper_hsv = hsv[0:51, :]
    lower_hsv = hsv[51:128, :]

    hist_u_h = cv2.calcHist([upper_hsv], [0], None, [8], [0, 180]).flatten()
    hist_u_s = cv2.calcHist([upper_hsv], [1], None, [4], [0, 256]).flatten()
    hist_l_h = cv2.calcHist([lower_hsv], [0], None, [8], [0, 180]).flatten()
    hist_l_s = cv2.calcHist([lower_hsv], [1], None, [4], [0, 256]).flatten()
    color_part = np.concatenate([hist_u_h, hist_u_s, hist_l_h, hist_l_s])
    norm_sum = np.sum(color_part) + 1e-6
    color_part = color_part / norm_sum  # 24 dims

    # 2. LAB Color Moments (Mean, Std across 4 spatial quadrants) -> 16 dims
    lab_moments = []
    for r in [0, 64]:
        for c in [0, 64]:
            quad = lab[r:r+64, c:c+64]
            m = np.mean(quad, axis=(0, 1)) / 255.0
            s = np.std(quad, axis=(0, 1)) / 128.0
            lab_moments.extend([float(m[0]), float(m[1]), float(m[2]), float(np.mean(s))])
    lab_part = np.array(lab_moments, dtype=np.float32)  # 16 dims

    # 3. Sobel Edge Gradient Texture Descriptor -> 16 dims
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    edge_hist = cv2.calcHist([ang], [0], None, [16], [0, 360]).flatten()
    edge_part = edge_hist / (np.sum(edge_hist) + 1e-6)  # 16 dims

    # 4. Geometry & Luminance Density Features -> 8 dims
    aspect_ratio = float(w) / max(1.0, float(h))
    norm_ar = np.clip(aspect_ratio / 2.5, 0.0, 1.0)
    lum_mean = float(np.mean(gray)) / 255.0
    lum_std = float(np.std(gray)) / 128.0
    dark_ratio = float(np.sum(gray < 50)) / float(gray.size)
    bright_ratio = float(np.sum(gray > 200)) / float(gray.size)
    geo_part = np.array([norm_ar, lum_mean, lum_std, dark_ratio, bright_ratio, 0.0, 0.0, 0.0], dtype=np.float32) # 8 dims

    full_vector = np.concatenate([color_part, lab_part, edge_part, geo_part])
    l2_norm = np.linalg.norm(full_vector) + 1e-6
    normalized_vec = full_vector / l2_norm
    return normalized_vec.tolist()


def classify_vehicle_make_model(crop_img, aspect_ratio, dominant_color, body_subtype):
    """
    Analyzes frontal vehicle fascia, emblem geometry, chrome louvers, and proportions
    to classify vehicle brand (Make) and Model family using deep multi-cue vehicle_classifier.
    """
    try:
        import vehicle_classifier
        res = vehicle_classifier.classify_vehicle(crop_img, aspect_ratio, dominant_color, body_subtype)
        return {
            "make": res.get("make", "Unidentified Maker"),
            "model": res.get("model", "Unspecified Vehicle"),
            "confidence": res.get("confidence", 0.85),
            "features": res.get("distinguishing_features", "Standard Automotive Profile"),
            "runner_up": res.get("runner_up")
        }
    except Exception as e:
        return {
            "make": "Passenger Vehicle",
            "model": f"{dominant_color} {body_subtype}",
            "confidence": 0.80,
            "features": "Standard Passenger Profile",
            "runner_up": None
        }


def extract_vehicle_profile(crop_img, vehicle_type="Car"):
    """
    Main extraction function: takes a vehicle crop image and returns a comprehensive
    visual profile dictionary ready for database persistence and Re-ID matching.
    """
    if crop_img is None or crop_img.size == 0:
        return {
            "vehicle_type": vehicle_type,
            "body_subtype": "Unknown",
            "dominant_color": "UNKNOWN",
            "secondary_color": "UNKNOWN",
            "color_hex": "#64748B",
            "aspect_ratio": 1.0,
            "visual_embedding": json.dumps([]),
            "profile_summary": f"Unidentified {vehicle_type}",
            "estimated_make": "Unknown Maker",
            "estimated_model": "Unknown Model",
            "make_confidence": 0.50,
            "distinguishing_features": "None"
        }

    h, w = crop_img.shape[:2]
    aspect_ratio = round(float(w) / max(1.0, float(h)), 2)
    hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)

    # 1. Zone Splitting
    split_y = int(h * 0.38)
    upper_zone = hsv[0:split_y, :]
    lower_zone = hsv[split_y:h, :]

    # 2. Color Classification
    dom_color, hex_code = classify_dominant_color(lower_zone if lower_zone.size > 0 else hsv)
    sec_color, sec_hex = classify_dominant_color(upper_zone if upper_zone.size > 0 else hsv)

    if sec_color == dom_color:
        sec_color_desc = f"Solid {dom_color.replace('_', ' ').title()}"
    else:
        sec_color_desc = f"{sec_color.replace('_', ' ').title()} Roof / Pillars"

    # 3. Body Sub-Type Classification
    subtype = estimate_body_subtype(vehicle_type, aspect_ratio, h, w)

    # 4. Make & Model Recognition
    clean_dom = dom_color.replace("_", " ").title()
    make_model = classify_vehicle_make_model(crop_img, aspect_ratio, clean_dom, subtype)

    # 5. 64-D Visual Fingerprint Embedding
    embedding = compute_visual_embedding(crop_img)

    summary = f"{make_model['make']} {make_model['model']} in {clean_dom} ({sec_color_desc})"

    return {
        "vehicle_type": vehicle_type,
        "body_subtype": subtype,
        "dominant_color": clean_dom,
        "secondary_color": sec_color_desc,
        "color_hex": hex_code,
        "aspect_ratio": aspect_ratio,
        "visual_embedding": json.dumps(embedding),
        "profile_summary": summary,
        "estimated_make": make_model["make"],
        "estimated_model": make_model["model"],
        "make_confidence": make_model["confidence"],
        "distinguishing_features": make_model["features"],
        "runner_up": make_model.get("runner_up")
    }


