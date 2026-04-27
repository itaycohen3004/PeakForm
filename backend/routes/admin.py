"""
PeakForm — Admin routes. User management and system overview.
"""
from flask import Blueprint, request, jsonify, g
from backend.models.user import (
    find_user_by_id, delete_user, lock_user, 
    unlock_user, get_all_users_admin
)
from backend.models.audit import log_action
from backend.middleware.auth import require_auth
from backend.middleware.roles import require_admin

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/users", methods=["GET"])
@require_auth
@require_admin
def list_users():
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    users = get_all_users_admin(limit, offset)
    return jsonify({"users": users}), 200

@admin_bp.route("/users/<int:user_id>/lock", methods=["POST"])
@require_auth
@require_admin
def lock_account(user_id):
    if user_id == g.user_id:
        return jsonify({"error": "Cannot lock your own account"}), 400
    lock_user(user_id)
    log_action(g.user_id, "admin_lock_user", f"Locked user_id={user_id}", request.remote_addr)
    return jsonify({"message": "User locked"}), 200

@admin_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@require_auth
@require_admin
def unlock_account(user_id):
    unlock_user(user_id)
    log_action(g.user_id, "admin_unlock_user", f"Unlocked user_id={user_id}", request.remote_addr)
    return jsonify({"message": "User unlocked"}), 200

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete_account(user_id):
    if user_id == g.user_id:
        return jsonify({"error": "Cannot delete your own account"}), 400
    delete_user(user_id)
    log_action(g.user_id, "admin_delete_user", f"Deleted user_id={user_id}", request.remote_addr)
    return jsonify({"message": "User deleted"}), 200

@admin_bp.route("/stats", methods=["GET"])
@require_auth
@require_admin
def system_stats():
    # Simple system overview
    from backend.models.db import get_db
    db = get_db()
    user_count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    workout_count = db.execute("SELECT COUNT(*) as c FROM workouts").fetchone()["c"]
    return jsonify({
        "total_users": user_count,
        "total_workouts": workout_count,
    }), 200
