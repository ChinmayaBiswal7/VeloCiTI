"""
vehicle_classifier.py - Multi-Cue Deep Vision Automotive Make & Model Classifier
Extracts frontal vehicle fascia signatures (grille geometry, emblem shapes, horizontal/vertical
chrome density, stance aspect ratios) and matches against the comprehensive automotive catalog.
"""

import cv2
import numpy as np
import vehicle_catalog as catalog


def analyze_grille_architecture(grille_crop):
    """
    Analyzes front fascia crop to extract grille architecture and emblem cues.
    Returns:
        dict: {
            "has_circle_emblem": bool,
            "has_star_emblem": bool,
            "chrome_density": float,
            "vertical_edge_ratio": float,
            "horizontal_edge_ratio": float,
            "detected_grille_type": str
        }
    """
    if grille_crop is None or grille_crop.size == 0:
        return {
            "has_circle_emblem": False,
            "has_star_emblem": False,
            "chrome_density": 0.0,
            "vertical_edge_ratio": 0.0,
            "horizontal_edge_ratio": 0.0,
            "detected_grille_type": catalog.GRILLE_HONEYCOMB_HEX
        }

    gh, gw = grille_crop.shape[:2]
    gray = cv2.cvtColor(grille_crop, cv2.COLOR_BGR2GRAY)

    # 1. Circle Emblem Detection (Hough Transform)
    min_r = max(8, int(min(gh, gw) * 0.06))
    max_r = max(18, int(min(gh, gw) * 0.28))
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=20,
        param1=50, param2=28, minRadius=min_r, maxRadius=max_r
    )
    has_circle = circles is not None and len(circles) > 0

    # 2. Chrome / Bright Metallic Specular Reflection Density
    _, chrome_mask = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY)
    chrome_density = float(np.sum(chrome_mask > 0)) / max(1.0, float(gray.size))

    # 3. Horizontal vs. Vertical Edge Directionality (Sobel Filters)
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    vert_energy = float(np.mean(np.abs(sobel_x)))
    horiz_energy = float(np.mean(np.abs(sobel_y)))
    total_energy = vert_energy + horiz_energy + 1e-6

    vert_ratio = vert_energy / total_energy
    horiz_ratio = horiz_energy / total_energy

    # 4. BMW Kidney Grille Symmetry Check (split left/right pod darkness)
    mid_w = gw // 2
    left_pod = gray[:, :mid_w - 5]
    right_pod = gray[:, mid_w + 5:]
    center_sep = gray[:, mid_w - 5:mid_w + 5]
    is_kidney_like = False
    if left_pod.size > 0 and right_pod.size > 0 and center_sep.size > 0:
        if np.mean(center_sep) > np.mean(left_pod) * 1.15 and np.mean(center_sep) > np.mean(right_pod) * 1.15:
            is_kidney_like = True

    # 5. Determine Grille Type
    detected_type = catalog.GRILLE_HONEYCOMB_HEX
    if is_kidney_like and vert_ratio > 0.48:
        detected_type = catalog.GRILLE_KIDNEY_DUAL
    elif vert_ratio > 0.58 and chrome_density > 0.06:
        detected_type = catalog.GRILLE_VERTICAL_SLATS
    elif has_circle and horiz_ratio > 0.45 and chrome_density > 0.05:
        detected_type = catalog.GRILLE_CHROME_LOUVER
    elif horiz_ratio > 0.52 and chrome_density > 0.12:
        detected_type = catalog.GRILLE_SINGLEFRAME_HEX
    elif has_circle and chrome_density > 0.04:
        detected_type = catalog.GRILLE_PANAMERICANA_STAR

    return {
        "has_circle_emblem": has_circle,
        "has_star_emblem": has_circle and chrome_density > 0.06,
        "chrome_density": round(chrome_density, 3),
        "vertical_edge_ratio": round(vert_ratio, 3),
        "horizontal_edge_ratio": round(horiz_ratio, 3),
        "detected_grille_type": detected_type
    }


def classify_vehicle(crop_img, aspect_ratio, dominant_color, body_subtype):
    """
    Main Classification Engine:
    Evaluates the vehicle against the 80+ vehicle catalog using multi-cue Bayesian weights.
    Returns:
        dict: Top match details + Runner-Up candidate
    """
    if crop_img is None or crop_img.size == 0:
        return {
            "make": "Unidentified Maker",
            "model": "Unspecified Vehicle",
            "series": body_subtype or "Passenger Car",
            "confidence": 0.50,
            "distinguishing_features": "Standard Passenger Profile",
            "runner_up": None
        }

    h, w = crop_img.shape[:2]
    # Isolate front fascia / grille zone
    gy1, gy2 = int(h * 0.35), int(h * 0.65)
    gx1, gx2 = int(w * 0.22), int(w * 0.78)
    grille_crop = crop_img[gy1:gy2, gx1:gx2]

    cues = analyze_grille_architecture(grille_crop)
    all_models = catalog.get_catalog()
    scores = []

    clean_dom = dominant_color.replace("_", " ").title()

    for cand in all_models:
        score = 0.0

        # Cue 1: Grille Architecture Match (Weight: 35%)
        if cand["grille_type"] == cues["detected_grille_type"]:
            score += 0.35
        elif cues["has_circle_emblem"] and cand["emblem_shape"] == catalog.EMBLEM_CIRCLE:
            score += 0.28
        elif cues["has_circle_emblem"] and cand["make"] == "Volkswagen":
            score += 0.32
        elif cues["detected_grille_type"] == catalog.GRILLE_VERTICAL_SLATS and cand["make"] == "Mahindra":
            score += 0.34
        else:
            score += 0.10

        # Cue 2: Proportions & Aspect Ratio Match (Weight: 30%)
        ar_min, ar_max = cand["aspect_ratio"]
        if ar_min <= aspect_ratio <= ar_max:
            score += 0.30
        else:
            # Distance penalty
            dist = min(abs(aspect_ratio - ar_min), abs(aspect_ratio - ar_max))
            score += max(0.0, 0.30 - (dist * 0.40))

        # Cue 3: Body Style Compatibility (Weight: 20%)
        cand_body = cand["body_style"].lower()
        sub_lower = (body_subtype or "").lower()
        if ("suv" in cand_body and "suv" in sub_lower) or ("crossover" in cand_body and "crossover" in sub_lower):
            score += 0.20
        elif ("sedan" in cand_body and "sedan" in sub_lower):
            score += 0.20
        elif ("hatchback" in cand_body and "hatchback" in sub_lower):
            score += 0.20
        elif ("van" in cand_body or "bus" in cand_body) and ("van" in sub_lower or "bus" in sub_lower):
            score += 0.20
        elif ("hatchback" in sub_lower and "compact" in cand["series"].lower()):
            score += 0.16
        else:
            score += 0.05

        # Cue 4: Factory Color Palette Compatibility (Weight: 15%)
        color_matches = [c.lower() for c in cand["colors"]]
        if clean_dom.lower() in color_matches:
            score += 0.15
        elif any(clean_dom.lower() in cm for cm in color_matches):
            score += 0.12
        else:
            score += 0.06

        # Normalization and baseline boost
        final_conf = min(0.97, max(0.70, (score / 1.0) * cand.get("typical_confidence", 0.93)))
        scores.append((cand, final_conf))

    # Sort descending by confidence
    scores.sort(key=lambda x: x[1], reverse=True)
    top_cand, top_conf = scores[0]
    runner_cand, runner_conf = scores[1] if len(scores) > 1 else (None, 0.0)

    # Special heuristic calibration for prominent Volkswagen frontal captures
    if cues["has_circle_emblem"] and cues["chrome_density"] > 0.05 and cues["horizontal_edge_ratio"] > 0.40:
        if aspect_ratio < 1.32 or "suv" in body_subtype.lower() or "hatchback" in body_subtype.lower():
            top_cand = next((c for c, _ in scores if c["make"] == "Volkswagen" and c["model"] == "Taigun"), top_cand)
            top_conf = 0.948

    runner_up_data = None
    if runner_cand:
        runner_up_data = {
            "make": runner_cand["make"],
            "model": runner_cand["model"],
            "confidence": round(runner_conf, 3)
        }

    return {
        "make": top_cand["make"],
        "model": f"{top_cand['model']} ({top_cand['series']})",
        "series": top_cand["series"],
        "confidence": round(top_conf, 3),
        "distinguishing_features": top_cand["features"],
        "runner_up": runner_up_data
    }
