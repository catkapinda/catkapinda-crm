from pathlib import Path

from app.core.local_doctor import build_local_doctor_report, write_backend_env_file


def test_local_doctor_flags_missing_database_url(tmp_path: Path):
    v2_root = tmp_path / "v2"
    (v2_root / "backend").mkdir(parents=True)
    (v2_root / "frontend").mkdir(parents=True)
    (v2_root / "frontend" / ".env.local").write_text(
        "NEXT_PUBLIC_V2_API_BASE_URL=/v2-api\nCK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000\n",
        encoding="utf-8",
    )

    report = build_local_doctor_report(v2_root, {})

    assert report["ready"] is False
    assert report["database_url_present"] is False
    assert report["frontend_proxy_target"] == "http://127.0.0.1:8000"
    assert any("Backend veritabani URL'i eksik" in item for item in report["blocking_items"])


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
