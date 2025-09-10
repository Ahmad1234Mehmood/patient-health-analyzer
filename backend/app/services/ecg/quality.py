"""Signal-quality index (SQI) so the user knows whether the numbers can be trusted."""
from __future__ import annotations

import numpy as np

from .spectral import band_powers, powerline_excess_db, welch_psd


def beat_snr_db(raw: np.ndarray, peaks: np.ndarray, fs: float) -> float | None:
    """Ensemble SNR: variance of the average beat (signal) / variance of beat-to-beat residuals (noise).

    Unlike `var(filtered) / var(raw - filtered)` this does not count the high-frequency part of a
    sharp QRS as "noise", so a clean ECG is not penalised.  Needs >= 5 beats.
    """
    pre, post = int(0.16 * fs), int(0.32 * fs)
    beats = []
    for i, p in enumerate(peaks):
        # skip beats whose neighbours fall inside the window (fast / irregular rhythm would inflate "noise")
        if i > 0 and p - peaks[i - 1] < pre + int(0.05 * fs):
            continue
        if i + 1 < len(peaks) and peaks[i + 1] - p < post + int(0.02 * fs):
            continue
        if p - pre >= 0 and p + post <= raw.size:
            seg = raw[p - pre: p + post].copy()
            x = np.arange(seg.size)
            seg -= np.polyval(np.polyfit(x, seg, 1), x)  # remove per-beat offset/slope (baseline)
            beats.append(seg)
    if len(beats) < 5:
        return None
    arr = np.vstack(beats)
    template = np.median(arr, axis=0)
    resid = arr - template
    p_noise = float(np.mean(np.var(resid, axis=1)))
    p_sig = float(np.var(template))
    if p_noise < 1e-12 or p_sig <= 0:
        return 60.0
    return float(10 * np.log10(p_sig / p_noise))


def _flat_fraction(x: np.ndarray, fs: float) -> float:
    """Fraction of samples in constant runs >= 100 ms (real lead-off), not individual equal samples."""
    same = np.abs(np.diff(x)) < 1e-9
    min_run = max(5, int(0.1 * fs))
    padded = np.concatenate(([False], same, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[::2], edges[1::2]
    return float(sum(e - s for s, e in zip(starts, ends) if e - s >= min_run) / max(x.size, 1))


def signal_quality(raw: np.ndarray, filtered: np.ndarray, fs: float, mains_hz: float, peaks: np.ndarray | None = None) -> dict:
    snr_db = beat_snr_db(raw, peaks, fs) if peaks is not None else None
    if snr_db is None:  # too few beats: fall back to the crude band-limited estimate
        noise = raw - filtered
        p_sig, p_noise = float(np.var(filtered)), float(np.var(noise))
        snr_db = 10 * np.log10(p_sig / p_noise) if p_noise > 1e-18 and p_sig > 0 else 60.0
    f, p = welch_psd(raw, fs)
    bands = band_powers(f, p)
    baseline = bands["baseline_wander"]
    pl_db = powerline_excess_db(f, p, mains_hz)
    flat = _flat_fraction(raw, fs)
    top, bot = raw.max(), raw.min()
    clip = float(np.mean((np.abs(raw - top) < 1e-9) | (np.abs(raw - bot) < 1e-9)))

    score = 100.0
    if snr_db < 15:
        score -= (15 - snr_db) * 4
    if baseline > 0.2:
        score -= (baseline - 0.2) * 60
    if pl_db > 10:
        score -= min(8.0, pl_db - 10)  # mains is removable by the notch filter -> small penalty
    if flat > 0.01:
        score -= 40
    if clip > 0.005:
        score -= 20
    score = float(np.clip(score, 0, 100))
    label = "good" if score >= 75 else "fair" if score >= 50 else "poor"
    return {
        "score": round(score, 1),
        "label": label,
        "snr_db": float(snr_db),
        "baseline_wander_ratio": float(baseline),
        "powerline_excess_db": float(pl_db),
        "flatline_fraction": flat,
        "clipping_fraction": clip,
    }

# v2
