from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


def get_rooms():
    db = get_db()
    return db.execute(
        """SELECT cr.*, COUNT(DISTINCT crm.user_id) as member_count
           FROM chat_rooms cr
           LEFT JOIN chat_room_members crm ON crm.room_id = cr.id
           WHERE cr.room_type = 'public'
           GROUP BY cr.id
           ORDER BY cr.id""",
    ).fetchall()


def get_room(room_id: int):
    db = get_db()
    return db.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,)).fetchone()


def get_room_with_membership(room_id: int, user_id: int):
    db = get_db()
    room = db.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        return None
    membership = db.execute(
        "SELECT * FROM chat_room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id),
    ).fetchone()
    result = dict(room)
    result["is_member"] = membership is not None
    result["display_name"] = membership["nickname"] if membership else None
    return result


def join_room(room_id: int, user_id: int, display_name: str):
    db = get_db()
    db.execute(
        """INSERT INTO chat_room_members (room_id, user_id, nickname)
           VALUES (?, ?, ?)
           ON CONFLICT(room_id, user_id) DO UPDATE SET nickname = excluded.nickname""",
        (room_id, user_id, display_name),
    )
    db.commit()


def leave_room(room_id: int, user_id: int):
    db = get_db()
    db.execute("DELETE FROM chat_room_members WHERE room_id = ? AND user_id = ?", (room_id, user_id))
    db.commit()


def get_messages(room_id: int, limit: int = 80):
    db = get_db()
    rows = db.execute(
        """SELECT cm.*, ap.display_name as profile_name, ap.avatar_url
           FROM chat_messages cm
           LEFT JOIN athlete_profiles ap ON ap.user_id = cm.user_id
           WHERE cm.room_id = ? AND cm.is_deleted = 0
           ORDER BY cm.sent_at DESC
           LIMIT ?""",
        (room_id, limit),
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["message"] = decrypt_data(d["message"])
        # profile_name might already be decrypted or null
        results.append(d)
    return results


def save_message(room_id: int, user_id: int, display_name: str, message: str) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO chat_messages (room_id, user_id, display_name, message) VALUES (?,?,?,?)",
        (room_id, user_id, display_name, encrypt_data(message)),
    )
    db.commit()
    return cur.lastrowid


def delete_message(message_id: int):
    db = get_db()
    db.execute("UPDATE chat_messages SET is_deleted = 1 WHERE id = ?", (message_id,))
    db.commit()


def report_message(message_id: int):
    db = get_db()
    db.execute("UPDATE chat_messages SET is_reported = 1 WHERE id = ?", (message_id,))
    db.commit()


def get_reported_messages():
    db = get_db()
    return db.execute(
        """SELECT cm.*, ap.display_name FROM chat_messages cm
           LEFT JOIN athlete_profiles ap ON ap.user_id = cm.user_id
           WHERE cm.is_reported = 1 AND cm.is_deleted = 0
           ORDER BY cm.sent_at DESC"""
    ).fetchall()
def log_chat_activity(user_id: int, room_id: int):
    db = get_db()
    db.execute(
        "UPDATE chat_room_members SET last_active_at = CURRENT_TIMESTAMP WHERE user_id=? AND room_id=?",
        (user_id, room_id)
    )
    db.commit()
