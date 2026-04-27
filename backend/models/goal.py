"""
PeakForm — Goal model (OOP class + query helpers).

OOP Class: Goal — represents a training goal with progress tracking.
Satisfies academic OOP requirement.
"""
from .db import get_db
import datetime

VALID_GOAL_TYPES = [
    "exercise_weight",    # target max weight on a specific exercise
    "exercise_reps",      # target reps (e.g. 20 pull-ups)
    "exercise_1rm",       # target estimated 1RM
    "body_weight_target", # reach target body weight
    "weekly_frequency",   # X workouts per week
    "workout_count",      # complete N total workouts
    "volume_target",      # total volume in kg lifted
    "streak_days",        # consecutive training days
    "custom",             # any custom metric
]


class Goal:
    """
    OOP representation of a PeakForm training goal.
    Satisfies academic OOP requirement.
    """
    def __init__(self, data: dict):
        self.id             = data.get("id")
        self.user_id        = data.get("user_id")
        self.goal_type      = data.get("goal_type", "custom")
        self.title          = data.get("title", "")
        self.exercise_id    = data.get("exercise_id")
        self.target_value   = float(data.get("target_value", 1))
        self.current_value  = float(data.get("current_value", 0))
        self.starting_value = float(data.get("starting_value", 0))
        self.unit           = data.get("unit", "")
        self.deadline       = data.get("deadline")
        self.is_completed   = bool(data.get("is_completed", 0))
        self.completed_at   = data.get("completed_at")
        self.photo_path     = data.get("photo_path")
        self.created_at     = data.get("created_at")

    @property
    def progress_pct(self) -> float:
        """Return progress as a percentage (0-100)."""
        span = self.target_value - self.starting_value
        if span <= 0:
            return 100.0 if self.current_value >= self.target_value else 0.0
        progress = self.current_value - self.starting_value
        return min(100.0, max(0.0, (progress / span) * 100))

    @property
    def remaining(self) -> float:
        """How much remains to reach the target."""
        return max(0.0, self.target_value - self.current_value)

    @property
    def is_body_weight_goal(self) -> bool:
        return self.goal_type == "body_weight_target"

    @property
    def status_label(self) -> str:
        if self.is_completed:
            return "completed"
        if self.deadline:
            try:
                dl = datetime.date.fromisoformat(self.deadline)
                if dl < datetime.date.today():
                    return "overdue"
            except ValueError:
                pass
        return "active"

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "user_id":        self.user_id,
            "goal_type":      self.goal_type,
            "title":          self.title,
            "exercise_id":    self.exercise_id,
            "target_value":   self.target_value,
            "current_value":  self.current_value,
            "starting_value": self.starting_value,
            "unit":           self.unit,
            "deadline":       self.deadline,
            "is_completed":   self.is_completed,
            "completed_at":   self.completed_at,
            "photo_path":     self.photo_path,
            "progress_pct":   round(self.progress_pct, 1),
            "remaining":      round(self.remaining, 2),
            "status":         self.status_label,
        }


# ── Query helpers ──────────────────────────────────────────────────────────


def create_goal(user_id: int, data: dict) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO goals
           (user_id, goal_type, title, exercise_id, target_value, starting_value, current_value, unit, deadline)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            data["goal_type"],
            data["title"].strip(),
            data.get("exercise_id"),
            float(data["target_value"]),
            float(data.get("starting_value", 0)),
            float(data.get("current_value", data.get("starting_value", 0))),
            data.get("unit", ""),
            data.get("deadline"),
        ),
    )
    db.commit()
    return cur.lastrowid


def get_goals(user_id: int, include_completed: bool = True):
    db = get_db()
    sql = """SELECT g.*, e.name as exercise_name
             FROM goals g
             LEFT JOIN exercises e ON g.exercise_id = e.id
             WHERE g.user_id = ?"""
    if not include_completed:
        sql += " AND g.is_completed = 0"
    sql += " ORDER BY g.is_completed ASC, g.created_at DESC"
    return db.execute(sql, (user_id,)).fetchall()


def get_goal(goal_id: int):
    db = get_db()
    return db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()


def get_goal_with_details(goal_id: int):
    db = get_db()
    return db.execute(
        """SELECT g.*, e.name as exercise_name
           FROM goals g
           LEFT JOIN exercises e ON g.exercise_id = e.id
           WHERE g.id = ?""",
        (goal_id,)
    ).fetchone()


def update_goal_progress(goal_id: int, current_value: float = None) -> bool:
    db = get_db()
    goal = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        return False

    cv = current_value if current_value is not None else goal["current_value"]
    completed = cv >= goal["target_value"]

    db.execute(
        """UPDATE goals SET current_value = ?,
           is_completed = ?, completed_at = ?
           WHERE id = ?""",
        (
            cv,
            int(completed),
            datetime.datetime.utcnow().isoformat() if completed and not goal["is_completed"] else goal["completed_at"],
            goal_id,
        ),
    )
    db.commit()
    return completed and not bool(goal["is_completed"])  # True only if newly completed


def delete_goal(goal_id: int):
    db = get_db()
    db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.commit()


def update_goal_photo(goal_id: int, photo_path: str):
    db = get_db()
    db.execute("UPDATE goals SET photo_path = ? WHERE id = ?", (photo_path, goal_id))
    db.commit()


def auto_update_goals_from_workout(user_id: int, workout_data: dict):
    """
    After a workout, auto-update relevant goals.
    Checks workout_count and exercise_weight goals.
    """
    db = get_db()
    goals = db.execute(
        "SELECT * FROM goals WHERE user_id=? AND is_completed=0",
        (user_id,)
    ).fetchall()

    for goal in goals:
        g = Goal(dict(goal))

        if g.goal_type == "workout_count":
            # Count total completed workouts
            count = db.execute(
                "SELECT COUNT(*) as c FROM workouts WHERE user_id=? AND finished_at IS NOT NULL AND is_draft=0",
                (user_id,)
            ).fetchone()["c"]
            update_goal_progress(g.id, float(count))

        elif g.goal_type == "exercise_weight" and g.exercise_id:
            # Find best weight for this exercise in the workout
            for ex in workout_data.get("exercises", []):
                if ex.get("exercise_id") == g.exercise_id:
                    best = max((s.get("weight_kg", 0) or 0 for s in ex.get("sets", [])), default=0)
                    if best > g.current_value:
                        update_goal_progress(g.id, best)

        elif g.goal_type == "volume_target":
            # Sum total volume across all workouts
            vol = db.execute(
                """SELECT COALESCE(SUM(ws.reps * ws.weight_kg), 0) as v FROM workout_sets ws
                   JOIN workout_exercises we ON ws.workout_exercise_id = we.id
                   JOIN workouts w ON we.workout_id = w.id
                   WHERE w.user_id=? AND ws.reps IS NOT NULL AND ws.weight_kg IS NOT NULL""",
                (user_id,)
            ).fetchone()["v"]
            update_goal_progress(g.id, float(vol))
