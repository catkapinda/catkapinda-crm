from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.purchases_repository import (
    delete_purchase_record,
    fetch_purchases_management_df,
    insert_purchase_record,
    update_purchase_record,
)


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE inventory_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_invoice_amount REAL NOT NULL,
            unit_cost REAL NOT NULL,
            supplier TEXT,
            invoice_no TEXT,
            notes TEXT
        );
        """
    )
    return conn


class PurchasesRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_purchase_record(self) -> None:
        insert_purchase_record(
            self.conn,
            {
                "purchase_date": "2026-03-10",
                "item_name": "Kask",
                "quantity": 10,
                "total_invoice_amount": 15000.0,
                "unit_cost": 1500.0,
                "supplier": "Tedarikci A",
                "invoice_no": "INV-1",
                "notes": "Ilk alim",
            },
        )
        self.conn.commit()

        df = fetch_purchases_management_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["item_name"], "Kask")
        self.assertEqual(int(df.iloc[0]["quantity"]), 10)
        self.assertEqual(float(df.iloc[0]["unit_cost"]), 1500.0)

    def test_update_purchase_record(self) -> None:
        insert_purchase_record(
            self.conn,
            {
                "purchase_date": "2026-03-10",
                "item_name": "Kask",
                "quantity": 10,
                "total_invoice_amount": 15000.0,
                "unit_cost": 1500.0,
                "supplier": "Tedarikci A",
                "invoice_no": "INV-1",
                "notes": "Ilk alim",
            },
        )
        self.conn.commit()

        update_purchase_record(
            self.conn,
            1,
            {
                "purchase_date": "2026-03-12",
                "item_name": "Box",
                "quantity": 8,
                "total_invoice_amount": 12000.0,
                "unit_cost": 1500.0,
                "supplier": "Tedarikci B",
                "invoice_no": "INV-2",
                "notes": "Guncel alim",
            },
        )
        self.conn.commit()

        row = self.conn.execute(
            """
            SELECT purchase_date, item_name, quantity, total_invoice_amount, supplier, invoice_no, notes
            FROM inventory_purchases
            WHERE id = ?
            """,
            (1,),
        ).fetchone()
        self.assertEqual(row["purchase_date"], "2026-03-12")
        self.assertEqual(row["item_name"], "Box")
        self.assertEqual(int(row["quantity"]), 8)
        self.assertEqual(float(row["total_invoice_amount"]), 12000.0)
        self.assertEqual(row["supplier"], "Tedarikci B")

    def test_delete_purchase_record(self) -> None:
        insert_purchase_record(
            self.conn,
            {
                "purchase_date": "2026-03-10",
                "item_name": "Kask",
                "quantity": 10,
                "total_invoice_amount": 15000.0,
                "unit_cost": 1500.0,
                "supplier": "Tedarikci A",
                "invoice_no": "INV-1",
                "notes": "Ilk alim",
            },
        )
        self.conn.commit()

        delete_purchase_record(self.conn, 1)
        self.conn.commit()

        row = self.conn.execute("SELECT COUNT(*) AS count_value FROM inventory_purchases").fetchone()
        self.assertEqual(int(row["count_value"]), 0)
