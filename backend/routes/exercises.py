"""
Exercise library routes — search, custom creation, history, PRs, admin approval.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.middleware.roles import require_admin
from backend.models.exercise import (
    search_exercises, get_exercise_by_id, create_custom_exercise,
    get_exercise_history, get_exercise_prs, get_all_categories,
    get_pending_exercises, approve_exercise, reject_exercise,
    get_last_session,
)
from backend.services.encryption_service import decrypt_data

exercises_bp = Blueprint("exercises", __name__, url_prefix="/api/exercises")


@exercises_bp.route("", methods=["GET"])
@require_auth
def list_exercises():
    q        = request.args.get("q", "")
    category = request.args.get("category", "")
    limit    = int(request.args.get("limit", 50))
    rows     = search_exercises(q, category, limit, user_id=g.user_id)
    return jsonify([dict(r) for r in rows]), 200


@exercises_bp.route("/categories", methods=["GET"])
@require_auth
def categories():
    return jsonify(get_all_categories()), 200


@exercises_bp.route("/pending", methods=["GET"])
@require_auth
@require_admin
def pending_exercises():
    """Admin: list all pending exercises for review."""
    rows = get_pending_exercises()
    result = []
    for r in rows:
        d = dict(r)
        # Decrypt submitted_by_email if encrypted
        try:
            d["submitted_by_email"] = decrypt_data(d.get("submitted_by_email")) or d.get("submitted_by_email")
        except Exception:
            pass
        result.append(d)
    return jsonify(result), 200


@exercises_bp.route("/<int:exercise_id>", methods=["GET"])
@require_auth
def detail(exercise_id):
    ex = get_exercise_by_id(exercise_id)
    if not ex:
        return jsonify({"error": "Exercise not found"}), 404
    return jsonify(dict(ex)), 200


@exercises_bp.route("/<int:exercise_id>/approve", methods=["POST"])
@require_auth
@require_admin
def approve(exercise_id):
    approve_exercise(exercise_id)
    return jsonify({"message": "Exercise approved."}), 200


@exercises_bp.route("/<int:exercise_id>/reject", methods=["POST"])
@require_auth
@require_admin
def reject(exercise_id):
    reject_exercise(exercise_id)
    return jsonify({"message": "Exercise rejected."}), 200


@exercises_bp.route("/<int:exercise_id>/last-session", methods=["GET"])
@require_auth
def last_session(exercise_id):
    """Return the user's most recent session data for this exercise (for in-workout intel)."""
    data = get_last_session(g.user_id, exercise_id)
    if not data:
        return jsonify({"found": False}), 200
    return jsonify({"found": True, **data}), 200


@exercises_bp.route("/<int:exercise_id>/history", methods=["GET"])
@require_auth
def history(exercise_id):
    limit = int(request.args.get("limit", 20))
    rows  = get_exercise_history(g.user_id, exercise_id, limit)
    return jsonify([dict(r) for r in rows]), 200


@exercises_bp.route("/<int:exercise_id>/prs", methods=["GET"])
@require_auth
def personal_records(exercise_id):
    prs = get_exercise_prs(g.user_id, exercise_id)
    return jsonify(prs), 200


@exercises_bp.route("/custom", methods=["POST"])
@require_auth
def create_custom():
    data = request.get_json(silent=True) or {}
    name        = (data.get("name") or "").strip()
    category    = data.get("category", "full_body")
    set_type    = data.get("set_type", "reps_weight")
    muscles     = data.get("muscles", "")
    muscles_tags = data.get("muscles_tags", "")
    equipment   = data.get("equipment", "bodyweight")

    if not name:
        return jsonify({"error": "Exercise name required"}), 400

    valid_types = ["reps_weight","reps_only","time_only","time_weight"]
    if set_type not in valid_types:
        return jsonify({"error": f"set_type must be one of {valid_types}"}), 400

    ex_id = create_custom_exercise(g.user_id, name, category, set_type, muscles, equipment, muscles_tags)
    return jsonify({
        "id": ex_id,
        "message": "Exercise submitted for approval. It will appear once an admin reviews it.",
        "status": "pending",
    }), 201


@exercises_bp.route("/<int:exercise_id>", methods=["PUT"])
@require_auth
@require_admin
def update(exercise_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = data.get("category", "")
    set_type = data.get("set_type", "")
    muscles_tags = data.get("muscles_tags", "")
    equipment = data.get("equipment", "")

    if not name:
        return jsonify({"error": "Exercise name required"}), 400

    from backend.models.exercise import update_exercise
    update_exercise(exercise_id, name, category, set_type, muscles_tags, equipment)
    return jsonify({"message": "Exercise updated successfully."}), 200


@exercises_bp.route("/<int:exercise_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete(exercise_id):
    from backend.models.exercise import delete_exercise
    delete_exercise(exercise_id)
    return jsonify({"message": "Exercise deleted."}), 200
