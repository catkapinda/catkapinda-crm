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
            monthly_fixed_cost REAL,
            start_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL
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
            (2, 'Ebru Aslan', 'CK-K02', 'Kurye', 'Aktif', 'fixed_kurye', 0)
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
    raw_conn.execute(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (2, '2026-05-15', 'Zimmet Taksiti', 3200)
        """
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")

    payload = build_payroll_dashboard(conn)

    assert payload.selected_month == "2026-04"
    assert payload.month_options == ["2026-05", "2026-04"]
    assert payload.summary is not None
    assert payload.summary.personnel_count == 2
    assert payload.summary.gross_payroll == 34360.0
    assert payload.summary.total_deductions == 1500.0
    assert next(entry.gross_pay for entry in payload.entries if entry.personnel == "Ebru Aslan") == 2360.0
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
            monthly_fixed_cost REAL,
            start_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL
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


def test_payroll_dashboard_uses_monthly_threshold_for_courier_package_bonus():
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
            monthly_fixed_cost REAL,
            start_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL
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
        VALUES (1, 'Destek Kurye', 'CK-K03', 'Kurye', 'Aktif', 'standard_courier', 0)
        """
    )
    raw_conn.executemany(
        "INSERT INTO restaurants (id, brand, branch) VALUES (?, ?, ?)",
        [
            (10, "Burger@", "Kavacık"),
            (11, "SushiCo", "Beyoğlu"),
            (12, "Quick China", "Ataşehir"),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO daily_entries (
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            worked_hours,
            package_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-04-10", 10, 1, 1, 100, 385),
            ("2026-04-11", 11, 1, 1, 10, 40),
            ("2026-04-12", 12, 1, 1, 5, 4),
        ],
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.summary.gross_payroll == 39475.0
    assert payload.entries[0].gross_pay == 39475.0


def test_payroll_dashboard_uses_fixed_pay_for_sushi_inn_and_sc_petshop():
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
            monthly_fixed_cost REAL,
            start_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL
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
        VALUES (1, 'Sabit Kurye', 'CK-K04', 'Kurye', 'Aktif', 'standard_courier', 0)
        """
    )
    raw_conn.executemany(
        "INSERT INTO restaurants (id, brand, branch) VALUES (?, ?, ?)",
        [
            (10, "Sushi Inn", "Merkez"),
            (11, "SC Petshop", "Merkez"),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO daily_entries (
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            worked_hours,
            package_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-04-10", 10, 1, 1, 200, 500),
            ("2026-04-11", 11, 1, 1, 10, 25),
        ],
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.summary.gross_payroll == 73600.0
    assert payload.entries[0].gross_pay == 73600.0


def test_payroll_dashboard_prorates_company_motor_rental_deduction():
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
            monthly_fixed_cost REAL,
            start_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL
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
        INSERT INTO personnel (
            id,
            full_name,
            person_code,
            role,
            status,
            cost_model,
            monthly_fixed_cost,
            start_date,
            vehicle_type,
            motor_rental,
            motor_purchase,
            motor_rental_monthly_amount
        )
        VALUES (1, 'Kiralık Motor Kurye', 'CK-M01', 'Kurye', 'Aktif', 'standard_courier', 0, '2026-04-21', 'Çat Kapında', 'Evet', 'Hayır', 13000)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Burger@', 'Kavacık')")
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
        VALUES ('2026-04-22', 10, 1, 1, 10, 0)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (1, '2026-04-25', 'Motor Kirası', 1000)
        """
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.entries[0].gross_pay == 2500.0
    assert round(payload.entries[0].total_deductions, 2) == 4333.33
    assert round(payload.summary.total_deductions, 2) == 4333.33
