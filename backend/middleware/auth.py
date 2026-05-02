"""
Auth middleware — JWT token validation decorator.
ה"שומר סף" של האתר! קובץ זה בודק כל בקשה שמגיעה לשרת 
כדי לוודא שלמתאמן יש "תעודת כניסה" (Token) תקפה.
"""

import os
import jwt
from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_fallback")


def require_auth(f):
    """
    Decorator that validates JWT from Authorization: Bearer <token> header.
    Sets g.user_id, g.role on the Flask request context.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check cookie first (more secure)
        token = request.cookies.get("auth_token")
        
        # Fallback to header
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
        
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            g.user_id    = payload["user_id"]
            g.role       = payload["role"]
            g.user_email = payload.get("email", "")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired. Please log in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        return None

"""
English Summary:
This is a critical security middleware file. It provides the @require_auth decorator, which intercepts 
incoming HTTP requests to verify the presence and validity of a JWT (JSON Web Token) inside the cookies 
or headers. If the token is valid, it decodes it and attaches the user's ID and role to the Flask context, 
granting access. Otherwise, it blocks the request.

סיכום בעברית:
הקובץ הזה משמש כ"שומר סף" קפדני בכניסה לאזורים הפרטיים באתר. לפני שמתאמן יכול לראות את
פרופיל האימונים שלו או את הודעות הקהילה, הקובץ הזה בודק את "תעודת הזהות הדיגיטלית" שלו (JWT).
אם התעודה תקינה, הוא מרשה לו להיכנס. אם לא (או שהתעודה פגה), הוא זורק אותו החוצה בחזרה למסך ההתחברות.
"""
