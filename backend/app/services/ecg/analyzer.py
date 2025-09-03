"""High-level ECG analysis: ties every step together and returns one JSON-ready dict."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.utils.encoding import decimate_indices, to_jsonable
from app.utils.errors import ApiError

from . import filters
from .autocorr import autocorr_analysis
from .hrv import compute_hrv
from .loader import ECGRecord
from .quality import signal_quality
from .rpeaks import detect_r_peaks
from .spectral import spectrum_analysis

MAX_PLOT_POINTS = 3000


@dataclass
class ECGParams:
    lead: str = "II"
    apply_filter: bool = True
    low_hz: float = 0.5
    high_hz: float = 40.0
    order: int = 4
    notch: bool = True
    mains_hz: float = 50.0
    notch_q: float = 30.0
    start_s: float = 0.0
    duration_s: float | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any], default_mains: float = 50.0) -> "ECGParams":
        def num(key: str, default, cast=float, lo=None, hi=None):
            v = d.get(key, None)
            if v is None or v == "":
                return default
            try:
                v = cast(v)
            except (TypeError, ValueError):
                raise ApiError(f"Parameter '{key}' must be a number", 400)
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                raise ApiError(f"Parameter '{key}' out of range [{lo}, {hi}]", 400)
            return v

        return cls(
            lead=str(d.get("lead") or "II"),
            apply_filter=bool(d.get("apply_filter", True)),
            low_hz=num("low_hz", 0.5, float, 0.01, 100),
            high_hz=num("high_hz", 40.0, float, 1, 200),
            order=num("order", 4, int, 1, 10),
            notch=bool(d.get("notch", True)),
            mains_hz=num("mains_hz", default_mains, float, 40, 70),
            notch_q=num("notch_q", 30.0, float, 5, 100),
            start_s=num("start_s", 0.0, float, 0, None),
            duration_s=num("duration_s", None, float, 1, None),
        )


def _beat_template(x: np.ndarray, peaks: np.ndarray, fs: float, pre_s: float = 0.25, post_s: float = 0.45) -> dict:
    pre, post = int(pre_s * fs), int(post_s * fs)
    beats = [x[p - pre: p + post] for p in peaks if p - pre >= 0 and p + post <= x.size]
    if len(beats) < 2:
        return {"n_beats": len(beats)}
    arr = np.vstack(beats)
    t = (np.arange(-pre, post)) / fs
    idx = decimate_indices(t.size, 400)
    return {"n_beats": len(beats), "t_s": t[idx], "mean_mv": arr.mean(0)[idx], "std_mv": arr.std(0)[idx]}


def _findings(hrv: dict, hr_methods: dict, quality: dict, spectrum: dict, n_beats: int) -> list[dict]:
    f: list[dict] = []
    if quality["label"] == "poor":
        f.append({"level": "alert", "text": f"Poor signal quality (score {quality['score']}). Results below are unreliable."})
    elif quality["label"] == "fair":
        f.append({"level": "warn", "text": f"Fair signal quality (score {quality['score']}). Interpret with care."})
    if spectrum["powerline_excess_db_raw"] > 10:
        f.append({"level": "info", "text": f"Powerline interference detected ({spectrum['powerline_excess_db_raw']:.0f} dB above neighbours at {spectrum['mains_hz']:g} Hz) - removed by the notch filter."})
    if quality["baseline_wander_ratio"] > 0.2:
        f.append({"level": "info", "text": "Strong baseline wander (<0.5 Hz) - removed by the high-pass edge of the band-pass filter."})
    if n_beats < 3 or not hrv.get("valid"):
        f.append({"level": "alert", "text": "Too few beats detected to compute heart rate / HRV."})
        return f
    hr = hrv["hr_bpm"]
    if hr < 50:
        f.append({"level": "warn", "text": f"Heart rate {hr:.0f} bpm is below 50 (bradycardic range)."})
    elif hr > 100:
        f.append({"level": "warn", "text": f"Heart rate {hr:.0f} bpm is above 100 (tachycardic range)."})
    else:
        f.append({"level": "ok", "text": f"Heart rate {hr:.0f} bpm is within the usual resting range (50-100)."})
    if hrv["cv"] > 0.15:
        f.append({"level": "warn", "text": f"RR intervals are irregular (CV {hrv['cv'] * 100:.0f}%). Screening flag only - could be arrhythmia, ectopy or detection errors."})
    vals = [v for v in hr_methods.values() if v]
    if len(vals) >= 2 and (max(vals) - min(vals)) > 10:
        f.append({"level": "info", "text": "Heart-rate estimates from R-peaks / autocorrelation / FFT disagree by >10 bpm - typical for irregular rhythm or noise."})
    return f


def analyze_ecg(rec: ECGRecord, p: ECGParams) -> dict[str, Any]:
    fs = rec.fs
    if p.apply_filter:
        filters.validate_band(p.low_hz, p.high_hz, p.order, fs)
    lead_idx = rec.lead_index(p.lead)

    i0 = int(max(0, p.start_s) * fs)
    i1 = rec.n_samples if p.duration_s is None else min(rec.n_samples, i0 + int(p.duration_s * fs))
    if i1 - i0 < int(2 * fs):
        raise ApiError("Selected window must be at least 2 seconds long", 400)
    seg_all = rec.signal[i0:i1, :]
    raw = seg_all[:, lead_idx]

    if p.apply_filter:
        filt_all = filters.preprocess(seg_all, fs, p.low_hz, p.high_hz, p.order, p.notch, p.mains_hz, p.notch_q)
    else:
        filt_all = seg_all.copy()
    filt = filt_all[:, lead_idx]

    peaks = detect_r_peaks(filt, fs)
    hrv = compute_hrv(peaks, fs)
    spectrum = spectrum_analysis(raw, filt, fs, p.mains_hz)
    ac = autocorr_analysis(filt, fs)
    quality = signal_quality(raw, filt, fs, p.mains_hz, peaks)
    template = _beat_template(filt, peaks, fs)

    hr_methods = {
        "r_peaks": hrv.get("hr_bpm"),
        "autocorrelation": ac["hr_bpm"],
        "fft": spectrum["hr_from_fft_bpm"],
    }

    # ---- per-lead overview (same filter, shared beat times from the selected lead)
    leads_summary = []
    pre = int(0.06 * fs)
    for j, name in enumerate(rec.lead_names):
        r_j, f_j = seg_all[:, j], filt_all[:, j]
        amps = [np.max(np.abs(f_j[max(0, q - pre): q + pre + 1])) for q in peaks]
        noise = r_j - f_j
        pn = np.var(noise)
        leads_summary.append({
            "lead": name,
            "rms_mv": float(np.sqrt(np.mean(f_j ** 2))),
            "peak_to_peak_mv": float(np.ptp(f_j)),
            "r_amplitude_mv": float(np.median(amps)) if amps else None,
            "snr_db": float(10 * np.log10(np.var(f_j) / pn)) if pn > 1e-18 and np.var(f_j) > 0 else None,
        })

    # ---- signal arrays for plotting (thinned)
    t = (np.arange(raw.size) / fs) + i0 / fs
    idx = decimate_indices(raw.size, MAX_PLOT_POINTS)
    peak_info = [{"t_s": float(t[q]), "amp_mv": float(filt[q])} for q in peaks]

    result = {
        "record": rec.summary(),
        "params": {**p.__dict__, "lead": rec.lead_names[lead_idx], "window": [i0 / fs, i1 / fs]},
        "signal": {"t_s": t[idx], "raw_mv": raw[idx], "filtered_mv": filt[idx]},
        "r_peaks": peak_info,
        "hrv": hrv,
        "hr_methods_bpm": hr_methods,
        "spectrum": spectrum,
        "autocorr": {k: v for k, v in ac.items()},
        "quality": quality,
        "template": template,
        "leads_summary": leads_summary,
        "findings": _findings(hrv, hr_methods, quality, spectrum, int(peaks.size)),
        "disclaimer": "Educational/research tool - not a medical device and not a diagnosis.",
    }
    # thin the big arrays that are only used for charts
    ac_idx = decimate_indices(len(ac["lags_s"]), 1500)
    result["autocorr"]["lags_s"] = np.asarray(ac["lags_s"])[ac_idx]
    result["autocorr"]["values"] = np.asarray(ac["values"])[ac_idx]
    return to_jsonable(result)
