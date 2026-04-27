from flask import Blueprint, jsonify, request

notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)

_demo_notifications = []


def _get_user_id():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return 1
    return 1


@notifications_bp.route("/", methods=["GET"])
def get_notifications():
    user_id = _get_user_id()

    items = [n for n in _demo_notifications if n["user_id"] == user_id]
    items.sort(key=lambda x: x["id"], reverse=True)

    return jsonify(items)


@notifications_bp.route("/add", methods=["POST"])
def add_notification():
    user_id = _get_user_id()
    data = request.get_json() or {}

    title = (data.get("title") or "").strip()
    message = (data.get("message") or "").strip()

    if not title:
        return jsonify({"error": "Title required"}), 400

    item = {
        "id": len(_demo_notifications) + 1,
        "user_id": user_id,
        "title": title,
        "message": message,
        "is_read": False,
    }

    _demo_notifications.append(item)

    return jsonify({"success": True, "notification": item})


@notifications_bp.route("/<int:item_id>/read", methods=["POST"])
def mark_read(item_id):
    user_id = _get_user_id()

    for item in _demo_notifications:
        if item["id"] == item_id and item["user_id"] == user_id:
            item["is_read"] = True
            return jsonify({"success": True})

    return jsonify({"error": "Not found"}), 404


@notifications_bp.route("/clear", methods=["POST"])
def clear_all():
    global _demo_notifications
    user_id = _get_user_id()

    _demo_notifications = [
        n for n in _demo_notifications
        if n["user_id"] != user_id
    ]

    return jsonify({"success": True})