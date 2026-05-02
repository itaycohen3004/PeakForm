"""
SocketIO service — שירות הצ'אט בזמן אמת של PeakForm.
כאן מתבצע החיבור שמאפשר למשתמשים לשלוח הודעות אחד לשני מיידית!
"""
from flask_socketio import SocketIO, join_room, leave_room, emit

# יוצרים את ה"מרכזייה" של הצ'אט שמתירה גישה מכל מקום (CORS=*)
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

# רשימה סודית ששומרת מי מחובר כרגע לאיזה חדר
_online_users = {}  # {user_id: {sid, display_name, room_id}}


# פונקציה שמחברת את השרת שלנו (האפליקציה) למערכת הצ'אט
def init_socketio(app):
    socketio.init_app(app)


# ברגע שמישהו מתחבר לאתר (פותח דפדפן)
@socketio.on("connect")
def on_connect():
    print(f"[SocketIO] Client connected: {__import__('flask').request.sid}")


# ברגע שמישהו סוגר את הדפדפן ומתנתק מהשרת
@socketio.on("disconnect")
def on_disconnect():
    sid = __import__("flask").request.sid # המספר המזהה של החיבור שלו
    # עוברים על רשימת המשתמשים כדי למצוא מי התנתק
    user_id = None
    for uid, info in list(_online_users.items()):
        if info.get("sid") == sid:
            user_id = uid
            break
            
    # אם מצאנו אותו, נמחק אותו מהרשימה ונודיע לכולם שהוא עזב
    if user_id:
        info = _online_users.pop(user_id)
        room_id = info.get("room_id")
        if room_id:
            # שולחים הודעה "משתמש עזב" לחדר שלו
            emit("user_left", {"display_name": info.get("display_name")}, room=str(room_id))
            _broadcast_online_count(room_id) # מעדכנים את מונה המחוברים בחדר


# כשהמשתמש לוחץ על חדר ונכנס אליו
@socketio.on("join_room")
def on_join_room(data):
    room_id   = str(data.get("room_id"))
    user_id   = data.get("user_id")
    display   = data.get("display_name", "Athlete")

    if not room_id or not user_id:
        return

    join_room(room_id) # מצרפים אותו טכנית לחדר
    # שומרים את השם שלו ברשימה של החדר הזה
    _online_users[user_id] = {"sid": __import__("flask").request.sid, "display_name": display, "room_id": room_id}
    # שולחים הודעה לכולם בחדר "היי, מישהו חדש הצטרף!"
    emit("user_joined", {"display_name": display}, room=room_id)
    _broadcast_online_count(room_id)


# כשהמשתמש יוצא מהחדר
@socketio.on("leave_room")
def on_leave_room(data):
    room_id = str(data.get("room_id"))
    user_id = data.get("user_id")
    leave_room(room_id) # מוציאים אותו
    if user_id in _online_users:
        del _online_users[user_id] # מוחקים אותו מהרישומים
    _broadcast_online_count(room_id)


# כשהמשתמש כותב הודעה ולוחץ "שלח"
@socketio.on("send_message")
def on_send_message(data):
    room_id      = str(data.get("room_id"))
    user_id      = data.get("user_id")
    display_name = data.get("display_name", "Athlete")
    message      = (data.get("message") or "").strip()

    if not message or not room_id:
        return # לא שולחים הודעה ריקה!

    # שומרים את ההודעה לתמיד בתוך בסיס הנתונים שלנו (DB)
    msg_id = None
    try:
        from backend.models.chat import save_message
        msg_id = save_message(int(room_id), user_id, display_name, message)
    except Exception as e:
        print(f"[SocketIO] DB save error: {e}")

    # ואז מפזרים את ההודעה (משדרים אותה) לכל מי שמחובר עכשיו לחדר הזה!
    emit("new_message", {
        "id": msg_id,
        "room_id": int(room_id),
        "user_id": user_id,
        "display_name": display_name,
        "message": message,
        "sent_at": __import__("datetime").datetime.utcnow().isoformat(),
    }, room=room_id)


# דיווח על הודעה פוגענית
@socketio.on("report_message")
def on_report_message(data):
    msg_id = data.get("message_id")
    if msg_id:
        try:
            from backend.models.chat import report_message
            report_message(msg_id) # רושמים בבסיס הנתונים שיש תלונה על ההודעה
        except Exception:
            pass


# פונקציית עזר: סופרת כמה משתמשים נמצאים עכשיו באותו החדר ושולחת להם את המספר
def _broadcast_online_count(room_id):
    count = sum(1 for u in _online_users.values() if str(u.get("room_id")) == str(room_id))
    emit("online_count", {"room_id": room_id, "count": count}, room=str(room_id))

"""
English Summary:
This module initializes and manages the overarching Socket.IO server setup. It handles global 
connection lifecycle events like connect and disconnect, tracks online users in a volatile memory map, 
broadcasts live "online counts" to chat rooms, and persists real-time messages to the database.

סיכום בעברית:
קובץ זה הוא "מרכזיית התקשורת" המהירה של האתר. הוא מנהל את רשימת כל האנשים שמחוברים כרגע לאתר
ויודע לאיזה חדר צ'אט הם נכנסו. אם מישהו יוצא מהדפדפן, הוא מוחק אותו מיד מהרשימה ומעדכן את כולם
שהוא עזב. הוא גם אחראי לשמור בבסיס הנתונים כל הודעה שנכתבת ולשלוח אותה למסכים של כולם מיד.
"""
