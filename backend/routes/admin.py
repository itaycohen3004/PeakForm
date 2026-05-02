"""
PeakForm — Admin routes. User management and system overview.
קובץ זה מיועד אך ורק למנהלים (Admins). מפה הם יכולים לשלוט בכל המשתמשים באתר.
"""
from flask import Blueprint, request, jsonify, g
from backend.models.user import (
    find_user_by_id, delete_user, lock_user, 
    unlock_user, get_all_users_admin
)
from backend.models.audit import log_action
from backend.middleware.auth import require_auth
from backend.middleware.roles import require_admin

# יוצרים את אזור הכתובות של המנהלים, שמתחיל ב /api/admin
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# מביא את רשימת כל המשתמשים שרשומים לאתר
@admin_bp.route("/users", methods=["GET"])
@require_auth
@require_admin # רק מי שיש לו תג מנהל נכנס!
def list_users():
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    users = get_all_users_admin(limit, offset)
    return jsonify({"users": users}), 200

# נעילת משתמש (חסימה) כדי שלא יוכל להתחבר יותר
@admin_bp.route("/users/<int:user_id>/lock", methods=["POST"])
@require_auth
@require_admin
def lock_account(user_id):
    if user_id == g.user_id: # המנהל לא יכול לנעול את עצמו בטעות
        return jsonify({"error": "Cannot lock your own account"}), 400
    lock_user(user_id)
    log_action(g.user_id, "admin_lock_user", f"Locked user_id={user_id}", request.remote_addr)
    return jsonify({"message": "User locked"}), 200

# שחרור חסימה של משתמש
@admin_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@require_auth
@require_admin
def unlock_account(user_id):
    unlock_user(user_id)
    log_action(g.user_id, "admin_unlock_user", f"Unlocked user_id={user_id}", request.remote_addr)
    return jsonify({"message": "User unlocked"}), 200

# מחיקה לצמיתות של משתמש מהאתר
@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete_account(user_id):
    if user_id == g.user_id: # המנהל לא יכול למחוק את עצמו
        return jsonify({"error": "Cannot delete your own account"}), 400
    delete_user(user_id)
    log_action(g.user_id, "admin_delete_user", f"Deleted user_id={user_id}", request.remote_addr)
    return jsonify({"message": "User deleted"}), 200

# מביא נתונים כלליים למנהל (כמה משתמשים נרשמו, כמה אימונים נעשו)
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

"""
English Summary:
This file contains the administrative routes for PeakForm. It requires the user to have an 'admin' role.
It allows the admin to view all registered users, lock/unlock accounts, delete users, and retrieve 
general system statistics like the total number of users and workouts in the database.

סיכום בעברית:
קובץ זה הוא "חדר הבקרה" של המנהלים בלבד! באמצעות הקובץ הזה, מנהל המערכת יכול לראות רשימה של
כל המשתמשים שנרשמו, לנעול חשבונות של משתמשים בעייתיים (כדי שלא יוכלו להתחבר), לשחרר מנעילה, 
ואפילו למחוק חשבונות לחלוטין. בנוסף, הוא מציג למנהל נתונים כלליים על גודל המערכת (כמו כמות אימונים שנרשמו).
"""
