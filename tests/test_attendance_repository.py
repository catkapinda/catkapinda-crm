from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.attendance_repository import (
    delete_daily_entry,
    fetch_bulk_attendance_people_rows,
    fetch_daily_entry_by_id,
    fetch_daily_entry_management_df,
    insert_daily_entry,
    update_daily_entry,
)


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            branch TEXT NOT NULL
        );

        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            assigned_restaurant_id INTEGER
        );

        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            restaurant_id INTEGER NOT NULL,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            status TEXT NOT NULL,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL DEFAULT 0,
            absence_reason TEXT,
            coverage_type TEXT,
            notes TEXT
        );
        """
    )
    return conn


def _entry_values() -> dict[str, object]:
    return {
        "entry_date": "2026-03-22",
        "restaurant_id": 1,
        "planned_personnel_id": 1,
        "actual_personnel_id": 2,
        "status": "Çalıştı",
        "worked_hours": 8.0,
        "package_count": 22.0,
        "monthly_invoice_amount": 125000.0,
        "absence_reason": "İzin",
        "coverage_type": "Joker",
        "notes": "Not",
    }


class AttendanceRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.execute("INSERT INTO restaurants (brand, branch) VALUES (?, ?)", ("Fasuli", "Beyoglu"))
        self.conn.execute("INSERT INTO restaurants (brand, branch) VALUES (?, ?)", ("Quick China", "Atasehir"))
        self.conn.execute(
            "INSERT INTO personnel (full_name, role, status, assigned_restaurant_id) VALUES (?, ?, ?, ?)",
            ("Ali Veli", "Kurye", "Aktif", 1),
        )
        self.conn.execute(
            "INSERT INTO personnel (full_name, role, status, assigned_restaurant_id) VALUES (?, ?, ?, ?)",
            ("Mehmet Kaya", "Joker", "Aktif", None),
        )
        self.conn.execute(
            "INSERT INTO personnel (full_name, role, status, assigned_restaurant_id) VALUES (?, ?, ?, ?)",
            ("Ayse Yilmaz", "Kurye", "Aktif", 2),
        )
        self.conn.execute(
            "INSERT INTO personnel (full_name, role, status, assigned_restaurant_id) VALUES (?, ?, ?, ?)",
            ("Zeynep Demir", "Restoran Takım Şefi", "Aktif", None),
        )
        self.conn.execute(
            "INSERT INTO personnel (full_name, role, status, assigned_restaurant_id) VALUES (?, ?, ?, ?)",
            ("Eski Personel", "Kurye", "Pasif", 1),
        )
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_daily_entry_management_df(self) -> None:
        insert_daily_entry(self.conn, _entry_values())
        self.conn.commit()

        df = fetch_daily_entry_management_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["restoran"], "Fasuli - Beyoglu")
        self.assertEqual(df.iloc[0]["calisan_personel"], "Mehmet Kaya")
        self.assertEqual(df.iloc[0]["neden_girmedi"], "İzin")
        self.assertEqual(df.iloc[0]["yerine_giren_tipi"], "Joker")
        self.assertEqual(float(df.iloc[0]["monthly_invoice_amount"]), 125000.0)

    def test_fetch_daily_entry_by_id(self) -> None:
        insert_daily_entry(self.conn, _entry_values())
        self.conn.commit()

        row = fetch_daily_entry_by_id(self.conn, 1)
        self.assertEqual(row["entry_date"], "2026-03-22")
        self.assertEqual(row["status"], "Çalıştı")
        self.assertEqual(float(row["worked_hours"]), 8.0)
        self.assertEqual(float(row["monthly_invoice_amount"]), 125000.0)
        self.assertEqual(row["absence_reason"], "İzin")
        self.assertEqual(row["coverage_type"], "Joker")

    def test_update_daily_entry(self) -> None:
        insert_daily_entry(self.conn, _entry_values())
        self.conn.commit()

        updated = _entry_values()
        updated["actual_personnel_id"] = 1
        updated["status"] = "İzin"
        updated["worked_hours"] = 0.0
        updated["package_count"] = 0.0
        updated["monthly_invoice_amount"] = 132500.0
        updated["absence_reason"] = "Raporlu"
        updated["coverage_type"] = ""
        updated["notes"] = "Guncel"
        update_daily_entry(self.conn, 1, updated)
        self.conn.commit()

        row = self.conn.execute(
            "SELECT actual_personnel_id, status, worked_hours, package_count, monthly_invoice_amount, absence_reason, coverage_type, notes FROM daily_entries WHERE id = ?",
            (1,),
        ).fetchone()
        self.assertEqual(row["actual_personnel_id"], 1)
        self.assertEqual(row["status"], "İzin")
        self.assertEqual(float(row["worked_hours"]), 0.0)
        self.assertEqual(float(row["monthly_invoice_amount"]), 132500.0)
        self.assertEqual(row["absence_reason"], "Raporlu")
        self.assertEqual(row["notes"], "Guncel")

    def test_delete_daily_entry(self) -> None:
        insert_daily_entry(self.conn, _entry_values())
        self.conn.commit()

        delete_daily_entry(self.conn, 1)
        self.conn.commit()

        row = self.conn.execute("SELECT COUNT(*) AS count_value FROM daily_entries").fetchone()
        self.assertEqual(int(row["count_value"]), 0)

    def test_fetch_bulk_attendance_people_rows_filters_for_restaurant_and_special_roles(self) -> None:
        rows = fetch_bulk_attendance_people_rows(self.conn, restaurant_id=1, include_all_active=False)
        labels = [f"{row['full_name']} ({row['role']})" for row in rows]

        self.assertEqual(
            labels,
            [
                "Zeynep Demir (Restoran Takım Şefi)",
                "Mehmet Kaya (Joker)",
                "Ali Veli (Kurye)",
            ],
        )

    def test_fetch_bulk_attendance_people_rows_include_all_active(self) -> None:
        rows = fetch_bulk_attendance_people_rows(self.conn, restaurant_id=1, include_all_active=True)
        labels = [f"{row['full_name']} ({row['role']})" for row in rows]

        self.assertEqual(
            labels,
            [
                "Zeynep Demir (Restoran Takım Şefi)",
                "Mehmet Kaya (Joker)",
                "Ali Veli (Kurye)",
                "Ayse Yilmaz (Kurye)",
            ],
        )

    def test_fetch_daily_entry_management_df_returns_more_than_500_rows(self) -> None:
        for index in range(550):
            values = _entry_values()
            values["entry_date"] = f"2026-03-{(index % 28) + 1:02d}"
            values["notes"] = f"Kayit {index}"
            insert_daily_entry(self.conn, values)
        self.conn.commit()

        df = fetch_daily_entry_management_df(self.conn)

        self.assertEqual(len(df), 550)
