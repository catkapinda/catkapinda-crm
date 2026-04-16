from __future__ import annotations

from pydantic import BaseModel


class BackupStatusResponse(BaseModel):
    module: str
    status: str
    active_backend: str
    active_backend_label: str
    can_download_archive: bool
    archive_download_label: str
    suggested_archive_name: str
    can_download_sqlite_file: bool
    sqlite_download_label: str
    suggested_sqlite_name: str | None = None
    sqlite_download_note: str = ""
    can_import_sqlite_backup: bool
    import_title: str
    import_note: str


class BackupImportResponse(BaseModel):
    message: str
    imported_anything: bool
