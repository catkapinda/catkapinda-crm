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
    normalized_smoke_report = None
    if smoke_report is not None:
        raw_smoke_report = json.loads(json.dumps(smoke_report))
        smoke_results = raw_smoke_report.get("results") or []
        passed_count = raw_smoke_report.get("passed_count")
        if passed_count is None:
            passed_count = sum(1 for result in smoke_results if result.get("ok")) if smoke_results else (1 if raw_smoke_report["overall_ok"] else 0)
        failed_count = raw_smoke_report.get("failed_count")
        if failed_count is None:
            failed_count = sum(1 for result in smoke_results if not result.get("ok"))
        normalized_smoke_report = {
            "base_url": base_url,
            "preset": None,
            "generated_at": "2026-01-01T00:00:00+00:00",
            "timeout_seconds": 5,
            "identity_provided": False,
            "legacy_url": None,
            "legacy_cutover_mode": None,
            "overall_ok": raw_smoke_report["overall_ok"],
            "passed_count": passed_count,
            "failed_count": failed_count,
            "results": smoke_results,
        }
        normalized_smoke_report["decision"] = {
            **pilot_smoke.build_decision_summary(normalized_smoke_report),
            **(raw_smoke_report.get("decision") or {}),
        }

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
            smoke_report=normalized_smoke_report,
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
    if normalized_smoke_report is not None:
        (output_dir / "pilot-smoke-live.md").write_text(
            pilot_smoke.build_markdown_report(normalized_smoke_report),
            encoding="utf-8",
        )
        (output_dir / "pilot-smoke-live.json").write_text(json.dumps(normalized_smoke_report), encoding="utf-8")
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
        raw_smoke_report = dict(smoke_report)
        smoke_report = {
            "overall_ok": False,
            "failed_count": 0,
            "results": [],
            "decision": {},
            **smoke_report,
        }
        smoke_report["decision"] = {
            "recommended_next_step": "Smoke blokajlarini kapat.",
            **(smoke_report.get("decision") or {}),
        }
        if not smoke_report.get("results"):
            smoke_report["results"] = (
                [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ]
                if smoke_report.get("overall_ok")
                else [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Synthetic smoke failure",
                    }
                ]
            )
        if "passed_count" not in raw_smoke_report:
            smoke_report["passed_count"] = sum(1 for result in smoke_report["results"] if result.get("ok"))
        if "failed_count" not in raw_smoke_report:
            smoke_report["failed_count"] = sum(1 for result in smoke_report["results"] if not result.get("ok"))

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
            result["smoke_report"] = json.loads((output_dir / "pilot-smoke-live.json").read_text(encoding="utf-8"))
        return result

    return fake_preflight_bundle


def test_pilot_smoke_accepts_local_sqlite_backend_for_localhost(monkeypatch):
    def fake_fetch_json(base_url: str, path: str, timeout: int):
        assert base_url == "http://127.0.0.1:3001"
        payloads = {
            "/api/health": (200, {"status": "ok", "service": "frontend"}),
            "/api/ready": (
                200,
                {
                    "proxyConfigured": True,
                    "proxyMode": "explicit_base_url",
                    "sourceEnvKey": "CK_V2_INTERNAL_API_BASE_URL",
                    "backendReachable": True,
                    "backendStatus": "ok",
                },
            ),
            "/api/pilot-status": (
                200,
                {
                    "frontend": {
                        "proxyConfigured": True,
                        "proxyMode": "explicit_base_url",
                        "backendReachable": True,
                        "backendStatus": "ok",
                        "releaseLabel": "crmcatkapinda-v2",
                    },
                    "backend": {
                        "release_label": None,
                        "cutover": {"phase": "not_ready"},
                    },
                },
            ),
            "/v2-api/health": (200, {"status": "ok", "service": "backend"}),
            "/v2-api/health/ready": (200, {"status": "degraded", "checks": [{"name": "database_url"}]}),
            "/v2-api/health/pilot": (
                200,
                {
                    "status": "degraded",
                    "modules": [{"module": f"m-{index}"} for index in range(11)],
                    "auth": {"email_login": True, "phone_login": True, "sms_login": False},
                    "required_missing_env_vars": ["CK_V2_DATABASE_URL"],
                    "optional_missing_env_vars": ["SMS_PROVIDER"],
                    "cutover": {"phase": "not_ready", "ready": False, "modules_ready_count": 11},
                    "checks": [{"name": "database_url", "detail": "Local sqlite fallback aktif"}],
                },
            ),
        }
        return payloads[path]

    monkeypatch.setattr(pilot_smoke, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        pilot_smoke,
        "fetch_text",
        lambda base_url, path, timeout: (200, "text/html; charset=utf-8", "<html></html>"),
    )

    results = pilot_smoke.run_smoke_checks(
        "http://127.0.0.1:3001",
        12,
        legacy_url="https://crmcatkapinda.com",
        legacy_cutover_mode="banner",
    )
    result_map = {result.name: result for result in results}

    assert result_map["backend_pilot"].ok is True
    assert "local_sqlite_hazir=True" in result_map["backend_pilot"].detail
    assert result_map["legacy_banner_bridge"].ok is True
    assert result_map["legacy_banner_bridge"].detail == "Yerel calismada legacy banner koprusu atlandi."


def test_pilot_smoke_localhost_report_becomes_clean_with_local_sqlite(monkeypatch):
    def fake_fetch_json(base_url: str, path: str, timeout: int):
        payloads = {
            "/api/health": (200, {"status": "ok", "service": "frontend"}),
            "/api/ready": (
                200,
                {
                    "proxyConfigured": True,
                    "proxyMode": "explicit_base_url",
                    "sourceEnvKey": "CK_V2_INTERNAL_API_BASE_URL",
                    "backendReachable": True,
                    "backendStatus": "ok",
                },
            ),
            "/api/pilot-status": (
                200,
                {
                    "frontend": {
                        "proxyConfigured": True,
                        "proxyMode": "explicit_base_url",
                        "backendReachable": True,
                        "backendStatus": "ok",
                        "releaseLabel": "crmcatkapinda-v2",
                    },
                    "backend": {
                        "release_label": None,
                        "cutover": {"phase": "not_ready"},
                    },
                },
            ),
            "/v2-api/health": (200, {"status": "ok", "service": "backend"}),
            "/v2-api/health/ready": (200, {"status": "degraded", "checks": [{"name": "database_url"}]}),
            "/v2-api/health/pilot": (
                200,
                {
                    "status": "degraded",
                    "modules": [{"module": f"m-{index}"} for index in range(11)],
                    "auth": {"email_login": True, "phone_login": True, "sms_login": False},
                    "required_missing_env_vars": ["CK_V2_DATABASE_URL"],
                    "optional_missing_env_vars": ["SMS_PROVIDER"],
                    "cutover": {"phase": "not_ready", "ready": False, "modules_ready_count": 11},
                    "checks": [{"name": "database_url", "detail": "Local sqlite fallback aktif"}],
                },
            ),
        }
        return payloads[path]

    monkeypatch.setattr(pilot_smoke, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        pilot_smoke,
        "fetch_text",
        lambda base_url, path, timeout: (200, "text/html; charset=utf-8", "<html></html>"),
    )

    results = pilot_smoke.run_smoke_checks(
        "http://localhost:3001",
        12,
        legacy_url="https://crmcatkapinda.com",
        legacy_cutover_mode="banner",
    )
    report = pilot_smoke.build_report(
        base_url="http://localhost:3001",
        timeout=12,
        preset="pilot",
        identity=None,
        legacy_url="https://crmcatkapinda.com",
        legacy_cutover_mode="banner",
        results=results,
    )

    assert report["overall_ok"] is True
    assert report["decision"]["status"] == "pass"
    assert report["decision"]["failing_checks"] == []


def test_day_zero_verify_manifest_core_accepts_localhost_http_urls(tmp_path: Path):
    manifest = {
        "frontend_url": "http://127.0.0.1:3001",
        "api_url": "http://localhost:8000",
        "streamlit_url": "https://crmcatkapinda.com",
        "generated_at": "2026-04-16T20:00:00+00:00",
        "service_names": {
            "api": "crmcatkapinda-v2-api",
            "frontend": "crmcatkapinda-v2",
            "streamlit": "crmcatkapinda",
        },
        "archive_path": str((tmp_path.parent / f"{tmp_path.name}.zip").resolve()),
    }

    checked, issues = pilot_day_zero_verify._check_manifest_core(output_dir=tmp_path, manifest=manifest)

    assert checked is True
    assert issues == []


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


def test_preflight_bundle_removes_stale_smoke_files_when_smoke_is_disabled(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_preflight, "fetch_pilot_status", lambda base_url, timeout: sample_payload())

    (tmp_path / "pilot-smoke-live.md").write_text("stale", encoding="utf-8")
    (tmp_path / "pilot-smoke-live.json").write_text("{}", encoding="utf-8")

    result = pilot_preflight.build_preflight_bundle(
        base_url="https://pilot.example.com",
        timeout=5,
        output_dir=tmp_path,
        include_smoke=False,
    )

    assert result.get("smoke_report") is None
    assert (tmp_path / "pilot-smoke-live.md").exists() is False
    assert (tmp_path / "pilot-smoke-live.json").exists() is False


def test_preflight_bundle_can_freshen_existing_output_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_preflight, "fetch_pilot_status", lambda base_url, timeout: sample_payload())

    pilot_preflight.build_preflight_bundle(
        base_url="https://pilot.example.com",
        timeout=5,
        output_dir=tmp_path,
    )
    stale_file = tmp_path / "stale-preflight.txt"
    stale_file.write_text("eski dosya", encoding="utf-8")

    result = pilot_preflight.build_preflight_bundle(
        base_url="https://pilot.example.com",
        timeout=5,
        output_dir=tmp_path,
        fresh_output=True,
    )

    assert result["pilot_gate"]["passed"] is True
    assert stale_file.exists() is False


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
    embedded_verify = json.loads((tmp_path / "pilot-day-zero-verify.json").read_text(encoding="utf-8"))
    assert embedded_verify["verify_reports_checked"] is True
    assert embedded_verify["verify_reports_ok"] is True
    start_here = (tmp_path / "00-START-HERE.md").read_text(encoding="utf-8")
    assert "Verify: `PASS`" in start_here
    assert "Day-zero kiti kullanima hazir." in start_here


def test_day_zero_bundle_embeds_final_verify_snapshot(monkeypatch, tmp_path: Path):
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

    embedded_verify = json.loads((tmp_path / "pilot-day-zero-verify.json").read_text(encoding="utf-8"))
    fresh_verify = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert embedded_verify["passed"] == fresh_verify["passed"]
    assert embedded_verify["verify_reports_checked"] == fresh_verify["verify_reports_checked"]
    assert embedded_verify["verify_reports_ok"] == fresh_verify["verify_reports_ok"]
    assert embedded_verify["manifest_core_checked"] == fresh_verify["manifest_core_checked"]
    assert embedded_verify["manifest_core_ok"] == fresh_verify["manifest_core_ok"]


def test_day_zero_bundle_normalizes_output_dir_before_manifest(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

    real_output_dir = tmp_path / "real-output"
    alias_output_dir = tmp_path / "alias-output"
    alias_output_dir.symlink_to(real_output_dir, target_is_directory=True)

    manifest = pilot_day_zero.build_day_zero_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        streamlit_url="https://crmcatkapinda.com",
        output_dir=alias_output_dir,
        timeout=5,
        database_url="postgresql://pilot",
        default_auth_password="secret",
        identity="ebru@catkapinda.com",
        password_placeholder="<sifre>",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
    )

    assert manifest["output_dir"] == str(real_output_dir.resolve())
    assert manifest["archive_path"] == str(real_output_dir.resolve().parent / "real-output.zip")
    assert pilot_day_zero_verify.verify_day_zero_bundle(alias_output_dir)["passed"] is True


def test_day_zero_verify_accepts_alias_manifest_paths(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

    real_output_dir = tmp_path / "real-output"
    alias_output_dir = tmp_path / "alias-output"
    alias_output_dir.symlink_to(real_output_dir, target_is_directory=True)

    manifest = pilot_day_zero.build_day_zero_bundle(
        frontend_url="https://pilot.example.com",
        api_url="https://pilot-api.example.com",
        streamlit_url="https://crmcatkapinda.com",
        output_dir=real_output_dir,
        timeout=5,
        database_url="postgresql://pilot",
        default_auth_password="secret",
        identity="ebru@catkapinda.com",
        password_placeholder="<sifre>",
        api_service_name="crmcatkapinda-v2-api",
        frontend_service_name="crmcatkapinda-v2",
        streamlit_service_name="crmcatkapinda",
    )

    real_archive_path = Path(manifest["archive_path"])
    alias_archive_path = tmp_path / "alias-output.zip"
    alias_archive_path.symlink_to(real_archive_path)

    manifest_path = real_output_dir / "pilot-day-zero-manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["output_dir"] = str(alias_output_dir)
    manifest_payload["archive_path"] = str(alias_archive_path)
    for label, raw_path in list(manifest_payload["files"].items()):
        manifest_payload["files"][label] = str(alias_output_dir / Path(raw_path).name)
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    verify_json_path = real_output_dir / "pilot-day-zero-verify.json"
    verify_payload = json.loads(verify_json_path.read_text(encoding="utf-8"))
    verify_payload["output_dir"] = str(alias_output_dir)
    verify_payload["archive_path"] = str(alias_archive_path)
    verify_json_path.write_text(json.dumps(verify_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    verify_md_path = real_output_dir / "pilot-day-zero-verify.md"
    verify_md = verify_md_path.read_text(encoding="utf-8").replace(str(real_output_dir.resolve()), str(alias_output_dir))
    verify_md_path.write_text(verify_md, encoding="utf-8")

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["integrity"] = pilot_day_zero._build_integrity_manifest(
        output_dir=real_output_dir.resolve(),
        manifest=manifest_payload,
    )
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pilot_day_zero._zip_directory(real_output_dir.resolve(), real_archive_path)

    result = pilot_day_zero_verify.verify_day_zero_bundle(alias_output_dir)

    assert result["passed"] is True
    assert result["consistency_issues"] == []


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


def test_day_zero_bundle_can_freshen_existing_output_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(pilot_day_zero, "build_preflight_bundle", make_fake_preflight_bundle())

    first_manifest = pilot_day_zero.build_day_zero_bundle(
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
    assert first_manifest["verify_passed"] is True

    stale_file = tmp_path / "stale-note.txt"
    stale_file.write_text("eski arti dosya", encoding="utf-8")

    refreshed_manifest = pilot_day_zero.build_day_zero_bundle(
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
        fresh_output=True,
    )

    assert refreshed_manifest["verify_passed"] is True
    assert stale_file.exists() is False
    verify_result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)
    assert verify_result["passed"] is True


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
    assert result["archive_manifest_checked"] is True
    assert result["archive_manifest_ok"] is True
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
    assert result["manifest_core_checked"] is True
    assert result["manifest_core_ok"] is True
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
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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


def test_day_zero_verify_fails_when_smoke_payload_root_is_not_a_dict(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_json_path.write_text(json.dumps(["bozuk"]), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("kok payload'i dict degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_count_fields_are_not_numeric(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["passed_count"] = "NaN"
    smoke_payload["failed_count"] = "oops"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("passed_count sayisal degil" in item or "failed_count sayisal degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_next_step_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["recommended_next_step"] = {"bad": True}
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.recommended_next_step string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_failing_checks_is_not_a_list(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["failing_checks"] = "frontend_ready"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.failing_checks list degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_failing_checks_item_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["failing_checks"] = ["frontend_ready", {"bad": True}]
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.failing_checks[1] string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_result_name_is_invalid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["results"][0].pop("name")
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("results[0].name gecersiz" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_result_ok_is_not_bool(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["results"][0]["ok"] = "yes"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("results[0].ok bool degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_result_detail_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["results"][0]["detail"] = {"bad": True}
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("results[0].detail string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_status_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["status"] = {"bad": True}
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.status string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_headline_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["headline"] = ["bozuk"]
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.headline string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_primary_blocker_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["primary_blocker"] = ["bozuk"]
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.primary_blocker string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_primary_blocker_is_blank(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["primary_blocker"] = "   "
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.primary_blocker bos" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_next_step_is_blank(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["recommended_next_step"] = "   "
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.recommended_next_step bos" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_overall_ok_is_not_bool(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["overall_ok"] = "true"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("overall_ok bool degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_identity_provided_is_not_bool(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["identity_provided"] = "yes"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("identity_provided bool degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_timeout_seconds_is_not_numeric(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["timeout_seconds"] = "hizli"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("timeout_seconds sayisal degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_base_url_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["base_url"] = {"bad": True}
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("base_url string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_base_url_is_blank(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["base_url"] = "   "
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("base_url bos" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_status_is_blank(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["status"] = "   "
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.status bos" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_status_is_invalid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend baglantisi yok",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend hazir degil.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["status"] = "blocked"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.status gecersiz deger" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_generated_at_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["generated_at"] = ["bozuk"]
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("generated_at string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_preset_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["preset"] = {"bad": True}
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("preset string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_preset_is_invalid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["preset"] = "dry-run"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("preset gecersiz deger" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_legacy_url_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["legacy_url"] = ["bozuk"]
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("legacy_url string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_legacy_cutover_mode_is_not_a_string(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["legacy_cutover_mode"] = {"bad": True}
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("legacy_cutover_mode string degil" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_legacy_cutover_mode_is_invalid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["legacy_cutover_mode"] = "soft"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("legacy_cutover_mode gecersiz deger" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_payload_is_not_a_dict(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"] = "bozuk"
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision alani dict degil" in item or "gecersiz alan yapi" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "- Recommended Next Step: Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz.",
        "- Recommended Next Step: Frontend ready blokajini kapat.",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("pilot-smoke-live.md" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_metadata_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "- Base URL: `https://pilot.example.com`",
        "- Base URL: `https://wrong.example.com`",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("Base URL" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_has_unexpected_summary_bullet(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "## Decision\n",
        "- Overall OK: `False`\n## Decision\n",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("summary/decision satirlari" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_primary_blocker_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend pilot status alinmadi",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend backend'e saglikli baglanamiyor.",
                    "primary_blocker": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "CK_V2_INTERNAL_API_HOSTPORT veya yerel base URL ayarlarini kontrol edelim.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "- Primary Blocker: Frontend backend'e saglikli baglanamiyor.",
        "- Primary Blocker: Yanlis blokaj metni",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("Primary Blocker" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_check_table_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend pilot status alinmadi",
                    }
                ],
                "decision": {"recommended_next_step": "Frontend ready blokajini kapat."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "| `frontend_ready` | **FAIL** | Backend pilot status alinmadi |",
        "| `frontend_ready` | **OK** | Backend pilot status alinmadi |",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("pilot-smoke-live.md" in item and "frontend_ready" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_check_table_order_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "failed_count": 2,
                "results": [
                    {
                        "name": "backend_ready",
                        "ok": False,
                        "detail": "Backend readiness bozuk",
                    },
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Frontend backend'e baglanamiyor",
                    },
                ],
                "decision": {"recommended_next_step": "CK_V2_INTERNAL_API_HOSTPORT veya yerel base URL ayarlarini kontrol edelim."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8")
    first_row = "| `backend_ready` | **FAIL** | Backend readiness bozuk |"
    second_row = "| `frontend_ready` | **FAIL** | Frontend backend'e baglanamiyor |"
    content = content.replace(f"{first_row}\n{second_row}", f"{second_row}\n{first_row}")
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("check satiri sirasi bozuk" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_has_unexpected_extra_row(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    smoke_markdown_path.write_text(
        smoke_markdown_path.read_text(encoding="utf-8") + "| `ghost_check` | **OK** | Stale satir |\n",
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("beklenmeyen check satiri" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_has_duplicate_row(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    duplicate_row = "| `frontend_health` | **OK** | HTTP 200 |"
    smoke_markdown_path.write_text(
        smoke_markdown_path.read_text(encoding="utf-8") + duplicate_row + "\n",
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("tekrarlanan check satiri" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_structure_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "| Check | Result | Detail |",
        "| Check | Sonuc | Detail |",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("beklenen yapi satiri eksik" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_has_unexpected_freeform_line(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    smoke_markdown_path.write_text(
        smoke_markdown_path.read_text(encoding="utf-8") + "\nNot: stale serbest satir\n",
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("canonical smoke raporuyla birebir uyusmuyor" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_markdown_has_unexpected_structure_line(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        "## Decision\n",
        "## Legacy\n## Decision\n",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("yapi satirlari beklenen listeyle birebir uyusmuyor" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_row_exists_only_outside_table(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_markdown_path = tmp_path / "pilot-smoke-live.md"
    expected_row = "| `frontend_health` | **OK** | HTTP 200 |"
    content = smoke_markdown_path.read_text(encoding="utf-8").replace(
        expected_row,
        f"Satir tasindi: {expected_row}",
    )
    smoke_markdown_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("beklenen check satiri eksik" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_json_counts_drift_from_results(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "passed_count": 0,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend pilot status alinmadi",
                    }
                ],
                "decision": {
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["passed_count"] = 3
    smoke_payload["overall_ok"] = True
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("passed_count" in item or "overall_ok" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_decision_drifts_from_results(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "passed_count": 0,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend pilot status alinmadi",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend ready bloklu.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["status"] = "pass"
    smoke_payload["decision"]["headline"] = "Pilot smoke temiz."
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.status" in item or "decision.headline" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_next_step_drifts_from_results(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "passed_count": 0,
                "failed_count": 1,
                "results": [
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Backend pilot status alinmadi",
                    }
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend ready bloklu.",
                    "recommended_next_step": "Frontend ready blokajini kapat.",
                    "failing_checks": ["frontend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["recommended_next_step"] = "Dogrudan redirect provasi yapalim."
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("decision.recommended_next_step" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_failing_checks_order_drifts(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": False,
                "passed_count": 0,
                "failed_count": 2,
                "results": [
                    {
                        "name": "backend_ready",
                        "ok": False,
                        "detail": "Backend readiness bozuk",
                    },
                    {
                        "name": "frontend_ready",
                        "ok": False,
                        "detail": "Frontend backend'e baglanamiyor",
                    },
                ],
                "decision": {
                    "status": "blocking",
                    "headline": "Frontend backend'e saglikli baglanamiyor.",
                    "recommended_next_step": "CK_V2_INTERNAL_API_HOSTPORT veya yerel base URL ayarlarini kontrol edelim.",
                    "failing_checks": ["frontend_ready", "backend_ready"],
                },
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["decision"]["failing_checks"] = ["backend_ready", "frontend_ready"]
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("failing_checks" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_results_list_is_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "results": [
                    {
                        "name": "frontend_health",
                        "ok": True,
                        "detail": "HTTP 200",
                    }
                ],
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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

    smoke_json_path = tmp_path / "pilot-smoke-live.json"
    smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    smoke_payload["results"] = []
    smoke_json_path.write_text(json.dumps(smoke_payload), encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["smoke_checked"] is True
    assert any("results listesi" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_smoke_archive_member_is_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pilot_day_zero, "fetch_pilot_status", lambda base_url, timeout: sample_payload())
    monkeypatch.setattr(
        pilot_day_zero,
        "build_preflight_bundle",
        make_fake_preflight_bundle(
            smoke_report={
                "overall_ok": True,
                "failed_count": 0,
                "decision": {"recommended_next_step": "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."},
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


def test_day_zero_verify_fails_when_archive_manifest_is_stale(monkeypatch, tmp_path: Path):
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
    replacement_archive = archive_path.with_name("replacement.zip")
    with zipfile.ZipFile(archive_path) as source_archive, zipfile.ZipFile(replacement_archive, "w", compression=zipfile.ZIP_DEFLATED) as target_archive:
        for member in source_archive.infolist():
            payload = source_archive.read(member.filename)
            if member.filename == "pilot-day-zero-manifest.json":
                archive_manifest = json.loads(payload.decode("utf-8"))
                archive_manifest["verify_passed"] = False
                payload = (json.dumps(archive_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            target_archive.writestr(member, payload)
    replacement_archive.replace(archive_path)

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["archive_manifest_checked"] is True
    assert result["archive_manifest_ok"] is False
    assert any("pilot-day-zero-manifest.json" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_unexpected_bundle_file_remains(monkeypatch, tmp_path: Path):
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

    stale_file = tmp_path / "stale-notes.txt"
    stale_file.write_text("eski artefakt", encoding="utf-8")
    pilot_day_zero._zip_directory(tmp_path, Path(manifest["archive_path"]))

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert any("beklenmeyen dosya" in item for item in result["consistency_issues"])
    assert any("stale-notes.txt" in item for item in result["consistency_issues"])


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


def test_day_zero_verify_fails_when_env_bundle_contains_unexpected_service_section(monkeypatch, tmp_path: Path):
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

    render_bundle_path = tmp_path / "render-env-bundle.env"
    render_bundle_path.write_text(
        render_bundle_path.read_text(encoding="utf-8") + "\n[ghost-service]\nDUMMY=1\n",
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["env_checked"] is True
    assert result["env_ok"] is False
    assert any("render-env-bundle.env" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_env_bundle_contains_unexpected_env_key(monkeypatch, tmp_path: Path):
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

    render_bundle_path = tmp_path / "render-env-bundle.env"
    render_bundle_path.write_text(
        render_bundle_path.read_text(encoding="utf-8").replace(
            "CK_V2_API_PUBLIC_URL=https://pilot-api.example.com",
            "CK_V2_API_PUBLIC_URL=https://pilot-api.example.com\nLEGACY_EXTRA_FLAG=1",
        ),
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["env_checked"] is True
    assert result["env_ok"] is False
    assert any("API env anahtarlari" in item for item in result["consistency_issues"])


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


def test_day_zero_verify_fails_when_banner_guarded_env_drifts_from_guard_json(monkeypatch, tmp_path: Path):
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

    guarded_env_path = tmp_path / "streamlit-banner-guarded.env"
    guarded_env_path.write_text(
        "[crmcatkapinda]\nCK_V2_PILOT_URL=https://wrong.example.com\nCK_V2_CUTOVER_MODE=banner\n",
        encoding="utf-8",
    )

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert any("streamlit-banner-guarded.env" in item for item in result["consistency_issues"])


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


def test_day_zero_verify_fails_when_embedded_verify_manifest_core_is_wrong(monkeypatch, tmp_path: Path):
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
    verify_payload["manifest_core_ok"] = False
    verify_json_path.write_text(json.dumps(verify_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["verify_reports_checked"] is True
    assert result["verify_reports_ok"] is False
    assert any("manifest_core_ok" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_embedded_verify_manifest_summary_is_wrong(monkeypatch, tmp_path: Path):
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
    verify_payload["manifest_summary_ok"] = False
    verify_json_path.write_text(json.dumps(verify_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["verify_reports_checked"] is True
    assert result["verify_reports_ok"] is False
    assert any("manifest_summary_ok" in item for item in result["consistency_issues"])


def test_day_zero_verify_fails_when_embedded_verify_env_state_is_wrong(monkeypatch, tmp_path: Path):
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
    verify_payload["env_ok"] = False
    verify_json_path.write_text(json.dumps(verify_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["verify_reports_checked"] is True
    assert result["verify_reports_ok"] is False
    assert any("env_ok" in item for item in result["consistency_issues"])


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


def test_day_zero_verify_fails_when_manifest_core_metadata_is_wrong(monkeypatch, tmp_path: Path):
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
    manifest_payload["streamlit_url"] = "http://crmcatkapinda.com"
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["manifest_core_checked"] is True
    assert result["manifest_core_ok"] is False
    assert any("streamlit_url" in item for item in result["consistency_issues"])


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


def test_day_zero_verify_fails_when_launch_packet_env_block_drifts(monkeypatch, tmp_path: Path):
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

    packet_path = tmp_path / "pilot-launch.md"
    content = packet_path.read_text(encoding="utf-8").replace(
        "CK_V2_API_PUBLIC_URL=https://pilot-api.example.com",
        "CK_V2_API_PUBLIC_URL=https://stale-api.example.com",
    )
    packet_path.write_text(content, encoding="utf-8")

    result = pilot_day_zero_verify.verify_day_zero_bundle(tmp_path)

    assert result["passed"] is False
    assert result["packet_checked"] is True
    assert result["packet_ok"] is False
    assert any("pilot-launch.md" in item and "env blogu" in item for item in result["consistency_issues"])


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
            "archive_manifest_checked": True,
            "archive_manifest_ok": True,
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
            "manifest_core_checked": True,
            "manifest_core_ok": True,
            "recommended_next_step": "Day-zero kiti kullanima hazir.",
        }
    )

    assert "# Cat Kapinda CRM v2 Day Zero Verify" in markdown
    assert "Integrity" in markdown
    assert "Archive Manifest" in markdown
    assert "Release Snapshot" in markdown
    assert "Start Here" in markdown
    assert "Env Payloads" in markdown
    assert "Launch Packets" in markdown
    assert "Status Reports" in markdown
    assert "Embedded Verify Reports" in markdown
    assert "Manifest Summary" in markdown
    assert "Manifest Files" in markdown
    assert "Manifest Core" in markdown
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
