"""
Exercise library model — search, CRUD, and set-type resolution.
"""
from .db import get_db


def search_exercises(query: str = "", category: str = "", limit: int = 50):
    db = get_db()
    sql = "SELECT * FROM exercises WHERE 1=1"
    params = []
    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY name LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()


def get_exercise_by_id(exercise_id: int):
    db = get_db()
    return db.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()


def get_exercise_by_name(name: str):
    db = get_db()
    return db.execute("SELECT * FROM exercises WHERE name = ?", (name,)).fetchone()


def find_exercise_by_name(name: str):
    """Fuzzy-search by name (exact first, then LIKE)."""
    db = get_db()
    row = db.execute("SELECT * FROM exercises WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
    if row:
        return row
    # Try partial match
    return db.execute("SELECT * FROM exercises WHERE name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()


def create_custom_exercise(user_id: int, name: str, category: str,
                            set_type: str, muscles: str = "", equipment: str = "") -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO exercises (name, category, set_type, muscles, equipment, is_custom, created_by)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (name, category, set_type, muscles, equipment, user_id),
    )
    db.commit()
    return cur.lastrowid


def get_all_categories():
    return ["chest","back","shoulders","arms","legs","core","full_body","skill","cardio"]


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



def get_exercise_prs(user_id: int, exercise_id: int) -> dict:
    """Return personal records for an exercise."""
    db = get_db()
    max_weight = db.execute(
        """SELECT MAX(ws.weight_kg) as val FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ? AND ws.is_warmup = 0""",
        (user_id, exercise_id),
    ).fetchone()["val"]

    max_reps = db.execute(
        """SELECT MAX(ws.reps) as val FROM workout_sets ws
           JOIN workout_exercises we ON ws.workout_exercise_id = we.id
           JOIN workouts w ON we.workout_id = w.id
           WHERE w.user_id = ? AND we.exercise_id = ? AND ws.is_warmup = 0""",
        (user_id, exercise_id),
    ).fetchone()["val"]

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
