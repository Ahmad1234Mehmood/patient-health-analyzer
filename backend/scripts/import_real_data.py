"""Import REAL data you downloaded (e.g. from Kaggle) into the app - layout-agnostic.

ECG (PTB-XL or any WFDB 12-lead set; picks the 500 Hz records, 12 leads only):
    python scripts/import_real_data.py ecg --src /path/to/ptb-xl --n 28 --clear-synthetic

Chest X-rays + lung masks (Kaggle "Chest X-ray Masks and Labels", Montgomery, Shenzhen ... any folder tree):
    python scripts/import_real_data.py xray --src /path/to/dataset --max 338 --clear-synthetic

X-ray matching rule: every image file is paired with a mask file whose name contains the same stem
(`X.png` <-> `X_mask.png`, `X.png` <-> `X.png` in a "mask" folder).  Montgomery `leftMask` + `rightMask`
are OR-merged.  Images without a mask are skipped (the app needs masks for Dice).
Datasets are downloaded by you (kaggle CLI / website) - nothing is fetched here.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config  # noqa: E402

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _clear(cfg, kind: str) -> None:
    if kind == "ecg":
        for f in cfg.ecg_dir.glob("SYN-ECG-*"):
            f.unlink()
    else:
        for d in (cfg.xray_image_dir, cfg.xray_mask_dir):
            for f in d.glob("SYN-CXR-*"):
                f.unlink()
        (cfg.xray_image_dir / "manifest.json").unlink(missing_ok=True)


def import_ecg(a, cfg) -> None:
    import wfdb

    heas = sorted(a.src.rglob("*.hea"))
    if not heas:
        sys.exit(f"No .hea files under {a.src}")
    cfg.ecg_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for hea in heas:
        if n >= a.n:
            break
        try:
            h = wfdb.rdheader(str(hea.with_suffix("")))
        except Exception:
            continue
        if h.n_sig != 12 or abs(h.fs - 500) > 1:
            continue  # keep only 12-lead @ 500 Hz (PTB-XL "records500", Chapman, ...)
        stem = hea.stem
        dats = list(hea.parent.glob(stem + ".dat")) + list(hea.parent.glob(stem + ".mat"))
        if not dats:
            continue
        name = f"PTBXL-{stem}" if not stem.startswith(("PTBXL", "JS")) else stem
        shutil.copy2(hea, cfg.ecg_dir / f"{name}.hea")
        for d in dats:
            shutil.copy2(d, cfg.ecg_dir / f"{name}{d.suffix}")
        # the header references the data file by name -> rewrite it
        text = (cfg.ecg_dir / f"{name}.hea").read_text()
        text = re.sub(rf"\b{re.escape(stem)}(\.dat|\.mat)", rf"{name}\1", text)
        text = re.sub(rf"^{re.escape(stem)}\b", name, text, count=1)
        (cfg.ecg_dir / f"{name}.hea").write_text(text)
        n += 1
    print(f"Imported {n} twelve-lead 500 Hz records into {cfg.ecg_dir}")
    if n < a.n:
        print(f"  only {n} found: for PTB-XL use the 'records500' folder (the 100 Hz copies are skipped).")


def _stem(p: Path) -> str:
    s = p.stem.lower()
    return re.sub(r"[_\-]?(mask|seg|label)s?$", "", s)


def import_xray(a, cfg) -> None:
    files = [p for p in a.src.rglob("*") if p.suffix.lower() in IMG_EXT]
    is_mask = lambda p: any(k in str(p.relative_to(a.src)).lower() for k in ("mask", "seg", "label"))  # noqa: E731
    masks: dict[str, list[Path]] = {}
    images: list[Path] = []
    for p in files:
        if is_mask(p):
            masks.setdefault(_stem(p), []).append(p)
        else:
            images.append(p)
    cfg.xray_image_dir.mkdir(parents=True, exist_ok=True)
    cfg.xray_mask_dir.mkdir(parents=True, exist_ok=True)
    n = skipped = 0
    for img in sorted(images):
        if n >= a.max:
            break
        ms = masks.get(_stem(img))
        if not ms:
            skipped += 1
            continue
        merged = None
        for m in ms:
            arr = cv2.imread(str(m), cv2.IMREAD_GRAYSCALE)
            if arr is None:
                continue
            arr = arr > 127
            merged = arr if merged is None else (merged | arr if merged.shape == arr.shape else merged)
        if merged is None or merged.mean() < 0.02:
            skipped += 1
            continue
        out = f"{_stem(img).upper()}.png"
        pic = cv2.imread(str(img), cv2.IMREAD_GRAYSCALE)
        if pic is None:
            skipped += 1
            continue
        if pic.shape != merged.shape:  # some sets ship masks at another resolution
            merged = cv2.resize(merged.astype(np.uint8), (pic.shape[1], pic.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        cv2.imwrite(str(cfg.xray_image_dir / out), pic)
        cv2.imwrite(str(cfg.xray_mask_dir / out), merged.astype(np.uint8) * 255)
        n += 1
    print(f"Imported {n} images with masks ({skipped} skipped: no/empty mask) into {cfg.xray_image_dir.parent}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="kind", required=True)
    e = sub.add_parser("ecg"); e.add_argument("--src", type=Path, required=True); e.add_argument("--n", type=int, default=28)
    x = sub.add_parser("xray"); x.add_argument("--src", type=Path, required=True); x.add_argument("--max", type=int, default=338)
    for s in (e, x):
        s.add_argument("--clear-synthetic", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    if not a.src.exists():
        sys.exit(f"Folder not found: {a.src}")
    if a.clear_synthetic:
        _clear(cfg, a.kind)
    (import_ecg if a.kind == "ecg" else import_xray)(a, cfg)


if __name__ == "__main__":
    main()
