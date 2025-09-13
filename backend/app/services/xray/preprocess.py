"""Pre-processing: resize, contrast enhancement (CLAHE) and denoising.

Why CLAHE?  Chest X-rays have a huge dynamic range: the lungs are dark and low-contrast, while
bones and the heart are bright.  Plain histogram equalisation over-amplifies noise.  CLAHE
(Contrast-Limited Adaptive Histogram Equalisation) equalises small tiles separately and clips the
histogram, so local contrast (vessels, rib edges, lung borders) improves without blowing up noise.
"""
from __future__ import annotations

import cv2
import numpy as np


def resize_max_side(img: np.ndarray, max_side: int = 512, interp: int = cv2.INTER_AREA) -> np.ndarray:
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1.0:
        return img
    return cv2.resize(img, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=interp)


def enhance(img: np.ndarray, clip_limit: float = 2.0, tile: int = 8, blur_k: int = 5) -> np.ndarray:
    """CLAHE followed by a light Gaussian blur (blur_k must be odd; 0/1 disables)."""
    clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=(int(tile), int(tile)))
    out = clahe.apply(img)
    if blur_k and blur_k > 1:
        k = int(blur_k) | 1
        out = cv2.GaussianBlur(out, (k, k), 0)
    return out


def histogram(img: np.ndarray, bins: int = 64) -> list[int]:
    h = cv2.calcHist([img], [0], None, [bins], [0, 256]).ravel()
    return h.astype(int).tolist()

# v2
