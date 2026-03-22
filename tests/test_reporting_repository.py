from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.reporting_repository import (
    fetch_reporting_deductions_for_period,
    fetch_reporting_entries,
    fetch_reporting_personnel,
    fetch_reporting_restaurants,
    fetch_reporting_role_history,
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
            branch TEXT NOT NULL,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold REAL,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );

        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            role TEXT
        );

        CREATE TABLE personnel_role_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            effective_date TEXT,
            role TEXT,
            cost_model TEXT
        );

        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            restaurant_id INTEGER NOT NULL,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            status TEXT,
            worked_hours REAL,
            package_count REAL
        );

        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER,
            deduction_date TEXT NOT NULL,
            deduction_type TEXT,
            amount REAL
        );
        """
    )
    return conn


class ReportingRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.execute(
            """
            INSERT INTO restaurants
            (brand, branch, pricing_model, hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Fasuli", "Beyoglu", "Hacimli Primli", 273.0, 0.0, 390.0, 33.75, 37.5, 0.0, 20.0),
        )
        self.conn.execute("INSERT INTO personnel (full_name, role) VALUES (?, ?)", ("Ali Veli", "Kurye"))
        self.conn.execute(
            "INSERT INTO personnel_role_history (personnel_id, effective_date, role, cost_model) VALUES (?, ?, ?, ?)",
            (1, "2026-03-01", "Kurye", "Kurye"),
        )
        self.conn.execute(
            """
            INSERT INTO daily_entries
            (entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, status, worked_hours, package_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-03-22", 1, 1, 1, "Çalıştı", 8.0, 22.0),
        )
        self.conn.execute(
            "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount) VALUES (?, ?, ?, ?)",
            (1, "2026-03-31", "Yakıt", 500.0),
        )
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_fetch_reporting_entries_returns_joined_restaurant_fields(self) -> None:
        df = fetch_reporting_entries(self.conn)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["brand"], "Fasuli")
        self.assertEqual(row["branch"], "Beyoglu")
        self.assertEqual(row["pricing_model"], "Hacimli Primli")
        self.assertAlmostEqual(float(row["hourly_rate"]), 273.0)

    def test_fetch_reporting_restaurants_and_personnel(self) -> None:
        restaurants_df = fetch_reporting_restaurants(self.conn)
        personnel_df = fetch_reporting_personnel(self.conn)

        self.assertEqual(len(restaurants_df), 1)
        self.assertEqual(restaurants_df.iloc[0]["branch"], "Beyoglu")
        self.assertEqual(len(personnel_df), 1)
        self.assertEqual(personnel_df.iloc[0]["full_name"], "Ali Veli")

    def test_fetch_reporting_role_history(self) -> None:
        df = fetch_reporting_role_history(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["role"], "Kurye")
        self.assertEqual(df.iloc[0]["cost_model"], "Kurye")

    def test_fetch_reporting_deductions_for_period_filters_dates(self) -> None:
        self.conn.execute(
            "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount) VALUES (?, ?, ?, ?)",
            (1, "2026-04-01", "HGS", 250.0),
        )
        self.conn.commit()

        march_df = fetch_reporting_deductions_for_period(self.conn, "2026-03-01", "2026-03-31")
        self.assertEqual(len(march_df), 1)
        self.assertEqual(march_df.iloc[0]["deduction_type"], "Yakıt")
