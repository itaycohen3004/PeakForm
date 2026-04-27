"""
Authentication service — bcrypt hashing, JWT generation, 2FA codes.
"""

import os
import random
import string
import datetime
import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_fallback")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))


# ============================================================
# Password Hashing
# ============================================================

def hash_password(password: str) -> str:
    """Hash a plain password with bcrypt. Returns a UTF-8 string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ============================================================
# Password Validation
# ============================================================

def validate_password_strength(password: str) -> list:
    """
    Return a list of validation error messages.
    Empty list means password is valid.
    """
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errors.append("Password must contain at least one special character.")
    return errors


# ============================================================
# JWT
# ============================================================

def generate_jwt(user_id: int, role: str, email: str = "", **kwargs) -> str:
    """Generate a JWT token valid for JWT_EXPIRY_HOURS hours."""
    payload = {
        "user_id": user_id,
        "role":    role,
        "email":   email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Decode and validate a JWT token. Raises jwt.* on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


# ============================================================
# Two-Factor Authentication
# ============================================================

def generate_2fa_code() -> str:
    """Generate a random 6-digit numeric 2FA code."""
    return "".join(random.choices(string.digits, k=6))


def store_2fa_code(user_id: int, code: str):
    """Store a 2FA code in the database with 5-minute expiry."""
    from backend.models.db import get_db
    import datetime
    db = get_db()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
    # Invalidate any previous unused codes for this user
    db.execute(
        "UPDATE two_factor_codes SET used = 1 WHERE user_id = ? AND used = 0",
        (user_id,),
    )
    db.execute(
        "INSERT INTO two_factor_codes (user_id, code, expires_at) VALUES (?, ?, ?)",
        (user_id, code, expires_at.isoformat()),
    )
    db.commit()


def verify_2fa_code(user_id: int, code: str) -> bool:
    """
    Verify a 2FA code. Returns True if valid (unused, not expired).
    Marks the code as used on success.
    """
    from backend.models.db import get_db
    import datetime
    db = get_db()
    row = db.execute(
        """SELECT * FROM two_factor_codes
           WHERE user_id = ? AND code = ? AND used = 0
           AND expires_at > ?""",
        (user_id, code, datetime.datetime.utcnow().isoformat()),
    ).fetchone()
    if row:
        db.execute(
            "UPDATE two_factor_codes SET used = 1 WHERE id = ?", (row["id"],)
        )
        db.commit()
        return True
    return False
