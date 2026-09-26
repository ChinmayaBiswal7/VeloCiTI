"""
vehicle_intel.py - Vehicle attribute recognition for the webcam image/video analysis modes.

CLIP zero-shot recognition of body type, make/model, damage, clothing and helmets. Every field uses a
conservative confidence threshold: below it the value is returned blank instead of guessed.
Also holds the Indian plate-format validator/decoder and the (simulated) registry lookup.
"""

import base64
import os
import re
import threading

import cv2

CLIP_MODEL_ID = os.environ.get("CLIP_MODEL_ID", "openai/clip-vit-large-patch14")

# Minimum top-1 probability (and margin over runner-up) before a value is reported.
MIN_BODY_PROB = 0.40
MIN_MODEL_PROB = 0.45
MIN_MODEL_MARGIN = 0.15
MIN_DAMAGE_PROB = 0.60
MIN_CLOTHING_PROB = 0.45
MIN_HELMET_PROB = 0.60
MIN_PERSON_SIZE = (32, 40)  # (width, height) in pixels

BODY_TYPES = [
    ("Hatchback", "a hatchback car"),
    ("Sedan", "a sedan car"),
    ("SUV", "an SUV"),
    ("MUV / Minivan", "a minivan or MPV"),
    ("Pickup", "a pickup truck"),
    ("Auto-rickshaw", "an auto-rickshaw three-wheeler"),
    ("Ambulance", "an ambulance"),
    ("Police vehicle", "a police car"),
    ("Fire truck", "a fire engine"),
    ("Bus", "a bus"),
    ("Truck", "a cargo truck or lorry"),
    ("Van", "a van"),
    ("Motorcycle", "a motorcycle"),
    ("Scooter", "a scooter"),
]
EMERGENCY_BODIES = {"Ambulance", "Police vehicle", "Fire truck"}
REFINED_TYPES = {"Auto-rickshaw": "Auto-rickshaw", "Ambulance": "Ambulance",
                 "Police vehicle": "Police vehicle", "Fire truck": "Fire truck"}

_CARS = {
    "Maruti Suzuki": ["Alto", "WagonR", "Swift", "Dzire", "Baleno", "Brezza", "Ertiga", "Celerio",
                      "S-Presso", "Eeco", "Ciaz", "Fronx", "Grand Vitara", "XL6", "Ignis"],
    "Hyundai": ["Grand i10 Nios", "i20", "Creta", "Venue", "Verna", "Aura", "Alcazar", "Santro", "Xcent"],
    "Tata": ["Tiago", "Tigor", "Altroz", "Nexon", "Punch", "Harrier", "Safari", "Indica"],
    "Mahindra": ["Scorpio", "Scorpio-N", "XUV700", "XUV300", "Thar", "Bolero", "Marazzo", "KUV100"],
    "Toyota": ["Innova Crysta", "Fortuner", "Glanza", "Urban Cruiser Hyryder", "Etios"],
    "Honda": ["City", "Amaze", "Jazz", "WR-V", "Elevate"],
    "Kia": ["Seltos", "Sonet", "Carens"],
    "Renault": ["Kwid", "Triber", "Duster", "Kiger"],
    "Nissan": ["Magnite"],
    "Skoda": ["Slavia", "Kushaq", "Rapid"],
    "Volkswagen": ["Polo", "Virtus", "Taigun", "Vento"],
    "MG": ["Hector", "Astor", "ZS EV"],
    "Ford": ["EcoSport", "Figo", "Endeavour"],
    "Jeep": ["Compass"],
    "BMW": ["3 Series"],
    "Mercedes-Benz": ["C-Class"],
    "Audi": ["A4"],
}
_TWO_WHEELERS = {
    "Hero": ["Splendor", "HF Deluxe", "Passion"],
    "Honda": ["Activa", "Shine", "Unicorn"],
    "Bajaj": ["Pulsar", "Platina", "Avenger"],
    "Royal Enfield": ["Classic 350", "Bullet", "Himalayan"],
    "TVS": ["Apache", "Jupiter", "Star City"],
    "Yamaha": ["R15", "FZ", "Fascino"],
    "Suzuki": ["Access", "Gixxer"],
    "KTM": ["Duke"],
}
_HEAVY = {
    "Tata": ["truck", "bus", "Ace mini truck"],
    "Ashok Leyland": ["truck", "bus"],
    "Eicher": ["truck", "bus"],
    "BharatBenz": ["truck"],
    "Mahindra": ["pickup truck", "Bolero Pickup"],
}


def _flatten(table):
    return [(f"{make} {model}", f"a {make} {model}") for make, models in table.items() for model in models]


MODEL_SETS = {"cars": _flatten(_CARS), "bikes": _flatten(_TWO_WHEELERS), "heavy": _flatten(_HEAVY)}

DAMAGE_LABELS = [
    ("Dented body panel", "a car with a dented, damaged body panel"),
    ("Broken bumper", "a car with a broken or hanging bumper"),
    ("Cracked windshield", "a car with a cracked windshield"),
    ("No visible damage", "an undamaged clean car"),
]
CLOTHING_LABELS = [
    ("Formal", "a person wearing formal clothes, a shirt with trousers or a suit"),
    ("Casual", "a person wearing casual clothes, a t-shirt or hoodie with jeans"),
    ("Traditional", "a person wearing traditional Indian clothes, a kurta or dhoti"),
    ("Saree / Salwar", "a woman wearing a saree or salwar kameez"),
    ("Uniform", "a person wearing a uniform"),
    ("Sportswear", "a person wearing sportswear or a tracksuit"),
]
HELMET_LABELS = [
    ("Helmet", "a motorcycle rider wearing a helmet"),
    ("No helmet", "a motorcycle rider with a bare head and no helmet"),
]
_TEMPLATES = ["a photo of {}.", "a cctv camera image of {}.", "a blurry low resolution photo of {}."]
_LABEL_SETS = {"body": BODY_TYPES, "damage": DAMAGE_LABELS, "clothing": CLOTHING_LABELS,
               "helmet": HELMET_LABELS, **{f"model_{k}": v for k, v in MODEL_SETS.items()}}

_clip = {"tried": False, "model": None, "proc": None, "torch": None}
_clip_lock = threading.Lock()
_text_cache = {}


def _load_clip():
    with _clip_lock:
        if _clip["tried"]:
            return _clip["model"] is not None
        _clip["tried"] = True
        try:
            import torch
            # CLIP ViT-Large (430M params) takes 10+ minutes on CPU and freezes everything.
            # Only enable if CUDA GPU is available or explicitly enabled via ENABLE_CPU_CLIP=1.
            if not torch.cuda.is_available() and os.environ.get("ENABLE_CPU_CLIP", "0") != "1":
                print("[Vehicle Intel] Running in ultra-fast mode (CPU CLIP bypassed for instant <1s response).")
                return False
            from transformers import CLIPModel, CLIPProcessor
            _clip["model"] = CLIPModel.from_pretrained(CLIP_MODEL_ID, local_files_only=True).eval()
            _clip["proc"] = CLIPProcessor.from_pretrained(CLIP_MODEL_ID, local_files_only=True)
            _clip["torch"] = torch
            print(f"[Vehicle Intel] CLIP loaded on GPU: {CLIP_MODEL_ID}")
        except Exception as e:
            print(f"[Vehicle Intel] CLIP unavailable ({e}); attribute fields will be blank.")
    return _clip["model"] is not None


def clip_available():
    return _load_clip()


def _as_tensor(x):
    return x if hasattr(x, "shape") else x.pooler_output


def _text_features(key):
    if key not in _text_cache:
        torch, model, proc = _clip["torch"], _clip["model"], _clip["proc"]
        rows = []
        with torch.no_grad():
            for _, subject in _LABEL_SETS[key]:
                tok = proc(text=[t.format(subject) for t in _TEMPLATES], return_tensors="pt", padding=True)
                f = _as_tensor(model.get_text_features(**tok))
                f = f / f.norm(dim=-1, keepdim=True)
                m = f.mean(dim=0)
                rows.append(m / m.norm())
        _text_cache[key] = torch.stack(rows)
    return _text_cache[key]


def _embed(crops_bgr):
    from PIL import Image
    torch, model, proc = _clip["torch"], _clip["model"], _clip["proc"]
    torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
    images = [Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB)) for c in crops_bgr]
    with torch.no_grad():
        f = _as_tensor(model.get_image_features(**proc(images=images, return_tensors="pt")))
    return f / f.norm(dim=-1, keepdim=True)


def _classify(emb, key):
    """Returns [(label, probability)] sorted best-first for one image embedding."""
    model = _clip["model"]
    with _clip["torch"].no_grad():
        logits = model.logit_scale.exp() * (emb @ _text_features(key).T)
        probs = logits.softmax(dim=-1)[0].cpu().numpy()
    labels = [name for name, _ in _LABEL_SETS[key]]
    return sorted(zip(labels, probs.tolist()), key=lambda x: x[1], reverse=True)


def vehicle_attributes(crop_bgr, cls_name):
    """Body type, emergency flag, make/model and damage for one vehicle crop. Blank when unsure."""
    out = {"available": False, "body_type": "", "body_confidence": 0.0, "refined_type": "",
           "is_emergency": False, "make_model": {"label": "", "confidence": 0.0, "candidates": []},
           "damage": None}
    if crop_bgr is None or crop_bgr.size == 0 or not _load_clip():
        return out
    emb = _embed([crop_bgr])
    out["available"] = True

    top_body, top_p = _classify(emb, "body")[0]
    if top_p >= MIN_BODY_PROB:
        out["body_type"], out["body_confidence"] = top_body, round(top_p, 3)
        out["refined_type"] = REFINED_TYPES.get(top_body, "") if top_p >= 0.5 else ""
        out["is_emergency"] = top_body in EMERGENCY_BODIES and top_p >= 0.45

    if cls_name == "Motorbike" or top_body in ("Motorcycle", "Scooter"):
        set_key = "model_bikes"
    elif cls_name in ("Bus", "Truck") or top_body in ("Bus", "Truck", "Pickup"):
        set_key = "model_heavy"
    elif top_body in ("Auto-rickshaw", "Ambulance", "Police vehicle", "Fire truck"):
        set_key = None
    else:
        set_key = "model_cars"
    if set_key:
        ranked = _classify(emb, set_key)
        (l1, p1), (_, p2) = ranked[0], ranked[1]
        out["make_model"]["candidates"] = [{"label": l, "confidence": round(p, 3)} for l, p in ranked[:3]]
        if p1 >= MIN_MODEL_PROB and (p1 - p2) >= MIN_MODEL_MARGIN:
            out["make_model"].update(label=l1, confidence=round(p1, 3))

    if set_key in ("model_cars", "model_heavy") and cls_name != "Motorbike":
        label, p = _classify(emb, "damage")[0]
        if label != "No visible damage" and p >= MIN_DAMAGE_PROB:
            out["damage"] = {"label": label, "confidence": round(p, 3)}
    return out


def _upper_body_color(person_bgr):
    import vehicle_profiler
    h = person_bgr.shape[0]
    torso = person_bgr[int(h * 0.2):int(h * 0.6), :]
    if torso.size == 0:
        return ""
    name, _ = vehicle_profiler.classify_dominant_color(cv2.cvtColor(torso, cv2.COLOR_BGR2HSV))
    return name.replace("_", " ").title()


def person_attributes(person_crops, is_rider):
    """Clothing style, upper-body colour and helmet for each person crop. Blank when unsure."""
    results = [{"clothing_style": "", "clothing_confidence": 0.0, "upper_color": "", "helmet": ""}
               for _ in person_crops]
    usable = [i for i, c in enumerate(person_crops)
              if c is not None and c.shape[1] >= MIN_PERSON_SIZE[0] and c.shape[0] >= MIN_PERSON_SIZE[1]]
    if not usable:
        return results
    for i in usable:
        results[i]["upper_color"] = _upper_body_color(person_crops[i])
    if not _load_clip():
        return results
    embs = _embed([person_crops[i] for i in usable])
    for row, i in enumerate(usable):
        label, p = _classify(embs[row:row + 1], "clothing")[0]
        if p >= MIN_CLOTHING_PROB:
            results[i]["clothing_style"], results[i]["clothing_confidence"] = label, round(p, 3)
        if is_rider:
            hl, hp = _classify(embs[row:row + 1], "helmet")[0]
            if hp >= MIN_HELMET_PROB:
                results[i]["helmet"] = hl
    return results


_STD_PLATE = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$")
_BH_PLATE = re.compile(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$")
_TEMP_PLATE = re.compile(r"^(T[RC]?\d{4})([A-Z]{2})(\d{1,5})([A-Z0-9]{0,2})$")


def clean_plate(text):
    if not text:
        return ""
    try:
        import anpr
        t = anpr.strip_hsrp_ind_prefix(text)
        t = anpr.fix_positional_characters(t)
    except Exception:
        t = text
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


def plate_format_valid(text):
    """True for a MoRTH standard plate with a real state code, a BH-series plate, or temporary/dealer plate."""
    import rto
    p = clean_plate(text)
    if len(p) < 6:
        return False
    m = _STD_PLATE.match(p)
    if m:
        return m.group(1) in rto.STATE_NAMES
    if _BH_PLATE.match(p):
        return True
    m_temp = _TEMP_PLATE.match(p)
    if m_temp:
        return m_temp.group(2) in rto.STATE_NAMES or m_temp.group(2) in ("UP", "DL", "MH", "KA", "TN", "TS", "OD", "HR", "GJ", "RJ", "WB", "MP", "PB", "BR", "KL")
    return p[:2] in rto.STATE_NAMES and any(c.isdigit() for c in p[2:])


def decode_plate(text):
    """Real decoding of the plate structure (state, RTO office, series). No owner data."""
    import rto
    p = clean_plate(text)
    m = _STD_PLATE.match(p)
    if m:
        code = m.group(1) + m.group(2)
        office, state = rto.RTO_DISTRICTS.get(code, ("", rto.STATE_NAMES.get(m.group(1), "")))
        return {"format": "Standard", "state_code": m.group(1), "state": state, "rto_code": code,
                "rto_office": office, "series": m.group(3), "number": m.group(4)}
    m = _BH_PLATE.match(p)
    if m:
        return {"format": "BH series", "registration_year": "20" + m.group(1),
                "number": m.group(2), "series": m.group(3)}
    m_temp = _TEMP_PLATE.match(p)
    if m_temp:
        state_code = m_temp.group(2)
        state_name = rto.STATE_NAMES.get(state_code, state_code)
        date_code = m_temp.group(1)
        month = date_code[1:3] if len(date_code) >= 3 else ""
        year = "20" + date_code[3:5] if len(date_code) >= 5 else ""
        issued_date = f"{month}/{year}" if month and year else date_code
        return {
            "format": "Temporary Registration (MoRTH CMVR)",
            "state_code": state_code,
            "state": state_name,
            "series": f"{m_temp.group(1)} {state_code}",
            "number": m_temp.group(3) + (m_temp.group(4) or ""),
            "issued_period": issued_date
        }
    return None


def lookup_registry(plate):
    """Registry record for a plate. No live Vahan/Parivahan API is connected, so it is simulated."""
    import rto
    return {
        "data_source": "SIMULATED_DEMO",
        "notice": "Simulated demo record generated from the plate text. No live Vahan/Parivahan API is "
                  "connected, so owner details shown here are not real.",
        "record": rto.lookup_rto_vehicle(plate),
    }


def to_b64(img, max_side=480, quality=80):
    h, w = img.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode() if ok else ""
