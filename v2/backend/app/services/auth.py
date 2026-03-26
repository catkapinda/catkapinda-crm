from __future__ import annotations

import psycopg

from app.core.security import (
    AuthenticatedUser,
    build_session_token,
    build_session_window,
    normalize_auth_identity,
    resolve_allowed_actions,
    verify_auth_password,
)
from app.repositories.auth import (
    cleanup_expired_auth_sessions,
    delete_auth_session,
    fetch_auth_session,
    fetch_auth_user_by_identity,
    insert_auth_session,
)
from app.schemas.auth import AuthCurrentUserResponse, AuthLoginResponse, AuthModesResponse


def build_auth_modes() -> AuthModesResponse:
    return AuthModesResponse(
        email_login=True,
        phone_login=True,
        sms_login=False,
    )


def authenticate_user(
    conn: psycopg.Connection,
    *,
    identity: str,
    password: str,
) -> AuthenticatedUser:
    user_row = fetch_auth_user_by_identity(conn, identity=identity)
    if not user_row:
        raise ValueError("Giris bilgileri gecersiz.")
    if int(user_row.get("is_active") or 0) != 1:
        raise ValueError("Bu hesap aktif degil.")
    if not verify_auth_password(password, str(user_row.get("password_hash") or "")):
        raise ValueError("Giris bilgileri gecersiz.")

    session_identity = normalize_auth_identity(identity) or str(user_row.get("email") or "")
    token = create_auth_session(conn, username=session_identity)
    return build_authenticated_user(user_row=user_row, token=token)


def create_auth_session(conn: psycopg.Connection, *, username: str) -> str:
    cleanup_expired_auth_sessions(conn)
    token = build_session_token()
    created_at, expires_at = build_session_window()
    insert_auth_session(
        conn,
        token=token,
        username=username,
        created_at=created_at,
        expires_at=expires_at,
    )
    conn.commit()
    return token


def resolve_authenticated_user(
    conn: psycopg.Connection,
    *,
    token: str,
) -> AuthenticatedUser:
    cleanup_expired_auth_sessions(conn)
    session_row = fetch_auth_session(conn, token=token)
    if not session_row:
        raise LookupError("Oturum bulunamadi.")

    user_row = fetch_auth_user_by_identity(conn, identity=str(session_row.get("username") or ""))
    if not user_row or int(user_row.get("is_active") or 0) != 1:
        delete_auth_session(conn, token=token)
        conn.commit()
        raise LookupError("Oturum gecersiz.")

    return build_authenticated_user(
        user_row=user_row,
        token=token,
        expires_at=str(session_row.get("expires_at") or ""),
    )


def revoke_authenticated_session(conn: psycopg.Connection, *, token: str) -> None:
    delete_auth_session(conn, token=token)
    conn.commit()


def build_authenticated_user(
    *,
    user_row: dict,
    token: str,
    expires_at: str | None = None,
) -> AuthenticatedUser:
    allowed_actions = resolve_allowed_actions(str(user_row.get("role") or ""))
    identity = normalize_auth_identity(str(user_row.get("email") or "")) or normalize_auth_identity(
        str(user_row.get("phone") or "")
    )
    return AuthenticatedUser(
        id=int(user_row.get("id") or 0),
        identity=identity,
        email=str(user_row.get("email") or ""),
        phone=str(user_row.get("phone") or ""),
        full_name=str(user_row.get("full_name") or ""),
        role=str(user_row.get("role") or ""),
        role_display=str(user_row.get("role_display") or str(user_row.get("role") or "")),
        must_change_password=bool(int(user_row.get("must_change_password") or 0)),
        allowed_actions=allowed_actions,
        expires_at=expires_at or build_session_window()[1],
        token=token,
    )


def serialize_authenticated_user(user: AuthenticatedUser) -> AuthCurrentUserResponse:
    return AuthCurrentUserResponse(
        id=user.id,
        identity=user.identity,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        role_display=user.role_display,
        must_change_password=user.must_change_password,
        allowed_actions=user.allowed_actions,
        expires_at=user.expires_at,
    )


def build_login_response(user: AuthenticatedUser) -> AuthLoginResponse:
    return AuthLoginResponse(
        access_token=user.token,
        token_type="bearer",
        expires_at=user.expires_at,
        user=serialize_authenticated_user(user),
    )
