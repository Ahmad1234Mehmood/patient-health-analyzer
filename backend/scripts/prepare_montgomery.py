"""Import the Montgomery County TB chest X-ray set (images + merged lung masks).

Download (free, no login): https://data.lhncbc.nlm.nih.gov/public/Tuberculosis-Chest-X-ray-Datasets/Montgomery-County-CXR-Set/MontgomerySet.zip
Unzip it, then run:

    python scripts/prepare_montgomery.py --src /path/to/MontgomerySet

Expected layout inside --src:
    CXR_png/MCUCXR_0001_0.png ...
    ManualMask/leftMask/MCUCXR_0001_0.png ...
    ManualMask/rightMask/MCUCXR_0001_0.png ...

Left and right masks are OR-merged into one binary lung mask per image.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--clear-synthetic", action="store_true", help="delete SYN-CXR-* files first")
    a = ap.parse_args()
    cfg = load_config()
    imgs_dir = a.src / "CXR_png"
    left_dir, right_dir = a.src / "ManualMask" / "leftMask", a.src / "ManualMask" / "rightMask"
    for d in (imgs_dir, left_dir, right_dir):
        if not d.exists():
            sys.exit(f"Missing folder: {d}")
    if a.clear_synthetic:
        for d in (cfg.xray_image_dir, cfg.xray_mask_dir):
            for f in d.glob("SYN-CXR-*"):
                f.unlink()
        m = cfg.xray_image_dir / "manifest.json"
        if m.exists():
            m.unlink()
    cfg.xray_image_dir.mkdir(parents=True, exist_ok=True)
    cfg.xray_mask_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for img_path in sorted(imgs_dir.glob("*.png")):
        l, r = left_dir / img_path.name, right_dir / img_path.name
        if not (l.exists() and r.exists()):
            print(f"  skip {img_path.name}: mask missing")
            continue
        ml, mr = cv2.imread(str(l), cv2.IMREAD_GRAYSCALE), cv2.imread(str(r), cv2.IMREAD_GRAYSCALE)
        merged = ((ml > 127) | (mr > 127)).astype(np.uint8) * 255
        shutil.copy2(img_path, cfg.xray_image_dir / img_path.name)
        cv2.imwrite(str(cfg.xray_mask_dir / img_path.name), merged)
        n += 1
    print(f"Imported {n} Montgomery images + merged masks into {cfg.xray_image_dir.parent}")


if __name__ == "__main__":
    main()
