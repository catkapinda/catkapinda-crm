import sqlite3

from app.core import bootstrap
from app.core.config import settings


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.executed: list[str] = []
        self.params: list[tuple | None] = []
        self.committed = False

    def execute(self, sql: str, params=None):
        self.executed.append(sql.strip())
        self.params.append(tuple(params) if params is not None else None)
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT * FROM auth_users"):
            return FakeResult(None)
        return FakeResult(None)

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_runtime_bootstrap_executes_auth_schema_sql(monkeypatch):
    fake_conn = FakeConnection()
    bootstrap.reset_runtime_bootstrap_state()
    monkeypatch.setattr(settings, "database_url", "postgresql://pilot")
    monkeypatch.setattr("app.core.bootstrap.psycopg.connect", lambda *args, **kwargs: fake_conn)
    mobile_sync_called = {"value": False}
    monkeypatch.setattr(
        "app.core.bootstrap.sync_mobile_auth_users",
        lambda conn: mobile_sync_called.__setitem__("value", True),
    )

    bootstrap.ensure_runtime_bootstrap()

    state = bootstrap.get_runtime_bootstrap_state()
    assert state["ok"] is True
    assert fake_conn.committed is True
    assert mobile_sync_called["value"] is True
    assert any("CREATE TABLE IF NOT EXISTS auth_users" in sql for sql in fake_conn.executed)
    assert any("CREATE TABLE IF NOT EXISTS auth_phone_codes" in sql for sql in fake_conn.executed)
    assert any("INSERT INTO auth_users" in sql for sql in fake_conn.executed)


def test_runtime_bootstrap_marks_failure_when_connection_breaks(monkeypatch):
    bootstrap.reset_runtime_bootstrap_state()
    monkeypatch.setattr(settings, "database_url", "postgresql://pilot")

    def raise_connect(*args, **kwargs):
        raise RuntimeError("db offline")

    monkeypatch.setattr("app.core.bootstrap.psycopg.connect", raise_connect)

    bootstrap.ensure_runtime_bootstrap()

    state = bootstrap.get_runtime_bootstrap_state()
    assert state["ok"] is False
    assert "db offline" in str(state["detail"])


def test_runtime_bootstrap_can_use_local_sqlite_fallback(monkeypatch, tmp_path):
    sqlite_path = tmp_path / "catkapinda_crm.db"
    with sqlite3.connect(sqlite_path) as raw_conn:
        raw_conn.row_factory = sqlite3.Row
        raw_conn.execute(
            """
            CREATE TABLE personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                phone TEXT
            )
            """
        )
        raw_conn.execute(
            """
            CREATE TABLE daily_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT,
                restaurant_id INTEGER,
                planned_personnel_id INTEGER,
                actual_personnel_id INTEGER,
                status TEXT,
                worked_hours REAL,
                package_count REAL,
                notes TEXT
            )
            """
        )
        raw_conn.execute(
            """
            CREATE TABLE restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT,
                branch TEXT,
                pricing_model TEXT,
                active INTEGER DEFAULT 1
            )
            """
        )
        raw_conn.execute(
            """
            CREATE TABLE deductions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personnel_id INTEGER,
                deduction_date TEXT,
                deduction_type TEXT,
                amount REAL,
                notes TEXT
            )
            """
        )
        raw_conn.execute(
            """
            CREATE TABLE courier_equipment_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personnel_id INTEGER,
                issue_date TEXT,
                item_name TEXT,
                quantity REAL,
                unit_cost REAL,
                unit_sale_price REAL,
                installment_count INTEGER,
                sale_type TEXT,
                notes TEXT
            )
            """
        )
        raw_conn.commit()

    bootstrap.reset_runtime_bootstrap_state()
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "local_sqlite_fallback_enabled", True)
    monkeypatch.setattr(settings, "local_sqlite_path", str(sqlite_path))

    bootstrap.ensure_runtime_bootstrap()

    state = bootstrap.get_runtime_bootstrap_state()
    assert state["ok"] is True
    assert "local sqlite fallback" in str(state["detail"])

    with sqlite3.connect(sqlite_path) as raw_conn:
        auth_user_count = raw_conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
        phone_code_table = raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'auth_phone_codes'"
        ).fetchone()
        audit_table = raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'audit_logs'"
        ).fetchone()
        role_history_table = raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'personnel_role_history'"
        ).fetchone()
        vehicle_history_table = raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'personnel_vehicle_history'"
        ).fetchone()
        sales_table = raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sales_leads'"
        ).fetchone()
        daily_entry_cols = {row[1] for row in raw_conn.execute("PRAGMA table_info(daily_entries)").fetchall()}
        personnel_cols = {row[1] for row in raw_conn.execute("PRAGMA table_info(personnel)").fetchall()}
        restaurant_cols = {row[1] for row in raw_conn.execute("PRAGMA table_info(restaurants)").fetchall()}
        deduction_cols = {row[1] for row in raw_conn.execute("PRAGMA table_info(deductions)").fetchall()}
        equipment_cols = {row[1] for row in raw_conn.execute("PRAGMA table_info(courier_equipment_issues)").fetchall()}

    assert auth_user_count == 3
    assert phone_code_table is not None
    assert audit_table is not None
    assert role_history_table is not None
    assert vehicle_history_table is not None
    assert sales_table is not None
    assert {"monthly_invoice_amount", "absence_reason", "coverage_type"} <= daily_entry_cols
    assert {"motor_purchase", "address"} <= personnel_cols
    assert {"company_title", "address"} <= restaurant_cols
    assert {"auto_source_key"} <= deduction_cols
    assert {"vat_rate", "auto_source_key"} <= equipment_cols
