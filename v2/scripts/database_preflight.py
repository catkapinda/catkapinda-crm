#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from render_env_bundle import validate_database_url


APPLICATION_NAME = "catkapinda-crm-v2-db-preflight"
CONNECT_TIMEOUT = 5
CUTOVER_ATTENDANCE_STALENESS_DAYS = 45
WRITE_REQUIRED_PRIVILEGES: tuple[str, ...] = ("SELECT", "INSERT", "UPDATE", "DELETE")
SEQUENCE_REQUIRED_PRIVILEGES: tuple[str, ...] = ("USAGE",)

REQUIRED_TABLES: tuple[tuple[str, str], ...] = (
    ("restaurants", "Restoran kartlari"),
    ("personnel", "Personel kartlari"),
    ("daily_entries", "Gunluk puantaj"),
    ("deductions", "Kesinti kayitlari"),
    ("inventory_purchases", "Satin alma kayitlari"),
    ("sales_leads", "Satis firsatlari"),
    ("courier_equipment_issues", "Zimmet kayitlari"),
    ("box_returns", "Box geri alim kayitlari"),
)

BOOTSTRAP_TABLES: tuple[tuple[str, str], ...] = (
    ("auth_users", "Auth kullanicilari"),
    ("auth_sessions", "Auth oturumlari"),
    ("auth_phone_codes", "SMS giris kodlari"),
    ("auth_login_attempts", "Login deneme kayitlari"),
    ("audit_logs", "Sistem kayitlari"),
    ("personnel_role_history", "Rol gecmisi"),
    ("personnel_vehicle_history", "Motor gecmisi"),
    ("plate_history", "Plaka gecmisi"),
)

BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES: frozenset[str] = frozenset(
    {
        "auth_users",
        "auth_sessions",
        "auth_phone_codes",
        "auth_login_attempts",
        "audit_logs",
    }
)

REQUIRED_CRITICAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "restaurants": (
        "id",
        "brand",
        "branch",
        "pricing_model",
        "hourly_rate",
        "package_rate",
        "package_threshold",
        "package_rate_low",
        "package_rate_high",
        "fixed_monthly_fee",
        "vat_rate",
        "target_headcount",
        "start_date",
        "end_date",
        "contact_name",
        "contact_phone",
        "company_title",
        "address",
        "active",
        "notes",
    ),
    "personnel": (
        "id",
        "person_code",
        "full_name",
        "role",
        "status",
        "phone",
        "assigned_restaurant_id",
        "vehicle_type",
        "motor_rental",
        "motor_purchase",
        "motor_rental_monthly_amount",
        "motor_purchase_start_date",
        "motor_purchase_commitment_months",
        "motor_purchase_sale_price",
        "motor_purchase_monthly_deduction",
        "current_plate",
        "start_date",
        "monthly_fixed_cost",
        "notes",
    ),
    "daily_entries": (
        "id",
        "entry_date",
        "restaurant_id",
        "planned_personnel_id",
        "actual_personnel_id",
        "status",
        "worked_hours",
        "package_count",
        "monthly_invoice_amount",
        "absence_reason",
        "coverage_type",
        "notes",
    ),
    "deductions": (
        "id",
        "personnel_id",
        "deduction_date",
        "deduction_type",
        "amount",
        "notes",
        "auto_source_key",
        "equipment_issue_id",
    ),
    "inventory_purchases": (
        "id",
        "purchase_date",
        "item_name",
        "quantity",
        "total_invoice_amount",
        "unit_cost",
        "supplier",
        "invoice_no",
        "notes",
    ),
    "sales_leads": (
        "id",
        "restaurant_name",
        "city",
        "district",
        "address",
        "contact_name",
        "contact_phone",
        "contact_email",
        "requested_courier_count",
        "lead_source",
        "proposed_quote",
        "pricing_model",
        "hourly_rate",
        "package_rate",
        "package_threshold",
        "package_rate_low",
        "package_rate_high",
        "fixed_monthly_fee",
        "pricing_model_hint",
        "status",
        "next_follow_up_date",
        "assigned_owner",
        "notes",
        "created_at",
        "updated_at",
    ),
    "courier_equipment_issues": (
        "id",
        "personnel_id",
        "issue_date",
        "item_name",
        "quantity",
        "unit_cost",
        "unit_sale_price",
        "vat_rate",
        "installment_count",
        "sale_type",
        "notes",
        "auto_source_key",
    ),
    "box_returns": (
        "id",
        "personnel_id",
        "return_date",
        "quantity",
        "condition_status",
        "payout_amount",
        "waived",
        "notes",
    ),
}

BOOTSTRAP_CRITICAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "auth_users": (
        "id",
        "email",
        "phone",
        "full_name",
        "role",
        "role_display",
        "password_hash",
        "is_active",
        "must_change_password",
        "created_at",
        "updated_at",
    ),
    "auth_sessions": ("token", "username", "created_at", "expires_at"),
    "auth_phone_codes": (
        "id",
        "auth_user_id",
        "phone",
        "code_hash",
        "purpose",
        "created_at",
        "expires_at",
        "consumed_at",
        "attempt_count",
        "last_attempt_at",
    ),
    "auth_login_attempts": (
        "identity",
        "failed_count",
        "first_failed_at",
        "last_failed_at",
        "blocked_until",
    ),
    "audit_logs": (
        "id",
        "created_at",
        "actor_username",
        "actor_full_name",
        "actor_role",
        "entity_type",
        "entity_id",
        "action_type",
        "summary",
        "details_json",
    ),
    "personnel_role_history": (
        "id",
        "personnel_id",
        "role",
        "cost_model",
        "monthly_fixed_cost",
        "effective_date",
        "changed_at",
        "notes",
    ),
    "personnel_vehicle_history": (
        "id",
        "personnel_id",
        "vehicle_type",
        "motor_rental",
        "motor_rental_monthly_amount",
        "motor_purchase",
        "motor_purchase_start_date",
        "motor_purchase_commitment_months",
        "motor_purchase_sale_price",
        "motor_purchase_monthly_deduction",
        "effective_date",
        "changed_at",
        "notes",
    ),
    "plate_history": (
        "id",
        "personnel_id",
        "plate",
        "start_date",
        "end_date",
        "reason",
        "active",
    ),
}


def _is_placeholder(value: str) -> bool:
    normalized = str(value or "").strip()
    return normalized.startswith("<") and normalized.endswith(">")


def resolve_database_url(explicit_value: str | None = None) -> str:
    candidates = (
        explicit_value,
        os.getenv("CK_V2_DATABASE_URL"),
        os.getenv("DATABASE_URL"),
    )
    for item in candidates:
        value = str(item or "").strip()
        if value:
            return value
    raise ValueError("CK_V2_DATABASE_URL veya DATABASE_URL tanimli degil.")


def mask_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    user = parsed.username or ""
    database_name = parsed.path.lstrip("/") or "-"
    query = f"?{parsed.query}" if parsed.query else ""
    auth = f"{user}:***@" if user else ""
    return f"{parsed.scheme}://{auth}{host}{port}/{database_name}{query}"


def _row_to_mapping(row: object) -> dict[str, object]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return {}


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    cursor = conn.execute("SELECT to_regclass(%s) AS table_name", (table_name,))
    row = _row_to_mapping(cursor.fetchone())
    return bool(row.get("table_name"))


def _table_count(conn: psycopg.Connection, table_name: str) -> int | None:
    cursor = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
    row = _row_to_mapping(cursor.fetchone())
    count = row.get("count")
    if count is None:
        return None
    return int(count)


def _table_columns(conn: psycopg.Connection, table_name: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND table_schema = ANY(current_schemas(false))
        ORDER BY ordinal_position
        """,
        (table_name,),
    ).fetchall()
    columns: set[str] = set()
    for row in rows:
        item = _row_to_mapping(row)
        column_name = str(item.get("column_name") or "").strip()
        if column_name:
            columns.add(column_name)
    return columns


def _current_schema_name(conn: psycopg.Connection) -> str:
    cursor = conn.execute("SELECT current_schema() AS schema_name")
    row = _row_to_mapping(cursor.fetchone())
    schema_name = str(row.get("schema_name") or "").strip()
    return schema_name or "public"


def _schema_create_allowed(conn: psycopg.Connection, schema_name: str) -> bool:
    cursor = conn.execute(
        "SELECT has_schema_privilege(current_user, %s, 'CREATE') AS allowed",
        (schema_name,),
    )
    row = _row_to_mapping(cursor.fetchone())
    return bool(row.get("allowed"))


def _table_privileges(
    conn: psycopg.Connection,
    table_name: str,
    *,
    required_privileges: tuple[str, ...],
) -> dict[str, bool]:
    privileges: dict[str, bool] = {}
    for privilege in required_privileges:
        cursor = conn.execute(
            "SELECT has_table_privilege(current_user, %s, %s) AS allowed",
            (table_name, privilege),
        )
        row = _row_to_mapping(cursor.fetchone())
        privileges[privilege] = bool(row.get("allowed"))
    return privileges


def _table_sequence_name(conn: psycopg.Connection, table_name: str) -> str | None:
    cursor = conn.execute(
        "SELECT pg_get_serial_sequence(%s, 'id') AS sequence_name",
        (table_name,),
    )
    row = _row_to_mapping(cursor.fetchone())
    sequence_name = str(row.get("sequence_name") or "").strip()
    return sequence_name or None


def _table_max_id(conn: psycopg.Connection, table_name: str) -> int:
    cursor = conn.execute(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table_name}")
    row = _row_to_mapping(cursor.fetchone())
    return int(row.get("max_id") or 0)


def _sequence_last_value(conn: psycopg.Connection, sequence_name: str) -> int | None:
    if "." in sequence_name:
        schema_name, sequence_only_name = sequence_name.split(".", 1)
    else:
        schema_name, sequence_only_name = "public", sequence_name
    cursor = conn.execute(
        """
        SELECT last_value
        FROM pg_sequences
        WHERE schemaname = %s
          AND sequencename = %s
        """,
        (schema_name, sequence_only_name),
    )
    row = _row_to_mapping(cursor.fetchone())
    value = row.get("last_value")
    return int(value) if value is not None else None


def _sequence_privileges(
    conn: psycopg.Connection,
    sequence_name: str,
    *,
    required_privileges: tuple[str, ...],
) -> dict[str, bool]:
    privileges: dict[str, bool] = {}
    for privilege in required_privileges:
        cursor = conn.execute(
            "SELECT has_sequence_privilege(current_user, %s, %s) AS allowed",
            (sequence_name, privilege),
        )
        row = _row_to_mapping(cursor.fetchone())
        privileges[privilege] = bool(row.get("allowed"))
    return privileges


def _scalar_value(conn: psycopg.Connection, query: str, params: tuple[object, ...] = ()) -> object:
    cursor = conn.execute(query, params)
    row = _row_to_mapping(cursor.fetchone())
    if not row:
        return None
    return next(iter(row.values()))


def _normalize_date_value(raw_value: object) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value.date()
    if isinstance(raw_value, date):
        return raw_value
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    if " " in normalized:
        normalized = normalized.split(" ", 1)[0]
    if "T" in normalized:
        normalized = normalized.split("T", 1)[0]
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _build_data_health(conn: psycopg.Connection, *, reference_date: date) -> tuple[dict[str, object], list[str]]:
    active_restaurants = int(
        _scalar_value(
            conn,
            "SELECT COUNT(*) AS count FROM restaurants WHERE COALESCE(active, TRUE) = TRUE",
        )
        or 0
    )
    active_personnel = int(
        _scalar_value(
            conn,
            "SELECT COUNT(*) AS count FROM personnel WHERE COALESCE(status, '') = 'Aktif'",
        )
        or 0
    )
    assigned_personnel = int(
        _scalar_value(
            conn,
            """
            SELECT COUNT(*) AS count
            FROM personnel
            WHERE COALESCE(status, '') = 'Aktif'
              AND assigned_restaurant_id IS NOT NULL
            """,
        )
        or 0
    )
    latest_attendance_date = _normalize_date_value(
        _scalar_value(conn, "SELECT MAX(entry_date) AS latest_value FROM daily_entries")
    )
    latest_deduction_date = _normalize_date_value(
        _scalar_value(conn, "SELECT MAX(deduction_date) AS latest_value FROM deductions")
    )
    latest_purchase_date = _normalize_date_value(
        _scalar_value(conn, "SELECT MAX(purchase_date) AS latest_value FROM inventory_purchases")
    )
    latest_sales_date = _normalize_date_value(
        _scalar_value(conn, "SELECT MAX(updated_at) AS latest_value FROM sales_leads")
    )
    latest_equipment_issue_date = _normalize_date_value(
        _scalar_value(conn, "SELECT MAX(issue_date) AS latest_value FROM courier_equipment_issues")
    )

    attendance_age_days = (
        (reference_date - latest_attendance_date).days
        if latest_attendance_date is not None
        else None
    )

    cutover_blocking_items: list[str] = []
    if active_restaurants <= 0:
        cutover_blocking_items.append("Aktif restoran sayisi 0; canli veri baglantisi dogrulanmali.")
    if active_personnel <= 0:
        cutover_blocking_items.append("Aktif personel sayisi 0; canli veri baglantisi dogrulanmali.")
    if assigned_personnel <= 0:
        cutover_blocking_items.append("Subeye atanmis aktif personel gorunmuyor; veri kapsami yetersiz.")
    if latest_attendance_date is None:
        cutover_blocking_items.append("Gunluk puantaj gecmisi bulunamadi; cutover oncesi veri tazeligi dogrulanmali.")
    elif attendance_age_days is not None and attendance_age_days > CUTOVER_ATTENDANCE_STALENESS_DAYS:
        cutover_blocking_items.append(
            "Gunluk puantaj verisi eski gorunuyor; son kayit "
            f"{latest_attendance_date.isoformat()} ({attendance_age_days} gun once)."
        )

    return (
        {
            "active_restaurants": active_restaurants,
            "active_personnel": active_personnel,
            "assigned_personnel": assigned_personnel,
            "latest_attendance_date": latest_attendance_date.isoformat() if latest_attendance_date else None,
            "attendance_age_days": attendance_age_days,
            "latest_deduction_date": latest_deduction_date.isoformat() if latest_deduction_date else None,
            "latest_purchase_date": latest_purchase_date.isoformat() if latest_purchase_date else None,
            "latest_sales_date": latest_sales_date.isoformat() if latest_sales_date else None,
            "latest_equipment_issue_date": (
                latest_equipment_issue_date.isoformat() if latest_equipment_issue_date else None
            ),
        },
        cutover_blocking_items,
    )


def _build_data_quality(
    conn: psycopg.Connection,
    *,
    has_auth_users: bool,
) -> tuple[dict[str, int], list[str]]:
    quality_counts = {
        "active_restaurants_missing_identity": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM restaurants
                WHERE COALESCE(active, TRUE) = TRUE
                  AND (
                    NULLIF(BTRIM(COALESCE(brand, '')), '') IS NULL
                    OR NULLIF(BTRIM(COALESCE(branch, '')), '') IS NULL
                  )
                """,
            )
            or 0
        ),
        "active_personnel_missing_identity": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM personnel
                WHERE COALESCE(status, '') = 'Aktif'
                  AND (
                    NULLIF(BTRIM(COALESCE(person_code, '')), '') IS NULL
                    OR NULLIF(BTRIM(COALESCE(full_name, '')), '') IS NULL
                  )
                """,
            )
            or 0
        ),
        "duplicate_restaurant_keys": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM (
                    SELECT LOWER(BTRIM(COALESCE(brand, ''))) AS brand_key,
                           LOWER(BTRIM(COALESCE(branch, ''))) AS branch_key
                    FROM restaurants
                    WHERE COALESCE(active, TRUE) = TRUE
                      AND NULLIF(BTRIM(COALESCE(brand, '')), '') IS NOT NULL
                      AND NULLIF(BTRIM(COALESCE(branch, '')), '') IS NOT NULL
                    GROUP BY 1, 2
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
            )
            or 0
        ),
        "duplicate_person_codes": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM (
                    SELECT LOWER(BTRIM(COALESCE(person_code, ''))) AS person_code_key
                    FROM personnel
                    WHERE NULLIF(BTRIM(COALESCE(person_code, '')), '') IS NOT NULL
                    GROUP BY 1
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
            )
            or 0
        ),
        "duplicate_auth_emails": 0,
    }
    if has_auth_users:
        quality_counts["duplicate_auth_emails"] = int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM (
                    SELECT LOWER(BTRIM(COALESCE(email, ''))) AS email_key
                    FROM auth_users
                    WHERE NULLIF(BTRIM(COALESCE(email, '')), '') IS NOT NULL
                    GROUP BY 1
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
            )
            or 0
        )

    cutover_blocking_items: list[str] = []
    if quality_counts["active_restaurants_missing_identity"] > 0:
        cutover_blocking_items.append("Aktif restoran kartlarinda bos marka/sube alanlari var.")
    if quality_counts["active_personnel_missing_identity"] > 0:
        cutover_blocking_items.append(
            "Aktif personel kartlarinda bos personel kodu veya ad soyad alanlari var."
        )
    if quality_counts["duplicate_restaurant_keys"] > 0:
        cutover_blocking_items.append(
            f"Ayni marka/sube kombinasyonunda {quality_counts['duplicate_restaurant_keys']} cakisan restoran kaydi var."
        )
    if quality_counts["duplicate_person_codes"] > 0:
        cutover_blocking_items.append(
            f"{quality_counts['duplicate_person_codes']} personel kodu birden fazla kartta tekrar ediyor."
        )
    if quality_counts["duplicate_auth_emails"] > 0:
        cutover_blocking_items.append(
            f"{quality_counts['duplicate_auth_emails']} auth e-posta degeri birden fazla kullanicida tekrar ediyor."
        )

    return quality_counts, cutover_blocking_items


def _build_relation_health(conn: psycopg.Connection) -> tuple[dict[str, int], list[str]]:
    relation_counts = {
        "personnel_restaurant_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM personnel p
                LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
                WHERE p.assigned_restaurant_id IS NOT NULL
                  AND r.id IS NULL
                """,
            )
            or 0
        ),
        "attendance_restaurant_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM daily_entries d
                LEFT JOIN restaurants r ON r.id = d.restaurant_id
                WHERE d.restaurant_id IS NOT NULL
                  AND r.id IS NULL
                """,
            )
            or 0
        ),
        "attendance_planned_personnel_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM daily_entries d
                LEFT JOIN personnel p ON p.id = d.planned_personnel_id
                WHERE d.planned_personnel_id IS NOT NULL
                  AND p.id IS NULL
                """,
            )
            or 0
        ),
        "attendance_actual_personnel_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM daily_entries d
                LEFT JOIN personnel p ON p.id = d.actual_personnel_id
                WHERE d.actual_personnel_id IS NOT NULL
                  AND p.id IS NULL
                """,
            )
            or 0
        ),
        "deduction_personnel_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM deductions d
                LEFT JOIN personnel p ON p.id = d.personnel_id
                WHERE d.personnel_id IS NOT NULL
                  AND p.id IS NULL
                """,
            )
            or 0
        ),
        "equipment_personnel_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM courier_equipment_issues i
                LEFT JOIN personnel p ON p.id = i.personnel_id
                WHERE i.personnel_id IS NOT NULL
                  AND p.id IS NULL
                """,
            )
            or 0
        ),
        "box_return_personnel_orphans": int(
            _scalar_value(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM box_returns b
                LEFT JOIN personnel p ON p.id = b.personnel_id
                WHERE b.personnel_id IS NOT NULL
                  AND p.id IS NULL
                """,
            )
            or 0
        ),
    }

    cutover_blocking_items: list[str] = []
    relation_labels = {
        "personnel_restaurant_orphans": "Personel -> restoran",
        "attendance_restaurant_orphans": "Puantaj -> restoran",
        "attendance_planned_personnel_orphans": "Puantaj -> planli personel",
        "attendance_actual_personnel_orphans": "Puantaj -> fiili personel",
        "deduction_personnel_orphans": "Kesinti -> personel",
        "equipment_personnel_orphans": "Ekipman -> personel",
        "box_return_personnel_orphans": "Box iade -> personel",
    }
    for key, count in relation_counts.items():
        if count > 0:
            cutover_blocking_items.append(
                f"{relation_labels[key]} iliskisinde {count} kopuk kayit var."
            )

    return relation_counts, cutover_blocking_items


def _inspect_group(
    conn: psycopg.Connection,
    table_specs: tuple[tuple[str, str], ...],
    *,
    critical_columns_map: dict[str, tuple[str, ...]],
    required_privileges: tuple[str, ...],
) -> tuple[
    list[dict[str, object]],
    list[str],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, dict[str, int | str | None]],
]:
    entries: list[dict[str, object]] = []
    missing_tables: list[str] = []
    missing_columns_by_table: dict[str, list[str]] = {}
    missing_privileges_by_table: dict[str, list[str]] = {}
    missing_sequence_privileges_by_table: dict[str, list[str]] = {}
    sequence_alignment_issues_by_table: dict[str, dict[str, int | str | None]] = {}

    for table_name, label in table_specs:
        critical_columns = list(critical_columns_map.get(table_name, ()))
        present = _table_exists(conn, table_name)
        row_count: int | None = None
        detail = "Tablo bulundu."
        missing_columns: list[str] = []
        missing_privileges: list[str] = []
        sequence_name: str | None = None
        missing_sequence_privileges: list[str] = []
        sequence_last_value: int | None = None
        table_max_id: int | None = None
        sequence_out_of_sync = False
        if present:
            available_columns = _table_columns(conn, table_name)
            missing_columns = [column for column in critical_columns if column not in available_columns]
            if missing_columns:
                missing_columns_by_table[table_name] = missing_columns
            available_privileges = _table_privileges(
                conn,
                table_name,
                required_privileges=required_privileges,
            )
            missing_privileges = [
                privilege for privilege in required_privileges if not available_privileges.get(privilege, False)
            ]
            if missing_privileges:
                missing_privileges_by_table[table_name] = missing_privileges
            if "id" in available_columns:
                sequence_name = _table_sequence_name(conn, table_name)
                if sequence_name:
                    table_max_id = _table_max_id(conn, table_name)
                    sequence_last_value = _sequence_last_value(conn, sequence_name)
                    sequence_privileges = _sequence_privileges(
                        conn,
                        sequence_name,
                        required_privileges=SEQUENCE_REQUIRED_PRIVILEGES,
                    )
                    missing_sequence_privileges = [
                        privilege
                        for privilege in SEQUENCE_REQUIRED_PRIVILEGES
                        if not sequence_privileges.get(privilege, False)
                    ]
                    if missing_sequence_privileges:
                        missing_sequence_privileges_by_table[table_name] = missing_sequence_privileges
                    if table_max_id > 0 and (sequence_last_value is None or sequence_last_value < table_max_id):
                        sequence_out_of_sync = True
                        sequence_alignment_issues_by_table[table_name] = {
                            "sequence_name": sequence_name,
                            "sequence_last_value": sequence_last_value,
                            "max_id": table_max_id,
                        }
            try:
                row_count = _table_count(conn, table_name)
                detail_parts = [
                    (
                        f"Tablo bulundu. Satir sayisi: {row_count}."
                        if row_count is not None
                        else "Tablo bulundu. Satir sayisi okunamadi."
                    )
                ]
            except Exception as exc:  # pragma: no cover
                detail_parts = [f"Tablo bulundu ancak satir sayisi alinamadi: {exc}"]
            if missing_columns:
                detail_parts.append(
                    f"Eksik kritik kolonlar: {', '.join(missing_columns)}."
                )
            elif critical_columns:
                detail_parts.append(f"Kritik kolonlar dogrulandi ({len(critical_columns)}).")
            if missing_privileges:
                detail_parts.append(
                    f"Eksik tablo yetkileri: {', '.join(missing_privileges)}."
                )
            if missing_sequence_privileges and sequence_name:
                detail_parts.append(
                    f"Eksik sequence yetkileri ({sequence_name}): {', '.join(missing_sequence_privileges)}."
                )
            if sequence_out_of_sync and sequence_name:
                detail_parts.append(
                    f"Sequence geride kalmis ({sequence_name}): last_value={sequence_last_value}, max_id={table_max_id}."
                )
            detail = " ".join(detail_parts)
        else:
            missing_tables.append(table_name)
            detail = "Tablo eksik."

        entries.append(
            {
                "table": table_name,
                "label": label,
                "present": present,
                "row_count": row_count,
                "critical_columns": critical_columns,
                "missing_columns": missing_columns,
                "missing_privileges": missing_privileges,
                "sequence_name": sequence_name,
                "missing_sequence_privileges": missing_sequence_privileges,
                "sequence_last_value": sequence_last_value,
                "table_max_id": table_max_id,
                "sequence_out_of_sync": sequence_out_of_sync,
                "detail": detail,
            }
        )

    return (
        entries,
        missing_tables,
        missing_columns_by_table,
        missing_privileges_by_table,
        missing_sequence_privileges_by_table,
        sequence_alignment_issues_by_table,
    )


def build_database_preflight_report(
    *,
    database_url: str,
    connect_fn=psycopg.connect,
    reference_date: date | None = None,
) -> dict[str, object]:
    normalized_database_url = str(database_url or "").strip()
    if not normalized_database_url:
        raise ValueError("Veritabani URL'i bos olamaz.")
    if _is_placeholder(normalized_database_url):
        raise ValueError("Veritabani URL'i icin gercek bir deger girilmeli.")

    validated_database_url = validate_database_url(normalized_database_url)
    effective_reference_date = reference_date or date.today()

    with connect_fn(
        validated_database_url,
        row_factory=dict_row,
        connect_timeout=CONNECT_TIMEOUT,
        application_name=APPLICATION_NAME,
    ) as conn:
        current_schema_name = _current_schema_name(conn)
        schema_create_allowed = _schema_create_allowed(conn, current_schema_name)
        (
            required_entries,
            required_missing,
            required_missing_columns,
            required_missing_privileges,
            required_missing_sequence_privileges,
            required_sequence_alignment_issues,
        ) = _inspect_group(
            conn,
            REQUIRED_TABLES,
            critical_columns_map=REQUIRED_CRITICAL_COLUMNS,
            required_privileges=WRITE_REQUIRED_PRIVILEGES,
        )
        (
            bootstrap_entries,
            bootstrap_missing,
            bootstrap_missing_columns,
            bootstrap_missing_privileges,
            bootstrap_missing_sequence_privileges,
            bootstrap_sequence_alignment_issues,
        ) = _inspect_group(
            conn,
            BOOTSTRAP_TABLES,
            critical_columns_map=BOOTSTRAP_CRITICAL_COLUMNS,
            required_privileges=WRITE_REQUIRED_PRIVILEGES,
        )
        data_health, cutover_blocking_items = _build_data_health(
            conn,
            reference_date=effective_reference_date,
        )
        data_quality, data_quality_blocking_items = _build_data_quality(
            conn,
            has_auth_users=_table_exists(conn, "auth_users"),
        )
        relation_health, relation_blocking_items = _build_relation_health(conn)

    warnings: list[str] = []
    row_count_map = {entry["table"]: entry["row_count"] for entry in required_entries if entry["present"]}
    for table_name in ("restaurants", "personnel", "daily_entries"):
        count = row_count_map.get(table_name)
        if count == 0:
            warnings.append(
                f"`{table_name}` tablosu bos gorunuyor; ayni canli PostgreSQL baglantisini kullandigini tekrar dogrula."
            )

    if bootstrap_missing:
        warnings.append(
            "Auth ve gecmis tablolarinin bir kismi eksik; v2 bootstrap bunlari acilista tamamlayabilir."
        )
    for table_name, missing_columns in bootstrap_missing_columns.items():
        warnings.append(
            f"`{table_name}` tablosunda eksik kritik kolonlar var: {', '.join(missing_columns)}."
        )
    for table_name, missing_privileges in bootstrap_missing_privileges.items():
        message = f"`{table_name}` tablosunda eksik tablo yetkileri var: {', '.join(missing_privileges)}."
        if table_name in BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES:
            cutover_blocking_items.append(message)
        else:
            warnings.append(message)
    for table_name, missing_sequence_privileges in bootstrap_missing_sequence_privileges.items():
        sequence_name = next(
            (
                str(entry.get("sequence_name") or "")
                for entry in bootstrap_entries
                if entry.get("table") == table_name
            ),
            "",
        )
        message = (
            f"`{table_name}` tablosunun sequence yetkileri eksik: "
            f"{sequence_name or 'sequence'} ({', '.join(missing_sequence_privileges)})."
        )
        if table_name in BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES:
            cutover_blocking_items.append(message)
        else:
            warnings.append(message)
    for table_name, issue in bootstrap_sequence_alignment_issues.items():
        message = (
            f"`{table_name}` tablosunun sequence degeri geride: "
            f"{issue.get('sequence_name') or 'sequence'} "
            f"(last_value={issue.get('sequence_last_value')}, max_id={issue.get('max_id')})."
        )
        if table_name in BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES:
            cutover_blocking_items.append(message)
        else:
            warnings.append(message)

    cutover_blocking_items.extend(data_quality_blocking_items)
    cutover_blocking_items.extend(relation_blocking_items)

    blocking_items = [f"`{table_name}` tablosu eksik." for table_name in required_missing]
    if bootstrap_missing and not schema_create_allowed:
        blocking_items.append(
            f"Bootstrap tablolarinin bir kismi eksik ve `{current_schema_name}` semasinda CREATE yetkisi yok."
        )
    blocking_items.extend(
        [
            f"`{table_name}` tablosunda eksik kritik kolonlar var: {', '.join(missing_columns)}."
            for table_name, missing_columns in required_missing_columns.items()
        ]
    )
    blocking_items.extend(
        [
            f"`{table_name}` tablosunda eksik tablo yetkileri var: {', '.join(missing_privileges)}."
            for table_name, missing_privileges in required_missing_privileges.items()
        ]
    )
    blocking_items.extend(
        [
            (
                f"`{table_name}` tablosunun sequence yetkileri eksik: "
                f"{next((str(entry.get('sequence_name') or '') for entry in required_entries if entry.get('table') == table_name), '') or 'sequence'} "
                f"({', '.join(missing_sequence_privileges)})."
            )
            for table_name, missing_sequence_privileges in required_missing_sequence_privileges.items()
        ]
    )
    blocking_items.extend(
        [
            (
                f"`{table_name}` tablosunun sequence degeri geride: "
                f"{issue.get('sequence_name') or 'sequence'} "
                f"(last_value={issue.get('sequence_last_value')}, max_id={issue.get('max_id')})."
            )
            for table_name, issue in required_sequence_alignment_issues.items()
        ]
    )
    blocking_items.extend(
        [
            f"`{table_name}` tablosunda eksik tablo yetkileri var: {', '.join(missing_privileges)}."
            for table_name, missing_privileges in bootstrap_missing_privileges.items()
            if table_name in BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES
        ]
    )
    blocking_items.extend(
        [
            (
                f"`{table_name}` tablosunun sequence yetkileri eksik: "
                f"{next((str(entry.get('sequence_name') or '') for entry in bootstrap_entries if entry.get('table') == table_name), '') or 'sequence'} "
                f"({', '.join(missing_sequence_privileges)})."
            )
            for table_name, missing_sequence_privileges in bootstrap_missing_sequence_privileges.items()
            if table_name in BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES
        ]
    )
    blocking_items.extend(
        [
            (
                f"`{table_name}` tablosunun sequence degeri geride: "
                f"{issue.get('sequence_name') or 'sequence'} "
                f"(last_value={issue.get('sequence_last_value')}, max_id={issue.get('max_id')})."
            )
            for table_name, issue in bootstrap_sequence_alignment_issues.items()
            if table_name in BOOTSTRAP_BLOCKING_PRIVILEGE_TABLES
        ]
    )
    passed = not blocking_items
    cutover_ready = passed and not cutover_blocking_items
    summary = (
        "Veritabani omurgasi v2 pilotu icin hazir."
        if passed
        else "Veritabani omurgasinda pilotu durduran tablo veya kolon eksikleri var."
    )
    recommended_next_step = (
        "Ayni PostgreSQL ile pilot acilabilir; yine de deploy oncesi tam yedek al."
        if passed
        else "Eksik tablo/kolonlari tamamla veya dogru canli PostgreSQL baglantisini gir."
    )
    cutover_recommended_next_step = (
        "Canli domaine gecis icin veri kapsami da yeterli gorunuyor."
        if cutover_ready
        else "Canli domaine gecmeden once aktif restoran/personel ve guncel puantaj kapsamini dogrula."
    )

    return {
        "passed": passed,
        "cutover_ready": cutover_ready,
        "summary": summary,
        "recommended_next_step": recommended_next_step,
        "cutover_recommended_next_step": cutover_recommended_next_step,
        "database_url_masked": mask_database_url(validated_database_url),
        "schema_name": current_schema_name,
        "schema_create_allowed": schema_create_allowed,
        "required_tables": required_entries,
        "bootstrap_tables": bootstrap_entries,
        "required_missing_columns": required_missing_columns,
        "bootstrap_missing_columns": bootstrap_missing_columns,
        "required_missing_privileges": required_missing_privileges,
        "bootstrap_missing_privileges": bootstrap_missing_privileges,
        "required_missing_sequence_privileges": required_missing_sequence_privileges,
        "bootstrap_missing_sequence_privileges": bootstrap_missing_sequence_privileges,
        "required_sequence_alignment_issues": required_sequence_alignment_issues,
        "bootstrap_sequence_alignment_issues": bootstrap_sequence_alignment_issues,
        "data_health": data_health,
        "data_quality": data_quality,
        "relation_health": relation_health,
        "blocking_items": blocking_items,
        "cutover_blocking_items": cutover_blocking_items,
        "warnings": warnings,
    }


def render_report_text(report: dict[str, object]) -> str:
    database_url_masked = str(report.get("database_url_masked") or "-")
    lines = [
        "Cat Kapinda CRM v2 Database Preflight",
        f"Passed: {report['passed']}",
        f"Summary: {report['summary']}",
        f"Database: {database_url_masked}",
        f"Schema: {report.get('schema_name') or '-'}",
        f"Schema Create Allowed: {report.get('schema_create_allowed')}",
        "",
        "Required Tables:",
    ]
    for entry in report.get("required_tables") or []:
        item = entry if isinstance(entry, dict) else {}
        status = (
            "OK"
            if item.get("present")
            and not item.get("missing_columns")
            and not item.get("missing_privileges")
            and not item.get("missing_sequence_privileges")
            and not item.get("sequence_out_of_sync")
            else (
                "MISSING"
                if not item.get("present")
                else (
                    "SEQ"
                    if item.get("missing_sequence_privileges") or item.get("sequence_out_of_sync")
                    else ("PRIV" if item.get("missing_privileges") else "SCHEMA")
                )
            )
        )
        lines.append(f"- [{status}] {item.get('table')}: {item.get('detail')}")

    lines.extend(["", "Bootstrap Tables:"])
    for entry in report.get("bootstrap_tables") or []:
        item = entry if isinstance(entry, dict) else {}
        status = (
            "OK"
            if item.get("present")
            and not item.get("missing_columns")
            and not item.get("missing_privileges")
            and not item.get("missing_sequence_privileges")
            and not item.get("sequence_out_of_sync")
            else (
                "OPTIONAL"
                if not item.get("present")
                else (
                    "WARN"
                    if item.get("missing_columns")
                    or item.get("missing_privileges")
                    or item.get("missing_sequence_privileges")
                    or item.get("sequence_out_of_sync")
                    else "WARN"
                )
            )
        )
        lines.append(f"- [{status}] {item.get('table')}: {item.get('detail')}")

    lines.extend(["", "Blocking Items:"])
    lines.extend([f"- {item}" for item in report.get("blocking_items") or []] or ["- Yok"])
    lines.extend(["", "Warnings:"])
    lines.extend([f"- {item}" for item in report.get("warnings") or []] or ["- Yok"])
    data_health = report.get("data_health") if isinstance(report.get("data_health"), dict) else {}
    lines.extend(
        [
            "",
            "Data Health:",
            f"- Active Restaurants: {data_health.get('active_restaurants', '-')}",
            f"- Active Personnel: {data_health.get('active_personnel', '-')}",
            f"- Assigned Personnel: {data_health.get('assigned_personnel', '-')}",
            f"- Latest Attendance Date: {data_health.get('latest_attendance_date') or '-'}",
            f"- Attendance Age Days: {data_health.get('attendance_age_days') if data_health.get('attendance_age_days') is not None else '-'}",
            f"- Latest Deduction Date: {data_health.get('latest_deduction_date') or '-'}",
            f"- Latest Purchase Date: {data_health.get('latest_purchase_date') or '-'}",
            f"- Latest Sales Date: {data_health.get('latest_sales_date') or '-'}",
            f"- Latest Equipment Issue Date: {data_health.get('latest_equipment_issue_date') or '-'}",
            "",
            "Cutover Readiness:",
            f"- Ready: {report.get('cutover_ready')}",
        ]
    )
    lines.extend(
        [f"- {item}" for item in report.get("cutover_blocking_items") or []]
        or ["- Cutover blokaji yok"]
    )
    data_quality = report.get("data_quality") if isinstance(report.get("data_quality"), dict) else {}
    lines.extend(
        [
            "",
            "Data Quality:",
            f"- Active Restaurants Missing Identity: {data_quality.get('active_restaurants_missing_identity', '-')}",
            f"- Active Personnel Missing Identity: {data_quality.get('active_personnel_missing_identity', '-')}",
            f"- Duplicate Restaurant Keys: {data_quality.get('duplicate_restaurant_keys', '-')}",
            f"- Duplicate Person Codes: {data_quality.get('duplicate_person_codes', '-')}",
            f"- Duplicate Auth Emails: {data_quality.get('duplicate_auth_emails', '-')}",
        ]
    )
    relation_health = report.get("relation_health") if isinstance(report.get("relation_health"), dict) else {}
    lines.extend(
        [
            "",
            "Relation Health:",
            f"- Personnel -> Restaurant Orphans: {relation_health.get('personnel_restaurant_orphans', '-')}",
            f"- Attendance -> Restaurant Orphans: {relation_health.get('attendance_restaurant_orphans', '-')}",
            f"- Attendance -> Planned Personnel Orphans: {relation_health.get('attendance_planned_personnel_orphans', '-')}",
            f"- Attendance -> Actual Personnel Orphans: {relation_health.get('attendance_actual_personnel_orphans', '-')}",
            f"- Deduction -> Personnel Orphans: {relation_health.get('deduction_personnel_orphans', '-')}",
            f"- Equipment -> Personnel Orphans: {relation_health.get('equipment_personnel_orphans', '-')}",
            f"- Box Return -> Personnel Orphans: {relation_health.get('box_return_personnel_orphans', '-')}",
        ]
    )
    lines.extend(["", f"Recommended Next Step: {report['recommended_next_step']}"])
    lines.append(f"Cutover Next Step: {report.get('cutover_recommended_next_step') or '-'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect the target PostgreSQL schema before Cat Kapinda CRM v2 pilot deploy."
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL URL to inspect. Defaults to CK_V2_DATABASE_URL or DATABASE_URL.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of plain text.",
    )
    args = parser.parse_args()

    try:
        database_url = resolve_database_url(args.database_url)
        report = build_database_preflight_report(database_url=database_url)
    except Exception as exc:
        payload = {
            "passed": False,
            "summary": "Veritabani preflight basarisiz.",
            "blocking_items": [str(exc)],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("Cat Kapinda CRM v2 Database Preflight")
            print("Passed: False")
            print("Summary: Veritabani preflight basarisiz.")
            print(f"Blocking Items: {exc}")
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_report_text(report), end="")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
