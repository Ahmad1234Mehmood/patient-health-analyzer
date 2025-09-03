from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    cfg = current_app.extensions["cfg"]
    return jsonify(
        status="healthy",
        service="Patient Health Data Analyzer API",
        version="1.0.0",
        environment=cfg.environment,
        mains_hz=cfg.mains_hz,
    )


@bp.get("/api")
def api_root():
    return jsonify(
        message="Patient Health Data Analyzer API",
        endpoints=["/health", "/api/v1/datasets/summary", "/api/v1/ecg/records", "/api/v1/ecg/analyze",
                   "/api/v1/xray/images", "/api/v1/xray/analyze", "/api/v1/xray/evaluate", "/api/v1/history"],
    )
