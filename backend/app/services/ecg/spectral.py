"""Frequency-domain analysis: FFT amplitude spectrum, Welch PSD, band powers, powerline check.

FFT  : decomposes the signal into sinusoids.  Peaks show *which* frequencies carry energy
       (heart-rate fundamental ~1-2 Hz, QRS energy ~5-15 Hz, mains interference at 50/60 Hz).
Welch: averages the periodograms of overlapping, windowed segments -> a much smoother and
       statistically more reliable estimate of the Power Spectral Density (PSD).
"""
from __future__ import annotations

import numpy as np
from scipy import signal

_trapz = getattr(np, "trapezoid", None) or np.trapz  # np.trapezoid exists in NumPy >= 2.0

# Physiologically motivated bands (Hz)
BANDS = {
    "baseline_wander": (0.0, 0.5),
    "p_t_waves": (0.5, 5.0),
    "qrs": (5.0, 15.0),
    "high_freq": (15.0, 40.0),
    "noise": (40.0, 250.0),
}


def fft_amplitude(x: np.ndarray, fs: float, fmax: float = 60.0) -> tuple[np.ndarray, np.ndarray]:
    """Single-sided amplitude spectrum (Hann window to limit spectral leakage)."""
    x = np.asarray(x, dtype=np.float64) - np.mean(x)
    w = np.hanning(x.size)
    spec = np.fft.rfft(x * w)
    amp = 2.0 * np.abs(spec) / np.sum(w)
    f = np.fft.rfftfreq(x.size, d=1.0 / fs)
    keep = f <= fmax
    return f[keep], amp[keep]


def welch_psd(x: np.ndarray, fs: float, seg_s: float = 4.0, fmax: float = 100.0) -> tuple[np.ndarray, np.ndarray]:
    nper = int(min(x.size, seg_s * fs))
    f, p = signal.welch(x, fs=fs, window="hann", nperseg=nper, noverlap=nper // 2, detrend="constant")
    keep = f <= fmax
    return f[keep], p[keep]


def band_powers(f: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """Relative power (0-1) in each band; integrates the PSD with the trapezoid rule."""
    total = _trapz(p, f)
    out = {}
    for name, (lo, hi) in BANDS.items():
        m = (f >= lo) & (f < hi)
        val = _trapz(p[m], f[m]) if m.sum() > 1 else 0.0
        out[name] = float(val / total) if total > 0 else 0.0
    return out


def powerline_excess_db(f: np.ndarray, p: np.ndarray, mains_hz: float) -> float:
    """How many dB the PSD at the mains frequency stands above its spectral neighbours."""
    if mains_hz >= f[-1]:
        return 0.0
    at = (f >= mains_hz - 1.0) & (f <= mains_hz + 1.0)
    near = ((f >= mains_hz - 8) & (f < mains_hz - 3)) | ((f > mains_hz + 3) & (f <= mains_hz + 8))
    if not at.any() or not near.any():
        return 0.0
    return float(10 * np.log10((p[at].max() + 1e-18) / (np.median(p[near]) + 1e-18)))


def spectrum_analysis(raw: np.ndarray, filtered: np.ndarray, fs: float, mains_hz: float) -> dict:
    f_fft, amp = fft_amplitude(filtered, fs)
    f_w, p_raw = welch_psd(raw, fs)
    _, p_filt = welch_psd(filtered, fs)
    bp_raw = band_powers(f_w, p_raw)
    bp_filt = band_powers(f_w, p_filt)

    # Heart-rate fundamental: strongest spectral line in 0.7-3.5 Hz (42-210 bpm) of the filtered ECG
    m = (f_fft >= 0.7) & (f_fft <= 3.5)
    dom = float(f_fft[m][np.argmax(amp[m])]) if m.any() else float("nan")
    # decimate PSD for plotting
    to_db = lambda p: 10 * np.log10(p + 1e-18)  # noqa: E731
    return {
        "fft": {"freqs_hz": f_fft, "amplitude_mv": amp},
        "psd": {"freqs_hz": f_w, "raw_db": to_db(p_raw), "filtered_db": to_db(p_filt)},
        "band_power_raw": bp_raw,
        "band_power_filtered": bp_filt,
        "dominant_hz": dom,
        "hr_from_fft_bpm": dom * 60.0 if np.isfinite(dom) else None,
        "powerline_excess_db_raw": powerline_excess_db(f_w, p_raw, mains_hz),
        "powerline_excess_db_filtered": powerline_excess_db(f_w, p_filt, mains_hz),
        "mains_hz": mains_hz,
    }
