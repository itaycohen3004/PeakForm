import datetime
import calendar
import json
from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data

# ============================================================
# מחלקת אימון (WorkoutSession)
# מחלקה זו מייצגת אימון אחד של מתאמן. היא כמו "תבנית" לאימון שמכילה את כל המידע עליו:
# מתי התחיל, מתי הסתיים, כמה זמן לקח, וכמה סטים ותחנות היו בו.
# ============================================================
class WorkoutSession:
    def __init__(self, id=None, user_id=None, template_id=None, name=None, workout_date=None,
                 started_at=None, finished_at=None, duration_minutes=0, total_sets=0,
                 total_reps=0, total_volume_kg=0, muscles_worked=None, notes=None,
                 is_draft=0, created_at=None, **kwargs):
        """
        כאן אנחנו יוצרים את האימון ושומרים את כל הפרטים שלו במשתנים כדי שנוכל להשתמש בהם אחר כך.
        """
        self.id = id # המספר המזהה של האימון במסד הנתונים
        self.user_id = user_id # המספר של המשתמש שעשה את האימון
        self.template_id = template_id # אם האימון מבוסס על תוכנית קיימת, נשמור את המספר שלה
        self.name = name # שם האימון (למשל: "אימון חזה וגב")
        self.workout_date = workout_date # התאריך שבו התבצע האימון
        self.started_at = started_at # השעה המדויקת שבה האימון התחיל
        self.finished_at = finished_at # השעה המדויקת שבה האימון הסתיים
        self.duration_minutes = duration_minutes or 0 # כמה דקות לקח האימון
        self.total_sets = total_sets or 0 # כמה סטים בסך הכל המתאמן עשה
        self.total_reps = total_reps or 0 # כמה חזרות בסך הכל
        self.total_volume_kg = total_volume_kg or 0 # סך הכל המשקל שהמתאמן הרים (נפח האימון)
        self.muscles_worked = muscles_worked # איזה שרירים עבדו באימון הזה
        self.notes = notes # הערות שהמתאמן כתב על האימון
        self.is_draft = is_draft or 0 # האם האימון הזה הוא רק טיוטה (עדיין לא הסתיים)
        self.created_at = created_at # מתי יצרנו את הרשומה הזו במערכת

    @staticmethod
    def get_by_id(workout_id):
        """
        פונקציה שמביאה את האימון ממסד הנתונים לפי המספר המזהה שלו.
        """
        db = get_db() # מתחברים למסד הנתונים (הטבלאות ששומרות את המידע)
        # מחפשים בטבלת 'workouts' את האימון עם המספר שביקשנו
        row = db.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
        if row:
            # אם מצאנו את האימון, ניצור אובייקט של אימון ונחזיר אותו
            return WorkoutSession(**dict(row))
        return None # אם לא מצאנו, נחזיר "כלום"

    def finish(self, duration=None, notes=None):
        """
        פונקציה שמסיימת את האימון.
        היא מחשבת את כל הנתונים הסופיים (כמה סטים, משקל כולל, ושרירים) ושומרת אותם.
        """
        import traceback
        db = get_db()
        # שומרים את השעה המדויקת של סיום האימון
        self.finished_at = datetime.datetime.now().isoformat()
        
        # מעדכנים כמה זמן האימון לקח, אם קיבלנו את המידע הזה
        if duration is not None:
            self.duration_minutes = int(duration)
        # מעדכנים את ההערות אם יש, ומצפינים אותן כדי שאף אחד לא יוכל לקרוא בלי אישור
        if notes is not None:
            self.notes = encrypt_data(notes) if notes else None

        # עכשיו אנחנו הולכים למסד הנתונים ומביאים את כל התרגילים והסטים שהיו באימון הזה
        sets_data = db.execute("""
            SELECT ws.reps, ws.weight_kg, e.muscles
            FROM workout_sets ws
            JOIN workout_exercises we ON ws.workout_exercise_id = we.id
            LEFT JOIN exercises e ON we.exercise_id = e.id
            WHERE we.workout_id = ?
        """, (self.id,)).fetchall()

        # סופרים כמה סטים היו בסך הכל
        total_sets = len(sets_data)
        # סוכמים את כל החזרות מכל הסטים
        total_reps = sum(s["reps"] or 0 for s in sets_data)
        # מחשבים את המשקל הכולל: מכפילים חזרות במשקל לכל סט ומחברים הכל
        total_volume = sum((s["reps"] or 0) * (s["weight_kg"] or 0) for s in sets_data)
        
        # אוספים את כל השרירים שעבדו באימון הזה לרשימה בלי כפילויות
        muscles = set()
        for s in sets_data:
            if s["muscles"]:
                for m in s["muscles"].split(','):
                    muscles.add(m.strip().lower())
        
        # מעדכנים את הנתונים בתוך אובייקט האימון
        self.total_sets = total_sets
        self.total_reps = total_reps
        self.total_volume_kg = round(total_volume, 1) # מעגלים את המשקל למספר נוח
        self.muscles_worked = ",".join(sorted(muscles)) # הופכים את השרירים לטקסט מופרד בפסיקים

        # מעדכנים את השורה במסד הנתונים עם כל הנתונים החדשים שחישבנו
        db.execute("""
            UPDATE workouts SET 
                finished_at = ?, duration_minutes = ?, total_sets = ?, 
                total_reps = ?, total_volume_kg = ?, muscles_worked = ?, 
                notes = ?, is_draft = 0
            WHERE id = ?
        """, (self.finished_at, self.duration_minutes, self.total_sets, 
              self.total_reps, self.total_volume_kg, self.muscles_worked, 
              self.notes, self.id))
        db.commit() # שומרים סופית את כל השינויים

# --- פונקציות עזר ישנות ---
def finish_workout(workout_id: int, duration: int = None, notes: str = None):
    """
    פונקציית עזר קטנה שקוראת לפונקציית הסיום של האימון ובודקת אם הכל עבד כמו שצריך.
    """
    import traceback
    try:
        # מחפשים את האימון
        ws = WorkoutSession.get_by_id(workout_id)
        if not ws:
            print(f"[finish_workout] Workout {workout_id} not found in DB")
            return False # אם לא מצאנו, מחזירים "שקר" (נכשל)
        # אם מצאנו, מסיימים אותו
        ws.finish(duration, notes)
        return True # מחזירים "אמת" (הצליח)
    except Exception as exc:
        # אם הייתה שגיאה לא צפויה במחשב, מדפיסים אותה
        print(f"[finish_workout] ERROR finishing workout {workout_id}: {exc}")
        traceback.print_exc()
        raise

# ============================================================
# פונקציות שמטפלות באימונים (יצירה, קריאה, עדכון ומחיקה)
# ============================================================

def create_workout(user_id: int, data: dict) -> int:
    """
    פונקציה שיוצרת אימון חדש ושומרת אותו במסד הנתונים.
    """
    db = get_db()

    # מוסיפים שורה חדשה לטבלת האימונים
    cur = db.execute(
        """
        INSERT INTO workouts
        (user_id, template_id, name, workout_date, started_at, finished_at, duration_minutes, notes, is_draft)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, # מספר המשתמש
            data.get("template_id"), # מספר התבנית אם יש
            data.get("name"), # שם האימון
            data.get("workout_date") or datetime.date.today().isoformat(), # אם אין תאריך, נשתמש בתאריך של היום
            data.get("started_at"),
            data.get("finished_at"),
            data.get("duration_minutes"),
            encrypt_data(data.get("notes")), # מצפינים את ההערות בשביל פרטיות
            int(data.get("is_draft", 0)), # קובעים אם זה טיוטה או לא
        ),
    )

    db.commit() # שומרים שינויים
    return cur.lastrowid # מחזירים את המספר המזהה החדש של האימון שנוצר

def get_workout(workout_id: int):
    """
    פונקציה שמביאה אימון אחד בלבד לפי המספר שלו.
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM workouts WHERE id = ?",
        (workout_id,)
    ).fetchone()


def get_workouts(user_id: int, limit: int = 30, offset: int = 0):
    """
    פונקציה שמביאה רשימה של האימונים של משתמש מסוים, מסודרים מהחדש לישן.
    היא גם סופרת כמה תרגילים וכמה סטים היו בכל אימון.
    """
    db = get_db()

    rows = db.execute(
        """
        SELECT w.*,
               COUNT(DISTINCT we.id) as exercise_count,
               COUNT(ws.id) as set_count
        FROM workouts w
        LEFT JOIN workout_exercises we ON we.workout_id = w.id
        LEFT JOIN workout_sets ws ON ws.workout_exercise_id = we.id
        WHERE w.user_id = ?
        GROUP BY w.id
        ORDER BY w.workout_date DESC, w.created_at DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset), # המספרים שקובעים למי שייך המידע, כמה להביא ומאיפה להתחיל
    ).fetchall()

    result = []
    # עוברים על כל האימונים שמצאנו
    for row in rows:
        item = dict(row)
        # מפענחים (הופכים חזרה לטקסט קריא) את ההערות כדי שהמשתמש יוכל לקרוא אותן
        item["notes"] = decrypt_data(item.get("notes"))
        result.append(item)

    return result


def get_workouts_for_month(user_id: int, year: int, month: int):
    """
    מביאה את כל האימונים שעשה המשתמש בחודש ושנה מסוימים (בשביל להציג בלוח השנה).
    """
    db = get_db()

    # מגדירים את היום הראשון והאחרון של החודש המבוקש
    start = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{last_day}"

    return db.execute(
        """
        SELECT
            w.workout_date,
            COUNT(DISTINCT w.id) as count,
            COUNT(ws.id) as set_count,
            COALESCE(SUM(w.duration_minutes), 0) as duration_minutes
        FROM workouts w
        LEFT JOIN workout_exercises we ON we.workout_id = w.id
        LEFT JOIN workout_sets ws ON ws.workout_exercise_id = we.id
        WHERE w.user_id = ? AND w.workout_date BETWEEN ? AND ?
        GROUP BY w.workout_date
        ORDER BY w.workout_date
        """,
        (user_id, start, end),
    ).fetchall()

def update_workout(workout_id: int, data: dict):
    """
    פונקציה שמעדכנת פרטים של אימון קיים (למשל אם רוצים לשנות לו את השם).
    """
    db = get_db()

    # אלו השדות שמותר לעדכן:
    allowed = [
        "name",
        "workout_date",
        "notes",
        "duration_minutes",
        "finished_at",
        "is_draft",
    ]

    # לוקחים רק את הנתונים שמותר לעדכן
    updates = {k: v for k, v in data.items() if k in allowed}

    # אם ניסו לשים תאריך ריק, נחזיר את תאריך היום
    if "workout_date" in updates and not updates["workout_date"]:
        updates["workout_date"] = datetime.date.today().isoformat()

    # אם שלחו הערות חדשות, מצפינים אותן שוב
    if "notes" in updates:
        updates["notes"] = encrypt_data(updates["notes"])

    if updates:
        # בונים את הפקודה שתשנה את הנתונים במסד הנתונים
        fields = ", ".join(f"{k} = ?" for k in updates.keys())

        db.execute(
            f"UPDATE workouts SET {fields} WHERE id = ?",
            list(updates.values()) + [workout_id]
        )
        db.commit()


def delete_workout(workout_id: int):
    """
    פונקציה שמוחקת אימון לגמרי ממסד הנתונים.
    """
    db = get_db()
    db.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    db.commit()


# ============================================================
# תרגילי אימון (תרגילים שנמצאים בתוך האימון עצמו)
# ============================================================

def add_exercise_to_workout(
    workout_id: int,
    exercise_id: int,
    position: int = 0,
    notes: str = ""
) -> int:
    """
    פונקציה שמוסיפה תרגיל חדש לתוך האימון. (למשל: מוסיפה כפיפות בטן לאימון).
    """
    db = get_db()

    cur = db.execute(
        """
        INSERT INTO workout_exercises
        (workout_id, exercise_id, position, notes)
        VALUES (?, ?, ?, ?)
        """,
        (
            workout_id, # מזהה האימון
            exercise_id, # מזהה התרגיל מתוך מאגר התרגילים הכללי
            position, # המיקום של התרגיל באימון (ראשון, שני וכו')
            encrypt_data(notes), # הערות ספציפיות לתרגיל הזה באימון הזה (מוצפנות כמובן)
        ),
    )

    db.commit()
    return cur.lastrowid


def get_workout_exercises(workout_id: int):
    """
    מביאה את כל התרגילים ששייכים לאימון ספציפי.
    """
    db = get_db()

    rows = db.execute(
        """
        SELECT we.*,
               e.name as exercise_name,
               e.category,
               e.set_type,
               e.muscles,
               e.equipment
        FROM workout_exercises we
        JOIN exercises e ON we.exercise_id = e.id
        WHERE we.workout_id = ?
        ORDER BY we.position
        """,
        (workout_id,),
    ).fetchall()

    result = []

    for row in rows:
        item = dict(row)
        # מפענחים את ההערות של התרגיל
        item["notes"] = decrypt_data(item.get("notes"))
        result.append(item)

    return result


def remove_exercise_from_workout(workout_exercise_id: int):
    """
    מוחקת תרגיל מתוך האימון.
    """
    db = get_db()
    db.execute(
        "DELETE FROM workout_exercises WHERE id = ?",
        (workout_exercise_id,)
    )
    db.commit()


# ============================================================
# סטים (כמה פעמים עושים כל תרגיל וכמה משקל מרימים)
# ============================================================

def add_set(workout_exercise_id: int, data: dict) -> int:
    """
    מוסיפה סט חדש לאחד התרגילים באימון (למשל: סט של 10 חזרות עם משקולות של 5 קילו).
    """
    db = get_db()

    cur = db.execute(
        """
        INSERT INTO workout_sets
        (
            workout_exercise_id,
            set_number,
            reps,
            weight_kg,
            duration_seconds,
            rpe,
            is_warmup,
            is_failure
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workout_exercise_id, # לאיזה תרגיל מתוך האימון שייך הסט הזה
            data.get("set_number", 1), # איזה מספר הסט הזה (ראשון, שני...)
            data.get("reps"), # כמה חזרות עשה
            data.get("weight_kg"), # כמה משקל הרים
            data.get("duration_seconds"), # כמה זמן הסט לקח
            data.get("rpe"), # עד כמה קשה היה הסט (מ-1 עד 10)
            int(data.get("is_warmup", False)), # האם זה סט חימום
            int(data.get("is_failure", False)), # האם הגיע ל"כשל" (לא יכל לעשות עוד חזרה אחת)
        ),
    )

    db.commit()
    return cur.lastrowid


def update_set(set_id: int, data: dict):
    """
    פונקציה שמעדכנת נתונים של סט קיים.
    """
    db = get_db()

    allowed = [
        "reps",
        "weight_kg",
        "duration_seconds",
        "rpe",
        "is_warmup",
        "is_failure",
        "set_number",
    ]

    updates = {k: v for k, v in data.items() if k in allowed}

    if updates:
        fields = ", ".join(f"{k} = ?" for k in updates.keys())

        db.execute(
            f"UPDATE workout_sets SET {fields} WHERE id = ?",
            list(updates.values()) + [set_id]
        )
        db.commit()


def delete_set(set_id: int):
    """
    פונקציה שמוחקת סט.
    """
    db = get_db()
    db.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
    db.commit()


def get_sets_for_exercise(workout_exercise_id: int):
    """
    מביאה את כל הסטים שקשורים לתרגיל מסוים באימון.
    """
    db = get_db()

    return db.execute(
        """
        SELECT *
        FROM workout_sets
        WHERE workout_exercise_id = ?
        ORDER BY set_number
        """,
        (workout_exercise_id,),
    ).fetchall()

def get_full_workout(workout_id: int) -> dict:
    """
    פונקציה שמביאה את "החבילה המלאה" - את כל הנתונים על האימון, התרגילים שבו, והסטים בכל תרגיל!
    """
    db = get_db()

    # קודם מביאים את האימון עצמו
    workout = db.execute(
        "SELECT * FROM workouts WHERE id = ?",
        (workout_id,)
    ).fetchone()

    if not workout:
        return None

    # אחר כך מביאים את כל התרגילים שלו
    exercises_rows = get_workout_exercises(workout_id)
    exercises = []

    # עוברים על כל תרגיל ומביאים את הסטים שלו
    for ex in exercises_rows:
        sets = get_sets_for_exercise(ex["id"])
        ex_dict = dict(ex)
        ex_dict["sets"] = [dict(s) for s in sets] # מכניסים את הסטים לתוך התרגיל
        exercises.append(ex_dict)

    result = dict(workout)
    result["notes"] = decrypt_data(result.get("notes")) # מפענחים הערות אימון
    result["exercises"] = exercises # מכניסים את כל התרגילים והסטים לתוך האימון

    # אם האימון מבוסס על תבנית, מנסים למצוא את הפעם הקודמת שהמתאמן עשה את אותו אימון
    # כדי שנוכל להראות לו אם הוא השתפר!
    if result.get("template_id"):
        prev = db.execute(
            """
            SELECT *
            FROM workouts
            WHERE user_id = ? AND template_id = ? AND id < ?
            ORDER BY workout_date DESC, id DESC
            LIMIT 1
            """,
            (workout["user_id"], workout["template_id"], workout_id),
        ).fetchone()

        if prev:
            # אם מצאנו את האימון הקודם, מחשבים כמה משקל סך הכל הוא הרים אז
            prev_vol_row = db.execute(
                """
                SELECT SUM(COALESCE(ws.weight_kg, 0) * COALESCE(ws.reps, 1)) as vol
                FROM workout_sets ws
                JOIN workout_exercises we ON ws.workout_exercise_id = we.id
                WHERE we.workout_id = ? AND ws.is_warmup = 0
                """,
                (prev["id"],),
            ).fetchone()

            prev_vol = prev_vol_row["vol"] if prev_vol_row else 0

            # שומרים את הנתונים הישנים כדי שנוכל להשוות
            result["previous_stats"] = {
                "id": prev["id"],
                "date": prev["workout_date"],
                "volume_kg": round(prev_vol or 0, 1),
                "duration_minutes": prev["duration_minutes"],
            }

    return result


def get_weekly_volume(user_id: int, weeks: int = 8):
    """
    פונקציה שמחשבת את הנפח השבועי של מתאמן (כמה אימונים עשה, כמה סטים, ומשקל כולל בכל שבוע).
    זה טוב כדי להציג את זה בגרף יפה באפליקציה!
    """
    db = get_db()

    return db.execute(
        """
        SELECT strftime('%Y-W%W', workout_date) as week,
               COUNT(DISTINCT w.id) as workouts,
               COUNT(ws.id) as total_sets,
               ROUND(SUM(COALESCE(ws.weight_kg, 0) * COALESCE(ws.reps, 1)), 1) as total_volume_kg
        FROM workouts w
        LEFT JOIN workout_exercises we ON we.workout_id = w.id
        LEFT JOIN workout_sets ws ON ws.workout_exercise_id = we.id
        WHERE w.user_id = ?
        GROUP BY week
        ORDER BY week DESC
        LIMIT ?
        """,
        (user_id, weeks),
    ).fetchall()


def get_exercise_progression(user_id: int, exercise_id: int, limit: int = 30):
    """
    בודקת את ההתקדמות של המשתמש בתרגיל ספציפי (האם הוא מרים יותר משקל עכשיו מפעם שעברה?).
    """
    db = get_db()

    return db.execute(
        """
        SELECT
            w.workout_date,
            MAX(ws.weight_kg) as best_weight,
            MAX(ws.reps) as best_reps,
            MAX(ws.duration_seconds) as best_time,
            ROUND(SUM(COALESCE(ws.weight_kg, 0) * COALESCE(ws.reps, 0)), 1) as volume_kg,
            COUNT(ws.id) as set_count
        FROM workout_sets ws
        JOIN workout_exercises we ON ws.workout_exercise_id = we.id
        JOIN workouts w ON we.workout_id = w.id
        WHERE w.user_id = ?
          AND we.exercise_id = ?
          AND ws.is_warmup = 0
        GROUP BY w.workout_date
        ORDER BY w.workout_date DESC
        LIMIT ?
        """,
        (user_id, exercise_id, limit),
    ).fetchall()

def clone_from_template(user_id: int, template_id: int, workout_date: str, name: str = None) -> int:
    """
    לוקחת "תבנית אימון" מוכנה מראש ומעתיקה אותה כדי ליצור למשתמש אימון חדש לפי התבנית הזו.
    """
    db = get_db()

    # מחפשת את התבנית במסד הנתונים
    template = db.execute(
        "SELECT * FROM workout_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    ).fetchone()

    if not template:
        return None

    # יוצרת אימון ריק חדש
    workout_id = create_workout(
        user_id,
        {
            "template_id": template_id,
            "name": name or template["name"],
            "workout_date": workout_date,
        },
    )

    # מביאה את כל התרגילים מהתבנית
    template_exercises = db.execute(
        """
        SELECT *
        FROM template_exercises
        WHERE template_id = ?
        ORDER BY position
        """,
        (template_id,),
    ).fetchall()

    # מעתיקה כל תרגיל מהתבנית לאימון החדש
    for te in template_exercises:
        raw_notes = decrypt_data(te["notes"]) if te["notes"] else ""

        workout_exercise_id = add_exercise_to_workout(
            workout_id,
            te["exercise_id"],
            te["position"],
            raw_notes,
        )

        # מעתיקה גם את הסטים שהוגדרו בתבנית
        template_sets = db.execute(
            """
            SELECT *
            FROM template_exercise_sets
            WHERE template_exercise_id = ?
            ORDER BY set_number
            """,
            (te["id"],),
        ).fetchall()

        for s in template_sets:
            add_set(
                workout_exercise_id,
                {
                    "set_number": s["set_number"],
                    "reps": s["target_reps"],
                    "weight_kg": s["target_weight"],
                    "duration_seconds": s["target_seconds"],
                    "rpe": s["rpe"],
                },
            )

    # מחזירה את המספר המזהה של האימון החדש המלא שיצרנו
    return workout_id

"""
English Summary:
This module represents the core data model for a live Workout Session. It leverages the 
WorkoutSession class (OOP) to manage the state of an active workout. It provides functions to 
dynamically create and add exercises and individual sets to a draft workout. Once completed, 
the `finish` function aggregates total volume, sets, reps, and muscles worked, finalizing the 
record in the database. It also handles cloning predefined templates into actionable live workouts.
"""
