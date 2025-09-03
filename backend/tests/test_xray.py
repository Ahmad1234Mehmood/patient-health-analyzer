from __future__ import annotations

import numpy as np

from app.services.xray import edges
from app.services.xray.analyzer import XrayParams, evaluate_batch, run_pipeline
from app.services.xray.metrics import overlap_metrics
from app.services.xray.synthetic import make_phantom


def test_overlap_metrics_known_values():
    a = np.zeros((10, 10), np.uint8); a[:, :5] = 255
    b = np.zeros((10, 10), np.uint8); b[:, :5] = 255
    assert overlap_metrics(a, b)["dice"] > 0.999
    c = np.zeros((10, 10), np.uint8); c[:, 5:] = 255
    m = overlap_metrics(a, c)
    assert m["dice"] < 1e-6 and m["iou"] < 1e-6
    half = np.zeros((10, 10), np.uint8); half[:5, :5] = 255      # 25 of 50 true pixels found
    m = overlap_metrics(half, a)
    assert abs(m["dice"] - 2 * 25 / (25 + 50)) < 1e-6 and abs(m["iou"] - 0.5) < 1e-6


def test_sobel_and_canny_find_a_step_edge():
    img = np.zeros((64, 64), np.uint8); img[:, 32:] = 200
    mag, _ = edges.sobel(img)
    assert mag[:, 30:34].max() > 200 and mag[:, :20].max() == 0
    can, lo, hi = edges.canny(img, 50, 150)
    assert can[:, 30:34].any() and not can[:, :20].any()


def test_all_methods_segment_phantoms_well():
    rng = np.random.default_rng(5)
    for method in ("otsu", "kmeans", "adaptive"):
        dices = []
        for i in range(6):
            img, gt = make_phantom(rng, 512, opacity=(i % 3 == 2))
            r = run_pipeline(img, XrayParams(method=method), gt, with_images=False)
            dices.append(r["validation"]["dice"])
            assert r["measurements"]["n_regions"] == 2
        assert np.mean(dices) > 0.92, (method, dices)


def test_pipeline_returns_all_stage_images_and_measurements():
    img, gt = make_phantom(np.random.default_rng(2), 512)
    r = run_pipeline(img, XrayParams(), gt)
    assert set(r["images"]) == {"original", "enhanced", "sobel", "canny", "mask", "overlay"}
    assert all(v.startswith("data:image/png;base64,") for v in r["images"].values())
    m = r["measurements"]
    assert 8 < m["lung_area_pct"] < 60 and 0 <= m["asymmetry_index"] < 0.5


def test_batch_evaluation_summary():
    rng = np.random.default_rng(9)
    items = []
    for i in range(4):
        img, gt = make_phantom(rng, 512)
        items.append((f"p{i}", img, gt))
    res = evaluate_batch(items, XrayParams())
    assert res["n"] == 4 and res["summary"]["dice"]["mean"] > 0.9
    assert sum(res["dice_histogram"]["counts"]) == 4
