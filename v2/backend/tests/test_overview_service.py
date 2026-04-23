from datetime import date
import sqlite3

from app.core.database import CompatConnection
from app.services.overview import _build_operations_summary


def test_overview_brand_summary_uses_monthly_invoice_once_for_fixed_model():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            status TEXT,
            assigned_restaurant_id INTEGER,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            start_date TEXT,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_rental_monthly_amount REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            target_headcount INTEGER,
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
            id,
            full_name,
            role,
            status,
            assigned_restaurant_id,
            monthly_fixed_cost,
            cost_model,
            start_date,
            vehicle_type,
            motor_rental,
            motor_purchase,
            motor_rental_monthly_amount
        )
        VALUES (1, 'Sabit Marka Kurye', 'Kurye', 'Aktif', 10, 0, 'standard_courier', '2026-01-01', 'Kendi Motoru', 'Hayır', 'Hayır', 13000)
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id,
            brand,
            branch,
            active,
            target_headcount,
            pricing_model,
            hourly_rate,
            package_rate,
            package_threshold,
            package_rate_low,
            package_rate_high,
            fixed_monthly_fee,
            vat_rate
        )
        VALUES (10, 'Sushi Inn', 'Merkez', 1, 1, 'fixed_monthly', 0, 0, 390, 0, 0, 50000, 20)
        """
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
            monthly_invoice_amount,
            coverage_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "2026-04-10", 10, 1, 1, 140, 0, 50000, ""),
            (2, "2026-04-11", 10, 1, 1, 140, 0, 50000, ""),
        ],
    )
    raw_conn.commit()

    summary = _build_operations_summary(
        CompatConnection(raw_conn, "sqlite"),
        reference_date=date(2026, 4, 30),
        selected_month="2026-04",
    )

    sushi_inn = next(entry for entry in summary.brand_summary if entry.brand == "Sushi Inn")
    assert sushi_inn.total_hours == 280
    assert sushi_inn.gross_invoice == 60000
    assert sushi_inn.operation_gap == -13600
    assert sushi_inn.status == "Riskte"
