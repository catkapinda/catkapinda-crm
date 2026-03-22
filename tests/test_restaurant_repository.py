from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.restaurant_repository import (
    count_restaurant_linked_daily_entries,
    count_restaurant_linked_deductions,
    count_restaurant_linked_personnel,
    delete_restaurant_record,
    fetch_restaurant_management_df,
    insert_restaurant_record,
    update_restaurant_record,
    update_restaurant_status,
)


def _restaurant_values() -> dict[str, object]:
    return {
        "brand": "Fasuli",
        "branch": "Beyoglu",
        "billing_group": "Fasuli",
        "pricing_model": "Hacimli Primli",
        "hourly_rate": 273.0,
        "package_rate": 0.0,
        "package_threshold": 390.0,
        "package_rate_low": 33.75,
        "package_rate_high": 37.5,
        "fixed_monthly_fee": 0.0,
        "vat_rate": 20.0,
        "target_headcount": 3,
        "start_date": "2026-03-01",
        "end_date": None,
        "extra_headcount_request": "",
        "extra_headcount_request_date": None,
        "reduce_headcount_request": "",
        "reduce_headcount_request_date": None,
        "contact_name": "Yetkili Kisi",
        "contact_phone": "5550000000",
        "contact_email": "mail@example.com",
        "company_title": "Fasuli Gida",
        "address": "Istanbul",
        "tax_office": "Kadikoy",
        "tax_number": "1234567890",
        "notes": "Not",
    }


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            branch TEXT NOT NULL,
            billing_group TEXT,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold REAL,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL,
            target_headcount INTEGER,
            start_date TEXT,
            end_date TEXT,
            extra_headcount_request TEXT,
            extra_headcount_request_date TEXT,
            reduce_headcount_request TEXT,
            reduce_headcount_request_date TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            company_title TEXT,
            address TEXT,
            tax_office TEXT,
            tax_number TEXT,
            active INTEGER DEFAULT 1,
            notes TEXT
        );

        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            assigned_restaurant_id INTEGER
        );

        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER
        );

        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            deduction_date TEXT,
            deduction_type TEXT,
            amount REAL,
            notes TEXT
        );
        """
    )
    return conn


class RestaurantRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_restaurant_record(self) -> None:
        insert_restaurant_record(self.conn, _restaurant_values())
        self.conn.commit()

        df = fetch_restaurant_management_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["brand"], "Fasuli")
        self.assertEqual(df.iloc[0]["branch"], "Beyoglu")
        self.assertEqual(int(df.iloc[0]["active"]), 1)

    def test_update_restaurant_record(self) -> None:
        insert_restaurant_record(self.conn, _restaurant_values())
        self.conn.commit()

        updated = _restaurant_values()
        updated["branch"] = "Vatan"
        updated["contact_phone"] = "5551111111"
        update_restaurant_record(self.conn, 1, updated)
        self.conn.commit()

        row = self.conn.execute("SELECT branch, contact_phone FROM restaurants WHERE id = ?", (1,)).fetchone()
        self.assertEqual(row["branch"], "Vatan")
        self.assertEqual(row["contact_phone"], "5551111111")

    def test_update_restaurant_status(self) -> None:
        insert_restaurant_record(self.conn, _restaurant_values())
        self.conn.commit()

        update_restaurant_status(self.conn, 1, 0)
        self.conn.commit()

        row = self.conn.execute("SELECT active FROM restaurants WHERE id = ?", (1,)).fetchone()
        self.assertEqual(int(row["active"]), 0)

    def test_delete_restaurant_record(self) -> None:
        insert_restaurant_record(self.conn, _restaurant_values())
        self.conn.commit()

        delete_restaurant_record(self.conn, 1)
        self.conn.commit()

        row = self.conn.execute("SELECT COUNT(*) AS count_value FROM restaurants").fetchone()
        self.assertEqual(int(row["count_value"]), 0)

    def test_count_linked_records(self) -> None:
        insert_restaurant_record(self.conn, _restaurant_values())
        self.conn.execute("INSERT INTO personnel (full_name, assigned_restaurant_id) VALUES (?, ?)", ("Ali Veli", 1))
        self.conn.execute("INSERT INTO daily_entries (restaurant_id) VALUES (?)", (1,))
        self.conn.execute(
            "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes) VALUES (?, ?, ?, ?, ?)",
            (1, "2026-03-31", "Yakıt", 500.0, ""),
        )
        self.conn.commit()

        self.assertEqual(count_restaurant_linked_personnel(self.conn, 1), 1)
        self.assertEqual(count_restaurant_linked_daily_entries(self.conn, 1), 1)
        self.assertEqual(count_restaurant_linked_deductions(self.conn, 1), 1)
