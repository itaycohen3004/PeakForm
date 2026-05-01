"""
Encryption Service — Row-level encryption for sensitive database fields.
Uses Fernet symmetric encryption.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv('config.env')

# We derive the encryption key from SECRET_KEY to ensure persistence
SECRET_KEY = os.getenv("SECRET_KEY", "peakform_dev_secret_must_be_long")

def _get_fernet():
    """Derive a consistent 32-byte key from the SECRET_KEY."""
    salt = b'peakform_stable_salt' # In production, this should be unique per deployment
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY.encode()))
    return Fernet(key)

_cipher = _get_fernet()

def encrypt_data(data: str) -> str:
    """Encrypt a string and return a URL-safe base64 string."""
    if not data: return data
    if not isinstance(data, str): data = str(data)
    return _cipher.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    """Decrypt a token and return the original string."""
    if not token: return token
    try:
        return _cipher.decrypt(token.encode()).decode()
    except Exception:
        # Fallback for unencrypted data during migration or errors
        return token

def blind_index(data: str) -> str:
    """Generate a stable SHA256 hash of data for indexing/searching."""
    if not data: return data
    import hashlib
    salt = b'peakform_blind_index_salt'
    return hashlib.sha256(salt + data.lower().strip().encode()).hexdigest()
