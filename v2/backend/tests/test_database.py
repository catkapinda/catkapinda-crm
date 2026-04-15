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
