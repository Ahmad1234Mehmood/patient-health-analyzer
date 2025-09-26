"""Validate lung segmentation against ground-truth masks (Dice / IoU / sensitivity / specificity / HD95).

    python scripts/evaluate_segmentation.py --method otsu
    python scripts/evaluate_segmentation.py --all-methods --out reports/seg_eval.json

Use this on the real Montgomery images to get *your* numbers, and tune --morph-k / --clahe-clip.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config  # noqa: E402
from app.services.xray.analyzer import XrayParams, evaluate_batch  # noqa: E402
from app.services.xray.loader import XrayRepository  # noqa: E402
from app.services.xray.segmentation import METHODS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", default="otsu", choices=METHODS)
    ap.add_argument("--all-methods", action="store_true")
    ap.add_argument("--max-side", type=int, default=512)
    ap.add_argument("--morph-k", type=int, default=7)
    ap.add_argument("--clahe-clip", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None, help="write full JSON report here")
    a = ap.parse_args()

    cfg = load_config()
    repo = XrayRepository(cfg.xray_image_dir, cfg.xray_mask_dir)
    ids = [i["id"] for i in repo.list_images() if i["has_mask"]][: a.limit]
    if not ids:
        sys.exit("No images with masks found. See docs/DATASETS.md.")
    items = [(i, repo.get_image(i), repo.get_mask(i)) for i in ids]
    reports = {}
    for m in (METHODS if a.all_methods else (a.method,)):
        p = XrayParams(method=m, max_side=a.max_side, morph_k=a.morph_k, clahe_clip=a.clahe_clip)
        t0 = time.time()
        rep = evaluate_batch(items, p)
        reports[m] = rep
        s = rep["summary"]
        print(f"\n[{m}] n={rep['n']}  ({time.time() - t0:.1f}s)")
        for k in ("dice", "iou", "sensitivity", "specificity", "hd95_px"):
            if s[k]:
                print(f"  {k:<12} mean={s[k]['mean']:.4f}  std={s[k]['std']:.4f}  median={s[k]['median']:.4f}  min={s[k]['min']:.4f}")
        print(f"  Dice >= 0.90 in {rep['fraction_dice_above_0_9']:.1%} of images")
        worst = rep["rows"][:3]
        print("  worst:", ", ".join(f"{r['id']} ({r['dice']:.2f})" for r in worst))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(reports, indent=1))
        print(f"\nreport written to {a.out}")


if __name__ == "__main__":
    main()

# v2
