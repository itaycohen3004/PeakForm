"""
Exercise library model — search, CRUD, and set-type resolution.
הקובץ הזה מנהל את כל התרגילים באפליקציה! הוא יודע לחפש תרגילים, לאשר תרגילים חדשים שמשתמשים שלחו, למצוא שיאים אישיים ועוד.
"""
from .db import get_db


# פונקציית עזר: שולחת הודעה פרטית מהמנהל למשתמש בלי לתקוע את המערכת אם משהו משתבש
def _send_admin_dm(user_id: int, message: str):
    """Non-blocking helper — sends a DM without crashing the caller."""
    try:
        from backend.models.chat import send_admin_dm_message
        send_admin_dm_message(user_id, message)
    except Exception:
        pass


# פונקציה לחיפוש תרגילים כשמישהו מקליד בתיבת החיפוש באפליקציה
def search_exercises(query: str = "", category: str = "", limit: int = 50, user_id: int = None):
    db = get_db()
    # אנחנו מחפשים רק תרגילים שאושרו (approved) או תרגילים ישנים ורגילים (שאין להם סטטוס בכלל)
    sql = "SELECT * FROM exercises WHERE (status = 'approved' OR (status IS NULL AND is_custom = 0)"
    params = []
    
    # אם אנחנו יודעים איזה משתמש מחפש:
    if user_id:
        # נוסיף גם את התרגילים הפרטיים שהוא המציא ועדיין ממתינים לאישור המנהל
        sql += " OR (status = 'pending' AND created_by = ?)"
        params.append(user_id)
        # ונוסיף גם את התרגילים שלו שהמנהל לא אישר אבל נשארים פרטיים שלו
        sql += " OR (status = 'rejected' AND created_by = ?)"
        params.append(user_id)
    sql += ")"
    
    # אם המשתמש הקליד שם של תרגיל:
    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
        
    # אם המשתמש סינן לפי קטגוריה (כמו "חזה", "רגליים"):
    if category:
        sql += " AND (category = ? OR muscles_tags LIKE ?)"
        params.append(category)
        params.append(f"%{category}%")
        
    # נסדר לפי סדר האלף-בית
    sql += " ORDER BY name LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()


# מביא את כל התרגילים שמשתמשים המציאו ומחכים שהמנהל יאשר אותם
def get_pending_exercises():
    """Admin: return all exercises awaiting approval."""
    db = get_db()
    # מחבר את זה לטבלת המשתמשים כדי שהמנהל יראה מי הציע את התרגיל
    return db.execute(
        """SELECT e.*, u.email as submitted_by_email
           FROM exercises e
           LEFT JOIN users u ON e.created_by = u.id
           WHERE e.status = 'pending'
           ORDER BY e.id DESC"""
    ).fetchall()


# הפונקציה למנהל - הוא לוחץ "אישור" והתרגיל נכנס לספריית התרגילים הציבורית
def approve_exercise(exercise_id: int):
    db = get_db()
    # קודם בודקים מי המציא את התרגיל כדי שנוכל להגיד לו כל הכבוד
    ex = db.execute("SELECT name, created_by FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    
    # משנים את הסטטוס ל"מאושר"
    db.execute("UPDATE exercises SET status = 'approved' WHERE id = ?", (exercise_id,))
    db.commit()
    
    # עכשיו אנחנו שולחים התראה באפליקציה למשתמש שהמציא אותו
    if ex and ex["created_by"]:
        try:
            db.execute(
                """INSERT INTO notifications (user_id, type, title, message, is_read, created_at)
                   VALUES (?, 'exercise_approved', ?, ?, 0, datetime('now'))""",
                (
                    ex["created_by"],
                    "Exercise Approved! ✅",
                    f"Your exercise \u201c{ex['name']}\u201d has been approved and is now in the library!",
                )
            )
            db.commit()
        except Exception:
            pass
        # ושולחים לו גם הודעה אישית יפה בצ'אט
        _send_admin_dm(
            ex["created_by"],
            f"\u2705 Your exercise **{ex['name']}** has been **approved** and is now live in the exercise library! Start adding it to your workouts."
        )


# הפונקציה למנהל - הוא לוחץ "דחייה" והתרגיל נשאר פרטי רק למי שהמציא אותו
def reject_exercise(exercise_id: int):
    db = get_db()
    ex = db.execute("SELECT name, created_by FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    
    # משנים את הסטטוס ל"נדחה"
    db.execute("UPDATE exercises SET status = 'rejected' WHERE id = ?", (exercise_id,))
    db.commit()
    
    # שולחים הודעה למשתמש שמסבירה מה קרה
    if ex and ex["created_by"]:
        try:
            db.execute(
                """INSERT INTO notifications (user_id, type, title, message, is_read, created_at)
                   VALUES (?, 'exercise_rejected', ?, ?, 0, datetime('now'))""",
                (
                    ex["created_by"],
                    "Exercise Not Approved",
                    f"Your exercise \u201c{ex['name']}\u201d was not approved. You can resubmit with more details.",
                )
            )
            db.commit()
        except Exception:
            pass
        # ושולחים הסבר אישי בצ'אט
        _send_admin_dm(
            ex["created_by"],
            f"\u274c Your exercise **{ex['name']}** was **not approved** at this time. "
            f"It remains available as a **private exercise** for you only. "
            f"You can still use it in your workouts and templates — it just won't appear in the public library."
        )


# מביא פרטים של תרגיל מסוים לפי המספר המזהה שלו
def get_exercise_by_id(exercise_id: int):
    db = get_db()
    return db.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()


# מביא פרטים של תרגיל לפי השם שלו בדיוק
def get_exercise_by_name(name: str):
    db = get_db()
    return db.execute("SELECT * FROM exercises WHERE name = ?", (name,)).fetchone()


# חיפוש חכם יותר לפי שם - קודם מחפש בדיוק אותו שם, ואם לא מוצא, מחפש שם דומה
def find_exercise_by_name(name: str):
    """Fuzzy-search by name (exact first, then LIKE)."""
    db = get_db()
    row = db.execute("SELECT * FROM exercises WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
    if row:
        return row
    return db.execute("SELECT * FROM exercises WHERE name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()


# יוצר תרגיל חדש שמשתמש בנה בעצמו! הסטטוס מתחיל כ"ממתין" לאישור
def create_custom_exercise(user_id: int, name: str, category: str,
                            set_type: str, muscles: str = "", equipment: str = "",
                            muscles_tags: str = "") -> int:
    """Create a user-submitted custom exercise — starts as 'pending' for admin approval."""
    db = get_db()
    cur = db.execute(
        """INSERT INTO exercises
           (name, category, set_type, muscles, muscles_tags, equipment, is_custom, created_by, status)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'pending')""",
        (name, category, set_type, muscles, muscles_tags, equipment, user_id),
    )
    db.commit()
    return cur.lastrowid # מחזיר את המספר המזהה של התרגיל החדש


# מוצא את הנתונים מהפעם האחרונה שעשית את התרגיל הזה (כדי להזכיר לך כמה הרמת)
def get_last_session(user_id: int, exercise_id: int) -> dict:
    """Return the most recent session sets for an exercise (for in-workout intel panel)."""
    db = get_db()
    # מוצא את האימון האחרון שסיימת שכלל את התרגיל הזה
    last_we = db.execute(
        """SELECT we.id, w.id as workout_id, w.workout_date, w.name as workout_name
           FROM workout_exercises we
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ? AND w.finished_at IS NOT NULL AND w.is_draft = 0
           ORDER BY w.workout_date DESC, w.id DESC
           LIMIT 1""",
        (user_id, exercise_id),
    ).fetchone()
    
    if not last_we:
        return None # לא עשית אותו אף פעם

    # מביא את הסטים של התרגיל מאותו אימון
    sets = db.execute(
        """SELECT set_number, weight_kg, reps, duration_seconds, is_warmup
           FROM workout_sets
           WHERE workout_exercise_id = ?
           ORDER BY set_number ASC""",
        (last_we["id"],),
    ).fetchall()

    # מסנן רק את הסטים שהם לא חימום, כדי לתת לך את המשקל "האמיתי" שהרמת
    working_sets = [dict(s) for s in sets if not s["is_warmup"]]
    return {
        "workout_date":  last_we["workout_date"],
        "workout_name":  last_we["workout_name"],
        "workout_id":    last_we["workout_id"],
        "sets":          working_sets,
        "best_weight":   max((s["weight_kg"] or 0 for s in working_sets), default=None),
        "best_reps":     max((s["reps"] or 0 for s in working_sets), default=None),
    }


# רשימה של כל קבוצות השרירים (קטגוריות) שאפשר לבחור מהן
def get_all_categories():
    return ["chest","back","shoulders","arms","legs","core","full_body","skill","cardio"]


# מביא את כל ההיסטוריה שלך בתרגיל הזה (כדי לצייר לך גרף של התקדמות)
def get_exercise_history(user_id: int, exercise_id: int, limit: int = 20):
    """Return all sets for a given exercise across all workouts, newest first."""
    db = get_db()
    return db.execute(
        """SELECT w.workout_date, w.name as workout_name, w.id as workout_id,
                  ws.set_number, ws.reps, ws.weight_kg, ws.duration_seconds,
                  ws.is_warmup, ws.rpe
           FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ?
           ORDER BY w.workout_date DESC, ws.set_number ASC
           LIMIT ?""",
        (user_id, exercise_id, limit),
    ).fetchall()


# מחשב את "השיאים האישיים" (PRs - Personal Records) שלך בתרגיל הזה
def get_exercise_prs(user_id: int, exercise_id: int) -> dict:
    """Return personal records for an exercise."""
    db = get_db()
    # המשקל הכי כבד שהרמת בו אי פעם
    max_weight = db.execute(
        """SELECT MAX(ws.weight_kg) as val FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ? AND ws.is_warmup = 0""",
        (user_id, exercise_id),
    ).fetchone()["val"]

    # הכי הרבה חזרות שעשית בסט אחד
    max_reps = db.execute(
        """SELECT MAX(ws.reps) as val FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ? AND ws.is_warmup = 0""",
        (user_id, exercise_id),
    ).fetchone()["val"]

    # הזמן הכי ארוך שהחזקת (אם זה תרגיל של זמן כמו פלאנק)
    max_time = db.execute(
        """SELECT MAX(ws.duration_seconds) as val FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ? AND ws.is_warmup = 0""",
        (user_id, exercise_id),
    ).fetchone()["val"]

    return {
        "max_weight_kg": max_weight,
        "max_reps": max_reps,
        "max_time_seconds": max_time,
    }


# למנהלים בלבד: מאפשר לעדכן פרטים של תרגיל קיים (כמו לשנות לו קטגוריה)
def update_exercise(exercise_id: int, name: str, category: str, set_type: str, muscles_tags: str, equipment: str):
    db = get_db()
    db.execute("""
        UPDATE exercises 
        SET name = ?, category = ?, set_type = ?, muscles_tags = ?, equipment = ?
        WHERE id = ?
    """, (name, category, set_type, muscles_tags, equipment, exercise_id))
    db.commit()


# למנהלים בלבד: "מוחק" תרגיל על ידי סימון שהוא נמחק, ולא באמת מוחק אותו כדי לא לשבור אימונים של אנשים
def delete_exercise(exercise_id: int):
    """Mark exercise as deleted instead of dropping to preserve foreign keys."""
    db = get_db()
    db.execute("UPDATE exercises SET status = 'deleted' WHERE id = ?", (exercise_id,))
    db.commit()

"""
English Summary:
This file is the database model layer for Exercises. It provides powerful query functions 
to filter exercises by category and permission scope (public library vs. user's private pending submissions).
It includes the logic for Admin approval/rejection workflows which automatically dispatch DMs 
and notifications. Finally, it provides specialized analytical queries to fetch a user's 
personal records (PRs) and their most recent session data for a specific exercise to power 
the intelligent workout logger.
"""
