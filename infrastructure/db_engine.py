from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st


_APP_DATA_DIR: Path | None = None
_DB_PATH: Path | None = None
_LEGACY_DB_PATHS: list[Path] = []


def _get_streamlit_secrets_mapping() -> Any | None:
    try:
        return st.secrets
    except Exception:
        return None


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


def _derive_default_cache_key(raw_conn: Any, backend: str) -> str:
    if backend == "sqlite":
        try:
            rows = raw_conn.execute("PRAGMA database_list").fetchall()
            for row in rows:
                row_values = tuple(row)
                if len(row_values) < 3:
                    continue
                db_name = str(row_values[1] or "")
                db_path = str(row_values[2] or "").strip()
                if db_name != "main":
                    continue
                if db_path:
                    return f"sqlite:{Path(db_path).expanduser().resolve()}"
        except Exception:
            pass
    return f"{backend}:{id(raw_conn)}"


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
    def __init__(self, raw_conn: Any, backend: str, *, cache_key: str | None = None):
        self.raw_conn = raw_conn
        self.backend = backend
        self.cache_key = cache_key or _derive_default_cache_key(raw_conn, backend)

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
        clear_runtime_data_cache()

    def rollback(self) -> None:
        self.raw_conn.rollback()

    def backup(self, target_conn: Any) -> None:
        if self.backend != "sqlite":
            raise NotImplementedError("Yedekleme işlemi sadece SQLite için desteklenir.")
        self.raw_conn.backup(target_conn)

    def close(self) -> None:
        self.raw_conn.close()


def _iter_database_config_candidates() -> list[tuple[str, str | dict[str, Any]]]:
    candidates: list[tuple[str, str | dict[str, Any]]] = []
    seen: set[str] = set()

    def add_candidate(label: str, value: str | dict[str, Any] | None) -> None:
        if not value:
            return
        if isinstance(value, dict):
            fingerprint = "dict:" + json.dumps(value, sort_keys=True, ensure_ascii=False)
        else:
            fingerprint = f"url:{str(value).strip()}"
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        candidates.append((label, value))

    env_value = os.getenv("DATABASE_URL")
    add_candidate("render_database_url", env_value)

    env_host = (os.getenv("DB_HOST") or os.getenv("DATABASE_HOST") or "").strip()
    env_user = (os.getenv("DB_USER") or os.getenv("DATABASE_USER") or "").strip()
    env_password = os.getenv("DB_PASSWORD") or os.getenv("DATABASE_PASSWORD")
    if env_host and env_user and env_password:
        add_candidate(
            "render_split_database_env",
            {
                "host": env_host,
                "port": int(os.getenv("DB_PORT") or os.getenv("DATABASE_PORT") or 5432),
                "dbname": (
                    os.getenv("DB_NAME")
                    or os.getenv("DATABASE_NAME")
                    or os.getenv("DB_DATABASE")
                    or "postgres"
                ).strip(),
                "user": env_user,
                "password": str(env_password),
                "sslmode": (os.getenv("DB_SSLMODE") or os.getenv("DATABASE_SSLMODE") or "require").strip() or "require",
            },
        )

    secrets_mapping = _get_streamlit_secrets_mapping()
    try:
        if secrets_mapping and "database" in secrets_mapping:
            db_secrets = secrets_mapping["database"]
            if "url" in db_secrets:
                add_candidate("streamlit_database_url", db_secrets["url"])
            required = {"host", "user", "password"}
            if required.issubset(set(db_secrets.keys())):
                add_candidate(
                    "streamlit_database_mapping",
                    {
                        "host": str(db_secrets["host"]).strip(),
                        "port": int(db_secrets.get("port", 5432)),
                        "dbname": str(db_secrets.get("dbname", db_secrets.get("database", "postgres"))).strip(),
                        "user": str(db_secrets["user"]).strip(),
                        "password": str(db_secrets["password"]),
                        "sslmode": str(db_secrets.get("sslmode", "require")).strip() or "require",
                    },
                )
        if secrets_mapping and "DATABASE_URL" in secrets_mapping:
            add_candidate("streamlit_root_database_url", secrets_mapping["DATABASE_URL"])
    except Exception:
        pass
    return candidates


def _safe_database_target(database_config: str | dict[str, Any]) -> str:
    try:
        if isinstance(database_config, dict):
            return f"{database_config.get('host', '?')}:{database_config.get('port', 5432)}/{database_config.get('dbname', 'postgres')}"
        cleaned_url = (database_config or "").strip().strip('"').strip("'")
        parsed = urlsplit(cleaned_url)
        return f"{parsed.hostname or '?'}:{parsed.port or 5432}/{(parsed.path or '').lstrip('/') or 'postgres'}"
    except Exception:
        return "?"


def _classify_postgres_connect_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "password authentication failed" in message or "authentication failed" in message:
        return "Kullanici adi veya sifre reddedildi"
    if "timeout expired" in message or "timed out" in message or "timeout" in message:
        return "Baglanti zaman asimina ugradi"
    if "could not translate host name" in message or "name or service not known" in message:
        return "Host adi cozumlenemedi"
    if "connection refused" in message:
        return "Hedef sunucu baglantiyi reddetti"
    if "too many clients" in message or "max_client_conn" in message:
        return "Baglanti limiti dolu gorunuyor"
    if "server closed the connection unexpectedly" in message or "terminating connection" in message:
        return "Sunucu baglantiyi beklenmedik sekilde kapatti"
    if "ssl" in message and "failed" in message:
        return "SSL baglantisi kurulurken hata alindi"
    return "Veritabani erisimi basarisiz oldu"


def _short_exception_text(exc: Exception, *, max_len: int = 220) -> str:
    text = " ".join(str(exc).split()).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def describe_database_config_sources() -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for label, database_config in _iter_database_config_candidates():
        sources.append(
            {
                "label": label,
                "type": "mapping" if isinstance(database_config, dict) else "url",
                "target": _safe_database_target(database_config),
            }
        )
    return sources


def build_database_diagnostics_snapshot() -> dict[str, Any]:
    sources = describe_database_config_sources()
    labels = {entry["label"] for entry in sources}
    targets = " ".join(entry["target"] for entry in sources).lower()

    if not sources:
        summary = "Uygulama staging tarafinda okunabilir bir veritabani kaynagi bulamiyor."
    elif "supabase" in targets or "pooler" in targets:
        summary = "Veritabani kaynagi bulundu; sorun daha cok staging ile Supabase pooler arasindaki erisim veya credential tarafinda gorunuyor."
    else:
        summary = "Veritabani kaynagi bulundu; sorun baglanti kurulurken erisim ya da credential tarafinda gorunuyor."

    checklist: list[str] = []
    if "render_database_url" in labels:
        checklist.append("Render staging Environment icindeki DATABASE_URL degerini kontrol et.")
    if "render_split_database_env" in labels:
        checklist.append("Render staging tarafindaki DB_HOST / DB_USER / DB_PASSWORD alanlarini kontrol et.")
    if any(label.startswith("streamlit_") for label in labels):
        checklist.append("Streamlit secrets fallback degerleri eski ya da farkliysa staging ile ayni oldugunu kontrol et.")
    checklist.append("Env degisikligi yapildiysa staging servisine yeniden deploy ver.")
    if "supabase" in targets or "pooler" in targets:
        checklist.append("Supabase pooler tarafinda anlik erisim ya da limit sorunu olup olmadigini kontrol et.")

    return {
        "sources": sources,
        "summary": summary,
        "checklist": checklist,
    }


def get_database_config() -> str | dict[str, Any] | None:
    candidates = _iter_database_config_candidates()
    return candidates[0][1] if candidates else None


def connect_postgres(database_config: str | dict[str, Any]) -> CompatConnection:
    import psycopg
    from psycopg.rows import dict_row

    safe_target = "?"
    safe_user = "?"
    try:
        if isinstance(database_config, dict):
            safe_target = f"{database_config.get('host', '?')}:{database_config.get('port', 5432)}/{database_config.get('dbname', 'postgres')}"
            safe_user = str(database_config.get("user", "?") or "?")
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
            try:
                parsed = urlsplit(cleaned_url)
                safe_target = f"{parsed.hostname or '?'}:{parsed.port or 5432}/{(parsed.path or '').lstrip('/') or 'postgres'}"
                safe_user = parsed.username or "?"
            except Exception:
                safe_target = "?"
                safe_user = "?"
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
            f"Sebep: {_classify_postgres_connect_error(exc)}. "
            f"Teknik: {_short_exception_text(exc)}. "
            "Render Environment veya Streamlit secrets icindeki veritabani bilgilerini kontrol et."
        ) from exc
    return CompatConnection(
        raw_conn,
        "postgres",
        cache_key=f"postgres:{safe_target}:{safe_user}",
    )


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
    return CompatConnection(raw_conn, "sqlite", cache_key=f"sqlite:{_DB_PATH.expanduser().resolve()}")


def connect_database() -> CompatConnection:
    database_candidates = _iter_database_config_candidates()
    if database_candidates:
        last_error: RuntimeError | None = None
        attempted_labels: list[str] = []
        retry_delays = (0.0, 0.75, 1.5, 2.5, 4.0)
        for round_index, delay in enumerate(retry_delays, start=1):
            if delay:
                time.sleep(delay)
            for label, database_config in database_candidates:
                try:
                    return connect_postgres(database_config)
                except RuntimeError as exc:
                    last_error = exc
                    attempted_labels.append(label)
        if last_error is not None:
            attempted_sources = ", ".join(dict.fromkeys(attempted_labels)) or "database_url"
            raise RuntimeError(
                "Veritabanina su an ulasilamiyor. Baglanti otomatik olarak yeniden denendi ama kurulamadı. "
                f"Denenen kaynaklar: {attempted_sources}. "
                f"Son baglanti nedeni: {_short_exception_text(last_error)}. "
                "Lutfen kisa bir sure sonra tekrar deneyin. Sorun devam ederse Render Environment veya Streamlit secrets "
                "icindeki veritabani ayarlarini kontrol edin."
            ) from last_error
    return connect_sqlite()


def compat_connection_cache_key(conn: CompatConnection) -> str:
    return str(getattr(conn, "cache_key", f"{getattr(conn, 'backend', 'unknown')}:{id(conn)}"))


def cache_db_read(*, ttl: int = 30):
    return st.cache_data(
        show_spinner=False,
        ttl=ttl,
        hash_funcs={CompatConnection: compat_connection_cache_key},
    )


def clear_runtime_data_cache() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass


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
