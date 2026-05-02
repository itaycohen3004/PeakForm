from flask_socketio import emit, join_room, leave_room
from backend.models.chat import save_message, log_chat_activity

# קובץ זה גם כן אחראי על ניהול אירועים של הצ'אט (כניסה לחדרים, יציאה ושליחת הודעות)
def register_socket_events(socketio):

    # ברגע שמשתמש אומר לנו "אני רוצה להצטרף לחדר ספציפי"
    @socketio.on("join")
    def on_join(data):
        room_id = data.get("room") # איזה חדר הוא בחר?
        if not room_id:
            return # אם הוא לא אמר, אל תעשה כלום
        join_room(str(room_id)) # מצרפים אותו לערוץ של החדר

    # ברגע שהמשתמש רוצה לעזוב את החדר
    @socketio.on("leave")
    def on_leave(data):
        room_id = data.get("room")
        if not room_id:
            return
        leave_room(str(room_id)) # מוציאים אותו מהערוץ כדי שלא יקבל הודעות יותר

    # כשמשתמש שולח הודעה טקסטואלית רגילה
    @socketio.on("message")
    def handle_message(data):
        room_id = data.get("room")
        user_id = data.get("user_id")
        text = (data.get("message") or "").strip() # שולפים את הטקסט ומנקים רווחים מיותרים
        display_name = data.get("display_name", "Athlete") # השם שלו (או "מתאמן" כברירת מחדל)

        if not room_id or not user_id or not text:
            return # חובה שיהיה טקסט!

        # שומרים במסד הנתונים
        msg_id = save_message(int(room_id), user_id, display_name, text)

        # מרכיבים את ההודעה כמו שצריך כדי לשלוח למסכים של שאר האנשים
        payload = {
            "id": msg_id,
            "room_id": int(room_id),
            "user_id": user_id,
            "display_name": display_name,
            "message": text,
            "created_at": "Just now", # עכשיו נשלח!
        }

        emit("message", payload, room=str(room_id)) # משדרים לכולם

        try:
            # רושמים לעצמנו מתי הוא היה פעיל לאחרונה (בשביל אנליטיקות של האתר)
            log_chat_activity(user_id, room_id)
        except Exception:
            pass

    # גירסה נוספת שמטפלת בהצטרפות אבל גם מודיעה לכולם כמה אנשים עכשיו מחוברים
    @socketio.on("join_room")
    def on_join_room(data):
        room_id = data.get("room_id")
        if not room_id:
            return

        join_room(str(room_id))
        emit("online_count", {"room_id": int(room_id), "count": 1}, room=str(room_id))

    # גירסה נוספת לעזיבת חדר
    @socketio.on("leave_room")
    def on_leave_room(data):
        room_id = data.get("room_id")
        if not room_id:
            return

        leave_room(str(room_id))

    # גירסה מורחבת לשליחת הודעה שמוסיפה תווית מיוחדת "new_message" לדפדפן
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

"""
English Summary:
This file implements the WebSocket event handlers (Socket.IO) for real-time community chat functionality.
It listens for user connections, room joins/leaves, and incoming messages, ensuring that chats update 
instantly across all connected clients without requiring a page refresh.

סיכום בעברית:
קובץ זה מתפעל את האירועים החיים של מערכת הצ'אט. הוא מאזין לכל מה שקורה בזמן אמת - מי התחבר,
מי עזב, ואיזו הודעה נשלחה. ברגע שהודעה נשלחת, הקובץ משדר אותה באופן מיידי לכל שאר המשתמשים
שנמצאים באותו חדר, מה שמאפשר שיחה רציפה וחלקה כמו בווטסאפ או בטלגרם.
"""