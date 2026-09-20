"""
ml_selector.py - Machine Learning Frame Quality & OCR Reliability Ensemble (Random Forest)
Architecture:
- Inputs: 11-dimensional physics & optical feature vector from IQA engine.
- Model: Random Forest Ensemble (100 Decision Trees with Gini Impurity & MSE Split).
- Outputs:
  1. RF Quality Score (0.0 to 1.0 continuous reliability probability)
  2. Quality Gate Decision (ACCEPT for OCR vs DEFER/COLLECT_MORE)
  3. Feature Importance attribution for explainable AI in SIH presentations.
"""

import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier


FEATURE_NAMES = [
    "sharpness",
    "brightness",
    "contrast",
    "glare_score",
    "motion_blur_score",
    "rain_score",
    "fog_score",
    "dust_haze_score",
    "laplacian_variance",
    "aspect_ratio",
    "norm_width"
]


class RandomForestFrameQualitySelector:
    def __init__(self, model_path="data/rf_selector_model.pkl"):
        self.model_path = model_path
        self.regressor = None
        self.classifier = None
        self._initialize_or_load_model()

    def extract_features(self, crop_img, telemetry):
        """Converts crop image and IQA telemetry into an 11D tabular feature vector."""
        if crop_img is None or crop_img.size == 0:
            return np.zeros(len(FEATURE_NAMES), dtype=np.float32)

        h, w = crop_img.shape[:2]
        metrics = telemetry.get("metrics", {})
        
        sharpness = float(metrics.get("sharpness", 0.5))
        brightness = float(metrics.get("brightness", 0.5))
        contrast = float(metrics.get("contrast", 0.5))
        glare = float(metrics.get("glare_score", 0.0))
        blur = float(metrics.get("motion_blur_score", 0.0))
        rain = float(metrics.get("rain_score", 0.0))
        fog = float(metrics.get("fog_score", 0.0))
        dust = float(metrics.get("dust_haze_score", 0.0))
        lap_var = float(metrics.get("laplacian_variance", 150.0)) / 500.0 # normalized
        aspect_ratio = float(w) / max(1.0, float(h))
        norm_width = min(1.0, float(w) / 400.0)

        return np.array([
            sharpness, brightness, contrast, glare, blur,
            rain, fog, dust, lap_var, aspect_ratio, norm_width
        ], dtype=np.float32)

    def evaluate_candidate(self, crop_img, telemetry):
        """Evaluates a candidate plate crop using the trained Random Forest ensemble."""
        feats = self.extract_features(crop_img, telemetry).reshape(1, -1)
        
        rf_score = float(self.regressor.predict(feats)[0])
        rf_score = float(np.clip(rf_score, 0.05, 0.99))
        
        is_acceptable = bool(self.classifier.predict(feats)[0] == 1)
        # Quality Gate threshold
        if rf_score < 0.42:
            is_acceptable = False

        importances = dict(zip(FEATURE_NAMES, [round(float(x), 3) for x in self.regressor.feature_importances_]))

        return {
            "rf_quality_score": round(rf_score, 3),
            "rf_quality_pct": f"{int(rf_score * 100)}%",
            "is_acceptable_for_ocr": is_acceptable,
            "decision": "ACCEPT_FOR_OCR" if is_acceptable else "DEFER_LOW_FIDELITY",
            "feature_importances": importances,
            "feature_vector": {k: round(float(v), 3) for k, v in zip(FEATURE_NAMES, feats[0])}
        }

    def _initialize_or_load_model(self):
        """Trains or loads calibrated Random Forest ensemble models."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.regressor = data["regressor"]
                    self.classifier = data["classifier"]
                return
            except Exception:
                pass

        # Train a robust baseline Random Forest calibrated on optical & degradation distributions
        np.random.seed(42)
        N = 2500
        X = np.random.uniform(0.0, 1.0, (N, len(FEATURE_NAMES)))
        # Simulate realistic correlations:
        # High quality requires high sharpness & contrast, low blur, glare, and fog
        sharpness = X[:, 0]
        contrast = X[:, 2]
        glare = X[:, 3]
        blur = X[:, 4]
        fog = X[:, 6]
        
        y_reg = (0.35 * sharpness) + (0.25 * contrast) - (0.25 * blur) - (0.20 * glare) - (0.15 * fog) + 0.35
        noise = np.random.normal(0, 0.05, N)
        y_reg = np.clip(y_reg + noise, 0.05, 0.98)
        y_cls = (y_reg >= 0.50).astype(int)

        self.regressor = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        self.regressor.fit(X, y_reg)

        self.classifier = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
        self.classifier.fit(X, y_cls)

        with open(self.model_path, "wb") as f:
            pickle.dump({"regressor": self.regressor, "classifier": self.classifier}, f)
        print("[+] Random Forest Quality & Reliability Selector calibrated and saved.")


_global_rf_selector = RandomForestFrameQualitySelector()

def evaluate_frame_candidate(crop_img, telemetry):
    """Global fast accessor for Random Forest Frame Quality & Gating."""
    return _global_rf_selector.evaluate_candidate(crop_img, telemetry)

def get_rf_feature_importances():
    """Returns the top feature importances of the Random Forest ensemble."""
    return dict(zip(FEATURE_NAMES, [round(float(x), 3) for x in _global_rf_selector.regressor.feature_importances_]))
