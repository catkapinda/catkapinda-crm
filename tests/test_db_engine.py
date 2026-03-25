from __future__ import annotations

import os
import sqlite3
from unittest import TestCase
from unittest.mock import patch

from infrastructure import db_engine
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


class DbEngineConfigTests(TestCase):
    def tearDown(self) -> None:
        clear_runtime_data_cache()

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://env-user:env-pass@env-host:5432/postgres?sslmode=require",
        },
        clear=True,
    )
    def test_database_url_env_takes_priority(self) -> None:
        with patch.object(
            db_engine.st,
            "secrets",
            {"database": {"url": "postgresql://secret-user:secret-pass@secret-host:5432/postgres?sslmode=require"}},
        ):
            self.assertEqual(
                db_engine.get_database_config(),
                "postgresql://env-user:env-pass@env-host:5432/postgres?sslmode=require",
            )

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "db.example.com",
            "DB_PORT": "5439",
            "DB_NAME": "crm",
            "DB_USER": "db-user",
            "DB_PASSWORD": "db-pass",
            "DB_SSLMODE": "require",
        },
        clear=True,
    )
    def test_split_env_database_config_is_supported(self) -> None:
        with patch.object(db_engine.st, "secrets", {}):
            self.assertEqual(
                db_engine.get_database_config(),
                {
                    "host": "db.example.com",
                    "port": 5439,
                    "dbname": "crm",
                    "user": "db-user",
                    "password": "db-pass",
                    "sslmode": "require",
                },
            )

    def test_connect_database_retries_postgres_before_failing(self) -> None:
        expected_error = RuntimeError("temp fail")
        with (
            patch.object(db_engine, "get_database_config", return_value="postgresql://demo"),
            patch.object(db_engine, "connect_postgres", side_effect=[expected_error, expected_error, expected_error]) as connect_mock,
            patch.object(db_engine.time, "sleep") as sleep_mock,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                db_engine.connect_database()

        self.assertIn("Veritabanina su an ulasilamiyor", str(ctx.exception))
        self.assertEqual(connect_mock.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)
