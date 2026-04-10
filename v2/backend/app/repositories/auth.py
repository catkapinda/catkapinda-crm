from __future__ import annotations

from datetime import datetime, timedelta

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
    return datetime.utcnow().isoformat(timespec="seconds")


def delete_pending_phone_codes(
    conn: psycopg.Connection,
    *,
    auth_user_id: int,
    purpose: str,
) -> None:
    conn.execute(
        """
        DELETE FROM auth_phone_codes
        WHERE auth_user_id = %s
          AND purpose = %s
          AND consumed_at IS NULL
        """,
        (auth_user_id, purpose),
    )


def cleanup_expired_phone_codes(conn: psycopg.Connection) -> None:
    now_text = build_current_timestamp()
    stale_consumed_before = (datetime.utcnow() - timedelta(days=1)).isoformat(timespec="seconds")
    conn.execute(
        """
        DELETE FROM auth_phone_codes
        WHERE expires_at <= %s
           OR (consumed_at IS NOT NULL AND consumed_at <= %s)
        """,
        (now_text, stale_consumed_before),
    )


def insert_phone_code(
    conn: psycopg.Connection,
    *,
    auth_user_id: int,
    phone: str,
    code_hash: str,
    purpose: str,
    created_at: str,
    expires_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO auth_phone_codes (
            auth_user_id, phone, code_hash, purpose, created_at, expires_at, consumed_at, attempt_count, last_attempt_at
        ) VALUES (%s, %s, %s, %s, %s, %s, NULL, 0, NULL)
        """,
        (auth_user_id, phone, code_hash, purpose, created_at, expires_at),
    )


def fetch_active_phone_code(
    conn: psycopg.Connection,
    *,
    phone: str,
    purpose: str,
    now_text: str,
) -> dict | None:
    row = conn.execute(
        """
        SELECT
            c.id AS code_row_id,
            c.auth_user_id AS code_auth_user_id,
            c.code_hash AS code_hash,
            c.attempt_count AS code_attempt_count,
            u.*
        FROM auth_phone_codes c
        JOIN auth_users u ON u.id = c.auth_user_id
        WHERE c.phone = %s
          AND c.purpose = %s
          AND c.consumed_at IS NULL
          AND c.expires_at > %s
        ORDER BY c.created_at DESC, c.id DESC
        LIMIT 1
        """,
        (phone, purpose, now_text),
    ).fetchone()
    return dict(row) if row else None


def increment_phone_code_attempt(
    conn: psycopg.Connection,
    *,
    code_row_id: int,
    attempt_count: int,
    attempted_at: str,
) -> None:
    conn.execute(
        """
        UPDATE auth_phone_codes
        SET attempt_count = %s, last_attempt_at = %s
        WHERE id = %s
        """,
        (attempt_count, attempted_at, code_row_id),
    )


def consume_phone_code(
    conn: psycopg.Connection,
    *,
    code_row_id: int,
    attempt_count: int,
    consumed_at: str,
) -> None:
    conn.execute(
        """
        UPDATE auth_phone_codes
        SET consumed_at = %s, last_attempt_at = %s, attempt_count = %s
        WHERE id = %s
        """,
        (consumed_at, consumed_at, attempt_count, code_row_id),
    )


def fetch_personnel_role_status(
    conn: psycopg.Connection,
    *,
    personnel_id: int,
) -> dict | None:
    row = conn.execute(
        """
        SELECT role, status
        FROM personnel
        WHERE id = %s
        LIMIT 1
        """,
        (personnel_id,),
    ).fetchone()
    return dict(row) if row else None
