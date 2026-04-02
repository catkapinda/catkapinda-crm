from __future__ import annotations

from datetime import UTC, datetime

import psycopg

from app.core.config import settings
from app.core.security import (
    build_mobile_auth_email,
    hash_auth_password,
    normalize_auth_identity,
    normalize_auth_phone,
)

MOBILE_AUTH_PERSONNEL_ROLES = {"Joker", "Bölge Müdürü"}
MOBILE_AUTH_ROLE = "mobile_ops"
MOBILE_AUTH_ROLE_DISPLAY = "Mobil Operasyon"
DEFAULT_MOBILE_AUTH_PASSWORD = ""


def sync_mobile_auth_user_for_personnel(
    conn: psycopg.Connection,
    *,
    personnel_id: int,
    fallback_row: dict | None = None,
) -> None:
    personnel_row = fallback_row or _fetch_personnel_auth_row(conn, personnel_id=personnel_id)
    normalized_phone = normalize_auth_phone(str((personnel_row or {}).get("phone") or ""))
    placeholder_email = build_mobile_auth_email(personnel_id)
    existing_user = _fetch_existing_mobile_auth_user(
        conn,
        placeholder_email=placeholder_email,
        normalized_phone=normalized_phone,
    )

    if not _is_mobile_auth_eligible(personnel_row, normalized_phone=normalized_phone):
        _deactivate_mobile_auth_user(
            conn,
            auth_user=existing_user,
            placeholder_email=placeholder_email,
            normalized_phone=normalized_phone,
        )
        return

    _upsert_mobile_auth_user(
        conn,
        auth_user=existing_user,
        placeholder_email=placeholder_email,
        normalized_phone=normalized_phone,
        full_name=str(personnel_row.get("full_name") or "").strip(),
    )


def _fetch_personnel_auth_row(
    conn: psycopg.Connection,
    *,
    personnel_id: int,
) -> dict | None:
    row = conn.execute(
        """
        SELECT id, full_name, role, status, phone
        FROM personnel
        WHERE id = %s
        LIMIT 1
        """,
        (personnel_id,),
    ).fetchone()
    return dict(row) if row else None


def _fetch_existing_mobile_auth_user(
    conn: psycopg.Connection,
    *,
    placeholder_email: str,
    normalized_phone: str,
) -> dict | None:
    row = conn.execute(
        """
        SELECT *
        FROM auth_users
        WHERE lower(COALESCE(email, '')) = lower(%s)
        LIMIT 1
        """,
        (placeholder_email,),
    ).fetchone()
    if row:
        return dict(row)

    if not normalized_phone:
        return None

    row = conn.execute(
        """
        SELECT *
        FROM auth_users
        WHERE role = %s
          AND phone = %s
        LIMIT 1
        """,
        (MOBILE_AUTH_ROLE, normalized_phone),
    ).fetchone()
    return dict(row) if row else None


def _is_mobile_auth_eligible(personnel_row: dict | None, *, normalized_phone: str) -> bool:
    if not personnel_row or not normalized_phone:
        return False
    return (
        str(personnel_row.get("status") or "").strip() == "Aktif"
        and str(personnel_row.get("role") or "").strip() in MOBILE_AUTH_PERSONNEL_ROLES
    )


def _upsert_mobile_auth_user(
    conn: psycopg.Connection,
    *,
    auth_user: dict | None,
    placeholder_email: str,
    normalized_phone: str,
    full_name: str,
) -> None:
    now_text = datetime.now(UTC).isoformat(timespec="seconds")
    if auth_user is None:
        conn.execute(
            """
            INSERT INTO auth_users (
                email,
                phone,
                full_name,
                role,
                role_display,
                password_hash,
                is_active,
                must_change_password,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s, %s)
            """,
            (
                placeholder_email,
                normalized_phone,
                full_name,
                MOBILE_AUTH_ROLE,
                MOBILE_AUTH_ROLE_DISPLAY,
                hash_auth_password(settings.default_auth_password or DEFAULT_MOBILE_AUTH_PASSWORD),
                now_text,
                now_text,
            ),
        )
        return

    auth_user_id = int(auth_user.get("id") or 0)
    old_email = str(auth_user.get("email") or "")
    old_phone = normalize_auth_phone(str(auth_user.get("phone") or ""))
    password_hash = str(auth_user.get("password_hash") or "")
    must_change_password = int(auth_user.get("must_change_password") or 0)
    if not password_hash:
        password_hash = hash_auth_password(settings.default_auth_password or DEFAULT_MOBILE_AUTH_PASSWORD)
        must_change_password = 1

    conn.execute(
        """
        UPDATE auth_users
        SET email = %s,
            phone = %s,
            full_name = %s,
            role = %s,
            role_display = %s,
            password_hash = %s,
            is_active = 1,
            must_change_password = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            placeholder_email,
            normalized_phone,
            full_name,
            MOBILE_AUTH_ROLE,
            MOBILE_AUTH_ROLE_DISPLAY,
            password_hash,
            must_change_password,
            now_text,
            auth_user_id,
        ),
    )
    _clear_auth_runtime_state(
        conn,
        auth_user_id=auth_user_id,
        identities={old_email, old_phone, placeholder_email, normalized_phone},
    )


def _deactivate_mobile_auth_user(
    conn: psycopg.Connection,
    *,
    auth_user: dict | None,
    placeholder_email: str,
    normalized_phone: str,
) -> None:
    if auth_user is None:
        return

    auth_user_id = int(auth_user.get("id") or 0)
    old_email = str(auth_user.get("email") or "")
    old_phone = normalize_auth_phone(str(auth_user.get("phone") or ""))
    now_text = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE auth_users
        SET is_active = 0, updated_at = %s
        WHERE id = %s
        """,
        (now_text, auth_user_id),
    )
    _clear_auth_runtime_state(
        conn,
        auth_user_id=auth_user_id,
        identities={old_email, old_phone, placeholder_email, normalized_phone},
    )


def _clear_auth_runtime_state(
    conn: psycopg.Connection,
    *,
    auth_user_id: int,
    identities: set[str],
) -> None:
    for identity in sorted(
        normalize_auth_identity(value) for value in identities if normalize_auth_identity(value)
    ):
        conn.execute("DELETE FROM auth_sessions WHERE username = %s", (identity,))
    conn.execute("DELETE FROM auth_phone_codes WHERE auth_user_id = %s", (auth_user_id,))
