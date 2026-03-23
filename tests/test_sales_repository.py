from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.sales_repository import (
    delete_sales_lead_record,
    fetch_sales_leads_df,
    insert_sales_lead_record,
    update_sales_lead_record,
)


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE sales_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_name TEXT NOT NULL,
            city TEXT,
            district TEXT,
            address TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            requested_courier_count INTEGER DEFAULT 0,
            lead_source TEXT,
            proposed_quote REAL DEFAULT 0,
            pricing_model_hint TEXT,
            status TEXT NOT NULL,
            next_follow_up_date TEXT,
            assigned_owner TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    return conn


def _lead_values() -> dict[str, object]:
    return {
        "restaurant_name": "Burger House",
        "city": "İstanbul",
        "district": "Kadıköy",
        "address": "Moda Cd. No:10",
        "contact_name": "Ayşe Yetkili",
        "contact_phone": "05551234567",
        "contact_email": "ayse@example.com",
        "requested_courier_count": 3,
        "lead_source": "Telefon",
        "proposed_quote": 25000.0,
        "pricing_model_hint": "273₺/saat + 33,75₺/paket",
        "status": "Yeni Talep",
        "next_follow_up_date": "2026-03-25",
        "assigned_owner": "Ebru",
        "notes": "İlk görüşme olumlu",
        "created_at": "2026-03-23T10:00:00+00:00",
        "updated_at": "2026-03-23T10:00:00+00:00",
    }


class SalesRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_sales_lead(self) -> None:
        insert_sales_lead_record(self.conn, _lead_values())
        self.conn.commit()

        df = fetch_sales_leads_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["restaurant_name"], "Burger House")
        self.assertEqual(df.iloc[0]["lead_source"], "Telefon")

    def test_update_sales_lead(self) -> None:
        insert_sales_lead_record(self.conn, _lead_values())
        self.conn.commit()

        values = _lead_values()
        values["status"] = "Teklif İletildi"
        values["requested_courier_count"] = 5
        update_sales_lead_record(self.conn, 1, values)
        self.conn.commit()

        row = self.conn.execute("SELECT status, requested_courier_count FROM sales_leads WHERE id = 1").fetchone()
        self.assertEqual(row["status"], "Teklif İletildi")
        self.assertEqual(int(row["requested_courier_count"]), 5)

    def test_delete_sales_lead(self) -> None:
        insert_sales_lead_record(self.conn, _lead_values())
        self.conn.commit()

        delete_sales_lead_record(self.conn, 1)
        self.conn.commit()

        row = self.conn.execute("SELECT COUNT(*) AS count_value FROM sales_leads").fetchone()
        self.assertEqual(int(row["count_value"]), 0)
