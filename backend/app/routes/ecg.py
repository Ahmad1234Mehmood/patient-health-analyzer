from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.services.ecg import filters
from app.services.ecg.analyzer import ECGParams, analyze_ecg
from app.utils.encoding import to_jsonable
from app.utils.errors import ApiError

bp = Blueprint("ecg", __name__)


def _repo():
    return current_app.extensions["ecg_repo"]


@bp.get("/records")
def list_records():
    return jsonify(records=_repo().list_records())


@bp.post("/upload")
def upload():
    """Accepts multipart: one .csv/.npy/.npz (+ optional `fs`), or a WFDB .hea + .dat pair."""
    files = {f.filename: f.read() for f in request.files.getlist("files") if f and f.filename}
    if not files:
        raise ApiError("No file received (field name: 'files')", 400)
    fs = request.form.get("fs", type=float)
    rec = _repo().add_upload(files, fs)
    return jsonify(record=rec.summary()), 201


@bp.post("/analyze")
def analyze():
    body = request.get_json(silent=True) or {}
    rid = body.get("record_id")
    if not rid:
        raise ApiError("'record_id' is required", 400)
    cfg = current_app.extensions["cfg"]
    rec = _repo().get(rid)
    params = ECGParams.from_dict(body, default_mains=cfg.mains_hz)
    result = analyze_ecg(rec, params)
    if body.get("save"):
        hrv, q = result["hrv"], result["quality"]
        sid = current_app.extensions["history"].add("ecg", rid, {
            "lead": result["params"]["lead"],
            "hr_bpm": hrv.get("hr_bpm"), "sdnn_ms": hrv.get("sdnn_ms"), "rmssd_ms": hrv.get("rmssd_ms"),
            "quality": q["label"], "quality_score": q["score"], "n_beats": hrv.get("n_beats"),
        })
        result["saved_id"] = sid
    return jsonify(result)


@bp.get("/filter-response")
def filter_response():
    """Magnitude response of the Butterworth band-pass (for the educational Bode plot)."""
    try:
        low = float(request.args.get("low_hz", 0.5))
        high = float(request.args.get("high_hz", 40))
        order = int(request.args.get("order", 4))
        fs = float(request.args.get("fs", 500))
    except ValueError:
        raise ApiError("Query parameters must be numbers", 400)
    return jsonify(to_jsonable(filters.frequency_response(low, high, order, fs)))
