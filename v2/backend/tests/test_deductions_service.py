from datetime import date
import sqlite3

from app.core.database import CompatConnection
from app.services.deductions import _build_management_entry, build_deductions_dashboard, build_deductions_management


def test_unknown_deduction_type_does_not_show_maintenance_caption():
    entry = _build_management_entry(
        {
            "id": 1,
            "personnel_id": 10,
            "personnel_label": "Kurye",
            "deduction_date": date(2026, 4, 10),
            "deduction_type": "Zimmet Taksiti",
            "amount": 1300,
            "notes": "",
            "auto_source_key": "",
        }
    )

    assert entry.deduction_type == "Zimmet Taksiti"
    assert entry.type_caption == ""


def test_deductions_dashboard_shows_virtual_motor_rental_and_purchase_rows():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            status TEXT,
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
    raw_conn.executemany(
        """
        INSERT INTO personnel (
            id,
            full_name,
            role,
            status,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "Kiralık Kurye", "Kurye", "Aktif", "2026-04-21", "Çat Kapında", "Evet", "Hayır", 13000, None, 0, 0, 0),
            (2, "Satılık Kurye", "Kurye", "Aktif", "2026-04-01", "Çat Kapında", "Hayır", "Evet", 0, "2026-04-17", 12, 84000, 7000),
        ],
    )
    raw_conn.commit()
    conn = CompatConnection(raw_conn, "sqlite")

    dashboard = build_deductions_dashboard(conn, reference_date=date(2026, 4, 23), limit=10)
    management = build_deductions_management(conn, limit=10)

    types = {entry.deduction_type for entry in dashboard.recent_entries}
    assert {"Motor Kirası", "Motor Satış Taksiti"} <= types
    assert dashboard.summary.auto_entries == 2
    assert management.total_entries == 2
    assert any("taahhüt 12 ay" in entry.notes for entry in management.entries)
