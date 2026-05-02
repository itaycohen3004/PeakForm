"""
Workout routes — sessions, exercises, sets CRUD + progression charts.
הקובץ שמנהל את כל מה שקשור לאימונים! 
מכאן יוצרים אימון חדש, מוסיפים סטים של משקולות ומוחקים אם טעינו.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.workout import (
    create_workout, get_workout, get_workouts, get_full_workout,
    update_workout, delete_workout,
    add_exercise_to_workout, get_workout_exercises, remove_exercise_from_workout,
    add_set, update_set, delete_set, get_sets_for_exercise,
    get_sets_for_exercise, get_weekly_volume, get_exercise_progression, 
    clone_from_template, get_workouts_for_month, finish_workout,
)
from backend.models.audit import log_action

# יוצרים אזור חדש בשרת שכל הכתובות בו יתחילו במילים /api/workouts
workouts_bp = Blueprint("workouts", __name__, url_prefix="/api/workouts")


# ── Sessions (אימונים כלליים) ──

# פונקציה שמחזירה לנו רשימה של כל האימונים שעשינו
@workouts_bp.route("", methods=["GET"])
@require_auth
def list_workouts():
    limit  = int(request.args.get("limit", 30)) # מבקש רק את ה-30 האחרונים כדי לא להעמיס
    offset = int(request.args.get("offset", 0))
    rows   = get_workouts(g.user_id, limit, offset)
    return jsonify([dict(r) for r in rows]), 200 # שולחים את זה חזרה לדפדפן


# כשאנחנו לוחצים על "התחל אימון חדש"
@workouts_bp.route("", methods=["POST"])
@require_auth
def create():
    data = request.get_json(silent=True) or {} # קוראים מה המתאמן שלח (למשל תאריך או שם אימון)
    workout_id = create_workout(g.user_id, data) # שומרים אימון ריק במסד הנתונים
    log_action(g.user_id, "workout_created", f"id={workout_id}", request.remote_addr) # רושמים ביומן
    return jsonify({"id": workout_id, "message": "Workout created."}), 201


# התחלת אימון מתוך תבנית שמורה (כמו "אימון חזה וגב הקבוע שלי")
@workouts_bp.route("/from-template", methods=["POST"])
@require_auth
def from_template():
    data        = request.get_json(silent=True) or {}
    template_id = data.get("template_id") # איזה תבנית הוא בחר?
    date        = data.get("workout_date")
    name        = data.get("name")
    if not template_id:
        return jsonify({"error": "template_id required"}), 400
        
    try:
        template_id = int(template_id)
    except ValueError:
        return jsonify({"error": "template_id must be an integer"}), 400
        
    workout_id = clone_from_template(g.user_id, template_id, date, name) # מעתיקים הכל!
    if not workout_id:
        return jsonify({"error": "Template not found or access denied"}), 404
    return jsonify({"id": workout_id, "message": "Workout cloned from template."}), 201


# מביא לנו את האימונים שמוצגים על הלוח שנה
@workouts_bp.route("/calendar", methods=["GET"])
@require_auth
def calendar():
    import datetime
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))
    rows  = get_workouts_for_month(g.user_id, year, month)
    return jsonify([dict(r) for r in rows]), 200


# מביא לנו גרף של "כמה קילוגרמים הרמתי השבוע"
@workouts_bp.route("/weekly-volume", methods=["GET"])
@require_auth
def weekly_volume():
    weeks = int(request.args.get("weeks", 8)) # מביא נתונים אחורה 8 שבועות
    rows  = get_weekly_volume(g.user_id, weeks)
    return jsonify([dict(r) for r in reversed(rows)]), 200


# מביא פרטים על אימון אחד ספציפי
@workouts_bp.route("/<int:workout_id>", methods=["GET"])
@require_auth
def detail(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id: # בודקים שאף אחד לא מנסה להציץ באימון של מישהו אחר
        return jsonify({"error": "Not found"}), 404
    full = get_full_workout(workout_id)
    return jsonify(full), 200


# עדכון שם של אימון קיים
@workouts_bp.route("/<int:workout_id>", methods=["PATCH"])
@require_auth
def update(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    update_workout(workout_id, data)
    return jsonify({"message": "Workout updated."}), 200
 
 
# כפתור "סיום אימון" (שמחשב לנו כמה זמן לקח וכו')
@workouts_bp.route("/<int:workout_id>/finish", methods=["POST"])
@require_auth
def finish(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    duration = data.get("duration_minutes")
    notes = data.get("notes")
    
    try:
        result = finish_workout(workout_id, duration, notes)
        if result:
            log_action(g.user_id, "workout_finished", f"id={workout_id}", request.remote_addr)
            return jsonify({"message": "Workout finished and metrics calculated."}), 200
        return jsonify({"error": "Workout not found in database"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to finish workout: {str(e)}"}), 500


# מחיקת אימון
@workouts_bp.route("/<int:workout_id>", methods=["DELETE"])
@require_auth
def remove(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    delete_workout(workout_id)
    return jsonify({"message": "Workout deleted."}), 200


# ── Exercises within a workout (הוספת תרגילים לאימון) ──

# כשאנחנו מוסיפים תרגיל חדש לרשימה של האימון (למשל: בנץ' פרס)
@workouts_bp.route("/<int:workout_id>/exercises", methods=["POST"])
@require_auth
def add_exercise(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    exercise_id = data.get("exercise_id") # איזה תרגיל מתוך הרשימה הכללית בחרנו?
    if not exercise_id:
        return jsonify({"error": "exercise_id required"}), 400
    we_id = add_exercise_to_workout(workout_id, exercise_id,
                                     data.get("position", 0), data.get("notes", ""))
    return jsonify({"id": we_id, "message": "Exercise added."}), 201


# כשאנחנו מתחרטים ומוחקים את התרגיל מהאימון
@workouts_bp.route("/exercises/<int:we_id>", methods=["DELETE"])
@require_auth
def remove_exercise(we_id):
    remove_exercise_from_workout(we_id)
    return jsonify({"message": "Exercise removed."}), 200


# ── Sets (סטים - כמה משקל וכמה חזרות) ──

# הוספת סט (כמו: עשיתי 10 חזרות של 50 קילו)
@workouts_bp.route("/exercises/<int:we_id>/sets", methods=["POST"])
@require_auth
def add_set_route(we_id):
    data = request.get_json(silent=True) or {}
    set_id = add_set(we_id, data)
    return jsonify({"id": set_id, "message": "Set added."}), 201


# עריכת סט אם טעינו בהקלדה
@workouts_bp.route("/sets/<int:set_id>", methods=["PATCH"])
@require_auth
def update_set_route(set_id):
    data = request.get_json(silent=True) or {}
    update_set(set_id, data)
    return jsonify({"message": "Set updated."}), 200


# מחיקת סט אם פתאום לא בא לנו לעשות אותו
@workouts_bp.route("/sets/<int:set_id>", methods=["DELETE"])
@require_auth
def delete_set_route(set_id):
    delete_set(set_id)
    return jsonify({"message": "Set deleted."}), 200


# ── Progression Charts (גרפים וניתוחי התקדמות) ──

# מבקש מהשרת את כל ההיסטוריה של תרגיל ספציפי (למשל "סקוואט") כדי לצייר גרף
@workouts_bp.route("/progression/<int:exercise_id>", methods=["GET"])
@require_auth
def progression(exercise_id):
    limit = int(request.args.get("limit", 30))
    rows  = get_exercise_progression(g.user_id, exercise_id, limit)
    return jsonify([dict(r) for r in reversed(rows)]), 200

"""
English Summary:
This file provides the REST API endpoints for managing workouts. It allows the frontend application 
to create new workouts, duplicate templates, add/remove exercises, and log specific sets (reps and weights).
It acts as the intermediary between the frontend interface and the database logic, ensuring users only 
have access to their own private workout data.

סיכום בעברית:
הקובץ הזה משמש כ"גשר" בין האפליקציה (מה שהמתאמן רואה) לבין מסד הנתונים בכל מה שקשור לאימונים.
כאן מתקבלות הבקשות ליצור אימון חדש, להוסיף תרגילים, לערוך סטים או למחוק אימון. הקובץ גם מוודא
באופן קפדני שכל מתאמן יכול לראות ולערוך אך ורק את האימונים שלו, ולא את אלה של אחרים.
"""
