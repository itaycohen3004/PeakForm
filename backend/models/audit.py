from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


def log_action(user_id, action: str, details: str = None, ip_address: str = None):
    """Write an audit log entry (safe to call even if user_id is None)."""
    try:
        db = get_db()
        db.execute(
            "INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
            (user_id, action, encrypt_data(details), ip_address),
        )
        db.commit()
    except Exception as e:
        # Never let audit logging break the main flow
        print(f"[AUDIT LOG ERROR] {e}")


def get_audit_logs(limit: int = 200, offset: int = 0, user_id: int = None):
    db = get_db()
    query = """SELECT al.*, u.email
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id = u.id"""
    params = []
    if user_id:
        query += " WHERE al.user_id = ?"
        params.append(user_id)
    query += " ORDER BY al.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = db.execute(query, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["details"] = decrypt_data(d["details"])
        d["email"]   = decrypt_data(d["email"])
        results.append(d)
    return results
