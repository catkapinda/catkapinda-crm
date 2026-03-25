from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.auth_engine import (
    can_email_temporary_password_for_user,
    can_issue_phone_login_code,
    can_phone_login_for_user,
    configure_auth_engine,
    extract_mobile_auth_personnel_id,
    get_auth_user,
    issue_phone_login_code,
    mask_auth_phone,
    normalize_auth_identity,
    normalize_auth_phone,
    sync_mobile_auth_users,
    verify_phone_login_code,
)
from infrastructure.db_engine import CompatConnection


def _get_row_value(row, key: str, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            role_display TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE auth_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE auth_phone_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_user_id INTEGER NOT NULL,
            phone TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'login',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TEXT
        );

        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            status TEXT NOT NULL
        );
        """
    )
    return conn


class AuthEngineTests(TestCase):
    def setUp(self) -> None:
        configure_auth_engine(
            get_row_value_fn=_get_row_value,
            safe_int_fn=_safe_int,
            default_auth_users=[],
            default_auth_password="123456",
            legacy_auth_identities=set(),
            password_hash_iterations=1000,
            login_logo_candidates=[],
            auth_query_key="ck_session",
            auth_session_days=30,
            sms_phone_auth_email_allowlist={"ebru@catkapinda.com", "mert.kurtulus@catkapinda.com", "muhammed.terim@catkapinda.com"},
        )
        self.conn = _make_conn()

    def tearDown(self) -> None:
        self.conn.close()

    def test_normalize_auth_identity_accepts_phone_numbers(self) -> None:
        self.assertEqual(normalize_auth_phone("0532 123 45 67"), "5321234567")
        self.assertEqual(normalize_auth_identity("+90 532 123 45 67"), "5321234567")
        self.assertEqual(normalize_auth_identity("Ebru@CatKapinda.com"), "ebru@catkapinda.com")

    def test_get_auth_user_can_find_row_by_phone(self) -> None:
        self.conn.execute(
            """
            INSERT INTO auth_users (
                email, phone, full_name, role, role_display, password_hash,
                is_active, must_change_password, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mobile.personnel.7@auth.catkapinda.local",
                "5321234567",
                "Emine Ebru Aslan",
                "mobile_ops",
                "Mobil Operasyon",
                "hash",
                1,
                1,
                "2026-03-24T10:00:00",
                "2026-03-24T10:00:00",
            ),
        )
        self.conn.commit()

        row = get_auth_user(self.conn, "0532 123 45 67")
        self.assertIsNotNone(row)
        self.assertEqual(row["full_name"], "Emine Ebru Aslan")

    def test_get_auth_user_falls_back_to_email_when_phone_column_is_missing(self) -> None:
        raw_conn = sqlite3.connect(":memory:")
        raw_conn.row_factory = sqlite3.Row
        conn = CompatConnection(raw_conn, "sqlite")
        conn.executescript(
            """
            CREATE TABLE auth_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                role_display TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            );
            """
        )
        conn.execute(
            """
            INSERT INTO auth_users (
                email, full_name, role, role_display, password_hash,
                is_active, must_change_password, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ebru@catkapinda.com",
                "Emine Ebru Aslan",
                "admin",
                "Yönetici",
                "hash",
                1,
                0,
                "2026-03-24T10:00:00",
                "2026-03-24T10:00:00",
            ),
        )
        conn.commit()

        row = get_auth_user(conn, "ebru@catkapinda.com")
        self.assertIsNotNone(row)
        self.assertEqual(row["full_name"], "Emine Ebru Aslan")
        conn.close()

    def test_sync_mobile_auth_users_creates_mobile_ops_auth_rows(self) -> None:
        self.conn.execute(
            "INSERT INTO personnel (full_name, role, phone, status) VALUES (?, ?, ?, ?)",
            ("Ali Veli", "Joker", "0532 111 22 33", "Aktif"),
        )
        self.conn.commit()

        sync_mobile_auth_users(self.conn)

        row = self.conn.execute(
            "SELECT email, phone, role, role_display, must_change_password FROM auth_users WHERE phone = ?",
            ("5321112233",),
        ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["role"], "mobile_ops")
        self.assertEqual(row["role_display"], "Mobil Operasyon")
        self.assertEqual(row["must_change_password"], 1)

    def test_extract_mobile_auth_personnel_id_parses_placeholder_email(self) -> None:
        self.assertEqual(
            extract_mobile_auth_personnel_id("mobile.personnel.17@auth.catkapinda.local"),
            17,
        )
        self.assertEqual(extract_mobile_auth_personnel_id("ebru@catkapinda.com"), 0)

    def test_can_email_temporary_password_for_user_rejects_mobile_placeholder_emails(self) -> None:
        self.assertFalse(
            can_email_temporary_password_for_user(
                {"email": "mobile.personnel.3@auth.catkapinda.local"}
            )
        )
        self.assertTrue(
            can_email_temporary_password_for_user(
                {"email": "ebru@catkapinda.com"}
            )
        )

    def test_phone_login_helpers_issue_and_verify_code(self) -> None:
        self.conn.execute(
            "INSERT INTO personnel (id, full_name, role, phone, status) VALUES (?, ?, ?, ?, ?)",
            (9, "Ali Veli", "Bölge Müdürü", "0532 765 43 21", "Aktif"),
        )
        sync_mobile_auth_users(self.conn)
        self.conn.commit()

        user_row = get_auth_user(self.conn, "0532 765 43 21")
        self.assertTrue(can_phone_login_for_user(user_row))
        self.assertTrue(can_issue_phone_login_code(self.conn, user_row))
        self.assertEqual(mask_auth_phone("0532 765 43 21"), "0532 *** ** 21")

        login_code = issue_phone_login_code(self.conn, user_row)
        self.assertEqual(len(login_code), 6)

        verified_user = verify_phone_login_code(self.conn, "0532 765 43 21", login_code)
        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user["full_name"], "Ali Veli")
        self.assertIsNone(verify_phone_login_code(self.conn, "0532 765 43 21", login_code))

    def test_joker_cannot_receive_phone_login_code(self) -> None:
        self.conn.execute(
            "INSERT INTO personnel (id, full_name, role, phone, status) VALUES (?, ?, ?, ?, ?)",
            (12, "Joker Kullanici", "Joker", "0532 999 88 77", "Aktif"),
        )
        sync_mobile_auth_users(self.conn)
        self.conn.commit()

        user_row = get_auth_user(self.conn, "0532 999 88 77")
        self.assertIsNotNone(user_row)
        self.assertTrue(can_phone_login_for_user(user_row))
        self.assertFalse(can_issue_phone_login_code(self.conn, user_row))

    def test_allowlisted_admin_can_receive_phone_login_code(self) -> None:
        self.conn.execute(
            """
            INSERT INTO auth_users (
                email, phone, full_name, role, role_display, password_hash,
                is_active, must_change_password, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mert.kurtulus@catkapinda.com",
                "05335557788",
                "Mert Kurtuluş",
                "admin",
                "Yönetim Kurulu / Yönetici",
                "hash",
                1,
                0,
                "2026-03-25T10:00:00",
                "2026-03-25T10:00:00",
            ),
        )
        self.conn.commit()

        user_row = get_auth_user(self.conn, "0533 555 77 88")
        self.assertIsNotNone(user_row)
        self.assertTrue(can_phone_login_for_user(user_row))
        self.assertTrue(can_issue_phone_login_code(self.conn, user_row))

    def test_non_allowlisted_admin_cannot_receive_phone_login_code(self) -> None:
        self.conn.execute(
            """
            INSERT INTO auth_users (
                email, phone, full_name, role, role_display, password_hash,
                is_active, must_change_password, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "baska.yonetici@catkapinda.com",
                "05335557799",
                "Başka Yönetici",
                "admin",
                "Yönetim Kurulu / Yönetici",
                "hash",
                1,
                0,
                "2026-03-25T10:00:00",
                "2026-03-25T10:00:00",
            ),
        )
        self.conn.commit()

        user_row = get_auth_user(self.conn, "0533 555 77 99")
        self.assertIsNotNone(user_row)
        self.assertTrue(can_phone_login_for_user(user_row))
        self.assertFalse(can_issue_phone_login_code(self.conn, user_row))
