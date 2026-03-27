from __future__ import annotations

import psycopg

from app.core.security import normalize_auth_identity, normalize_auth_phone


def fetch_auth_user_by_identity(
    conn: psycopg.Connection,
    *,
    identity: str,
) -> dict | None:
    normalized_identity = normalize_auth_identity(identity)
    if not normalized_identity:
        return None

    row = conn.execute(
        """
        SELECT *
        FROM auth_users
        WHERE lower(COALESCE(email, '')) = lower(%s)
           OR COALESCE(phone, '') = %s
        LIMIT 1
        """,
        (normalized_identity, normalized_identity),
    ).fetchone()
    if row is not None:
        return dict(row)

    normalized_phone = normalize_auth_phone(normalized_identity)
    if not normalized_phone:
        return None

    rows = conn.execute(
        """
        SELECT *
        FROM auth_users
        WHERE COALESCE(phone, '') <> ''
        """
    ).fetchall()
    for candidate in rows:
        candidate_row = dict(candidate)
        if normalize_auth_phone(str(candidate_row.get("phone") or "")) == normalized_phone:
            return candidate_row
    return None


def cleanup_expired_auth_sessions(conn: psycopg.Connection) -> None:
    conn.execute("DELETE FROM auth_sessions WHERE expires_at <= %s", (build_current_timestamp(),))


def insert_auth_session(
    conn: psycopg.Connection,
    *,
    token: str,
    username: str,
    created_at: str,
    expires_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO auth_sessions (token, username, created_at, expires_at)
        VALUES (%s, %s, %s, %s)
        """,
        (token, username, created_at, expires_at),
    )


def fetch_auth_session(conn: psycopg.Connection, *, token: str) -> dict | None:
    row = conn.execute(
        """
        SELECT token, username, created_at, expires_at
        FROM auth_sessions
        WHERE token = %s
        LIMIT 1
        """,
        (token,),
    ).fetchone()
    return dict(row) if row else None


def delete_auth_session(conn: psycopg.Connection, *, token: str) -> None:
    conn.execute("DELETE FROM auth_sessions WHERE token = %s", (token,))


def update_auth_user_password(
    conn: psycopg.Connection,
    *,
    user_id: int,
    password_hash: str,
) -> None:
    conn.execute(
        """
        UPDATE auth_users
        SET password_hash = %s,
            must_change_password = 0,
            updated_at = NOW()
        WHERE id = %s
        """,
        (password_hash, user_id),
    )


def build_current_timestamp() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat(timespec="seconds")
