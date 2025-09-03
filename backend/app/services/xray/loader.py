"""Chest X-ray loading (PNG/JPG/TIFF/BMP) with optional ground-truth lung masks.

Dataset conventions
-------------------
* images : data/xray/images/<id>.png|jpg
* masks  : data/xray/masks/<id>.png          (binary lung mask, same stem)
           also accepted: <id>_mask.png

Montgomery County TB set ships *separate* left/right masks - merge them first with
`python scripts/prepare_montgomery.py` (see docs/DATASETS.md).
"""
from __future__ import annotations

import json
import re
import secrets
from collections import OrderedDict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.utils.errors import ApiError

IMG_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


def to_uint8_gray(img: np.ndarray) -> np.ndarray:
    """Any depth / channel count -> 8-bit grayscale (16-bit medical PNGs are min-max rescaled)."""
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    if img.dtype == np.uint8:
        return img
    img = img.astype(np.float64)
    lo, hi = np.percentile(img, [0.5, 99.5])
    if hi <= lo:
        hi = lo + 1
    return np.clip((img - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)


def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ApiError("Could not decode image (supported: PNG, JPG, TIFF, BMP)", 415, "unsupported")
    return to_uint8_gray(img)


class XrayRepository:
    def __init__(self, image_dir: Path, mask_dir: Path, max_uploads: int = 8):
        self.image_dir, self.mask_dir = Path(image_dir), Path(mask_dir)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.mask_dir.mkdir(parents=True, exist_ok=True)
        self._uploads: "OrderedDict[str, np.ndarray]" = OrderedDict()
        self._max_uploads = max_uploads

    # ---------------------------------------------------------------- helpers
    def _image_path(self, image_id: str) -> Path | None:
        if not _SAFE_ID.match(image_id or ""):
            raise ApiError("Invalid image id", 400)
        for p in self.image_dir.iterdir():
            if p.stem == image_id and p.suffix.lower() in IMG_EXT:
                return p
        return None

    def _mask_path(self, image_id: str) -> Path | None:
        for name in (image_id, f"{image_id}_mask"):
            for p in self.mask_dir.glob(f"{name}.*"):
                if p.suffix.lower() in IMG_EXT:
                    return p
        return None

    def _manifest(self) -> dict[str, Any]:
        p = self.image_dir / "manifest.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    # ---------------------------------------------------------------- listing
    def list_images(self) -> list[dict[str, Any]]:
        man = self._manifest()
        masks = {p.stem.removesuffix("_mask") for p in self.mask_dir.iterdir() if p.suffix.lower() in IMG_EXT}
        out = []
        for p in sorted(self.image_dir.iterdir()):
            if p.suffix.lower() in IMG_EXT:
                out.append({"id": p.stem, "has_mask": p.stem in masks, "filename": p.name, **man.get(p.stem, {})})
        return out

    # ---------------------------------------------------------------- reading
    def get_image(self, image_id: str) -> np.ndarray:
        if image_id in self._uploads:
            self._uploads.move_to_end(image_id)
            return self._uploads[image_id]
        path = self._image_path(image_id)
        if path is None:
            raise ApiError(f"Image '{image_id}' not found", 404, "not_found")
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ApiError(f"Could not read image '{image_id}'", 422, "bad_image")
        return to_uint8_gray(img)

    def get_mask(self, image_id: str) -> np.ndarray | None:
        if image_id in self._uploads:
            return None
        path = self._mask_path(image_id)
        if path is None:
            return None
        m = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if m is None:
            return None
        m = to_uint8_gray(m)
        return (m > 127).astype(np.uint8) * 255

    def raw_file(self, image_id: str) -> Path:
        path = self._image_path(image_id)
        if path is None:
            raise ApiError("Image not found", 404, "not_found")
        return path

    def add_upload(self, data: bytes) -> str:
        img = decode_image(data)
        rid = f"upload-{secrets.token_hex(3)}"
        self._uploads[rid] = img
        while len(self._uploads) > self._max_uploads:
            self._uploads.popitem(last=False)
        return rid
