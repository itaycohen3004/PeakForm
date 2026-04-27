"""
Community routes — posts, comments, likes feed.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.community import (
    create_post, get_feed, delete_post,
    get_comments, add_comment, delete_comment,
    toggle_like, get_user_liked_posts,
)

community_bp = Blueprint("community", __name__, url_prefix="/api/community")


@community_bp.route("/feed", methods=["GET"])
@require_auth
def feed():
    limit  = int(request.args.get("limit", 30))
    offset = int(request.args.get("offset", 0))
    user_filter = request.args.get("user_id")
    rows   = get_feed(limit, offset, int(user_filter) if user_filter else None)
    posts  = [dict(r) for r in rows]
    post_ids = [p["id"] for p in posts]
    liked  = get_user_liked_posts(g.user_id, post_ids)
    for p in posts:
        p["liked_by_me"] = p["id"] in liked
    return jsonify(posts), 200


@community_bp.route("/posts", methods=["POST"])
@require_auth
def create():
    data    = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400

    valid_types = ["update","achievement","progress_photo","question","tip"]
    post_type = data.get("post_type", "update")
    if post_type not in valid_types:
        post_type = "update"

    post_id = create_post(g.user_id, content, post_type)
    return jsonify({"id": post_id, "message": "Post created."}), 201


@community_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@require_auth
def remove_post(post_id):
    delete_post(post_id)
    return jsonify({"message": "Post removed."}), 200


@community_bp.route("/posts/<int:post_id>/like", methods=["POST"])
@require_auth
def like(post_id):
    liked = toggle_like(post_id, g.user_id)
    return jsonify({"liked": liked}), 200


@community_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
@require_auth
def list_comments(post_id):
    rows = get_comments(post_id)
    return jsonify([dict(r) for r in rows]), 200


@community_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@require_auth
def add_comment_route(post_id):
    data    = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    comment_id = add_comment(post_id, g.user_id, content)
    return jsonify({"id": comment_id, "message": "Comment added."}), 201


@community_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@require_auth
def remove_comment(comment_id):
    delete_comment(comment_id)
    return jsonify({"message": "Comment removed."}), 200
