"""
enhancer.py - Adaptive Image Restoration & Enhancement Suite for ANPR
Applies specialized computer vision transformations tailored to adverse environmental conditions:
- Night: Adaptive Multi-Scale Gamma Correction + Bilateral Noise Removal
- Fog / Haze: Dark Channel Prior (DCP) Atmospheric Dehazing
- Dust / Smog: LAB Illuminant Color Balancing + Adaptive Histogram Equalization
- Rain: Directional Streak Morphological Attenuation + Gradient Sharpener
- Glare: Specular Overexposure Inpainting + Tone Mapping
- Motion Blur: Laplacian High-Frequency Unsharp Masking
"""

import cv2
import numpy as np


class AdaptiveImageEnhancer:
    def __init__(self):
        # Pre-build gamma lookup tables for ultra-fast execution
        self.gamma_lut_night = np.array([((i / 255.0) ** 0.45) * 255 for i in np.arange(0, 256)]).astype("uint8")
        self.gamma_lut_glare = np.array([((i / 255.0) ** 1.35) * 255 for i in np.arange(0, 256)]).astype("uint8")

    def enhance_night(self, img):
        """Brightens underexposed night frames and suppresses sensor noise."""
        if img is None or img.size == 0:
            return img
        # 1. Non-linear Gamma Brightening
        bright = cv2.LUT(img, self.gamma_lut_night)
        # 2. Bilateral filtering to preserve character boundaries
        denoised = cv2.bilateralFilter(bright, d=5, sigmaColor=40, sigmaSpace=40)
        # 3. CLAHE in LAB space for local contrast
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enh = clahe.apply(l)
        lab_enh = cv2.merge((l_enh, a, b))
        return cv2.cvtColor(lab_enh, cv2.COLOR_LAB2BGR)

    def enhance_fog(self, img):
        """Fast Dark Channel Prior (DCP) Dehazing + Contrast Normalization."""
        if img is None or img.size == 0:
            return img
        # Normalize to float [0, 1]
        norm = img.astype(np.float32) / 255.0
        # Estimate Dark Channel
        dark = np.min(norm, axis=2)
        dark = cv2.erode(dark, np.ones((5, 5), np.uint8))
        
        # Estimate Atmospheric Light A (top 0.1% brightest in dark channel)
        num_pixels = dark.size
        num_top = max(1, int(num_pixels * 0.001))
        flat_dark = dark.flatten()
        indices = np.argpartition(flat_dark, -num_top)[-num_top:]
        flat_img = norm.reshape(-1, 3)
        A = np.mean(flat_img[indices], axis=0)
        A = np.clip(A, 0.5, 0.95)

        # Transmission map estimation with omega=0.85
        t = 1.0 - 0.85 * (dark / np.max(A))
        t = np.clip(t, 0.20, 1.0)
        t_smooth = cv2.GaussianBlur(t, (9, 9), 0)

        # Recover scene radiance: J = (I - A)/max(t, 0.1) + A
        t_3d = np.repeat(t_smooth[:, :, np.newaxis], 3, axis=2)
        dehazed = (norm - A) / np.maximum(t_3d, 0.18) + A
        dehazed = np.clip(dehazed * 255.0, 0, 255).astype(np.uint8)

        # Post-dehaze CLAHE
        lab = cv2.cvtColor(dehazed, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l_enh = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l_enh, a, b)), cv2.COLOR_LAB2BGR)

    def enhance_dust(self, img):
        """Removes yellow/brown smog cast via LAB chromatic balance + contrast stretching."""
        if img is None or img.size == 0:
            return img
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Neutralize yellow cast by centering b* channel around 128
        b_float = b.astype(np.float32)
        b_shift = np.mean(b_float) - 128.0
        if b_shift > 4.0:
            b_float = np.clip(b_float - (b_shift * 0.75), 0, 255).astype(np.uint8)
        else:
            b_float = b

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enh = clahe.apply(l)
        restored = cv2.cvtColor(cv2.merge((l_enh, a, b_float.astype(np.uint8))), cv2.COLOR_LAB2BGR)
        return restored

    def enhance_rain(self, img):
        """Enhances contrast and edge gradients without eroding character strokes."""
        if img is None or img.size == 0:
            return img
        # Gentle bilateral filter to smooth streak noise while locking edges
        denoised = cv2.bilateralFilter(img, d=5, sigmaColor=30, sigmaSpace=30)
        # Unsharp mask to bring out character contours
        blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
        boosted = cv2.addWeighted(denoised, 1.4, blurred, -0.4, 0)
        return np.clip(boosted, 0, 255).astype(np.uint8)


    def enhance_glare(self, img):
        """Neutralizes specular headlight/sun glare via inpainting and tone curve."""
        if img is None or img.size == 0:
            return img
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Find overexposed glare hotspots
        _, glare_mask = cv2.threshold(gray, 242, 255, cv2.THRESH_BINARY)
        # Dilate mask slightly to cover halo
        glare_mask = cv2.dilate(glare_mask, np.ones((3, 3), np.uint8), iterations=1)
        
        # If glare area is moderate, inpaint texture
        glare_ratio = float(np.sum(glare_mask > 0)) / float(glare_mask.size)
        if 0.01 < glare_ratio < 0.30:
            inpainted = cv2.inpaint(img, glare_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        else:
            inpainted = img

        # Apply glare compression LUT
        compressed = cv2.LUT(inpainted, self.gamma_lut_glare)
        return compressed

    def enhance_blur(self, img):
        """Laplacian high-frequency unsharp masking for motion blur recovery."""
        if img is None or img.size == 0:
            return img
        blurred = cv2.GaussianBlur(img, (3, 3), 0)
        sharpened = cv2.addWeighted(img, 1.65, blurred, -0.65, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    def adaptive_restore(self, img, telemetry):
        """
        Orchestrates condition-specific enhancement pipeline based on IQA telemetry.
        """
        if img is None or img.size == 0:
            return img
        
        recs = telemetry.get("recommended_enhancements", [])
        proc = img.copy()

        # Chain enhancements in logical optical order:
        # 1. Glare Inpainting -> 2. Dehazing/Dust -> 3. Night Brightening -> 4. Rain Streak Filter -> 5. Blur Sharpening
        if "SPECULAR_GLARE_INPAINT" in recs:
            proc = self.enhance_glare(proc)
        if "DCP_GUIDED_DEHAZE" in recs:
            proc = self.enhance_fog(proc)
        if "LAB_COLOR_BALANCE_CLAHE" in recs:
            proc = self.enhance_dust(proc)
        if "MSR_GAMMA_CORRECTION" in recs:
            proc = self.enhance_night(proc)
        if "DIRECTIONAL_RAIN_FILTER" in recs:
            proc = self.enhance_rain(proc)
        if "UNSHARP_LAPLACIAN_SHARPEN" in recs:
            proc = self.enhance_blur(proc)
        if "STANDARD_CLAHE" in recs and len(recs) == 1:
            lab = cv2.cvtColor(proc, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            proc = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

        return proc


_global_enhancer = AdaptiveImageEnhancer()

def restore_image(img, telemetry):
    """Global fast accessor for Adaptive Image Restoration."""
    return _global_enhancer.adaptive_restore(img, telemetry)
