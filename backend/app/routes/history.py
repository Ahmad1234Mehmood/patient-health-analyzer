from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.utils.errors import ApiError

bp = Blueprint("history", __name__)


@bp.get("")
def list_history():
    limit = min(int(request.args.get("limit", 50)), 200)
    return jsonify(items=current_app.extensions["history"].list(limit))


@bp.delete("/<int:analysis_id>")
def delete_one(analysis_id: int):
    if not current_app.extensions["history"].delete(analysis_id):
        raise ApiError("Analysis not found", 404, "not_found")
    return jsonify(deleted=analysis_id)


@bp.delete("")
def clear():
    current_app.extensions["history"].clear()
    return jsonify(cleared=True)

# v2
