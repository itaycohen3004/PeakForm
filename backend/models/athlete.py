"""
PeakForm — Athlete profile model (OOP class + query helpers).

OOP Class: Athlete — represents a training athlete profile.
"""
from .db import get_db
import datetime
from backend.services.encryption_service import encrypt_data, decrypt_data


class Athlete:
    """
    OOP representation of a PeakForm athlete.
    Satisfies academic OOP requirement.
    """
    def __init__(self, data: dict):
        self.user_id         = data.get("user_id")
        self.display_name    = decrypt_data(data.get("display_name", "Athlete"))
        self.training_type   = data.get("training_type", "gym")
        self.age             = decrypt_data(data.get("age"))
        self.gender          = data.get("gender")
        self.height_cm       = decrypt_data(data.get("height_cm"))
        self.current_weight  = decrypt_data(data.get("current_weight_kg"))
        self.target_weight   = decrypt_data(data.get("target_weight_kg"))
        self.experience      = data.get("experience_level", "intermediate")
        self.main_goal       = data.get("main_goal", "general_fitness")
        self.days_per_week   = data.get("days_per_week", 3)
        self.avatar_url      = data.get("avatar_url")
        self.onboarding_done = bool(data.get("onboarding_complete", 0))

        # Convert decrypted strings back to numbers if needed
        try:
            if self.age: self.age = int(float(self.age))
            if self.height_cm: self.height_cm = float(self.height_cm)
            if self.current_weight: self.current_weight = float(self.current_weight)
            if self.target_weight: self.target_weight = float(self.target_weight)
        except Exception: 
            pass

    @property
    def bmi(self) -> float | None:
        try:
            if self.height_cm and self.current_weight:
                h_m = float(self.height_cm) / 100
                return round(float(self.current_weight) / (h_m * h_m), 1)
        except (ValueError, TypeError):
            pass
        return None

    @property
    def goal_direction(self) -> str:
        """Returns 'gain' or 'lose' or 'maintain' based on goal."""
        if self.main_goal in ("build_muscle",):
            return "gain"
        if self.main_goal in ("fat_loss",):
            return "lose"
        return "maintain"

    @property
    def weight_color_logic(self) -> str:
        """Returns whether weight increase is good ('green_up') or bad ('red_up')."""
        return "green_up" if self.goal_direction == "gain" else "red_up"

    def to_dict(self) -> dict:
        return {
            "user_id":           self.user_id,
            "display_name":      self.display_name,
            "training_type":     self.training_type,
            "age":               self.age,
            "gender":            self.gender,
            "height_cm":         self.height_cm,
            "current_weight_kg": self.current_weight,
            "target_weight_kg":  self.target_weight,
            "experience_level":  self.experience,
            "main_goal":         self.main_goal,
            "days_per_week":     self.days_per_week,
            "avatar_url":        self.avatar_url,
            "onboarding_complete": self.onboarding_done,
            "bmi":               self.bmi,
            "goal_direction":    self.goal_direction,
            "weight_color_logic": self.weight_color_logic,
        }


# ── Query helpers ──────────────────────────────────────────────────────────


def get_athlete_profile(user_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM athlete_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()


def get_athlete_by_id(athlete_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM athlete_profiles WHERE id = ?", (athlete_id,)
    ).fetchone()


def create_athlete_profile(user_id: int, display_name: str, **kwargs) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO athlete_profiles
           (user_id, display_name, training_type, age, gender, height_cm,
            current_weight_kg, target_weight_kg, experience_level,
            main_goal, days_per_week, bio, onboarding_complete)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, 
            encrypt_data(display_name),
            kwargs.get("training_type", "gym"),
            encrypt_data(kwargs.get("age")),
            kwargs.get("gender"),
            encrypt_data(kwargs.get("height_cm")),
            encrypt_data(kwargs.get("current_weight_kg")),
            encrypt_data(kwargs.get("target_weight_kg")),
            kwargs.get("experience_level", "beginner"),
            kwargs.get("main_goal", "general_fitness"),
            kwargs.get("days_per_week", 3),
            encrypt_data(kwargs.get("bio")),
            0,
        ),
    )
    db.commit()
    return cur.lastrowid


def update_athlete_profile(user_id: int, updates: dict):
    db = get_db()
    allowed = [
        "display_name", "training_type", "age", "gender", "height_cm",
        "current_weight_kg", "target_weight_kg", "experience_level",
        "main_goal", "days_per_week", "bio", "avatar_url", "onboarding_complete"
    ]
    to_encrypt = ["display_name", "age", "height_cm", "current_weight_kg", "target_weight_kg", "bio"]
    
    filtered = {}
    for k, v in updates.items():
        if k in allowed:
            filtered[k] = encrypt_data(v) if k in to_encrypt else v

    if not filtered:
        return
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [user_id]
    db.execute(f"UPDATE athlete_profiles SET {set_clause} WHERE user_id = ?", values)
    db.commit()


def get_athlete_stats(user_id: int) -> dict:
    db = get_db()
    try:
        total_workouts = db.execute(
            "SELECT COUNT(*) as c FROM workouts WHERE user_id=? AND finished_at IS NOT NULL AND is_draft=0",
            (user_id,)
        ).fetchone()["c"]
    except Exception:
        total_workouts = 0

    try:
        total_sets = db.execute(
            """SELECT COUNT(ws.id) as c FROM workout_sets ws
               JOIN workout_exercises we ON ws.workout_exercise_id = we.id
               JOIN workouts w ON we.workout_id = w.id
               WHERE w.user_id=? AND w.finished_at IS NOT NULL""",
            (user_id,),
        ).fetchone()["c"]
    except Exception:
        total_sets = 0

    try:
        total_volume = db.execute(
            """SELECT COALESCE(SUM(ws.reps * ws.weight_kg), 0) as v FROM workout_sets ws
               JOIN workout_exercises we ON ws.workout_exercise_id = we.id
               JOIN workouts w ON we.workout_id = w.id
               WHERE w.user_id=? AND w.finished_at IS NOT NULL
                 AND ws.reps IS NOT NULL AND ws.weight_kg IS NOT NULL""",
            (user_id,),
        ).fetchone()["v"]
    except Exception:
        total_volume = 0

    try:
        streak = _calculate_streak(user_id, db)
    except Exception:
        streak = 0

    try:
        workouts_this_week = _workouts_this_week(user_id, db)
    except Exception:
        workouts_this_week = 0

    try:
        last_workout = db.execute(
            "SELECT workout_date FROM workouts WHERE user_id=? AND finished_at IS NOT NULL ORDER BY workout_date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        last_workout_date = last_workout["workout_date"] if last_workout else None
    except Exception:
        last_workout_date = None

    try:
        avg_dur = _avg_duration(user_id, db)
    except Exception:
        avg_dur = 0

    return {
        "total_workouts":     total_workouts,
        "total_sets":         total_sets,
        "total_volume_kg":    round(float(total_volume or 0), 1),
        "current_streak":     streak,
        "workouts_this_week": workouts_this_week,
        "last_workout_date":  last_workout_date,
        "avg_duration":       avg_dur,
    }

def _avg_duration(user_id: int, db) -> int:
    row = db.execute(
        "SELECT AVG(duration_minutes) as avg FROM workouts WHERE user_id=? AND finished_at IS NOT NULL",
        (user_id,)
    ).fetchone()
    return int(row["avg"]) if row and row["avg"] else 0


def _calculate_streak(user_id: int, db) -> int:
    try:
        rows = db.execute(
            """SELECT DISTINCT workout_date FROM workouts
               WHERE user_id=? AND finished_at IS NOT NULL AND workout_date IS NOT NULL
               ORDER BY workout_date DESC""",
            (user_id,),
        ).fetchall()
    except Exception:
        return 0
    if not rows:
        return 0
    streak = 0
    today = datetime.date.today()
    for i, row in enumerate(rows):
        try:
            d = datetime.date.fromisoformat(str(row["workout_date"]).split("T")[0].split(" ")[0])
        except Exception:
            break
        expected = today - datetime.timedelta(days=i)
        if d == expected:
            streak += 1
        else:
            break
    return streak


def _workouts_this_week(user_id: int, db) -> int:
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    row = db.execute(
        """SELECT COUNT(*) as c FROM workouts
           WHERE user_id=? AND finished_at IS NOT NULL AND is_draft=0
             AND workout_date >= ?""",
        (user_id, start_of_week.isoformat()),
    ).fetchone()
    return row["c"] if row else 0


def get_today_template(user_id: int):
    """Return scheduled template for today if any."""
    db = get_db()
    today_weekday = datetime.date.today().weekday()
    row = db.execute(
        """SELECT ws.template_id, wt.name as template_name
           FROM weekly_schedule ws
           JOIN workout_templates wt ON ws.template_id = wt.id
           WHERE ws.user_id = ? AND ws.weekday = ?""",
        (user_id, today_weekday),
    ).fetchone()
    return row
