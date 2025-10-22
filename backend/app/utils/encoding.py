"""JSON-safe conversion of NumPy objects and image -> base64 helpers."""
from __future__ import annotations

import base64
import math
from typing import Any

import cv2
import numpy as np


def to_jsonable(obj: Any, ndigits: int = 5) -> Any:
    """Recursively convert NumPy scalars/arrays to plain Python (NaN/inf -> None)."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v, ndigits) for v in obj]
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist(), ndigits)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, ndigits)
    return obj


def png_data_url(img: np.ndarray) -> str:
    """Encode an 8-bit gray/BGR image as a `data:image/png;base64,...` string."""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def decimate_indices(n: int, max_points: int) -> np.ndarray:
    """Evenly spaced indices used to thin long signals before sending them to the browser."""
    if n <= max_points:
        return np.arange(n)
    return np.unique(np.linspace(0, n - 1, max_points).astype(int))

# v2
