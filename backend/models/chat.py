"""
Chat model — handles database interactions for real-time messaging.
הקובץ שמדבר עם בסיס הנתונים עבור מערכת הצ'אט! הוא יודע ליצור חדרים,
לשמור הודעות, לצרף אנשים ולמחוק הודעות בעייתיות.
"""
from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


# מביא את רשימת כל חדרי הצ'אט הציבוריים בקהילה
def get_rooms():
    db = get_db()
    # סופר גם כמה משתמשים (members) יש כרגע בכל חדר
    return db.execute(
        """SELECT cr.*, COUNT(DISTINCT crm.user_id) as member_count
           FROM chat_rooms cr
           LEFT JOIN chat_room_members crm ON crm.room_id = cr.id
           WHERE cr.room_type = 'public' OR cr.room_type IS NULL
           GROUP BY cr.id
           ORDER BY cr.id""",
    ).fetchall()


# מביא פרטים של חדר אחד ספציפי (לפי המספר שלו)
def get_room(room_id: int):
    db = get_db()
    return db.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,)).fetchone()


# יוצר חדר צ'אט ציבורי חדש! (הפעולה הזו מותרת בדרך כלל רק למנהלים)
def create_public_room(name: str, description: str, owner_user_id: int) -> int:
    """Create a new public chat room. Returns the new room_id."""
    db = get_db()
    cur = db.execute(
        """INSERT INTO chat_rooms (name, description, room_type, owner_user_id)
           VALUES (?, ?, 'public', ?)""",
        (name, description or "", owner_user_id),
    )
    db.commit()
    return cur.lastrowid # מחזיר את המספר של החדר החדש


# בודק האם משתמש מסוים הוא כרגע בפנים (חבר) בתוך חדר צ'אט מסוים
def get_room_with_membership(room_id: int, user_id: int):
    db = get_db()
    room = db.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        return None # אין חדר כזה
        
    # מחפש האם השם של המשתמש רשום ברשימת האנשים שבתוך החדר
    membership = db.execute(
        "SELECT * FROM chat_room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id),
    ).fetchone()
    
    result = dict(room)
    # אם זה צ'אט פרטי (DM) בין מישהו למנהל, אז המנהל תמיד נחשב "חבר" שם
    is_dm = result.get("room_type") == "dm"
    is_owner_or_admin_of_dm = is_dm and (result.get("owner_user_id") == user_id or user_id == 1)
    
    result["is_member"] = membership is not None or is_owner_or_admin_of_dm
    # קובע מה יהיה השם של המשתמש שיוצג בחדר
    result["display_name"] = membership["nickname"] if membership else ("Admin" if user_id == 1 else "You")
    return result


# מכניס מישהו לתוך חדר (רושם אותו כ"נוכח" עכשיו בחדר)
def join_room(room_id: int, user_id: int, display_name: str):
    db = get_db()
    db.execute(
        """INSERT INTO chat_room_members (room_id, user_id, nickname)
           VALUES (?, ?, ?)
           ON CONFLICT(room_id, user_id) DO UPDATE SET nickname = excluded.nickname""",
        (room_id, user_id, display_name),
    )
    db.commit()


# מוציא מישהו מהחדר (הוא עזב)
def leave_room(room_id: int, user_id: int):
    db = get_db()
    db.execute("DELETE FROM chat_room_members WHERE room_id = ? AND user_id = ?", (room_id, user_id))
    db.commit()


# שולף את ההודעות האחרונות שנשלחו בחדר מסוים (עד 80 הודעות)
def get_messages(room_id: int, limit: int = 80):
    db = get_db()
    # מביא את ההודעות ומחבר אליהן את השם פרופיל והתמונה של מי ששלח אותן
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
        # הופך את ההודעות מ"ג'יבריש מוצפן" בחזרה לטקסט קריא!
        d["message"] = decrypt_data(d["message"])
        # גם השם של המשתמש שמור אצלנו מוצפן, אז פותחים גם אותו
        try:
            if d.get("profile_name"):
                d["profile_name"] = decrypt_data(d["profile_name"])
        except Exception:
            pass  # אם לא הצלחנו, משאירים כמו שזה
        results.append(d)
    return results


# שומר הודעה חדשה שמישהו הרגע כתב בצ'אט
def save_message(room_id: int, user_id: int, display_name: str, message: str) -> int:
    db = get_db()
    # בשביל הפרטיות - כל הודעה ננעלת עם צופן (encrypt) לפני שהיא נכנסת למסד הנתונים!
    cur = db.execute(
        "INSERT INTO chat_messages (room_id, user_id, display_name, message) VALUES (?,?,?,?)",
        (room_id, user_id, display_name, encrypt_data(message)),
    )
    db.commit()
    return cur.lastrowid


# מוחק הודעה (למשל אם מנהל ראה שהיא לא מתאימה)
def delete_message(message_id: int):
    db = get_db()
    # אנחנו לא באמת מוחקים אותה לגמרי, רק מסמנים אותה כ"נמחקה" כדי שהיא תוסתר
    db.execute("UPDATE chat_messages SET is_deleted = 1 WHERE id = ?", (message_id,))
    db.commit()


# מדווח על הודעה למנהלים (אם מישהו כתב משהו מעליב)
def report_message(message_id: int):
    db = get_db()
    db.execute("UPDATE chat_messages SET is_reported = 1 WHERE id = ?", (message_id,))
    db.commit()


# המנהל משתמש בזה כדי לקבל רשימה של כל ההודעות שאנשים דיווחו עליהן
def get_reported_messages():
    db = get_db()
    return db.execute(
        """SELECT cm.*, ap.display_name FROM chat_messages cm
           LEFT JOIN athlete_profiles ap ON ap.user_id = cm.user_id
           WHERE cm.is_reported = 1 AND cm.is_deleted = 0
           ORDER BY cm.sent_at DESC"""
    ).fetchall()
    
    
# מעדכן מתי בפעם האחרונה המשתמש היה פעיל בחדר
def log_chat_activity(user_id: int, room_id: int):
    db = get_db()
    db.execute(
        "UPDATE chat_room_members SET last_active_at = CURRENT_TIMESTAMP WHERE user_id=? AND room_id=?",
        (user_id, room_id)
    )
    db.commit()


# ── צ'אט אישי מול המנהל (תמיכה טכנית / הודעות מהמערכת) ──

# יוצר (או מביא אם כבר קיים) חדר צ'אט סודי בין משתמש רגיל למנהל הראשי (Admin)
def get_or_create_admin_dm(user_id: int) -> int:
    """Get or create a private DM room between user_id and the admin."""
    db = get_db()
    # בודק אם כבר יש להם צ'אט פתוח בעבר
    existing = db.execute(
        "SELECT id FROM chat_rooms WHERE room_type='dm' AND owner_user_id=?",
        (user_id,)
    ).fetchone()
    
    if existing:
        return existing["id"]

    # אם אין, פותח חדר פרטי חדש
    ADMIN_ID = 1  # המנהל הראשי של המערכת הוא משתמש מספר 1
    room_name = f"Admin Support Chat"
    cur = db.execute(
        """INSERT INTO chat_rooms (name, description, room_type, owner_user_id)
           VALUES (?, ?, 'dm', ?)""",
        (room_name, "Private messages with the PeakForm admin team", user_id)
    )
    room_id = cur.lastrowid
    
    # מכניס את שניהם כ"נוכחים" בתוך החדר הפרטי
    for uid in [user_id, ADMIN_ID]:
        db.execute(
            "INSERT OR IGNORE INTO chat_room_members (room_id, user_id, nickname) VALUES (?,?,?)",
            (room_id, uid, "Admin" if uid == ADMIN_ID else "You")
        )
    db.commit()

    # המערכת שולחת הודעת פתיחה אוטומטית נחמדה
    welcome = "👋 Welcome to your private support channel! The admin team will respond here."
    db.execute(
        "INSERT INTO chat_messages (room_id, user_id, display_name, message) VALUES (?,?,?,?)",
        (room_id, ADMIN_ID, "PeakForm Admin", encrypt_data(welcome))
    )
    db.commit()
    return room_id


# מושך עבור המנהל את כל רשימת הצ'אטים הפרטיים שלו עם כל המשתמשים כדי שיוכל לענות להם
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
        # פותחים את ההצפנה של שם המשתמש
        try:
            d["user_display_name"] = decrypt_data(d["user_display_name"]) if d["user_display_name"] else "User"
        except Exception:
            pass
        results.append(d)
    return results


# פונקציה שמאפשרת לשלוח הודעה מתוך השרת ישר לתוך הצ'אט הפרטי (למשל: "התרגיל שלך אושר!")
def send_admin_dm_message(user_id: int, message: str):
    """Send an automatic message from admin into the user's DM room."""
    try:
        room_id = get_or_create_admin_dm(user_id)
        db = get_db()
        ADMIN_ID = 1
        # שומר את ההודעה מוצפנת בתוך החדר הפרטי
        db.execute(
            "INSERT INTO chat_messages (room_id, user_id, display_name, message) VALUES (?,?,?,?)",
            (room_id, ADMIN_ID, "PeakForm Admin", encrypt_data(message))
        )
        db.commit()
    except Exception:
        pass  # אם נכשל, אנחנו פשוט מתעלמים מזה כדי לא לעצור את מה שעשינו קודם

"""
English Summary:
This file is the database model layer for the chat system. It supports public community 
rooms and private admin Direct Messages (DMs). Functions are provided to securely insert 
encrypted chat messages, fetch and decrypt message history, track room memberships, report 
abuse, and programmatically send automated messages from the Admin to users.
"""
