import sqlite3

from app.core import database
from app.core.config import settings


def test_get_db_uses_local_sqlite_fallback(monkeypatch, tmp_path):
    sqlite_path = tmp_path / "catkapinda_crm.db"
    with sqlite3.connect(sqlite_path) as raw_conn:
        raw_conn.execute("CREATE TABLE restaurants (id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT)")
        raw_conn.commit()

    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "local_sqlite_fallback_enabled", True)
    monkeypatch.setattr(settings, "local_sqlite_path", str(sqlite_path))

    generator = database.get_db()
    conn = next(generator)
    try:
        assert getattr(conn, "backend", "") == "sqlite"
        row = conn.execute("SELECT COUNT(*) AS count FROM restaurants").fetchone()
        assert int(row["count"]) == 0
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def test_sqlite_compat_connection_normalizes_ilike_and_nulls_last():
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.execute("CREATE TABLE sample_rows (id INTEGER PRIMARY KEY, name TEXT, updated_at TEXT)")
    raw_conn.executemany(
        "INSERT INTO sample_rows (id, name, updated_at) VALUES (?, ?, ?)",
        [
            (1, "Alpha", "2026-04-01T10:00:00"),
            (2, "beta", None),
            (3, "alpine", "2026-04-02T10:00:00"),
        ],
    )
    conn = database.CompatConnection(raw_conn, "sqlite")

    rows = conn.execute(
        """
        SELECT name
        FROM sample_rows
        WHERE name ILIKE %s
        ORDER BY updated_at DESC NULLS LAST, id DESC
        """,
        ("%alp%",),
    ).fetchall()

    assert [row["name"] for row in rows] == ["alpine", "Alpha"]
