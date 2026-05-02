"""
Audit log model — tracks what happens in the system.
קובץ "יומן המעקב" שלנו! כמו מצלמות אבטחה של האתר. 
הוא שומר תיעוד של כל פעולה חשובה שקורית כדי שנדע מי עשה מה ומתי.
"""
from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


# פונקציה שכותבת ביומן: היא לוקחת איזה משתמש עשה משהו, מה הוא עשה, פרטים וכתובת האינטרנט שלו
def log_action(user_id, action: str, details: str = None, ip_address: str = None):
    """Write an audit log entry (safe to call even if user_id is None)."""
    try:
        db = get_db()
        # אנחנו שומרים את הפעולה במסד הנתונים, אבל מצפינים את הפרטים (details) בשביל אבטחה!
        db.execute(
            "INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
            (user_id, action, encrypt_data(details), ip_address),
        )
        db.commit()
    except Exception as e:
        # Never let audit logging break the main flow
        # אם יש שגיאה ברישום, לא נקריס את האתר בגלל זה. רק נדפיס הודעת שגיאה.
        print(f"[AUDIT LOG ERROR] {e}")


# פונקציה שהמנהל משתמש בה כדי לקרוא את היומן ולהבין מה קרה באתר
def get_audit_logs(limit: int = 200, offset: int = 0, user_id: int = None):
    db = get_db()
    # אנחנו מחברים את הטבלה של היומן לטבלה של המשתמשים כדי לקבל את המייל של מי שעשה את הפעולה
    query = """SELECT al.*, u.email
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id = u.id"""
    params = []
    
    # אם המנהל מחפש מידע רק על משתמש אחד ספציפי
    if user_id:
        query += " WHERE al.user_id = ?"
        params.append(user_id)
        
    # מסדרים מהחדש לישן, ובוחרים כמה להביא כדי לא לתקוע את המחשב
    query += " ORDER BY al.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.execute(query, params).fetchall()
    results = []
    
    # עוברים על כל שורה ביומן ופותחים את ההצפנה (פענוח) כדי שהמנהל יוכל לקרוא!
    for r in rows:
        d = dict(r)
        d["details"] = decrypt_data(d["details"])
        d["email"]   = decrypt_data(d["email"])
        results.append(d)
        
    return results

"""
English Summary:
This file is the "security camera" (audit log) model of the application. It provides 
functions to securely insert new log entries into the database whenever an important 
action occurs. Sensitive details inside the logs are encrypted at rest. It also provides 
a function for administrators to fetch, decrypt, and review the history of system actions.
"""
