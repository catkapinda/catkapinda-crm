import sqlite3

from app.core.database import CompatConnection
from app.services.reports import build_reports_dashboard


def _build_reports_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL
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
        INSERT INTO personnel (
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "Ali Kurye", "Kurye", 30000, "standard_courier", "Aktif", "2026-01-01", "Hayır", "Hayır", "Kendi Motoru", 13000),
            (2, "Ayşe Kurye", "Kurye", 32000, "standard_courier", "Aktif", "2026-01-01", "Hayır", "Hayır", "Kendi Motoru", 13000),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO restaurants (
            id,
            brand,
            branch,
            active,
            pricing_model,
            hourly_rate,
            package_rate,
            package_threshold,
            package_rate_low,
            package_rate_high,
            fixed_monthly_fee,
            vat_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (10, "Burger@", "Kavacık", 1, "hourly_plus_package", 100, 10, 390, 0, 0, 0, 20),
            (11, "Kod", "Deneme", 1, "threshold_package", 0, 0, 10, 3, 5, 0, 20),
            (12, "Fasuli", "Beyoğlu", 1, "fixed_monthly", 0, 0, 390, 0, 0, 50000, 20),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO daily_entries (
            id,
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            worked_hours,
            package_count,
            monthly_invoice_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "2026-04-10", 10, 1, 1, 10, 5, 0),
            (2, "2026-04-11", 10, 2, 2, 8, 7, 0),
            (3, "2026-04-12", 11, 1, 1, 0, 9, 0),
            (4, "2026-04-12", 11, 2, 2, 0, 11, 0),
            (5, "2026-04-13", 12, 1, 1, 10, 0, 0),
        ],
    )
    raw_conn.commit()
    return CompatConnection(raw_conn, "sqlite")


def test_reports_dashboard_calculates_restaurant_invoices_from_attendance_rates():
    payload = build_reports_dashboard(
        _build_reports_conn(),
        selected_month="2026-04",
        limit=10,
    )

    invoice_by_restaurant = {
        entry.restaurant: entry
        for entry in payload.invoice_entries
    }

    burger_invoice = invoice_by_restaurant["Burger@ - Kavacık"]
    assert burger_invoice.total_hours == 18
    assert burger_invoice.total_packages == 12
    assert burger_invoice.net_invoice == 1920
    assert burger_invoice.gross_invoice == 2304

    threshold_invoice = invoice_by_restaurant["Kod - Deneme"]
    assert threshold_invoice.net_invoice == 82
    assert threshold_invoice.gross_invoice == 98.4

    fixed_invoice = invoice_by_restaurant["Fasuli - Beyoğlu"]
    assert fixed_invoice.net_invoice == 50000
    assert fixed_invoice.gross_invoice == 60000

    drilldown = next(
        entry
        for entry in payload.invoice_drilldown_entries
        if entry.restaurant == "Burger@ - Kavacık" and entry.personnel == "Ali Kurye"
    )
    assert drilldown.net_invoice_amount == 1050
    assert drilldown.gross_invoice_amount == 1260

    assert payload.summary is not None
    assert payload.summary.restaurant_count == 3
    assert payload.summary.total_revenue == 62402.4


def test_reports_dashboard_keeps_standard_courier_formula_on_fixed_monthly_restaurants():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL
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
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (1, 'Standart Kurye', 'Kurye', 0, 'standard_courier', 'Aktif', '2026-01-01', 'Hayır', 'Hayır', 'Kendi Motoru', 13000)
        """
    )
    raw_conn.executemany(
        """
        INSERT INTO restaurants (
            id,
            brand,
            branch,
            active,
            pricing_model,
            hourly_rate,
            package_rate,
            package_threshold,
            package_rate_low,
            package_rate_high,
            fixed_monthly_fee,
            vat_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (10, "Sushi Inn", "Merkez", 1, "fixed_monthly", 0, 0, 390, 0, 0, 50000, 20),
            (11, "Burger@", "Kavacık", 1, "hourly_plus_package", 279, 32, 390, 0, 0, 0, 20),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO daily_entries (
            id,
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            worked_hours,
            package_count,
            monthly_invoice_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "2026-04-10", 10, 1, 1, 20, 40, 0),
            (2, "2026-04-11", 11, 1, 1, 10, 20, 0),
        ],
    )
    raw_conn.commit()

    payload = build_reports_dashboard(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-04",
        limit=10,
    )

    assert payload.cost_entries
    assert payload.cost_entries[0].net_cost == 8700.0
    assert payload.top_couriers
    assert payload.top_couriers[0].net_cost == 8700.0


def test_reports_dashboard_distributes_gross_cost_when_deductions_zero_out_net():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL
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
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (1, 'Barancan Ay', 'Kurye', 0, 'standard_courier', 'Aktif', '2026-01-01', 'Hayır', 'Hayır', 'Kendi Motoru', 13000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id, brand, branch, active, pricing_model, hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate
        )
        VALUES (10, 'Burger@', 'Kavacık', 1, 'hourly_plus_package', 279, 32, 390, 0, 0, 0, 20)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO daily_entries (
            id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count, monthly_invoice_amount
        )
        VALUES (1, '2026-04-10', 10, 1, 1, 4, 2, 0)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO deductions (id, personnel_id, deduction_date, deduction_type, amount)
        VALUES (1, 1, '2026-04-11', 'Avans', 5000)
        """
    )
    raw_conn.commit()

    payload = build_reports_dashboard(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-04",
        limit=10,
    )

    assert payload.cost_entries
    assert payload.cost_entries[0].gross_cost == 1040.0
    assert payload.cost_entries[0].net_cost == 0.0
    assert payload.distribution_entries
    assert payload.distribution_entries[0].allocated_cost == 1040.0
    assert payload.profit_entries[0].direct_personnel_cost == 1040.0


def test_reports_dashboard_uses_fixed_role_invoice_override_with_holiday_bonus():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL,
            coverage_type TEXT
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
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (1, 'Recep Çevik', 'Restoran Takım Şefi', 0, 'fixed_restoran_takim_sefi', 'Aktif', '2026-01-01', 'Hayır', 'Hayır', 'Kendi Motoru', 13000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id, brand, branch, active, pricing_model, hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate
        )
        VALUES (10, 'Quick China', 'Ataşehir', 1, 'hourly_plus_package', 264, 33, 390, 0, 0, 0, 20)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO daily_entries (
            id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count, monthly_invoice_amount, coverage_type
        )
        VALUES (1, '2026-03-10', 10, 1, 1, 11, 85, 84500, '')
        """
    )
    raw_conn.commit()

    payload = build_reports_dashboard(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-03",
        limit=10,
    )

    invoice = payload.invoice_entries[0]
    assert invoice.net_invoice == 90133.33
    assert invoice.gross_invoice == 108160.0

    drilldown = payload.invoice_drilldown_entries[0]
    assert round(drilldown.net_invoice_amount, 2) == 90133.33
    assert round(drilldown.gross_invoice_amount, 2) == 108160.0


def test_reports_dashboard_keeps_fixed_role_restaurant_on_standard_formula_outside_quick_china():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL,
            coverage_type TEXT
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
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (1, 'Recep Çevik', 'Restoran Takım Şefi', 0, 'fixed_restoran_takim_sefi', 'Aktif', '2026-01-01', 'Hayır', 'Hayır', 'Kendi Motoru', 13000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id, brand, branch, active, pricing_model, hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate
        )
        VALUES (10, 'Burger Yiyelim', 'Kadıköy', 1, 'hourly_plus_package', 264, 33, 390, 0, 0, 0, 20)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO daily_entries (
            id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count, monthly_invoice_amount, coverage_type
        )
        VALUES (1, '2026-03-10', 10, 1, 1, 11, 85, 84500, '')
        """
    )
    raw_conn.commit()

    payload = build_reports_dashboard(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-03",
        limit=10,
    )

    invoice = payload.invoice_entries[0]
    assert invoice.net_invoice == 5709.0
    assert invoice.gross_invoice == 6850.8


def test_reports_dashboard_uses_fixed_monthly_brand_support_proration():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL,
            coverage_type TEXT
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
        INSERT INTO personnel (
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, 'Seyfullah', 'Kurye', 0, 'fixed_kurye', 'Aktif', '2026-01-01', 'Hayır', 'Hayır', 'Kendi Motoru', 13000),
            (2, 'Erkan Çelik', 'Kaptan', 0, 'fixed_kaptan', 'Aktif', '2026-01-01', 'Hayır', 'Hayır', 'Kendi Motoru', 13000),
        ],
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id, brand, branch, active, pricing_model, hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate
        )
        VALUES (10, 'SC Petshop', 'Merkez', 1, 'fixed_monthly', 0, 0, 390, 0, 0, 79800, 20)
        """
    )
    raw_conn.executemany(
        """
        INSERT INTO daily_entries (
            id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count, monthly_invoice_amount, coverage_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, '2026-03-12', 10, 1, 1, 270, 0, 79800, ''),
            (2, '2026-03-14', 10, 1, 2, 10, 0, 79800, 'Destek'),
        ],
    )
    raw_conn.commit()

    payload = build_reports_dashboard(
        CompatConnection(raw_conn, "sqlite"),
        selected_month="2026-03",
        limit=10,
    )

    invoice = payload.invoice_entries[0]
    assert invoice.net_invoice == 85120.0
    assert invoice.gross_invoice == 102144.0

    drilldown_by_person = {entry.personnel: entry for entry in payload.invoice_drilldown_entries}
    assert drilldown_by_person["Seyfullah"].net_invoice_amount == 82460.0
    assert drilldown_by_person["Erkan Çelik"].net_invoice_amount == 2660.0
