from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.deductions_repository import (
    delete_deduction_record,
    delete_deduction_records,
    fetch_deduction_management_df,
    insert_deduction_record,
    update_deduction_record,
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

        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            deduction_date TEXT NOT NULL,
            deduction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            auto_source_key TEXT
        );
        """
    )
    return conn


class DeductionsRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.execute("INSERT INTO personnel (full_name) VALUES (?)", ("Ali Veli",))
        self.conn.execute("INSERT INTO personnel (full_name) VALUES (?)", ("Ayse Yilmaz",))
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_deduction_record(self) -> None:
        insert_deduction_record(
            self.conn,
            {
                "personnel_id": 1,
                "deduction_date": "2026-03-31",
                "deduction_type": "Yakıt",
                "amount": 750.0,
                "notes": "Mart yakit",
            },
        )
        self.conn.commit()

        df = fetch_deduction_management_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["personel"], "Ali Veli")
        self.assertEqual(df.iloc[0]["deduction_type"], "Yakıt")
        self.assertEqual(float(df.iloc[0]["amount"]), 750.0)

    def test_update_deduction_record(self) -> None:
        insert_deduction_record(
            self.conn,
            {
                "personnel_id": 1,
                "deduction_date": "2026-03-31",
                "deduction_type": "Yakıt",
                "amount": 750.0,
                "notes": "Mart yakit",
            },
        )
        self.conn.commit()

        update_deduction_record(
            self.conn,
            1,
            {
                "personnel_id": 2,
                "deduction_date": "2026-04-01",
                "deduction_type": "HGS",
                "amount": 900.0,
                "notes": "Nisan hgs",
            },
        )
        self.conn.commit()

        row = self.conn.execute(
            "SELECT personnel_id, deduction_date, deduction_type, amount, notes FROM deductions WHERE id = ?",
            (1,),
        ).fetchone()
        self.assertEqual(row["personnel_id"], 2)
        self.assertEqual(row["deduction_date"], "2026-04-01")
        self.assertEqual(row["deduction_type"], "HGS")
        self.assertEqual(float(row["amount"]), 900.0)
        self.assertEqual(row["notes"], "Nisan hgs")

    def test_delete_deduction_record(self) -> None:
        insert_deduction_record(
            self.conn,
            {
                "personnel_id": 1,
                "deduction_date": "2026-03-31",
                "deduction_type": "Yakıt",
                "amount": 750.0,
                "notes": "",
            },
        )
        self.conn.commit()

        delete_deduction_record(self.conn, 1)
        self.conn.commit()

        count_row = self.conn.execute("SELECT COUNT(*) AS count_value FROM deductions").fetchone()
        self.assertEqual(int(count_row["count_value"]), 0)

    def test_bulk_delete_deduction_records(self) -> None:
        for personnel_id in (1, 2, 1):
            insert_deduction_record(
                self.conn,
                {
                    "personnel_id": personnel_id,
                    "deduction_date": "2026-03-31",
                    "deduction_type": "Yakıt",
                    "amount": 500.0,
                    "notes": "",
                },
            )
        self.conn.commit()

        deleted_count = delete_deduction_records(self.conn, [1, 3])
        self.conn.commit()

        remaining = self.conn.execute("SELECT id FROM deductions ORDER BY id").fetchall()
        self.assertEqual(deleted_count, 2)
        self.assertEqual([row["id"] for row in remaining], [2])
