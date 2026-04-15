from pathlib import Path

from app.core import local_doctor
from app.core.local_doctor import (
    build_local_doctor_report,
    discover_current_app_seed_values,
    write_backend_env_file,
    write_backend_env_scaffold_file,
)


def test_local_doctor_flags_missing_database_url(tmp_path: Path, monkeypatch):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)
    (v2_root / "frontend").mkdir(parents=True)
    (v2_root / "frontend" / ".env.local").write_text(
        "NEXT_PUBLIC_V2_API_BASE_URL=/v2-api\nCK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(local_doctor, "discover_local_frontend_urls", lambda: [])

    report = build_local_doctor_report(v2_root, {})

    assert report["ready"] is False
    assert report["database_url_present"] is False
    assert report["frontend_proxy_target"] == "http://127.0.0.1:8000"
    assert report["suggested_frontend_url"] == "http://127.0.0.1:3000"
    assert any("Backend veritabani URL'i eksik" in item for item in report["blocking_items"])
    assert any("--write-backend-scaffold" in item for item in report["next_actions"])


def test_local_doctor_reports_detected_frontend_urls_and_duplicate_warning(tmp_path: Path, monkeypatch):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)
    (v2_root / "frontend").mkdir(parents=True)

    monkeypatch.setattr(local_doctor, "discover_local_frontend_urls", lambda: ["http://127.0.0.1:3000", "http://127.0.0.1:3001"])

    report = build_local_doctor_report(v2_root, {})

    assert report["detected_frontend_urls"] == ["http://127.0.0.1:3000", "http://127.0.0.1:3001"]
    assert report["suggested_frontend_url"] == "http://127.0.0.1:3000"
    assert any("Birden fazla local frontend oturumu" in item for item in report["warnings"])
    assert any("tek aktif frontend URL" in item for item in report["next_actions"])


def test_write_backend_env_file_uses_runtime_database_url(tmp_path: Path):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)
    (v2_root / "frontend").mkdir(parents=True)

    env_path = write_backend_env_file(
        v2_root,
        {
            "DATABASE_URL": "postgresql://local-user:secret@localhost:5432/postgres?sslmode=require",
            "CK_V2_DEFAULT_AUTH_PASSWORD": "GizliSifre123",
            "AUTH_EBRU_PHONE": "05321234567",
        },
    )

    content = env_path.read_text(encoding="utf-8")
    assert "CK_V2_DATABASE_URL=postgresql://local-user:secret@localhost:5432/postgres?sslmode=require" in content
    assert "CK_V2_DEFAULT_AUTH_PASSWORD=GizliSifre123" in content
    assert "AUTH_EBRU_PHONE=05321234567" in content
    assert "CK_V2_FRONTEND_BASE_URL=http://127.0.0.1:3000" in content


def test_write_backend_env_scaffold_file_can_prepare_partial_env(tmp_path: Path):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)

    env_path = write_backend_env_scaffold_file(
        v2_root,
        {"CK_V2_DEFAULT_AUTH_PASSWORD": "GizliSifre123"},
        current_app_seed_values={"AUTH_EBRU_PHONE": "05321234567"},
    )

    content = env_path.read_text(encoding="utf-8")
    assert "# CK_V2_DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require" in content
    assert "CK_V2_DEFAULT_AUTH_PASSWORD=GizliSifre123" in content
    assert "AUTH_EBRU_PHONE=05321234567" in content


def test_write_backend_env_scaffold_file_can_use_detected_frontend_url(tmp_path: Path):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)

    env_path = write_backend_env_scaffold_file(
        v2_root,
        {},
        frontend_url="http://127.0.0.1:3001",
    )

    content = env_path.read_text(encoding="utf-8")
    assert "CK_V2_FRONTEND_BASE_URL=http://127.0.0.1:3001" in content
    assert "CK_V2_PUBLIC_APP_URL=http://127.0.0.1:3001" in content


def test_discover_local_frontend_urls_falls_back_to_next_dev_process_ports(monkeypatch):
    class Completed:
        def __init__(self, stdout: str):
            self.stdout = stdout

    def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
        if command[:2] == ["lsof", "-nP"] and "-iTCP:3001" in command:
            return Completed("COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\nnode    90979 ebruaslan   17u  IPv6 0x0 0t0 TCP *:3001 (LISTEN)\n")
        if command[:2] == ["lsof", "-nP"]:
            return Completed("COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n")
        raise AssertionError(f"Beklenmeyen komut: {command}")

    monkeypatch.setattr(local_doctor, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("network disabled")))
    monkeypatch.setattr(local_doctor.subprocess, "run", fake_run)

    urls = local_doctor.discover_local_frontend_urls()

    assert urls == ["http://127.0.0.1:3001"]


def test_local_doctor_prefers_direct_database_url_command_when_backend_env_exists(tmp_path: Path):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)
    (v2_root / "frontend").mkdir(parents=True)
    (v2_root / "backend" / ".env").write_text(
        "CK_V2_APP_ENV=development\n# CK_V2_DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require\n",
        encoding="utf-8",
    )

    report = build_local_doctor_report(v2_root, {})

    assert report["backend_env_exists"] is True
    assert report["database_url_present"] is False
    assert any("--database-url '<postgresql://...>'" in item for item in report["next_actions"])


def test_current_app_seed_reads_real_secrets_and_ignores_template_placeholders(tmp_path: Path):
    current_root = tmp_path / "current-app"
    current_root.mkdir()
    (current_root / "secrets.template.toml").write_text(
        'DATABASE_URL = "postgresql://postgres:PAROLA@db.PROJE_REF.supabase.co:5432/postgres?sslmode=require"\n'
        '[auth]\n'
        'ebru_phone = "05XXXXXXXXX"\n',
        encoding="utf-8",
    )
    (current_root / "secrets.toml").write_text(
        'DATABASE_URL = "postgresql://real-user:real-pass@db.real.supabase.co:5432/postgres?sslmode=require"\n'
        '[auth]\n'
        'ebru_phone = "05321234567"\n'
        'mert_phone = "05331234567"\n',
        encoding="utf-8",
    )

    seed = discover_current_app_seed_values(current_root)

    assert seed["values"]["database_url"] == "postgresql://real-user:real-pass@db.real.supabase.co:5432/postgres?sslmode=require"
    assert seed["values"]["AUTH_EBRU_PHONE"] == "05321234567"
    assert seed["values"]["AUTH_MERT_PHONE"] == "05331234567"
    assert "workspace_secrets_template:DATABASE_URL" in seed["placeholders_detected"]


def test_write_backend_env_file_can_use_current_app_seed_values(tmp_path: Path):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)

    env_path = write_backend_env_file(
        v2_root,
        {},
        current_app_seed_values={
            "database_url": "postgresql://seed-user:seed-pass@db.real.supabase.co:5432/postgres?sslmode=require",
            "AUTH_EBRU_PHONE": "05321234567",
        },
    )

    content = env_path.read_text(encoding="utf-8")
    assert "CK_V2_DATABASE_URL=postgresql://seed-user:seed-pass@db.real.supabase.co:5432/postgres?sslmode=require" in content
    assert "AUTH_EBRU_PHONE=05321234567" in content
