from pathlib import Path
import sys

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import render_env_bundle  # noqa: E402


def test_build_bundle_accepts_https_urls_and_strong_password():
    bundle = render_env_bundle.build_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        default_auth_password="GucluPilot!2026",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
        cutover_mode="banner",
    )

    assert bundle["crmcatkapinda-v2-api"]["CK_V2_APP_ENV"] == "production"
    assert bundle["crmcatkapinda-v2-api"]["CK_V2_FRONTEND_BASE_URL"] == "https://pilot.example.com"
    assert bundle["crmcatkapinda-v2-api"]["CK_V2_API_PUBLIC_URL"] == "https://pilot-api.example.com"
    assert bundle["crmcatkapinda-v2-api"]["CK_V2_DEFAULT_AUTH_PASSWORD"] == "GucluPilot!2026"


def test_validate_public_url_rejects_non_https_public_url():
    with pytest.raises(ValueError, match="https"):
        render_env_bundle.validate_public_url("http://pilot.example.com", label="Frontend URL")


def test_validate_default_auth_password_rejects_weak_default_auth_password():
    with pytest.raises(ValueError, match="12 karakterli"):
        render_env_bundle.validate_default_auth_password("123456")


def test_validate_database_url_rejects_non_ssl_remote_database_url():
    with pytest.raises(ValueError, match="sslmode=require"):
        render_env_bundle.validate_database_url("postgresql://user:pass@db.example.com:5432/postgres")


def test_build_bundle_allows_placeholder_values_for_packet_generation():
    bundle = render_env_bundle.build_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        database_url="<mevcut-postgresql-url>",
        default_auth_password="<GucluParola!2026>",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
        cutover_mode="redirect",
    )

    assert bundle["crmcatkapinda-v2-api"]["CK_V2_DATABASE_URL"] == "<mevcut-postgresql-url>"
    assert bundle["crmcatkapinda-v2-api"]["CK_V2_DEFAULT_AUTH_PASSWORD"] == "<GucluParola!2026>"
    assert bundle["crmcatkapinda"]["CK_V2_CUTOVER_MODE"] == "redirect"


def test_build_validation_report_marks_values_ready_when_all_inputs_are_safe():
    report = render_env_bundle.build_validation_report(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require",
        default_auth_password="GucluPilot!2026",
    )

    assert report["passed"] is True
    assert report["normalized_frontend_url"] == "https://pilot.example.com"
    assert report["normalized_api_url"] == "https://pilot-api.example.com"
    assert report["blocking_items"] == []


def test_build_validation_report_blocks_placeholders_for_real_deploy():
    report = render_env_bundle.build_validation_report(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        database_url="<mevcut-postgresql-url>",
        default_auth_password="<pilot-sifresi>",
    )

    assert report["passed"] is False
    assert any("gercek bir deger" in item.lower() for item in report["blocking_items"])


def test_build_validation_report_blocks_insecure_values():
    report = render_env_bundle.build_validation_report(
        frontend_url="http://pilot.example.com",
        api_url="https://pilot-api.example.com",
        database_url="postgresql://user:pass@db.example.com:5432/postgres",
        default_auth_password="123456",
    )

    assert report["passed"] is False
    details = [entry["detail"] for entry in report["checks"]]
    assert any("https" in str(detail).lower() for detail in details)
    assert any("sslmode=require" in str(detail).lower() for detail in details)
    assert any("12 karakterli" in str(detail) for detail in details)
