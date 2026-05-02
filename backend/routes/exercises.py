"""
Exercise library routes — search, custom creation, history, PRs, admin approval.
ספריית התרגילים שלנו! כאן אפשר לחפש תרגילים, ליצור תרגילים משלנו, לראות 
שיאים היסטוריים וגם למנהלים יש אזור משלהם לאשר תרגילים חדשים.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.middleware.roles import require_admin
from backend.models.exercise import (
    search_exercises, get_exercise_by_id, create_custom_exercise,
    get_exercise_history, get_exercise_prs, get_all_categories,
    get_pending_exercises, approve_exercise, reject_exercise,
    get_last_session,
)
from backend.services.encryption_service import decrypt_data

# יוצרים את ספריית הכתובות שמתחילות ב /api/exercises
exercises_bp = Blueprint("exercises", __name__, url_prefix="/api/exercises")


# כשמישהו מחפש תרגיל ספציפי
@exercises_bp.route("", methods=["GET"])
@require_auth
def list_exercises():
    q        = request.args.get("q", "") # מה המשתמש כתב בשורת החיפוש?
    category = request.args.get("category", "") # האם הוא סינן לפי "חזה" או "רגליים"?
    limit    = int(request.args.get("limit", 50))
    rows     = search_exercises(q, category, limit, user_id=g.user_id) # הולכים לחפש בטבלה
    return jsonify([dict(r) for r in rows]), 200


# מביא את כל הקטגוריות הקיימות (ידיים, רגליים, בטן וכו')
@exercises_bp.route("/categories", methods=["GET"])
@require_auth
def categories():
    return jsonify(get_all_categories()), 200


# רק למנהלים! מביא רשימה של תרגילים שאנשים הציעו ומחכים לאישור מנהל
@exercises_bp.route("/pending", methods=["GET"])
@require_auth
@require_admin # רק מי שתפקידו מנהל יכול לעבור מפה!
def pending_exercises():
    """Admin: list all pending exercises for review."""
    rows = get_pending_exercises()
    result = []
    for r in rows:
        d = dict(r)
        # מכיוון שהאימיילים מוצפנים, אנחנו מפענחים אותם כדי שהמנהל יראה מי הציע
        try:
            d["submitted_by_email"] = decrypt_data(d.get("submitted_by_email")) or d.get("submitted_by_email")
        except Exception:
            pass
        result.append(d)
    return jsonify(result), 200


# מביא מידע מלא על תרגיל ספציפי (למשל תרגיל מספר 5)
@exercises_bp.route("/<int:exercise_id>", methods=["GET"])
@require_auth
def detail(exercise_id):
    ex = get_exercise_by_id(exercise_id)
    if not ex:
        return jsonify({"error": "Exercise not found"}), 404
    return jsonify(dict(ex)), 200


# המנהל לוחץ "אשר" על תרגיל שאנשים הציעו!
@exercises_bp.route("/<int:exercise_id>/approve", methods=["POST"])
@require_auth
@require_admin
def approve(exercise_id):
    approve_exercise(exercise_id)
    return jsonify({"message": "Exercise approved."}), 200


# המנהל לוחץ "דחה" על תרגיל גרוע שאנשים הציעו!
@exercises_bp.route("/<int:exercise_id>/reject", methods=["POST"])
@require_auth
@require_admin
def reject(exercise_id):
    reject_exercise(exercise_id)
    return jsonify({"message": "Exercise rejected."}), 200


# כשאנחנו מתחילים תרגיל, השרת מחפש כמה עשינו באימון הקודם, כדי להזכיר לנו
@exercises_bp.route("/<int:exercise_id>/last-session", methods=["GET"])
@require_auth
def last_session(exercise_id):
    """Return the user's most recent session data for this exercise (for in-workout intel)."""
    data = get_last_session(g.user_id, exercise_id)
    if not data:
        return jsonify({"found": False}), 200
    return jsonify({"found": True, **data}), 200


# מביא את היסטוריית הפעמים שעשינו את התרגיל
@exercises_bp.route("/<int:exercise_id>/history", methods=["GET"])
@require_auth
def history(exercise_id):
    limit = int(request.args.get("limit", 20))
    rows  = get_exercise_history(g.user_id, exercise_id, limit)
    return jsonify([dict(r) for r in rows]), 200


# מביא את השיאים האישיים שלנו בתרגיל (Personal Records = PRs)
@exercises_bp.route("/<int:exercise_id>/prs", methods=["GET"])
@require_auth
def personal_records(exercise_id):
    prs = get_exercise_prs(g.user_id, exercise_id)
    return jsonify(prs), 200


# יצירת תרגיל חדש וייחודי שאנחנו ממציאים לבד!
@exercises_bp.route("/custom", methods=["POST"])
@require_auth
def create_custom():
    data = request.get_json(silent=True) or {}
    name        = (data.get("name") or "").strip()
    category    = data.get("category", "full_body")
    set_type    = data.get("set_type", "reps_weight") # סוג הסט: שניות או חזרות?
    muscles     = data.get("muscles", "")
    muscles_tags = data.get("muscles_tags", "")
    equipment   = data.get("equipment", "bodyweight") # איזה ציוד צריך?

    if not name:
        return jsonify({"error": "Exercise name required"}), 400

    from backend.models.db import get_db
    db = get_db()
    
    # בודקים שלא קראתם לתרגיל בשם של תרגיל שכבר קיים - זה יעשה בלאגן עם הגרפים שלכם!
    existing = db.execute(
        """SELECT id FROM exercises 
           WHERE name COLLATE NOCASE = ? 
           AND (created_by = ? OR status = 'approved' OR (status IS NULL AND is_custom = 0))""",
        (name, g.user_id)
    ).fetchone()
    
    if existing:
        return jsonify({"error": f"An exercise named '{name}' already exists. Please search for it in your library instead."}), 409

    # בודקים שבחרתם סוג סט הגיוני
    valid_types = ["reps_weight","reps_only","time_only","time_weight"]
    if set_type not in valid_types:
        return jsonify({"error": f"set_type must be one of {valid_types}"}), 400

    ex_id = create_custom_exercise(g.user_id, name, category, set_type, muscles, equipment, muscles_tags)
    return jsonify({
        "id": ex_id,
        "message": "Exercise submitted for approval. It will appear once an admin reviews it.",
        "status": "pending",
    }), 201


# עריכת פרטים של תרגיל קיים (למשל לשנות לו את השם - רק מנהלים)
@exercises_bp.route("/<int:exercise_id>", methods=["PUT"])
@require_auth
@require_admin
def update(exercise_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = data.get("category", "")
    set_type = data.get("set_type", "")
    muscles_tags = data.get("muscles_tags", "")
    equipment = data.get("equipment", "")

    if not name:
        return jsonify({"error": "Exercise name required"}), 400

    from backend.models.exercise import update_exercise
    update_exercise(exercise_id, name, category, set_type, muscles_tags, equipment)
    return jsonify({"message": "Exercise updated successfully."}), 200


# מחיקת תרגיל (רק מנהלים)
@exercises_bp.route("/<int:exercise_id>", methods=["DELETE"])
@require_auth
@require_admin
def delete(exercise_id):
    from backend.models.exercise import delete_exercise
    delete_exercise(exercise_id)
    return jsonify({"message": "Exercise deleted."}), 200

"""
English Summary:
This file exposes endpoints for managing the exercise library. It supports searching the 
global exercise database, creating custom exercises, and tracking a user's exercise history 
and personal records. It also includes protected administrative routes (using the @require_admin 
decorator) that allow admins to review, approve, or reject pending custom exercises submitted by users.

סיכום בעברית:
קובץ זה מנהל את מאגר התרגילים של המערכת. הוא מאפשר חיפוש תרגילים, הצגת היסטוריית התקדמות בתרגיל
מסוים וצפייה בשיאים אישיים. בנוסף, הוא מאפשר למתאמנים להציע תרגילים חדשים משלהם למערכת.
הקובץ מכיל גם אזור מאובטח המיועד למנהלים בלבד, שבו הם יכולים לאשר, לדחות או למחוק תרגילים שאנשים הציעו.
"""
