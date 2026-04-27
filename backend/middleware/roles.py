"""
PeakForm Role-Based Access Control
Keeps only essential Athlete/Admin roles.
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
