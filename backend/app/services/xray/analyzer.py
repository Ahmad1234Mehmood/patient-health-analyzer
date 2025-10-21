"""One call = full chest X-ray pipeline: enhance -> edges -> segment -> measure -> (validate)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from app.utils.encoding import png_data_url, to_jsonable
from app.utils.errors import ApiError

from . import edges as edge_ops
from . import preprocess as pre
from .metrics import lung_measurements, overlap_metrics
from .segmentation import METHODS, segment_lungs, split_left_right


@dataclass
class XrayParams:
    method: str = "otsu"
    max_side: int = 512
    clahe_clip: float = 2.0
    clahe_tile: int = 8
    blur_k: int = 5
    sobel_ksize: int = 3
    canny_low: float | None = None
    canny_high: float | None = None
    morph_k: int = 7
    min_area_pct: float = 1.0
    invert: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "XrayParams":
        def num(key, default, cast=float, lo=None, hi=None):
            v = d.get(key)
            if v is None or v == "":
                return default
            try:
                v = cast(v)
            except (TypeError, ValueError):
                raise ApiError(f"Parameter '{key}' must be a number", 400)
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                raise ApiError(f"Parameter '{key}' out of range [{lo}, {hi}]", 400)
            return v

        method = str(d.get("method") or "otsu")
        if method not in METHODS:
            raise ApiError(f"method must be one of {', '.join(METHODS)}", 400)
        return cls(
            method=method,
            max_side=num("max_side", 512, int, 128, 1024),
            clahe_clip=num("clahe_clip", 2.0, float, 0.5, 10),
            clahe_tile=num("clahe_tile", 8, int, 2, 32),
            blur_k=num("blur_k", 5, int, 0, 21),
            sobel_ksize=num("sobel_ksize", 3, int, 1, 7),
            canny_low=num("canny_low", None, float, 0, 255),
            canny_high=num("canny_high", None, float, 0, 255),
            morph_k=num("morph_k", 7, int, 3, 31),
            min_area_pct=num("min_area_pct", 1.0, float, 0.1, 20),
            invert=str(d.get("invert", False)).lower() in ("1", "true", "yes"),
        )


def _overlay(base: np.ndarray, mask: np.ndarray, gt: np.ndarray | None) -> np.ndarray:
    bgr = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    tint = bgr.copy()
    tint[mask > 0] = (120, 220, 90)           # BGR green fill
    out = cv2.addWeighted(tint, 0.35, bgr, 0.65, 0)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, cnts, -1, (230, 200, 40), 2)       # predicted: cyan-ish
    if gt is not None:
        gcnts, _ = cv2.findContours(gt, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, gcnts, -1, (200, 60, 230), 2)  # ground truth: magenta
    return out


def run_pipeline(original: np.ndarray, p: XrayParams, gt_mask: np.ndarray | None = None, with_images: bool = True) -> dict[str, Any]:
    img = pre.resize_max_side(original, p.max_side)
    if p.invert:  # e.g. DICOM MONOCHROME1 exports (air is white)
        img = 255 - img
    enh = pre.enhance(img, p.clahe_clip, p.clahe_tile, p.blur_k)
    sob, _ = edge_ops.sobel(enh, p.sobel_ksize)
    can, c_lo, c_hi = edge_ops.canny(enh, p.canny_low, p.canny_high)
    mask, seg_info = segment_lungs(enh, p.method, p.morph_k, p.min_area_pct)
    left, right = split_left_right(mask)

    result: dict[str, Any] = {
        "params": p.__dict__,
        "segmentation": {**seg_info, "canny_low": c_lo, "canny_high": c_hi},
        "measurements": lung_measurements(img, mask, can, left, right),
        "histogram": {"original": pre.histogram(img), "enhanced": pre.histogram(enh)},
        "warnings": [],
    }
    if seg_info["n_components"] < 2:
        result["warnings"].append("Fewer than two lung regions found - try another method or lower 'min area'.")
    if result["measurements"]["lung_area_pct"] < 8:
        result["warnings"].append("Segmented lung area is very small - the image may be low-contrast or inverted.")

    gt_resized = None
    if gt_mask is not None:
        gt_resized = cv2.resize(gt_mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
        result["validation"] = overlap_metrics(mask, gt_resized)

    if with_images:
        result["images"] = {
            "original": png_data_url(img),
            "enhanced": png_data_url(enh),
            "sobel": png_data_url(sob),
            "canny": png_data_url(can),
            "mask": png_data_url(mask),
            "overlay": png_data_url(_overlay(img, mask, gt_resized)),
        }
    return to_jsonable(result)


def evaluate_batch(items: list[tuple[str, np.ndarray, np.ndarray]], p: XrayParams) -> dict[str, Any]:
    """items = [(id, image, gt_mask)] -> per-image metrics + summary statistics."""
    rows = []
    for rid, img, gt in items:
        res = run_pipeline(img, p, gt, with_images=False)
        v = res["validation"]
        rows.append({"id": rid, **{k: v[k] for k in ("dice", "iou", "sensitivity", "specificity", "hd95_px")}, "n_regions": res["measurements"]["n_regions"]})
    if not rows:
        return {"n": 0, "rows": [], "summary": None}
    summary = {}
    for k in ("dice", "iou", "sensitivity", "specificity", "hd95_px"):
        vals = np.array([r[k] for r in rows if r[k] is not None], dtype=float)
        summary[k] = {"mean": vals.mean(), "std": vals.std(), "median": np.median(vals), "min": vals.min(), "max": vals.max()} if vals.size else None
    dice = np.array([r["dice"] for r in rows])
    hist, edges_ = np.histogram(dice, bins=10, range=(0, 1))
    return to_jsonable({
        "n": len(rows),
        "rows": sorted(rows, key=lambda r: r["dice"]),
        "summary": summary,
        "dice_histogram": {"bins": [f"{edges_[i]:.1f}-{edges_[i + 1]:.1f}" for i in range(10)], "counts": hist},
        "fraction_dice_above_0_9": float(np.mean(dice >= 0.9)),
        "params": p.__dict__,
    })

# v2
