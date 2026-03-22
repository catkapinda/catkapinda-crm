from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st


_APP_DATA_DIR: Path | None = None
_DB_PATH: Path | None = None
_LEGACY_DB_PATHS: list[Path] = []


def configure_db_engine(
    *,
    app_data_dir: Path,
    db_path: Path,
    legacy_db_paths: list[Path],
) -> None:
    global _APP_DATA_DIR
    global _DB_PATH
    global _LEGACY_DB_PATHS

    _APP_DATA_DIR = app_data_dir
    _DB_PATH = db_path
    _LEGACY_DB_PATHS = list(legacy_db_paths)


def split_sql_script(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def adapt_sql(query: str, backend: str) -> str:
    if backend == "postgres":
        return query.replace("?", "%s")
    return query


class CompatCursor:
    def __init__(self, cursor: Any):
        self.cursor = cursor

    def __iter__(self):
        return iter(self.cursor)

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
        sql = adapt_sql(query, self.backend)
        if self.backend == "sqlite":
            cursor = self.raw_conn.execute(sql, params)
            return CompatCursor(cursor)
        cursor = self.raw_conn.cursor()
        cursor.execute(sql, params)
        return CompatCursor(cursor)

    def executemany(self, query: str, param_sets: Iterable[Sequence[Any]]):
        sql = adapt_sql(query, self.backend)
        if self.backend == "sqlite":
            cursor = self.raw_conn.executemany(sql, param_sets)
            return CompatCursor(cursor)
        cursor = self.raw_conn.cursor()
        cursor.executemany(sql, list(param_sets))
        return CompatCursor(cursor)

    def executescript(self, script: str) -> None:
        if self.backend == "sqlite":
            self.raw_conn.executescript(script)
            return
        cursor = self.raw_conn.cursor()
        try:
            for statement in split_sql_script(script):
                cursor.execute(statement)
        finally:
            cursor.close()

    def commit(self) -> None:
        self.raw_conn.commit()

    def rollback(self) -> None:
        self.raw_conn.rollback()

    def backup(self, target_conn: Any) -> None:
        if self.backend != "sqlite":
            raise NotImplementedError("Yedekleme işlemi sadece SQLite için desteklenir.")
        self.raw_conn.backup(target_conn)

    def close(self) -> None:
        self.raw_conn.close()


def get_database_config() -> str | dict[str, Any] | None:
    try:
        if "database" in st.secrets:
            db_secrets = st.secrets["database"]
            if "url" in db_secrets:
                return db_secrets["url"]
            required = {"host", "user", "password"}
            if required.issubset(set(db_secrets.keys())):
                return {
                    "host": str(db_secrets["host"]).strip(),
                    "port": int(db_secrets.get("port", 5432)),
                    "dbname": str(db_secrets.get("dbname", db_secrets.get("database", "postgres"))).strip(),
                    "user": str(db_secrets["user"]).strip(),
                    "password": str(db_secrets["password"]),
                    "sslmode": str(db_secrets.get("sslmode", "require")).strip() or "require",
                }
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass

    env_value = os.getenv("DATABASE_URL")
    if env_value:
        return env_value
    return None


def connect_postgres(database_config: str | dict[str, Any]) -> CompatConnection:
    import psycopg
    from psycopg.rows import dict_row

    try:
        if isinstance(database_config, dict):
            raw_conn = psycopg.connect(
                host=database_config["host"],
                port=int(database_config.get("port", 5432)),
                dbname=database_config.get("dbname", "postgres"),
                user=database_config["user"],
                password=database_config["password"],
                sslmode=database_config.get("sslmode", "require"),
                row_factory=dict_row,
                connect_timeout=10,
            )
        else:
            cleaned_url = (database_config or "").strip().strip('"').strip("'")
            if "sslmode=" not in cleaned_url:
                separator = "&" if "?" in cleaned_url else "?"
                cleaned_url = f"{cleaned_url}{separator}sslmode=require"
            raw_conn = psycopg.connect(cleaned_url, row_factory=dict_row, connect_timeout=10)
    except Exception as exc:
        if isinstance(database_config, dict):
            safe_target = f"{database_config.get('host', '?')}:{database_config.get('port', 5432)}"
            safe_user = database_config.get("user", "?")
        else:
            cleaned_value = (database_config or "").strip().strip('"').strip("'")
            try:
                parsed = urlsplit(cleaned_value)
                safe_target = f"{parsed.hostname or '?'}:{parsed.port or 5432}"
                safe_user = parsed.username or "?"
            except Exception:
                safe_target = "?"
                safe_user = "?"
        raise RuntimeError(
            "PostgreSQL baglantisi kurulamadi. "
            f"Hedef: {safe_target} | Kullanici: {safe_user}. "
            "Supabase bilgilerini yeniden kopyalayip Streamlit Secrets'e kaydet."
        ) from exc
    return CompatConnection(raw_conn, "postgres")


def ensure_data_storage() -> Path | None:
    if _APP_DATA_DIR is None or _DB_PATH is None:
        raise RuntimeError("db_engine henüz yapılandırılmadı.")

    _APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if _DB_PATH.exists():
        return None

    candidates = [path for path in _LEGACY_DB_PATHS if path.exists() and path != _DB_PATH]
    if not candidates:
        return None

    latest_source = max(candidates, key=lambda path: path.stat().st_mtime)
    shutil.copy2(latest_source, _DB_PATH)
    return latest_source


def connect_sqlite() -> CompatConnection:
    if _DB_PATH is None:
        raise RuntimeError("db_engine henüz yapılandırılmadı.")
    ensure_data_storage()
    raw_conn = sqlite3.connect(_DB_PATH)
    raw_conn.row_factory = sqlite3.Row
    return CompatConnection(raw_conn, "sqlite")


def connect_database() -> CompatConnection:
    database_config = get_database_config()
    if database_config:
        return connect_postgres(database_config)
    return connect_sqlite()


def fetch_df(conn: CompatConnection, query: str, params: tuple = ()) -> pd.DataFrame:
    if conn.backend == "sqlite":
        return pd.read_sql_query(adapt_sql(query, conn.backend), conn.raw_conn, params=params)

    cursor = conn.execute(query, params)
    try:
        rows = cursor.fetchall()
    finally:
        cursor.close()

    if not rows:
        return pd.DataFrame()

    normalized_rows = []
    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append(row)
            continue
        try:
            normalized_rows.append(dict(row))
            continue
        except Exception:
            pass
        if hasattr(row, "keys"):
            try:
                normalized_rows.append({key: row[key] for key in row.keys()})
                continue
            except Exception:
                pass
        normalized_rows.append(dict(enumerate(row)))

    return pd.DataFrame(normalized_rows)
