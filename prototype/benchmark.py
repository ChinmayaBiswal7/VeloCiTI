"""
benchmark.py - Empirical Benchmarking & Validation Suite for SIH ANPR Pipeline
Performs comparative evaluation:
1. Baseline Single-Frame OCR
2. Proposed SIH Pipeline (Real-Time IQA + Adaptive Restoration + Spatio-Temporal Consensus)
"""

import cv2
import numpy as np
import time
import json
import os
import random
import quality
import enhancer
import anpr

random.seed(42)
np.random.seed(42)

SAMPLE_STATES = ["TN", "OD", "MH", "DL", "KA", "TS", "WB", "GJ", "HR", "UP"]
SAMPLE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_ground_truth_plate():
    st = random.choice(SAMPLE_STATES)
    rto = f"{random.randint(1, 99):02d}"
    series = "".join(random.choices(SAMPLE_LETTERS, k=random.choice([1, 2])))
    num = f"{random.randint(1000, 9999):04d}"
    return f"{st}{rto}{series}{num}"


def render_plate_image(plate_text, condition="NORMAL", severity=1.0):
    """Renders a vehicle plate image and applies physical environmental degradation."""
    h, w = 180, 480
    img = np.zeros((h, w, 3), dtype=np.uint8) + 210

    # Car bumper background
    cv2.rectangle(img, (0, 0), (w, h), (70, 75, 80), -1)

    # Plate border & body
    px1, py1, px2, py2 = 40, 35, 440, 145
    cv2.rectangle(img, (px1, py1), (px2, py2), (255, 255, 255), -1)
    cv2.rectangle(img, (px1, py1), (px2, py2), (10, 10, 10), 3)

    # Blue IND strip
    cv2.rectangle(img, (px1, py1), (px1 + 36, py2), (160, 60, 0), -1)
    cv2.putText(img, "IND", (px1 + 4, py1 + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    # Plate text
    formatted = f"{plate_text[:2]} {plate_text[2:4]} {plate_text[4:-4]} {plate_text[-4:]}"
    cv2.putText(img, formatted, (px1 + 48, py1 + 72), cv2.FONT_HERSHEY_DUPLEX, 1.15, (0, 0, 0), 2)

    if condition == "NIGHT":
        factor = 0.18 + (0.10 * (1.0 - severity))
        img = (img.astype(np.float32) * factor).astype(np.uint8)
        noise = np.random.normal(0, 4 * severity, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    elif condition == "FOG":
        fog_layer = np.full_like(img, 220)
        alpha = 0.35 - (0.10 * severity)
        img = cv2.addWeighted(img, alpha, fog_layer, 1.0 - alpha, 0)

    elif condition == "DUST":
        dust_overlay = np.zeros_like(img)
        dust_overlay[:, :] = [40, 130, 175]
        img = cv2.addWeighted(img, 0.65, dust_overlay, 0.35, 0)

    elif condition == "RAIN":
        num_streaks = int(220 * severity)
        for _ in range(num_streaks):
            rx = random.randint(0, w - 1)
            ry = random.randint(0, h - 25)
            length = random.randint(10, 22)
            cv2.line(img, (rx, ry), (rx + random.randint(-1, 1), ry + length), (240, 240, 245), 1)

    elif condition == "GLARE":
        radius = int(50 * severity)
        cv2.circle(img, (px1 + 160, py1 + 55), radius, (255, 255, 255), -1)
        img = cv2.GaussianBlur(img, (3, 3), 0)

    elif condition == "MOTION_BLUR":
        k_size = max(3, int(9 * severity))
        if k_size % 2 == 0:
            k_size += 1
        kernel_motion = np.zeros((k_size, k_size))
        kernel_motion[int((k_size - 1) / 2), :] = np.ones(k_size) / k_size
        img = cv2.filter2D(img, -1, kernel_motion)

    return img


def calculate_cer(reference, hypothesis):
    """Calculates Levenshtein distance Character Error Rate (CER)."""
    if not reference:
        return 1.0 if hypothesis else 0.0
    if not hypothesis:
        return 1.0

    r = reference.upper().replace(" ", "")
    h = hypothesis.upper().replace(" ", "")

    dp = np.zeros((len(r) + 1, len(h) + 1), dtype=int)
    for i in range(len(r) + 1):
        dp[i][0] = i
    for j in range(len(h) + 1):
        dp[0][j] = j

    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            if r[i - 1] == h[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    dist = dp[len(r)][len(h)]
    return dist / max(len(r), 1)


def run_benchmark(samples_per_condition=10):
    print("=" * 82)
    print("  SIH 2026 EMPIRICAL ACCURACY & ENVIRONMENTAL BENCHMARK SUITE")
    print("=" * 82)

    conditions = [
        ("Normal Daylight", "NORMAL"),
        ("Night / Low Light", "NIGHT"),
        ("Heavy Rain", "RAIN"),
        ("Dense Fog / Haze", "FOG"),
        ("Dust / Smog", "DUST"),
        ("Specular Glare", "GLARE"),
        ("Motion Blur", "MOTION_BLUR")
    ]

    benchmark_results = []
    total_samples = 0
    total_single_correct = 0
    total_consensus_correct = 0

    for label, cond_code in conditions:
        print(f"\n[*] Evaluating: {label} ({samples_per_condition} vehicle track sequences)...")
        single_correct = 0
        consensus_correct = 0
        cer_list = []
        latencies = []

        for i in range(samples_per_condition):
            gt_plate = generate_ground_truth_plate()
            # Fresh dedicated buffer per vehicle track
            fusion_engine = anpr.SpatioTemporalSequenceFusion(buffer_size=6)
            track_id = i + 1

            # Generate a 4-frame tracking sequence for this vehicle
            severities = [0.7, 0.9, 0.3, 0.5] if cond_code != "NORMAL" else [0.0, 0.0, 0.0, 0.0]
            track_frames = [render_plate_image(gt_plate, condition=cond_code, severity=s) for s in severities]


            # 1. Evaluate baseline single-frame on the first frame
            f0 = track_frames[0]
            t0 = time.perf_counter()
            d0 = anpr.scan_frame_for_plates(f0)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

            pred_single = d0[0]["plate"] if d0 else ""
            if pred_single == gt_plate:
                single_correct += 1

            # 2. Evaluate Proposed SIH Pipeline (IQA + Adaptive Restoration + Multi-Frame Consensus)
            final_consensus_plate = ""
            for frame_obs in track_frames:
                tel = quality.assess_image_quality(frame_obs)
                restored = enhancer.restore_image(frame_obs, tel)
                dets = anpr.scan_frame_for_plates(restored)
                obs_text = dets[0]["plate"] if dets else ""
                obs_conf = dets[0]["confidence"] if dets else 0.5
                if obs_text:
                    res = fusion_engine.add_frame_observation(track_id, frame_obs, obs_text, obs_conf, tel)
                    final_consensus_plate = res[0]

            cer = calculate_cer(gt_plate, final_consensus_plate)
            cer_list.append(cer)

            if final_consensus_plate == gt_plate:
                consensus_correct += 1

        single_acc = (single_correct / samples_per_condition) * 100.0
        cons_acc = (consensus_correct / samples_per_condition) * 100.0
        avg_cer = float(np.mean(cer_list)) * 100.0
        avg_lat = float(np.mean(latencies))

        total_samples += samples_per_condition
        total_single_correct += single_correct
        total_consensus_correct += consensus_correct

        res_item = {
            "condition": label,
            "samples": samples_per_condition,
            "single_frame_acc": round(single_acc, 1),
            "sih_consensus_acc": round(cons_acc, 1),
            "cer_pct": round(avg_cer, 2),
            "avg_latency_ms": round(avg_lat, 1),
            "gain_pct": round(cons_acc - single_acc, 1)
        }
        benchmark_results.append(res_item)
        print(f"    -> Baseline Single-Frame: {single_acc:.1f}% | SIH Consensus: {cons_acc:.1f}% (+{cons_acc-single_acc:.1f}% Gain) | CER: {avg_cer:.2f}%")

    overall_single = (total_single_correct / total_samples) * 100.0
    overall_cons = (total_consensus_correct / total_samples) * 100.0

    print("\n" + "=" * 82)
    print("  EMPIRICAL ACCURACY GAIN COMPARISON (SIH Presentation Ready)")
    print("=" * 82)
    print(f"{'Condition':<20} | {'Samples':<7} | {'Single-Frame':<13} | {'SIH Consensus':<13} | {'Gain':<8} | {'Avg CER'}")
    print("-" * 82)
    for r in benchmark_results:
        print(f"{r['condition']:<20} | {r['samples']:<7} | {r['single_frame_acc']:>6.1f}%       | {r['sih_consensus_acc']:>6.1f}%       | +{r['gain_pct']:>4.1f}%  | {r['cer_pct']:>5.2f}%")
    print("-" * 82)
    print(f"{'TOTAL / OVERALL':<20} | {total_samples:<7} | {overall_single:>6.1f}%       | {overall_cons:>6.1f}%       | +{overall_cons-overall_single:>4.1f}%  |")
    print("=" * 82)

    out_path = os.path.join(os.path.dirname(__file__), "data", "benchmark_report.json")
    with open(out_path, "w") as f:
        json.dump({
            "overall_single_frame_acc": round(overall_single, 2),
            "overall_sih_consensus_acc": round(overall_cons, 2),
            "overall_accuracy_gain": round(overall_cons - overall_single, 2),
            "results": benchmark_results
        }, f, indent=2)
    print(f"\n[+] Full empirical report saved to: {out_path}")
    return benchmark_results


if __name__ == "__main__":
    run_benchmark(samples_per_condition=10)
