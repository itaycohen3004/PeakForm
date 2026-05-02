from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


# ============================================================
# פוסטים (Posts) - כמו באינסטגרם או פייסבוק, המתאמנים יכולים לפרסם פוסטים!
# ============================================================

def create_post(user_id: int, content: str, post_type: str = "update", media_path: str = None, meta_data: str = None) -> int:
    """
    פונקציה שיוצרת פוסט חדש. היא לוקחת את המילים שהמשתמש כתב ושומרת אותן.
    """
    db = get_db() # מתחברים למסד הנתונים
    # מכניסים שורה חדשה לטבלת הפוסטים.
    # שימו לב: אנחנו מצפינים (נועלים במפתח) את התוכן של הפוסט כדי לשמור על פרטיות!
    cur = db.execute(
        "INSERT INTO community_posts (user_id, content, post_type, media_path, meta_data) VALUES (?,?,?,?,?)",
        (user_id, encrypt_data(content), post_type, media_path, meta_data),
    )
    db.commit() # שומרים
    return cur.lastrowid # מחזירים את המספר המזהה של הפוסט החדש שנוצר


def get_feed(limit: int = 30, offset: int = 0, user_id_filter: int = None):
    """
    הפונקציה הזו מביאה את כל הפוסטים (כמו "פיד" של טיקטוק), מהחדש לישן.
    אפשר גם להביא רק פוסטים של מישהו ספציפי אם רוצים.
    """
    db = get_db()
    # אנחנו מכינים את השאלה (הבקשה) שלנו למסד הנתונים.
    # אנחנו רוצים את הפוסט, את השם של מי שכתב אותו, התמונה שלו, וכמה תגובות יש לו.
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
    # אם ביקשנו פוסטים רק של משתמש אחד:
    if user_id_filter:
        sql += " AND cp.user_id = ?"
        params.append(user_id_filter)
        
    # ממשיכים לבנות את הבקשה: תסדר לפי תאריך (הכי חדש קודם) ותביא רק כמות מסוימת של פוסטים
    sql += " GROUP BY cp.id ORDER BY cp.created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    
    # מפעילים את הבקשה ושומרים את התוצאות
    rows = db.execute(sql, params).fetchall()
    
    results = []
    # עוברים פוסט פוסט, פותחים את ההצפנה שלו (כדי שאפשר יהיה לקרוא) ומוסיפים לרשימה
    for r in rows:
        d = dict(r)
        d["content"] = decrypt_data(d["content"]) # פותחים נעילה של הטקסט
        d["display_name"] = decrypt_data(d["display_name"]) # פותחים נעילה של השם
        d["email"] = decrypt_data(d["email"]) # פותחים נעילה של האימייל
        # מידע נוסף (meta_data) ששמור בצורה רגילה פשוט נשאר כמו שהוא
        results.append(d)
    return results


def delete_post(post_id: int):
    """
    פונקציה שמוחקת פוסט. האמת היא שאנחנו לא באמת מוחקים אותו, 
    אנחנו פשוט מסמנים אותו כ"נמחק" (is_deleted = 1) ואז הוא פשוט לא מופיע יותר.
    זה נקרא "מחיקה רכה" (Soft delete).
    """
    db = get_db()
    db.execute("UPDATE community_posts SET is_deleted = 1 WHERE id = ?", (post_id,))
    db.commit()


# ============================================================
# תגובות (Comments) - המשתמשים יכולים להגיב אחד לשני!
# ============================================================

def get_comments(post_id: int):
    """
    פונקציה שמביאה את כל התגובות של פוסט מסוים.
    """
    db = get_db()
    # מבקשים את התגובות יחד עם הפרטים של מי שכתב אותן
    rows = db.execute(
        """SELECT cc.*, u.email, ap.display_name, ap.avatar_url
           FROM community_comments cc
           JOIN users u ON cc.user_id = u.id
           LEFT JOIN athlete_profiles ap ON ap.user_id = u.id
           WHERE cc.post_id = ? AND cc.is_deleted = 0
           ORDER BY cc.created_at ASC""",
        (post_id,),
    ).fetchall()
    
    results = []
    # כמו בפוסטים, אנחנו צריכים לפענח את התגובות המוצפנות
    for r in rows:
        d = dict(r)
        d["content"] = decrypt_data(d.get("content"))
        d["display_name"] = decrypt_data(d.get("display_name"))
        d["email"] = decrypt_data(d.get("email"))
        results.append(d)
    return results


def add_comment(post_id: int, user_id: int, content: str) -> int:
    """
    הפונקציה הזו לוקחת תגובה שמשתמש כתב, מצפינה אותה, ושומרת אותה במסד הנתונים.
    """
    db = get_db()
    cur = db.execute(
        "INSERT INTO community_comments (post_id, user_id, content) VALUES (?,?,?)",
        (post_id, user_id, encrypt_data(content)), # מצפינים את תוכן התגובה
    )
    db.commit()
    return cur.lastrowid # מחזירה את המספר המזהה של התגובה החדשה


def delete_comment(comment_id: int):
    """
    מוחקת תגובה (אותו טריק כמו בפוסט - מסמנים אותה כ"נמחקה" ולא באמת מעלימים).
    """
    db = get_db()
    db.execute("UPDATE community_comments SET is_deleted = 1 WHERE id = ?", (comment_id,))
    db.commit()


# ============================================================
# לייקים (Likes) - אפשר לעשות לייק לפוסטים!
# ============================================================

def toggle_like(post_id: int, user_id: int) -> bool:
    """
    הפונקציה של כפתור הלייק! היא עובדת כמו מתג:
    אם עשית כבר לייק, היא מורידה אותו. אם לא עשית, היא מוסיפה.
    היא מחזירה "אמת" (True) אם הוסף לייק, ו"שקר" (False) אם ירד לייק.
    """
    db = get_db()
    # בודקים האם המשתמש הזה כבר עשה לייק לפוסט הזה
    existing = db.execute(
        "SELECT id FROM community_likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    ).fetchone()
    
    if existing:
        # אם יש כבר לייק -> נמחק אותו
        db.execute("DELETE FROM community_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
        # ומורידים 1 מכמות הלייקים של הפוסט
        db.execute("UPDATE community_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
        db.commit()
        return False # מחזירים שהלייק הוסר
    else:
        # אם אין לייק -> נוסיף אותו
        db.execute("INSERT INTO community_likes (post_id, user_id) VALUES (?,?)", (post_id, user_id))
        # ומוסיפים 1 לכמות הלייקים של הפוסט
        db.execute("UPDATE community_posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        db.commit()
        return True # מחזירים שהלייק הוסף


def get_user_liked_posts(user_id: int, post_ids: list) -> set:
    """
    פונקציה שמקבלת רשימה של פוסטים ואומרת לנו לאילו מהם המשתמש עשה כבר לייק.
    זה חשוב כדי שנדע מתי לצבוע את הלב באדום באפליקציה!
    """
    if not post_ids: # אם הרשימה ריקה, אין מה לבדוק
        return set()
        
    db = get_db()
    # מכינים את השאלה למסד הנתונים
    placeholders = ",".join("?" for _ in post_ids)
    rows = db.execute(
        f"SELECT post_id FROM community_likes WHERE user_id = ? AND post_id IN ({placeholders})",
        [user_id] + post_ids,
    ).fetchall()
    
    # מחזירים רשימה (מסוג קבוצה - set) של כל הפוסטים שהמשתמש אהב
    return {r["post_id"] for r in rows}

"""
English Summary:
This file implements the backend logic for the PeakForm Community Feed. It provides 
database operations for creating encrypted posts, fetching the global feed with pagination, 
soft-deleting content, and adding/removing encrypted comments. It also handles the logic 
for toggling post likes and efficiently determining which posts a specific user has already liked.
"""
