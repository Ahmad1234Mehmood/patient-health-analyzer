"""Synthetic 12-lead ECG generator (for demos, tests and running without credentialed data).

IMPORTANT: this is NOT clinical data.  It uses a sum-of-Gaussians beat model (P, Q, R, S, T waves)
with a per-lead gain table, plus realistic artefacts (baseline wander, powerline hum, muscle noise).
Because we know the true beat times, the R-peak detector can be *quantitatively* tested.
The real project data (PhysioNet) is read by the exact same loader - see docs/DATASETS.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .loader import LEADS_12

# wave: (offset_s from R, amplitude_mV, width_s)
_WAVES = {
    "P": (-0.165, 0.14, 0.028),
    "Q": (-0.028, -0.12, 0.011),
    "R": (0.000, 1.10, 0.013),
    "S": (0.030, -0.26, 0.013),
    "T": (0.250, 0.32, 0.048),
}
# per-lead multipliers for (P, Q, R, S, T) - a coarse model of the frontal/horizontal-plane projections
_LEAD_GAIN = {
    "I":   (0.8, 0.6, 0.70, 0.5, 0.8),
    "II":  (1.0, 1.0, 1.00, 1.0, 1.0),
    "III": (0.4, 0.5, 0.35, 0.6, 0.3),
    "aVR": (-0.8, -0.8, -0.70, -0.8, -0.8),
    "aVL": (0.3, 0.3, 0.40, 0.5, 0.4),
    "aVF": (0.8, 0.8, 0.70, 0.8, 0.7),
    "V1":  (0.3, 0.1, 0.25, 3.5, 0.2),
    "V2":  (0.4, 0.2, 0.50, 3.0, 0.9),
    "V3":  (0.5, 0.3, 0.80, 2.0, 0.9),
    "V4":  (0.6, 0.5, 1.30, 1.0, 0.9),
    "V5":  (0.6, 0.6, 1.20, 0.4, 0.7),
    "V6":  (0.6, 0.6, 1.00, 0.2, 0.6),
}


def _beat_times(rng: np.random.Generator, duration: float, hr: float, rhythm: str) -> np.ndarray:
    mean_rr = 60.0 / hr
    t, times = rng.uniform(0.2, 0.6), []
    while t < duration - 0.3:
        times.append(t)
        if rhythm == "irregular":                       # AF-like: erratic RR, no P wave
            rr = mean_rr * rng.uniform(0.55, 1.45)
        else:                                           # sinus rhythm with mild respiratory variability
            rr = mean_rr * (1 + 0.04 * np.sin(2 * np.pi * 0.25 * t) + rng.normal(0, 0.015))
        t += rr
    return np.asarray(times)


def synth_ecg(
    duration: float = 10.0,
    fs: int = 500,
    hr: float = 72.0,
    rhythm: str = "sinus",
    noise_mv: float = 0.015,
    baseline_mv: float = 0.12,
    powerline_mv: float = 0.03,
    mains_hz: float = 50.0,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (signal[n, 12] in mV, true R-peak times in seconds)."""
    rng = np.random.default_rng(seed)
    n = int(duration * fs)
    t = np.arange(n) / fs
    r_times = _beat_times(rng, duration, hr, rhythm)
    sig = np.zeros((n, 12))
    amp_jitter = rng.normal(1.0, 0.03, r_times.size)
    for j, lead in enumerate(LEADS_12):
        g = dict(zip("PQRST", _LEAD_GAIN[lead]))
        for bt, aj in zip(r_times, amp_jitter):
            # QT shortens with heart rate: scale T offset ~ sqrt(RR)
            for w, (off, amp, width) in _WAVES.items():
                if w == "P" and rhythm == "irregular":
                    continue
                off_s = off * (np.sqrt(60.0 / hr) if w == "T" else 1.0)
                sig[:, j] += g[w] * amp * aj * np.exp(-0.5 * ((t - bt - off_s) / width) ** 2)
        # artefacts: slow baseline wander (respiration / movement), mains hum, broadband noise
        f1, f2 = rng.uniform(0.12, 0.25), rng.uniform(0.3, 0.45)
        sig[:, j] += baseline_mv * (np.sin(2 * np.pi * f1 * t + rng.uniform(0, 6.28)) + 0.5 * np.sin(2 * np.pi * f2 * t + rng.uniform(0, 6.28)))
        sig[:, j] += powerline_mv * np.sin(2 * np.pi * mains_hz * t + rng.uniform(0, 6.28))
        sig[:, j] += rng.normal(0, noise_mv, n)
    return sig, r_times


def generate_dataset(out_dir: Path, n_records: int = 28, fs: int = 500, duration: float = 10.0, seed: int = 2026) -> list[str]:
    """Write `n_records` WFDB files (+ manifest.json with ground truth) into out_dir."""
    import wfdb

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    hr_grid = np.linspace(48, 128, n_records)
    rng.shuffle(hr_grid)
    manifest: dict[str, Any] = {}
    ids = []
    for i in range(n_records):
        rid = f"SYN-ECG-{i + 1:03d}"
        rhythm = "irregular" if i % 7 == 3 else "sinus"
        noisy = i % 9 == 5
        wander = i % 11 == 7
        hr = float(round(hr_grid[i], 1))
        sig, r_times = synth_ecg(
            duration, fs, hr, rhythm,
            noise_mv=0.08 if noisy else 0.015,
            baseline_mv=0.45 if wander else 0.12,
            powerline_mv=0.10 if noisy else 0.03,
            seed=int(rng.integers(0, 2**31 - 1)),
        )
        true_hr = 60.0 / float(np.mean(np.diff(r_times)))
        wfdb.wrsamp(
            rid, fs=fs, units=["mV"] * 12, sig_name=LEADS_12, p_signal=sig,
            fmt=["16"] * 12, write_dir=str(out_dir),
            comments=["SYNTHETIC - not clinical data", f"rhythm={rhythm}", f"hr_true={true_hr:.1f}"],
        )
        manifest[rid] = {
            "source": "synthetic",
            "label": ("irregular (AF-like)" if rhythm == "irregular" else "sinus") + (" + heavy noise" if noisy else "") + (" + strong wander" if wander else ""),
            "rhythm": rhythm,
            "hr_true": round(true_hr, 1),
            "r_times": [round(float(x), 4) for x in r_times],
        }
        ids.append(rid)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return ids

# v2
