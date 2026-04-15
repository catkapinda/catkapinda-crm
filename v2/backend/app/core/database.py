from __future__ import annotations

from collections.abc import Generator, Sequence
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from fastapi import HTTPException
import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

LOCAL_SQLITE_SEED_PATHS = (
    Path.home() / "Documents" / "CatKapindaData" / "catkapinda_crm.db",
    Path(__file__).resolve().parents[4] / "catkapinda_crm.db",
)


class CompatCursor:
    def __init__(self, cursor: Any):
        self.cursor = cursor

    def __iter__(self):
        return iter(self.cursor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.cursor, name)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def close(self) -> None:
        try:
            self.cursor.close()
        except Exception:
            pass


class CompatConnection:
    def __init__(self, raw_conn: Any, backend: str):
        self.raw_conn = raw_conn
        self.backend = backend

    def execute(self, query: str, params: Sequence[Any] = ()):
        sql = query.replace("%s", "?") if self.backend == "sqlite" else query
        if self.backend == "sqlite":
            cursor = self.raw_conn.execute(sql, params)
            return CompatCursor(cursor)
        cursor = self.raw_conn.cursor()
        cursor.execute(sql, params)
        return CompatCursor(cursor)

    def executemany(self, query: str, param_sets: Sequence[Sequence[Any]]):
        sql = query.replace("%s", "?") if self.backend == "sqlite" else query
        if self.backend == "sqlite":
            cursor = self.raw_conn.executemany(sql, param_sets)
            return CompatCursor(cursor)
        cursor = self.raw_conn.cursor()
        cursor.executemany(sql, param_sets)
        return CompatCursor(cursor)

    def commit(self) -> None:
        self.raw_conn.commit()

    def rollback(self) -> None:
        self.raw_conn.rollback()

    def close(self) -> None:
        self.raw_conn.close()


def resolve_local_sqlite_fallback_path() -> Path:
    return Path(settings.resolved_local_sqlite_path).expanduser()


def local_sqlite_fallback_available() -> bool:
    if settings.app_env == "production" or not settings.local_sqlite_fallback_enabled:
        return False
    target_path = resolve_local_sqlite_fallback_path()
    return target_path.exists() or any(path.exists() for path in LOCAL_SQLITE_SEED_PATHS)


def ensure_local_sqlite_fallback_file() -> Path:
    target_path = resolve_local_sqlite_fallback_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        return target_path

    for seed_path in LOCAL_SQLITE_SEED_PATHS:
        if seed_path.exists() and seed_path != target_path:
            shutil.copy2(seed_path, target_path)
            return target_path

    sqlite3.connect(target_path).close()
    return target_path


def connect_local_sqlite_fallback() -> CompatConnection:
    sqlite_path = ensure_local_sqlite_fallback_file()
    raw_conn = sqlite3.connect(sqlite_path, check_same_thread=False)
    raw_conn.row_factory = sqlite3.Row
    return CompatConnection(raw_conn, "sqlite")


def get_db() -> Generator[psycopg.Connection | CompatConnection, None, None]:
    if settings.database_url:
        conn = psycopg.connect(
            settings.database_url,
            row_factory=dict_row,
            connect_timeout=5,
            application_name="catkapinda-crm-v2",
        )
        try:
            yield conn
        finally:
            conn.close()
        return

    if local_sqlite_fallback_available():
        conn = connect_local_sqlite_fallback()
        try:
            yield conn
        finally:
            conn.close()
        return

    raise HTTPException(
        status_code=503,
        detail="DATABASE_URL tanimli olmadigi icin v2 backend veritabanina baglanamiyor.",
    )
