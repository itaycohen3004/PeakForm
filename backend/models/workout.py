import datetime
import calendar
import json
from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data

class WorkoutSession:
    def __init__(self, id=None, user_id=None, template_id=None, name=None, workout_date=None, 
                 started_at=None, finished_at=None, duration_minutes=0, total_sets=0, 
                 total_reps=0, total_volume_kg=0, muscles_worked=None, notes=None):
        self.id = id
        self.user_id = user_id
        self.template_id = template_id
        self.name = name
        self.workout_date = workout_date
        self.started_at = started_at
        self.finished_at = finished_at
        self.duration_minutes = duration_minutes
        self.total_sets = total_sets
        self.total_reps = total_reps
        self.total_volume_kg = total_volume_kg
        self.muscles_worked = muscles_worked
        self.notes = notes

    @staticmethod
    def get_by_id(workout_id):
        db = get_db()
        row = db.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
        if row:
            return WorkoutSession(**dict(row))
        return None

    def finish(self, duration=None, notes=None):
        """Calculate and save final workout data."""
        db = get_db()
        self.finished_at = datetime.datetime.now().isoformat()
        if duration: self.duration_minutes = duration
        if notes: self.notes = encrypt_data(notes)

        # Calculate metrics
        sets_data = db.execute("""
            SELECT ws.reps, ws.weight_kg, e.muscles
            FROM workout_sets ws
            JOIN workout_exercises we ON ws.workout_exercise_id = we.id
            JOIN exercises e ON we.exercise_id = e.id
            WHERE we.workout_id = ?
        """, (self.id,)).fetchall()

        total_sets = len(sets_data)
        total_reps = sum(s["reps"] or 0 for s in sets_data)
        total_volume = sum((s["reps"] or 0) * (s["weight_kg"] or 0) for s in sets_data)
        
        muscles = set()
        for s in sets_data:
            if s["muscles"]:
                for m in s["muscles"].split(','):
                    muscles.add(m.strip().lower())
        
        self.total_sets = total_sets
        self.total_reps = total_reps
        self.total_volume_kg = round(total_volume, 1)
        self.muscles_worked = ",".join(sorted(muscles))

        db.execute("""
            UPDATE workouts SET 
                finished_at = ?, duration_minutes = ?, total_sets = ?, 
                total_reps = ?, total_volume_kg = ?, muscles_worked = ?, 
                notes = ?, is_draft = 0
            WHERE id = ?
        """, (self.finished_at, self.duration_minutes, self.total_sets, 
              self.total_reps, self.total_volume_kg, self.muscles_worked, 
              self.notes, self.id))
        db.commit()

# --- Legacy Functional Wrappers ---
def finish_workout(workout_id: int, duration: int = None, notes: str = None):
    ws = WorkoutSession.get_by_id(workout_id)
    if ws:
        ws.finish(duration, notes)
        return True
    return False

# ============================================================
# Workouts
# ============================================================

def create_workout(user_id: int, data: dict) -> int:
    db = get_db()

    cur = db.execute(
        """
        INSERT INTO workouts
        (user_id, template_id, name, workout_date, started_at, finished_at, duration_minutes, notes, is_draft)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            data.get("template_id"),
            data.get("name"),
            data.get("workout_date") or datetime.date.today().isoformat(),
            data.get("started_at"),
            data.get("finished_at"),
            data.get("duration_minutes"),
            encrypt_data(data.get("notes")),
            int(data.get("is_draft", 0)),
        ),
    )

    db.commit()
    return cur.lastrowid

def get_workout(workout_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM workouts WHERE id = ?",
        (workout_id,)
    ).fetchone()


def get_workouts(user_id: int, limit: int = 30, offset: int = 0):
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
        (user_id, limit, offset),
    ).fetchall()

    result = []
    for row in rows:
        item = dict(row)
        item["notes"] = decrypt_data(item.get("notes"))
        result.append(item)

    return result


def get_workouts_for_month(user_id: int, year: int, month: int):
    db = get_db()

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
    db = get_db()

    allowed = [
        "name",
        "workout_date",
        "notes",
        "duration_minutes",
        "finished_at",
    ]

    updates = {k: v for k, v in data.items() if k in allowed}

    if "workout_date" in updates and not updates["workout_date"]:
        updates["workout_date"] = datetime.date.today().isoformat()

    if "notes" in updates:
        updates["notes"] = encrypt_data(updates["notes"])

    if updates:
        fields = ", ".join(f"{k} = ?" for k in updates.keys())

        db.execute(
            f"UPDATE workouts SET {fields} WHERE id = ?",
            list(updates.values()) + [workout_id]
        )
        db.commit()


def delete_workout(workout_id: int):
    db = get_db()
    db.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    db.commit()


# ============================================================
# Workout Exercises
# ============================================================

def add_exercise_to_workout(
    workout_id: int,
    exercise_id: int,
    position: int = 0,
    notes: str = ""
) -> int:

    db = get_db()

    cur = db.execute(
        """
        INSERT INTO workout_exercises
        (workout_id, exercise_id, position, notes)
        VALUES (?, ?, ?, ?)
        """,
        (
            workout_id,
            exercise_id,
            position,
            encrypt_data(notes),
        ),
    )

    db.commit()
    return cur.lastrowid


def get_workout_exercises(workout_id: int):
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
        item["notes"] = decrypt_data(item.get("notes"))
        result.append(item)

    return result


def remove_exercise_from_workout(workout_exercise_id: int):
    db = get_db()
    db.execute(
        "DELETE FROM workout_exercises WHERE id = ?",
        (workout_exercise_id,)
    )
    db.commit()


# ============================================================
# Sets
# ============================================================

def add_set(workout_exercise_id: int, data: dict) -> int:
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
            workout_exercise_id,
            data.get("set_number", 1),
            data.get("reps"),
            data.get("weight_kg"),
            data.get("duration_seconds"),
            data.get("rpe"),
            int(data.get("is_warmup", False)),
            int(data.get("is_failure", False)),
        ),
    )

    db.commit()
    return cur.lastrowid


def update_set(set_id: int, data: dict):
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
    db = get_db()
    db.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
    db.commit()


def get_sets_for_exercise(workout_exercise_id: int):
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
    """Return a workout with all exercises and sets nested."""
    db = get_db()

    workout = db.execute(
        "SELECT * FROM workouts WHERE id = ?",
        (workout_id,)
    ).fetchone()

    if not workout:
        return None

    exercises_rows = get_workout_exercises(workout_id)
    exercises = []

    for ex in exercises_rows:
        sets = get_sets_for_exercise(ex["id"])
        ex_dict = dict(ex)
        ex_dict["sets"] = [dict(s) for s in sets]
        exercises.append(ex_dict)

    result = dict(workout)
    result["notes"] = decrypt_data(result.get("notes"))
    result["exercises"] = exercises

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

            result["previous_stats"] = {
                "id": prev["id"],
                "date": prev["workout_date"],
                "volume_kg": round(prev_vol or 0, 1),
                "duration_minutes": prev["duration_minutes"],
            }

    return result


def get_weekly_volume(user_id: int, weeks: int = 8):
    """Return weekly set counts and total volume for chart."""
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
    """Clone a template into a new workout session."""
    db = get_db()

    template = db.execute(
        "SELECT * FROM workout_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    ).fetchone()

    if not template:
        return None

    workout_id = create_workout(
        user_id,
        {
            "template_id": template_id,
            "name": name or template["name"],
            "workout_date": workout_date,
        },
    )

    template_exercises = db.execute(
        """
        SELECT *
        FROM template_exercises
        WHERE template_id = ?
        ORDER BY position
        """,
        (template_id,),
    ).fetchall()

    for te in template_exercises:
        raw_notes = decrypt_data(te["notes"]) if te["notes"] else ""

        workout_exercise_id = add_exercise_to_workout(
            workout_id,
            te["exercise_id"],
            te["position"],
            raw_notes,
        )

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

    return workout_id

