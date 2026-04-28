from datetime import date
import sqlite3

import pytest

from app.core.database import CompatConnection
from app.schemas.attendance import (
    AttendanceBulkCreateRequest,
    AttendanceBulkCreateRowRequest,
    AttendanceCreateRequest,
    AttendanceUpdateRequest,
)
from app.services.attendance import (
    build_attendance_management,
    create_attendance_entries_bulk,
    create_attendance_entry,
    update_attendance_entry_record,
)


def _build_attendance_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
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
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            status TEXT,
            assigned_restaurant_id INTEGER
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            status TEXT,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL,
            absence_reason TEXT,
            coverage_type TEXT,
            notes TEXT
        );
        """
    )
    raw_conn.execute(
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
        VALUES (10, 'Burger@', 'Kavacık', 1, 'hourly_plus_package', 100, 10, 390, 0, 0, 0, 20)
        """
    )
    raw_conn.executemany(
        """
        INSERT INTO personnel (id, full_name, role, status, assigned_restaurant_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, "Ali Kurye", "Kurye", "Aktif", 10),
            (2, "Ayşe Kurye", "Kurye", "Aktif", 10),
        ],
    )
    raw_conn.commit()
    return CompatConnection(raw_conn, "sqlite")


def test_single_attendance_entry_calculates_invoice_from_restaurant_rates():
    conn = _build_attendance_conn()

    response = create_attendance_entry(
        conn,
        payload=AttendanceCreateRequest(
            entry_date=date(2026, 4, 19),
            restaurant_id=10,
            entry_mode="Restoran Kuryesi",
            primary_person_id=1,
            worked_hours=8,
            package_count=10,
        ),
    )

    row = conn.execute("SELECT monthly_invoice_amount FROM daily_entries WHERE id = %s", (response.entry_id,)).fetchone()
    assert row["monthly_invoice_amount"] == 900


def test_bulk_attendance_entries_calculate_invoice_and_keep_absence_zero():
    conn = _build_attendance_conn()

    response = create_attendance_entries_bulk(
        conn,
        payload=AttendanceBulkCreateRequest(
            entry_date=date(2026, 4, 19),
            restaurant_id=10,
            rows=[
                AttendanceBulkCreateRowRequest(
                    person_id=1,
                    worked_hours=9,
                    package_count=18,
                    entry_status="Normal",
                ),
                AttendanceBulkCreateRowRequest(
                    person_id=2,
                    worked_hours=0,
                    package_count=0,
                    entry_status="İzin",
                ),
            ],
        ),
    )

    assert response.created_count == 2
    rows = conn.execute(
        """
        SELECT planned_personnel_id, actual_personnel_id, status, monthly_invoice_amount
        FROM daily_entries
        ORDER BY planned_personnel_id
        """
    ).fetchall()
    assert rows[0]["monthly_invoice_amount"] == 1080
    assert rows[1]["actual_personnel_id"] is None
    assert rows[1]["status"] == "İzin"
    assert rows[1]["monthly_invoice_amount"] == 0


def test_attendance_management_supports_offset_pagination():
    conn = _build_attendance_conn()

    for day in (19, 18, 17):
        create_attendance_entry(
            conn,
            payload=AttendanceCreateRequest(
                entry_date=date(2026, 4, day),
                restaurant_id=10,
                entry_mode="Restoran Kuryesi",
                primary_person_id=1,
                worked_hours=8,
                package_count=10,
            ),
        )

    first_page = build_attendance_management(conn, limit=2, offset=0)
    second_page = build_attendance_management(conn, limit=2, offset=2)

    assert first_page.total_entries == 3
    assert [entry.entry_date.isoformat() for entry in first_page.entries] == ["2026-04-19", "2026-04-18"]
    assert [entry.entry_date.isoformat() for entry in second_page.entries] == ["2026-04-17"]


@pytest.mark.parametrize("entry_mode", ["Joker", "Destek"])
def test_update_attendance_entry_recalculates_invoice_for_covering_leave(entry_mode: str):
    conn = _build_attendance_conn()

    create_response = create_attendance_entry(
        conn,
        payload=AttendanceCreateRequest(
            entry_date=date(2026, 4, 19),
            restaurant_id=10,
            entry_mode="Haftalık İzin",
            primary_person_id=1,
            absence_reason="İzin",
            worked_hours=0,
            package_count=0,
        ),
    )

    update_response = update_attendance_entry_record(
        conn,
        entry_id=create_response.entry_id,
        payload=AttendanceUpdateRequest(
            entry_date=date(2026, 4, 19),
            restaurant_id=10,
            entry_mode=entry_mode,
            primary_person_id=1,
            replacement_person_id=2,
            absence_reason="İzin",
            worked_hours=9,
            package_count=18,
            monthly_invoice_amount=0,
            notes="",
        ),
    )

    assert update_response.entry_id == create_response.entry_id
    row = conn.execute(
        """
        SELECT actual_personnel_id, worked_hours, package_count, monthly_invoice_amount, coverage_type
        FROM daily_entries
        WHERE id = %s
        """,
        (create_response.entry_id,),
    ).fetchone()
    assert row["actual_personnel_id"] == 2
    assert row["worked_hours"] == 9
    assert row["package_count"] == 18
    assert row["coverage_type"] == entry_mode
    assert row["monthly_invoice_amount"] == 1080
