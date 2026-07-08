"""
מודול אימות מרכזי — JWT creation, verification, ו-middleware דקורטורים.
"""

import os
import functools
import secrets
from datetime import datetime, timedelta

import jwt
from flask import request, jsonify

# ── הגדרות ──────────────────────────────────────────────
SECRET_KEY = os.environ.get("JWT_SECRET", "smart-stock-dev-secret-key-2024!")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# CSRF token lives as a claim inside the JWT — the client reads it
# from the JWT payload and sends it back via X-CSRF-Token header
# on every state-changing request (POST / PUT / DELETE).
# An attacker cannot read the JWT payload, so they cannot guess the CSRF token.


def create_access_token(user_id: int) -> str:
    """יוצר Access Token עם תוקף קצר (30 דקות) + CSRF claim."""
    payload = {
        "sub": str(user_id),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
        "csrf": secrets.token_hex(32),  # 64-char random CSRF token
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    """יוצר Refresh Token עם תוקף ארוך (7 ימים)."""
    payload = {
        "sub": str(user_id),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """מפענח ומאמת Token. מחזיר את ה-payload או זורק שגיאה."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def login_required(f):
    """דקורטור: חוסם גישה ל-endpoint ללא Access Token תקף.
    מחדיר את user_id לתוך הפונקציה כפרמטר keyword.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[7:]  # skip "Bearer "

        try:
            payload = decode_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        if payload.get("type") != "access":
            return jsonify({"error": "Invalid token type"}), 401

        # מחדיר את user_id ל-kwargs (ממיר חזרה ל-int)
        kwargs["user_id"] = int(payload["sub"])
        return f(*args, **kwargs)

    return decorated


# ═══════════════════════════════════════════════════════════
# RBAC — Role-Based Access Control
# ═══════════════════════════════════════════════════════════

def get_user_permissions(user_id, session):
    """מחזיר set של כל ה-permissions של משתמש (דרך ה-roles שלו).
    משתמש ב-session פעיל (לא יוצר אחד משלו).
    """
    from models.users import User

    user = session.query(User).filter(User.id == user_id).first()
    if not user or not user.roles:
        return set()

    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.name)
    return perms


def require_permission(permission_name):
    """דקורטור: דורש permission ספציפי (דרך RBAC).
    יש להשתמש מעל @login_required.
    """

    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_id = kwargs.get("user_id")
            if not user_id:
                return jsonify({"error": "login_required must be applied first"}), 500

            # צור session לייבוא המודלים
            from db_connection import SessionLocal
            session = SessionLocal()
            try:
                perms = get_user_permissions(user_id, session)
            finally:
                session.close()

            if permission_name not in perms:
                return jsonify({"error": f"Permission denied: '{permission_name}' required"}), 403

            return f(*args, **kwargs)

        return decorated

    return decorator


def require_role(role_name):
    """דקורטור: דורש Role ספציפי.
    פשוט יותר מ-require_permission — בודק שם Role ישירות.
    """

    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_id = kwargs.get("user_id")
            if not user_id:
                return jsonify({"error": "login_required must be applied first"}), 500

            from db_connection import SessionLocal
            from models.users import User

            session = SessionLocal()
            try:
                user = session.query(User).filter(User.id == user_id).first()
                role_names = {r.name for r in (user.roles or [])}
            finally:
                session.close()

            if role_name not in role_names:
                return jsonify({"error": f"Permission denied: '{role_name}' role required"}), 403

            return f(*args, **kwargs)

        return decorated

    return decorator


# ═══════════════════════════════════════════════════════════
# CSRF Protection
# ═══════════════════════════════════════════════════════════

def csrf_required(f):
    """דקורטור: דורש X-CSRF-Token תואם ל-csrf claim מה-JWT.
    יש להשתמש מעל @login_required.

    איך זה עובד:
    1. JWT מכיל csrf claim (64 תווים רנדומליים)
    2. ה-frontend שולח X-CSRF-Token header עם אותו ערך
    3. תוקף מצד שלישי לא יכול לקרוא את ה-JWT -> לא יודע את ה-csrf
    4. אנחנו משווים - חייבים להיות זהים
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

        if not token:
            return jsonify({"error": "Missing Authorization header"}), 401

        try:
            payload = decode_token(token)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        expected_csrf = payload.get("csrf", "")
        if not expected_csrf:
            return jsonify({"error": "CSRF claim missing from token"}), 400

        client_csrf = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(expected_csrf, client_csrf):
            return jsonify({"error": "CSRF token mismatch"}), 403

        return f(*args, **kwargs)

    return decorated
