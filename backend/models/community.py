from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


# ============================================================
# Posts
# ============================================================

def create_post(user_id: int, content: str, post_type: str = "update", media_path: str = None) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO community_posts (user_id, content, post_type, media_path) VALUES (?,?,?,?)",
        (user_id, encrypt_data(content), post_type, media_path),
    )
    db.commit()
    return cur.lastrowid


def get_feed(limit: int = 30, offset: int = 0, user_id_filter: int = None):
    db = get_db()
    sql = """
        SELECT cp.*, u.email,
               ap.display_name, ap.avatar_url,
               COUNT(DISTINCT cc.id) as comment_count
        FROM community_posts cp
        JOIN users u ON cp.user_id = u.id
        LEFT JOIN athlete_profiles ap ON ap.user_id = u.id
        LEFT JOIN community_comments cc ON cc.post_id = cp.id AND cc.is_deleted = 0
        WHERE cp.is_deleted = 0
    """
    params = []
    if user_id_filter:
        sql += " AND cp.user_id = ?"
        params.append(user_id_filter)
    sql += " GROUP BY cp.id ORDER BY cp.created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = db.execute(sql, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["content"] = decrypt_data(d["content"])
        d["display_name"] = decrypt_data(d["display_name"])
        d["email"] = decrypt_data(d["email"])
        results.append(d)
    return results


def delete_post(post_id: int):
    db = get_db()
    db.execute("UPDATE community_posts SET is_deleted = 1 WHERE id = ?", (post_id,))
    db.commit()


# ============================================================
# Comments
# ============================================================

def get_comments(post_id: int):
    db = get_db()
    return db.execute(
        """SELECT cc.*, u.email, ap.display_name, ap.avatar_url
           FROM community_comments cc
           JOIN users u ON cc.user_id = u.id
           LEFT JOIN athlete_profiles ap ON ap.user_id = u.id
           WHERE cc.post_id = ? AND cc.is_deleted = 0
           ORDER BY cc.created_at ASC""",
        (post_id,),
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["content"] = decrypt_data(d["content"])
        d["display_name"] = decrypt_data(d["display_name"])
        d["email"] = decrypt_data(d["email"])
        results.append(d)
    return results


def add_comment(post_id: int, user_id: int, content: str) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO community_comments (post_id, user_id, content) VALUES (?,?,?)",
        (post_id, user_id, encrypt_data(content)),
    )
    db.commit()
    return cur.lastrowid


def delete_comment(comment_id: int):
    db = get_db()
    db.execute("UPDATE community_comments SET is_deleted = 1 WHERE id = ?", (comment_id,))
    db.commit()


# ============================================================
# Likes
# ============================================================

def toggle_like(post_id: int, user_id: int) -> bool:
    """Returns True if liked, False if unliked."""
    db = get_db()
    existing = db.execute(
        "SELECT id FROM community_likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    ).fetchone()
    if existing:
        db.execute("DELETE FROM community_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
        db.execute("UPDATE community_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
        db.commit()
        return False
    else:
        db.execute("INSERT INTO community_likes (post_id, user_id) VALUES (?,?)", (post_id, user_id))
        db.execute("UPDATE community_posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        db.commit()
        return True


def get_user_liked_posts(user_id: int, post_ids: list) -> set:
    if not post_ids:
        return set()
    db = get_db()
    placeholders = ",".join("?" for _ in post_ids)
    rows = db.execute(
        f"SELECT post_id FROM community_likes WHERE user_id = ? AND post_id IN ({placeholders})",
        [user_id] + post_ids,
    ).fetchall()
    return {r["post_id"] for r in rows}
