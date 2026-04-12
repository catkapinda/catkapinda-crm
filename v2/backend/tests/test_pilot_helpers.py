import json
from pathlib import Path
import sys
import zipfile


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pilot_cutover_guard  # noqa: E402
import pilot_day_zero  # noqa: E402
import pilot_day_zero_verify  # noqa: E402
import pilot_gate  # noqa: E402
import pilot_preflight  # noqa: E402
import pilot_smoke  # noqa: E402
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


def write_valid_preflight_artifacts(
    output_dir: Path,
    *,
    payload: dict | None = None,
    pilot_gate_result: dict | None = None,
    cutover_gate_result: dict | None = None,
    smoke_report: dict | None = None,
) -> dict[str, str]:
    payload = payload or sample_payload()
    pilot_gate_result = pilot_gate_result or {
        "passed": True,
        "summary": "Pilot acilabilir.",
        "recommended_next_step": "Devam",
        "blocking_items": [],
    }
    cutover_gate_result = cutover_gate_result or {
        "passed": False,
        "summary": "Redirect cutover'a gecilemez.",
        "recommended_next_step": "Bekle",
        "blocking_items": [],
    }

    base_url = "https://pilot.example.com"
    (output_dir / "pilot-status-live.md").write_text(
        pilot_status_report.build_markdown_report(base_url=base_url, payload=payload),
        encoding="utf-8",
    )
    (output_dir / "pilot-status-live.json").write_text(json.dumps(payload), encoding="utf-8")
    (output_dir / "pilot-gate-pilot.json").write_text(json.dumps(pilot_gate_result), encoding="utf-8")
    (output_dir / "pilot-gate-cutover.json").write_text(json.dumps(cutover_gate_result), encoding="utf-8")
    (output_dir / "pilot-preflight-summary.md").write_text(
        pilot_preflight._build_summary_markdown(
            base_url=base_url,
            generated_at="2026-01-01T00:00:00+00:00",
            payload=payload,
            pilot_gate=pilot_gate_result,
            cutover_gate=cutover_gate_result,
            output_dir=output_dir,
            smoke_report=smoke_report,
        ),
        encoding="utf-8",
    )

    files = {
        "summary_markdown": str(output_dir / "pilot-preflight-summary.md"),
        "status_markdown": str(output_dir / "pilot-status-live.md"),
        "status_json": str(output_dir / "pilot-status-live.json"),
        "pilot_gate_json": str(output_dir / "pilot-gate-pilot.json"),
        "cutover_gate_json": str(output_dir / "pilot-gate-cutover.json"),
    }
    if smoke_report is not None:
        (output_dir / "pilot-smoke-live.md").write_text(
            pilot_smoke.build_markdown_report(
                {
                    "base_url": base_url,
                    "preset": None,
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "timeout_seconds": 5,
                    "identity_provided": False,
                    "legacy_url": None,
                    "legacy_cutover_mode": None,
                    "overall_ok": smoke_report["overall_ok"],
                    "passed_count": 1 if smoke_report["overall_ok"] else 0,
                    "failed_count": smoke_report["failed_count"],
                    "decision": {
                        "status": "pass" if smoke_report["overall_ok"] else "blocking",
                        "headline": "Smoke report",
                        "primary_blocker": None,
                        "recommended_next_step": smoke_report["decision"]["recommended_next_step"],
                        "failing_checks": [],
                    },
                    "results": [],
                }
            ),
            encoding="utf-8",
        )
        (output_dir / "pilot-smoke-live.json").write_text(json.dumps(smoke_report), encoding="utf-8")
        files["smoke_markdown"] = str(output_dir / "pilot-smoke-live.md")
        files["smoke_json"] = str(output_dir / "pilot-smoke-live.json")
    return files


def make_fake_preflight_bundle(
    *,
    payload: dict | None = None,
    pilot_gate_result: dict | None = None,
    cutover_gate_result: dict | None = None,
    smoke_report: dict | None = None,
):
    payload = payload or sample_payload()
    default_pilot_gate = {
        "passed": True,
        "summary": "Pilot acilabilir.",
        "recommended_next_step": "Devam",
        "blocking_items": [],
    }
    default_cutover_gate = {
        "passed": False,
        "summary": "Redirect cutover'a gecilemez.",
        "recommended_next_step": "Bekle",
        "blocking_items": [],
    }
    pilot_gate_result = {**default_pilot_gate, **(pilot_gate_result or {})}
    cutover_gate_result = {**default_cutover_gate, **(cutover_gate_result or {})}
    if smoke_report is not None:
        smoke_report = {
            "overall_ok": False,
            "failed_count": 0,
            "decision": {
                "headline": "Smoke report",
                "recommended_next_step": "Smoke blokajlarini kapat.",
                "failing_checks": [],
            },
            **smoke_report,
        }
        smoke_report["decision"] = {
            "headline": "Smoke report",
            "recommended_next_step": "Smoke blokajlarini kapat.",
            "failing_checks": [],
            **(smoke_report.get("decision") or {}),
        }

    def fake_preflight_bundle(*, base_url: str, timeout: int, output_dir: Path, **kwargs) -> dict:
        files = write_valid_preflight_artifacts(
            output_dir,
            payload=payload,
            pilot_gate_result=pilot_gate_result,
            cutover_gate_result=cutover_gate_result,
            smoke_report=smoke_report,
        )
        result = {
            "pilot_gate": json.loads(json.dumps(pilot_gate_result)),
            "cutover_gate": json.loads(json.dumps(cutover_gate_result)),
            "files": files,
        }
        if smoke_report is not None:
            result["smoke_report"] = json.loads(json.dumps(smoke_report))
        return result

    return fake_preflight_bundle


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


def test_preflight_bundle_can_embed_smoke_outputs(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_preflight, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_preflight,
        "run_smoke_checks",
        lambda **kwargs: [pilot_smoke.CheckResult(name="frontend_health", ok=True, detail="HTTP 200")],
    )

    result = pilot_preflight.build_preflight_bundle(
        base_url="https://pilot.example.com",
        timeout=5,
        output_dir=tmp_path,
        include_smoke=True,
        preset="pilot",
        legacy_url="https://crmcatkapinda.com",
        legacy_cutover_mode="banner",
    )

    assert result["smoke_report"]["overall_ok"] is True
    assert (tmp_path / "pilot-smoke-live.md").exists()
    assert (tmp_path / "pilot-smoke-live.json").exists()
    summary = (tmp_path / "pilot-preflight-summary.md").read_text(encoding="utf-8")
    assert "## Smoke" in summary
    assert "Smoke Markdown" in summary


def test_day_zero_bundle_writes_manifest_and_env_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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
    assert manifest["release_snapshot"]["frontend_release"] == "front123"
    assert manifest["release_snapshot"]["backend_release"] == "back123"
    assert manifest["release_snapshot"]["release_alignment"] == "mismatch"
    assert manifest["service_names"]["api"] == "crmcatkapinda-v2-api"
    assert manifest["service_names"]["frontend"] == "crmcatkapinda-v2"
    assert manifest["service_names"]["streamlit"] == "crmcatkapinda"
    assert manifest["verify_passed"] is True
    assert manifest["verify_missing_files_count"] == 0
    assert manifest["verify_consistency_issues_count"] == 0
    assert manifest["verify_archive_exists"] is True
    assert manifest["verify_recommended_next_step"] == "Day-zero kiti kullanima hazir."
    assert manifest["smoke_included"] is False
    assert manifest["smoke_overall_ok"] is None
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


def test_day_zero_bundle_can_surface_embedded_smoke_summary(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 2,
                "decision": {
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                },
            }
        ),
    )

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
        include_smoke=True,
        smoke_preset="pilot",
    )

    assert manifest["smoke_included"] is True
    assert manifest["smoke_overall_ok"] is False
    assert manifest["smoke_failed_count"] == 2
    assert manifest["smoke_recommended_next_step"] == "Frontend ready blokajini kapat."
    start_here = (tmp_path / "00-START-HERE.md").read_text(encoding="utf-8")
    assert "Smoke: `FAIL`" in start_here
    assert "Frontend ready blokajini kapat." in start_here


def test_day_zero_can_derive_api_url_from_status_payload():
    derived = pilot_day_zero._derive_api_url(sample_payload())

    assert derived == "https://pilot-api.example.com"


def test_day_zero_verify_passes_for_valid_bundle(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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
    assert result["integrity_checked"] is True
    assert result["integrity_ok"] is True
    assert result["integrity_algorithm"] == "sha256"
    assert result["release_snapshot_checked"] is True
    assert result["release_snapshot_ok"] is True
    assert result["release_snapshot_actual"]["frontend_release"] == "front123"
    assert result["start_here_checked"] is True
    assert result["start_here_ok"] is True
    assert result["env_checked"] is True
    assert result["env_ok"] is True
    assert result["packet_checked"] is True
    assert result["packet_ok"] is True
    assert result["reports_checked"] is True
    assert result["reports_ok"] is True
    assert result["verify_reports_checked"] is True
    assert result["verify_reports_ok"] is True
    assert result["manifest_summary_checked"] is True
    assert result["manifest_summary_ok"] is True
    assert result["manifest_files_checked"] is True
    assert result["manifest_files_ok"] is True
    assert result["smoke_checked"] is False
    assert result["consistency_issues"] == []


def test_day_zero_verify_checks_embedded_smoke_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini ac."},
            }
        ),
    )

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
        include_smoke=True,
        smoke_preset="pilot",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is True
    assert result["smoke_checked"] is True
    assert result["smoke_overall_ok"] is True
    assert result["smoke_failed_count"] == 0


def test_day_zero_verify_fails_when_smoke_manifest_and_file_disagree(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini ac."},
            }
        ),
    )

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
        include_smoke=True,
        smoke_preset="pilot",
    )

    (tmp_path / "pilot-smoke-live.json").write_text(
        json.dumps(
            {
                "overall_ok": False,
                "failed_count": 2,
                "decision": {"recommended_next_step": "Frontend ready blokajini kapat."},
            }
        ),
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("smoke_overall_ok" in item or "smoke_failed_count" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_archive_member_is_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini ac."},
            }
        ),
    )

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
        include_smoke=True,
        smoke_preset="pilot",
    )

    archive_path = Path(manifest["archive_path"])
    replacement_archive = archive_path.with_name("replacement.zip")
    with zipfile.ZipFile(archive_path) as source_archive, zipfile.ZipFile(replacement_archive, "w", compression=zipfile.ZIP_DEFLATED) as target_archive:
        for member in source_archive.infolist():
            if member.filename == "pilot-smoke-live.md":
                continue
            target_archive.writestr(member, source_archive.read(member.filename))
    replacement_archive.replace(archive_path)

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert any("pilot-smoke-live.md" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_integrity_checksum_changes(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    (tmp_path / "pilot-launch.md").write_text("bozuldu", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["integrity_checked"] is True
    assert result["integrity_ok"] is False
    assert any("pilot-launch.md" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_release_snapshot_disagrees(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    manifest_path = tmp_path / "pilot-day-zero-manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["release_snapshot"]["frontend_release"] = "front999"
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["release_snapshot_checked"] is True
    assert result["release_snapshot_ok"] is False
    assert any("Frontend release" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_start_here_markdown_is_stale(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    start_here_path = tmp_path / "00-START-HERE.md"
    content = start_here_path.read_text(encoding="utf-8").replace("- Verify: `PASS`", "- Verify: `FAIL`")
    start_here_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["start_here_checked"] is True
    assert result["start_here_ok"] is False
    assert any("00-START-HERE.md" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_streamlit_banner_env_is_wrong(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    banner_env_path = tmp_path / "streamlit-banner.env"
    content = banner_env_path.read_text(encoding="utf-8").replace("CK_V2_CUTOVER_MODE=banner", "CK_V2_CUTOVER_MODE=redirect")
    banner_env_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["env_checked"] is True
    assert result["env_ok"] is False
    assert any("streamlit-banner.env" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_render_env_bundle_json_is_wrong(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    bundle_json_path = tmp_path / "render-env-bundle.json"
    bundle_payload = json.loads(bundle_json_path.read_text(encoding="utf-8"))
    bundle_payload["crmcatkapinda-v2-api"]["CK_V2_API_PUBLIC_URL"] = "https://wrong-api.example.com"
    bundle_json_path.write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["env_checked"] is True
    assert result["env_ok"] is False
    assert any("render-env-bundle.json" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_banner_guard_json_is_wrong(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    guard_json_path = tmp_path / "streamlit-banner-guard.json"
    guard_payload = json.loads(guard_json_path.read_text(encoding="utf-8"))
    guard_payload["mode"] = "redirect"
    guard_json_path.write_text(json.dumps(guard_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert any("streamlit-banner-guard.json" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_embedded_verify_json_is_wrong(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    verify_json_path = tmp_path / "pilot-day-zero-verify.json"
    verify_payload = json.loads(verify_json_path.read_text(encoding="utf-8"))
    verify_payload["recommended_next_step"] = "Yanlis sonraki adim"
    verify_json_path.write_text(json.dumps(verify_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["verify_reports_checked"] is True
    assert result["verify_reports_ok"] is False
    assert any("pilot-day-zero-verify.json" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_manifest_summary_is_wrong(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    manifest_path = tmp_path / "pilot-day-zero-manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["verify_consistency_issues_count"] = 99
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["manifest_summary_checked"] is True
    assert result["manifest_summary_ok"] is False
    assert any("verify_consistency_issues_count" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_manifest_file_map_is_wrong(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    manifest_path = tmp_path / "pilot-day-zero-manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["files"]["pilot_launch_packet"] = str(tmp_path / "pilot-cutover.md")
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["manifest_files_checked"] is True
    assert result["manifest_files_ok"] is False
    assert any("pilot_launch_packet" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_launch_packet_is_stale(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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

    packet_path = tmp_path / "pilot-cutover.md"
    content = packet_path.read_text(encoding="utf-8").replace("--cutover-mode redirect", "--cutover-mode banner")
    packet_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["packet_checked"] is True
    assert result["packet_ok"] is False
    assert any("pilot-cutover.md" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_preflight_summary_is_stale(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            pilot_gate_result={"passed": True, "summary": "Pilot acilabilir.", "recommended_next_step": "Devam"},
            cutover_gate_result={
                "passed": False,
                "summary": "Redirect cutover'a gecilemez.",
                "recommended_next_step": "Bekle",
            },
        ),
    )

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

    summary_path = tmp_path / "pilot-preflight-summary.md"
    content = summary_path.read_text(encoding="utf-8").replace("- Pilot Gate: `PASS`", "- Pilot Gate: `FAIL`")
    summary_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["reports_checked"] is True
    assert result["reports_ok"] is False
    assert any("pilot-preflight-summary.md" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_archive_is_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

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
            "integrity_checked": True,
            "integrity_ok": True,
            "integrity_algorithm": "sha256",
            "integrity_entries_count": 12,
            "release_snapshot_checked": True,
            "release_snapshot_ok": True,
            "start_here_checked": True,
            "start_here_ok": True,
            "env_checked": True,
            "env_ok": True,
            "packet_checked": True,
            "packet_ok": True,
            "reports_checked": True,
            "reports_ok": True,
            "verify_reports_checked": True,
            "verify_reports_ok": True,
            "manifest_summary_checked": True,
            "manifest_summary_ok": True,
            "manifest_files_checked": True,
            "manifest_files_ok": True,
            "recommended_next_step": "Day-zero kiti kullanima hazir.",
        }
    )

    assert "# Cat Kapinda CRM v2 Day Zero Verify" in markdown
    assert "Integrity" in markdown
    assert "Release Snapshot" in markdown
    assert "Start Here" in markdown
    assert "Env Payloads" in markdown
    assert "Launch Packets" in markdown
    assert "Status Reports" in markdown
    assert "Embedded Verify Reports" in markdown
    assert "Manifest Summary" in markdown
    assert "Manifest Files" in markdown
    assert "## Missing Files" in markdown
    assert "## Consistency Issues" in markdown
    assert "Smoke" in markdown


def test_day_zero_exit_code_respects_strict_verify_mode():
    manifest = {
        "pilot_gate_passed": True,
        "verify_passed": False,
        "smoke_included": False,
    }

    assert pilot_day_zero.compute_exit_code(manifest, strict=False, strict_smoke=False) == 0
    assert pilot_day_zero.compute_exit_code(manifest, strict=True, strict_smoke=False) == 2


def test_day_zero_exit_code_can_enforce_strict_smoke_mode():
    manifest = {
        "pilot_gate_passed": True,
        "verify_passed": True,
        "smoke_included": True,
        "smoke_overall_ok": False,
    }

    assert pilot_day_zero.compute_exit_code(manifest, strict=False, strict_smoke=False) == 0
    assert pilot_day_zero.compute_exit_code(manifest, strict=False, strict_smoke=True) == 2
