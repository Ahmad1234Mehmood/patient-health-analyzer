"""Benchmark the R-peak detector against ground-truth beat times stored in data/ecg/manifest.json.

    python scripts/evaluate_ecg.py [--lead II] [--tol-ms 50]

Works on the synthetic set (ground truth known exactly). For real PhysioNet records that come with
annotation files you can extend this script with `wfdb.rdann`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config  # noqa: E402
from app.services.ecg import filters  # noqa: E402
from app.services.ecg.loader import ECGRepository  # noqa: E402
from app.services.ecg.rpeaks import detect_r_peaks  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lead", default="II")
    ap.add_argument("--tol-ms", type=float, default=50.0)
    a = ap.parse_args()
    cfg = load_config()
    repo = ECGRepository(cfg.ecg_dir)
    manifest = json.loads((cfg.ecg_dir / "manifest.json").read_text()) if (cfg.ecg_dir / "manifest.json").exists() else {}
    rows = []
    for info in repo.list_records():
        truth = manifest.get(info["id"], {}).get("r_times")
        if not truth:
            continue
        rec = repo.get(info["id"])
        x = filters.preprocess(rec.signal[:, rec.lead_index(a.lead)], rec.fs, mains_hz=cfg.mains_hz)
        pk = detect_r_peaks(x, rec.fs) / rec.fs
        tp = sum(bool(np.any(np.abs(pk - r) < a.tol_ms / 1000)) for r in truth)
        se, ppv = tp / len(truth), tp / max(len(pk), 1)
        hr_err = abs(60 / np.mean(np.diff(pk)) - 60 / np.mean(np.diff(truth))) if len(pk) > 2 else float("nan")
        rows.append((info["id"], len(truth), len(pk), se, ppv, hr_err))
        print(f"{info['id']:<12} beats={len(truth):>3} det={len(pk):>3}  Se={se:6.1%}  PPV={ppv:6.1%}  |dHR|={hr_err:5.2f} bpm")
    if rows:
        arr = np.array([r[3:] for r in rows], float)
        print("-" * 70)
        print(f"{len(rows)} records | mean Se={arr[:, 0].mean():.2%}  mean PPV={arr[:, 1].mean():.2%}  mean |dHR|={np.nanmean(arr[:, 2]):.2f} bpm")
    else:
        print("No records with ground-truth beat times found (manifest.json missing).")


if __name__ == "__main__":
    main()

# v2
