"""
Chat routes — public group chat rooms.
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

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("/rooms", methods=["GET"])
@require_auth
def list_rooms():
    rows = get_rooms()
    rooms = []
    for r in rows:
        room = dict(r)
        membership = get_room_with_membership(r["id"], g.user_id)
        room["is_member"] = membership["is_member"]
        room["display_name"] = membership["display_name"]
        rooms.append(room)
    return jsonify(rooms), 200


@chat_bp.route("/rooms/<int:room_id>", methods=["GET"])
@require_auth
def room_detail(room_id):
    room = get_room_with_membership(room_id, g.user_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(room), 200


@chat_bp.route("/rooms/<int:room_id>/join", methods=["POST"])
@require_auth
def join(room_id):
    data = request.get_json(silent=True) or {}
    display_name = (data.get("display_name") or g.user_email.split("@")[0]).strip()
    if len(display_name) < 2:
        return jsonify({"error": "display_name must be at least 2 characters"}), 400
    join_room(room_id, g.user_id, display_name)
    return jsonify({"message": "Joined room.", "display_name": display_name}), 200


@chat_bp.route("/rooms/<int:room_id>/leave", methods=["POST"])
@require_auth
def leave(room_id):
    leave_room(room_id, g.user_id)
    return jsonify({"message": "Left room."}), 200


@chat_bp.route("/rooms/<int:room_id>/messages", methods=["GET"])
@require_auth
def messages(room_id):
    limit = int(request.args.get("limit", 80))
    rows  = get_messages(room_id, limit)
    return jsonify(list(reversed([dict(r) for r in rows]))), 200


@chat_bp.route("/rooms/<int:room_id>/messages", methods=["POST"])
@require_auth
def send_message(room_id):
    data    = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    print(f"[Chat] send_message called: room={room_id} user={g.user_id} msg_len={len(message)}")

    if not message:
        print(f"[Chat] Rejected: empty message from user={g.user_id}")
        return jsonify({"error": "message required"}), 400

    # Resolve display name: client payload → athlete profile → fallback
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

    # Verify the room exists before saving
    from backend.models.chat import get_room
    room = get_room(room_id)
    if not room:
        print(f"[Chat] Room {room_id} not found — rejecting message")
        return jsonify({"error": "Room not found"}), 404

    msg_id = save_message(room_id, g.user_id, display, message)
    print(f"[Chat] Message saved: id={msg_id} room={room_id} sender='{display}'")
    return jsonify({"id": msg_id, "message": "Message sent."}), 201


@chat_bp.route("/rooms", methods=["POST"])
@require_auth
@require_admin
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


@chat_bp.route("/messages/<int:msg_id>/report", methods=["POST"])
@require_auth
def report(msg_id):
    report_message(msg_id)
    return jsonify({"message": "Reported."}), 200


@chat_bp.route("/messages/<int:msg_id>", methods=["DELETE"])
@require_auth
def delete(msg_id):
    delete_message(msg_id)
    return jsonify({"message": "Deleted."}), 200
