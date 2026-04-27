"""
Exercise library routes — search, custom creation, history, PRs.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.exercise import (
    search_exercises, get_exercise_by_id, create_custom_exercise,
    get_exercise_history, get_exercise_prs, get_all_categories,
)

exercises_bp = Blueprint("exercises", __name__, url_prefix="/api/exercises")


@exercises_bp.route("", methods=["GET"])
@require_auth
def list_exercises():
    q        = request.args.get("q", "")
    category = request.args.get("category", "")
    limit    = int(request.args.get("limit", 50))
    rows     = search_exercises(q, category, limit)
    return jsonify([dict(r) for r in rows]), 200


@exercises_bp.route("/categories", methods=["GET"])
@require_auth
def categories():
    return jsonify(get_all_categories()), 200


@exercises_bp.route("/<int:exercise_id>", methods=["GET"])
@require_auth
def detail(exercise_id):
    ex = get_exercise_by_id(exercise_id)
    if not ex:
        return jsonify({"error": "Exercise not found"}), 404
    return jsonify(dict(ex)), 200


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
    name     = (data.get("name") or "").strip()
    category = data.get("category", "full_body")
    set_type = data.get("set_type", "reps_weight")
    muscles  = data.get("muscles", "")
    equipment = data.get("equipment", "bodyweight")

    if not name:
        return jsonify({"error": "Exercise name required"}), 400

    valid_types = ["reps_weight","reps_only","time_only","time_weight"]
    if set_type not in valid_types:
        return jsonify({"error": f"set_type must be one of {valid_types}"}), 400

    ex_id = create_custom_exercise(g.user_id, name, category, set_type, muscles, equipment)
    return jsonify({"id": ex_id, "message": "Custom exercise created."}), 201
