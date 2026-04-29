from flask import Blueprint, jsonify, request, g
from backend.middleware.auth import require_auth
from backend.models.db import get_db

notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)

@notifications_bp.route("/", methods=["GET"])
@require_auth
def get_notifications():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (g.user_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@notifications_bp.route("/add", methods=["POST"])
@require_auth
def add_notification():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    message = (data.get("message") or "").strip()

    if not title:
        return jsonify({"error": "Title required"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO notifications (user_id, title, message) VALUES (?, ?, ?)",
        (g.user_id, title, message)
    )
    db.commit()
    return jsonify({"success": True})

@notifications_bp.route("/<int:item_id>/read", methods=["POST"])
@require_auth
def mark_read(item_id):
    db = get_db()
    db.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (item_id, g.user_id)
    )
    db.commit()
    return jsonify({"success": True})

@notifications_bp.route("/clear", methods=["POST"])
@require_auth
def clear_all():
    db = get_db()
    db.execute("DELETE FROM notifications WHERE user_id = ?", (g.user_id,))
    db.commit()
    return jsonify({"success": True})