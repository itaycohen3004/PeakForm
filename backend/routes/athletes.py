"""
PeakForm — Athletes routes (profile, stats, dashboard, PR tracking).
קובץ זה מנהל את הפרופיל של המתאמן! כאן רואים את לוח הבקרה (הדשבורד),
את התמונה שלו, את הסטטיסטיקות והשיאים האישיים שלו.
"""
import os
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from backend.middleware.auth import require_auth
from backend.models.athlete import (
    Athlete, get_athlete_profile, create_athlete_profile,
    update_athlete_profile, get_athlete_stats,
)
from backend.models.audit import log_action
from backend.models.db import get_db

athletes_bp = Blueprint("athletes", __name__, url_prefix="/api/athletes")


# מביא לנו את פרופיל המתאמן (מידע אישי, שם, גיל וכו')
@athletes_bp.route("/profile", methods=["GET"])
@require_auth
def get_profile():
    row = get_athlete_profile(g.user_id)
    if not row:
        return jsonify({"error": "Profile not found"}), 404
    athlete = Athlete(dict(row))
    return jsonify(athlete.to_dict()), 200


# עדכון הפרופיל האישי (למשל אם המתאמן רוצה לשנות את המשקל יעד שלו)
@athletes_bp.route("/profile", methods=["PUT"])
@require_auth
def update_profile():
    data = request.get_json(silent=True) or {}
    profile = get_athlete_profile(g.user_id)
    if not profile:
        create_athlete_profile(
            g.user_id,
            data.get("display_name", "Athlete"),
            **data,
        )
    else:
        update_athlete_profile(g.user_id, data)
    log_action(g.user_id, "profile_updated", None, request.remote_addr)
    return jsonify({"message": "Profile updated."}), 200


# העלאת תמונת פרופיל מהטלפון או המחשב
@athletes_bp.route("/avatar", methods=["POST"])
@require_auth
def upload_avatar():
    if "avatar" not in request.files: # בודקים אם באמת שלחו קובץ
        return jsonify({"error": "No file provided"}), 400
    file = request.files["avatar"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
        
    # שומרים את התמונה בתיקייה מיוחדת בתוך פרויקט השרת
    upload_dir = os.path.join(os.getcwd(), "frontend", "static", "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f"avatar_{g.user_id}_{file.filename}")
    file.save(os.path.join(upload_dir, filename))
    url = f"/static/uploads/avatars/{filename}"
    
    # מעדכנים לפרופיל את הכתובת של התמונה החדשה
    update_athlete_profile(g.user_id, {"avatar_url": url})
    return jsonify({"avatar_url": url}), 200


# מביא נתונים כלליים למתאמן (כמה אימונים עשיתי החודש?)
@athletes_bp.route("/stats", methods=["GET"])
@require_auth
def stats():
    s = get_athlete_stats(g.user_id)
    return jsonify(s), 200


# ה"מוח" המרכזי של עמוד הבית! מביא בבת אחת את כל המידע כדי שהאפליקציה תעלה מהר.
@athletes_bp.route("/dashboard", methods=["GET"])
@require_auth
def dashboard():
    """Combined dashboard data in one efficient call."""
    from backend.models.athlete import get_athlete_profile, get_athlete_stats
    from backend.models.workout import get_workouts, get_weekly_volume
    from backend.models.goal import get_goals
    from backend.models.body_weight import get_latest_body_weight

    try:
        profile = get_athlete_profile(g.user_id)
    except Exception:
        profile = None

    try:
        stats_data = get_athlete_stats(g.user_id)
    except Exception:
        stats_data = {}

    try:
        recent = get_workouts(g.user_id, limit=8) # מביא 8 אימונים אחרונים
    except Exception:
        recent = []

    try:
        volume = get_weekly_volume(g.user_id, weeks=8) # כמה משקל סחבתי ב-8 השבועות האחרונים
    except Exception:
        volume = []

    try:
        goals = get_goals(g.user_id, include_completed=True) # המטרות שלי
    except Exception:
        goals = []

    try:
        latest_bw = get_latest_body_weight(g.user_id) # השקילה האחרונה שלי
    except Exception:
        latest_bw = None

    try:
        from backend.models.template import get_today_template
        today_tpl = get_today_template(g.user_id)
    except Exception:
        today_tpl = None

    # סופרים כמה התראות חדשות יש למשתמש (פעמון שלא נקרא)
    try:
        db = get_db()
        unread = db.execute(
            "SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0",
            (g.user_id,)
        ).fetchone()["c"]
    except Exception:
        unread = 0

    # Build athlete object for extra metadata
    try:
        athlete_obj = Athlete(dict(profile)) if profile else None
    except Exception:
        athlete_obj = None

    # אוספים כמה תרגילים יש בכל אימון שחזר
    recent_list = []
    for w in recent:
        wd = dict(w)
        try:
            db = get_db()
            cnt = db.execute(
                "SELECT COUNT(*) as c FROM workout_exercises WHERE workout_id=?",
                (wd["id"],)
            ).fetchone()["c"]
            wd["exercise_count"] = cnt
        except Exception:
            wd["exercise_count"] = 0
        recent_list.append(wd)

    # אורזים את הכל לחבילה ענקית וסופר מהירה ושולחים לדפדפן
    return jsonify({
        "profile":            athlete_obj.to_dict() if athlete_obj else None,
        "stats":              stats_data,
        "recent_workouts":    recent_list,
        "weekly_volume":      [dict(v) for v in reversed(list(volume))],
        "goals":              [dict(g2) for g2 in goals],
        "latest_body_weight": dict(latest_bw) if latest_bw else None,
        "today_template":     dict(today_tpl) if today_tpl else None,
        "unread_notifications": unread,
    }), 200


# מביא את כל השיאים האישיים (Personal Records) שהמתאמן הגיע אליהם
@athletes_bp.route("/prs", methods=["GET"])
@require_auth
def get_prs():
    """Return personal records for all exercises."""
    db = get_db()
    rows = db.execute(
        """SELECT pr.*, e.name as exercise_name, e.category, e.muscles
           FROM personal_records pr
           JOIN exercises e ON pr.exercise_id = e.id
           WHERE pr.user_id = ?
           ORDER BY e.category, e.name""",
        (g.user_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows]), 200


# מחשב מחדש מיד את השיאים האישיים כדי שאם עשיתי שיא באימון האחרון זה יתעדכן!
@athletes_bp.route("/prs/compute", methods=["POST"])
@require_auth
def compute_prs():
    """
    Scan all workout sets and update PRs for the user.
    Can be called after saving a workout.
    """
    db = get_db()

    # Get all sets with weight and reps for this user
    rows = db.execute(
        """SELECT ws.weight_kg, ws.reps, we.exercise_id, w.id as workout_id, w.workout_date
           FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id=? AND ws.weight_kg IS NOT NULL AND ws.reps IS NOT NULL
             AND ws.weight_kg > 0 AND ws.reps > 0 AND ws.is_warmup=0
           ORDER BY ws.weight_kg DESC""",
        (g.user_id,)
    ).fetchall()

    # Group by exercise, find best weight
    best_per_exercise = {}
    for r in rows:
        ex_id = r["exercise_id"]
        w = r["weight_kg"]
        reps = r["reps"]
        # נוסחה שמחשבת כמה המשקל המקסימלי שהיית מצליח להרים לחזרה אחת (1RM)
        one_rm = w * (1 + reps / 30) if reps > 1 else w

        if ex_id not in best_per_exercise or one_rm > best_per_exercise[ex_id]["estimated_1rm"]:
            best_per_exercise[ex_id] = {
                "exercise_id":    ex_id,
                "weight_kg":      w,
                "reps":           reps,
                "estimated_1rm":  round(one_rm, 1),
                "workout_id":     r["workout_id"],
                "achieved_at":    r["workout_date"],
            }

    updated = 0
    # שומרים את כל השיאים ששברו את השיא הישן
    for ex_id, pr in best_per_exercise.items():
        db.execute(
            """INSERT INTO personal_records
                   (user_id, exercise_id, weight_kg, reps, estimated_1rm, achieved_at, workout_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, exercise_id) DO UPDATE SET
                   weight_kg     = excluded.weight_kg,
                   reps          = excluded.reps,
                   estimated_1rm = excluded.estimated_1rm,
                   achieved_at   = excluded.achieved_at,
                   workout_id    = excluded.workout_id
               WHERE excluded.estimated_1rm > personal_records.estimated_1rm""",
            (g.user_id, ex_id, pr["weight_kg"], pr["reps"],
             pr["estimated_1rm"], pr["achieved_at"], pr["workout_id"])
        )
        updated += 1

    db.commit()
    return jsonify({"message": f"PRs computed.", "exercises_checked": updated}), 200

"""
English Summary:
This file handles routes related to the athlete's personal profile, such as retrieving and 
updating profile details, uploading avatars, fetching dashboard aggregate stats, and calculating 
Personal Records (PRs) based on completed workout sets using the 1RM (One Rep Max) Epley formula.

סיכום בעברית:
קובץ זה מנהל את הפרופיל האישי של המתאמן ואת מסך הבית (הדשבורד). הוא מאפשר למתאמן להעלות 
תמונת פרופיל ולעדכן נתונים אישיים. בנוסף, הוא מכיל לוגיקה חכמה שקוראת את כל האימונים הקודמים 
ומחשבת באופן אוטומטי את "השיאים האישיים" (PRs) של המתאמן לכל תרגיל.
"""
