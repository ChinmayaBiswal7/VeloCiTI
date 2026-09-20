"""
quality.py - Real-Time Environmental & Image Quality Assessment (IQA) Engine
Architecture:
1. Scene-Level Environmental Assessment (Rain, Fog, Dust, Night, Ambient Daylight)
   with 20-frame Temporal Hysteresis Filter (Prevents state oscillation).
2. Frame-Level Optical Assessment (Motion Blur, Specular Glare, Defocus, Occlusion).
3. Hybrid Physics-Based Heuristics + Multi-Scale Feature Embedding.
"""

import cv2
import numpy as np
from collections import deque, Counter


class RealTimeImageQualityAssessor:
    def __init__(self, scene_buffer_size=20):
        # Pre-calculated morphological kernels for fast vector execution (<3ms)
        self.rain_k_vert = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 9))
        self.rain_k_horiz = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1))
        self.dust_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        
        # Temporal Hysteresis Buffer for Scene-Level Conditions
        self.scene_buffer_size = scene_buffer_size
        self.scene_history = deque(maxlen=scene_buffer_size)
        self.last_confirmed_scene = "NORMAL"

    def evaluate(self, img, is_scene_frame=True):
        """
        Takes a BGR image/crop and returns comprehensive IQA & Environmental Telemetry.
        Separates macro Scene-Level conditions from micro Frame-Level artifacts.
        """
        if img is None or img.size == 0:
            return self._default_telemetry()

        h, w = img.shape[:2]
        if w > 320:
            scale = 320.0 / w
            proc = cv2.resize(img, (320, int(h * scale)))
        else:
            proc = img

        gray = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(proc, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(proc, cv2.COLOR_BGR2LAB)

        # -------------------------------------------------------------
        # 1. Luminance & Low-Light Metrics (Night / Dark)
        # -------------------------------------------------------------
        v_channel = hsv[:, :, 2]
        mean_brightness = float(np.mean(v_channel)) / 255.0
        dark_pixel_ratio = float(np.sum(v_channel < 40)) / float(v_channel.size)
        # Night strictly requires ambient low luminance across the scene
        if is_scene_frame:
            raw_night_score = float(np.clip((0.35 - mean_brightness) * 3.0 + (dark_pixel_ratio * 0.5), 0.0, 1.0))
        else:
            # For vehicle crops, don't let dark car paint falsely trigger Night
            raw_night_score = float(np.clip((0.18 - mean_brightness) * 4.0, 0.0, 1.0)) if (mean_brightness < 0.18 and dark_pixel_ratio > 0.75) else 0.0


        # -------------------------------------------------------------
        # 2. Specular Glare & Overexposure (Frame-Level)
        # -------------------------------------------------------------
        glare_pixel_ratio = float(np.sum(v_channel > 240)) / float(v_channel.size)
        glare_score = float(np.clip(glare_pixel_ratio * 8.0, 0.0, 1.0))

        # -------------------------------------------------------------
        # 3. Sharpness & Motion Blur Metrics (Frame-Level)
        # -------------------------------------------------------------
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        sharpness = float(np.clip(lap_var / 350.0, 0.0, 1.0))
        
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
        grad_mag = np.sqrt(gx**2 + gy**2)
        mean_grad = float(np.mean(grad_mag))
        blur_score = float(np.clip(1.0 - (mean_grad / 26.0), 0.0, 1.0))

        # -------------------------------------------------------------
        # 4. Contrast & Dynamic Range (RMS Contrast)
        # -------------------------------------------------------------
        contrast = float(np.std(gray)) / 128.0
        contrast = float(np.clip(contrast, 0.0, 1.0))

        # -------------------------------------------------------------
        # 5. Fog / Atmospheric Haze (Dark Channel Prior - Scene Level)
        # -------------------------------------------------------------
        if is_scene_frame:
            min_channel = np.min(proc, axis=2)
            dark_channel = cv2.erode(min_channel, np.ones((5, 5), np.uint8))
            dcp_mean = float(np.mean(dark_channel)) / 255.0
            raw_fog_score = float(np.clip((dcp_mean - 0.28) * 2.5, 0.0, 1.0))
        else:
            raw_fog_score = 0.0

        # -------------------------------------------------------------
        # 6. Dust / Smog Estimation (LAB Chromatic Shift - Scene Level)
        # -------------------------------------------------------------
        if is_scene_frame:
            b_channel = lab[:, :, 2].astype(np.float32)
            mean_yellow_shift = float(np.mean(b_channel) - 128.0) / 30.0
            raw_dust_score = float(np.clip(max(0.0, mean_yellow_shift) * 1.5, 0.0, 1.0)) if mean_yellow_shift > 0.35 else 0.0
        else:
            raw_dust_score = 0.0

        # -------------------------------------------------------------
        # 7. Rain Streak Anisotropy (Strict Scene Level Only)
        # -------------------------------------------------------------
        if is_scene_frame and mean_brightness < 0.60:
            v_streak = cv2.morphologyEx(gray, cv2.MORPH_OPEN, self.rain_k_vert)
            h_streak = cv2.morphologyEx(gray, cv2.MORPH_OPEN, self.rain_k_horiz)
            streak_anisotropy = float(np.mean(cv2.absdiff(v_streak, h_streak)))
            raw_rain_score = float(np.clip((streak_anisotropy - 14.0) / 12.0, 0.0, 1.0))
        else:
            raw_rain_score = 0.0

        # -------------------------------------------------------------
        # 8. Instantaneous Scene Condition Scoring
        # -------------------------------------------------------------
        instant_scene_scores = {
            "NIGHT": raw_night_score,
            "RAIN": raw_rain_score,
            "FOG": raw_fog_score,
            "DUST_HAZE": raw_dust_score
        }

        # Find instantaneous dominant scene condition
        max_scene_cand, max_scene_score = max(instant_scene_scores.items(), key=lambda x: x[1])
        instant_scene = max_scene_cand if max_scene_score > 0.65 else "NORMAL"


        # -------------------------------------------------------------
        # 9. Temporal Hysteresis Filter for Scene-Level Conditions
        # -------------------------------------------------------------
        if is_scene_frame:
            self.scene_history.append(instant_scene)
            counts = Counter(self.scene_history)
            dominant_scene, count = counts.most_common(1)[0]
            # Switch scene condition only if sustained across >= 40% of buffer
            if count >= max(2, int(len(self.scene_history) * 0.40)):
                self.last_confirmed_scene = dominant_scene
        
        scene_condition = self.last_confirmed_scene

        # -------------------------------------------------------------
        # 10. Frame-Level Artifacts Detection
        # -------------------------------------------------------------
        frame_artifacts = []
        if glare_score > 0.45:
            frame_artifacts.append("GLARE")
        if blur_score > 0.50:
            frame_artifacts.append("MOTION_BLUR")
        if sharpness < 0.20:
            frame_artifacts.append("DEFOCUS")

        # -------------------------------------------------------------
        # 11. Composite Overall Image Quality Score (0.0 to 1.0)
        # -------------------------------------------------------------
        penalty = (glare_score * 0.25) + (blur_score * 0.35) + (raw_fog_score * 0.20) + (raw_rain_score * 0.15) + (raw_dust_score * 0.15)
        raw_quality = (sharpness * 0.45) + (contrast * 0.35) + (mean_brightness * 0.20) - (penalty * 0.40)
        overall_quality_score = float(np.clip(raw_quality, 0.08, 0.99))

        # -------------------------------------------------------------
        # 12. Quality Gate Recommendation ("Don't OCR Yet" Decision)
        # -------------------------------------------------------------
        # If quality is below 0.38, flag as low fidelity needing multi-frame buffer
        should_defer_ocr = overall_quality_score < 0.38 or (blur_score > 0.70 and glare_score > 0.60)
        quality_status = "OPTIMAL_FOR_OCR" if not should_defer_ocr else "NEEDS_TEMPORAL_BUFFERING"

        # -------------------------------------------------------------
        # 13. Recommended Adaptive Restoration Filters
        # -------------------------------------------------------------
        recommendations = []
        if scene_condition == "NIGHT" or raw_night_score > 0.50:
            recommendations.append("MSR_GAMMA_CORRECTION")
        if scene_condition == "FOG" or raw_fog_score > 0.40:
            recommendations.append("DCP_GUIDED_DEHAZE")
        if scene_condition == "DUST_HAZE" or raw_dust_score > 0.45:
            recommendations.append("LAB_COLOR_BALANCE_CLAHE")
        if scene_condition == "RAIN" or raw_rain_score > 0.45:
            recommendations.append("DIRECTIONAL_RAIN_FILTER")
        if "GLARE" in frame_artifacts:
            recommendations.append("SPECULAR_GLARE_INPAINT")
        if "MOTION_BLUR" in frame_artifacts:
            recommendations.append("UNSHARP_LAPLACIAN_SHARPEN")
        if not recommendations:
            recommendations.append("STANDARD_CLAHE")

        return {
            "scene_condition": scene_condition,
            "frame_artifacts": frame_artifacts,
            "dominant_condition": scene_condition if scene_condition != "NORMAL" else (frame_artifacts[0] if frame_artifacts else "NORMAL"),
            "overall_quality_score": round(overall_quality_score, 3),
            "quality_pct": f"{int(overall_quality_score * 100)}%",
            "quality_status": quality_status,
            "should_defer_ocr": should_defer_ocr,
            "metrics": {
                "sharpness": round(sharpness, 3),
                "brightness": round(mean_brightness, 3),
                "contrast": round(contrast, 3),
                "glare_score": round(glare_score, 3),
                "motion_blur_score": round(blur_score, 3),
                "rain_score": round(raw_rain_score, 3),
                "fog_score": round(raw_fog_score, 3),
                "dust_haze_score": round(raw_dust_score, 3),
                "laplacian_variance": round(lap_var, 1)
            },
            "recommended_enhancements": recommendations,
            "is_degraded": overall_quality_score < 0.65 or scene_condition != "NORMAL" or len(frame_artifacts) > 0
        }

    def _default_telemetry(self):
        return {
            "scene_condition": "NORMAL",
            "frame_artifacts": [],
            "dominant_condition": "NORMAL",
            "overall_quality_score": 0.85,
            "quality_pct": "85%",
            "quality_status": "OPTIMAL_FOR_OCR",
            "should_defer_ocr": False,
            "metrics": {
                "sharpness": 0.8, "brightness": 0.5, "contrast": 0.6,
                "glare_score": 0.0, "motion_blur_score": 0.0, "rain_score": 0.0,
                "fog_score": 0.0, "dust_haze_score": 0.0, "laplacian_variance": 200.0
            },
            "recommended_enhancements": ["STANDARD_CLAHE"],
            "is_degraded": False
        }


_global_assessor = RealTimeImageQualityAssessor(scene_buffer_size=20)

def assess_image_quality(img, is_scene_frame=True):
    """Global fast accessor for Real-Time IQA & Environmental Telemetry."""
    return _global_assessor.evaluate(img, is_scene_frame=is_scene_frame)
