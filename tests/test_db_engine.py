from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection, cache_db_read, clear_runtime_data_cache, fetch_df


class DbEngineCacheTests(TestCase):
    def setUp(self) -> None:
        clear_runtime_data_cache()

    def tearDown(self) -> None:
        clear_runtime_data_cache()

    def test_cached_db_reads_are_reused_until_commit_invalidates_them(self) -> None:
        raw_conn = sqlite3.connect(":memory:")
        raw_conn.row_factory = sqlite3.Row
        conn = CompatConnection(raw_conn, "sqlite")
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT)")
        conn.execute("INSERT INTO sample (value) VALUES (?)", ("ilk",))
        conn.commit()

        calls = {"count": 0}

        @cache_db_read(ttl=30)
        def load_rows(active_conn: CompatConnection):
            calls["count"] += 1
            return fetch_df(active_conn, "SELECT value FROM sample ORDER BY id")

        first_df = load_rows(conn)
        second_df = load_rows(conn)
        self.assertEqual(calls["count"], 1)
        self.assertEqual(first_df.iloc[0]["value"], "ilk")
        self.assertEqual(second_df.iloc[0]["value"], "ilk")

        conn.execute("INSERT INTO sample (value) VALUES (?)", ("ikinci",))
        conn.commit()

        third_df = load_rows(conn)
        self.assertEqual(calls["count"], 2)
        self.assertEqual(third_df["value"].tolist(), ["ilk", "ikinci"])
