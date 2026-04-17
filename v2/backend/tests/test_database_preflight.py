from pathlib import Path
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


class FakeConnection:
    def __init__(self, present_tables: set[str], row_counts: dict[str, int]):
        self.present_tables = present_tables
        self.row_counts = row_counts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple[str, ...] | None = None):
        normalized = " ".join(query.split())
        if normalized == "SELECT to_regclass(%s) AS table_name":
            assert params is not None
            table_name = params[0]
            return FakeCursor({"table_name": table_name if table_name in self.present_tables else None})

        if normalized.startswith("SELECT COUNT(*) AS count FROM "):
            table_name = normalized.removeprefix("SELECT COUNT(*) AS count FROM ").strip()
            return FakeCursor({"count": self.row_counts.get(table_name, 0)})

        raise AssertionError(f"Beklenmeyen sorgu: {query}")


def connect_factory(present_tables: set[str], row_counts: dict[str, int]):
    def _connect(*args, **kwargs):
        return FakeConnection(present_tables=present_tables, row_counts=row_counts)

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
    )

    assert report["passed"] is True
    assert report["blocking_items"] == []
    assert report["database_url_masked"] == "postgresql://user:***@db.example.com:5432/postgres?sslmode=require"
    assert any("bootstrap" in item.lower() for item in report["warnings"])


def test_build_database_preflight_report_blocks_when_required_table_is_missing():
    present_tables = {name for name, _ in database_preflight.REQUIRED_TABLES if name != "daily_entries"}
    report = database_preflight.build_database_preflight_report(
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        connect_fn=connect_factory(present_tables, {"restaurants": 10, "personnel": 22}),
    )

    assert report["passed"] is False
    assert "`daily_entries` tablosu eksik." in report["blocking_items"]
    assert "eksikler" in report["summary"].lower()


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
    )

    assert report["passed"] is True
    assert any("canli PostgreSQL" in item for item in report["warnings"])


def test_build_database_preflight_report_rejects_placeholder_database_url():
    with pytest.raises(ValueError, match="gercek bir deger"):
        database_preflight.build_database_preflight_report(
            database_url="<mevcut-postgresql-url>",
            connect_fn=connect_factory(set(), {}),
        )
