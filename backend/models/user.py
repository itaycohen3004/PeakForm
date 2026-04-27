from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data, blind_index


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
        self.id = id
        self.email = email
        self.email_index = email_index
        self.password_hash = password_hash
        self.role = role
        self.is_locked = bool(is_locked)
        self.failed_attempts = failed_attempts or 0
        self.created_at = created_at

    @staticmethod
    def _from_row(row):
        if not row:
            return None

        data = dict(row)
        user = User(**data)

        try:
            user.email = decrypt_data(data.get("email"))
        except Exception:
            user.email = data.get("email")

        return user

    @staticmethod
    def find_by_email(email: str):
        db = get_db()
        idx = blind_index(email)

        row = db.execute(
            "SELECT * FROM users WHERE email_index = ?",
            (idx,)
        ).fetchone()

        return User._from_row(row)

    @staticmethod
    def find_by_id(user_id: int):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        return User._from_row(row)

    @staticmethod
    def create(email: str, password_hash: str, role: str = "athlete") -> int:
        db = get_db()

        encrypted_email = encrypt_data(email)
        email_idx = blind_index(email)

        cur = db.execute(
            """
            INSERT INTO users (email, email_index, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (encrypted_email, email_idx, password_hash, role),
        )

        db.commit()
        return cur.lastrowid

    def update_password(self, new_hash: str):
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, self.id)
        )
        db.commit()

    def record_failed_attempt(self):
        db = get_db()

        self.failed_attempts += 1

        db.execute(
            "UPDATE users SET failed_attempts = ? WHERE id = ?",
            (self.failed_attempts, self.id)
        )

        if self.failed_attempts >= 10:
            db.execute(
                "UPDATE users SET is_locked = 1 WHERE id = ?",
                (self.id,)
            )
            self.is_locked = True

        db.commit()

    def unlock(self):
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
        db = get_db()

        db.execute(
            "UPDATE users SET is_locked = 1 WHERE id = ?",
            (self.id,)
        )

        self.is_locked = True
        db.commit()


def find_user_by_email(email: str):
    db = get_db()
    idx = blind_index(email)

    return db.execute(
        "SELECT * FROM users WHERE email_index = ?",
        (idx,)
    ).fetchone()


def find_user_by_id(user_id: int):
    db = get_db()

    return db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()


def create_user(email: str, password_hash: str, role: str) -> int:
    return User.create(email, password_hash, role)


def increment_failed_attempts(user_id: int):
    user = User.find_by_id(user_id)
    if user:
        user.record_failed_attempt()


def lock_user(user_id: int):
    user = User.find_by_id(user_id)
    if user:
        user.lock()


def reset_failed_attempts(user_id: int):
    user = User.find_by_id(user_id)
    if user:
        user.unlock()


def unlock_user(user_id: int):
    user = User.find_by_id(user_id)
    if user:
        user.unlock()


def get_all_users_admin(limit: int = 50, offset: int = 0):
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

        try:
            item["email"] = decrypt_data(item.get("email"))
        except Exception:
            pass

        users.append(item)

    return users


def delete_user(user_id: int):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def update_user_password(user_id: int, new_hash: str):
    user = User.find_by_id(user_id)
    if user:
        user.update_password(new_hash)