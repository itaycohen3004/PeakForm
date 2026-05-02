"""
Exercise library model — search, CRUD, and set-type resolution.
"""
from .db import get_db


def _send_admin_dm(user_id: int, message: str):
    """Non-blocking helper — sends a DM without crashing the caller."""
    try:
        from backend.models.chat import send_admin_dm_message
        send_admin_dm_message(user_id, message)
    except Exception:
        pass


def search_exercises(query: str = "", category: str = "", limit: int = 50, user_id: int = None):
    db = get_db()
    # Globally-visible: approved (or legacy exercises with NULL status)
    # Personal-only: user's own pending submissions
    sql = "SELECT * FROM exercises WHERE (status = 'approved' OR (status IS NULL AND is_custom = 0)"
    params = []
    if user_id:
        sql += " OR (status = 'pending' AND created_by = ?)"
        params.append(user_id)
    sql += ")"
    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if category:
        sql += " AND (category = ? OR muscles_tags LIKE ?)"
        params.append(category)
        params.append(f"%{category}%")
    sql += " ORDER BY name LIMIT ?"
    params.append(limit)
    return db.execute(sql, params).fetchall()


def get_pending_exercises():
    """Admin: return all exercises awaiting approval."""
    db = get_db()
    return db.execute(
        """SELECT e.*, u.email as submitted_by_email
           FROM exercises e
           LEFT JOIN users u ON e.created_by = u.id
           WHERE e.status = 'pending'
           ORDER BY e.id DESC"""
    ).fetchall()


def approve_exercise(exercise_id: int):
    db = get_db()
    # Get exercise details before approving for notification
    ex = db.execute("SELECT name, created_by FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    db.execute("UPDATE exercises SET status = 'approved' WHERE id = ?", (exercise_id,))
    db.commit()
    # Send in-app notification to the creator
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
            pass  # Notifications table may not exist yet — migration handles it
        # Also send automatic private DM
        _send_admin_dm(
            ex["created_by"],
            f"\u2705 Your exercise **{ex['name']}** has been **approved** and is now live in the exercise library! Start adding it to your workouts."
        )


def reject_exercise(exercise_id: int):
    db = get_db()
    ex = db.execute("SELECT name, created_by FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    db.execute("UPDATE exercises SET status = 'rejected' WHERE id = ?", (exercise_id,))
    db.commit()
    # Notify the creator of rejection
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
        # Also send automatic private DM
        _send_admin_dm(
            ex["created_by"],
            f"\u274c Your exercise **{ex['name']}** was **not approved** at this time. Please ensure it has a unique name, correct muscle tags, and accurate equipment details, then resubmit."
        )


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
    return db.execute("SELECT * FROM exercises WHERE name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()


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
    return cur.lastrowid


def get_last_session(user_id: int, exercise_id: int) -> dict:
    """Return the most recent session sets for an exercise (for in-workout intel panel)."""
    db = get_db()
    # Get the most recent workout that contains this exercise
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
        return None

    sets = db.execute(
        """SELECT set_number, weight_kg, reps, duration_seconds, is_warmup
           FROM workout_sets
           WHERE workout_exercise_id = ?
           ORDER BY set_number ASC""",
        (last_we["id"],),
    ).fetchall()

    working_sets = [dict(s) for s in sets if not s["is_warmup"]]
    return {
        "workout_date":  last_we["workout_date"],
        "workout_name":  last_we["workout_name"],
        "workout_id":    last_we["workout_id"],
        "sets":          working_sets,
        "best_weight":   max((s["weight_kg"] or 0 for s in working_sets), default=None),
        "best_reps":     max((s["reps"] or 0 for s in working_sets), default=None),
    }


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


def update_exercise(exercise_id: int, name: str, category: str, set_type: str, muscles_tags: str, equipment: str):
    db = get_db()
    db.execute("""
        UPDATE exercises 
        SET name = ?, category = ?, set_type = ?, muscles_tags = ?, equipment = ?
        WHERE id = ?
    """, (name, category, set_type, muscles_tags, equipment, exercise_id))
    db.commit()


def delete_exercise(exercise_id: int):
    """Mark exercise as deleted instead of dropping to preserve foreign keys."""
    db = get_db()
    db.execute("UPDATE exercises SET status = 'deleted' WHERE id = ?", (exercise_id,))
    db.commit()
