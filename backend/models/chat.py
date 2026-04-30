from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


def get_rooms():
    db = get_db()
    return db.execute(
        """SELECT cr.*, COUNT(DISTINCT crm.user_id) as member_count
           FROM chat_rooms cr
           LEFT JOIN chat_room_members crm ON crm.room_id = cr.id
           WHERE cr.room_type = 'public' OR cr.room_type IS NULL
           GROUP BY cr.id
           ORDER BY cr.id""",
    ).fetchall()


def get_room(room_id: int):
    db = get_db()
    return db.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,)).fetchone()


def create_public_room(name: str, description: str, owner_user_id: int) -> int:
    """Create a new public chat room. Returns the new room_id."""
    db = get_db()
    cur = db.execute(
        """INSERT INTO chat_rooms (name, description, room_type, owner_user_id)
           VALUES (?, ?, 'public', ?)""",
        (name, description or "", owner_user_id),
    )
    db.commit()
    return cur.lastrowid


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
    # For DM rooms, the owner and admin are always considered members
    is_dm = result.get("room_type") == "dm"
    is_owner_or_admin_of_dm = is_dm and (result.get("owner_user_id") == user_id or user_id == 1)
    result["is_member"] = membership is not None or is_owner_or_admin_of_dm
    result["display_name"] = membership["nickname"] if membership else ("Admin" if user_id == 1 else "You")
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
        # profile_name from athlete_profiles is stored encrypted — decrypt it
        try:
            if d.get("profile_name"):
                d["profile_name"] = decrypt_data(d["profile_name"])
        except Exception:
            pass  # If not encrypted, keep as-is
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


def get_or_create_admin_dm(user_id: int) -> int:
    """Get or create a private DM room between user_id and the admin."""
    db = get_db()
    # Look for existing DM room owned by this user
    existing = db.execute(
        "SELECT id FROM chat_rooms WHERE room_type='dm' AND owner_user_id=?",
        (user_id,)
    ).fetchone()
    if existing:
        return existing["id"]

    # Create the DM room
    ADMIN_ID = 1  # The platform admin user
    room_name = f"Admin Support Chat"
    cur = db.execute(
        """INSERT INTO chat_rooms (name, description, room_type, owner_user_id)
           VALUES (?, ?, 'dm', ?)""",
        (room_name, "Private messages with the PeakForm admin team", user_id)
    )
    room_id = cur.lastrowid
    # Add both members
    for uid in [user_id, ADMIN_ID]:
        db.execute(
            "INSERT OR IGNORE INTO chat_room_members (room_id, user_id, nickname) VALUES (?,?,?)",
            (room_id, uid, "Admin" if uid == ADMIN_ID else "You")
        )
    db.commit()

    # Send welcome message from admin
    welcome = "👋 Welcome to your private support channel! The admin team will respond here."
    db.execute(
        "INSERT INTO chat_messages (room_id, user_id, display_name, message) VALUES (?,?,?,?)",
        (room_id, ADMIN_ID, "PeakForm Admin", encrypt_data(welcome))
    )
    db.commit()
    return room_id


def get_dm_rooms_for_admin(admin_id: int = 1):
    """Get all DM rooms for the admin panel view."""
    db = get_db()
    rows = db.execute(
        """SELECT cr.*, ap.display_name as user_display_name
           FROM chat_rooms cr
           LEFT JOIN athlete_profiles ap ON ap.user_id = cr.owner_user_id
           WHERE cr.room_type = 'dm'
           ORDER BY cr.id DESC"""
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["user_display_name"] = decrypt_data(d["user_display_name"]) if d["user_display_name"] else "User"
        except Exception:
            pass
        results.append(d)
    return results


def send_admin_dm_message(user_id: int, message: str):
    """Send an automatic message from admin into the user's DM room."""
    try:
        room_id = get_or_create_admin_dm(user_id)
        db = get_db()
        ADMIN_ID = 1
        db.execute(
            "INSERT INTO chat_messages (room_id, user_id, display_name, message) VALUES (?,?,?,?)",
            (room_id, ADMIN_ID, "PeakForm Admin", encrypt_data(message))
        )
        db.commit()
    except Exception:
        pass  # Never block the approval flow
