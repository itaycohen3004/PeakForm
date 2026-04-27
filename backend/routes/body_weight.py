"""
Body weight routes — logging and chart data.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.body_weight import (
    log_body_weight, get_body_weight_logs,
    delete_body_weight_log, get_latest_body_weight,
)
import os

body_weight_bp = Blueprint("body_weight", __name__, url_prefix="/api/body-weight")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "progress_photos")


@body_weight_bp.route("", methods=["GET"])
@require_auth
def list_logs():
    limit = int(request.args.get("limit", 90))
    rows  = get_body_weight_logs(g.user_id, limit)
    return jsonify([dict(r) for r in rows]), 200


@body_weight_bp.route("", methods=["POST"])
@require_auth
def add_log():
    data = request.get_json(silent=True) or {}
    weight = data.get("weight_kg")
    if not weight:
        return jsonify({"error": "weight_kg required"}), 400
    log_id = log_body_weight(
        g.user_id, float(weight),
        notes=data.get("notes"),
        logged_at=data.get("logged_at"),
    )
    return jsonify({"id": log_id, "message": "Weight logged."}), 201


@body_weight_bp.route("/photo", methods=["POST"])
@require_auth
def upload_photo():
    """Upload a progress photo alongside a weight entry."""
    weight = request.form.get("weight_kg")
    notes  = request.form.get("notes", "")
    date   = request.form.get("logged_at")
    file   = request.files.get("photo")

    if not weight:
        return jsonify({"error": "weight_kg required"}), 400

    photo_path = None
    if file and file.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = f"user{g.user_id}_{__import__('datetime').datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        photo_path = os.path.join(UPLOAD_DIR, filename)
        file.save(photo_path)
        photo_path = f"/uploads/progress_photos/{filename}"

    log_id = log_body_weight(g.user_id, float(weight), notes=notes, photo_path=photo_path, logged_at=date)
    return jsonify({"id": log_id, "message": "Weight logged with photo."}), 201


@body_weight_bp.route("/<int:log_id>", methods=["DELETE"])
@require_auth
def delete_log(log_id):
    delete_body_weight_log(log_id)
    return jsonify({"message": "Log deleted."}), 200


@body_weight_bp.route("/latest", methods=["GET"])
@require_auth
def latest():
    row = get_latest_body_weight(g.user_id)
    return jsonify(dict(row) if row else {}), 200
