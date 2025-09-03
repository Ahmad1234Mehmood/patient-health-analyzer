"""Unit tests for the signal-processing building blocks (known-answer tests)."""
from __future__ import annotations

import numpy as np
import pytest

from app.services.ecg import filters
from app.services.ecg.autocorr import autocorr_analysis
from app.services.ecg.hrv import compute_hrv
from app.services.ecg.loader import LEADS_12
from app.services.ecg.rpeaks import detect_r_peaks
from app.services.ecg.spectral import fft_amplitude, spectrum_analysis
from app.services.ecg.synthetic import synth_ecg
from app.utils.errors import ApiError

FS = 500


def test_bandpass_attenuates_out_of_band_and_keeps_in_band():
    t = np.arange(0, 10, 1 / FS)
    drift = np.sin(2 * np.pi * 0.05 * t)       # 0.05 Hz baseline wander (should vanish)
    inband = np.sin(2 * np.pi * 10 * t)        # 10 Hz (QRS band, should stay)
    hf = np.sin(2 * np.pi * 120 * t)           # 120 Hz (should vanish)
    y = filters.bandpass(drift + inband + hf, FS, 0.5, 40, 4)
    core = slice(2 * FS, -2 * FS)              # ignore edge transients of the 0.5 Hz high-pass
    assert np.std(y[core] - inband[core]) < 0.05


def test_notch_removes_mains():
    t = np.arange(0, 10, 1 / FS)
    x = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 8 * t)
    y = filters.notch(x, FS, 50, 30)
    f, a = fft_amplitude(y, FS)
    assert a[np.argmin(abs(f - 50))] < 0.02 and a[np.argmin(abs(f - 8))] > 0.4


def test_filter_validation_rejects_bad_cutoffs():
    with pytest.raises(ApiError):
        filters.validate_band(0.5, 300, 4, FS)       # above Nyquist
    with pytest.raises(ApiError):
        filters.validate_band(40, 0.5, 4, FS)        # low > high
    with pytest.raises(ApiError):
        filters.validate_band(0.5, 40, 0, FS)        # bad order


def test_fft_peak_at_known_frequency():
    t = np.arange(0, 10, 1 / FS)
    f, a = fft_amplitude(np.sin(2 * np.pi * 1.5 * t), FS)
    assert abs(f[np.argmax(a)] - 1.5) < 0.1


def test_autocorrelation_recovers_period():
    t = np.arange(0, 10, 1 / FS)
    x = np.sin(2 * np.pi * 1.2 * t)             # 72 bpm "heart"
    r = autocorr_analysis(x, FS)
    assert abs(r["hr_bpm"] - 72) < 2 and r["regularity"] > 0.9


@pytest.mark.parametrize("hr,rhythm", [(50, "sinus"), (75, "sinus"), (120, "sinus"), (90, "irregular")])
@pytest.mark.parametrize("lead", ["II", "aVR", "V1", "V5"])
def test_rpeak_detection_matches_ground_truth(hr, rhythm, lead):
    sig, truth = synth_ecg(10, FS, hr, rhythm, seed=11)
    x = filters.preprocess(sig[:, LEADS_12.index(lead)], FS)
    peaks = detect_r_peaks(x, FS) / FS
    tp = sum(np.any(np.abs(peaks - r) < 0.05) for r in truth)
    sensitivity = tp / len(truth)
    ppv = tp / max(len(peaks), 1)
    assert sensitivity >= 0.95 and ppv >= 0.95


def test_hrv_known_values():
    peaks = (np.cumsum([0.8] * 12) * FS).astype(int)       # perfectly regular 75 bpm
    h = compute_hrv(peaks, FS)
    assert abs(h["hr_bpm"] - 75) < 0.5 and h["sdnn_ms"] < 5 and h["rmssd_ms"] < 5


def test_spectrum_detects_powerline():
    sig, _ = synth_ecg(10, FS, 70, powerline_mv=0.2, seed=1)
    x = sig[:, 1]
    s = spectrum_analysis(x, filters.preprocess(x, FS), FS, 50.0)
    assert s["powerline_excess_db_raw"] > 10 > s["powerline_excess_db_filtered"] + 0


def test_quality_index_separates_clean_from_noisy():
    from app.services.ecg.quality import signal_quality

    def quality(noise):
        sig, _ = synth_ecg(10, FS, 72, noise_mv=noise, powerline_mv=0.03, seed=8)
        raw = sig[:, 1]
        filt = filters.preprocess(raw, FS)
        return signal_quality(raw, filt, FS, 50.0, detect_r_peaks(filt, FS))

    clean, noisy = quality(0.015), quality(0.12)
    assert clean["label"] == "good" and noisy["score"] < clean["score"] - 20
