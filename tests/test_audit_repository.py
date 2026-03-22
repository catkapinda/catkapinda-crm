from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.audit_repository import fetch_audit_log_df, insert_audit_log_record


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            actor_username TEXT,
            actor_full_name TEXT,
            actor_role TEXT,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            action_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            details_json TEXT
        );
        """
    )
    return conn


class AuditRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_audit_log_record(self) -> None:
        insert_audit_log_record(
            self.conn,
            {
                "created_at": "2026-03-22T18:00:00+00:00",
                "actor_username": "ebru",
                "actor_full_name": "Ebru Aslan",
                "actor_role": "admin",
                "entity_type": "personnel",
                "entity_id": "7",
                "action_type": "create",
                "summary": "Personel eklendi",
                "details_json": "{\"role\": \"Kurye\"}",
            },
        )
        self.conn.commit()

        df = fetch_audit_log_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["actor_full_name"], "Ebru Aslan")
        self.assertEqual(df.iloc[0]["entity_type"], "personnel")
        self.assertEqual(df.iloc[0]["action_type"], "create")

    def test_fetch_audit_log_df_orders_newest_first(self) -> None:
        for created_at, summary in [
            ("2026-03-22T18:00:00+00:00", "ilk"),
            ("2026-03-22T18:05:00+00:00", "ikinci"),
        ]:
            insert_audit_log_record(
                self.conn,
                {
                    "created_at": created_at,
                    "actor_username": "ebru",
                    "actor_full_name": "Ebru Aslan",
                    "actor_role": "admin",
                    "entity_type": "purchase",
                    "entity_id": "3",
                    "action_type": "update",
                    "summary": summary,
                    "details_json": "{}",
                },
            )
        self.conn.commit()

        df = fetch_audit_log_df(self.conn)
        self.assertEqual(df.iloc[0]["summary"], "ikinci")
        self.assertEqual(df.iloc[1]["summary"], "ilk")
