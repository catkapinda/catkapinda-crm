"""Authentication helpers — bcrypt hash + JWT token.

Token akışı:
- POST /api/auth/login (email, password) → access_token (HS256, 7 gün)
- Frontend Authorization: Bearer <token> header'ı ile her istek
- get_current_user dependency JWT'yi açar, users tablosundan kullanıcıyı döner
- Şifre sıfırlama: tek kullanımlık reset_token (24 saat geçerli)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.database import get_connection


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ─── Hash & verify ──────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """bcrypt hash — saltsız ham parolayı 60 karakterlik hash'e çevirir."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


# ─── JWT ────────────────────────────────────────────────────────────


JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7


def _jwt_secret() -> str:
    settings = get_settings()
    # JWT_SECRET env'de yoksa SECRET_KEY veya APP_NAME'den türet (deterministik
    # ama production'da JWT_SECRET ayarlamak ZORUNLU — yoksa rastgele)
    return (
        getattr(settings, "jwt_secret", None)
        or getattr(settings, "secret_key", None)
        or "catkapinda-jwt-secret-CHANGE-ME-IN-PROD"
    )


def create_access_token(user_id: int, email: str) -> str:
    """Yeni access token üret — 7 gün geçerli."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# ─── Reset token (parola sıfırlama) ────────────────────────────────


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)


# ─── User CRUD ──────────────────────────────────────────────────────


def get_user_by_email(email: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, email, full_name, password_hash, role, status,
                       reset_token, reset_token_expires_at
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, email, full_name, role, status, last_login_at
                FROM users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_last_login(user_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login_at = now() WHERE id = %s",
                (user_id,),
            )
            conn.commit()


def set_reset_token(user_id: int) -> str:
    token = generate_reset_token()
    expires = reset_token_expiry()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET reset_token = %s, reset_token_expires_at = %s
                WHERE id = %s
                """,
                (token, expires, user_id),
            )
            conn.commit()
    return token


def use_reset_token(token: str, new_password: str) -> bool:
    """Reset token doğrula → parola güncelle, token'ı temizle."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id FROM users
                WHERE reset_token = %s
                  AND reset_token_expires_at > now()
                  AND status = 'active'
                LIMIT 1
                """,
                (token,),
            )
            row = cur.fetchone()
            if not row:
                return False
            cur.execute(
                """
                UPDATE users
                SET password_hash = %s,
                    reset_token = NULL,
                    reset_token_expires_at = NULL
                WHERE id = %s
                """,
                (hash_password(new_password), row["id"]),
            )
            conn.commit()
            return True


def change_password(user_id: int, new_password: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hash_password(new_password), user_id),
            )
            conn.commit()


# ─── FastAPI dependency ────────────────────────────────────────────


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    """Bearer JWT'yi açar, users satırını döner. Yoksa 401."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum açın",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
        )
    user = get_user_by_id(int(payload["sub"]))
    if not user or user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya pasif",
        )
    return user
