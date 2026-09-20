"""
vehicle_reid.py - Cross-Camera Vehicle Re-Identification (Re-ID) Engine
Matches plate-less / covered-plate vehicles across distributed CCTV cameras
using visual embeddings, color histograms, and body structure metrics.
"""

import json
import random
import numpy as np
import database as db
import vehicle_profiler


def cosine_similarity(vec1, vec2):
    """Computes cosine similarity between two normalized feature vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def generate_ghost_id(dom_color, body_subtype):
    """Generates a clean, human-readable Ghost Vehicle Identifier."""
    color_tag = dom_color.split()[0].upper()[:3] if dom_color else "UNK"
    type_tag = body_subtype.split()[0].upper()[:3] if body_subtype else "VEH"
    rand_num = random.randint(1000, 9999)
    return f"UNPLATED-{color_tag}-{type_tag}-{rand_num}"


def match_or_create_ghost(profile, camera_id, timestamp, image_path, speed_kmph=0.0):
    """
    Compares newly extracted vehicle visual profile against existing active ghost profiles.
    Returns:
        dict: {
            "ghost_id": str,
            "match_score": float,
            "is_new": bool,
            "matched_profile": dict
        }
    """
    curr_emb = json.loads(profile.get("visual_embedding", "[]"))
    curr_type = profile.get("vehicle_type", "Car")
    curr_subtype = profile.get("body_subtype", "Passenger Car")
    curr_color = profile.get("dominant_color", "UNKNOWN").upper()
    curr_ar = float(profile.get("aspect_ratio", 1.0))

    active_candidates = db.get_active_ghost_candidates(limit=40)
    best_match = None
    best_score = 0.0

    for cand in active_candidates:
        cand_emb = json.loads(cand.get("visual_embedding", "[]"))
        cand_type = cand.get("vehicle_type", "Car")
        cand_subtype = cand.get("body_subtype", "Passenger Car")
        cand_color = cand.get("dominant_color", "UNKNOWN").upper()
        cand_ar = float(cand.get("aspect_ratio", 1.0))

        # 1. Base Class Match (Strict requirement - Cars don't match Bikes)
        if curr_type.lower() != cand_type.lower():
            continue

        class_match = 1.0

        # 2. Embedding Cosine Similarity
        emb_sim = max(0.0, cosine_similarity(curr_emb, cand_emb))

        # 3. Dominant Color Match
        if curr_color == cand_color:
            color_match = 1.0
        elif ("SILVER" in curr_color and "WHITE" in cand_color) or ("WHITE" in curr_color and "SILVER" in cand_color):
            color_match = 0.65
        else:
            color_match = 0.0

        # 4. Body Sub-type & Aspect Ratio Match
        subtype_match = 1.0 if curr_subtype == cand_subtype else 0.5
        aspect_diff = abs(curr_ar - cand_ar)
        aspect_sim = max(0.0, 1.0 - (aspect_diff / 0.75))

        # Composite Weighted Multi-Factor Score
        composite_score = (
            0.40 * emb_sim +
            0.25 * color_match +
            0.15 * class_match +
            0.10 * subtype_match +
            0.10 * aspect_sim
        )

        if composite_score > best_score:
            best_score = composite_score
            best_match = cand

    # Re-ID Decision Threshold (0.74 represents high confidence cross-camera match)
    if best_match and best_score >= 0.74:
        ghost_id = best_match["ghost_id"]
        # Update existing profile
        db.update_ghost_last_seen(
            ghost_id=ghost_id,
            last_seen_ts=timestamp,
            last_camera=camera_id,
            new_image_path=image_path
        )
        db.insert_ghost_sighting(
            ghost_id=ghost_id,
            camera_id=camera_id,
            timestamp=timestamp,
            image_path=image_path,
            match_score=round(best_score, 3),
            speed_kmph=speed_kmph
        )
        return {
            "ghost_id": ghost_id,
            "match_score": round(best_score, 3),
            "is_new": False,
            "profile": best_match
        }
    else:
        # Create a new Ghost Profile
        new_ghost_id = generate_ghost_id(curr_color, curr_subtype)
        runner_up_json = json.dumps(profile.get("runner_up")) if profile.get("runner_up") else ""
        db.upsert_ghost_profile(
            ghost_id=new_ghost_id,
            vehicle_type=curr_type,
            body_subtype=curr_subtype,
            dominant_color=profile.get("dominant_color", "UNKNOWN"),
            secondary_color=profile.get("secondary_color", ""),
            color_hex=profile.get("color_hex", "#64748B"),
            aspect_ratio=curr_ar,
            visual_embedding=profile.get("visual_embedding", "[]"),
            first_seen_ts=timestamp,
            last_seen_ts=timestamp,
            first_camera=camera_id,
            last_camera=camera_id,
            best_image_path=image_path,
            status="ACTIVE_TRACKING",
            estimated_make=profile.get("estimated_make", ""),
            estimated_model=profile.get("estimated_model", ""),
            make_confidence=profile.get("make_confidence", 0.0),
            distinguishing_features=profile.get("distinguishing_features", ""),
            runner_up=runner_up_json
        )
        db.insert_ghost_sighting(
            ghost_id=new_ghost_id,
            camera_id=camera_id,
            timestamp=timestamp,
            image_path=image_path,
            match_score=1.0,
            speed_kmph=speed_kmph
        )
        return {
            "ghost_id": new_ghost_id,
            "match_score": 1.0,
            "is_new": True,
            "profile": profile
        }
