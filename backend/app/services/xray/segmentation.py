"""Classical lung segmentation (no deep learning) with three interchangeable methods.

Idea: in a chest X-ray the lungs are filled with air, so they are *dark*; the surrounding
soft-tissue/bone is brighter.  We threshold, then use morphology + connected components +
anatomical priors (two big blobs, not touching the image border) to isolate the two lungs.

methods
-------
otsu     : global Otsu threshold (maximises between-class variance) - fast baseline
kmeans   : k-means (k=4) on intensities - air / lung / soft tissue / dense (bone, heart) clusters
adaptive : local Gaussian adaptive threshold AND'ed with a relaxed Otsu level - copes with uneven exposure
"""
from __future__ import annotations

import cv2
import numpy as np

METHODS = ("otsu", "kmeans", "adaptive")


def _candidate(blur: np.ndarray, method: str) -> tuple[np.ndarray, float]:
    """Boolean mask of 'dark' pixels (lung OR outside-body air) and the threshold used."""
    otsu_t, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if method == "otsu":
        return blur < otsu_t, float(otsu_t)
    if method == "kmeans":
        data = blur.reshape(-1, 1).astype(np.float32)
        # subsample for speed on large images, then assign all pixels
        sample = data[:: max(1, data.shape[0] // 40000)]
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
        cv2.setRNGSeed(0)
        _, _, centers = cv2.kmeans(sample, 4, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        c = np.sort(centers.ravel())
        thr = float((c[1] + c[2]) / 2.0)  # boundary between the 2nd (lung) and 3rd (soft tissue) cluster
        return blur < thr, thr
    if method == "adaptive":
        block = max(31, (min(blur.shape) // 4) | 1)
        local = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, 2)
        return (local > 0) & (blur < otsu_t * 1.15), float(otsu_t)
    raise ValueError(f"unknown method {method}")


def _components(mask: np.ndarray):
    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    return n, labels, stats, cents


def _border_contact(labels: np.ndarray, lab: int, frame: int = 2) -> int:
    m = labels == lab
    return int(m[:frame].sum() + m[-frame:].sum() + m[:, :frame].sum() + m[:, -frame:].sum())


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    inv = (mask == 0).astype(np.uint8) * 255
    ff = inv.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 0)
    # pixels of `inv` still 255 after the flood are holes surrounded by the mask
    return ((mask > 0) | (ff > 0)).astype(np.uint8) * 255


def _pick_two_lungs(binary: np.ndarray, min_area_pct: float) -> np.ndarray:
    """Drop outside-body air (touches the border broadly), keep the two largest central blobs."""
    h, w = binary.shape
    n, labels, stats, cents = _components(binary)
    perimeter = 2 * (h + w)
    min_area = min_area_pct / 100.0 * h * w
    cands = []
    for lab in range(1, n):
        area = stats[lab, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        touch = _border_contact(labels, lab)
        if touch > 0.03 * perimeter:       # large contact with the frame -> background air
            continue
        cx = cents[lab][0] / w
        if not 0.1 < cx < 0.9:             # lungs sit in the central 80 % horizontally
            continue
        cands.append((area, lab))
    cands.sort(reverse=True)
    out = np.zeros_like(binary, np.uint8)
    for _, lab in cands[:2]:
        out[labels == lab] = 255
    return out


def _split_merged(binary: np.ndarray, min_area_pct: float, max_erosions: int = 12) -> np.ndarray:
    """If both lungs fused into one blob, erode until they separate, pick them, grow them back."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cur = binary.copy()
    for i in range(1, max_erosions + 1):
        cur = cv2.erode(cur, k)
        n, labels, stats, _ = _components(cur)
        big = [l for l in range(1, n) if stats[l, cv2.CC_STAT_AREA] > min_area_pct / 100.0 * binary.size * 0.3]
        if len(big) >= 2:
            seeds = np.zeros_like(cur)
            for l in sorted(big, key=lambda l: -stats[l, cv2.CC_STAT_AREA])[:2]:
                seeds[labels == l] = 255
            grown = cv2.dilate(seeds, k, iterations=i)
            return cv2.bitwise_and(grown, binary)
    return binary


def segment_lungs(
    enhanced: np.ndarray,
    method: str = "otsu",
    morph_k: int = 7,
    min_area_pct: float = 1.0,
) -> tuple[np.ndarray, dict]:
    """Return (mask uint8 0/255, info dict). `enhanced` = CLAHE'd 8-bit image."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    blur = cv2.GaussianBlur(enhanced, (5, 5), 0)
    cand, thr = _candidate(blur, method)
    binary = cand.astype(np.uint8) * 255

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(3, int(morph_k)) | 1,) * 2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)    # remove specks / thin bridges
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)   # close small gaps (vessels, ribs)

    lungs = _pick_two_lungs(binary, min_area_pct)
    n_found = _components(lungs)[0] - 1
    if n_found < 2:
        # maybe fused: try to split the biggest central blob
        merged = _pick_two_lungs(binary, min_area_pct)
        split = _split_merged(merged, min_area_pct) if merged.any() else merged
        lungs = _pick_two_lungs(split, min_area_pct)
        n_found = _components(lungs)[0] - 1

    lungs = _fill_holes(lungs)
    lungs = cv2.morphologyEx(lungs, cv2.MORPH_CLOSE, k)
    lungs = cv2.medianBlur(lungs, 9)
    return lungs, {"threshold": thr, "method": method, "n_components": int(n_found)}


def split_left_right(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (image-left blob, image-right blob). Radiological convention: image-left = patient's RIGHT lung."""
    n, labels, stats, cents = _components(mask > 0)
    comps = sorted(range(1, n), key=lambda l: cents[l][0])
    empty = np.zeros_like(mask)
    if not comps:
        return empty, empty
    if len(comps) == 1:
        l = comps[0]
        m = (labels == l).astype(np.uint8) * 255
        # one blob: split at its horizontal centre of mass
        x = int(cents[l][0])
        a, b = m.copy(), m.copy()
        a[:, x:] = 0
        b[:, :x] = 0
        return a, b
    left = (labels == comps[0]).astype(np.uint8) * 255
    right = np.zeros_like(mask)
    for l in comps[1:]:
        right[labels == l] = 255
    return left, right

# v2
