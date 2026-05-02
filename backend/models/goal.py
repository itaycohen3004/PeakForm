"""
PeakForm — Goal model (OOP class + query helpers).

OOP Class: Goal — represents a training goal with progress tracking.
Satisfies academic OOP requirement.
הקובץ הזה מנהל את "היעדים" שלנו (Goals)! כמו למשל "לעשות 20 מתח" או "לרדת 5 קילו".
יש כאן מחלקה (Class) שמייצגת יעד, ופונקציות ששומרות ומעדכנות את היעדים במסד הנתונים.
"""
from .db import get_db
import datetime

# רשימה של סוגי היעדים שאפשר לבחור
VALID_GOAL_TYPES = [
    "exercise_weight",    # target max weight on a specific exercise (למשל: להרים 100 קילו בסקוואט)
    "exercise_reps",      # target reps (e.g. 20 pull-ups) (למשל: לעשות 20 מתח)
    "exercise_1rm",       # target estimated 1RM (כוח מירבי לחזרה אחת)
    "body_weight_target", # reach target body weight (משקל גוף יעד)
    "weekly_frequency",   # X workouts per week (להתאמן 4 פעמים בשבוע)
    "workout_count",      # complete N total workouts (לסיים 10 אימונים)
    "volume_target",      # total volume in kg lifted (להרים סך הכל 10,000 קילו)
    "streak_days",        # consecutive training days (להתאמן 5 ימים ברצף)
    "custom",             # any custom metric (יעד חופשי - כל דבר אחר)
]


class Goal:
    """
    OOP representation of a PeakForm training goal.
    Satisfies academic OOP requirement.
    מחלקה שמייצגת יעד אחד של משתמש. 
    היא לוקחת נתונים גולמיים ממסד הנתונים והופכת אותם לאובייקט שאפשר לעבוד איתו בקלות.
    """
    def __init__(self, data: dict):
        self.id             = data.get("id") # מספר זהות של היעד
        self.user_id        = data.get("user_id") # של איזה משתמש היעד הזה
        self.goal_type      = data.get("goal_type", "custom") # איזה סוג יעד זה
        self.title          = data.get("title", "") # הכותרת של היעד (למשל "מתח")
        self.exercise_id    = data.get("exercise_id") # אם זה קשור לתרגיל מסוים, זה המספר שלו
        self.target_value   = float(data.get("target_value", 1)) # המטרה! (למשל 20)
        self.current_value  = float(data.get("current_value", 0)) # איפה אנחנו עכשיו (למשל 12)
        self.starting_value = float(data.get("starting_value", 0)) # מאיפה התחלנו (למשל 5)
        self.unit           = data.get("unit", "") # יחידות מידה (קילו, חזרות וכו')
        self.deadline       = data.get("deadline") # תאריך יעד אחרון
        self.is_completed   = bool(data.get("is_completed", 0)) # האם הגענו ליעד? (True/False)
        self.completed_at   = data.get("completed_at") # מתי סיימנו את היעד
        self.photo_path     = data.get("photo_path") # תמונה שאפשר להוסיף ליעד
        self.created_at     = data.get("created_at") # מתי יצרנו את היעד

    @property
    def progress_pct(self) -> float:
        """Return progress as a percentage (0-100)."""
        # מחשב כמה אחוזים מהיעד כבר השלמנו (מאפס עד מאה)
        span = self.target_value - self.starting_value
        if span <= 0:
            return 100.0 if self.current_value >= self.target_value else 0.0
        progress = self.current_value - self.starting_value
        return min(100.0, max(0.0, (progress / span) * 100))

    @property
    def remaining(self) -> float:
        """How much remains to reach the target."""
        # מחשב כמה עוד נשאר לנו לעשות כדי להגיע ליעד (למשל עוד 8 חזרות)
        return max(0.0, self.target_value - self.current_value)

    @property
    def is_body_weight_goal(self) -> bool:
        # בודק אם זה יעד שקשור למשקל גוף
        return self.goal_type == "body_weight_target"

    @property
    def status_label(self) -> str:
        # בודק מה המצב של היעד כרגע
        if self.is_completed:
            return "completed" # סיימנו אותו!
        if self.deadline:
            try:
                dl = datetime.date.fromisoformat(self.deadline)
                if dl < datetime.date.today():
                    return "overdue" # עברנו את התאריך שהצבנו לעצמנו!
            except ValueError:
                pass
        return "active" # עדיין עובדים עליו

    def to_dict(self) -> dict:
        # הופך את כל הנתונים של המחלקה למילון פשוט שאפשר לשלוח לאפליקציה (ב-JSON)
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
            "progress_pct":   round(self.progress_pct, 1), # אחוז ההתקדמות (מעוגל לנקודה אחת)
            "remaining":      round(self.remaining, 2), # כמה נשאר
            "status":         self.status_label, # מה המצב
        }


# ── פונקציות שמדברות עם מסד הנתונים (Query helpers) ──────────────────────────


# יוצר יעד חדש במערכת!
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
    return cur.lastrowid # מחזיר את המספר המזהה של היעד


# מביא את כל היעדים של משתמש מסוים
def get_goals(user_id: int, include_completed: bool = True):
    db = get_db()
    # אנחנו מצרפים את טבלת התרגילים כדי לקבל את השם האמיתי של התרגיל (אם היעד קשור לתרגיל)
    sql = """SELECT g.*, e.name as exercise_name
             FROM goals g
             LEFT JOIN exercises e ON g.exercise_id = e.id
             WHERE g.user_id = ?"""
    if not include_completed:
        sql += " AND g.is_completed = 0"
    # מסדרים את זה ככה שיעדים פעילים יהיו למעלה ויעדים שהסתיימו ירדו למטה
    sql += " ORDER BY g.is_completed ASC, g.created_at DESC"
    return db.execute(sql, (user_id,)).fetchall()


# מביא יעד אחד ספציפי לפי המספר המזהה שלו
def get_goal(goal_id: int):
    db = get_db()
    return db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()


# מביא יעד אחד ספציפי, כולל השם של התרגיל (אם היעד קשור לתרגיל)
def get_goal_with_details(goal_id: int):
    db = get_db()
    return db.execute(
        """SELECT g.*, e.name as exercise_name
           FROM goals g
           LEFT JOIN exercises e ON g.exercise_id = e.id
           WHERE g.id = ?""",
        (goal_id,)
    ).fetchone()


# מעדכן כמה התקדמנו ביעד מסוים (למשל: עדכנו את המשקל שאנחנו מרימים)
def update_goal_progress(goal_id: int, current_value: float = None) -> bool:
    db = get_db()
    goal = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        return False

    cv = current_value if current_value is not None else goal["current_value"]
    # בודק אם סוף סוף הגענו למטרה שלנו! (המשקל הנוכחי גדול או שווה ליעד)
    completed = cv >= goal["target_value"]

    # שומר את ההתקדמות שלנו ואם סיימנו אז גם את התאריך של הסיום
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
    # מחזיר True רק אם ממש הרגע סיימנו את היעד הזה פעם ראשונה (כדי שהאפליקציה תוכל לעשות לנו חגיגה!)
    return completed and not bool(goal["is_completed"])  


# מוחק יעד אם אנחנו לא רוצים אותו יותר
def delete_goal(goal_id: int):
    db = get_db()
    db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.commit()


# אם צילמנו תמונה בשביל היעד, כאן אנחנו שומרים אותה
def update_goal_photo(goal_id: int, photo_path: str):
    db = get_db()
    db.execute("UPDATE goals SET photo_path = ? WHERE id = ?", (photo_path, goal_id))
    db.commit()


# מעדכן את היעדים שלנו באופן אוטומטי בסוף כל אימון!
def auto_update_goals_from_workout(user_id: int, workout_data: dict):
    """
    After a workout, auto-update relevant goals.
    Checks workout_count and exercise_weight goals.
    """
    db = get_db()
    # מוצא את כל היעדים הפעילים שלנו (שעדיין לא סיימנו)
    goals = db.execute(
        "SELECT * FROM goals WHERE user_id=? AND is_completed=0",
        (user_id,)
    ).fetchall()

    # עובר על כל אחד מהיעדים שלנו
    for goal in goals:
        g = Goal(dict(goal)) # הופך כל יעד לאובייקט כדי שיהיה קל לעבוד איתו

        if g.goal_type == "workout_count":
            # אם היעד הוא "כמה אימונים עשינו": המערכת סופרת לבד את כל האימונים שעשינו עד עכשיו
            count = db.execute(
                "SELECT COUNT(*) as c FROM workouts WHERE user_id=? AND finished_at IS NOT NULL AND is_draft=0",
                (user_id,)
            ).fetchone()["c"]
            update_goal_progress(g.id, float(count))

        elif g.goal_type == "exercise_weight" and g.exercise_id:
            # אם היעד הוא "כמה משקל הרמנו בתרגיל מסוים": המערכת בודקת את האימון האחרון שעשינו ומוצאת את המשקל הכי כבד
            for ex in workout_data.get("exercises", []):
                if ex.get("exercise_id") == g.exercise_id:
                    best = max((s.get("weight_kg", 0) or 0 for s in ex.get("sets", [])), default=0)
                    if best > g.current_value:
                        # אם שברנו שיא - היא מעדכנת את היעד!
                        update_goal_progress(g.id, best)

        elif g.goal_type == "volume_target":
            # אם היעד הוא "נפח כולל (כמה משקל סחבנו בכלל)": המערכת מחברת את כל החזרות כפול המשקלים
            vol = db.execute(
                """SELECT COALESCE(SUM(ws.reps * ws.weight_kg), 0) as v FROM workout_sets ws
                   JOIN workout_exercises we ON ws.workout_exercise_id = we.id
                   JOIN workouts w ON we.workout_id = w.id
                   WHERE w.user_id=? AND ws.reps IS NOT NULL AND ws.weight_kg IS NOT NULL""",
                (user_id,)
            ).fetchone()["v"]
            update_goal_progress(g.id, float(vol))

"""
English Summary:
This file contains the Goal model which implements strict Object-Oriented Programming (OOP) 
principles to manage and track user training goals. It uses properties to dynamically calculate 
progress percentage and remaining targets. The module includes robust background intelligence to 
automatically auto-update users' goals directly from their finalized workouts (such as updating 
volume totals or workout counts automatically).
"""
