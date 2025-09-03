"""Segmentation validation metrics + lung measurements.

Overlap metrics compare a predicted mask P with a ground-truth mask G (both boolean):
  Dice  = 2|P∩G| / (|P|+|G|)        (F1 of the pixels; 1 = perfect)
  IoU   = |P∩G| / |P∪G|             (Jaccard; always <= Dice)
  Sens. = TP / (TP+FN)              (how much of the true lung we found)
  Spec. = TN / (TN+FP)              (how well we avoided non-lung)
  HD95  = 95th percentile of boundary-to-boundary distances (pixels) - robust version of Hausdorff
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage as ndi


def _boundary(m: np.ndarray) -> np.ndarray:
    m = m.astype(bool)
    return m & ~ndi.binary_erosion(m, iterations=1)


def hd95(pred: np.ndarray, gt: np.ndarray) -> float | None:
    p, g = _boundary(pred), _boundary(gt)
    if not p.any() or not g.any():
        return None
    d_to_g = ndi.distance_transform_edt(~g)
    d_to_p = ndi.distance_transform_edt(~p)
    d = np.concatenate([d_to_g[p], d_to_p[g]])
    return float(np.percentile(d, 95))


def overlap_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray, with_hd: bool = True) -> dict:
    p, g = pred_mask > 0, gt_mask > 0
    tp = int(np.sum(p & g))
    fp = int(np.sum(p & ~g))
    fn = int(np.sum(~p & g))
    tn = int(np.sum(~p & ~g))
    eps = 1e-9
    out = {
        "dice": 2 * tp / (2 * tp + fp + fn + eps),
        "iou": tp / (tp + fp + fn + eps),
        "sensitivity": tp / (tp + fn + eps),
        "specificity": tn / (tn + fp + eps),
        "precision": tp / (tp + fp + eps),
        "pixel_accuracy": (tp + tn) / (tp + tn + fp + fn),
    }
    if with_hd:
        out["hd95_px"] = hd95(p, g)
    return out


def _entropy(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    hist = np.bincount(values.ravel(), minlength=256).astype(np.float64)
    p = hist / hist.sum()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def lung_measurements(original: np.ndarray, mask: np.ndarray, edges: np.ndarray, left: np.ndarray, right: np.ndarray) -> dict:
    """Simple, explainable image-derived measurements (NOT diagnostic)."""
    h, w = mask.shape
    m = mask > 0
    area = int(m.sum())
    a_l, a_r = int((left > 0).sum()), int((right > 0).sum())
    out = {
        "lung_area_px": area,
        "lung_area_pct": 100.0 * area / (h * w),
        "area_right_lung_px": a_l,   # image-left = patient's right lung
        "area_left_lung_px": a_r,
        "asymmetry_index": abs(a_l - a_r) / max(a_l + a_r, 1),
        "n_regions": int(cv2.connectedComponents((mask > 0).astype(np.uint8))[0] - 1),
        "image_size": [int(w), int(h)],
    }
    if area:
        ys, xs = np.where(m)
        out["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        vals = original[m]
        out["lung_mean_intensity"] = float(vals.mean())
        out["lung_std_intensity"] = float(vals.std())
        out["lung_entropy_bits"] = _entropy(vals)
        out["edge_density_in_lung"] = float((edges[m] > 0).mean())
        out["thoracic_width_px"] = int(xs.max() - xs.min() + 1)
        out["lung_height_px"] = int(ys.max() - ys.min() + 1)
    return out
