"""Heart-rate variability (time domain) from R-peak positions.

Notes for interpretation: clinical HRV norms need 5-minute (short-term) or 24-hour recordings.
With the usual 10-second 12-lead snapshot, SDNN/RMSSD are only *indicative*.
"""
from __future__ import annotations

import numpy as np


def compute_hrv(peaks: np.ndarray, fs: float) -> dict:
    out: dict = {"n_beats": int(peaks.size), "rr_ms": [], "valid": False}
    if peaks.size < 3:
        return out
    rr = np.diff(peaks) / fs * 1000.0
    ok = (rr > 300) & (rr < 2000)  # drop physiologically impossible intervals (missed/extra detections)
    rr = rr[ok]
    if rr.size < 2:
        return out
    d = np.diff(rr)
    mean_rr = float(rr.mean())
    sdnn = float(rr.std(ddof=1))
    rmssd = float(np.sqrt(np.mean(d ** 2))) if d.size else 0.0
    pnn50 = float(np.mean(np.abs(d) > 50.0) * 100.0) if d.size else 0.0
    sd1 = rmssd / np.sqrt(2)
    sd2 = float(np.sqrt(max(2 * sdnn ** 2 - 0.5 * rmssd ** 2, 0.0)))
    out.update(
        valid=True,
        rr_ms=rr,
        mean_rr_ms=mean_rr,
        hr_bpm=60000.0 / mean_rr,
        hr_min_bpm=60000.0 / float(rr.max()),
        hr_max_bpm=60000.0 / float(rr.min()),
        sdnn_ms=sdnn,
        rmssd_ms=rmssd,
        pnn50_pct=pnn50,
        cv=sdnn / mean_rr,
        poincare={"x": rr[:-1], "y": rr[1:], "sd1_ms": float(sd1), "sd2_ms": sd2},
    )
    return out

# v2
