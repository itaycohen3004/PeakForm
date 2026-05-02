"""
Chat routes — public group chat rooms.
כאן נמצאת מערכת הצ'אט של הקהילה! פה אנחנו מנהלים את החדרים 
ואת כל ההודעות שאנשים שולחים אחד לשני.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.middleware.roles import require_admin
from backend.models.chat import (
    get_rooms, get_room, get_room_with_membership,
    join_room, leave_room, get_messages, save_message,
    delete_message, report_message,
    create_public_room,
)

# אזור הצ'אט באתר מתחיל תמיד בכתובת /api/chat
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


# מביא לנו את רשימת כל חדרי הצ'אט שקיימים באתר
@chat_bp.route("/rooms", methods=["GET"])
@require_auth
def list_rooms():
    rows = get_rooms()
    rooms = []
    for r in rows:
        room = dict(r)
        # בודקים אם המתאמן כבר הצטרף לחדר הזה או לא
        membership = get_room_with_membership(r["id"], g.user_id)
        room["is_member"] = membership["is_member"]
        room["display_name"] = membership["display_name"]
        rooms.append(room)
    return jsonify(rooms), 200


# מביא פרטים על חדר ספציפי אחד (למשל חדר "מתחילים")
@chat_bp.route("/rooms/<int:room_id>", methods=["GET"])
@require_auth
def room_detail(room_id):
    room = get_room_with_membership(room_id, g.user_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(room), 200


# כשהמשתמש רוצה להצטרף לחדר בפעם הראשונה
@chat_bp.route("/rooms/<int:room_id>/join", methods=["POST"])
@require_auth
def join(room_id):
    data = request.get_json(silent=True) or {}
    # מנסה לקחת את הכינוי שלו, או חותך את תחילת האימייל שלו אם אין לו כינוי
    display_name = (data.get("display_name") or g.user_email.split("@")[0]).strip()
    if len(display_name) < 2:
        return jsonify({"error": "display_name must be at least 2 characters"}), 400
    join_room(room_id, g.user_id, display_name)
    return jsonify({"message": "Joined room.", "display_name": display_name}), 200


# כשהמשתמש רוצה לעזוב חדר
@chat_bp.route("/rooms/<int:room_id>/leave", methods=["POST"])
@require_auth
def leave(room_id):
    leave_room(room_id, g.user_id)
    return jsonify({"message": "Left room."}), 200


# מושך את כל ההודעות הישנות שנשלחו בחדר (כדי שנוכל לגלול אחורה)
@chat_bp.route("/rooms/<int:room_id>/messages", methods=["GET"])
@require_auth
def messages(room_id):
    limit = int(request.args.get("limit", 80)) # מביא את ה-80 האחרונות
    rows  = get_messages(room_id, limit)
    return jsonify(list(reversed([dict(r) for r in rows]))), 200


# כשמשתמש שולח הודעה לתוך החדר
@chat_bp.route("/rooms/<int:room_id>/messages", methods=["POST"])
@require_auth
def send_message(room_id):
    data    = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    print(f"[Chat] send_message called: room={room_id} user={g.user_id} msg_len={len(message)}")

    if not message:
        print(f"[Chat] Rejected: empty message from user={g.user_id}")
        return jsonify({"error": "message required"}), 400

    # מנסים למצוא את השם האמיתי של המתאמן כדי להציג אותו ליד ההודעה
    display = data.get("display_name", "").strip()
    if not display or display.startswith("gAAAA"):
        try:
            from backend.models.athlete import get_athlete_profile, Athlete
            p = get_athlete_profile(g.user_id)
            display = Athlete(dict(p)).display_name if p else "User"
            print(f"[Chat] Resolved display_name from profile: '{display}'")
        except Exception as ex:
            display = "User"
            print(f"[Chat] display_name fallback to 'User': {ex}")
    else:
        print(f"[Chat] Using client-provided display_name: '{display}'")

    # מוודאים שהחדר בכלל קיים לפני ששומרים את ההודעה
    from backend.models.chat import get_room
    room = get_room(room_id)
    if not room:
        print(f"[Chat] Room {room_id} not found — rejecting message")
        return jsonify({"error": "Room not found"}), 404

    msg_id = save_message(room_id, g.user_id, display, message) # שומרים במסד הנתונים
    print(f"[Chat] Message saved: id={msg_id} room={room_id} sender='{display}'")
    return jsonify({"id": msg_id, "message": "Message sent."}), 201


# מנהל יכול לפתוח חדר צ'אט חדש! (למשל: "חדר מרימי משקולות")
@chat_bp.route("/rooms", methods=["POST"])
@require_auth
@require_admin # רק מנהלים יכולים!
def create_room():
    """Admin only — create a new public chat room."""
    from backend.models.chat import create_public_room
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    desc = (data.get("description") or "").strip()
    if not name:
        return jsonify({"error": "Room name required"}), 400
    if len(name) > 60:
        return jsonify({"error": "Room name too long (max 60 chars)"}), 400
    room_id = create_public_room(name, desc, g.user_id)
    print(f"[Chat] Admin created new room: '{name}' id={room_id}")
    return jsonify({"id": room_id, "message": f"Room '{name}' created."}), 201


# אם מישהו כתב משהו מעליב, אפשר לדווח על ההודעה הזו למנהל
@chat_bp.route("/messages/<int:msg_id>/report", methods=["POST"])
@require_auth
def report(msg_id):
    report_message(msg_id)
    return jsonify({"message": "Reported."}), 200


# אפשרות למחוק הודעה
@chat_bp.route("/messages/<int:msg_id>", methods=["DELETE"])
@require_auth
def delete(msg_id):
    delete_message(msg_id)
    return jsonify({"message": "Deleted."}), 200

"""
English Summary:
This module manages the chat rooms for the platform. It provides endpoints for users to list rooms,
join or leave rooms, send messages, and fetch message history. It also includes an admin-only endpoint 
to create new chat rooms, and general user endpoints to report abusive messages or delete their own messages.

סיכום בעברית:
קובץ זה מנהל את חדרי הצ'אט של המערכת. הוא מאפשר למשתמשים לראות את כל החדרים הזמינים,
להצטרף לחדר, לשלוח הודעות ולמשוך היסטוריה של הודעות ישנות. יש בו מנגנונים ששומרים על סביבה 
בטוחה (כמו אפשרות לדווח על הודעות פוגעניות). בנוסף, מנהלי המערכת יכולים דרך קובץ זה ליצור 
חדרי צ'אט חדשים.
"""
