from flask_socketio import emit, join_room, leave_room
from backend.models.chat import save_message, log_chat_activity


def register_socket_events(socketio):

    @socketio.on("join")
    def on_join(data):
        room_id = data.get("room")
        if not room_id:
            return
        join_room(str(room_id))

    @socketio.on("leave")
    def on_leave(data):
        room_id = data.get("room")
        if not room_id:
            return
        leave_room(str(room_id))

    @socketio.on("message")
    def handle_message(data):
        room_id = data.get("room")
        user_id = data.get("user_id")
        text = (data.get("message") or "").strip()
        display_name = data.get("display_name", "Athlete")

        if not room_id or not user_id or not text:
            return

        msg_id = save_message(int(room_id), user_id, display_name, text)

        payload = {
            "id": msg_id,
            "room_id": int(room_id),
            "user_id": user_id,
            "display_name": display_name,
            "message": text,
            "created_at": "Just now",
        }

        emit("message", payload, room=str(room_id))

        try:
            log_chat_activity(user_id, room_id)
        except Exception:
            pass

    @socketio.on("join_room")
    def on_join_room(data):
        room_id = data.get("room_id")
        if not room_id:
            return

        join_room(str(room_id))
        emit("online_count", {"room_id": int(room_id), "count": 1}, room=str(room_id))

    @socketio.on("leave_room")
    def on_leave_room(data):
        room_id = data.get("room_id")
        if not room_id:
            return

        leave_room(str(room_id))

    @socketio.on("send_message")
    def on_send_message(data):
        room_id = data.get("room_id")
        user_id = data.get("user_id")
        display_name = data.get("display_name", "Athlete")
        message = (data.get("message") or "").strip()

        if not room_id or not user_id or not message:
            return

        msg_id = save_message(int(room_id), user_id, display_name, message)

        emit(
            "new_message",
            {
                "id": msg_id,
                "room_id": int(room_id),
                "user_id": user_id,
                "display_name": display_name,
                "message": message,
            },
            room=str(room_id),
        )