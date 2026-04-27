"""
PeakForm — Auth routes. Register, login, logout, profile.
No forced 2FA — simple secure JWT flow.
"""
import re
from flask import Blueprint, request, jsonify, g, make_response
from backend.models.user import (
    find_user_by_email, create_user, find_user_by_id,
    increment_failed_attempts, lock_user, reset_failed_attempts,
)
from backend.models.athlete import create_athlete_profile, get_athlete_profile, update_athlete_profile
from backend.models.audit import log_action
from backend.services.auth_service import (
    hash_password, check_password, validate_password_strength,
    generate_jwt, generate_2fa_code, store_2fa_code, verify_2fa_code,
)
from backend.middleware.auth import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL_REGEX = re.compile(r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$")


@auth_bp.route("/register", methods=["POST"])
def register():
    data         = request.get_json(silent=True) or {}
    email        = (data.get("email") or "").strip().lower()
    password     = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip()
    training_type = data.get("training_type", "gym")

    errors = {}
    if not email or not EMAIL_REGEX.match(email):
        errors["email"] = "Valid email address required."
    if not display_name:
        errors["display_name"] = "Display name is required."
    pw_errors = validate_password_strength(password)
    if pw_errors:
        errors["password"] = pw_errors
    if errors:
        return jsonify({"errors": errors}), 400

    if find_user_by_email(email):
        return jsonify({"errors": {"email": "An account with this email already exists."}}), 409

    user_id = create_user(email, hash_password(password), "athlete")
    create_athlete_profile(
        user_id, display_name,
        training_type=training_type,
        age=data.get("age"),
        gender=data.get("gender"),
        experience_level=data.get("experience_level", "beginner"),
    )
    log_action(user_id, "register", f"New athlete: {email}", request.remote_addr)

    token = generate_jwt(user_id, "athlete", email=email)
    res = make_response(jsonify({
        "message":      "Registration successful!",
        "token":        token, # Still return for legacy if needed, but cookie is primary
        "user_id":      user_id,
        "role":         "athlete",
        "email":        email,
        "display_name": display_name,
        "onboarding_complete": False,
    }), 201)
    res.set_cookie('auth_token', token, httponly=True, secure=True, samesite='Lax')
    return res


@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ip       = request.remote_addr

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    if user["is_locked"]:
        return jsonify({"error": "Account locked. Contact support."}), 403

    # ✅ CRITICAL: verify password
    if not check_password(password, user["password_hash"]):
        increment_failed_attempts(user["id"])
        if user["failed_attempts"] + 1 >= 10:
            lock_user(user["id"])
        log_action(user["id"], "login_failed", f"bad password", ip)
        return jsonify({"error": "Invalid email or password."}), 401

    reset_failed_attempts(user["id"])
    token = generate_jwt(user["id"], user["role"], email=user["email"])
    log_action(user["id"], "login_success", f"role={user['role']}", ip)

    profile = get_athlete_profile(user["id"])

    res = make_response(jsonify({
        "token":             token,
        "user_id":           user["id"],
        "role":              user["role"],
        "email":             user["email"],
        "display_name":      profile["display_name"] if profile else user["email"],
        "training_type":     profile["training_type"] if profile else "gym",
        "onboarding_complete": bool(profile["onboarding_complete"]) if profile else False,
    }), 200)
    res.set_cookie('auth_token', token, httponly=True, secure=True, samesite='Lax')
    return res


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    log_action(g.user_id, "logout", None, request.remote_addr)
    res = make_response(jsonify({"message": "Logged out successfully."}), 200)
    res.delete_cookie('auth_token')
    return res


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    user = find_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    profile = get_athlete_profile(g.user_id)
    return jsonify({
        "user_id":           g.user_id,
        "email":             user["email"],
        "role":              g.role,
        "display_name":      profile["display_name"] if profile else user["email"],
        "training_type":     profile["training_type"] if profile else "gym",
        "onboarding_complete": bool(profile["onboarding_complete"]) if profile else False,
        "avatar_url":        profile["avatar_url"] if profile else None,
    }), 200


@auth_bp.route("/onboarding", methods=["POST"])
@require_auth
def complete_onboarding():
    """Save onboarding data and mark profile as complete."""
    data = request.get_json(silent=True) or {}

    allowed_fields = {
        "display_name", "age", "gender", "height_cm",
        "current_weight_kg", "target_weight_kg",
        "experience_level", "training_type",
        "main_goal", "days_per_week",
    }
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    updates["onboarding_complete"] = 1

    update_athlete_profile(g.user_id, updates)

    # Log initial weight if provided
    if data.get("current_weight_kg"):
        from backend.models.db import get_db
        import datetime
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO body_weight_logs (user_id, weight_kg, logged_at) VALUES (?,?,?)",
            (g.user_id, float(data["current_weight_kg"]), datetime.date.today().isoformat()),
        )
        db.commit()

    log_action(g.user_id, "onboarding_complete", None, request.remote_addr)
    return jsonify({"message": "Profile updated.", "onboarding_complete": True}), 200


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    data         = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    if not old_password or not new_password:
        return jsonify({"error": "old_password and new_password required."}), 400
    user = find_user_by_id(g.user_id)
    if not user or not check_password(old_password, user["password_hash"]):
        return jsonify({"error": "Current password is incorrect."}), 401
    errors = validate_password_strength(new_password)
    if errors:
        return jsonify({"error": " ".join(errors)}), 400
    from backend.models.user import update_user_password
    update_user_password(g.user_id, hash_password(new_password))
    log_action(g.user_id, "password_changed", None, request.remote_addr)
    return jsonify({"message": "Password updated."}), 200
