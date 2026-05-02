"""
PeakForm Role-Based Access Control
הקובץ שמגדיר הרשאות באתר. הוא בודק האם מי שמנסה
להיכנס לדף מסוים הוא סתם "מתאמן" או "מנהל ראשי".
"""

from functools import wraps
from flask import jsonify, g


def require_role(*allowed_roles):
    """
    Decorator that checks g.role is in allowed_roles.
    Usage: @require_role('athlete') or @require_role('admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, "role") or g.role not in allowed_roles:
                return jsonify({
                    "error": "Access denied. Insufficient permissions."
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_admin(f):
    """Shorthand for admin-only routes."""
    return require_role("admin")(f)


def require_athlete(f):
    """Shorthand for athlete-only routes."""
    return require_role("athlete")(f)

"""
English Summary:
This middleware handles Role-Based Access Control (RBAC). It provides custom decorators 
(@require_admin and @require_athlete) that wrap API routes, ensuring that only users with 
the correct permission level can execute certain operations (like deleting another user's account).

סיכום בעברית:
קובץ זה מנהל את מערכת ה"דרגות" באתר. הוא מוודא שפעולות מסוכנות או ניהוליות (כמו מחיקת
משתמשים מהאתר) יכולות להתבצע אך ורק על ידי משתמש עם תג "מנהל" (Admin). אם משתמש רגיל ינסה
לעשות פעולת מנהל, הקובץ יעצור אותו מיד ויציג לו הודעת שגיאה.
"""
