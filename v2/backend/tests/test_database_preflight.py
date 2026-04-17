from pathlib import Path
from datetime import date
import sys

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import database_preflight  # noqa: E402


class FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeRowsCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(
        self,
        present_tables: set[str],
        row_counts: dict[str, int],
        table_columns: dict[str, list[str]],
        table_privileges: dict[str, dict[str, bool]],
        table_sequences: dict[str, str | None],
        sequence_privileges: dict[str, dict[str, bool]],
        data_health_counts: dict[str, int],
        data_quality_counts: dict[str, int],
        latest_dates: dict[str, str | None],
        relation_health_counts: dict[str, int],
        schema_create_allowed: bool,
    ):
        self.present_tables = present_tables
        self.row_counts = row_counts
        self.table_columns = table_columns
        self.table_privileges = table_privileges
        self.table_sequences = table_sequences
        self.sequence_privileges = sequence_privileges
        self.data_health_counts = data_health_counts
        self.data_quality_counts = data_quality_counts
        self.latest_dates = latest_dates
        self.relation_health_counts = relation_health_counts
        self.schema_create_allowed = schema_create_allowed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple[object, ...] | None = None):
        normalized = " ".join(query.split())
        if normalized == "SELECT current_schema() AS schema_name":
            return FakeCursor({"schema_name": "public"})

        if normalized == "SELECT has_schema_privilege(current_user, %s, 'CREATE') AS allowed":
            assert params is not None
            return FakeCursor({"allowed": self.schema_create_allowed})

        if normalized == "SELECT to_regclass(%s) AS table_name":
            assert params is not None
            table_name = params[0]
            return FakeCursor({"table_name": table_name if table_name in self.present_tables else None})

        if normalized == (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s AND table_schema = ANY(current_schemas(false)) "
            "ORDER BY ordinal_position"
        ):
            assert params is not None
            table_name = params[0]
            return FakeRowsCursor(
                [{"column_name": column_name} for column_name in self.table_columns.get(table_name, [])]
            )

        if normalized == "SELECT has_table_privilege(current_user, %s, %s) AS allowed":
            assert params is not None
            table_name = str(params[0])
            privilege = str(params[1]).upper()
            return FakeCursor({"allowed": self.table_privileges.get(table_name, {}).get(privilege, False)})

        if normalized == "SELECT pg_get_serial_sequence(%s, 'id') AS sequence_name":
            assert params is not None
            table_name = str(params[0])
            return FakeCursor({"sequence_name": self.table_sequences.get(table_name)})

        if normalized == "SELECT has_sequence_privilege(current_user, %s, %s) AS allowed":
            assert params is not None
            sequence_name = str(params[0])
            privilege = str(params[1]).upper()
            return FakeCursor({"allowed": self.sequence_privileges.get(sequence_name, {}).get(privilege, False)})

        if normalized == (
            "SELECT last_value FROM pg_sequences "
            "WHERE schemaname = %s AND sequencename = %s"
        ):
            assert params is not None
            schema_name = str(params[0])
            sequence_name = str(params[1])
            full_name = f"{schema_name}.{sequence_name}"
            row = {
                "last_value": self.sequence_privileges.get(full_name, {}).get("_LAST_VALUE")
            }
            return FakeCursor(row)

        if normalized == "SELECT COUNT(*) AS count FROM restaurants WHERE COALESCE(active, TRUE) = TRUE":
            return FakeCursor({"count": self.data_health_counts.get("active_restaurants", 0)})

        if normalized == "SELECT COUNT(*) AS count FROM personnel WHERE COALESCE(status, '') = 'Aktif'":
            return FakeCursor({"count": self.data_health_counts.get("active_personnel", 0)})

        if normalized == (
            "SELECT COUNT(*) AS count FROM personnel "
            "WHERE COALESCE(status, '') = 'Aktif' AND assigned_restaurant_id IS NOT NULL"
        ):
            return FakeCursor({"count": self.data_health_counts.get("assigned_personnel", 0)})

        if normalized == "SELECT MAX(entry_date) AS latest_value FROM daily_entries":
            return FakeCursor({"latest_value": self.latest_dates.get("daily_entries")})

        if normalized == "SELECT MAX(deduction_date) AS latest_value FROM deductions":
            return FakeCursor({"latest_value": self.latest_dates.get("deductions")})

        if normalized == "SELECT MAX(purchase_date) AS latest_value FROM inventory_purchases":
            return FakeCursor({"latest_value": self.latest_dates.get("inventory_purchases")})

        if normalized == "SELECT MAX(updated_at) AS latest_value FROM sales_leads":
            return FakeCursor({"latest_value": self.latest_dates.get("sales_leads")})

        if normalized == "SELECT MAX(issue_date) AS latest_value FROM courier_equipment_issues":
            return FakeCursor({"latest_value": self.latest_dates.get("courier_equipment_issues")})

        quality_query_map = {
            (
                "SELECT COUNT(*) AS count FROM restaurants "
                "WHERE COALESCE(active, TRUE) = TRUE "
                "AND ( NULLIF(BTRIM(COALESCE(brand, '')), '') IS NULL "
                "OR NULLIF(BTRIM(COALESCE(branch, '')), '') IS NULL )"
            ): "active_restaurants_missing_identity",
            (
                "SELECT COUNT(*) AS count FROM personnel "
                "WHERE COALESCE(status, '') = 'Aktif' "
                "AND ( NULLIF(BTRIM(COALESCE(person_code, '')), '') IS NULL "
                "OR NULLIF(BTRIM(COALESCE(full_name, '')), '') IS NULL )"
            ): "active_personnel_missing_identity",
            (
                "SELECT COUNT(*) AS count FROM ( "
                "SELECT LOWER(BTRIM(COALESCE(brand, ''))) AS brand_key, "
                "LOWER(BTRIM(COALESCE(branch, ''))) AS branch_key "
                "FROM restaurants "
                "WHERE COALESCE(active, TRUE) = TRUE "
                "AND NULLIF(BTRIM(COALESCE(brand, '')), '') IS NOT NULL "
                "AND NULLIF(BTRIM(COALESCE(branch, '')), '') IS NOT NULL "
                "GROUP BY 1, 2 HAVING COUNT(*) > 1 "
                ") duplicates"
            ): "duplicate_restaurant_keys",
            (
                "SELECT COUNT(*) AS count FROM ( "
                "SELECT LOWER(BTRIM(COALESCE(person_code, ''))) AS person_code_key "
                "FROM personnel "
                "WHERE NULLIF(BTRIM(COALESCE(person_code, '')), '') IS NOT NULL "
                "GROUP BY 1 HAVING COUNT(*) > 1 "
                ") duplicates"
            ): "duplicate_person_codes",
            (
                "SELECT COUNT(*) AS count FROM ( "
                "SELECT LOWER(BTRIM(COALESCE(email, ''))) AS email_key "
                "FROM auth_users "
                "WHERE NULLIF(BTRIM(COALESCE(email, '')), '') IS NOT NULL "
                "GROUP BY 1 HAVING COUNT(*) > 1 "
                ") duplicates"
            ): "duplicate_auth_emails",
        }
        if normalized in quality_query_map:
            return FakeCursor({"count": self.data_quality_counts.get(quality_query_map[normalized], 0)})

        relation_query_map = {
            (
                "SELECT COUNT(*) AS count FROM personnel p LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id "
                "WHERE p.assigned_restaurant_id IS NOT NULL AND r.id IS NULL"
            ): "personnel_restaurant_orphans",
            (
                "SELECT COUNT(*) AS count FROM daily_entries d LEFT JOIN restaurants r ON r.id = d.restaurant_id "
                "WHERE d.restaurant_id IS NOT NULL AND r.id IS NULL"
            ): "attendance_restaurant_orphans",
            (
                "SELECT COUNT(*) AS count FROM daily_entries d LEFT JOIN personnel p ON p.id = d.planned_personnel_id "
                "WHERE d.planned_personnel_id IS NOT NULL AND p.id IS NULL"
            ): "attendance_planned_personnel_orphans",
            (
                "SELECT COUNT(*) AS count FROM daily_entries d LEFT JOIN personnel p ON p.id = d.actual_personnel_id "
                "WHERE d.actual_personnel_id IS NOT NULL AND p.id IS NULL"
            ): "attendance_actual_personnel_orphans",
            (
                "SELECT COUNT(*) AS count FROM deductions d LEFT JOIN personnel p ON p.id = d.personnel_id "
                "WHERE d.personnel_id IS NOT NULL AND p.id IS NULL"
            ): "deduction_personnel_orphans",
            (
                "SELECT COUNT(*) AS count FROM courier_equipment_issues i LEFT JOIN personnel p ON p.id = i.personnel_id "
                "WHERE i.personnel_id IS NOT NULL AND p.id IS NULL"
            ): "equipment_personnel_orphans",
            (
                "SELECT COUNT(*) AS count FROM box_returns b LEFT JOIN personnel p ON p.id = b.personnel_id "
                "WHERE b.personnel_id IS NOT NULL AND p.id IS NULL"
            ): "box_return_personnel_orphans",
        }
        if normalized in relation_query_map:
            return FakeCursor({"count": self.relation_health_counts.get(relation_query_map[normalized], 0)})

        if normalized.startswith("SELECT COUNT(*) AS count FROM "):
            table_name = normalized.removeprefix("SELECT COUNT(*) AS count FROM ").strip()
            return FakeCursor({"count": self.row_counts.get(table_name, 0)})

        if normalized.startswith("SELECT COALESCE(MAX(id), 0) AS max_id FROM "):
            table_name = normalized.removeprefix("SELECT COALESCE(MAX(id), 0) AS max_id FROM ").strip()
            return FakeCursor({"max_id": self.row_counts.get(table_name, 0)})

        raise AssertionError(f"Beklenmeyen sorgu: {query}")


def _default_columns_for_tables(present_tables: set[str]) -> dict[str, list[str]]:
    all_columns = {
        **database_preflight.REQUIRED_CRITICAL_COLUMNS,
        **database_preflight.BOOTSTRAP_CRITICAL_COLUMNS,
    }
    return {
        table_name: list(all_columns.get(table_name, ()))
        for table_name in present_tables
    }


def connect_factory(
    present_tables: set[str],
    row_counts: dict[str, int],
    table_columns: dict[str, list[str]] | None = None,
    table_privileges: dict[str, dict[str, bool]] | None = None,
    table_sequences: dict[str, str | None] | None = None,
    sequence_privileges: dict[str, dict[str, bool]] | None = None,
    data_health_counts: dict[str, int] | None = None,
    data_quality_counts: dict[str, int] | None = None,
    latest_dates: dict[str, str | None] | None = None,
    relation_health_counts: dict[str, int] | None = None,
    schema_create_allowed: bool = True,
):
    resolved_columns = table_columns or _default_columns_for_tables(present_tables)
    resolved_privileges = table_privileges or {
        table_name: {
            privilege: True
            for privilege in database_preflight.WRITE_REQUIRED_PRIVILEGES
        }
        for table_name in present_tables
    }
    resolved_sequences = table_sequences or {
        table_name: f"public.{table_name}_id_seq"
        for table_name in present_tables
        if "id" in resolved_columns.get(table_name, [])
    }
    resolved_sequence_privileges = sequence_privileges or {
        sequence_name: {
            privilege: True
            for privilege in database_preflight.SEQUENCE_REQUIRED_PRIVILEGES
        }
        for sequence_name in resolved_sequences.values()
        if sequence_name
    }
    for table_name, sequence_name in resolved_sequences.items():
        if sequence_name:
            resolved_sequence_privileges.setdefault(sequence_name, {})
            resolved_sequence_privileges[sequence_name].setdefault("_LAST_VALUE", row_counts.get(table_name, 0))
    resolved_health_counts = data_health_counts or {
        "active_restaurants": row_counts.get("restaurants", 0),
        "active_personnel": row_counts.get("personnel", 0),
        "assigned_personnel": row_counts.get("personnel", 0),
    }
    resolved_quality_counts = data_quality_counts or {
        "active_restaurants_missing_identity": 0,
        "active_personnel_missing_identity": 0,
        "duplicate_restaurant_keys": 0,
        "duplicate_person_codes": 0,
        "duplicate_auth_emails": 0,
    }
    resolved_latest_dates = latest_dates or {
        "daily_entries": "2026-04-17" if row_counts.get("daily_entries", 0) else None,
        "deductions": "2026-04-17" if row_counts.get("deductions", 0) else None,
        "inventory_purchases": "2026-04-17" if row_counts.get("inventory_purchases", 0) else None,
        "sales_leads": "2026-04-17" if row_counts.get("sales_leads", 0) else None,
        "courier_equipment_issues": "2026-04-17" if row_counts.get("courier_equipment_issues", 0) else None,
    }
    resolved_relation_health = relation_health_counts or {
        "personnel_restaurant_orphans": 0,
        "attendance_restaurant_orphans": 0,
        "attendance_planned_personnel_orphans": 0,
        "attendance_actual_personnel_orphans": 0,
        "deduction_personnel_orphans": 0,
        "equipment_personnel_orphans": 0,
        "box_return_personnel_orphans": 0,
    }

    def _connect(*args, **kwargs):
        return FakeConnection(
            present_tables=present_tables,
            row_counts=row_counts,
            table_columns=resolved_columns,
            table_privileges=resolved_privileges,
            table_sequences=resolved_sequences,
            sequence_privileges=resolved_sequence_privileges,
            data_health_counts=resolved_health_counts,
            data_quality_counts=resolved_quality_counts,
            latest_dates=resolved_latest_dates,
            relation_health_counts=resolved_relation_health,
            schema_create_allowed=schema_create_allowed,
        )

    return _connect


def test_build_database_preflight_report_passes_when_required_tables_exist():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES} | {
        "auth_users",
        "auth_sessions",
        "audit_logs",
    }
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is True
    assert report["cutover_ready"] is True
    assert report["blocking_items"] == []
    assert report["database_url_masked"] == "postgresql://user:***@db.example.com:5432/postgres?sslmode=require"
    assert all(not entry["missing_columns"] for entry in report["required_tables"])
    assert report["data_health"]["latest_attendance_date"] == "2026-04-17"
    assert report["relation_health"]["personnel_restaurant_orphans"] == 0
    assert any("bootstrap" in item.lower() for item in report["warnings"])


def test_build_database_preflight_report_blocks_when_required_table_is_missing():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES if name != "daily_entries"}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(present_tables, {"restaurants": 10, "personnel": 22}),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert "`daily_entries` tablosu eksik." in report["blocking_items"]
    assert "eksikler" in report["summary"].lower()


def test_build_database_preflight_report_blocks_when_bootstrap_tables_are_missing_without_schema_create():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            schema_create_allowed=False,
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert report["schema_name"] == "public"
    assert report["schema_create_allowed"] is False
    assert (
        "Bootstrap tablolarinin bir kismi eksik ve `public` semasinda CREATE yetkisi yok."
        in report["blocking_items"]
    )


def test_build_database_preflight_report_blocks_when_required_table_has_missing_columns():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    table_columns = _default_columns_for_tables(present_tables)
    table_columns["sales_leads"] = [
        column
        for column in table_columns["sales_leads"]
        if column not in {"pricing_model_hint", "updated_at"}
    ]
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            table_columns=table_columns,
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert (
        "`sales_leads` tablosunda eksik kritik kolonlar var: pricing_model_hint, updated_at."
        in report["blocking_items"]
    )
    sales_entry = next(entry for entry in report["required_tables"] if entry["table"] == "sales_leads")
    assert sales_entry["missing_columns"] == ["pricing_model_hint", "updated_at"]


def test_build_database_preflight_report_blocks_when_required_table_has_missing_privileges():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    table_privileges = {
        table_name: {
            privilege: True
            for privilege in database_preflight.WRITE_REQUIRED_PRIVILEGES
        }
        for table_name in present_tables
    }
    table_privileges["deductions"]["UPDATE"] = False
    table_privileges["deductions"]["DELETE"] = False
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            table_privileges=table_privileges,
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert (
        "`deductions` tablosunda eksik tablo yetkileri var: UPDATE, DELETE."
        in report["blocking_items"]
    )
    deduction_entry = next(entry for entry in report["required_tables"] if entry["table"] == "deductions")
    assert deduction_entry["missing_privileges"] == ["UPDATE", "DELETE"]


def test_build_database_preflight_report_blocks_when_auth_tables_have_missing_privileges():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES} | {
        "auth_users",
        "auth_sessions",
        "audit_logs",
    }
    table_privileges = {
        table_name: {
            privilege: True
            for privilege in database_preflight.WRITE_REQUIRED_PRIVILEGES
        }
        for table_name in present_tables
    }
    table_privileges["auth_sessions"]["INSERT"] = False
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            table_privileges=table_privileges,
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert (
        "`auth_sessions` tablosunda eksik tablo yetkileri var: INSERT."
        in report["blocking_items"]
    )


def test_build_database_preflight_report_blocks_when_required_table_has_missing_sequence_privileges():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    table_sequences = {
        table_name: f"public.{table_name}_id_seq"
        for table_name in present_tables
    }
    sequence_privileges = {
        sequence_name: {
            privilege: True
            for privilege in database_preflight.SEQUENCE_REQUIRED_PRIVILEGES
        }
        for sequence_name in table_sequences.values()
    }
    sequence_privileges["public.sales_leads_id_seq"]["USAGE"] = False
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            table_sequences=table_sequences,
            sequence_privileges=sequence_privileges,
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert (
        "`sales_leads` tablosunun sequence yetkileri eksik: public.sales_leads_id_seq (USAGE)."
        in report["blocking_items"]
    )
    sales_entry = next(entry for entry in report["required_tables"] if entry["table"] == "sales_leads")
    assert sales_entry["missing_sequence_privileges"] == ["USAGE"]


def test_build_database_preflight_report_blocks_when_sequence_is_behind_max_id():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    table_sequences = {
        table_name: f"public.{table_name}_id_seq"
        for table_name in present_tables
    }
    sequence_privileges = {
        sequence_name: {
            privilege: True
            for privilege in database_preflight.SEQUENCE_REQUIRED_PRIVILEGES
        }
        for sequence_name in table_sequences.values()
    }
    sequence_privileges["public.inventory_purchases_id_seq"]["_LAST_VALUE"] = 3
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            table_sequences=table_sequences,
            sequence_privileges=sequence_privileges,
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is False
    assert (
        "`inventory_purchases` tablosunun sequence degeri geride: "
        "public.inventory_purchases_id_seq (last_value=3, max_id=14)."
        in report["blocking_items"]
    )
    purchase_entry = next(entry for entry in report["required_tables"] if entry["table"] == "inventory_purchases")
    assert purchase_entry["sequence_out_of_sync"] is True


def test_build_database_preflight_report_warns_when_core_tables_are_empty():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 0,
                "personnel": 0,
                "daily_entries": 0,
                "deductions": 4,
                "inventory_purchases": 1,
                "sales_leads": 1,
                "courier_equipment_issues": 1,
                "box_returns": 1,
            },
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is True
    assert any("canli PostgreSQL" in item for item in report["warnings"])


def test_build_database_preflight_report_marks_cutover_unready_when_attendance_is_stale():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            latest_dates={
                "daily_entries": "2026-01-15",
                "deductions": "2026-04-16",
                "inventory_purchases": "2026-04-14",
                "sales_leads": "2026-04-12",
                "courier_equipment_issues": "2026-04-11",
            },
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is True
    assert report["cutover_ready"] is False
    assert any("Gunluk puantaj verisi eski gorunuyor" in item for item in report["cutover_blocking_items"])
    assert report["cutover_recommended_next_step"].startswith("Canli domaine gecmeden once")


def test_build_database_preflight_report_marks_cutover_unready_when_data_quality_is_broken():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES} | {"auth_users"}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
                "auth_users": 6,
            },
            data_quality_counts={
                "active_restaurants_missing_identity": 1,
                "active_personnel_missing_identity": 2,
                "duplicate_restaurant_keys": 1,
                "duplicate_person_codes": 2,
                "duplicate_auth_emails": 1,
            },
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is True
    assert report["cutover_ready"] is False
    assert report["data_quality"]["duplicate_person_codes"] == 2
    assert "Aktif restoran kartlarinda bos marka/sube alanlari var." in report["cutover_blocking_items"]
    assert (
        "Aktif personel kartlarinda bos personel kodu veya ad soyad alanlari var."
        in report["cutover_blocking_items"]
    )
    assert (
        "Ayni marka/sube kombinasyonunda 1 cakisan restoran kaydi var."
        in report["cutover_blocking_items"]
    )
    assert "2 personel kodu birden fazla kartta tekrar ediyor." in report["cutover_blocking_items"]
    assert "1 auth e-posta degeri birden fazla kullanicida tekrar ediyor." in report["cutover_blocking_items"]


def test_build_database_preflight_report_marks_cutover_unready_when_relation_health_is_broken():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(
            present_tables,
            {
                "restaurants": 12,
                "personnel": 54,
                "daily_entries": 3200,
                "deductions": 88,
                "inventory_purchases": 14,
                "sales_leads": 7,
                "courier_equipment_issues": 9,
                "box_returns": 2,
            },
            relation_health_counts={
                "personnel_restaurant_orphans": 2,
                "attendance_restaurant_orphans": 0,
                "attendance_planned_personnel_orphans": 1,
                "attendance_actual_personnel_orphans": 0,
                "deduction_personnel_orphans": 0,
                "equipment_personnel_orphans": 0,
                "box_return_personnel_orphans": 0,
            },
        ),
        reference_date=date(2026, 4, 17),
    )

    assert report["passed"] is True
    assert report["cutover_ready"] is False
    assert "Personel -> restoran iliskisinde 2 kopuk kayit var." in report["cutover_blocking_items"]
    assert "Puantaj -> planli personel iliskisinde 1 kopuk kayit var." in report["cutover_blocking_items"]


def test_build_database_preflight_report_rejects_placeholder_database_url():
    with pytest.raises(ValueError, match="gercek bir deger"):
        database_preflight.build_database_preflight_report(
            database_url="<mevcut-postgresql-url>",
            connect_fn=connect_factory(set(), {}),
        )
