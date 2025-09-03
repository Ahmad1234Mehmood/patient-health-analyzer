from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.services.ecg import synthetic as ecg_syn  # noqa: E402
from app.services.xray import synthetic as xr_syn  # noqa: E402


@pytest.fixture(scope="session")
def data_dirs(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    ecg_ids = ecg_syn.generate_dataset(root / "ecg", n_records=8)
    xr_ids = xr_syn.generate_dataset(root / "xray" / "images", root / "xray" / "masks", n_images=8)
    return root, ecg_ids, xr_ids


@pytest.fixture()
def client(data_dirs, tmp_path):
    root, _, _ = data_dirs
    cfg = Config(
        environment="testing", port=5000, frontend_url="http://localhost:5173", mains_hz=50.0, max_upload_mb=8,
        data_dir=root, ecg_dir=root / "ecg", xray_image_dir=root / "xray" / "images", xray_mask_dir=root / "xray" / "masks",
        db_path=tmp_path / "h.sqlite3", frontend_dist=tmp_path / "no-dist",
    )
    app = create_app(cfg)
    app.testing = True
    return app.test_client()
