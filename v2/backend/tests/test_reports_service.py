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
            motor_rental TEXT,
            motor_purchase TEXT
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
            id, full_name, role, monthly_fixed_cost, cost_model, motor_rental, motor_purchase
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "Ali Kurye", "Kurye", 30000, "standard_courier", "Hayır", "Hayır"),
            (2, "Ayşe Kurye", "Kurye", 32000, "standard_courier", "Hayır", "Hayır"),
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

    assert payload.summary is not None
    assert payload.summary.restaurant_count == 3
    assert payload.summary.total_revenue == 62402.4
