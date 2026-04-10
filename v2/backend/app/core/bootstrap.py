from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
import logging

import psycopg

from app.core.auth_sync import sync_mobile_auth_users
from app.core.config import settings
from app.core.security import hash_auth_password, normalize_auth_identity, normalize_auth_phone

LOGGER = logging.getLogger(__name__)

BOOTSTRAP_STATE: dict[str, str | bool | None] = {
    "attempted": False,
    "ok": None,
    "detail": "Runtime bootstrap henuz calismadi.",
}

AUTH_BOOTSTRAP_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS auth_users (
        id BIGSERIAL PRIMARY KEY,
        email TEXT,
        phone TEXT,
        full_name TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'viewer',
        role_display TEXT NOT NULL DEFAULT 'Viewer',
        password_hash TEXT NOT NULL DEFAULT '',
        is_active BIGINT NOT NULL DEFAULT 1,
        must_change_password BIGINT NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """,
    "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS phone TEXT",
    "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS role_display TEXT NOT NULL DEFAULT 'Viewer'",
    "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS must_change_password BIGINT NOT NULL DEFAULT 1",
    "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_email_unique
    ON auth_users ((lower(email)))
    WHERE email IS NOT NULL AND email <> ''
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_phone_unique
    ON auth_users (phone)
    WHERE phone IS NOT NULL AND phone <> ''
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions (expires_at)",
    """
    CREATE TABLE IF NOT EXISTS auth_phone_codes (
        id BIGSERIAL PRIMARY KEY,
        auth_user_id BIGINT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
        phone TEXT NOT NULL,
        code_hash TEXT NOT NULL,
        purpose TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        consumed_at TIMESTAMP NULL,
        attempt_count BIGINT NOT NULL DEFAULT 0,
        last_attempt_at TIMESTAMP NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_auth_phone_codes_phone_purpose ON auth_phone_codes (phone, purpose)",
)


def ensure_runtime_bootstrap() -> None:
    BOOTSTRAP_STATE["attempted"] = True

    if not settings.database_url:
        BOOTSTRAP_STATE["ok"] = False
        BOOTSTRAP_STATE["detail"] = "DATABASE_URL eksik oldugu icin runtime bootstrap atlandi."
        return

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=5,
            application_name="catkapinda-crm-v2-bootstrap",
        ) as conn:
            for statement in AUTH_BOOTSTRAP_STATEMENTS:
                conn.execute(statement)
            sync_default_auth_users(conn)
            sync_mobile_auth_users(conn)
            conn.commit()
        BOOTSTRAP_STATE["ok"] = True
        BOOTSTRAP_STATE["detail"] = "Auth runtime bootstrap basarili."
    except Exception as exc:  # pragma: no cover - runtime-only network/db failures
        BOOTSTRAP_STATE["ok"] = False
        BOOTSTRAP_STATE["detail"] = f"Runtime bootstrap basarisiz: {exc}"
        LOGGER.warning("v2 runtime bootstrap failed", exc_info=exc)


def get_runtime_bootstrap_state() -> dict[str, str | bool | None]:
    return dict(BOOTSTRAP_STATE)


def reset_runtime_bootstrap_state() -> None:
    BOOTSTRAP_STATE["attempted"] = False
    BOOTSTRAP_STATE["ok"] = None
    BOOTSTRAP_STATE["detail"] = "Runtime bootstrap henuz calismadi."


def mark_runtime_bootstrap_state(*, ok: bool | None, detail: str) -> None:
    BOOTSTRAP_STATE["attempted"] = True
    BOOTSTRAP_STATE["ok"] = ok
    BOOTSTRAP_STATE["detail"] = detail


def sync_default_auth_users(conn: psycopg.Connection) -> None:
    now_text = datetime.now(UTC).isoformat(timespec="seconds")

    for legacy_identity in settings.legacy_auth_identities:
        conn.execute("DELETE FROM auth_users WHERE lower(email) = lower(%s)", (legacy_identity,))
        conn.execute("DELETE FROM auth_sessions WHERE username = %s", (legacy_identity,))

    for user in settings.default_auth_users:
        normalized_email = normalize_auth_identity(str(user.get("email") or ""))
        normalized_phone = normalize_auth_phone(str(user.get("phone") or ""))
        existing = conn.execute(
            """
            SELECT *
            FROM auth_users
            WHERE lower(COALESCE(email, '')) = lower(%s)
               OR (%s <> '' AND COALESCE(phone, '') = %s)
            LIMIT 1
            """,
            (normalized_email, normalized_phone, normalized_phone),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO auth_users (
                    email, phone, full_name, role, role_display, password_hash,
                    is_active, must_change_password, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s, %s)
                """,
                (
                    normalized_email,
                    normalized_phone,
                    str(user.get("full_name") or "").strip(),
                    str(user.get("role") or "admin").strip(),
                    str(user.get("role_display") or "Yönetici").strip(),
                    hash_auth_password(settings.default_auth_password),
                    now_text,
                    now_text,
                ),
            )
            continue

        existing_row = dict(existing)
        password_hash = str(existing_row.get("password_hash") or "")
        must_change_password = int(existing_row.get("must_change_password") or 0)
        if not password_hash:
            password_hash = hash_auth_password(settings.default_auth_password)
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
                normalized_email,
                normalized_phone,
                str(user.get("full_name") or "").strip(),
                str(user.get("role") or "admin").strip(),
                str(user.get("role_display") or "Yönetici").strip(),
                password_hash,
                must_change_password,
                now_text,
                int(existing_row.get("id") or 0),
            ),
        )


with suppress(Exception):
    logging.getLogger("psycopg").setLevel(logging.WARNING)
