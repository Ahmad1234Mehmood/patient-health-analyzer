"""R-peak (QRS) detection - a compact Pan-Tompkins style detector.

Pipeline (Pan & Tompkins, 1985):
  1. Band-pass 5-15 Hz  -> keeps QRS energy, suppresses P/T waves, baseline drift and muscle noise
  2. Derivative         -> emphasises the steep slopes of the QRS
  3. Squaring           -> all positive, amplifies large slopes
  4. Moving-window integration (~120 ms) -> one smooth bump per heartbeat
  5. Peak picking with a 250 ms refractory period + adaptive threshold
  6. Search-back for missed beats when an RR gap is suspiciously long
  7. Refinement: snap each detection to the true local maximum of the filtered ECG
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def _qrs_energy(x: np.ndarray, fs: float) -> np.ndarray:
    high = min(15.0, fs / 2 * 0.9)
    sos = signal.butter(2, [5.0, high], btype="bandpass", fs=fs, output="sos")
    band = signal.sosfiltfilt(sos, x)
    sq = np.gradient(band) ** 2
    win = max(1, int(0.12 * fs))
    return np.convolve(sq, np.ones(win) / win, mode="same")


def detect_r_peaks(x: np.ndarray, fs: float) -> np.ndarray:
    """Return sample indices of R peaks in a single-lead ECG (already filtered or not)."""
    x = np.asarray(x, dtype=np.float64)
    x = x - np.median(x)
    if x.size < int(2 * fs) or np.ptp(x) < 1e-9:
        return np.array([], dtype=int)

    mwi = _qrs_energy(x, fs)
    refractory = int(0.25 * fs)
    cand, _ = signal.find_peaks(mwi, distance=refractory)
    if cand.size == 0:
        return np.array([], dtype=int)

    heights = mwi[cand]
    level = np.median(heights[heights >= np.median(heights)])  # robust "typical QRS" level
    thr = 0.3 * level
    sel = heights >= thr
    cand, heights = cand[sel], heights[sel]

    # ---- T-wave rejection (Pan-Tompkins rule): a candidate < 360 ms after the previous beat
    #      whose slope energy is < 50 % of that beat is a T wave, not a new QRS
    keep_idx: list[int] = []
    for i in range(cand.size):
        if keep_idx:
            j = keep_idx[-1]
            if cand[i] - cand[j] < int(0.36 * fs) and heights[i] < 0.5 * heights[j]:
                continue
        keep_idx.append(i)
    peaks = cand[keep_idx]

    # ---- search-back: look for a missed beat inside unusually long RR gaps
    if peaks.size >= 3:
        rr_med = np.median(np.diff(peaks))
        extra = []
        for a, b in zip(peaks[:-1], peaks[1:]):
            if (b - a) > 1.66 * rr_med:
                lo, hi = int(a + 0.35 * rr_med), int(b - 0.35 * rr_med)
                if hi > lo:
                    seg = mwi[lo:hi]
                    k = int(np.argmax(seg))
                    if seg[k] > 0.5 * thr:
                        extra.append(lo + k)
        if extra:
            peaks = np.sort(np.concatenate([peaks, extra]))

    if peaks.size == 0:
        return peaks

    # ---- refinement on the (0.5-40 Hz style) signal; handle inverted QRS (e.g. lead aVR)
    half = max(1, int(0.08 * fs))
    pos, neg = [], []
    for p in peaks:
        seg = x[max(0, p - half): p + half + 1]
        pos.append(seg.max())
        neg.append(-seg.min())
    polarity = 1.0 if np.median(pos) >= np.median(neg) else -1.0
    refined = []
    for p in peaks:
        lo = max(0, p - half)
        seg = polarity * x[lo: p + half + 1]
        refined.append(lo + int(np.argmax(seg)))
    refined = np.unique(refined)

    # ---- enforce refractory period, keeping the larger deflection
    keep = [refined[0]]
    for p in refined[1:]:
        if p - keep[-1] < refractory:
            if polarity * x[p] > polarity * x[keep[-1]]:
                keep[-1] = p
        else:
            keep.append(p)
    return np.asarray(keep, dtype=int)

# v2
