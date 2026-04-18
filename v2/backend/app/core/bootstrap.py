from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
import logging

import psycopg
from psycopg.rows import dict_row

from app.core.auth_sync import sync_mobile_auth_users
from app.core.config import settings
from app.core.database import connect_local_sqlite_fallback, local_sqlite_fallback_available
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
    """
    CREATE TABLE IF NOT EXISTS auth_login_attempts (
        identity TEXT PRIMARY KEY,
        failed_count BIGINT NOT NULL DEFAULT 0,
        first_failed_at TIMESTAMP NOT NULL,
        last_failed_at TIMESTAMP NOT NULL,
        blocked_until TIMESTAMP NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        actor_username TEXT,
        actor_full_name TEXT,
        actor_role TEXT,
        entity_type TEXT,
        entity_id TEXT,
        action_type TEXT,
        summary TEXT,
        details_json TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at)",
    """
    CREATE TABLE IF NOT EXISTS personnel_role_history (
        id BIGSERIAL PRIMARY KEY,
        personnel_id BIGINT NOT NULL,
        role TEXT,
        cost_model TEXT,
        monthly_fixed_cost NUMERIC NOT NULL DEFAULT 0,
        effective_date DATE,
        changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
        notes TEXT
    )
    """,
    "ALTER TABLE personnel_role_history ADD COLUMN IF NOT EXISTS cost_model TEXT",
    "ALTER TABLE personnel_role_history ADD COLUMN IF NOT EXISTS monthly_fixed_cost NUMERIC NOT NULL DEFAULT 0",
    "ALTER TABLE personnel_role_history ADD COLUMN IF NOT EXISTS effective_date DATE",
    "ALTER TABLE personnel_role_history ADD COLUMN IF NOT EXISTS changed_at TIMESTAMP NOT NULL DEFAULT NOW()",
    """
    CREATE TABLE IF NOT EXISTS personnel_vehicle_history (
        id BIGSERIAL PRIMARY KEY,
        personnel_id BIGINT NOT NULL,
        vehicle_type TEXT,
        motor_rental TEXT,
        motor_rental_monthly_amount NUMERIC NOT NULL DEFAULT 13000,
        motor_purchase TEXT,
        motor_purchase_start_date DATE,
        motor_purchase_commitment_months BIGINT,
        motor_purchase_sale_price NUMERIC NOT NULL DEFAULT 0,
        motor_purchase_monthly_deduction NUMERIC NOT NULL DEFAULT 0,
        effective_date DATE,
        changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
        notes TEXT
    )
    """,
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_rental TEXT",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_rental_monthly_amount NUMERIC NOT NULL DEFAULT 13000",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_purchase TEXT",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_purchase_start_date DATE",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_purchase_commitment_months BIGINT",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_purchase_sale_price NUMERIC NOT NULL DEFAULT 0",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS motor_purchase_monthly_deduction NUMERIC NOT NULL DEFAULT 0",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS effective_date DATE",
    "ALTER TABLE personnel_vehicle_history ADD COLUMN IF NOT EXISTS changed_at TIMESTAMP NOT NULL DEFAULT NOW()",
    """
    CREATE TABLE IF NOT EXISTS plate_history (
        id BIGSERIAL PRIMARY KEY,
        personnel_id BIGINT NOT NULL,
        plate TEXT NOT NULL DEFAULT '',
        start_date DATE NOT NULL,
        end_date DATE NULL,
        reason TEXT,
        active BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS motor_rental_monthly_amount NUMERIC NOT NULL DEFAULT 13000",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS motor_purchase TEXT DEFAULT 'Hayır'",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS motor_purchase_start_date DATE",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS motor_purchase_commitment_months BIGINT",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS motor_purchase_sale_price NUMERIC NOT NULL DEFAULT 0",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS motor_purchase_monthly_deduction NUMERIC NOT NULL DEFAULT 0",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS address TEXT",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS iban TEXT",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS tax_number TEXT",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS tax_office TEXT",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS emergency_contact_name TEXT",
    "ALTER TABLE personnel ADD COLUMN IF NOT EXISTS emergency_contact_phone TEXT",
    """
    CREATE TABLE IF NOT EXISTS sales_leads (
        id BIGSERIAL PRIMARY KEY,
        restaurant_name TEXT NOT NULL DEFAULT '',
        city TEXT NOT NULL DEFAULT '',
        district TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        contact_name TEXT NOT NULL DEFAULT '',
        contact_phone TEXT NOT NULL DEFAULT '',
        contact_email TEXT NOT NULL DEFAULT '',
        requested_courier_count BIGINT NOT NULL DEFAULT 0,
        lead_source TEXT NOT NULL DEFAULT '',
        proposed_quote NUMERIC NOT NULL DEFAULT 0,
        pricing_model TEXT NOT NULL DEFAULT '',
        hourly_rate NUMERIC NOT NULL DEFAULT 0,
        package_rate NUMERIC NOT NULL DEFAULT 0,
        package_threshold BIGINT NOT NULL DEFAULT 0,
        package_rate_low NUMERIC NOT NULL DEFAULT 0,
        package_rate_high NUMERIC NOT NULL DEFAULT 0,
        fixed_monthly_fee NUMERIC NOT NULL DEFAULT 0,
        pricing_model_hint TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Yeni Talep',
        next_follow_up_date DATE NULL,
        assigned_owner TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sales_leads_updated_at ON sales_leads (updated_at)",
)

AUTH_BOOTSTRAP_SQLITE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        phone TEXT,
        full_name TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'viewer',
        role_display TEXT NOT NULL DEFAULT 'Viewer',
        password_hash TEXT NOT NULL DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 1,
        must_change_password INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_email_unique
    ON auth_users (email)
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
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions (expires_at)",
    """
    CREATE TABLE IF NOT EXISTS auth_phone_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auth_user_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        code_hash TEXT NOT NULL,
        purpose TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT NULL,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        last_attempt_at TEXT NULL,
        FOREIGN KEY (auth_user_id) REFERENCES auth_users(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_auth_phone_codes_phone_purpose ON auth_phone_codes (phone, purpose)",
    """
    CREATE TABLE IF NOT EXISTS auth_login_attempts (
        identity TEXT PRIMARY KEY,
        failed_count INTEGER NOT NULL DEFAULT 0,
        first_failed_at TEXT NOT NULL,
        last_failed_at TEXT NOT NULL,
        blocked_until TEXT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        actor_username TEXT,
        actor_full_name TEXT,
        actor_role TEXT,
        entity_type TEXT,
        entity_id TEXT,
        action_type TEXT,
        summary TEXT,
        details_json TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at)",
    """
    CREATE TABLE IF NOT EXISTS personnel_role_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        role TEXT,
        cost_model TEXT,
        monthly_fixed_cost REAL NOT NULL DEFAULT 0,
        effective_date TEXT,
        changed_at TEXT NOT NULL,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS personnel_vehicle_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        vehicle_type TEXT,
        motor_rental TEXT,
        motor_rental_monthly_amount REAL NOT NULL DEFAULT 13000,
        motor_purchase TEXT,
        motor_purchase_start_date TEXT,
        motor_purchase_commitment_months INTEGER,
        motor_purchase_sale_price REAL NOT NULL DEFAULT 0,
        motor_purchase_monthly_deduction REAL NOT NULL DEFAULT 0,
        effective_date TEXT,
        changed_at TEXT NOT NULL,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plate_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        plate TEXT NOT NULL DEFAULT '',
        start_date TEXT NOT NULL,
        end_date TEXT,
        reason TEXT,
        active INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sales_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_name TEXT NOT NULL DEFAULT '',
        city TEXT NOT NULL DEFAULT '',
        district TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        contact_name TEXT NOT NULL DEFAULT '',
        contact_phone TEXT NOT NULL DEFAULT '',
        contact_email TEXT NOT NULL DEFAULT '',
        requested_courier_count INTEGER NOT NULL DEFAULT 0,
        lead_source TEXT NOT NULL DEFAULT '',
        proposed_quote REAL NOT NULL DEFAULT 0,
        pricing_model TEXT NOT NULL DEFAULT '',
        hourly_rate REAL NOT NULL DEFAULT 0,
        package_rate REAL NOT NULL DEFAULT 0,
        package_threshold INTEGER NOT NULL DEFAULT 0,
        package_rate_low REAL NOT NULL DEFAULT 0,
        package_rate_high REAL NOT NULL DEFAULT 0,
        fixed_monthly_fee REAL NOT NULL DEFAULT 0,
        pricing_model_hint TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Yeni Talep',
        next_follow_up_date TEXT NULL,
        assigned_owner TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sales_leads_updated_at ON sales_leads (updated_at)",
)

LOCAL_SQLITE_DOMAIN_ALTERATIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "daily_entries": (
        ("monthly_invoice_amount", "ALTER TABLE daily_entries ADD COLUMN monthly_invoice_amount REAL DEFAULT 0"),
        ("absence_reason", "ALTER TABLE daily_entries ADD COLUMN absence_reason TEXT"),
        ("coverage_type", "ALTER TABLE daily_entries ADD COLUMN coverage_type TEXT"),
    ),
    "personnel": (
        ("address", "ALTER TABLE personnel ADD COLUMN address TEXT"),
        ("iban", "ALTER TABLE personnel ADD COLUMN iban TEXT"),
        ("tax_number", "ALTER TABLE personnel ADD COLUMN tax_number TEXT"),
        ("tax_office", "ALTER TABLE personnel ADD COLUMN tax_office TEXT"),
        ("emergency_contact_name", "ALTER TABLE personnel ADD COLUMN emergency_contact_name TEXT"),
        ("emergency_contact_phone", "ALTER TABLE personnel ADD COLUMN emergency_contact_phone TEXT"),
        ("motor_rental_monthly_amount", "ALTER TABLE personnel ADD COLUMN motor_rental_monthly_amount REAL DEFAULT 13000"),
        ("motor_purchase", "ALTER TABLE personnel ADD COLUMN motor_purchase TEXT DEFAULT 'Hayır'"),
        ("motor_purchase_start_date", "ALTER TABLE personnel ADD COLUMN motor_purchase_start_date TEXT"),
        ("motor_purchase_commitment_months", "ALTER TABLE personnel ADD COLUMN motor_purchase_commitment_months INTEGER"),
        ("motor_purchase_sale_price", "ALTER TABLE personnel ADD COLUMN motor_purchase_sale_price REAL DEFAULT 0"),
        ("motor_purchase_monthly_deduction", "ALTER TABLE personnel ADD COLUMN motor_purchase_monthly_deduction REAL DEFAULT 0"),
        ("sgk_job_code", "ALTER TABLE personnel ADD COLUMN sgk_job_code TEXT"),
    ),
    "restaurants": (
        ("company_title", "ALTER TABLE restaurants ADD COLUMN company_title TEXT"),
        ("address", "ALTER TABLE restaurants ADD COLUMN address TEXT"),
    ),
    "deductions": (
        ("auto_source_key", "ALTER TABLE deductions ADD COLUMN auto_source_key TEXT"),
    ),
    "courier_equipment_issues": (
        ("vat_rate", "ALTER TABLE courier_equipment_issues ADD COLUMN vat_rate REAL DEFAULT 20"),
        ("auto_source_key", "ALTER TABLE courier_equipment_issues ADD COLUMN auto_source_key TEXT"),
    ),
    "personnel_role_history": (
        ("cost_model", "ALTER TABLE personnel_role_history ADD COLUMN cost_model TEXT"),
        ("monthly_fixed_cost", "ALTER TABLE personnel_role_history ADD COLUMN monthly_fixed_cost REAL DEFAULT 0"),
        ("effective_date", "ALTER TABLE personnel_role_history ADD COLUMN effective_date TEXT"),
        ("changed_at", "ALTER TABLE personnel_role_history ADD COLUMN changed_at TEXT"),
    ),
    "personnel_vehicle_history": (
        ("motor_rental", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_rental TEXT"),
        ("motor_rental_monthly_amount", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_rental_monthly_amount REAL DEFAULT 13000"),
        ("motor_purchase", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase TEXT"),
        ("motor_purchase_start_date", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_start_date TEXT"),
        ("motor_purchase_commitment_months", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_commitment_months INTEGER"),
        ("motor_purchase_sale_price", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_sale_price REAL DEFAULT 0"),
        ("motor_purchase_monthly_deduction", "ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_monthly_deduction REAL DEFAULT 0"),
        ("effective_date", "ALTER TABLE personnel_vehicle_history ADD COLUMN effective_date TEXT"),
        ("changed_at", "ALTER TABLE personnel_vehicle_history ADD COLUMN changed_at TEXT"),
    ),
}


def _sqlite_table_columns(conn: psycopg.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _run_local_sqlite_domain_bootstrap(conn: psycopg.Connection) -> None:
    for table_name, alterations in LOCAL_SQLITE_DOMAIN_ALTERATIONS.items():
        existing_columns = _sqlite_table_columns(conn, table_name)
        if not existing_columns:
            continue
        for column_name, sql in alterations:
            if column_name not in existing_columns:
                conn.execute(sql)


def _run_auth_bootstrap(conn: psycopg.Connection, *, allow_mobile_sync: bool) -> None:
    statements = AUTH_BOOTSTRAP_STATEMENTS if getattr(conn, "backend", "postgres") == "postgres" else AUTH_BOOTSTRAP_SQLITE_STATEMENTS
    for statement in statements:
        conn.execute(statement)
    if getattr(conn, "backend", "postgres") == "sqlite":
        _run_local_sqlite_domain_bootstrap(conn)
    sync_default_auth_users(conn)
    if allow_mobile_sync:
        sync_mobile_auth_users(conn)
    conn.commit()


def ensure_runtime_bootstrap() -> None:
    BOOTSTRAP_STATE["attempted"] = True

    if not settings.database_url and not local_sqlite_fallback_available():
        BOOTSTRAP_STATE["ok"] = False
        BOOTSTRAP_STATE["detail"] = "DATABASE_URL eksik oldugu icin runtime bootstrap atlandi."
        return

    try:
        if settings.database_url:
            with psycopg.connect(
                settings.database_url,
                connect_timeout=5,
                application_name="catkapinda-crm-v2-bootstrap",
                row_factory=dict_row,
            ) as conn:
                _run_auth_bootstrap(conn, allow_mobile_sync=True)
        else:
            conn = connect_local_sqlite_fallback()
            try:
                _run_auth_bootstrap(conn, allow_mobile_sync=False)
            finally:
                conn.close()
        BOOTSTRAP_STATE["ok"] = True
        BOOTSTRAP_STATE["detail"] = (
            "Auth runtime bootstrap basarili."
            if settings.database_url
            else "Auth runtime bootstrap basarili (local sqlite fallback)."
        )
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
