from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.xray.analyzer import XrayParams, evaluate_batch, run_pipeline
from app.utils.errors import ApiError

bp = Blueprint("xray", __name__)


def _repo():
    return current_app.extensions["xray_repo"]


@bp.get("/images")
def list_images():
    return jsonify(images=_repo().list_images())


@bp.get("/images/<image_id>/file")
def image_file(image_id: str):
    return send_file(_repo().raw_file(image_id))


@bp.post("/upload")
def upload():
    f = request.files.get("file")
    if not f:
        raise ApiError("No file received (field name: 'file')", 400)
    rid = _repo().add_upload(f.read())
    return jsonify(image={"id": rid, "has_mask": False, "filename": f.filename}), 201


@bp.post("/analyze")
def analyze():
    body = request.get_json(silent=True) or {}
    image_id = body.get("image_id")
    if not image_id:
        raise ApiError("'image_id' is required", 400)
    repo = _repo()
    img = repo.get_image(image_id)
    gt = repo.get_mask(image_id) if body.get("use_ground_truth", True) else None
    params = XrayParams.from_dict(body)
    result = run_pipeline(img, params, gt)
    result["image_id"] = image_id
    if body.get("save"):
        m, v = result["measurements"], result.get("validation") or {}
        result["saved_id"] = current_app.extensions["history"].add("xray", image_id, {
            "method": params.method, "lung_area_pct": m["lung_area_pct"], "asymmetry_index": m["asymmetry_index"],
            "dice": v.get("dice"), "iou": v.get("iou"),
        })
    return jsonify(result)


@bp.get("/evaluate")
def evaluate():
    """Batch validation against ground-truth masks (Dice / IoU / HD95). Cached per parameter set."""
    args = request.args.to_dict()
    limit = request.args.get("limit", type=int)
    params = XrayParams.from_dict(args)
    repo = _repo()
    imgs = [i for i in repo.list_images() if i["has_mask"]]
    if limit:
        imgs = imgs[:limit]
    key = json.dumps([params.__dict__, [i["id"] for i in imgs]], sort_keys=True, default=str)
    cache = current_app.extensions["eval_cache"]
    if key not in cache:
        items = [(i["id"], repo.get_image(i["id"]), repo.get_mask(i["id"])) for i in imgs]
        cache[key] = evaluate_batch(items, params)
        if len(cache) > 12:
            cache.pop(next(iter(cache)))
    return jsonify(cache[key])
