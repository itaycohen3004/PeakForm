"""
Notifications routes — persistent DB-backed notifications.
מערכת ההתראות שלנו! כמו הפעמון ביוטיוב, כאן מקבלים הודעות
על לייקים, השלמת מטרות או דברים חשובים שקרו.
"""
from flask import Blueprint, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.db import get_db

# הכתובות של ההתראות תמיד יתחילו ב /api/notifications
notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)


# מושך את כל ההודעות (התראות) שיש למשתמש - עד 50 אחרונות כדי לא להעמיס
@notifications_bp.route("/", methods=["GET"])
@require_auth
def get_notifications():
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (g.user_id,)
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    except Exception:
        return jsonify([]), 200


# בודק האם יש למשתמש התראות חדשות שהוא עוד לא קרא (כדי להראות נקודה אדומה על הפעמון)
@notifications_bp.route("/check", methods=["POST"])
@require_auth
def check_notifications():
    """Called on dashboard load — returns unread count and latest notifications."""
    db = get_db()
    try:
        unread = db.execute(
            "SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0",
            (g.user_id,)
        ).fetchone()["c"]
        return jsonify({"unread": unread}), 200
    except Exception:
        return jsonify({"unread": 0}), 200


# מסמן התראה ספציפית בתור "נקראה" כדי שהיא תפסיק להבהב
@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@require_auth
def mark_read(notif_id):
    db = get_db()
    try:
        db.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
            (notif_id, g.user_id)
        )
        db.commit()
    except Exception:
        pass
    return jsonify({"success": True}), 200


# כפתור "קרא הכל" - הופך את כל ההתראות ל"נקראו" בבת אחת!
@notifications_bp.route("/read-all", methods=["POST"])
@require_auth
def mark_all_read():
    db = get_db()
    try:
        db.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
            (g.user_id,)
        )
        db.commit()
    except Exception:
        pass
    return jsonify({"success": True}), 200


# מוחק לגמרי את כל ההיסטוריה של ההתראות שלי
@notifications_bp.route("/clear", methods=["POST"])
@require_auth
def clear_all():
    db = get_db()
    try:
        db.execute("DELETE FROM notifications WHERE user_id = ?", (g.user_id,))
        db.commit()
    except Exception:
        pass
    return jsonify({"success": True}), 200

"""
English Summary:
This file handles the API routes for the in-app notification system. It allows users to 
fetch their recent notifications, check the count of unread notifications, mark individual 
or all notifications as read, and clear their notification history. It acts like a classic 
bell-notification system.

סיכום בעברית:
קובץ זה מנהל את "פעמון ההתראות" של המשתמש. דרכו המשתמש יכול לקבל הודעות על דברים חדשים שקרו
(כמו מישהו שעשה לו לייק או מטרה שהושלמה), לסמן התראות מסוימות כאילו נקראו (כדי שהנקודה האדומה 
תעלם מהפעמון), ואפילו לנקות ולמחוק את כל היסטוריית ההתראות בבת אחת.
"""