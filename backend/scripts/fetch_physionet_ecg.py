"""Download a few open-access 12-lead ECG records (500 Hz) from PhysioNet.

    python scripts/fetch_physionet_ecg.py --n 28            # PTB-XL, 500 Hz version (open access)

Needs internet access to physionet.org.  PTB-XL: https://physionet.org/content/ptb-xl/
Files are stored as WFDB pairs (.hea + .dat) directly in data/ecg/ and appear in the app automatically.
If you already have your own PhysioNet recordings, simply copy the .hea/.dat pairs into data/ecg/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=28, help="number of records")
    ap.add_argument("--clear-synthetic", action="store_true", help="delete SYN-ECG-* files first")
    a = ap.parse_args()
    import wfdb

    cfg = load_config()
    if a.clear_synthetic:
        for f in cfg.ecg_dir.glob("SYN-ECG-*"):
            f.unlink()
        if (cfg.ecg_dir / "manifest.json").exists():
            (cfg.ecg_dir / "manifest.json").unlink()
    cfg.ecg_dir.mkdir(parents=True, exist_ok=True)
    db, ver = "ptb-xl", "1.0.3"
    ok = 0
    for i in range(1, a.n + 1):
        stem = f"{i:05d}_hr"
        sub = f"records500/{(i // 1000) * 1000:05d}/{stem}"
        try:
            wfdb.dl_files(f"{db}/{ver}", str(cfg.ecg_dir), [f"{sub}.hea", f"{sub}.dat"])
            # dl_files keeps the sub-folders; flatten so the app finds them
            src = cfg.ecg_dir / "records500" / f"{(i // 1000) * 1000:05d}"
            for f in src.glob(f"{stem}.*"):
                f.replace(cfg.ecg_dir / f.name)
            ok += 1
            print(f"  downloaded {stem}")
        except Exception as exc:  # network / availability problems
            print(f"  failed {stem}: {exc}")
    print(f"Done: {ok}/{a.n} records in {cfg.ecg_dir}")


if __name__ == "__main__":
    main()
