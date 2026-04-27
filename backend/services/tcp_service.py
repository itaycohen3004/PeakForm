"""
SocketIO service — real-time group chat for Reprise community rooms.
"""
from flask_socketio import SocketIO, join_room, leave_room, emit

socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

_online_users = {}  # {user_id: {sid, display_name, room_id}}


def init_socketio(app):
    socketio.init_app(app)


@socketio.on("connect")
def on_connect():
    print(f"[SocketIO] Client connected: {__import__('flask').request.sid}")


@socketio.on("disconnect")
def on_disconnect():
    sid = __import__("flask").request.sid
    # Remove from online users
    user_id = None
    for uid, info in list(_online_users.items()):
        if info.get("sid") == sid:
            user_id = uid
            break
    if user_id:
        info = _online_users.pop(user_id)
        room_id = info.get("room_id")
        if room_id:
            emit("user_left", {"display_name": info.get("display_name")}, room=str(room_id))
            _broadcast_online_count(room_id)


@socketio.on("join_room")
def on_join_room(data):
    room_id   = str(data.get("room_id"))
    user_id   = data.get("user_id")
    display   = data.get("display_name", "Athlete")

    if not room_id or not user_id:
        return

    join_room(room_id)
    _online_users[user_id] = {"sid": __import__("flask").request.sid, "display_name": display, "room_id": room_id}
    emit("user_joined", {"display_name": display}, room=room_id)
    _broadcast_online_count(room_id)


@socketio.on("leave_room")
def on_leave_room(data):
    room_id = str(data.get("room_id"))
    user_id = data.get("user_id")
    leave_room(room_id)
    if user_id in _online_users:
        del _online_users[user_id]
    _broadcast_online_count(room_id)


@socketio.on("send_message")
def on_send_message(data):
    room_id      = str(data.get("room_id"))
    user_id      = data.get("user_id")
    display_name = data.get("display_name", "Athlete")
    message      = (data.get("message") or "").strip()

    if not message or not room_id:
        return

    # Persist to DB
    msg_id = None
    try:
        from backend.models.chat import save_message
        msg_id = save_message(int(room_id), user_id, display_name, message)
    except Exception as e:
        print(f"[SocketIO] DB save error: {e}")

    emit("new_message", {
        "id": msg_id,
        "room_id": int(room_id),
        "user_id": user_id,
        "display_name": display_name,
        "message": message,
        "sent_at": __import__("datetime").datetime.utcnow().isoformat(),
    }, room=room_id)


@socketio.on("report_message")
def on_report_message(data):
    msg_id = data.get("message_id")
    if msg_id:
        try:
            from backend.models.chat import report_message
            report_message(msg_id)
        except Exception:
            pass


def _broadcast_online_count(room_id):
    count = sum(1 for u in _online_users.values() if str(u.get("room_id")) == str(room_id))
    emit("online_count", {"room_id": room_id, "count": count}, room=str(room_id))
