from __future__ import annotations

import csv
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
import sqlite3
import zipfile
from typing import Any

from app.core.database import resolve_local_sqlite_fallback_path
from app.schemas.backups import BackupImportResponse, BackupStatusResponse

TABLE_EXPORT_ORDER = [
    "restaurants",
    "sales_leads",
    "personnel",
    "personnel_role_history",
    "personnel_vehicle_history",
    "plate_history",
    "daily_entries",
    "deductions",
    "inventory_purchases",
    "courier_equipment_issues",
    "box_returns",
    "auth_users",
    "auth_sessions",
    "audit_logs",
]

OPERATIONAL_TABLES = [
    "restaurants",
    "personnel",
    "daily_entries",
    "deductions",
]


def _table_has_rows(conn: Any, table_name: str) -> bool:
    try:
        row = conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
    except Exception:
        return False
    return row is not None


def database_has_operational_data(conn: Any) -> bool:
    return any(_table_has_rows(conn, table_name) for table_name in OPERATIONAL_TABLES)


def build_backup_status(conn: Any) -> BackupStatusResponse:
    backend = str(getattr(conn, "backend", "postgres") or "postgres")
    backend_label = "Harici veritabanı" if backend == "postgres" else "Yerel veritabanı"
    archive_name = f"catkapinda_tam_yedek_{date.today().isoformat()}.zip"

    sqlite_path = resolve_sqlite_backup_file(conn)
    if backend == "postgres":
        can_import = not database_has_operational_data(conn)
        import_note = (
            "Harici veritabanı şu an boş görünüyor. Daha önce indirdiğin `.db` yedeğini buradan içe alabiliriz."
            if can_import
            else "Harici veritabanında canlı veri var. Çakışma yaşamamak için SQLite içe aktarma kapalı."
        )
    else:
        can_import = False
        import_note = "SQLite içe aktarma yalnızca harici veritabanına geçiş sırasında açılır."

    return BackupStatusResponse(
        module="backups",
        status="active",
        active_backend=backend,
        active_backend_label=backend_label,
        can_download_archive=True,
        archive_download_label="Tüm tabloları yedek olarak indir",
        suggested_archive_name=archive_name,
        can_download_sqlite_file=sqlite_path is not None,
        sqlite_download_label="SQLite veritabanı dosyasını indir",
        suggested_sqlite_name=f"catkapinda_crm_{date.today().isoformat()}.db" if sqlite_path else None,
        sqlite_download_note=(
            "Harici veritabanına geçmeden önce bu dosyayı indirmen en güvenli adım olur."
            if sqlite_path
            else "Şu an doğrudan indirilebilir bir SQLite dosyası görünmüyor."
        ),
        can_import_sqlite_backup=can_import,
        import_title="SQLite yedeğini içe aktar",
        import_note=import_note,
    )


def _read_table_rows(conn: Any, table_name: str) -> tuple[list[str], list[Any]]:
    cursor = conn.execute(f"SELECT * FROM {table_name}")
    description = getattr(cursor, "description", None) or []
    columns = [str(column[0]) for column in description]
    rows = cursor.fetchall()
    return columns, rows


def _serialize_csv(columns: list[str], rows: list[Any]) -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        if isinstance(row, dict):
            writer.writerow([row.get(column, "") for column in columns])
            continue
        try:
            writer.writerow([row[column] for column in columns])
        except Exception:
            writer.writerow(list(row))
    return buffer.getvalue().encode("utf-8-sig")


def build_table_backup_zip_bytes(conn: Any) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for table_name in TABLE_EXPORT_ORDER:
            columns, rows = _read_table_rows(conn, table_name)
            if not columns:
                continue
            archive.writestr(f"{table_name}.csv", _serialize_csv(columns, rows))
    buffer.seek(0)
    return buffer.getvalue()


def resolve_sqlite_backup_file(conn: Any) -> Path | None:
    if str(getattr(conn, "backend", "")) != "sqlite":
        return None
    sqlite_path = resolve_local_sqlite_fallback_path()
    return sqlite_path if sqlite_path.exists() else None


def _reset_postgres_sequences(conn: Any, tables: list[str]) -> None:
    if str(getattr(conn, "backend", "")) != "postgres":
        return
    for table_name in tables:
        conn.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                EXISTS (SELECT 1 FROM {table_name})
            )
            """
        )
    conn.commit()


def import_sqlite_backup_into_current_db(conn: Any, sqlite_path: Path) -> BackupImportResponse:
    if str(getattr(conn, "backend", "")) != "postgres":
        raise ValueError("SQLite yedeği yalnızca harici veritabanına aktarılabilir.")
    if database_has_operational_data(conn):
        raise ValueError("Harici veritabanında canlı veri varken SQLite yedeği içe aktarılamaz.")
    if not sqlite_path.exists():
        raise ValueError("Seçilen SQLite yedeği bulunamadı.")

    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    imported_anything = False
    identity_tables: list[str] = []

    try:
        for table_name in TABLE_EXPORT_ORDER:
            columns = [row["name"] for row in source.execute(f"PRAGMA table_info({table_name})").fetchall()]
            if not columns:
                continue
            rows = source.execute(f"SELECT {', '.join(columns)} FROM {table_name}").fetchall()
            if not rows:
                continue
            placeholders = ", ".join(["%s"] * len(columns))
            payload = [tuple(row[column] for column in columns) for row in rows]
            with conn.cursor() as cursor:
                cursor.executemany(
                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                    payload,
                )
            imported_anything = True
            if "id" in columns and table_name != "auth_sessions":
                identity_tables.append(table_name)
        conn.commit()
        _reset_postgres_sequences(conn, identity_tables)
    except Exception:
        conn.rollback()
        raise
    finally:
        source.close()

    if imported_anything:
        return BackupImportResponse(
            message="SQLite yedeği başarıyla harici veritabanına aktarıldı.",
            imported_anything=True,
        )

    return BackupImportResponse(
        message="Yedek dosyasında aktarılacak veri bulunamadı.",
        imported_anything=False,
    )
