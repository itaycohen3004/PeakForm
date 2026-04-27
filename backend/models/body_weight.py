"""
Body weight tracking model.
"""
from .db import get_db


def log_body_weight(user_id: int, weight_kg: float, notes: str = None,
                     photo_path: str = None, logged_at: str = None) -> int:
    import datetime
    db = get_db()
    cur = db.execute(
        "INSERT INTO body_weight_logs (user_id, weight_kg, notes, photo_path, logged_at) VALUES (?,?,?,?,?)",
        (user_id, weight_kg, notes, photo_path,
         logged_at or datetime.date.today().isoformat()),
    )
    db.commit()
    return cur.lastrowid


def get_body_weight_logs(user_id: int, limit: int = 90):
    db = get_db()
    return db.execute(
        "SELECT * FROM body_weight_logs WHERE user_id = ? ORDER BY logged_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def delete_body_weight_log(log_id: int):
    db = get_db()
    db.execute("DELETE FROM body_weight_logs WHERE id = ?", (log_id,))
    db.commit()


def get_latest_body_weight(user_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM body_weight_logs WHERE user_id = ? ORDER BY logged_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
