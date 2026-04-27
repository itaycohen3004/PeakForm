"""
PeakForm — Goals routes (fixed, complete, no crashes).
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.goal import (
    create_goal, get_goals, get_goal,
    update_goal_progress, delete_goal, VALID_GOAL_TYPES,
    update_goal_photo, get_goal_with_details
)
import os
from werkzeug.utils import secure_filename

goals_bp = Blueprint("goals", __name__, url_prefix="/api/goals")


@goals_bp.route("", methods=["GET"])
@require_auth
def list_goals():
    include_completed = request.args.get("include_completed", "true").lower() == "true"
    rows = get_goals(g.user_id, include_completed)
    return jsonify([dict(r) for r in rows]), 200


@goals_bp.route("", methods=["POST"])
@require_auth
def create():
    data = request.get_json(silent=True) or {}
    goal_type = data.get("goal_type", "").strip()

    if goal_type not in VALID_GOAL_TYPES:
        return jsonify({"error": f"Invalid goal_type. Valid: {', '.join(VALID_GOAL_TYPES)}"}), 400

    if not data.get("title", "").strip():
        return jsonify({"error": "title is required"}), 400

    try:
        target = float(data.get("target_value", 0))
        if target <= 0:
            raise ValueError("target must be positive")
    except (ValueError, TypeError):
        return jsonify({"error": "target_value must be a positive number"}), 400

    try:
        goal_id = create_goal(g.user_id, data)
    except Exception as e:
        return jsonify({"error": f"Failed to create goal: {str(e)}"}), 500

    return jsonify({"id": goal_id, "message": "Goal created."}), 201


@goals_bp.route("/<int:goal_id>", methods=["GET"])
@require_auth
def get_one(goal_id):
    row = get_goal_with_details(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row)), 200


@goals_bp.route("/<int:goal_id>/progress", methods=["PATCH"])
@require_auth
def update_progress(goal_id):
    row = get_goal(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        current = float(data["current_value"]) if "current_value" in data else None
    except (ValueError, TypeError):
        return jsonify({"error": "current_value must be a number"}), 400
    completed = update_goal_progress(goal_id, current)

    # If newly completed, create a notification
    if completed:
        try:
            from backend.routes.notifications import create_notification
            create_notification(
                g.user_id, "goal_completed",
                "🏆 Goal Completed!",
                f'You achieved your goal: "{row["title"]}"! Congratulations!',
                "/achievements.html"
            )
        except Exception:
            pass

    return jsonify({"message": "Progress updated.", "is_completed": completed}), 200


@goals_bp.route("/<int:goal_id>", methods=["DELETE"])
@require_auth
def remove(goal_id):
    row = get_goal(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    delete_goal(goal_id)
    return jsonify({"message": "Goal deleted."}), 200


@goals_bp.route("/<int:goal_id>/photo", methods=["POST"])
@require_auth
def upload_photo(goal_id):
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400

    file = request.files["photo"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    row = get_goal(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404

    upload_folder = os.path.join(os.getcwd(), "frontend", "static", "uploads", "achievements")
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(f"achievement_{goal_id}_{file.filename}")
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    photo_url = f"/static/uploads/achievements/{filename}"
    update_goal_photo(goal_id, photo_url)

    return jsonify({"message": "Photo uploaded.", "photo_url": photo_url}), 200
