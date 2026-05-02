import sqlite3

from app.core.database import CompatConnection
from app.services.payroll import (
    _build_payroll_document_html,
    _build_local_payroll_document_payload,
    _calculate_payroll_tevkifat_breakdown,
    _format_number_pdf,
    build_payroll_dashboard,
    build_payroll_document_file,
)


def test_format_number_pdf_supports_zero_decimals():
    assert _format_number_pdf(366, 0) == "366"
    assert _format_number_pdf(1128.5, 1) == "1.128,5"


def test_calculate_payroll_tevkifat_breakdown_uses_invoice_total_threshold():
    above_threshold = _calculate_payroll_tevkifat_breakdown(12000)
    assert round(above_threshold.invoice_base_amount, 2) == 10000.0
    assert round(above_threshold.vat_amount, 2) == 2000.0
    assert round(above_threshold.tevkifat_amount, 2) == 400.0

    below_threshold = _calculate_payroll_tevkifat_breakdown(11999)
    assert round(below_threshold.invoice_base_amount, 2) == 9999.17
    assert round(below_threshold.vat_amount, 2) == 1999.83
    assert below_threshold.tevkifat_amount == 0.0


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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
    assert round(payload.summary.total_deductions, 2) == 2566.67
    assert round(payload.summary.total_tevkifat, 2) == 1066.67
    assert round(payload.summary.net_payment, 2) == 31793.33
    assert next(entry.gross_pay for entry in payload.entries if entry.personnel == "Ebru Aslan") == 2360.0
    assert payload.entries[0].personnel in {"Mert Kurtuluş", "Ebru Aslan"}
    assert payload.cost_model_breakdown
    assert payload.top_personnel


def test_payroll_dashboard_and_document_include_accounting_and_company_setup_deductions():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL,
            accounting_revenue REAL,
            accountant_cost REAL,
            company_setup_revenue REAL,
            company_setup_cost REAL
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
            id, full_name, person_code, role, status, cost_model, monthly_fixed_cost,
            accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost
        )
        VALUES (1, 'Recep Şahin', 'CK-TS01', 'Restoran Takım Şefi', 'Aktif', 'fixed_monthly', 20000, 2000, 1400, 3000, 1500)
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
        VALUES ('2026-04-10', 10, 1, 1, 9, 24)
        """
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")
    payload = build_payroll_dashboard(conn, selected_month="2026-04")

    assert len(payload.entries) == 1
    entry = payload.entries[0]
    assert round(entry.total_deductions, 2) == 5666.67
    assert round(entry.net_payment, 2) == 14333.33
    assert {item.label for item in entry.deduction_items} >= {
        "Muhasebe Kesintisi",
        "Şirket Açılışı Kesintisi",
        "Tevkifat",
    }
    assert any(item.label == "Muhasebe Kesintisi" and round(item.amount, 2) == 2000 for item in entry.deduction_items)
    assert any(item.label == "Şirket Açılışı Kesintisi" and round(item.amount, 2) == 3000 for item in entry.deduction_items)

    document_payload = _build_local_payroll_document_payload(
        conn,
        selected_month="2026-04",
        personnel_id=1,
    )
    assert round(document_payload.total_deductions, 2) == 5666.67
    assert round(document_payload.net_payment, 2) == 14333.33
    assert any(item[0] == "Muhasebe Kesintisi" and round(item[1], 2) == 2000 for item in document_payload.deduction_items)
    assert any(item[0] == "Şirket Açılışı Kesintisi" and round(item[1], 2) == 3000 for item in document_payload.deduction_items)


def test_build_payroll_document_file_supports_local_sqlite(monkeypatch):
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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

    monkeypatch.setattr(
        "app.services.payroll._render_payroll_document_pdf",
        lambda payload: b"%PDF-mock",
    )

    file_name, file_bytes = build_payroll_document_file(
        conn,
        selected_month="2026-04",
        personnel_id=1,
    )

    assert file_name == "hakedis_Mert_Kurtulu_2026-04.pdf"
    assert file_bytes.startswith(b"%PDF")


def test_build_payroll_document_html_renders_template_sections():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Neçirvan Bulgan', 'CK-K10', 'Kurye', 'Aktif', 'fixed_monthly', 32000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (id, brand, branch)
        VALUES (10, 'Quick China', 'Ataşehir')
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
        VALUES ('2026-03-10', 10, 1, 1, 9, 24)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (1, '2026-03-15', 'Avans', 1500)
        """
    )
    raw_conn.commit()

    payload = _build_local_payroll_document_payload(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-03",
        personnel_id=1,
    )
    html = _build_payroll_document_html(payload)

    assert "Kurye Hakediş Belgesi" in html
    assert "Kesinti Kalemleri" in html
    assert "Fatura Bilgisi" in html
    assert "Operasyon Özeti" in html
    assert "Hakediş Tutarı" in html
    assert "Brüt Kazanç" not in html
    assert "Neçirvan Bulgan" in html
    assert "Quick China - Ataşehir" in html


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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
    assert payload.summary.gross_payroll == 37350.0
    assert payload.entries[0].gross_pay == 37350.0


def test_payroll_dashboard_uses_fixed_pay_for_fixed_monthly_courier():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Sabit Kurye', 'CK-K04', 'Kurye', 'Aktif', 'fixed_monthly', 73600)
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


def test_payroll_dashboard_keeps_standard_courier_formula_on_fixed_monthly_restaurants():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Standart Kurye', 'CK-K05', 'Kurye', 'Aktif', 'standard_courier', 0)
        """
    )
    raw_conn.executemany(
        "INSERT INTO restaurants (id, brand, branch) VALUES (?, ?, ?)",
        [
            (10, "Sushi Inn", "Merkez"),
            (11, "Burger@", "Kavacık"),
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
            ("2026-04-10", 10, 1, 1, 20, 40),
            ("2026-04-11", 11, 1, 1, 10, 20),
        ],
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.summary.gross_payroll == 8700.0
    assert payload.entries[0].gross_pay == 8700.0


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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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


def test_payroll_dashboard_prorates_company_motor_rental_by_exit_date():
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
            exit_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
            exit_date,
            vehicle_type,
            motor_rental,
            motor_purchase,
            motor_rental_monthly_amount
        )
        VALUES (1, 'Çıkış Yapan Kurye', 'CK-M02', 'Kurye', 'Pasif', 'standard_courier', 0, '2026-01-01', '2026-04-10', 'Çat Kapında', 'Evet', 'Hayır', 13000)
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
        VALUES ('2026-04-05', 10, 1, 1, 10, 0)
        """
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.entries[0].gross_pay == 2500.0
    assert round(payload.entries[0].total_deductions, 2) == 4333.33
    assert round(payload.summary.total_deductions, 2) == 4333.33


def test_payroll_dashboard_adds_company_motor_purchase_installment():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
            motor_rental_monthly_amount,
            motor_purchase_start_date,
            motor_purchase_commitment_months,
            motor_purchase_sale_price,
            motor_purchase_monthly_deduction
        )
        VALUES (1, 'Satış Motor Kurye', 'CK-S01', 'Kurye', 'Aktif', 'standard_courier', 0, '2026-04-01', 'Çat Kapında', 'Hayır', 'Evet', 0, '2026-04-17', 12, 84000, 7000)
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
        VALUES ('2026-04-22', 10, 1, 1, 40, 0)
        """
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.entries[0].gross_pay == 10000.0
    assert payload.entries[0].total_deductions == 7000.0
    assert payload.entries[0].net_payment == 3000.0


def test_payroll_dashboard_exposes_tevkifat_for_invoice_totals_over_threshold():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Tevkifat Kurye', 'CK-T01', 'Kurye', 'Aktif', 'fixed_monthly', 12000)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'SushiCo', 'İdealistpark')")
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
        VALUES ('2026-04-12', 10, 1, 1, 10, 10)
        """
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert payload.summary is not None
    assert payload.entries[0].total_deductions == 400.0
    assert payload.entries[0].net_payment == 11600.0
    assert round(payload.entries[0].tevkifat_amount, 2) == 400.0
    assert round(payload.summary.total_tevkifat, 2) == 400.0


def test_payroll_dashboard_calculates_tevkifat_after_invoice_base_reducing_deductions_only():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Cihan Can Çimen', 'CK-BM01', 'Bölge Müdürü', 'Aktif', 'fixed_bolge_muduru', 117475)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Doğu Otomotiv', 'Merkez')")
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
            (f"2026-03-{day:02d}", 10, 1, 1, 10, 0)
            for day in range(1, 31)
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "2026-03-25", "Motor Kirası", 13540),
            (1, "2026-03-25", "Avans", 30000),
            (1, "2026-03-25", "Yakit", 4587.10),
        ],
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")
    payload = build_payroll_dashboard(conn, selected_month="2026-03")

    assert round(payload.entries[0].gross_pay, 2) == 125306.67
    assert round(payload.entries[0].tevkifat_amount, 2) == 4176.89
    assert round(payload.entries[0].total_deductions, 2) == 52303.99
    assert round(payload.entries[0].net_payment, 2) == 73002.68

    document_payload = _build_local_payroll_document_payload(
        conn,
        selected_month="2026-03",
        personnel_id=1,
    )
    assert round(document_payload.tevkifat_amount, 2) == 4176.89
    assert any(item[0] == "Tevkifat" and round(item[1], 2) == 4176.89 for item in document_payload.deduction_items)


def test_payroll_dashboard_adds_religious_holiday_bonus_for_fixed_support_roles():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Cihan Can Çimen', 'CK-BM01', 'Bölge Müdürü', 'Aktif', 'fixed_bolge_muduru', 117475)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Doğu Otomotiv', 'Merkez')")
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
            (f"2026-03-{day:02d}", 10, 1, 1, 10, 0)
            for day in range(1, 31)
        ],
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-03")

    assert payload.summary is not None
    assert round(payload.entries[0].gross_pay, 2) == 125306.67
    assert round(payload.summary.gross_payroll, 2) == 125306.67
    assert round(payload.entries[0].tevkifat_amount, 2) == 4176.89
    assert round(payload.entries[0].total_deductions, 2) == 4176.89
    assert round(payload.entries[0].net_payment, 2) == 121129.78

    document_payload = _build_local_payroll_document_payload(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-03",
        personnel_id=1,
    )
    assert round(document_payload.gross_pay, 2) == 125306.67
    assert round(document_payload.total_deductions, 2) == 4176.89
    assert round(document_payload.net_payment, 2) == 121129.78
    assert ("Tevkifat", round(document_payload.tevkifat_amount, 2)) == ("Tevkifat", 4176.89)
    assert any(item[0] == "Tevkifat" for item in document_payload.deduction_items)


def test_payroll_dashboard_adds_religious_holiday_bonus_for_fixed_team_chief_roles():
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
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
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
        VALUES (1, 'Recep', 'CK-RTS01', 'Restoran Takım Şefi', 'Aktif', 'fixed_restoran_takim_sefi', 117475)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Doğu Otomotiv', 'Merkez')")
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
            (f"2026-03-{day:02d}", 10, 1, 1, 10, 0)
            for day in range(1, 31)
        ],
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-03")

    assert payload.summary is not None
    assert round(payload.entries[0].gross_pay, 2) == 125306.67
    assert round(payload.summary.gross_payroll, 2) == 125306.67
    assert round(payload.entries[0].tevkifat_amount, 2) == 4176.89
    assert round(payload.entries[0].total_deductions, 2) == 4176.89
    assert round(payload.entries[0].net_payment, 2) == 121129.78

    document_payload = _build_local_payroll_document_payload(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-03",
        personnel_id=1,
    )
    assert round(document_payload.gross_pay, 2) == 125306.67
    assert round(document_payload.total_deductions, 2) == 4176.89
    assert round(document_payload.net_payment, 2) == 121129.78
    assert ("Tevkifat", round(document_payload.tevkifat_amount, 2)) == ("Tevkifat", 4176.89)
    assert any(item[0] == "Tevkifat" for item in document_payload.deduction_items)
