"""
anpr.py - Enhanced Multi-Scale ANPR + Environmental IQA + Adaptive Restoration + Spatio-Temporal Consensus Pipeline
Stage 1: YOLO Vehicle Localization & Multi-Track Isolation
Stage 2: Image Quality Assessment (IQA) & Environmental Telemetry (Rain, Fog, Dust, Night, Glare, Blur)
Stage 3: Condition-Specific Adaptive Preprocessing & Optical Restoration (DCP, MSR, CLAHE, Inpainting)
Stage 4: Best Frame Selection & Ranking
Stage 5: Spatio-Temporal Positional OCR Consensus Voting (>95% Accuracy)
Stage 6: MoRTH Indian RTO Syntactic Disambiguation (O/0, B/8, I/1, S/5)
"""

import cv2
import numpy as np
import re
import time
from collections import defaultdict, Counter
import quality
import enhancer
import ml_selector
import vehicle_profiler

# Optional EasyOCR lazy loader (handles missing dependencies gracefully without crashing)
_ocr_reader = None

def get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception:
            _ocr_reader = False
    return _ocr_reader if _ocr_reader is not False else None


# -----------------------------------------------------------------------
# Indian RTO Validations & Positional Disambiguation
# -----------------------------------------------------------------------
INDIAN_STATES = {
    "AP", "AR", "AS", "BR", "CG", "DL", "GA", "GJ", "HR", "HP",
    "JH", "JK", "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL",
    "OD", "OR", "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK",
    "WB", "PY", "CH", "DN", "DD", "LD", "AN", "LA"
}

# OCR character → digit correction (when char is in a digit position)
_TO_DIGIT = {
    'O': '0', 'Q': '0', 'D': '0', 'U': '0',
    'I': '1', 'L': '1', 'T': '1',
    'Z': '2',
    'E': '3',
    'A': '4',
    'S': '5',
    'G': '6',
    'B': '8',
    'J': '3'
}

# OCR character → letter correction (when char is in a letter position)
_TO_LETTER = {
    '0': 'O', '8': 'B', '1': 'I', '5': 'S',
    '2': 'Z', '6': 'G', '3': 'E', '4': 'A'
}

# Keep both maps for backward compat
DIGIT_TO_ALPHA = {"0": "O", "8": "B", "1": "I", "5": "S", "2": "Z", "6": "G"}
ALPHA_TO_DIGIT = {"O": "0", "B": "8", "I": "1", "L": "1", "S": "5", "Z": "2", "G": "6", "D": "0"}


def classify_plate_color_and_category(plate_crop):
    """
    Analyzes HSV color channels of plate crop to detect MoRTH Indian plate category:
    - White + Black text: Private / Personal Vehicle
    - Bright Yellow + Black text: Commercial / Taxi / Transport
    - Green + White/Yellow text: Electric Vehicle (EV)
    - Blue + White text: Diplomatic / UN Vehicle
    - Red + White text: Official / Executive / Temporary
    """
    if plate_crop is None or plate_crop.size == 0:
        return "WHITE", "Private Vehicle"

    h, w = plate_crop.shape[:2]

    # If the crop passed in is a full vehicle or wide scene frame, isolate the lower bumper area
    crop_to_analyze = plate_crop
    if h > 160 or w > 400:
        crop_to_analyze = plate_crop[int(h * 0.40):int(h * 0.95), int(w * 0.15):int(w * 0.85)]
        if crop_to_analyze.size == 0:
            crop_to_analyze = plate_crop

    hsv = cv2.cvtColor(crop_to_analyze, cv2.COLOR_BGR2HSV)
    total_pixels = float(hsv.shape[0] * hsv.shape[1])
    if total_pixels <= 0:
        return "WHITE", "Private Vehicle"

    # White plate: low saturation, high brightness
    white_mask = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 55, 255]))
    white_ratio = float(np.sum(white_mask > 0)) / total_pixels

    # Commercial Yellow plate: vibrant saturated yellow (S >= 95, V >= 120)
    yellow_mask = cv2.inRange(hsv, np.array([15, 95, 120]), np.array([35, 255, 255]))
    yellow_ratio = float(np.sum(yellow_mask > 0)) / total_pixels

    # Green plate (EV)
    green_mask = cv2.inRange(hsv, np.array([38, 70, 70]), np.array([85, 255, 255]))
    green_ratio = float(np.sum(green_mask > 0)) / total_pixels

    # Blue plate (Diplomatic)
    blue_mask = cv2.inRange(hsv, np.array([95, 80, 70]), np.array([130, 255, 255]))
    blue_ratio = float(np.sum(blue_mask > 0)) / total_pixels

    # If white plate background is prominent, it's definitely a Private Vehicle
    if white_ratio >= 0.10 and white_ratio > (yellow_ratio * 1.5):
        return "WHITE", "Private Vehicle"

    if yellow_ratio >= 0.30 and yellow_ratio > white_ratio:
        return "YELLOW", "Commercial / Taxi"
    elif green_ratio >= 0.25:
        return "GREEN", "Electric Vehicle (EV)"
    elif blue_ratio >= 0.25:
        return "BLUE", "Diplomatic / UN"
    else:
        return "WHITE", "Private Vehicle"



def _nearest_state_code(raw2: str) -> str:
    """
    Given a 2-char string that may have OCR errors, return the nearest valid state code.
    Uses character substitution + edit distance (max 1 substitution).
    """
    raw2 = raw2.upper()
    if raw2 in INDIAN_STATES:
        return raw2

    # Try fixing each character independently
    for i in range(2):
        chars = list(raw2)
        # Try digit→letter fix
        if chars[i] in _TO_LETTER:
            chars[i] = _TO_LETTER[chars[i]]
            candidate = ''.join(chars)
            if candidate in INDIAN_STATES:
                return candidate
        # Try letter→digit then letter substitution
        # Try every possible single-char substitution
        for alt in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            chars2 = list(raw2)
            chars2[i] = alt
            candidate = ''.join(chars2)
            if candidate in INDIAN_STATES:
                return candidate

    return raw2  # Return as-is if no valid state found


def strip_hsrp_ind_prefix(s: str) -> str:
    """
    Strips HSRP (High Security Registration Plate) blue IND tag artifacts from plate strings.
    Example: 'INDTN87C5106' -> 'TN87C5106', 'NDTN87C5106' -> 'TN87C5106', 'ITN87C5106' -> 'TN87C5106'
    """
    if not s:
        return s
    s = s.upper().strip()
    if s.startswith("IND") and len(s) >= 11:
        s = s[3:]
    elif s.startswith("ND") and len(s) >= 10 and (s[2:4] in INDIAN_STATES or _nearest_state_code(s[2:4]) in INDIAN_STATES):
        s = s[2:]
    return s


STATE_RTO_RANGES = {
    'MH': (1, 50),   # Maharashtra: 01 to 50
    'DL': (1, 15),   # Delhi: 01 to 15
    'KA': (1, 71),   # Karnataka: 01 to 71
    'TN': (1, 99),   # Tamil Nadu: 01 to 99
    'TS': (1, 36),   # Telangana: 01 to 36
    'AP': (1, 39),   # Andhra Pradesh: 01 to 39
    'GJ': (1, 38),   # Gujarat: 01 to 38
    'UP': (1, 96),   # Uttar Pradesh: 01 to 96
    'HR': (1, 99),   # Haryana: 01 to 99
    'RJ': (1, 53),   # Rajasthan: 01 to 53
    'WB': (1, 99),   # West Bengal: 01 to 99
    'MP': (1, 70),   # Madhya Pradesh: 01 to 70
    'BR': (1, 57),   # Bihar: 01 to 57
    'PB': (1, 91),   # Punjab: 01 to 91
    'KL': (1, 86),   # Kerala: 01 to 86
    'OD': (1, 35),   # Odisha: 01 to 35
    'JH': (1, 24),   # Jharkhand: 01 to 24
    'CG': (1, 30),   # Chhattisgarh: 01 to 30
    'UK': (1, 20),   # Uttarakhand: 01 to 20
    'HP': (1, 97),   # Himachal Pradesh: 01 to 97
    'GA': (1, 12),   # Goa: 01 to 12
    'JK': (1, 22),   # Jammu & Kashmir: 01 to 22
    'PY': (1, 5),    # Puducherry: 01 to 05
    'CH': (1, 4),    # Chandigarh: 01 to 04
    'AS': (1, 34),   # Assam: 01 to 34
    'TR': (1, 8),    # Tripura: 01 to 08
}

# OCR State Code Confusion Matrix: common letter splits/merges
STATE_OCR_CONFUSIONS = {
    'CH': 'MH',  # C+H is OCR split for M+H (MH)
    'NH': 'MH',  # N+H is OCR misread of M+H
    'MA': 'MH',
    'MR': 'MH',
    'DH': 'DL',
    'CK': 'JK',
    'NK': 'JK',
}


def correct_state_code(state: str, rto_str: str) -> str:
    """
    Validates state code against official MoRTH RTO district ranges and
    resolves OCR letter split confusions (e.g. CH02 -> MH02).
    """
    state = state.upper()
    try:
        dist = int(rto_str)
    except ValueError:
        dist = 0

    # If state is in confusion map and district number fits target state:
    if state in STATE_OCR_CONFUSIONS:
        target_state = STATE_OCR_CONFUSIONS[state]
        min_d, max_d = STATE_RTO_RANGES.get(target_state, (1, 99))
        if min_d <= dist <= max_d:
            return target_state

    return state


def fix_positional_characters(plate_str: str) -> str:
    """
    Position-aware character correction for Indian plates.
    Format: [State: 2 ALPHA] [District: 2 DIGIT] [Series: 1-3 ALPHA] [RegNum: 4 DIGIT]

    Handles HSRP 'IND' logo prefixes & MoRTH RTO district ranges automatically.
    """
    s = plate_str.upper().replace(' ', '').replace('-', '').replace('.', '')
    s = strip_hsrp_ind_prefix(s)

    if len(s) < 8 or len(s) > 10:
        return s

    chars = list(s)
    n = len(chars)

    # ── Positions 0-1: State code → MUST be letters ────────────────────
    for i in (0, 1):
        c = chars[i]
        if not c.isalpha():
            chars[i] = _TO_LETTER.get(c, c)

    # ── Positions 2-3: District code → MUST be digits ─────────────────
    for i in (2, 3):
        c = chars[i]
        if not c.isdigit():
            chars[i] = _TO_DIGIT.get(c, c)

    # ── Last 4 characters: Registration number → MUST be digits ────────
    for i in range(n - 4, n):
        c = chars[i]
        if not c.isdigit():
            chars[i] = _TO_DIGIT.get(c, c)

    # ── Middle section (positions 4 to n-5): Series → MUST be letters ──
    # MoRTH RTO Rule: Series letters DO NOT use 'O' or 'I' (to avoid 0/1 confusion).
    # 'O' / '0' in series is an OCR segmentation misread of wide letter 'W' or 'V'.
    _SERIES_MAP = {'O': 'W', '0': 'W', 'Q': 'W', 'I': 'J', '1': 'J'}
    for i in range(4, n - 4):
        c = chars[i]
        if c in _SERIES_MAP:
            chars[i] = _SERIES_MAP[c]
        elif not c.isalpha():
            chars[i] = _TO_LETTER.get(c, c)

    corrected = ''.join(chars)

    # ── Validate and fix state code using RTO confusion matrix & nearest-match ─
    raw_state = corrected[:2]
    rto_num = corrected[2:4]
    state = correct_state_code(raw_state, rto_num)

    if state not in INDIAN_STATES:
        fixed_state = _nearest_state_code(state)
        corrected = fixed_state + corrected[2:]
    else:
        corrected = state + corrected[2:]

    return corrected


def post_process(raw: str) -> str:

    """
    Full Indian plate post-processing:
    1. Clean non-alphanumeric chars & strip HSRP 'IND' emblem
    2. Apply positional character correction
    3. Validate state code
    4. Return corrected plate or None if invalid
    """
    if not raw:
        return None
    raw_clean = re.sub(r'[^A-Za-z0-9]', '', raw.upper())
    raw_clean = strip_hsrp_ind_prefix(raw_clean)

    if len(raw_clean) < 8 or len(raw_clean) > 10:
        return None

    # Accept Bharat Series
    if re.match(r"^\d{2}BH\d{4}[A-Z]{1,2}$", raw_clean):
        return raw_clean

    # Accept Temporary Registration plate
    if re.match(r"^T\d{4}[A-Z]{2}\d{3,5}[A-Z]?$", raw_clean):
        return raw_clean

    corrected = fix_positional_characters(raw_clean)

    # Accept if it matches Indian plate pattern and has valid state
    if corrected[:2] in INDIAN_STATES and corrected[-3:].isdigit() and 8 <= len(corrected) <= 10:
        return corrected

    # Try regex extraction on corrected
    matches = _INDIAN_EXTRACTOR.findall(corrected)
    valid = [m for m in matches if (m[:2] in INDIAN_STATES or m.startswith("T") or "BH" in m) and 8 <= len(m) <= 13]
    if valid:
        return valid[0]

    return None


# Regex patterns (used by extraction functions below)
_PLATE_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
_STRICT_INDIAN_PATTERN = re.compile(r"^([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{4})$")
_INDIAN_EXTRACTOR = re.compile(r"([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}|T[0-9]{4}[A-Z]{2}[0-9]{3,5}[A-Z]?|[0-9]{2}BH[0-9]{4}[A-Z]{1,2})")


def extract_all_indian_plates_from_string(raw_text: str) -> list:
    """
    Scans any raw OCR string and extracts ALL valid Indian plates found.
    Applies HSRP IND prefix stripping and positional correction before extraction.
    """
    if not raw_text:
        return []
    clean = re.sub(r'[^A-Za-z0-9]', '', raw_text.upper())
    clean = strip_hsrp_ind_prefix(clean)

    # 1. Primary: direct regex extraction after character correction
    corrected = fix_positional_characters(clean) if (8 <= len(clean) <= 10 and not clean.startswith('T')) else clean
    matches = _INDIAN_EXTRACTOR.findall(corrected)
    found_plates = [m for m in matches if (m[:2] in INDIAN_STATES or m.startswith("T") or "BH" in m) and 8 <= len(m) <= 13]
    if found_plates:
        return list(dict.fromkeys(found_plates))

    # 2. Sliding window search with correction (for concatenated multi-token strings)
    for start in range(len(clean)):
        for length in (10, 9, 8, 11, 12, 13):
            end = start + length
            if end > len(clean):
                continue
            candidate = clean[start:end]
            candidate = strip_hsrp_ind_prefix(candidate)
            if candidate[:2] not in INDIAN_STATES and _nearest_state_code(candidate[:2]) not in INDIAN_STATES:
                continue
            fixed = fix_positional_characters(candidate)
            sub_m = _INDIAN_EXTRACTOR.findall(fixed)
            valid_sub = [m for m in sub_m if m[:2] in INDIAN_STATES and 8 <= len(m) <= 10]
            for vp in valid_sub:
                if vp not in found_plates:
                    found_plates.append(vp)
            if not valid_sub:
                p_val = post_process(fixed)
                if p_val and p_val not in found_plates:
                    found_plates.append(p_val)

    return list(dict.fromkeys(found_plates))



def extract_indian_plate_from_string(raw_text: str) -> str:
    """Returns the first valid Indian plate found in raw_text, or None."""
    plates = extract_all_indian_plates_from_string(raw_text)
    return plates[0] if plates else None



def multi_pass_ocr_on_plate(img, max_passes=4):
    """
    Runs OCR on multiple preprocessed versions of a plate crop and votes.
    Pass 1: CLAHE Local Contrast Enhanced Grayscale (Fastest)
    Pass 2: Upscaled + Laplacian Unsharp Sharpened CLAHE
    Pass 3: Otsu Binary Threshold
    Pass 4: Inverted Otsu Binary
    """
    if img is None or img.size == 0:
        return None, 0.0

    # Ensure PyTorch uses single-thread mode to stay strictly within 512MB RAM
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass

    reader = get_ocr()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    # Resize large crops to max height 140px preserving aspect ratio for sharp OCR inference
    gh, gw = gray.shape[:2]
    aspect = gw / max(1, gh)
    if gh > 140 and (aspect >= 1.6 or gw <= 500):
        scale = 140.0 / gh
        gray = cv2.resize(gray, (int(gw * scale), 140), interpolation=cv2.INTER_AREA)
    elif gw > 1280:
        scale = 1280.0 / gw
        gray = cv2.resize(gray, (1280, int(gh * scale)), interpolation=cv2.INTER_AREA)

    # Apply CLAHE to dramatically boost character contrast against plate background
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray)

    versions = [cv2.cvtColor(gray_clahe, cv2.COLOR_GRAY2BGR)]

    if max_passes >= 2:
        # Pass 2: Sharpened
        up = cv2.resize(gray_clahe, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(up, (0, 0), 1.5)
        p2_gray = cv2.addWeighted(up, 1.5, blur, -0.5, 0)
        versions.append(cv2.cvtColor(p2_gray, cv2.COLOR_GRAY2BGR))

    if max_passes >= 3:
        _, otsu = cv2.threshold(gray_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        versions.append(cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR))

    if max_passes >= 4:
        _, otsu = cv2.threshold(gray_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        versions.append(cv2.cvtColor(cv2.bitwise_not(otsu), cv2.COLOR_GRAY2BGR))

    # Fast-path: lightweight Tesseract OCR (< 25MB RAM, ~30ms) if available
    try:
        import pytesseract
        for ver in versions:
            txt = pytesseract.image_to_string(ver, config='--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            p = extract_indian_plate_from_string(txt) or post_process(txt)
            if p and 8 <= len(p) <= 10:
                return p, 0.95
    except Exception:
        pass

    candidates = []

    if reader is not None:
        for pass_idx, ver in enumerate(versions[:max_passes]):
            try:
                results = reader.readtext(ver, detail=1, paragraph=False,
                                          contrast_ths=0.05, adjust_contrast=0.5,
                                          allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -")
            except Exception:
                results = None
            if not results:
                continue

            # Strategy A: Full text joined in horizontal reading order
            sorted_res = sorted(results, key=lambda x: x[0][0][0])
            combined   = " ".join([t for _, t, _ in sorted_res])
            avg_conf   = float(np.mean([c for _, _, c in sorted_res]))

            full_plate = extract_indian_plate_from_string(combined) or post_process(combined)
            if full_plate and 8 <= len(full_plate) <= 10:
                return full_plate, round(max(0.50, avg_conf), 3)

            # Strategy B: Pairwise consecutive tokens (e.g. "MH 02" + "CV 8284")
            if len(sorted_res) >= 2:
                for i in range(len(sorted_res) - 1):
                    pair_str = sorted_res[i][1] + " " + sorted_res[i+1][1]
                    pair_conf = (sorted_res[i][2] + sorted_res[i+1][2]) / 2.0
                    pair_plate = extract_indian_plate_from_string(pair_str) or post_process(pair_str)
                    if pair_plate and 8 <= len(pair_plate) <= 10:
                        candidates.append((pair_plate, max(0.25, float(pair_conf)), pass_idx))

            # Strategy C: Individual token only if it contains the full 8-10 char plate
            for (_, text, conf) in results:
                p = extract_indian_plate_from_string(text) or post_process(text)
                if p and 8 <= len(p) <= 10:
                    candidates.append((p, max(0.25, float(conf)), pass_idx))



    if not candidates:
        return None, 0.0

    plate_passes   = {}
    plate_best_conf = {}
    for plate, conf, pidx in candidates:
        plate_passes.setdefault(plate, set()).add(pidx)
        if conf > plate_best_conf.get(plate, 0.0):
            plate_best_conf[plate] = conf

    # Rank by: (1) Number of agreeing passes, (2) Full 9-10 char plate length, (3) Confidence
    ranked = sorted(plate_passes.keys(),
                    key=lambda p: (len(plate_passes[p]), 1 if len(p) >= 9 else 0, plate_best_conf[p]),
                    reverse=True)

    best = ranked[0]
    return best, round(plate_best_conf[best], 3)





def read_plate_text(crop_img):
    """
    Runs multi-pass OCR on a plate crop with adaptive optical restoration.
    """
    if crop_img is None or crop_img.size == 0:
        return None, 0.0, {}

    # 1. Assess Quality & Environment
    telemetry = quality.assess_image_quality(crop_img)
    # 2. Apply Condition-Specific Restoration (Night/Fog/Rain/Glare/Blur/Dust)
    restored  = enhancer.restore_image(crop_img, telemetry)

    plate, conf = multi_pass_ocr_on_plate(restored)
    return plate, conf, telemetry



# -----------------------------------------------------------------------
# Spatio-Temporal Sequence Recognizer & Multi-Frame Consensus Engine 2.0
# -----------------------------------------------------------------------
class SpatioTemporalSequenceFusion:
    """
    Spatio-Temporal Sequence Fusion 2.0:
    1. Multi-Frame Quality Buffering & Best Frame Ranking.
    2. Character-Wise Positional Sequence Alignment Matrix.
    3. Fuses characters weighted by (OCR_Conf) x (Sharpness) x (IQA_Quality_Score).
    4. Positional Indian RTO Syntactic Disambiguation (>95% Accuracy).
    """
    def __init__(self, buffer_size=8):
        self.buffer_size = buffer_size
        self.track_buffers = defaultdict(list)

    def add_frame_observation(self, track_id, plate_crop, ocr_text, ocr_conf, telemetry=None):
        if not ocr_text or len(ocr_text) < 6:
            return ocr_text, ocr_conf, {}

        if telemetry is None:
            telemetry = quality.assess_image_quality(plate_crop)

        # 1. Random Forest Machine Learning Frame Evaluation
        rf_eval = ml_selector.evaluate_frame_candidate(plate_crop, telemetry)
        rf_score = rf_eval.get("rf_quality_score", 0.75)
        is_acceptable = rf_eval.get("is_acceptable_for_ocr", True)

        metrics = telemetry.get("metrics", {})
        sharpness = metrics.get("sharpness", 0.5)

        # Composite frame weight driven by ML Random Forest + Optical Focus
        weight = float(ocr_conf * (0.30 + (0.30 * sharpness) + (0.40 * rf_score)))

        obs = {
            "text": ocr_text,
            "conf": round(float(ocr_conf), 3),
            "sharpness": round(float(sharpness), 3),
            "rf_quality_score": round(float(rf_score), 3),
            "quality_score": round(float(rf_score), 3),
            "rf_decision": rf_eval.get("decision", "ACCEPT_FOR_OCR"),
            "condition": telemetry.get("dominant_condition", "NORMAL"),
            "weight": round(float(weight), 3),
            "enhancements": telemetry.get("recommended_enhancements", [])
        }

        self.track_buffers[track_id].append(obs)
        if len(self.track_buffers[track_id]) > self.buffer_size:
            self.track_buffers[track_id].pop(0)

        history = self.track_buffers[track_id]

        # 2. Identify Best Frame via Random Forest Quality & Weight
        best_idx = max(range(len(history)), key=lambda i: (history[i]["rf_quality_score"], history[i]["weight"]))
        for idx, item in enumerate(history):
            item["is_best"] = (idx == best_idx)

        # 3. Positional Sequence Majority Voting across ML-approved frames
        lengths = [len(x["text"]) for x in history]
        target_len = Counter(lengths).most_common(1)[0][0]

        valid_candidates = [x for x in history if len(x["text"]) == target_len]
        if not valid_candidates:
            valid_candidates = history

        fused_chars = []
        for pos in range(target_len):
            char_votes = defaultdict(float)
            for item in valid_candidates:
                if pos < len(item["text"]):
                    char_votes[item["text"][pos]] += item["weight"]
            best_char = max(char_votes.items(), key=lambda x: x[1])[0]
            fused_chars.append(best_char)

        fused_plate = "".join(fused_chars)
        final_plate = fix_positional_characters(fused_plate)

        avg_base_conf = float(np.mean([x["conf"] for x in history]))
        sequence_bonus = min(0.14, 0.035 * len(history))
        consensus_conf = min(0.995, avg_base_conf + sequence_bonus)

        # Determine dominant environmental condition across buffer
        all_conditions = [x["condition"] for x in history]
        dominant_env = Counter(all_conditions).most_common(1)[0][0]

        # Quality Gate Assessment ("Don't OCR Yet" decision via RF)
        is_provisional = bool((not is_acceptable or rf_score < 0.42) and len(history) < 3)
        gate_status = "GATED_BUFFERING_OBSERVATION" if is_provisional else "CONFIRMED_CONSENSUS"

        voting_details = {
            "frames_analyzed": len(history),
            "best_frame_index": best_idx + 1,
            "scene_condition": telemetry.get("scene_condition", dominant_env),
            "environmental_condition": dominant_env,
            "frame_artifacts": telemetry.get("frame_artifacts", []),
            "quality_gate_status": gate_status,
            "is_provisional": is_provisional,
            "rf_evaluation": rf_eval,
            "rf_top_feature_importances": ml_selector.get_rf_feature_importances(),
            "frame_observations": history,
            "fused_consensus": final_plate,
            "confidence_boost": f"+{sequence_bonus*100:.1f}% (Temporal Consensus Gain)",
            "telemetry": telemetry
        }

        return final_plate, round(float(consensus_conf), 3), voting_details




_sequence_fusion = SpatioTemporalSequenceFusion(buffer_size=8)


# -----------------------------------------------------------------------
# Direct Full-Frame & Multi-Scale Zoom Scanner
# -----------------------------------------------------------------------
# Direct Full-Frame & Multi-Scale Zoom Scanner
# -----------------------------------------------------------------------
def scan_frame_for_plates(frame):
    """
    Direct OCR scan on frame using multi-pass CLAHE pipeline.
    Works for close-up plate photos, zoomed screenshots, and thumbnails.
    Strategy 1: Run multi_pass_ocr_on_plate on the full frame directly.
    Strategy 2: Run on a center-ROI crop (handles bordered/padded images).
    Strategy 3: Raw EasyOCR fallback with strict confidence filtering.
    """
    if frame is None or frame.size == 0:
        return []

    h, w = frame.shape[:2]
    telemetry = quality.assess_image_quality(frame, is_scene_frame=False)
    reader = get_ocr()

    detections = []
    found_plates_set = set()

    # ── Strategy 1: multi_pass_ocr directly on frame ─────────────
    plate1, conf1 = multi_pass_ocr_on_plate(frame, max_passes=2)
    if plate1 and plate1 not in found_plates_set:
        found_plates_set.add(plate1)
        res = _sequence_fusion.add_frame_observation(
            abs(hash(plate1[:4])) % 10000, frame, plate1, conf1, telemetry)
        p_color, p_cat = classify_plate_color_and_category(frame)
        detections.append({
            "plate": res[0], "confidence": res[1],
            "vehicle_type": "Car", "bbox": (0, 0, w, h),
            "plate_bbox": (0, 0, w, h), "voting_details": res[2], "telemetry": telemetry,
            "plate_color": p_color, "category": p_cat, "violation": "NONE"
        })
        return detections

    # ── Strategy 2: Bumper Plate Region Localization (only if Strategy 1 found nothing) ──
    if not detections:
        try:
            plate_crop = find_plate_region_in_crop(frame)
            if plate_crop is not None and plate_crop.size > 0:
                p_reg, c_reg = multi_pass_ocr_on_plate(plate_crop, max_passes=2)
                if p_reg and p_reg not in found_plates_set:
                    found_plates_set.add(p_reg)
                    res_reg = _sequence_fusion.add_frame_observation(
                        abs(hash(p_reg[:4])) % 10000, plate_crop, p_reg, c_reg, telemetry)
                    p_color, p_cat = classify_plate_color_and_category(plate_crop)
                    detections.append({
                        "plate": res_reg[0], "confidence": res_reg[1],
                        "vehicle_type": "Car", "bbox": (0, 0, w, h),
                        "plate_bbox": (0, 0, w, h), "voting_details": res_reg[2], "telemetry": telemetry,
                        "plate_color": p_color, "category": p_cat, "violation": "NONE"
                    })
        except Exception:
            pass

    # ── Strategy 3: Center-ROI crop (only if Strategies 1 & 2 found nothing) ────
    if not detections:
        cy1, cy2 = int(h * 0.20), int(h * 0.85)
        cx1, cx2 = int(w * 0.05), int(w * 0.95)
        center_crop = frame[cy1:cy2, cx1:cx2]
        if center_crop.size > 0:
            plate2, conf2 = multi_pass_ocr_on_plate(center_crop, max_passes=2)
            if plate2 and plate2 not in found_plates_set:
                found_plates_set.add(plate2)
                res2 = _sequence_fusion.add_frame_observation(
                    abs(hash(plate2[:4])) % 10000, center_crop, plate2, conf2, telemetry)
                p_color, p_cat = classify_plate_color_and_category(center_crop)
                detections.append({
                    "plate": res2[0], "confidence": res2[1],
                    "vehicle_type": "Car", "bbox": (cx1, cy1, cx2, cy2),
                    "plate_bbox": (cx1, cy1, cx2, cy2), "voting_details": res2[2], "telemetry": telemetry,
                    "plate_color": p_color, "category": p_cat, "violation": "NONE"
                })

    # ── Strategy 4: Raw OCR fallback (long plates in complex scenes) ──
    if not detections and reader is not None:
        proc = frame if w <= 640 else cv2.resize(frame, (640, int(h * 640.0 / w)))
        restored = enhancer.restore_image(proc, telemetry)
        try:
            raw_results = reader.readtext(restored, detail=1, paragraph=False,
                                          contrast_ths=0.05, adjust_contrast=0.5,
                                          allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -")
        except Exception:
            raw_results = None
        if raw_results:
            scale_x = w / float(proc.shape[1])
            scale_y = h / float(proc.shape[0])

            # 1. Direct single-token plate match (e.g. TN87C5106 or T0322UP42298 in one token)
            for box, txt, c in raw_results:
                clean_t = re.sub(r'[^A-Za-z0-9]', '', txt.upper())
                p = extract_indian_plate_from_string(clean_t) or post_process(clean_t)
                if p and p not in found_plates_set:
                    found_plates_set.add(p)
                    res3 = _sequence_fusion.add_frame_observation(
                        abs(hash(p[:4])) % 10000, frame, p, float(c), telemetry)
                    p_color, p_cat = classify_plate_color_and_category(frame)
                    bx1 = max(0, int(min(pt[0] for pt in box) * scale_x))
                    by1 = max(0, int(min(pt[1] for pt in box) * scale_y))
                    bx2 = min(w, int(max(pt[0] for pt in box) * scale_x))
                    by2 = min(h, int(max(pt[1] for pt in box) * scale_y))
                    detections.append({
                        "plate": res3[0], "confidence": res3[1],
                        "vehicle_type": "Car", "bbox": (0, 0, w, h),
                        "plate_bbox": (bx1, by1, bx2, by2), "voting_details": res3[2], "telemetry": telemetry,
                        "plate_color": p_color, "category": p_cat, "violation": "NONE"
                    })
                    return detections

            # 2. Multi-token combination fallback (split plate e.g. "TN 87" + "C 5106")
            plate_tokens = [(box, txt, c) for box, txt, c in raw_results
                            if c >= 0.35 and 2 <= len(txt.replace(' ', '')) <= 8]
            if len(plate_tokens) >= 2:
                sorted_res = sorted(plate_tokens, key=lambda x: x[0][0][0])
                combined = " ".join([t for _, t, _ in sorted_res])
                avg_conf = float(sum(c for _, _, c in sorted_res) / len(sorted_res))
                full_plate = extract_indian_plate_from_string(combined) or post_process(combined)
                if full_plate and full_plate not in found_plates_set:
                    found_plates_set.add(full_plate)
                    res3 = _sequence_fusion.add_frame_observation(
                        abs(hash(full_plate[:4])) % 10000, frame, full_plate, avg_conf, telemetry)
                    p_color, p_cat = classify_plate_color_and_category(frame)
                    all_pts = [pt for b, _, _ in sorted_res for pt in b]
                    bx1 = max(0, int(min(pt[0] for pt in all_pts) * scale_x))
                    by1 = max(0, int(min(pt[1] for pt in all_pts) * scale_y))
                    bx2 = min(w, int(max(pt[0] for pt in all_pts) * scale_x))
                    by2 = min(h, int(max(pt[1] for pt in all_pts) * scale_y))
                    detections.append({
                        "plate": res3[0], "confidence": res3[1],
                        "vehicle_type": "Car", "bbox": (0, 0, w, h),
                        "plate_bbox": (bx1, by1, bx2, by2), "voting_details": res3[2], "telemetry": telemetry,
                        "plate_color": p_color, "category": p_cat, "violation": "NONE"
                    })

    return detections




# -----------------------------------------------------------------------
# Plate Region Localizer  (runs BEFORE OCR to narrow input to plate only)
# -----------------------------------------------------------------------
def find_plate_region_in_crop(veh_crop, cls=2):
    """
    Finds the license plate sub-region inside a vehicle crop.
    Strategy 1 – Edge + Contour with aspect-ratio filter (2:1 – 6.5:1).
    Strategy 2 – HSV color: white (private) or yellow (commercial) plates.

    Restricted strictly to the lower bumper region so side advertisements,
    doors, windows, and decals on buses/trucks are completely ignored.
    """
    if veh_crop is None or veh_crop.size == 0:
        return None

    h, w = veh_crop.shape[:2]
    gray = cv2.cvtColor(veh_crop, cv2.COLOR_BGR2GRAY)

    # For buses (5) and trucks (7), plates are exclusively on the bottom bumper (lowest 30%)
    min_cy = 0.65 if cls in (5, 7) else 0.35
    max_cy = 0.98

    all_cands = []

    # ── Strategy 1: Edge + Contour ──────────────────────────────────────
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 30, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if ch < 8 or cw < 30:
            continue
        aspect = cw / max(ch, 1)
        area   = cw * ch
        cx     = (x + cw / 2.0) / float(w)
        cy     = (y + ch / 2.0) / float(h)
        # Indian plates: aspect 2.2 to 6.5, strictly in bumper zone, horizontally centered
        if 2.0 <= aspect <= 6.5 and 400 < area < (h * w * 0.30) and min_cy <= cy <= max_cy:
            aspect_score = 1.0 / (1.0 + abs(aspect - 4.0))
            pos_score    = 1.0 - abs(cx - 0.5)
            score        = (aspect_score * 0.5) + (pos_score * 0.3) + (min(1.0, area / 2000.0) * 0.2)
            all_cands.append((x, y, cw, ch, score))

    # ── Strategy 2: HSV Color (white / yellow plates) ───────────────────
    hsv = cv2.cvtColor(veh_crop, cv2.COLOR_BGR2HSV)
    white_mask  = cv2.inRange(hsv, np.array([0,   0, 175]), np.array([180,  55, 255]))
    yellow_mask = cv2.inRange(hsv, np.array([16,  70,  90]), np.array([40, 255, 255]))
    combined    = cv2.bitwise_or(white_mask, yellow_mask)
    kc = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 6))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kc)
    contours2, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours2:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if ch < 10 or cw < 40:
            continue
        aspect = cw / max(ch, 1)
        area   = cw * ch
        cx     = (x + cw / 2.0) / float(w)
        cy     = (y + ch / 2.0) / float(h)
        if 2.0 <= aspect <= 6.5 and area > 500 and min_cy <= cy <= max_cy:
            aspect_score = 1.0 / (1.0 + abs(aspect - 4.0))
            pos_score    = 1.0 - abs(cx - 0.5)
            score        = (aspect_score * 0.55) + (pos_score * 0.30) + 0.20
            all_cands.append((x, y, cw, ch, score))

    if all_cands:
        all_cands.sort(key=lambda c: c[4], reverse=True)
        bx, by, bw, bh, _ = all_cands[0]
        pad_x = max(12, int(bw * 0.18))
        pad_y = max(8,  int(bh * 0.20))
        cx1 = max(0, bx - pad_x);  cy1 = max(0, by - pad_y)
        cx2 = min(w, bx + bw + pad_x); cy2 = min(h, by + bh + pad_y)
        plate_crop = veh_crop[cy1:cy2, cx1:cx2]
        if plate_crop.size > 0 and plate_crop.shape[1] > 35:
            return plate_crop

    # Fallback to lower bumper/trunk zone for cars/motorbikes
    if cls not in (5, 7):
        bottom_y = int(h * 0.38)
        bottom_crop = veh_crop[bottom_y:, :]
        if bottom_crop.size > 0 and bottom_crop.shape[1] > 40:
            return bottom_crop

    return None




# -----------------------------------------------------------------------
# Frame ANPR Detection Pipeline (YOLO detect vehicle → OCR → plate)
# -----------------------------------------------------------------------
def detect_plates_in_frame(frame, yolo_results=None, pixels_per_meter=50, fast_mode=False):
    """
    Simple 3-step ANPR: YOLO detects vehicle → CLAHE multi-pass OCR → extract plate.
    Works at any angle, zoom level, distance, or image quality.
    """
    detections = []
    vehicle_classes = {2: "Car", 3: "Motorbike", 5: "Bus", 7: "Truck"}
    ocr_passes = 2 if fast_mode else 4

    if yolo_results and yolo_results[0].boxes is not None and len(yolo_results[0].boxes) > 0:
        boxes = yolo_results[0].boxes
        seen_tracks = set()

        for box in boxes:
            cls = int(box.cls)
            if cls not in vehicle_classes:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            track_id = int(box.id[0]) if box.id is not None else 0

            # Skip duplicate tracks in same frame
            if track_id > 0 and track_id in seen_tracks:
                continue
            seen_tracks.add(track_id)

            # Skip truly tiny specks (distant background noise)
            bw, bh = x2 - x1, y2 - y1
            if bw < 60 or bh < 50:
                continue

            # ── Step 1: Crop the vehicle bounding box ─────────────────
            vx1, vx2 = max(0, x1), min(frame.shape[1], x2)
            vy1, vy2 = max(0, y1), min(frame.shape[0], y2)
            veh_crop = frame[vy1:vy2, vx1:vx2]
            if veh_crop.size == 0:
                continue

            # Upscale tiny crops so OCR can read small plates
            vh, vw = veh_crop.shape[:2]
            if vw < 280 or vh < 120:
                scale = max(280.0 / max(1, vw), 120.0 / max(1, vh))
                veh_crop = cv2.resize(veh_crop, None, fx=scale, fy=scale,
                                      interpolation=cv2.INTER_LANCZOS4)

            # ── Step 2: Try plate localization first (fast path) ───────
            plate_region = find_plate_region_in_crop(veh_crop, cls=cls)

            # Edge-Truncated Vehicle Check:
            # A vehicle is only a "narrow edge sliver" if it touches an image border AND occupies only a narrow strip
            # (e.g. half-van entering/exiting at edge). If the vehicle spans substantial width/height, it is a primary vehicle!
            is_narrow_edge_sliver = (
                (x1 <= 5 and bw < frame.shape[1] * 0.35) or
                (x2 >= frame.shape[1] - 5 and bw < frame.shape[1] * 0.35) or
                (y1 <= 5 and bh < frame.shape[0] * 0.25) or
                (y2 >= frame.shape[0] - 5 and bh < frame.shape[0] * 0.25)
            )

            # If it's a genuine narrow edge sliver with no plate region, skip OCR to avoid hallucinations
            if is_narrow_edge_sliver and (plate_region is None or plate_region.size == 0):
                continue

            # ── Step 3: Multi-pass CLAHE OCR ──────────────────────────
            # Try on localized plate region first, then fallback to full crop
            plate_found, avg_conf = None, 0.0

            if plate_region is not None and plate_region.size > 0:
                telemetry = quality.assess_image_quality(plate_region, is_scene_frame=False)
                restored  = enhancer.restore_image(plate_region, telemetry)
                plate_found, avg_conf = multi_pass_ocr_on_plate(restored, max_passes=ocr_passes)

            # Fallback: OCR on full vehicle crop (for vehicles that aren't narrow edge slivers)
            if not plate_found and not is_narrow_edge_sliver:
                telemetry = quality.assess_image_quality(veh_crop, is_scene_frame=False)
                restored  = enhancer.restore_image(veh_crop, telemetry)
                plate_found, avg_conf = multi_pass_ocr_on_plate(restored, max_passes=ocr_passes)

            # If plate is missing or covered on a prominent vehicle:
            if not plate_found or avg_conf < 0.45:
                if not is_narrow_edge_sliver and (bw * bh) > 10000:
                    t_id = track_id if track_id > 0 else (abs(hash(str(vx1))) % 10000)
                    v_type_name = vehicle_classes.get(cls, "Car")
                    v_profile = vehicle_profiler.extract_vehicle_profile(veh_crop, vehicle_type=v_type_name)
                    detections.append({
                        "plate": "⚠️ UNREADABLE / NO PLATE",
                        "track_id": t_id,
                        "confidence": 0.0,
                        "vehicle_type": v_type_name,
                        "bbox": (vx1, vy1, vx2, vy2),
                        "plate_bbox": (vx1, vy1, vx2, vy2),
                        "voting_details": {},
                        "telemetry": {},
                        "violation": "MISSING_OR_COVERED_PLATE",
                        "plate_color": "GREY",
                        "category": "Violation / Missing Plate",
                        "vehicle_profile": v_profile
                    })
                continue



            # ── Step 4: Sequence fusion & plate color classification ───────
            t_id = track_id if track_id > 0 else (abs(hash(plate_found[:4])) % 10000)
            crop_for_fusion = plate_region if (plate_region is not None and plate_region.size > 0) else veh_crop
            res = _sequence_fusion.add_frame_observation(t_id, crop_for_fusion, plate_found, avg_conf, telemetry)

            p_color, p_cat = classify_plate_color_and_category(crop_for_fusion)

            detections.append({
                "plate":          res[0],
                "track_id":       t_id,
                "confidence":     res[1],
                "vehicle_type":   vehicle_classes.get(cls, "Car"),
                "bbox":           (vx1, vy1, vx2, vy2),
                "plate_bbox":     (vx1, vy1, vx2, vy2),
                "voting_details": res[2],
                "telemetry":      telemetry,
                "violation":      "NONE",
                "plate_color":    p_color,
                "category":       p_cat
            })


    # Final fallback: run scan_frame_for_plates ONLY if YOLO found zero vehicles at all
    # (e.g. standalone cropped plate photo). Never run fallback if vehicles were detected
    # to avoid tagging background street signs onto vehicles without visible plates.
    if not detections and (not yolo_results or not yolo_results[0].boxes or len(yolo_results[0].boxes) == 0):
        detections = scan_frame_for_plates(frame)

    return detections



def annotate_frame(frame, plate_detections, last_sync_plate=""):
    """
    Renders a high-tech Smart City CCTV HUD overlay on the live camera stream:
    - Top CCTV Status Banner with FPS, Engine & Environmental Telemetry
    - Vehicle Bounding Boxes with Class & Track IDs
    - License Plate Bounding Boxes with Indian RTO Validation Badges
    - Bottom Sync Status Banner
    """
    h, w = frame.shape[:2]

    # Determine frame environment
    env_condition = "NORMAL"
    if plate_detections:
        env_condition = plate_detections[-1].get("telemetry", {}).get("dominant_condition", "NORMAL")

    # 1. Top CCTV HUD Header Bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 36), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    env_icons = {
        "NIGHT": "[ NIGHT/LOW-LIGHT ADAPTIVE ]",
        "RAIN": "[ RAIN STREAK FILTER ACTIVE ]",
        "FOG": "[ DCP DEHAZING ACTIVE ]",
        "DUST_HAZE": "[ SMOG / DUST COMPENSATION ]",
        "GLARE": "[ SPECULAR GLARE SUPPRESSION ]",
        "NORMAL": "[ AMBIENT CLEAR LIGHTING ]"
    }
    env_tag = env_icons.get(env_condition, "[ AI MULTI-FRAME FUSION ]")

    cv2.putText(frame, f"CCTV EDGE ANPR NODE | {env_tag}", (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (56, 189, 248), 2)
    cv2.circle(frame, (w - 24, 18), 6, (0, 0, 255), -1)
    cv2.putText(frame, "LIVE", (w - 65, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)

    # 2. Draw vehicle & plate detections
    for d in plate_detections:
        x1, y1, x2, y2 = d["bbox"]
        px1, py1, px2, py2 = d["plate_bbox"]
        is_plate_less = d.get("violation") == "MISSING_OR_COVERED_PLATE" or "NO PLATE" in str(d.get("plate", ""))

        # Vehicle Box (Neon Green for standard, Crimson/Magenta for Ghost)
        box_col = (180, 50, 230) if is_plate_less else (0, 255, 100)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_col, 2)
        v_tag = f"{d.get('vehicle_type', 'Vehicle')}" + (" [NO PLATE]" if is_plate_less else "")
        tag_w = 140 if is_plate_less else 80
        cv2.rectangle(frame, (x1, max(36, y1 - 24)), (x1 + tag_w, y1), box_col, -1)
        cv2.putText(frame, v_tag, (x1 + 4, max(52, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2)

        # Plate Crop Box
        if not is_plate_less:
            cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 220, 255), 2)

        # High-Contrast Plate Badge
        p_label = f" ⚠️ {d['plate']} " if is_plate_less else f" {d['plate']} ({d['confidence'] * 100:.0f}%) "
        (tw, th), _ = cv2.getTextSize(p_label, cv2.FONT_HERSHEY_DUPLEX, 0.65, 2)
        badge_y = min(y2 - 10, y1 + 35) if is_plate_less else max(38, py1 - 8)
        badge_border = (180, 50, 230) if is_plate_less else (0, 220, 255)
        badge_text_col = (230, 100, 240) if is_plate_less else (254, 240, 138)
        cv2.rectangle(frame, (px1, badge_y - th - 6), (px1 + tw + 6, badge_y + 4), (15, 23, 42), -1)
        cv2.rectangle(frame, (px1, badge_y - th - 6), (px1 + tw + 6, badge_y + 4), badge_border, 1)
        cv2.putText(frame, p_label, (px1 + 2, badge_y - 2),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, badge_text_col, 2)

    # 3. Bottom Sync Confirmation Bar
    if plate_detections:
        latest = plate_detections[-1]["plate"]
        bar_y = h - 28
        cv2.rectangle(frame, (0, bar_y), (w, h), (15, 23, 42), -1)
        sync_txt = f"SYNCED TO CENTRAL SERVER -> PLATE: {latest} [CAM_LIVE]"
        cv2.putText(frame, sync_txt, (14, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (34, 197, 94), 2)

    return frame
