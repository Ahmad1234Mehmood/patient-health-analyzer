"""Synthetic chest X-ray phantoms with exact ground-truth lung masks.

NOT clinical data - a drawn model (torso, two lungs, heart/mediastinum, spine, ribs, clavicles,
noise).  Its value: you can run, test and *validate* the segmentation pipeline immediately, and the
same code path is used later for real MIMIC-CXR / Montgomery images.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


def _blob(shape, cx, cy, rx, ry, rng, wobble=0.06):
    """Ellipse with a smooth low-frequency radial perturbation (organic outline)."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.arctan2((yy - cy) / ry, (xx - cx) / rx)
    r = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    k = rng.uniform(0, 6.28, 3)
    perturb = 1 + wobble * (np.sin(2 * ang + k[0]) + 0.6 * np.sin(3 * ang + k[1]) + 0.4 * np.sin(5 * ang + k[2]))
    return (r <= perturb).astype(np.uint8)


def make_phantom(rng: np.random.Generator, size: int = 512, opacity: bool = False) -> tuple[np.ndarray, np.ndarray]:
    S = size
    shape = (S, S)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    img = np.full(shape, rng.uniform(8, 22), np.float32)                    # air outside the body

    # torso
    body = _blob(shape, S * 0.5, S * 0.55, S * rng.uniform(0.40, 0.44), S * rng.uniform(0.50, 0.55), rng, 0.02)
    img[body > 0] = rng.uniform(135, 160)
    img += body * (xx - S / 2) ** 2 * -0.0003                                # soft shoulder falloff

    # lungs (image-left = patient right, usually slightly larger)
    cy = S * rng.uniform(0.44, 0.48)
    lx = _blob(shape, S * rng.uniform(0.33, 0.36), cy, S * rng.uniform(0.12, 0.15), S * rng.uniform(0.21, 0.25), rng)
    rx = _blob(shape, S * rng.uniform(0.64, 0.67), cy, S * rng.uniform(0.11, 0.14), S * rng.uniform(0.20, 0.24), rng)
    lungs = (lx | rx).astype(np.uint8)

    # heart / mediastinum encroaches on the medial side of the (image-right) lung
    heart = _blob(shape, S * rng.uniform(0.54, 0.58), S * rng.uniform(0.55, 0.60), S * 0.10, S * 0.11, rng, 0.03)
    media = ((np.abs(xx - S * 0.5) < S * 0.045) & (yy > S * 0.18) & (yy < S * 0.8)).astype(np.uint8)
    gt = lungs.copy()
    gt[(heart > 0) | (media > 0)] = 0

    lung_val = rng.uniform(55, 85)
    img[gt > 0] = lung_val
    img[(heart > 0) & (body > 0)] = rng.uniform(175, 200)
    img[(media > 0) & (body > 0)] = rng.uniform(170, 195)

    # texture: ribs (periodic arcs), vessels (smoothed noise), clavicles
    ribs = 7 * np.sin((yy + 0.15 * np.abs(xx - S / 2)) / S * 2 * np.pi * 7.5)
    vessels = cv2.GaussianBlur(rng.normal(0, 1, shape).astype(np.float32), (0, 0), 6) * 40
    img += np.where(gt > 0, ribs + vessels, 0)
    for sgn in (-1, 1):
        cv2.line(img, (int(S / 2), int(S * 0.2)), (int(S / 2 + sgn * S * 0.33), int(S * 0.17)), 190, 5)
    cv2.line(img, (int(S * 0.5), int(S * 0.15)), (int(S * 0.5), int(S * 0.85)), 185, int(S * 0.025))  # spine

    # diaphragm / liver below lungs
    liver = (yy > S * 0.72) & (body > 0)
    img[liver] = np.maximum(img[liver], rng.uniform(165, 185))

    if opacity:  # focal opacity (consolidation / nodule-like) inside one lung
        side = rng.choice([lx, rx])
        ys, xs = np.where((side & gt) > 0)
        if ys.size:
            i = rng.integers(0, ys.size)
            blob = _blob(shape, xs[i], ys[i], S * rng.uniform(0.03, 0.06), S * rng.uniform(0.03, 0.06), rng, 0.15)
            img += blob * np.where(gt > 0, rng.uniform(35, 60), 0)

    img = cv2.GaussianBlur(img, (0, 0), 1.6)
    img = img * rng.uniform(0.9, 1.1) + rng.uniform(-10, 10)
    img += rng.normal(0, 3.5, shape)
    return np.clip(img, 0, 255).astype(np.uint8), (gt * 255).astype(np.uint8)


def generate_dataset(image_dir: Path, mask_dir: Path, n_images: int = 40, size: int = 512, seed: int = 2026) -> list[str]:
    image_dir, mask_dir = Path(image_dir), Path(mask_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    manifest, ids = {}, []
    for i in range(n_images):
        rid = f"SYN-CXR-{i + 1:03d}"
        opacity = i % 4 == 3
        img, mask = make_phantom(rng, size, opacity)
        cv2.imwrite(str(image_dir / f"{rid}.png"), img)
        cv2.imwrite(str(mask_dir / f"{rid}.png"), mask)
        manifest[rid] = {"source": "synthetic", "label": "focal opacity" if opacity else "normal"}
        ids.append(rid)
    (image_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return ids

# v2
