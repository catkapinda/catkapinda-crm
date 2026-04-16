from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.main import create_app


def _fake_admin_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=1,
        identity="admin@catkapinda.com",
        email="admin@catkapinda.com",
        phone="05000000000",
        full_name="Admin Kullanıcı",
        role="admin",
        role_display="Admin",
        must_change_password=False,
        allowed_actions=["backup.manage"],
        expires_at="2099-01-01T00:00:00",
        token="token",
    )


def _build_client() -> TestClient:
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_current_user] = _fake_admin_user
    app.dependency_overrides[get_db] = lambda: object()
    return TestClient(app)


def test_backup_status_route_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.backups.build_backup_status",
        lambda conn: {
            "module": "backups",
            "status": "active",
            "active_backend": "sqlite",
            "active_backend_label": "Yerel veritabanı",
            "can_download_archive": True,
            "archive_download_label": "Tüm tabloları yedek olarak indir",
            "suggested_archive_name": "tam_yedek.zip",
            "can_download_sqlite_file": True,
            "sqlite_download_label": "SQLite veritabanı dosyasını indir",
            "suggested_sqlite_name": "catkapinda.db",
            "sqlite_download_note": "Önce SQLite dosyasını indir.",
            "can_import_sqlite_backup": False,
            "import_title": "SQLite yedeğini içe aktar",
            "import_note": "Bu akış kapalı.",
        },
    )
    client = _build_client()

    response = client.get("/api/backups/status")

    assert response.status_code == 200
    assert response.json()["active_backend_label"] == "Yerel veritabanı"


def test_backup_archive_download_route(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.backups.build_table_backup_zip_bytes",
        lambda conn: b"zip-payload",
    )
    client = _build_client()

    response = client.get("/api/backups/archive")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content == b"zip-payload"


def test_backup_sqlite_file_download_route(monkeypatch, tmp_path: Path):
    sqlite_path = tmp_path / "backup.db"
    sqlite_path.write_bytes(b"sqlite-bytes")
    monkeypatch.setattr(
        "app.api.routes.backups.resolve_sqlite_backup_file",
        lambda conn: sqlite_path,
    )
    client = _build_client()

    response = client.get("/api/backups/sqlite-file")

    assert response.status_code == 200
    assert response.content == b"sqlite-bytes"


def test_import_sqlite_route(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.backups.import_sqlite_backup_into_current_db",
        lambda conn, sqlite_path: {
            "message": "SQLite yedeği başarıyla harici veritabanına aktarıldı.",
            "imported_anything": True,
        },
    )
    client = _build_client()

    response = client.post(
        "/api/backups/import-sqlite",
        content=b"sqlite-bytes",
        headers={"X-Backup-File-Name": "backup.db", "Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200
    assert response.json()["imported_anything"] is True
