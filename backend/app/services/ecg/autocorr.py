"""Autocorrelation: how similar is the signal to a delayed copy of itself?

An ECG is quasi-periodic (one heartbeat after another).  The autocorrelation function
r[k] = sum_n x[n] x[n+k]  has its first strong peak at the lag k equal to the heartbeat period.
Heart rate = 60 / (lag in seconds).  The *height* of that peak (0..1) measures regularity:
~1 for a metronome-like rhythm, clearly lower for irregular rhythms or noisy signals.
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def autocorrelation(x: np.ndarray, max_lag: int) -> np.ndarray:
    """Unbiased, normalised autocorrelation (value at lag 0 == 1) using FFT-based correlation."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    n = x.size
    full = signal.correlate(x, x, mode="full", method="fft")[n - 1:]
    full = full[: max_lag + 1]
    # unbiased: divide each lag by the number of overlapping samples
    full = full / (n - np.arange(full.size))
    return full / full[0] if full[0] != 0 else full


def autocorr_analysis(
    x: np.ndarray,
    fs: float,
    min_bpm: float = 30.0,
    max_bpm: float = 220.0,
    max_lag_s: float = 3.0,
    lowpass_hz: float | None = 15.0,
) -> dict:
    """ACF-based heart rate + regularity.

    The input is first low-passed at `lowpass_hz` (QRS energy peaks near 10 Hz): a 12 ms-wide R spike
    decorrelates completely if the next beat is only 10 ms off, so without smoothing even a healthy
    sinus rhythm would score a low "regularity".  Typical values: sinus rhythm 0.4-0.8, irregular < 0.25.
    """
    if lowpass_hz and lowpass_hz < fs / 2 * 0.9:
        sos = signal.butter(2, lowpass_hz, btype="lowpass", fs=fs, output="sos")
        x = signal.sosfiltfilt(sos, x)
    max_lag = int(min(x.size - 1, max_lag_s * fs))
    r = autocorrelation(x, max_lag)
    lags_s = np.arange(r.size) / fs

    lo = int(60.0 / max_bpm * fs)
    hi = min(int(60.0 / min_bpm * fs), r.size - 1)
    peak_lag, peak_val = None, None
    if hi > lo + 2:
        seg = r[lo: hi + 1]
        peaks, _ = signal.find_peaks(seg, prominence=0.05)
        if peaks.size:
            # first *significant* peak = fundamental period (later peaks are multiples of it)
            strong = peaks[seg[peaks] >= 0.8 * seg[peaks].max()]
            k = strong[0]
            peak_lag = (lo + k) / fs
            peak_val = float(seg[k])
    return {
        "lags_s": lags_s,
        "values": r,
        "peak_lag_s": peak_lag,
        "peak_value": peak_val,
        "hr_bpm": 60.0 / peak_lag if peak_lag else None,
        "regularity": float(np.clip(peak_val, 0, 1)) if peak_val is not None else None,
    }

# v2
