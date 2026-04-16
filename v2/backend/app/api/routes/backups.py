from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
import psycopg
from starlette.responses import FileResponse, Response

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.backups import BackupImportResponse, BackupStatusResponse
from app.services.backups import (
    build_backup_status,
    build_table_backup_zip_bytes,
    import_sqlite_backup_into_current_db,
    resolve_sqlite_backup_file,
)

router = APIRouter()


@router.get("/status", response_model=BackupStatusResponse)
def get_backup_status_route(
    user: Annotated[AuthenticatedUser, Depends(require_action("backup.manage"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> BackupStatusResponse:
    del user
    return build_backup_status(conn)


@router.get("/archive")
def download_archive_route(
    user: Annotated[AuthenticatedUser, Depends(require_action("backup.manage"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> Response:
    del user
    payload = build_table_backup_zip_bytes(conn)
    file_name = f"catkapinda_tam_yedek_{date.today().isoformat()}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )


@router.get("/sqlite-file")
def download_sqlite_file_route(
    user: Annotated[AuthenticatedUser, Depends(require_action("backup.manage"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> FileResponse:
    del user
    sqlite_path = resolve_sqlite_backup_file(conn)
    if not sqlite_path:
        raise HTTPException(status_code=404, detail="İndirilebilir bir SQLite yedeği bulunamadı.")
    return FileResponse(
        path=sqlite_path,
        filename=f"catkapinda_crm_{date.today().isoformat()}.db",
        media_type="application/octet-stream",
    )


@router.post("/import-sqlite", response_model=BackupImportResponse)
async def import_sqlite_route(
    user: Annotated[AuthenticatedUser, Depends(require_action("backup.manage"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    request: Request,
    x_backup_file_name: Annotated[str | None, Header()] = None,
) -> BackupImportResponse:
    del user
    suffix = Path(x_backup_file_name or "backup.db").suffix.lower()
    if suffix != ".db":
        raise HTTPException(status_code=422, detail="Yalnızca `.db` uzantılı SQLite yedeği yüklenebilir.")

    temp_path: Path | None = None
    try:
        payload = await request.body()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            temp_file.write(payload)
            temp_path = Path(temp_file.name)
        return import_sqlite_backup_into_current_db(conn, temp_path)
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
