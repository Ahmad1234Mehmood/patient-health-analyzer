"""Edge detection: Sobel (gradient magnitude) and Canny (multi-stage detector).

Sobel : convolves with two 3x3 (or larger) kernels approximating d/dx and d/dy.
        magnitude = sqrt(Gx^2 + Gy^2) -> bright where intensity changes fast (rib edges, lung borders).
Canny : (1) Gaussian smoothing  (2) gradient magnitude/direction  (3) non-maximum suppression
        -> 1-pixel thin edges  (4) double threshold + hysteresis: strong edges are kept, weak edges
        are kept only if connected to strong ones.  Result is a clean binary edge map.
"""
from __future__ import annotations

import cv2
import numpy as np


def sobel(img: np.ndarray, ksize: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Return (magnitude as uint8 0-255, direction in radians)."""
    ksize = ksize if ksize in (1, 3, 5, 7) else 3
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=ksize)
    mag = cv2.magnitude(gx, gy)
    direction = np.arctan2(gy, gx)
    mag8 = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return mag8, direction


def canny(img: np.ndarray, low: float | None = None, high: float | None = None) -> tuple[np.ndarray, float, float]:
    """Canny with automatic thresholds when low/high are None (high = Otsu level, low = high/2)."""
    if high is None:
        high, _ = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if low is None:
        low = 0.5 * high
    low, high = float(min(low, high)), float(max(low, high))
    return cv2.Canny(img, low, high), low, high

# X-ray pipeline complete
