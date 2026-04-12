from pathlib import Path
import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pilot_cutover_guard  # noqa: E402
import pilot_day_zero  # noqa: E402
import pilot_day_zero_verify  # noqa: E402
import pilot_gate  # noqa: E402
import pilot_preflight  # noqa: E402
import pilot_status_report  # noqa: E402


def sample_payload(*, phase: str = "ready_for_pilot", ready: bool = False, required_missing: list[str] | None = None) -> dict:
    return {
        "frontend": {
            "status": "ok",
            "releaseLabel": "front123",
        },
        "backend": {
            "status": "ok",
            "release_label": "back123",
            "required_missing_env_vars": required_missing or [],
            "optional_missing_env_vars": [],
            "auth": {
                "email_login": True,
                "phone_login": True,
                "sms_login": True,
                "admin_user_count": 3,
                "mobile_ops_user_count": 2,
                "default_password_configured": True,
            },
            "decision": {
                "title": "Bugun pilotu acabiliriz",
                "detail": "Pilot smoke ve login kontrolu ile devam edebiliriz.",
                "tone": "success",
                "primary_label": "Pilot login",
                "primary_href": "/login",
            },
            "cutover": {
                "phase": phase,
                "ready": ready,
                "summary": "Hazirlik ilerliyor",
                "modules_ready_count": 10,
                "modules_total_count": 10,
                "blocking_items": [],
                "remaining_items": [],
            },
            "pilot_links": [
                {"label": "Pilot Login", "href": "https://pilot.example.com/login"},
                {"label": "Pilot Status", "href": "https://pilot.example.com/status"},
            ],
            "command_pack": [
                {"title": "1. Env", "detail": "Hazirla", "command": "python env.py"},
            ],
            "smoke_commands": [
                {"label": "Normal Smoke", "command": "python smoke.py"},
            ],
            "helper_commands": [
                {"label": "Launch Packet", "category": "packet", "command": "python launch.py"},
                {"label": "Env", "category": "env", "command": "python env.py"},
                {"label": "Curl", "category": "quick-check", "command": "curl https://pilot.example.com/api/health"},
            ],
            "pilot_accounts": [
                {
                    "email": "ebru@catkapinda.com",
                    "full_name": "Ebru Aslan",
                    "role": "admin",
                    "has_phone": True,
                }
            ],
            "next_actions": ["Pilot login ekranini ac"],
            "services": [
                {
                    "name": "crmcatkapinda-v2-api",
                    "service_type": "backend",
                    "public_url": "https://pilot-api.example.com",
                    "health_path": "/api/health",
                },
                {
                    "name": "crmcatkapinda-v2",
                    "service_type": "frontend",
                    "public_url": "https://pilot.example.com",
                    "health_path": "/api/health",
                },
            ],
            "modules": [
                {"module": "attendance", "status": "active"},
                {"module": "personnel", "status": "active"},
            ],
        },
    }


def test_pilot_gate_passes_when_phase_is_ready_for_pilot():
    result = pilot_gate.build_gate_result(mode="pilot", payload=sample_payload())

    assert result["passed"] is True
    assert result["actual_phase"] == "ready_for_pilot"
    assert result["summary"] == "Pilot acilabilir."


def test_cutover_gate_blocks_until_ready_for_cutover():
    result = pilot_gate.build_gate_result(mode="cutover", payload=sample_payload(phase="ready_for_pilot", ready=False))

    assert result["passed"] is False
    assert result["summary"] == "Redirect cutover'a gecilemez."
    assert result["expected_phase"] == "ready_for_cutover"


def test_cutover_guard_allows_force_override():
    blocked = pilot_cutover_guard.build_guard_result(
        base_url="https://pilot.example.com",
        mode="redirect",
        payload=sample_payload(phase="ready_for_pilot", ready=False),
        streamlit_service_name="crmcatkapinda",
        force=False,
    )
    forced = pilot_cutover_guard.build_guard_result(
        base_url="https://pilot.example.com",
        mode="redirect",
        payload=sample_payload(phase="ready_for_pilot", ready=False),
        streamlit_service_name="crmcatkapinda",
        force=True,
    )

    assert blocked["allowed"] is False
    assert forced["allowed"] is True
    assert forced["env_bundle"]["crmcatkapinda"]["CK_V2_CUTOVER_MODE"] == "redirect"


def test_pilot_status_report_markdown_includes_key_sections():
    markdown = pilot_status_report.build_markdown_report(
        base_url="https://pilot.example.com",
        payload=sample_payload(),
    )

    assert "Cat Kapinda CRM v2 Pilot Status Report" in markdown
    assert "## Bugunun Karari" in markdown
    assert "## Cutover Ozet" in markdown
    assert "Pilot Login" in markdown


def test_preflight_bundle_writes_expected_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_preflight, "fetch_pilot_status", lambda base_url, timeout: sample_payload())

    result = pilot_preflight.build_preflight_bundle(
        base_url="https://pilot.example.com",
        timeout=5,
        output_dir=tmp_path,
    )

    assert result["pilot_gate"]["passed"] is True
    assert (tmp_path / "pilot-status-live.md").exists()
    assert (tmp_path / "pilot-status-live.json").exists()
    assert (tmp_path / "pilot-gate-pilot.json").exists()
    assert (tmp_path / "pilot-gate-cutover.json").exists()
    assert (tmp_path / "pilot-preflight-summary.md").exists()


def test_day_zero_bundle_writes_manifest_and_env_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())

    def fake_preflight_bundle(*, base_url: str, timeout: int, output_dir: Path) -> dict:
        (output_dir / "pilot-status-live.md").write_text("status", encoding="utf-8")
        (output_dir / "pilot-status-live.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-gate-pilot.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-gate-cutover.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-preflight-summary.md").write_text("summary", encoding="utf-8")
        return {
            "pilot_gate": {"passed": True},
            "cutover_gate": {"passed": False},
            "files": {
                "summary_markdown": str(output_dir / "pilot-preflight-summary.md"),
                "status_markdown": str(output_dir / "pilot-status-live.md"),
                "status_json": str(output_dir / "pilot-status-live.json"),
                "pilot_gate_json": str(output_dir / "pilot-gate-pilot.json"),
                "cutover_gate_json": str(output_dir / "pilot-gate-cutover.json"),
            },
        }

    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", fake_preflight_bundle)

    manifest = pilot_day_zero.build_day_zero_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        streamlit_url="https://crmcatkapinda.com",
        output_dir=tmp_path,
        timeout=5,
        database_url="postgresql://pilot",
        default_auth_password="secret",
        identity="ebru@catkapinda.com",
        password_placeholder="<sifre>",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
    )

    assert manifest["pilot_gate_passed"] is True
    assert manifest["cutover_gate_passed"] is False
    assert manifest["banner_guard_allowed"] is True
    assert manifest["redirect_guard_allowed"] is False
    assert manifest["verify_passed"] is True
    assert manifest["verify_missing_files_count"] == 0
    assert manifest["verify_consistency_issues_count"] == 0
    assert manifest["verify_archive_exists"] is True
    assert manifest["verify_recommended_next_step"] == "Day-zero kiti kullanima hazir."
    assert "archive_path" in manifest
    assert (tmp_path / "render-env-bundle.env").exists()
    assert (tmp_path / "streamlit-banner.env").exists()
    assert (tmp_path / "streamlit-redirect.env").exists()
    assert (tmp_path / "streamlit-banner-guard.json").exists()
    assert (tmp_path / "streamlit-redirect-guard.json").exists()
    assert (tmp_path / "streamlit-banner-guarded.env").exists()
    assert (tmp_path / "streamlit-redirect-guarded.env").exists()
    assert (tmp_path / "pilot-launch.md").exists()
    assert (tmp_path / "pilot-cutover.md").exists()
    assert (tmp_path / "pilot-day-zero-manifest.json").exists()
    assert (tmp_path / "pilot-day-zero-verify.json").exists()
    assert (tmp_path / "pilot-day-zero-verify.md").exists()
    assert (tmp_path / "00-START-HERE.md").exists()
    assert (tmp_path.parent / f"{tmp_path.name}.zip").exists()
    assert "verify_json" in manifest["files"]
    assert "verify_markdown" in manifest["files"]
    assert "CK_V2_CUTOVER_MODE=banner" in (tmp_path / "streamlit-banner-guarded.env").read_text(encoding="utf-8")
    assert "# guard blocked redirect env" in (tmp_path / "streamlit-redirect-guarded.env").read_text(encoding="utf-8")
    start_here = (tmp_path / "00-START-HERE.md").read_text(encoding="utf-8")
    assert "Verify: `PASS`" in start_here
    assert "Day-zero kiti kullanima hazir." in start_here


def test_day_zero_can_derive_api_url_from_status_payload():
    derived = pilot_day_zero._derive_api_url(sample_payload())

    assert derived == "https://pilot-api.example.com"


def test_day_zero_verify_passes_for_valid_bundle(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())

    def fake_preflight_bundle(*, base_url: str, timeout: int, output_dir: Path) -> dict:
        (output_dir / "pilot-status-live.md").write_text("status", encoding="utf-8")
        (output_dir / "pilot-status-live.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-gate-pilot.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-gate-cutover.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-preflight-summary.md").write_text("summary", encoding="utf-8")
        return {
            "pilot_gate": {"passed": True},
            "cutover_gate": {"passed": False},
            "files": {
                "summary_markdown": str(output_dir / "pilot-preflight-summary.md"),
                "status_markdown": str(output_dir / "pilot-status-live.md"),
                "status_json": str(output_dir / "pilot-status-live.json"),
                "pilot_gate_json": str(output_dir / "pilot-gate-pilot.json"),
                "cutover_gate_json": str(output_dir / "pilot-gate-cutover.json"),
            },
        }

    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", fake_preflight_bundle)

    pilot_day_zero.build_day_zero_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        streamlit_url="https://crmcatkapinda.com",
        output_dir=tmp_path,
        timeout=5,
        database_url="postgresql://pilot",
        default_auth_password="secret",
        identity="ebru@catkapinda.com",
        password_placeholder="<sifre>",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is True
    assert result["archive_exists"] is True
    assert result["archive_members_count"] > 0
    assert result["consistency_issues"] == []


def test_day_zero_verify_fails_when_archive_is_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())

    def fake_preflight_bundle(*, base_url: str, timeout: int, output_dir: Path) -> dict:
        (output_dir / "pilot-status-live.md").write_text("status", encoding="utf-8")
        (output_dir / "pilot-status-live.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-gate-pilot.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-gate-cutover.json").write_text("{}", encoding="utf-8")
        (output_dir / "pilot-preflight-summary.md").write_text("summary", encoding="utf-8")
        return {
            "pilot_gate": {"passed": True},
            "cutover_gate": {"passed": False},
            "files": {
                "summary_markdown": str(output_dir / "pilot-preflight-summary.md"),
                "status_markdown": str(output_dir / "pilot-status-live.md"),
                "status_json": str(output_dir / "pilot-status-live.json"),
                "pilot_gate_json": str(output_dir / "pilot-gate-pilot.json"),
                "cutover_gate_json": str(output_dir / "pilot-gate-cutover.json"),
            },
        }

    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", fake_preflight_bundle)

    manifest = pilot_day_zero.build_day_zero_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        streamlit_url="https://crmcatkapinda.com",
        output_dir=tmp_path,
        timeout=5,
        database_url="postgresql://pilot",
        default_auth_password="secret",
        identity="ebru@catkapinda.com",
        password_placeholder="<sifre>",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
    )

    archive_path = Path(manifest["archive_path"])
    archive_path.unlink()

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["archive_exists"] is False
    assert any("zip arsivi" in item for item in result["consistency_issues"])


def test_day_zero_verify_markdown_includes_core_sections():
    markdown = pilot_day_zero_verify.render_markdown_report(
        {
            "passed": True,
            "output_dir": "pilot-day-zero",
            "missing_files": [],
            "consistency_issues": [],
            "archive_exists": True,
            "archive_members_count": 18,
            "recommended_next_step": "Day-zero kiti kullanima hazir.",
        }
    )

    assert "# Cat Kapinda CRM v2 Day Zero Verify" in markdown
    assert "## Missing Files" in markdown
    assert "## Consistency Issues" in markdown


def test_day_zero_exit_code_respects_strict_verify_mode():
    manifest = {
        "pilot_gate_passed": True,
        "verify_passed": False,
    }

    assert pilot_day_zero.compute_exit_code(manifest, strict=False) == 0
    assert pilot_day_zero.compute_exit_code(manifest, strict=True) == 2
