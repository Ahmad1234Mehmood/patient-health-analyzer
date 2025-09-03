from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("datasets", __name__)


@bp.get("/summary")
def summary():
    ecg_repo = current_app.extensions["ecg_repo"]
    xray_repo = current_app.extensions["xray_repo"]
    history = current_app.extensions["history"]
    ecg = ecg_repo.list_records()
    xr = xray_repo.list_images()

    def mode(items):
        if not items:
            return "empty"
        n_syn = sum(1 for i in items if i.get("source") == "synthetic")
        return "synthetic" if n_syn == len(items) else "real" if n_syn == 0 else "mixed"

    fs_set = sorted({r["fs"] for r in ecg if "fs" in r})
    return jsonify(
        ecg={
            "count": len(ecg),
            "mode": mode(ecg),
            "sampling_rates_hz": fs_set,
            "leads": max((r.get("n_leads", 0) for r in ecg), default=0),
        },
        xray={
            "count": len(xr),
            "mode": mode(xr),
            "with_masks": sum(1 for i in xr if i["has_mask"]),
        },
        history=history.counts(),
        paths={"ecg": str(current_app.extensions["cfg"].ecg_dir), "xray_images": str(current_app.extensions["cfg"].xray_image_dir),
               "xray_masks": str(current_app.extensions["cfg"].xray_mask_dir)},
    )
