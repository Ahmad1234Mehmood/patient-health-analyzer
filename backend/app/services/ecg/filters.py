"""Digital filters for ECG: Butterworth band-pass + mains notch.

Why Butterworth?  It has the flattest possible pass-band (no ripple), so QRS/ST amplitudes are
not distorted by the filter itself.  We build it as *second-order sections* (SOS) because the
direct `b, a` polynomial form becomes numerically unstable for high orders / low cut-offs.

Why zero-phase (`sosfiltfilt`)?  A normal causal filter delays and distorts the waveform
(phase shift), which shifts R-peak timing and changes ST morphology.  Running the filter forward
and then backward cancels the phase shift (the price: the magnitude response is squared, i.e.
the effective order doubles).  This is fine offline - not for real-time monitoring.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from app.utils.errors import ApiError


def validate_band(low_hz: float, high_hz: float, order: int, fs: float) -> None:
    nyq = fs / 2.0
    if not (0 < low_hz < high_hz < nyq):
        raise ApiError(f"Cut-offs must satisfy 0 < low < high < Nyquist ({nyq:g} Hz)", 400)
    if not 1 <= order <= 10:
        raise ApiError("Filter order must be between 1 and 10", 400)


def butter_bandpass_sos(low_hz: float, high_hz: float, fs: float, order: int = 4) -> np.ndarray:
    validate_band(low_hz, high_hz, order, fs)
    return signal.butter(order, [low_hz, high_hz], btype="bandpass", fs=fs, output="sos")


def bandpass(x: np.ndarray, fs: float, low_hz: float = 0.5, high_hz: float = 40.0, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth band-pass along axis 0."""
    sos = butter_bandpass_sos(low_hz, high_hz, fs, order)
    return signal.sosfiltfilt(sos, x, axis=0)


def notch(x: np.ndarray, fs: float, f0: float = 50.0, q: float = 30.0) -> np.ndarray:
    """Zero-phase IIR notch to remove powerline interference at f0 (Q = f0 / bandwidth)."""
    if f0 >= fs / 2:
        return x
    b, a = signal.iirnotch(f0, q, fs=fs)
    return signal.filtfilt(b, a, x, axis=0)


def preprocess(
    x: np.ndarray,
    fs: float,
    low_hz: float = 0.5,
    high_hz: float = 40.0,
    order: int = 4,
    use_notch: bool = True,
    mains_hz: float = 50.0,
    notch_q: float = 30.0,
) -> np.ndarray:
    """Notch first (narrow, surgical) then band-pass (broad)."""
    y = np.asarray(x, dtype=np.float64)
    if use_notch:
        y = notch(y, fs, mains_hz, notch_q)
    return bandpass(y, fs, low_hz, high_hz, order)


def frequency_response(low_hz: float, high_hz: float, order: int, fs: float, n_points: int = 512) -> dict:
    """Magnitude response of the band-pass (single pass and zero-phase = squared)."""
    sos = butter_bandpass_sos(low_hz, high_hz, fs, order)
    w, h = signal.sosfreqz(sos, worN=n_points, fs=fs)
    mag = np.abs(h)
    eps = 1e-12
    return {
        "freqs_hz": w,
        "single_pass_db": 20 * np.log10(mag + eps),
        "zero_phase_db": 40 * np.log10(mag + eps),  # |H|^2 in dB
        "order": order,
        "low_hz": low_hz,
        "high_hz": high_hz,
    }

# ECG pipeline complete

# v2
