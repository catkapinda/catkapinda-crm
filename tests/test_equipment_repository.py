from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.equipment_repository import (
    fetch_box_return_management_df,
    fetch_equipment_installment_df,
    fetch_equipment_issue_management_df,
    fetch_equipment_purchase_summary_df,
    fetch_equipment_sales_profit_df,
    insert_box_return_record,
)


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL
        );

        CREATE TABLE courier_equipment_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            unit_sale_price REAL NOT NULL,
            vat_rate REAL,
            auto_source_key TEXT,
            installment_count INTEGER,
            sale_type TEXT,
            notes TEXT
        );

        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            deduction_date TEXT NOT NULL,
            deduction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            auto_source_key TEXT,
            equipment_issue_id INTEGER
        );

        CREATE TABLE box_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            return_date TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            condition_status TEXT,
            payout_amount REAL,
            waived INTEGER,
            notes TEXT
        );

        CREATE TABLE inventory_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_invoice_amount REAL NOT NULL
        );
        """
    )
    return conn


class EquipmentRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.execute("INSERT INTO personnel (full_name) VALUES (?)", ("Ali Veli",))
        self.conn.execute("INSERT INTO personnel (full_name) VALUES (?)", ("Ayse Yilmaz",))
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_fetch_equipment_issue_management_df_computes_totals(self) -> None:
        self.conn.execute(
            """
            INSERT INTO courier_equipment_issues
            (personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, auto_source_key, installment_count, sale_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-03-20", "Kask", 2, 500.0, 750.0, 20.0, "", 2, "Satış", "Not"),
        )
        self.conn.commit()

        df = fetch_equipment_issue_management_df(self.conn)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["full_name"], "Ali Veli")
        self.assertEqual(row["item_name"], "Kask")
        self.assertAlmostEqual(float(row["total_cost"]), 1000.0)
        self.assertAlmostEqual(float(row["total_sale"]), 1500.0)
        self.assertAlmostEqual(float(row["gross_profit"]), 500.0)

    def test_fetch_equipment_installment_df_filters_only_equipment_linked_deductions(self) -> None:
        self.conn.execute(
            """
            INSERT INTO deductions
            (personnel_id, deduction_date, deduction_type, amount, notes, auto_source_key, equipment_issue_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-03-31", "Kask Taksiti", 750.0, "ilk", "equip:1", 1),
        )
        self.conn.execute(
            """
            INSERT INTO deductions
            (personnel_id, deduction_date, deduction_type, amount, notes, auto_source_key, equipment_issue_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (2, "2026-03-31", "Yakıt", 300.0, "ay sonu", "", None),
        )
        self.conn.commit()

        df = fetch_equipment_installment_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["full_name"], "Ali Veli")
        self.assertEqual(df.iloc[0]["deduction_type"], "Kask Taksiti")

    def test_insert_and_fetch_box_return_record(self) -> None:
        insert_box_return_record(
            self.conn,
            {
                "personnel_id": 2,
                "return_date": "2026-03-21",
                "quantity": 1,
                "condition_status": "Temiz",
                "payout_amount": 250.0,
                "waived": 0,
                "notes": "İade alındı",
            },
        )
        self.conn.commit()

        df = fetch_box_return_management_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["full_name"], "Ayse Yilmaz")
        self.assertEqual(df.iloc[0]["condition_status"], "Temiz")
        self.assertAlmostEqual(float(df.iloc[0]["payout_amount"]), 250.0)

    def test_fetch_equipment_sales_profit_df_groups_only_sales(self) -> None:
        self.conn.execute(
            """
            INSERT INTO courier_equipment_issues
            (personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, auto_source_key, installment_count, sale_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-03-20", "Kask", 2, 500.0, 750.0, 20.0, "", 2, "Satış", ""),
        )
        self.conn.execute(
            """
            INSERT INTO courier_equipment_issues
            (personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, auto_source_key, installment_count, sale_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (2, "2026-03-21", "Kask", 1, 500.0, 700.0, 20.0, "", 1, "Depozit / Teslim", ""),
        )
        self.conn.commit()

        df = fetch_equipment_sales_profit_df(self.conn)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["item_name"], "Kask")
        self.assertEqual(int(row["sold_qty"]), 2)
        self.assertAlmostEqual(float(row["total_cost"]), 1000.0)
        self.assertAlmostEqual(float(row["total_sale"]), 1500.0)
        self.assertAlmostEqual(float(row["gross_profit"]), 500.0)

    def test_fetch_equipment_purchase_summary_df_builds_weighted_unit_cost(self) -> None:
        self.conn.execute(
            "INSERT INTO inventory_purchases (purchase_date, item_name, quantity, total_invoice_amount) VALUES (?, ?, ?, ?)",
            ("2026-03-01", "Kask", 10, 12000.0),
        )
        self.conn.execute(
            "INSERT INTO inventory_purchases (purchase_date, item_name, quantity, total_invoice_amount) VALUES (?, ?, ?, ?)",
            ("2026-03-10", "Kask", 5, 7500.0),
        )
        self.conn.commit()

        df = fetch_equipment_purchase_summary_df(self.conn)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["item_name"], "Kask")
        self.assertEqual(int(row["purchased_qty"]), 15)
        self.assertAlmostEqual(float(row["purchased_total"]), 19500.0)
        self.assertAlmostEqual(float(row["weighted_unit_cost"]), 1300.0)
