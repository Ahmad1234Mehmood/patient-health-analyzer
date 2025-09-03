"""Generate the synthetic demo dataset (28 x 12-lead ECG @ 500 Hz + 40 chest-X-ray phantoms).

    python scripts/generate_synthetic_data.py            # only fills empty folders
    python scripts/generate_synthetic_data.py --force    # regenerate everything
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config, load_config  # noqa: E402
from app.services.ecg import synthetic as ecg_syn  # noqa: E402
from app.services.xray import synthetic as xr_syn  # noqa: E402


def ensure_demo_data(cfg: Config, force: bool = False, n_ecg: int = 28, n_xray: int = 40) -> None:
    has_ecg = any(Path(cfg.ecg_dir).glob("*.hea")) or any(Path(cfg.ecg_dir).glob("*.npz"))
    has_xr = any(p.suffix.lower() in {".png", ".jpg", ".jpeg"} for p in Path(cfg.xray_image_dir).glob("*"))
    if force or not has_ecg:
        ids = ecg_syn.generate_dataset(cfg.ecg_dir, n_records=n_ecg)
        print(f"[data] generated {len(ids)} synthetic 12-lead ECG records in {cfg.ecg_dir}")
    if force or not has_xr:
        ids = xr_syn.generate_dataset(cfg.xray_image_dir, cfg.xray_mask_dir, n_images=n_xray)
        print(f"[data] generated {len(ids)} synthetic chest X-ray phantoms in {cfg.xray_image_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="regenerate even if data already exists")
    ap.add_argument("--n-ecg", type=int, default=28)
    ap.add_argument("--n-xray", type=int, default=40)
    a = ap.parse_args()
    ensure_demo_data(load_config(), a.force, a.n_ecg, a.n_xray)
