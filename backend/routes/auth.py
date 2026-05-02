"""
PeakForm — Auth routes. Register, login, logout, profile.
קובץ ההתחברות וההרשמה! פה אנחנו בודקים תעודות זהות ומוודאים שאף אחד לא מתחזה לאדם אחר.
"""
import re
from flask import Blueprint, request, jsonify, g, make_response
from backend.models.user import (
    find_user_by_email, create_user, find_user_by_id,
    increment_failed_attempts, lock_user, reset_failed_attempts,
)
from backend.models.athlete import create_athlete_profile, get_athlete_profile, update_athlete_profile, Athlete
from backend.models.audit import log_action
from backend.services.auth_service import (
    hash_password, check_password, validate_password_strength,
    generate_jwt, generate_2fa_code, store_2fa_code, verify_2fa_code,
)
from backend.services.encryption_service import decrypt_data
from backend.middleware.auth import require_auth

# פותחים "תיקייה" לכתובות האינטרנט של אזור האבטחה (api/auth/)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# חוק סודי שבודק אם האימייל נכתב בצורה הגיונית (שיש @ ונקודה)
EMAIL_REGEX = re.compile(r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$")


# פונקציית הרשמה! משתמש חדש מגיע לכאן
@auth_bp.route("/register", methods=["POST"])
def register():
    data             = request.get_json(silent=True) or {} # שואבים את הטופס מהדפדפן
    email            = (data.get("email") or "").strip().lower() # מנקים רווחים מאימייל
    password         = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    display_name     = (data.get("display_name") or "").strip() # איך קוראים לו במשחק
    training_type    = data.get("training_type", "gym")

    errors = {} # רשימה של שגיאות (אם הוא עשה טעות נכניס לכאן)
    
    # בודקים אם האימייל תקין
    if not email or not EMAIL_REGEX.match(email):
        errors["email"] = "Valid email address required."
    if not display_name:
        errors["display_name"] = "Display name is required."
        
    # בודקים אם הסיסמה חזקה מספיק
    pw_errors = validate_password_strength(password)
    if pw_errors:
        errors["password"] = pw_errors
        
    # מוודאים ששתי הסיסמאות שהקליד זהות
    if confirm_password and password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."
        
    # אם יש שגיאות - אנחנו זורקים לו אותן חזרה בפרצוף!
    if errors:
        return jsonify({"errors": errors}), 400

    # האם המייל כבר קיים במערכת?
    if find_user_by_email(email):
        return jsonify({"errors": {"email": "This email already exists."}}), 409

    # הכל תקין! מצפינים את הסיסמה שלו ושומרים בטבלת משתמשים
    user_id = create_user(email, hash_password(password), "athlete")
    
    # יוצרים לו כרטיס פרופיל (כדי שישמור נתונים נוספים על עצמו)
    create_athlete_profile(
        user_id, display_name,
        training_type=training_type,
        age=data.get("age"),
        gender=data.get("gender"),
        experience_level=data.get("experience_level", "beginner"),
    )
    # שומרים ליומן (לוג) שמשתמש נרשם עכשיו
    log_action(user_id, "register", f"New athlete: {email}", request.remote_addr)

    # מכינים "כרטיס כניסה" חכם (טוקן) ומחזירים לדפדפן
    token = generate_jwt(user_id, "athlete", email=email)
    res = make_response(jsonify({
        "message":      "Registration successful!",
        "token":        token, 
        "user_id":      user_id,
        "role":         "athlete",
        "email":        email,
        "display_name": display_name,
        "onboarding_complete": False, # הוא רק התחיל, עוד לא עשה היכרות עמוקה
    }), 201)
    
    # נועלים את כרטיס הכניסה בקוקי מאובטחת! אי אפשר לגנוב אותו מחוץ לדפדפן
    res.set_cookie('auth_token', token, httponly=True, secure=True, samesite='Lax')
    return res


# פונקציית התחברות (לוגין)
@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ip       = request.remote_addr # שומרים את ה-IP למקרה שהוא האקר

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    # אם הוא ניסה לפרוץ וטעה 10 פעמים - החשבון ננעל!
    if user["is_locked"]:
        return jsonify({"error": "Account locked. Contact support."}), 403

    # ✅ החלק הכי קריטי: בודקים אם הסיסמה נכונה מול ההצפנה!
    if not check_password(password, user["password_hash"]):
        # מוסיפים "טעות" אחת לספירה שלו
        increment_failed_attempts(user["id"])
        if user["failed_attempts"] + 1 >= 10:
            lock_user(user["id"]) # נועלים אם הגיע ל-10 טעויות
        log_action(user["id"], "login_failed", f"bad password", ip)
        return jsonify({"error": "Invalid email or password."}), 401

    # הסיסמה נכונה! מנקים את כמות הטעויות שצבר ל-0
    reset_failed_attempts(user["id"])
    token = generate_jwt(user["id"], user["role"], email=user["email"])
    log_action(user["id"], "login_success", f"role={user['role']}", ip)

    profile_row = get_athlete_profile(user["id"])
    athlete = Athlete(dict(profile_row)) if profile_row else None
    plain_email = decrypt_data(user["email"]) # פענוח שם המשתמש!

    # מחזירים לו תשובה "התחברת בהצלחה" יחד עם כל המידע עליו
    res = make_response(jsonify({
        "token":             token,
        "user_id":           user["id"],
        "role":              user["role"],
        "email":             plain_email,
        "display_name":      athlete.display_name if athlete else plain_email.split("@")[0],
        "training_type":     athlete.training_type if athlete else "gym",
        "onboarding_complete": athlete.onboarding_done if athlete else False,
    }), 200)
    res.set_cookie('auth_token', token, httponly=True, secure=True, samesite='Lax')
    return res


# פונקציית התנתקות (Log out)
@auth_bp.route("/logout", methods=["POST"])
@require_auth # חובה להיות מחובר כדי לצאת!
def logout():
    log_action(g.user_id, "logout", None, request.remote_addr)
    res = make_response(jsonify({"message": "Logged out successfully."}), 200)
    res.delete_cookie('auth_token') # זורקים לפח את כרטיס הכניסה הדיגיטלי
    return res


# פונקציה ששואלת "מי אני עכשיו?" ומחזירה מידע עליי
@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    user = find_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    profile_row = get_athlete_profile(g.user_id)
    athlete = Athlete(dict(profile_row)) if profile_row else None
    plain_email = decrypt_data(user["email"])
    return jsonify({
        "user_id":           g.user_id,
        "email":             plain_email,
        "role":              g.role,
        "display_name":      athlete.display_name if athlete else plain_email.split("@")[0],
        "training_type":     athlete.training_type if athlete else "gym",
        "onboarding_complete": athlete.onboarding_done if athlete else False,
        "avatar_url":        athlete.avatar_url if athlete else None,
    }), 200


# פונקציה להשלמת פרופיל (כמו גיל, משקל, גובה בהרשמה ראשונה)
@auth_bp.route("/onboarding", methods=["POST"])
@require_auth
def complete_onboarding():
    data = request.get_json(silent=True) or {}

    # רשימת המילים שמותר למשתמש לשלוח ולשנות בשרת
    allowed_fields = {
        "display_name", "age", "gender", "height_cm",
        "current_weight_kg", "target_weight_kg",
        "experience_level", "training_type",
        "main_goal", "days_per_week",
    }
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    updates["onboarding_complete"] = 1 # מסמן שסיימנו!

    update_athlete_profile(g.user_id, updates)

    # אם הוא הכניס משקל נוכחי, מיד נוסיף את זה ליומן השקילות שלו!
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


# שינוי סיסמה
@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    data         = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    if not old_password or not new_password:
        return jsonify({"error": "old_password and new_password required."}), 400
        
    user = find_user_by_id(g.user_id)
    # מוודא שהסיסמה הישנה נכונה
    if not user or not check_password(old_password, user["password_hash"]):
        return jsonify({"error": "Current password is incorrect."}), 401
        
    # בודק שהסיסמה החדשה חזקה
    errors = validate_password_strength(new_password)
    if errors:
        return jsonify({"error": " ".join(errors)}), 400
        
    # שומר ומצפין מחדש!
    from backend.models.user import update_user_password
    update_user_password(g.user_id, hash_password(new_password))
    log_action(g.user_id, "password_changed", None, request.remote_addr)
    return jsonify({"message": "Password updated."}), 200

"""
English Summary:
This file handles authentication routes for PeakForm. It implements secure registration 
and login flows, utilizing password hashing and JWT token generation. The module manages 
session cookies (setting and deleting secure, HTTP-only cookies) and prevents brute-force 
attacks by tracking failed login attempts and locking accounts when necessary. It also 
provides endpoints for profile onboarding and password updates.

סיכום בעברית:
קובץ זה מנהל את מערכת ההזדהות (התחברות והרשמה) של האפליקציה. הוא מוודא שסיסמאות נשמרות בצורה 
מאובטחת (מוצפנת) ויוצר "תעודות זהות דיגיטליות" (Tokens) כדי שהאתר יזכור את המשתמש. בנוסף, הקובץ
מגן על המערכת מפני פורצים על ידי ספירת טעויות בהתחברות ונעילת החשבון לאחר 10 ניסיונות כושלים.
"""
