"""Central configuration (read once from environment variables)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend


def _path(env_name: str, default: Path) -> Path:
    value = os.getenv(env_name)
    return Path(value).expanduser().resolve() if value else default


@dataclass(frozen=True)
class Config:
    environment: str
    port: int
    frontend_url: str
    mains_hz: float
    max_upload_mb: int
    data_dir: Path
    ecg_dir: Path
    xray_image_dir: Path
    xray_mask_dir: Path
    db_path: Path
    frontend_dist: Path


def load_config() -> Config:
    data_dir = _path("DATA_DIR", BASE_DIR / "data")
    return Config(
        environment=os.getenv("ENVIRONMENT", "development"),
        port=int(os.getenv("BACKEND_PORT", "5000")),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        mains_hz=float(os.getenv("MAINS_HZ", "50")),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "64")),
        data_dir=data_dir,
        ecg_dir=_path("ECG_DIR", data_dir / "ecg"),
        xray_image_dir=_path("XRAY_IMAGE_DIR", data_dir / "xray" / "images"),
        xray_mask_dir=_path("XRAY_MASK_DIR", data_dir / "xray" / "masks"),
        db_path=_path("DB_PATH", data_dir / "history.sqlite3"),
        frontend_dist=_path("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"),
    )
