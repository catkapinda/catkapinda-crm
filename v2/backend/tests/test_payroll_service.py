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


def test_payroll_document_keeps_equipment_deductions_itemized():
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
        CREATE TABLE courier_equipment_issues (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            issue_date TEXT,
            item_name TEXT,
            quantity INTEGER,
            unit_cost REAL,
            unit_sale_price REAL,
            vat_rate REAL,
            installment_count INTEGER,
            sale_type TEXT,
            notes TEXT,
            auto_source_key TEXT
        );
        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            deduction_date TEXT,
            deduction_type TEXT,
            amount REAL,
            notes TEXT,
            equipment_issue_id INTEGER
        );
        """
    )
    raw_conn.execute(
        """
        INSERT INTO personnel (id, full_name, person_code, role, status, cost_model, monthly_fixed_cost)
        VALUES (1, 'Neçirvan Bulgan', 'CK-K10', 'Kurye', 'Aktif', 'fixed_kurye', 0)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Quick China', 'Ataşehir')")
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
        VALUES ('2026-05-10', 10, 1, 1, 8, 22)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO courier_equipment_issues (
            id, personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price,
            vat_rate, installment_count, sale_type, notes, auto_source_key
        )
        VALUES
            (11, 1, '2026-05-01', 'Elcik', 1, 500, 1200, 0, 2, 'Satış', 'Test', ''),
            (12, 1, '2026-05-02', 'Kask', 1, 700, 1800, 0, 2, 'Satış', 'Test', '')
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (
            personnel_id, deduction_date, deduction_type, amount, notes, equipment_issue_id
        )
        VALUES
            (1, '2026-05-15', 'Elcik', 600, 'Elcik 1/2', 11),
            (1, '2026-05-15', 'Kask', 900, 'Kask 1/2', 12)
        """
    )
    raw_conn.commit()

    document_payload = _build_local_payroll_document_payload(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-05",
        personnel_id=1,
    )

    assert any(item[0] == "Elcik" and round(item[1], 2) == 600 for item in document_payload.deduction_items)
    assert any(item[0] == "Kask" and round(item[1], 2) == 900 for item in document_payload.deduction_items)
    assert not any(item[0] == "Zimmet Taksiti" for item in document_payload.deduction_items)


def test_payroll_document_net_deductions_drop_when_equipment_is_returned():
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
            amount REAL,
            notes TEXT,
            auto_source_key TEXT
        );
        """
    )
    raw_conn.execute(
        """
        INSERT INTO personnel (id, full_name, person_code, role, status, cost_model, monthly_fixed_cost)
        VALUES (1, 'Ömer Acar', 'CK-K20', 'Kurye', 'Aktif', 'fixed_kurye', 0)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Quick China', 'Ataşehir')")
    raw_conn.execute(
        """
        INSERT INTO daily_entries (
            entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count
        )
        VALUES ('2026-05-10', 10, 1, 1, 8, 20)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes, auto_source_key)
        VALUES
            (1, '2026-05-05', 'Box', 3200, 'Box 1/2', ''),
            (1, '2026-05-06', 'Punch', 2000, 'Punch 1/2', ''),
            (1, '2026-05-12', 'Box', -1200, 'Box geri alım mahsubu', 'equipment:return:1'),
            (1, '2026-05-12', 'Punch', -800, 'Punch geri alım mahsubu', 'equipment:return:2')
        """
    )
    raw_conn.commit()

    document_payload = _build_local_payroll_document_payload(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-05",
        personnel_id=1,
    )

    deduction_map = {label: round(amount, 2) for label, amount in document_payload.deduction_items}
    assert deduction_map["Box"] == 2000.0
    assert deduction_map["Punch"] == 1200.0
    assert round(document_payload.total_deductions, 2) == 3200.0


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


def test_payroll_dashboard_uses_courier_monthly_threshold_for_package_bonus():
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
    assert payload.summary.gross_payroll == 39475.0
    assert payload.entries[0].gross_pay == 39475.0


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


def test_payroll_dashboard_defaults_fixed_monthly_brand_courier_pay_when_fixed_cost_missing():
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
        VALUES (1, 'Seyfullah Aksu', 'CK-K40', 'Kurye', 'Aktif', 'fixed_monthly', 0)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (11, 'SC Petshop', 'Merkez')")
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
        VALUES ('2026-03-10', 11, 1, 1, 10, 0)
        """
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-03")

    assert payload.summary is not None
    assert round(payload.summary.gross_payroll, 2) == 73600.0
    assert round(payload.entries[0].gross_pay, 2) == 73600.0


def test_payroll_dashboard_adds_captain_bonus_and_exposes_it_in_pdf():
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
        VALUES (1, 'Kaptan Kurye', 'CK-KPT01', 'Kaptan', 'Aktif', 'fixed_monthly', 50000)
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Quick China', 'Ataşehir')")
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
        VALUES ('2026-04-10', 10, 1, 1, 8, 10)
        """
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")
    payload = build_payroll_dashboard(conn, selected_month="2026-04")

    assert payload.summary is not None
    assert round(payload.summary.gross_payroll, 2) == 53000.0
    assert round(payload.entries[0].gross_pay, 2) == 53000.0

    document_payload = _build_local_payroll_document_payload(
        conn,
        selected_month="2026-04",
        personnel_id=1,
    )
    assert document_payload.earning_items == [("Kaptanlık Hakedişi", 3000.0)]
    html = _build_payroll_document_html(document_payload)
    assert "Kaptanlık Hakedişi" in html
    assert "3.000,00 ₺" in html


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


def test_payroll_dashboard_uses_courier_package_threshold_for_standard_restaurants():
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
        VALUES (1, 'Muhammed Emin Güneş', 'CK-K20', 'Kurye', 'Aktif', 'standard_courier', 0)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id, brand, branch
        ) VALUES (12, 'Yavuzbey İskender', 'Merkez')
        """
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
            ("2026-03-10", 12, 1, 1, 130.5, 184),
            ("2026-03-20", 12, 1, 1, 130.5, 184),
            ("2026-03-21", 12, 1, 1, 0, 0),
        ],
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
        VALUES ('2026-03-15', 12, 2, 2, 8, 30)
        """
    )
    raw_conn.commit()

    payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-03")

    assert payload.summary is not None
    assert round(payload.summary.gross_payroll, 2) == 72610.0
    assert round(payload.entries[0].gross_pay, 2) == 72610.0


def test_payroll_dashboard_adds_fixed_monthly_support_day_bonus_for_standard_courier():
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
    raw_conn.executemany(
        """
        INSERT INTO personnel (id, full_name, person_code, role, status, cost_model, monthly_fixed_cost)
        VALUES (?, ?, ?, 'Kurye', 'Aktif', 'standard_courier', 0)
        """,
        [
            (1, "Ömer Asap Özdemir", "CK-K10"),
            (2, "SC Petshop Kurye", "CK-K11"),
        ],
    )
    raw_conn.executemany(
        "INSERT INTO restaurants (id, brand, branch) VALUES (?, ?, ?)",
        [
            (10, "Quick China", "Ataşehir"),
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
            ("2026-04-10", 10, 1, 1, 10, 20),
            ("2026-04-11", 11, 2, 1, 8, 12)
        ],
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")
    payload = build_payroll_dashboard(conn, selected_month="2026-04")

    assert payload.summary is not None
    assert round(payload.summary.gross_payroll, 2) == 5453.33
    assert round(payload.entries[0].gross_pay, 2) == 5453.33

    document_payload = _build_local_payroll_document_payload(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-04",
        personnel_id=1,
    )
    assert round(document_payload.gross_pay, 2) == 5453.33


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


def test_payroll_dashboard_applies_accounting_deduction_from_effective_month_only():
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
            accounting_type TEXT,
            accounting_revenue REAL,
            accountant_cost REAL,
            company_setup_revenue REAL,
            company_setup_cost REAL,
            accounting_effective_date TEXT,
            company_setup_effective_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE personnel_accounting_history (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            accounting_type TEXT,
            new_company_setup TEXT,
            accounting_revenue REAL,
            accountant_cost REAL,
            company_setup_revenue REAL,
            company_setup_cost REAL,
            accounting_effective_date TEXT,
            company_setup_effective_date TEXT,
            effective_date TEXT,
            changed_at TEXT,
            notes TEXT
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
            id, full_name, person_code, role, status, cost_model, monthly_fixed_cost, start_date,
            accounting_type, accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost,
            accounting_effective_date, company_setup_effective_date,
            vehicle_type, motor_rental, motor_purchase, motor_rental_monthly_amount
        )
        VALUES (
            1, 'Nisan Muhasebe', 'CK-A01', 'Kurye', 'Aktif', 'standard_courier', 0, '2026-03-01',
            'Çat Kapında Muhasebe', 2000, 1400, 0, 0, '2026-04-01', NULL,
            'Kendi Motoru', 'Hayır', 'Hayır', 0
        )
        """
    )
    raw_conn.execute(
        """
        INSERT INTO personnel_accounting_history (
            id, personnel_id, accounting_type, new_company_setup, accounting_revenue, accountant_cost,
            company_setup_revenue, company_setup_cost, accounting_effective_date, company_setup_effective_date,
            effective_date, changed_at, notes
        )
        VALUES (
            1, 1, 'Çat Kapında Muhasebe', 'Hayır', 2000, 1400, 0, 0,
            '2026-04-01', NULL, '2026-04-01', '2026-04-01 09:00:00', 'test'
        )
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Burger@', 'Kavacık')")
    raw_conn.execute(
        """
        INSERT INTO daily_entries (entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count)
        VALUES ('2026-03-10', 10, 1, 1, 10, 0),
               ('2026-04-10', 10, 1, 1, 10, 0)
        """
    )
    raw_conn.commit()

    march_payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-03")
    april_payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-04")

    assert march_payload.summary is not None
    assert april_payload.summary is not None
    assert round(march_payload.entries[0].total_deductions, 2) == 0.0
    assert round(april_payload.entries[0].total_deductions, 2) == 2000.0


def test_payroll_dashboard_preserves_past_accounting_history_after_switching_away():
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
            accounting_type TEXT,
            accounting_revenue REAL,
            accountant_cost REAL,
            company_setup_revenue REAL,
            company_setup_cost REAL,
            accounting_effective_date TEXT,
            company_setup_effective_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE personnel_accounting_history (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            accounting_type TEXT,
            new_company_setup TEXT,
            accounting_revenue REAL,
            accountant_cost REAL,
            company_setup_revenue REAL,
            company_setup_cost REAL,
            accounting_effective_date TEXT,
            company_setup_effective_date TEXT,
            effective_date TEXT,
            changed_at TEXT,
            notes TEXT
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
            id, full_name, person_code, role, status, cost_model, monthly_fixed_cost, start_date,
            accounting_type, accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost,
            accounting_effective_date, company_setup_effective_date,
            vehicle_type, motor_rental, motor_purchase, motor_rental_monthly_amount
        )
        VALUES (
            1, 'Muhasebe Geçmişi', 'CK-A02', 'Kurye', 'Aktif', 'standard_courier', 0, '2026-03-01',
            'Kendi Muhasebecisi', 0, 0, 0, 0, '2026-04-01', NULL,
            'Kendi Motoru', 'Hayır', 'Hayır', 0
        )
        """
    )
    raw_conn.execute(
        """
        INSERT INTO personnel_accounting_history (
            id, personnel_id, accounting_type, new_company_setup, accounting_revenue, accountant_cost,
            company_setup_revenue, company_setup_cost, accounting_effective_date, company_setup_effective_date,
            effective_date, changed_at, notes
        )
        VALUES
            (1, 1, 'Çat Kapında Muhasebe', 'Hayır', 2000, 1400, 0, 0, '2026-04-01', NULL, '2026-04-01', '2026-04-01 09:00:00', 'start'),
            (2, 1, 'Kendi Muhasebecisi', 'Hayır', 0, 0, 0, 0, '2026-04-01', NULL, '2026-06-01', '2026-06-01 09:00:00', 'leave')
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Burger@', 'Kavacık')")
    raw_conn.execute(
        """
        INSERT INTO daily_entries (entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count)
        VALUES ('2026-05-10', 10, 1, 1, 10, 0),
               ('2026-06-10', 10, 1, 1, 10, 0)
        """
    )
    raw_conn.commit()

    may_payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-05")
    june_payload = build_payroll_dashboard(CompatConnection(raw_conn, "sqlite"), selected_month="2026-06")

    assert may_payload.summary is not None
    assert june_payload.summary is not None
    assert round(may_payload.entries[0].total_deductions, 2) == 2000.0
    assert round(june_payload.entries[0].total_deductions, 2) == 0.0


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


def test_payroll_dashboard_does_not_reduce_tevkifat_base_for_motor_rental():
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
            company_setup_cost REAL,
            accounting_effective_date TEXT,
            company_setup_effective_date TEXT
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
            accounting_revenue, accounting_effective_date
        )
        VALUES (
            1, 'Neçirvan Bulgan', 'CK-K10', 'Kurye', 'Aktif', 'fixed_monthly', 81650,
            2000, '2026-03-01'
        )
        """
    )
    raw_conn.execute("INSERT INTO restaurants (id, brand, branch) VALUES (10, 'Quick China', 'Ataşehir')")
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
        VALUES ('2026-03-10', 10, 1, 1, 10, 10)
        """
    )
    raw_conn.executemany(
        """
        INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "2026-03-25", "Yakıt", 3599.58),
            (1, "2026-03-25", "Motor Kirası", 13000),
        ],
    )
    raw_conn.commit()

    conn = CompatConnection(raw_conn, "sqlite")
    payload = build_payroll_dashboard(conn, selected_month="2026-03")

    assert round(payload.entries[0].gross_pay, 2) == 81650.00
    assert round(payload.entries[0].tevkifat_amount, 2) == 2721.67
    assert round(payload.entries[0].total_deductions, 2) == 21321.25
    assert round(payload.entries[0].net_payment, 2) == 60328.75

    document_payload = _build_local_payroll_document_payload(
        conn,
        selected_month="2026-03",
        personnel_id=1,
    )
    assert round(document_payload.invoice_base_amount, 2) == 68041.67
    assert round(document_payload.invoice_vat_amount, 2) == 13608.33
    assert round(document_payload.tevkifat_amount, 2) == 2721.67
    assert any(item[0] == "Motor Kirası" and round(item[1], 2) == 13000.00 for item in document_payload.deduction_items)
    assert any(item[0] == "Muhasebe Kesintisi" and round(item[1], 2) == 2000.00 for item in document_payload.deduction_items)
    assert any(item[0] == "Tevkifat" and round(item[1], 2) == 2721.67 for item in document_payload.deduction_items)


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
