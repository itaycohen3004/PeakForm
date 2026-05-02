"""
Body weight tracking model.
הקובץ הזה מדבר עם מסד הנתונים ושומר או מושך את נתוני משקל הגוף שלנו!
"""
from .db import get_db


# הפונקציה שמוסיפה שקילה חדשה למערכת
def log_body_weight(user_id: int, weight_kg: float, notes: str = None,
                     photo_path: str = None, logged_at: str = None) -> int:
    import datetime
    db = get_db()
    # מכניסה לטבלה של המשקלים את המספר של המשתמש, המשקל שלו, פתק אם יש, ואת הנתיב לתמונה (אם הוא העלה)
    cur = db.execute(
        "INSERT INTO body_weight_logs (user_id, weight_kg, notes, photo_path, logged_at) VALUES (?,?,?,?,?)",
        (user_id, weight_kg, notes, photo_path,
         logged_at or datetime.date.today().isoformat()), # אם לא ציינו תאריך, לוקחים את התאריך של היום
    )
    db.commit()
    return cur.lastrowid # מחזירה את המספר המזהה החדש של השקילה הזו


# הפונקציה שמביאה לנו את כל היסטוריית השקילות שלנו כדי שנוכל לצייר גרף
def get_body_weight_logs(user_id: int, limit: int = 90):
    db = get_db()
    # מבקשת את המשקלים של המשתמש, מהחדש לישן, ועד גבול מסוים (למשל 90 שקילות אחרונות)
    return db.execute(
        "SELECT * FROM body_weight_logs WHERE user_id = ? ORDER BY logged_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


# הפונקציה שמוחקת שקילה מסוימת (למשל אם הקלדנו משקל בטעות)
def delete_body_weight_log(log_id: int):
    db = get_db()
    db.execute("DELETE FROM body_weight_logs WHERE id = ?", (log_id,))
    db.commit()


# הפונקציה שמביאה רק את השקילה האחרונה ביותר שעשינו (כדי לדעת מה המשקל העדכני שלנו)
def get_latest_body_weight(user_id: int):
    db = get_db()
    # מושכת רק שורה אחת (LIMIT 1) שהיא הכי חדשה (DESC)
    return db.execute(
        "SELECT * FROM body_weight_logs WHERE user_id = ? ORDER BY logged_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()

"""
English Summary:
This file represents the data access layer (model) for body weight tracking. 
It connects to the SQLite database to insert new weight logs (with optional progress photos), 
retrieve the historical timeline of body weights for charting, delete accidental logs, 
and fetch the absolute most recent weight for dashboard display.
"""
