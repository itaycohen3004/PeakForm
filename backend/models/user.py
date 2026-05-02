from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data, blind_index

# ============================================================
# מחלקת משתמש (User) - המחלקה שאחראית על כל מי שרשום לאתר
# ============================================================
class User:
    def __init__(
        self,
        id=None,
        email=None,
        email_index=None,
        password_hash=None,
        role="athlete",
        is_locked=0,
        failed_attempts=0,
        created_at=None,
        **kwargs
    ):
        """
        כאן אנחנו יוצרים "כרטיסייה" לכל משתמש עם כל הפרטים שלו.
        """
        self.id = id # מספר זהות במערכת
        self.email = email # כתובת המייל שלו
        self.email_index = email_index # מייל מיוחד שעוזר לנו לחפש משתמשים בלי לחשוף את המייל האמיתי
        self.password_hash = password_hash # הסיסמה שלו (אבל לא הסיסמה האמיתית, אלא גרסה מעורבבת וסודית)
        self.role = role # התפקיד שלו - בדרך כלל "מתאמן" (athlete) אבל יכול להיות גם מנהל
        self.is_locked = bool(is_locked) # האם החשבון נעול? (למשל אם ניסה לנחש סיסמה יותר מדי פעמים)
        self.failed_attempts = failed_attempts or 0 # כמה פעמים הוא טעה בסיסמה
        self.created_at = created_at # מתי הוא נרשם לאתר

    @staticmethod
    def _from_row(row):
        """
        פונקציה שלוקחת את הנתונים שמצאנו במסד הנתונים והופכת אותם לאובייקט "משתמש" אמיתי.
        """
        if not row:
            return None # אם לא מצאנו כלום, נחזיר "כלום"

        data = dict(row) # הופכים את השורה למילון שאפשר לקרוא בקלות
        user = User(**data) # יוצרים את המשתמש

        # המייל שמור בצורה מוצפנת, אז אנחנו צריכים לפתוח את ההצפנה
        try:
            user.email = decrypt_data(data.get("email"))
        except Exception:
            # אם משום מה לא הצלחנו לפענח, נשאיר אותו כמו שהוא
            user.email = data.get("email")

        return user

    @staticmethod
    def find_by_email(email: str):
        """
        פונקציה שמחפשת משתמש לפי האימייל שלו.
        אנחנו משתמשים ב"אינדקס עיוור" כדי לחפש, שזו שיטה בטוחה למצוא מידע מוצפן.
        """
        db = get_db()
        idx = blind_index(email) # הופכים את האימייל לקוד חיפוש סודי

        row = db.execute(
            "SELECT * FROM users WHERE email_index = ?",
            (idx,)
        ).fetchone()

        return User._from_row(row)

    @staticmethod
    def find_by_id(user_id: int):
        """
        מחפשת משתמש לפי המספר המזהה (ID) שלו.
        """
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        return User._from_row(row)

    @staticmethod
    def create(email: str, password_hash: str, role: str = "athlete") -> int:
        """
        יוצרת משתמש חדש לגמרי במערכת כשהוא נרשם פעם ראשונה!
        """
        db = get_db()

        # שומרים על פרטיות! אנחנו מצפינים את המייל
        encrypted_email = encrypt_data(email)
        # ויוצרים קוד חיפוש סודי למייל
        email_idx = blind_index(email)

        cur = db.execute(
            """
            INSERT INTO users (email, email_index, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (encrypted_email, email_idx, password_hash, role),
        )

        db.commit()
        return cur.lastrowid # מחזירה את המספר החדש של המשתמש שנוצר

    def update_password(self, new_hash: str):
        """
        מעדכנת את הסיסמה של המשתמש (אם הוא שכח או רוצה להחליף).
        """
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, self.id)
        )
        db.commit()

    def record_failed_attempt(self):
        """
        הפונקציה הזו מופעלת כשמישהו מנסה להתחבר וטועה בסיסמה.
        אם הוא טועה יותר מדי פעמים, אנחנו נועלים לו את החשבון בשביל ביטחון!
        """
        db = get_db()

        self.failed_attempts += 1 # מוסיפים 1 לספירת הטעויות

        db.execute(
            "UPDATE users SET failed_attempts = ? WHERE id = ?",
            (self.failed_attempts, self.id)
        )

        # אם הוא טעה 10 פעמים או יותר!
        if self.failed_attempts >= 10:
            db.execute(
                "UPDATE users SET is_locked = 1 WHERE id = ?",
                (self.id,)
            )
            self.is_locked = True # נועלים את החשבון! האקר לא יכנס לפה!

        db.commit()

    def unlock(self):
        """
        פותחת את החשבון מחדש אחרי שהוא ננעל (ומאפסת את ספירת הטעויות).
        """
        db = get_db()

        db.execute(
            """
            UPDATE users
            SET is_locked = 0, failed_attempts = 0
            WHERE id = ?
            """,
            (self.id,)
        )

        self.is_locked = False
        self.failed_attempts = 0
        db.commit()

    def lock(self):
        """
        נועלת את החשבון בכוונה (למשל אם מנהל האתר מחליט לחסום משתמש רע).
        """
        db = get_db()

        db.execute(
            "UPDATE users SET is_locked = 1 WHERE id = ?",
            (self.id,)
        )

        self.is_locked = True
        db.commit()


# ============================================================
# פונקציות כלליות שעושות את אותן פעולות בצורה פשוטה יותר מחוץ למחלקה
# ============================================================

def find_user_by_email(email: str):
    """מוצא משתמש לפי אימייל"""
    db = get_db()
    idx = blind_index(email)

    return db.execute(
        "SELECT * FROM users WHERE email_index = ?",
        (idx,)
    ).fetchone()


def find_user_by_id(user_id: int):
    """מוצא משתמש לפי תעודת זהות (ID)"""
    db = get_db()

    return db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()


def create_user(email: str, password_hash: str, role: str) -> int:
    """יוצר משתמש חדש"""
    return User.create(email, password_hash, role)


def increment_failed_attempts(user_id: int):
    """רושם שהייתה טעות בסיסמה למשתמש מסוים"""
    user = User.find_by_id(user_id)
    if user:
        user.record_failed_attempt()


def lock_user(user_id: int):
    """נועל משתמש"""
    user = User.find_by_id(user_id)
    if user:
        user.lock()


def reset_failed_attempts(user_id: int):
    """מאפס את ספירת הטעויות של משתמש"""
    user = User.find_by_id(user_id)
    if user:
        user.unlock()


def unlock_user(user_id: int):
    """משחרר משתמש מנעילה"""
    user = User.find_by_id(user_id)
    if user:
        user.unlock()


def get_all_users_admin(limit: int = 50, offset: int = 0):
    """
    מביא רשימה של כל המשתמשים באתר. רק המנהל (Admin) משתמש בזה!
    """
    db = get_db()

    rows = db.execute(
        """
        SELECT id, email, role, is_locked, failed_attempts, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset)
    ).fetchall()

    users = []

    for row in rows:
        item = dict(row)

        # פותחים את ההצפנה של המייל של כל אחד כדי שהמנהל יוכל לראות
        try:
            item["email"] = decrypt_data(item.get("email"))
        except Exception:
            pass

        users.append(item)

    return users


def delete_user(user_id: int):
    """מוחק משתמש לצמיתות מהאתר"""
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def update_user_password(user_id: int, new_hash: str):
    """מעדכן סיסמה למשתמש"""
    user = User.find_by_id(user_id)
    if user:
        user.update_password(new_hash)

"""
English Summary:
This file implements the User model which orchestrates account creation, authentication, 
and account security. It uses a strict Object-Oriented approach for data manipulation.
Critical security mechanisms are employed here, including "Blind Indexing" to allow searching 
for users by email without storing their plaintext email in the database, and an automated 
account lockout mechanism that trips after 10 failed login attempts to prevent brute-force attacks.
"""