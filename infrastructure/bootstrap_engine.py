from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from infrastructure.migrations import MigrationStep, get_latest_migration_version, get_pending_migrations


_FIRST_ROW_VALUE: Callable[[Any, Any], Any] | None = None
_LEGACY_DB_PATHS: list[Path] = []
_DB_PATH: Path | None = None
_TABLE_EXPORT_ORDER: list[str] = []
_FIXED_COST_MODEL_BY_ROLE: dict[str, str] = {}
_AUTO_MOTOR_RENTAL_DEDUCTION = 13000.0
_AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION = 11250.0
_AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = 12
_RUNTIME_BOOTSTRAP_VERSION = ""

_NORMALIZE_EXISTING_DEDUCTION_DATES: Callable[[Any], None] | None = None
_NORMALIZE_EQUIPMENT_ISSUE_COSTS_AND_VAT: Callable[[Any], None] | None = None
_CLEANUP_AUTO_ONBOARDING_RECORDS: Callable[[Any], None] | None = None
_CLEANUP_AUTO_PERSONNEL_DEDUCTION_RECORDS: Callable[[Any], None] | None = None
_ENSURE_ALL_PERSON_ROLE_HISTORIES: Callable[[Any], None] | None = None
_ENSURE_ALL_PERSON_VEHICLE_HISTORIES: Callable[[Any], None] | None = None
_SYNC_ALL_PERSONNEL_BUSINESS_RULES: Callable[[Any], None] | None = None
_SYNC_DEFAULT_AUTH_USERS: Callable[[Any], None] | None = None
_CLEANUP_AUTH_SESSIONS: Callable[[Any], None] | None = None


_SQLITE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        branch TEXT NOT NULL,
        billing_group TEXT,
        pricing_model TEXT NOT NULL,
        hourly_rate REAL DEFAULT 0,
        package_rate REAL DEFAULT 0,
        package_threshold INTEGER,
        package_rate_low REAL DEFAULT 0,
        package_rate_high REAL DEFAULT 0,
        fixed_monthly_fee REAL DEFAULT 0,
        vat_rate REAL DEFAULT 20,
        target_headcount INTEGER DEFAULT 0,
        start_date TEXT,
        end_date TEXT,
        extra_headcount_request INTEGER DEFAULT 0,
        extra_headcount_request_date TEXT,
        reduce_headcount_request INTEGER DEFAULT 0,
        reduce_headcount_request_date TEXT,
        contact_name TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        company_title TEXT,
        address TEXT,
        tax_office TEXT,
        tax_number TEXT,
        active INTEGER DEFAULT 1,
        notes TEXT,
        UNIQUE(brand, branch)
    );

    CREATE TABLE IF NOT EXISTS personnel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_code TEXT,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Aktif',
        phone TEXT,
        address TEXT,
        tc_no TEXT,
        iban TEXT,
        emergency_contact_name TEXT,
        emergency_contact_phone TEXT,
        accounting_type TEXT DEFAULT 'Kendi Muhasebecisi',
        new_company_setup TEXT DEFAULT 'Hayır',
        accounting_revenue REAL DEFAULT 0,
        accountant_cost REAL DEFAULT 0,
        company_setup_revenue REAL DEFAULT 0,
        company_setup_cost REAL DEFAULT 0,
        assigned_restaurant_id INTEGER,
        vehicle_type TEXT,
        motor_rental TEXT DEFAULT 'Hayır',
        motor_rental_monthly_amount REAL DEFAULT 13000,
        motor_purchase TEXT DEFAULT 'Hayır',
        motor_purchase_start_date TEXT,
        motor_purchase_commitment_months INTEGER,
        motor_purchase_sale_price REAL,
        motor_purchase_monthly_amount REAL DEFAULT 11250,
        motor_purchase_installment_count INTEGER DEFAULT 12,
        current_plate TEXT,
        start_date TEXT,
        exit_date TEXT,
        cost_model TEXT NOT NULL DEFAULT 'standard_courier',
        monthly_fixed_cost REAL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (assigned_restaurant_id) REFERENCES restaurants(id)
    );

    CREATE TABLE IF NOT EXISTS personnel_role_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        cost_model TEXT NOT NULL DEFAULT 'standard_courier',
        monthly_fixed_cost REAL NOT NULL DEFAULT 0,
        effective_date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS personnel_vehicle_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        vehicle_type TEXT NOT NULL,
        motor_rental TEXT NOT NULL DEFAULT 'Hayır',
        motor_rental_monthly_amount REAL DEFAULT 13000,
        motor_purchase TEXT DEFAULT 'Hayır',
        motor_purchase_commitment_months INTEGER,
        motor_purchase_sale_price REAL,
        motor_purchase_monthly_amount REAL DEFAULT 11250,
        effective_date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS plate_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        plate TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        reason TEXT,
        active INTEGER DEFAULT 1,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS daily_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL,
        restaurant_id INTEGER NOT NULL,
        planned_personnel_id INTEGER,
        actual_personnel_id INTEGER,
        status TEXT NOT NULL,
        worked_hours REAL DEFAULT 0,
        package_count REAL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
        FOREIGN KEY (planned_personnel_id) REFERENCES personnel(id),
        FOREIGN KEY (actual_personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS deductions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        deduction_date TEXT NOT NULL,
        deduction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT,
        auto_source_key TEXT,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS inventory_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_date TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        total_invoice_amount REAL NOT NULL,
        unit_cost REAL NOT NULL,
        supplier TEXT,
        invoice_no TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS courier_equipment_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_cost REAL NOT NULL DEFAULT 0,
        unit_sale_price REAL NOT NULL DEFAULT 0,
        vat_rate REAL NOT NULL DEFAULT 20,
        installment_count INTEGER NOT NULL DEFAULT 2,
        sale_type TEXT NOT NULL DEFAULT 'Satış',
        auto_source_key TEXT,
        notes TEXT,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS box_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        return_date TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        condition_status TEXT NOT NULL,
        payout_amount REAL NOT NULL DEFAULT 0,
        waived INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id)
    );

    CREATE TABLE IF NOT EXISTS auth_sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        role_display TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        must_change_password INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS app_meta (
        meta_key TEXT PRIMARY KEY,
        meta_value TEXT NOT NULL
    );
"""


_POSTGRES_SCHEMA = """
    CREATE TABLE IF NOT EXISTS restaurants (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        brand TEXT NOT NULL,
        branch TEXT NOT NULL,
        billing_group TEXT,
        pricing_model TEXT NOT NULL,
        hourly_rate DOUBLE PRECISION DEFAULT 0,
        package_rate DOUBLE PRECISION DEFAULT 0,
        package_threshold BIGINT,
        package_rate_low DOUBLE PRECISION DEFAULT 0,
        package_rate_high DOUBLE PRECISION DEFAULT 0,
        fixed_monthly_fee DOUBLE PRECISION DEFAULT 0,
        vat_rate DOUBLE PRECISION DEFAULT 20,
        target_headcount BIGINT DEFAULT 0,
        start_date TEXT,
        end_date TEXT,
        extra_headcount_request BIGINT DEFAULT 0,
        extra_headcount_request_date TEXT,
        reduce_headcount_request BIGINT DEFAULT 0,
        reduce_headcount_request_date TEXT,
        contact_name TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        company_title TEXT,
        address TEXT,
        tax_office TEXT,
        tax_number TEXT,
        active BIGINT DEFAULT 1,
        notes TEXT,
        UNIQUE(brand, branch)
    );

    CREATE TABLE IF NOT EXISTS personnel (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        person_code TEXT,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Aktif',
        phone TEXT,
        address TEXT,
        tc_no TEXT,
        iban TEXT,
        emergency_contact_name TEXT,
        emergency_contact_phone TEXT,
        accounting_type TEXT DEFAULT 'Kendi Muhasebecisi',
        new_company_setup TEXT DEFAULT 'Hayır',
        accounting_revenue DOUBLE PRECISION DEFAULT 0,
        accountant_cost DOUBLE PRECISION DEFAULT 0,
        company_setup_revenue DOUBLE PRECISION DEFAULT 0,
        company_setup_cost DOUBLE PRECISION DEFAULT 0,
        assigned_restaurant_id BIGINT REFERENCES restaurants(id),
        vehicle_type TEXT,
        motor_rental TEXT DEFAULT 'Hayır',
        motor_rental_monthly_amount DOUBLE PRECISION DEFAULT 13000,
        motor_purchase TEXT DEFAULT 'Hayır',
        motor_purchase_start_date TEXT,
        motor_purchase_commitment_months BIGINT,
        motor_purchase_sale_price DOUBLE PRECISION,
        motor_purchase_monthly_amount DOUBLE PRECISION DEFAULT 11250,
        motor_purchase_installment_count BIGINT DEFAULT 12,
        current_plate TEXT,
        start_date TEXT,
        exit_date TEXT,
        cost_model TEXT NOT NULL DEFAULT 'standard_courier',
        monthly_fixed_cost DOUBLE PRECISION DEFAULT 0,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS personnel_role_history (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        personnel_id BIGINT NOT NULL REFERENCES personnel(id),
        role TEXT NOT NULL,
        cost_model TEXT NOT NULL DEFAULT 'standard_courier',
        monthly_fixed_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
        effective_date TEXT NOT NULL,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS personnel_vehicle_history (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        personnel_id BIGINT NOT NULL REFERENCES personnel(id),
        vehicle_type TEXT NOT NULL,
        motor_rental TEXT NOT NULL DEFAULT 'Hayır',
        motor_rental_monthly_amount DOUBLE PRECISION DEFAULT 13000,
        motor_purchase TEXT DEFAULT 'Hayır',
        motor_purchase_commitment_months BIGINT,
        motor_purchase_sale_price DOUBLE PRECISION,
        motor_purchase_monthly_amount DOUBLE PRECISION DEFAULT 11250,
        effective_date TEXT NOT NULL,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS plate_history (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        personnel_id BIGINT NOT NULL REFERENCES personnel(id),
        plate TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        reason TEXT,
        active BIGINT DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS daily_entries (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        entry_date TEXT NOT NULL,
        restaurant_id BIGINT NOT NULL REFERENCES restaurants(id),
        planned_personnel_id BIGINT REFERENCES personnel(id),
        actual_personnel_id BIGINT REFERENCES personnel(id),
        status TEXT NOT NULL,
        worked_hours DOUBLE PRECISION DEFAULT 0,
        package_count DOUBLE PRECISION DEFAULT 0,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS deductions (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        personnel_id BIGINT NOT NULL REFERENCES personnel(id),
        deduction_date TEXT NOT NULL,
        deduction_type TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL,
        notes TEXT,
        equipment_issue_id BIGINT,
        auto_source_key TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory_purchases (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        purchase_date TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity BIGINT NOT NULL,
        total_invoice_amount DOUBLE PRECISION NOT NULL,
        unit_cost DOUBLE PRECISION NOT NULL,
        supplier TEXT,
        invoice_no TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS courier_equipment_issues (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        personnel_id BIGINT NOT NULL REFERENCES personnel(id),
        issue_date TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity BIGINT NOT NULL DEFAULT 1,
        unit_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
        unit_sale_price DOUBLE PRECISION NOT NULL DEFAULT 0,
        vat_rate DOUBLE PRECISION NOT NULL DEFAULT 20,
        installment_count BIGINT NOT NULL DEFAULT 2,
        sale_type TEXT NOT NULL DEFAULT 'Satış',
        auto_source_key TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS box_returns (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        personnel_id BIGINT NOT NULL REFERENCES personnel(id),
        return_date TEXT NOT NULL,
        quantity BIGINT NOT NULL DEFAULT 1,
        condition_status TEXT NOT NULL,
        payout_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
        waived BIGINT NOT NULL DEFAULT 0,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS auth_sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS auth_users (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        role_display TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_active BIGINT NOT NULL DEFAULT 1,
        must_change_password BIGINT NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS app_meta (
        meta_key TEXT PRIMARY KEY,
        meta_value TEXT NOT NULL
    );
"""


def configure_bootstrap_engine(
    *,
    first_row_value_fn: Callable[[Any, Any], Any],
    legacy_db_paths: list[Path],
    db_path: Path,
    table_export_order: list[str],
    fixed_cost_model_by_role: dict[str, str],
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
    auto_motor_purchase_installment_count: int,
    runtime_bootstrap_version: str,
    normalize_existing_deduction_dates_fn: Callable[[Any], None],
    normalize_equipment_issue_costs_and_vat_fn: Callable[[Any], None],
    cleanup_auto_onboarding_records_fn: Callable[[Any], None],
    cleanup_auto_personnel_deduction_records_fn: Callable[[Any], None],
    ensure_all_person_role_histories_fn: Callable[[Any], None],
    ensure_all_person_vehicle_histories_fn: Callable[[Any], None],
    sync_all_personnel_business_rules_fn: Callable[[Any], None],
    sync_default_auth_users_fn: Callable[[Any], None],
    cleanup_auth_sessions_fn: Callable[[Any], None],
) -> None:
    global _FIRST_ROW_VALUE
    global _LEGACY_DB_PATHS
    global _DB_PATH
    global _TABLE_EXPORT_ORDER
    global _FIXED_COST_MODEL_BY_ROLE
    global _AUTO_MOTOR_RENTAL_DEDUCTION
    global _AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION
    global _AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT
    global _RUNTIME_BOOTSTRAP_VERSION
    global _NORMALIZE_EXISTING_DEDUCTION_DATES
    global _NORMALIZE_EQUIPMENT_ISSUE_COSTS_AND_VAT
    global _CLEANUP_AUTO_ONBOARDING_RECORDS
    global _CLEANUP_AUTO_PERSONNEL_DEDUCTION_RECORDS
    global _ENSURE_ALL_PERSON_ROLE_HISTORIES
    global _ENSURE_ALL_PERSON_VEHICLE_HISTORIES
    global _SYNC_ALL_PERSONNEL_BUSINESS_RULES
    global _SYNC_DEFAULT_AUTH_USERS
    global _CLEANUP_AUTH_SESSIONS

    _FIRST_ROW_VALUE = first_row_value_fn
    _LEGACY_DB_PATHS = list(legacy_db_paths)
    _DB_PATH = db_path
    _TABLE_EXPORT_ORDER = list(table_export_order)
    _FIXED_COST_MODEL_BY_ROLE = dict(fixed_cost_model_by_role)
    _AUTO_MOTOR_RENTAL_DEDUCTION = float(auto_motor_rental_deduction)
    _AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION = float(auto_motor_purchase_monthly_deduction)
    _AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = int(auto_motor_purchase_installment_count)
    _RUNTIME_BOOTSTRAP_VERSION = runtime_bootstrap_version
    _NORMALIZE_EXISTING_DEDUCTION_DATES = normalize_existing_deduction_dates_fn
    _NORMALIZE_EQUIPMENT_ISSUE_COSTS_AND_VAT = normalize_equipment_issue_costs_and_vat_fn
    _CLEANUP_AUTO_ONBOARDING_RECORDS = cleanup_auto_onboarding_records_fn
    _CLEANUP_AUTO_PERSONNEL_DEDUCTION_RECORDS = cleanup_auto_personnel_deduction_records_fn
    _ENSURE_ALL_PERSON_ROLE_HISTORIES = ensure_all_person_role_histories_fn
    _ENSURE_ALL_PERSON_VEHICLE_HISTORIES = ensure_all_person_vehicle_histories_fn
    _SYNC_ALL_PERSONNEL_BUSINESS_RULES = sync_all_personnel_business_rules_fn
    _SYNC_DEFAULT_AUTH_USERS = sync_default_auth_users_fn
    _CLEANUP_AUTH_SESSIONS = cleanup_auth_sessions_fn


def ensure_schema(conn: Any) -> None:
    conn.executescript(_POSTGRES_SCHEMA if conn.backend == "postgres" else _SQLITE_SCHEMA)
    conn.commit()


def get_app_meta_value(conn: Any, meta_key: str, default: str = "") -> str:
    row = conn.execute("SELECT meta_value FROM app_meta WHERE meta_key = ?", (meta_key,)).fetchone()
    return str(_FIRST_ROW_VALUE(row, default) or default)


def set_app_meta_value(conn: Any, meta_key: str, meta_value: str) -> None:
    conn.execute(
        """
        INSERT INTO app_meta (meta_key, meta_value)
        VALUES (?, ?)
        ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
        """,
        (meta_key, meta_value),
    )
    conn.commit()


def get_table_columns(conn: Any, table_name: str) -> set[str]:
    if conn.backend == "sqlite":
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}

    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ?
        """,
        (table_name,),
    ).fetchall()
    return {row["column_name"] for row in rows}


def table_has_rows(conn: Any, table: str) -> bool:
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return int(_FIRST_ROW_VALUE(cur.fetchone(), 0) or 0) > 0


def database_has_operational_data(conn: Any) -> bool:
    return any(table_has_rows(conn, table) for table in ["restaurants", "personnel", "daily_entries", "deductions"])


def find_legacy_sqlite_source() -> Path | None:
    candidates = []
    seen = set()
    for path in [*_LEGACY_DB_PATHS, _DB_PATH]:
        if path in seen or path is None:
            continue
        seen.add(path)
        if path.exists():
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def reset_postgres_sequences(conn: Any, tables: list[str]) -> None:
    if conn.backend != "postgres":
        return
    for table in tables:
        conn.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 1),
                EXISTS (SELECT 1 FROM {table})
            )
            """
        )
    conn.commit()


def import_sqlite_into_current_db(conn: Any, sqlite_path: Path) -> bool:
    if conn.backend != "postgres" or not sqlite_path.exists():
        return False

    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    imported_anything = False
    identity_tables = []

    try:
        for table in _TABLE_EXPORT_ORDER:
            columns = [row["name"] for row in source.execute(f"PRAGMA table_info({table})").fetchall()]
            if not columns:
                continue
            rows = source.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            if not rows:
                continue
            placeholders = ", ".join(["?"] * len(columns))
            insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            payload = [tuple(row[col] for col in columns) for row in rows]
            conn.executemany(insert_sql, payload)
            imported_anything = True
            if "id" in columns and table != "auth_sessions":
                identity_tables.append(table)
        conn.commit()
        reset_postgres_sequences(conn, identity_tables)
    except Exception:
        conn.rollback()
        raise
    finally:
        source.close()

    return imported_anything


def maybe_migrate_legacy_sqlite_to_postgres(conn: Any) -> Path | None:
    if conn.backend != "postgres" or database_has_operational_data(conn):
        return None
    source = find_legacy_sqlite_source()
    if not source:
        return None
    imported = import_sqlite_into_current_db(conn, source)
    return source if imported else None


def seed_initial_data(conn: Any) -> None:
    seed_flag_row = conn.execute("SELECT meta_value FROM app_meta WHERE meta_key = ?", ("initial_seed_done",)).fetchone()
    seed_done = str(_FIRST_ROW_VALUE(seed_flag_row, "") or "") == "1"
    has_existing_data = any(table_has_rows(conn, table) for table in ["restaurants", "personnel", "daily_entries", "deductions"])

    if seed_done:
        return

    if has_existing_data:
        conn.execute(
            """
            INSERT INTO app_meta (meta_key, meta_value)
            VALUES (?, ?)
            ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
            """,
            ("initial_seed_done", "1"),
        )
        conn.commit()
        return

    restaurants = [
        ("Fasuli", "Beyoğlu", "Fasuli", "threshold_package", 273, 0, 390, 33.75, 47.25, 0, 20, 2, 1, "390 pakete kadar düşük prim, üstü yüksek prim."),
        ("Fasuli", "Vatan", "Fasuli", "threshold_package", 273, 0, 390, 33.75, 47.25, 0, 20, 2, 1, "390 pakete kadar düşük prim, üstü yüksek prim."),
        ("Köroğlu Pide", "Merkez", "Köroğlu Pide", "threshold_package", 260, 0, 390, 27, 40.5, 0, 20, 4, 1, "390 paket eşiği."),
        ("Sushi Inn", "Merkez", "Sushi Inn", "fixed_monthly", 0, 0, None, 0, 0, 79800, 20, 1, 1, "26 gün 10 saat çalışan 1 kurye için sabit ücret."),
        ("SushiCo", "Beyoğlu", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Standart SushiCo modeli."),
        ("SushiCo", "Sancaktepe", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Standart SushiCo modeli."),
        ("SushiCo", "İdealistpark", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Standart SushiCo modeli."),
        ("Quick China", "Ataşehir", "Quick China", "hourly_plus_package", 279, 32, None, 0, 0, 84500, 20, 5, 1, "Şube içinde 4+1 kurye/şef yapısı var."),
        ("Quick China", "Suadiye", "Quick China", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Quick China standart şube."),
        ("Hacıbaşar", "Maltepe", "Hacıbaşar", "threshold_package", 254, 0, 390, 27, 40.5, 0, 20, 2, 1, "390 paket eşiği."),
        ("Hacıbaşar", "Ümraniye", "Hacıbaşar", "threshold_package", 254, 0, 390, 27, 40.5, 0, 20, 2, 1, "390 paket eşiği."),
        ("Yavuzbey İskender", "Merkez", "Yavuzbey İskender", "hourly_plus_package", 264, 33, None, 0, 0, 0, 20, 3, 1, "Saatlik + paket."),
        ("Burger@", "Kavacık", "Burger@", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 1, 1, "Saatlik + paket."),
        ("SushiCo", "Lens Kurtköy", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 2, 1, "Standart SushiCo modeli."),
        ("SushiCo", "Acr Loft", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 2, 1, "Standart SushiCo modeli."),
        ("SushiCo", "Çengelköy", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 5, 1, "Standart SushiCo modeli."),
        ("Doğu Otomotiv", "Merkez", "Doğu Otomotiv", "hourly_only", 330, 0, None, 0, 0, 0, 20, 4, 1, "Sadece saatlik."),
        ("SC Petshop", "Merkez", "SC Petshop", "fixed_monthly", 0, 0, None, 0, 0, 79800, 20, 1, 1, "10 saat çalışan 1 kurye için aylık sabit ücret."),
    ]
    conn.executemany(
        """
        INSERT INTO restaurants (
            brand, branch, billing_group, pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee,
            vat_rate, target_headcount, active, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        restaurants,
    )

    restaurant_rows = conn.execute("SELECT id, brand, branch FROM restaurants").fetchall()
    restaurant_map = {f"{row['brand']} - {row['branch']}": row["id"] for row in restaurant_rows}
    seeded_people = [
        ("CK-J01", "Evrem Karapınar", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_joker", 82500, "Joker havuzu"),
        ("CK-J02", "Ali Kudret Bakar", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_joker", 82500, "Joker havuzu"),
        ("CK-J03", "Cihan Can Çimen", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_joker", 117475, "Joker havuzu"),
        ("CK-J04", "Yaşar Tunç Beratoğlu", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_joker", 101600, "Joker havuzu"),
        ("CK-RTS01", "Recep Çevik", "Restoran Takım Şefi", "Aktif", None, None, None, restaurant_map.get("Quick China - Ataşehir"), "", "Hayır", "", None, None, "fixed_restoran_takim_sefi", 72050, "Quick China Takım Şefi; saatlik/paket maliyeti yok"),
    ]
    conn.executemany(
        """
        INSERT INTO personnel (
            person_code, full_name, role, status, phone, tc_no, iban,
            assigned_restaurant_id, vehicle_type, motor_rental, current_plate,
            start_date, exit_date, cost_model, monthly_fixed_cost, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        seeded_people,
    )

    conn.execute(
        """
        INSERT INTO app_meta (meta_key, meta_value)
        VALUES (?, ?)
        ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
        """,
        ("initial_seed_done", "1"),
    )
    conn.commit()


def migrate_data(conn: Any) -> None:
    corrections = [
        ("Evrem", "Evrem Karapınar", "Joker"),
        ("Ali", "Ali Kudret Bakar", "Joker"),
        ("Cihan", "Cihan Can Çimen", "Joker"),
        ("Tunç", "Yaşar Tunç Beratoğlu", "Joker"),
        ("Quick China Ataşehir Şefi", "Recep Çevik", "Şef"),
    ]
    for old_name, new_name, role in corrections:
        conn.execute(
            "UPDATE personnel SET full_name = ? WHERE full_name = ? AND role = ?",
            (new_name, old_name, role),
        )
    conn.execute(
        "UPDATE personnel SET notes = 'Quick China Takım Şefi; saatlik/paket maliyeti yok' WHERE full_name = 'Recep Çevik' AND role = 'Şef'"
    )
    conn.execute("UPDATE personnel SET role = 'Restoran Takım Şefi' WHERE role = 'Şef'")

    personnel_cols = get_table_columns(conn, "personnel")
    if "accounting_type" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN accounting_type TEXT DEFAULT 'Kendi Muhasebecisi'")
    if "new_company_setup" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN new_company_setup TEXT DEFAULT 'Hayır'")
    if "accounting_revenue" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN accounting_revenue REAL DEFAULT 0")
    if "accountant_cost" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN accountant_cost REAL DEFAULT 0")
    if "company_setup_revenue" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN company_setup_revenue REAL DEFAULT 0")
    if "company_setup_cost" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN company_setup_cost REAL DEFAULT 0")
    if "address" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN address TEXT")
    if "emergency_contact_name" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN emergency_contact_name TEXT")
    if "emergency_contact_phone" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN emergency_contact_phone TEXT")
    if "motor_purchase" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN motor_purchase TEXT DEFAULT 'Hayır'")
    if "motor_rental_monthly_amount" not in personnel_cols:
        amount_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE personnel ADD COLUMN motor_rental_monthly_amount {amount_type} DEFAULT 13000")
    if "motor_purchase_start_date" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN motor_purchase_start_date TEXT")
    if "motor_purchase_commitment_months" not in personnel_cols:
        commitment_type = "BIGINT" if conn.backend == "postgres" else "INTEGER"
        conn.execute(f"ALTER TABLE personnel ADD COLUMN motor_purchase_commitment_months {commitment_type}")
    if "motor_purchase_sale_price" not in personnel_cols:
        sale_price_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE personnel ADD COLUMN motor_purchase_sale_price {sale_price_type}")
    if "motor_purchase_monthly_amount" not in personnel_cols:
        amount_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE personnel ADD COLUMN motor_purchase_monthly_amount {amount_type} DEFAULT 11250")
    if "motor_purchase_installment_count" not in personnel_cols:
        installment_type = "BIGINT" if conn.backend == "postgres" else "INTEGER"
        conn.execute(f"ALTER TABLE personnel ADD COLUMN motor_purchase_installment_count {installment_type} DEFAULT 12")
    for role_name, cost_model_key in _FIXED_COST_MODEL_BY_ROLE.items():
        conn.execute(
            "UPDATE personnel SET cost_model = ? WHERE cost_model = 'fixed_monthly' AND role = ?",
            (cost_model_key, role_name),
        )
    conn.execute("UPDATE personnel SET cost_model = 'standard_courier' WHERE cost_model = 'fixed_kurye'")
    conn.execute("UPDATE personnel SET cost_model = 'standard_courier' WHERE cost_model IS NULL OR cost_model = ''")
    conn.execute("UPDATE personnel SET accounting_type = 'Kendi Muhasebecisi' WHERE accounting_type IS NULL OR TRIM(accounting_type) = '' OR accounting_type = '-'")
    conn.execute("UPDATE personnel SET vehicle_type = 'Kendi Motoru' WHERE vehicle_type = 'Kendi'")
    conn.execute("UPDATE personnel SET vehicle_type = 'Çat Kapında' WHERE (vehicle_type IS NULL OR vehicle_type = '') AND motor_rental = 'Evet'")
    conn.execute("UPDATE personnel SET vehicle_type = 'Kendi Motoru' WHERE vehicle_type IS NULL OR vehicle_type = ''")
    conn.execute(
        "UPDATE personnel SET motor_rental_monthly_amount = ? WHERE motor_rental_monthly_amount IS NULL OR motor_rental_monthly_amount <= 0",
        (_AUTO_MOTOR_RENTAL_DEDUCTION,),
    )
    conn.execute("UPDATE personnel SET motor_purchase = 'Hayır' WHERE motor_purchase IS NULL OR TRIM(motor_purchase) = ''")
    conn.execute(
        """
        UPDATE personnel
        SET motor_purchase_commitment_months = 12
        WHERE motor_purchase = 'Evet'
          AND (motor_purchase_commitment_months IS NULL OR motor_purchase_commitment_months <= 0)
        """
    )
    conn.execute(
        """
        UPDATE personnel
        SET motor_purchase_start_date = start_date
        WHERE motor_purchase = 'Evet'
          AND (motor_purchase_start_date IS NULL OR TRIM(motor_purchase_start_date) = '')
          AND start_date IS NOT NULL
          AND TRIM(start_date) <> ''
        """
    )
    conn.execute(
        """
        UPDATE personnel
        SET motor_purchase_sale_price = COALESCE(motor_purchase_monthly_amount, 0) * COALESCE(motor_purchase_installment_count, 0)
        WHERE motor_purchase = 'Evet'
          AND (motor_purchase_sale_price IS NULL OR motor_purchase_sale_price <= 0)
          AND COALESCE(motor_purchase_monthly_amount, 0) > 0
          AND COALESCE(motor_purchase_installment_count, 0) > 0
        """
    )
    conn.execute(
        "UPDATE personnel SET motor_purchase_monthly_amount = ? WHERE motor_purchase_monthly_amount IS NULL OR motor_purchase_monthly_amount <= 0",
        (_AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,),
    )
    conn.execute(
        "UPDATE personnel SET motor_purchase_installment_count = ? WHERE motor_purchase_installment_count IS NULL OR motor_purchase_installment_count <= 0",
        (_AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT,),
    )

    vehicle_history_cols = get_table_columns(conn, "personnel_vehicle_history")
    if "motor_rental_monthly_amount" not in vehicle_history_cols:
        amount_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE personnel_vehicle_history ADD COLUMN motor_rental_monthly_amount {amount_type} DEFAULT 13000")
    if "motor_purchase" not in vehicle_history_cols:
        conn.execute("ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase TEXT DEFAULT 'Hayır'")
    if "motor_purchase_commitment_months" not in vehicle_history_cols:
        commitment_type = "BIGINT" if conn.backend == "postgres" else "INTEGER"
        conn.execute(f"ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_commitment_months {commitment_type}")
    if "motor_purchase_sale_price" not in vehicle_history_cols:
        sale_price_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_sale_price {sale_price_type}")
    if "motor_purchase_monthly_amount" not in vehicle_history_cols:
        amount_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE personnel_vehicle_history ADD COLUMN motor_purchase_monthly_amount {amount_type} DEFAULT 11250")
    conn.execute(
        "UPDATE personnel_vehicle_history SET motor_rental_monthly_amount = ? WHERE motor_rental_monthly_amount IS NULL OR motor_rental_monthly_amount <= 0",
        (_AUTO_MOTOR_RENTAL_DEDUCTION,),
    )
    conn.execute("UPDATE personnel_vehicle_history SET motor_purchase = 'Hayır' WHERE motor_purchase IS NULL OR TRIM(motor_purchase) = ''")
    conn.execute(
        "UPDATE personnel_vehicle_history SET motor_purchase_monthly_amount = ? WHERE motor_purchase_monthly_amount IS NULL OR motor_purchase_monthly_amount <= 0",
        (_AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,),
    )

    restaurant_cols = get_table_columns(conn, "restaurants")
    if "start_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN start_date TEXT")
    if "end_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN end_date TEXT")
    if "extra_headcount_request" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN extra_headcount_request INTEGER DEFAULT 0")
    if "extra_headcount_request_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN extra_headcount_request_date TEXT")
    if "reduce_headcount_request" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN reduce_headcount_request INTEGER DEFAULT 0")
    if "reduce_headcount_request_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN reduce_headcount_request_date TEXT")
    if "contact_name" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN contact_name TEXT")
    if "contact_phone" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN contact_phone TEXT")
    if "contact_email" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN contact_email TEXT")
    if "company_title" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN company_title TEXT")
    if "address" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN address TEXT")
    if "tax_office" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN tax_office TEXT")
    if "tax_number" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN tax_number TEXT")

    existing = get_table_columns(conn, "deductions")
    if "equipment_issue_id" not in existing:
        conn.execute("ALTER TABLE deductions ADD COLUMN equipment_issue_id INTEGER")
    if "auto_source_key" not in existing:
        conn.execute("ALTER TABLE deductions ADD COLUMN auto_source_key TEXT")

    equipment_issue_cols = get_table_columns(conn, "courier_equipment_issues")
    if "vat_rate" not in equipment_issue_cols:
        vat_type = "DOUBLE PRECISION" if conn.backend == "postgres" else "REAL"
        conn.execute(f"ALTER TABLE courier_equipment_issues ADD COLUMN vat_rate {vat_type} DEFAULT 20")
    if "auto_source_key" not in equipment_issue_cols:
        conn.execute("ALTER TABLE courier_equipment_issues ADD COLUMN auto_source_key TEXT")
    conn.commit()


def _run_bootstrap_data_migration(conn: Any) -> None:
    migrate_data(conn)
    _NORMALIZE_EXISTING_DEDUCTION_DATES(conn)
    _NORMALIZE_EQUIPMENT_ISSUE_COSTS_AND_VAT(conn)
    _CLEANUP_AUTO_ONBOARDING_RECORDS(conn)
    _CLEANUP_AUTO_PERSONNEL_DEDUCTION_RECORDS(conn)
    _ENSURE_ALL_PERSON_ROLE_HISTORIES(conn)
    _ENSURE_ALL_PERSON_VEHICLE_HISTORIES(conn)
    _SYNC_ALL_PERSONNEL_BUSINESS_RULES(conn, full_history=True)


def get_registered_migrations() -> list[MigrationStep]:
    return [
        MigrationStep(
            version="2026-03-22-manual-motor-deductions",
            apply_fn=_run_bootstrap_data_migration,
            description="Bootstrap veri düzeltmeleri ve tam personel senkronizasyonu",
        ),
    ]


def _mark_current_schema_version(conn: Any, version: str) -> None:
    set_app_meta_value(conn, "schema_migration_version", version)
    set_app_meta_value(conn, "schema_migration_applied_at", datetime.now(timezone.utc).isoformat())


def apply_versioned_migrations(conn: Any) -> None:
    migrations = get_registered_migrations()
    latest_version = get_latest_migration_version(migrations)
    if not latest_version:
        return

    applied_schema_version = get_app_meta_value(conn, "schema_migration_version")
    applied_bootstrap_version = get_app_meta_value(conn, "runtime_bootstrap_version")

    # Existing live databases may already have the old monolithic bootstrap applied.
    # In that case we baseline the current schema migration version without rerunning it.
    if not applied_schema_version and applied_bootstrap_version == _RUNTIME_BOOTSTRAP_VERSION:
        _mark_current_schema_version(conn, latest_version)
        return

    for migration in get_pending_migrations(applied_schema_version, migrations):
        migration.apply_fn(conn)
        _mark_current_schema_version(conn, migration.version)


def ensure_runtime_bootstrap(conn: Any) -> None:
    bootstrap_key = f"_crm_bootstrap_done_{conn.backend}"
    if st.session_state.get(bootstrap_key):
        return
    ensure_schema(conn)
    maybe_migrate_legacy_sqlite_to_postgres(conn)
    seed_initial_data(conn)
    applied_bootstrap_version = get_app_meta_value(conn, "runtime_bootstrap_version")
    if applied_bootstrap_version != _RUNTIME_BOOTSTRAP_VERSION:
        apply_versioned_migrations(conn)
        set_app_meta_value(conn, "runtime_bootstrap_version", _RUNTIME_BOOTSTRAP_VERSION)
    else:
        apply_versioned_migrations(conn)
    _SYNC_DEFAULT_AUTH_USERS(conn)
    _CLEANUP_AUTH_SESSIONS(conn)
    st.session_state[bootstrap_key] = True
