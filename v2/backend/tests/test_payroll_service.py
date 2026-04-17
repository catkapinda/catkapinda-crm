import sqlite3

from app.core.database import CompatConnection
from app.services.payroll import build_payroll_dashboard, build_payroll_document_file


def test_build_payroll_dashboard_supports_local_sqlite_without_streamlit():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            person_code TEXT,
            role TEXT,
            status TEXT,
            cost_model TEXT,
            monthly_fixed_cost REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL
        );
        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            deduction_date TEXT,
            deduction_type TEXT,
            amount REAL
        );
        """
    )
    raw_conn.execute(
        """
        INSERT INTO personnel (id, full_name, person_code, role, status, cost_model, monthly_fixed_cost)
        VALUES
            (1, 'Mert Kurtuluş', 'CK-K01', 'Kurye', 'Aktif', 'fixed_monthly', 32000),
            (2, 'Ebru Aslan', 'CK-O01', 'Operasyon', 'Aktif', 'standard_courier', 28000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (id, brand, branch)
        VALUES (10, 'Burger@', 'Kavacık')
        """
    )
    raw_conn.execute(
        """
        INSERT INTO daily_entries (
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            worked_hours,
            package_count
        )
        VALUES
            ('2026-04-10', 10, 1, 1, 9, 24),
            ('2026-04-11', 10, 2, 2, 8, 18)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (1, '2026-04-15', 'Avans', 1500)
        """
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")

    payload = build_payroll_dashboard(conn)

    assert payload.selected_month == "2026-04"
    assert payload.summary is not None
    assert payload.summary.personnel_count == 2
    assert payload.summary.total_deductions == 1500.0
    assert payload.entries[0].personnel in {"Mert Kurtuluş", "Ebru Aslan"}
    assert payload.cost_model_breakdown
    assert payload.top_personnel


def test_build_payroll_document_file_supports_local_sqlite():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            person_code TEXT,
            role TEXT,
            status TEXT,
            cost_model TEXT,
            monthly_fixed_cost REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL
        );
        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            deduction_date TEXT,
            deduction_type TEXT,
            amount REAL
        );
        """
    )
    raw_conn.execute(
        """
        INSERT INTO personnel (id, full_name, person_code, role, status, cost_model, monthly_fixed_cost)
        VALUES (1, 'Mert Kurtuluş', 'CK-K01', 'Kurye', 'Aktif', 'fixed_monthly', 32000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (id, brand, branch)
        VALUES (10, 'Burger@', 'Kavacık')
        """
    )
    raw_conn.execute(
        """
        INSERT INTO daily_entries (
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            worked_hours,
            package_count
        )
        VALUES ('2026-04-10', 10, 1, 1, 9, 24)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (1, '2026-04-15', 'Avans', 1500)
        """
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")

    file_name, file_bytes = build_payroll_document_file(
        conn,
        selected_month="2026-04",
        personnel_id=1,
    )

    assert file_name == "hakedis_Mert_Kurtulu_2026-04.pdf"
    assert file_bytes.startswith(b"%PDF")
