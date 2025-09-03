"""Flask application factory for the Patient Health Data Analyzer."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import BASE_DIR, Config, load_config
from app.services.ecg.loader import ECGRepository
from app.services.history import HistoryStore
from app.services.xray.loader import XrayRepository
from app.utils.errors import ApiError


def create_app(config: Config | None = None) -> Flask:
    load_dotenv(BASE_DIR / ".env")
    cfg = config or load_config()

    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = cfg.max_upload_mb * 1024 * 1024
    app.extensions["cfg"] = cfg
    app.extensions["ecg_repo"] = ECGRepository(cfg.ecg_dir)
    app.extensions["xray_repo"] = XrayRepository(cfg.xray_image_dir, cfg.xray_mask_dir)
    app.extensions["history"] = HistoryStore(cfg.db_path)
    app.extensions["eval_cache"] = {}

    CORS(
        app,
        resources={r"/(api/.*|health)": {"origins": [cfg.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"]}},
    )

    from app.routes import datasets, ecg, health, history, xray

    app.register_blueprint(health.bp)
    app.register_blueprint(datasets.bp, url_prefix="/api/v1/datasets")
    app.register_blueprint(ecg.bp, url_prefix="/api/v1/ecg")
    app.register_blueprint(xray.bp, url_prefix="/api/v1/xray")
    app.register_blueprint(history.bp, url_prefix="/api/v1/history")

    # ---- JSON error handling (always `{error, message}` + correct HTTP status)
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        return jsonify(error=e.code, message=e.message), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        return jsonify(error=e.name.lower().replace(" ", "_"), message=e.description), e.code

    @app.errorhandler(Exception)
    def _unhandled(e: Exception):
        app.logger.exception("Unhandled error")
        return jsonify(error="internal_error", message="Unexpected server error", detail=str(e)), 500

    # ---- optional: serve the built React app (`npm run build`) from the same port
    dist = Path(cfg.frontend_dist)
    if dist.exists() and (dist / "index.html").exists():
        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def _spa(path: str):
            if path.startswith("api/") or path == "api":
                raise ApiError("Unknown API endpoint", 404, "not_found")
            if path and (dist / path).is_file():
                return send_from_directory(dist, path)
            return send_from_directory(dist, "index.html")

    return app
