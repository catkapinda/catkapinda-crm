#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile
from copy import deepcopy

from pilot_smoke import build_decision_summary as build_smoke_decision_summary


DEFAULT_OUTPUT_DIR = "pilot-day-zero"

REQUIRED_FILES = (
    "00-START-HERE.md",
    "render-env-bundle.env",
    "render-env-bundle.json",
    "streamlit-banner.env",
    "streamlit-redirect.env",
    "streamlit-banner-guard.json",
    "streamlit-redirect-guard.json",
    "streamlit-banner-guarded.env",
    "streamlit-redirect-guarded.env",
    "pilot-launch.md",
    "pilot-cutover.md",
    "pilot-status-live.md",
    "pilot-status-live.json",
    "pilot-gate-pilot.json",
    "pilot-gate-cutover.json",
    "pilot-preflight-summary.md",
    "pilot-day-zero-manifest.json",
)

OPTIONAL_SMOKE_FILES = (
    "pilot-smoke-live.md",
    "pilot-smoke-live.json",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_env_bundle(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current_section: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            sections[current_section] = {}
            continue
        if current_section and "=" in line:
            key, value = line.split("=", 1)
            sections[current_section][key.strip()] = value.strip()
    return sections


def _render_env_bundle(bundle: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for service_name, envs in bundle.items():
        lines.append(f"[{service_name}]")
        for key, value in envs.items():
            lines.append(f"{key}={value}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _extract_fenced_block(content: str, language: str) -> str | None:
    start_token = f"```{language}"
    start_index = content.find(start_token)
    if start_index == -1:
        return None
    block_start = content.find("\n", start_index)
    if block_start == -1:
        return None
    block_end = content.find("\n```", block_start + 1)
    if block_end == -1:
        return None
    return content[block_start + 1:block_end].strip()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonicalize_path_text(value: str | Path | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return str(Path(text).expanduser().resolve())


def _canonicalize_manifest_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    if "output_dir" in normalized:
        normalized["output_dir"] = _canonicalize_path_text(normalized.get("output_dir"))
    if "archive_path" in normalized:
        normalized["archive_path"] = _canonicalize_path_text(normalized.get("archive_path"))
    files = normalized.get("files")
    if isinstance(files, dict):
        normalized["files"] = {
            key: _canonicalize_path_text(value)
            for key, value in files.items()
        }
    return normalized


def _expected_bundle_members(*, output_dir: Path, manifest: dict) -> set[str]:
    output_root = output_dir.resolve()
    expected_members = {"00-START-HERE.md", "pilot-day-zero-manifest.json"}

    for raw_path in (manifest.get("files") or {}).values():
        path = Path(str(raw_path)).expanduser()
        try:
            relative_path = path.resolve().relative_to(output_root)
            expected_members.add(relative_path.as_posix())
        except Exception:
            expected_members.add(path.name)

    return expected_members


def _check_guard_file(
    *,
    mode: str,
    guard_json_path: Path,
    guarded_env_path: Path,
    manifest: dict,
    expected_allowed: bool | None,
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    guard_payload = _read_json(guard_json_path)
    content = guarded_env_path.read_text(encoding="utf-8")
    allowed = bool(guard_payload.get("allowed"))
    streamlit_service_name = (manifest.get("service_names") or {}).get("streamlit")
    expected_gate_mode = "pilot" if mode == "banner" else "cutover"
    env_bundle = guard_payload.get("env_bundle") or {}
    streamlit_env = env_bundle.get(streamlit_service_name or "", {})

    if guard_payload.get("mode") != mode:
        issues.append(f"{guard_json_path.name} icinde mode uyusmuyor: {mode}")
    if guard_payload.get("base_url") != manifest.get("frontend_url"):
        issues.append(f"{guard_json_path.name} icinde base_url uyusmuyor")
    if guard_payload.get("streamlit_service_name") != streamlit_service_name:
        issues.append(f"{guard_json_path.name} icinde streamlit service name uyusmuyor")
    if guard_payload.get("gate_mode") != expected_gate_mode:
        issues.append(f"{guard_json_path.name} icinde gate_mode uyusmuyor: {expected_gate_mode}")
    if expected_allowed is not None and allowed != expected_allowed:
        issues.append(f"{guard_json_path.name} icinde allowed degeri manifestle uyusmuyor")
    if streamlit_service_name not in env_bundle:
        issues.append(f"{guard_json_path.name} icinde env_bundle streamlit servisini icermiyor: {streamlit_service_name}")
    if streamlit_env.get("CK_V2_PILOT_URL") != manifest.get("frontend_url"):
        issues.append(f"{guard_json_path.name} icinde CK_V2_PILOT_URL uyusmuyor")
    if streamlit_env.get("CK_V2_CUTOVER_MODE") != mode:
        issues.append(f"{guard_json_path.name} icinde CK_V2_CUTOVER_MODE uyusmuyor: {mode}")

    if allowed:
        expected_token = f"CK_V2_CUTOVER_MODE={mode}"
        if expected_token not in content:
            issues.append(f"{guarded_env_path.name} icinde {expected_token} bulunamadi")
        if "# guard blocked" in content:
            issues.append(f"{guarded_env_path.name} izin varken blok mesajı iceriyor")
        parsed_guarded_env = _parse_env_bundle(guarded_env_path)
        if parsed_guarded_env != env_bundle:
            issues.append(f"{guarded_env_path.name} icindeki env blogu {guard_json_path.name} ile uyusmuyor")
    else:
        if "# guard blocked" not in content:
            issues.append(f"{guarded_env_path.name} guard blokluyken blok mesaji icermiyor")
        if "[" in content or "=" in content:
            issues.append(f"{guarded_env_path.name} guard blokluyken env bolumu icermemeli")

    return (not issues, issues)


def _check_smoke_consistency(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str], dict | None]:
    issues: list[str] = []
    smoke_payload: dict | None = None
    smoke_included = bool(manifest.get("smoke_included"))

    if not smoke_included:
        return (True, issues, None)

    smoke_json_path = output_dir / "pilot-smoke-live.json"
    smoke_markdown_path = output_dir / "pilot-smoke-live.md"

    for path in (smoke_json_path, smoke_markdown_path):
        if not path.exists():
            issues.append(f"Smoke acikken {path.name} bulunamadi")

    if issues:
        return (False, issues, None)

    smoke_payload = _read_json(smoke_json_path)
    smoke_markdown = smoke_markdown_path.read_text(encoding="utf-8").strip()
    smoke_results = [
        result
        for result in (smoke_payload.get("results") or [])
        if isinstance(result, dict)
    ]
    if not smoke_results:
        issues.append("pilot-smoke-live.json icinde results listesi bos veya eksik")
    derived_passed_count = smoke_payload.get("passed_count")
    if derived_passed_count is None:
        if smoke_results:
            derived_passed_count = sum(1 for result in smoke_results if result.get("ok"))
        else:
            derived_passed_count = 1 if smoke_payload.get("overall_ok") else 0

    if smoke_results:
        actual_passed_count = sum(1 for result in smoke_results if result.get("ok"))
        actual_failed_count = sum(1 for result in smoke_results if not result.get("ok"))
        if smoke_payload.get("passed_count") is not None and int(smoke_payload.get("passed_count") or 0) != actual_passed_count:
            issues.append("pilot-smoke-live.json icinde passed_count result listesiyle uyusmuyor")
        if smoke_payload.get("failed_count") is not None and int(smoke_payload.get("failed_count") or 0) != actual_failed_count:
            issues.append("pilot-smoke-live.json icinde failed_count result listesiyle uyusmuyor")
        if smoke_payload.get("overall_ok") is not None and bool(smoke_payload.get("overall_ok")) != (actual_failed_count == 0):
            issues.append("pilot-smoke-live.json icinde overall_ok result listesiyle uyusmuyor")

        decision = smoke_payload.get("decision") or {}
        failing_checks = decision.get("failing_checks")
        expected_decision = build_smoke_decision_summary(
            {
                "base_url": smoke_payload.get("base_url") or manifest.get("frontend_url"),
                "preset": smoke_payload.get("preset"),
                "identity_provided": bool(smoke_payload.get("identity_provided")),
                "legacy_url": smoke_payload.get("legacy_url"),
                "legacy_cutover_mode": smoke_payload.get("legacy_cutover_mode"),
                "results": smoke_results,
            }
        )
        if isinstance(failing_checks, list):
            expected_failing_checks = list(expected_decision.get("failing_checks") or [])
            if list(map(str, failing_checks)) != expected_failing_checks:
                issues.append("pilot-smoke-live.json icinde failing_checks result listesiyle uyusmuyor")
        for key in ("status", "headline", "primary_blocker", "recommended_next_step"):
            if key in decision and decision.get(key) != expected_decision.get(key):
                issues.append(f"pilot-smoke-live.json icinde decision.{key} result listesiyle uyusmuyor")

    expected_overall_ok = manifest.get("smoke_overall_ok")
    if expected_overall_ok is not None and bool(smoke_payload.get("overall_ok")) != bool(expected_overall_ok):
        issues.append(
            "Manifest smoke_overall_ok degeri ile pilot-smoke-live.json uyusmuyor"
        )

    expected_failed_count = manifest.get("smoke_failed_count")
    if expected_failed_count is not None and int(smoke_payload.get("failed_count") or 0) != int(expected_failed_count):
        issues.append(
            "Manifest smoke_failed_count degeri ile pilot-smoke-live.json uyusmuyor"
        )

    expected_next_step = manifest.get("smoke_recommended_next_step")
    actual_next_step = ((smoke_payload.get("decision") or {}).get("recommended_next_step") or "").strip()
    if expected_next_step and actual_next_step != expected_next_step:
        issues.append(
            "Manifest smoke_recommended_next_step degeri ile pilot-smoke-live.json uyusmuyor"
        )

    expected_markdown_structure = [
        "# v2 Pilot Smoke Report",
        "## Decision",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for snippet in expected_markdown_structure:
        if snippet not in smoke_markdown:
            issues.append(f"pilot-smoke-live.md icinde beklenen yapi satiri eksik: {snippet}")
    actual_structure_lines = [
        line.strip()
        for line in smoke_markdown.splitlines()
        if line.strip().startswith("# ")
        or line.strip().startswith("## ")
        or line.strip() in {"| Check | Result | Detail |", "| --- | --- | --- |"}
    ]
    if actual_structure_lines != expected_markdown_structure:
        issues.append("pilot-smoke-live.md icinde yapi satirlari beklenen listeyle birebir uyusmuyor")

    expected_markdown_snippets = [
        f"- Base URL: `{smoke_payload.get('base_url')}`",
        f"- Preset: `{smoke_payload.get('preset') or '-'}`",
        f"- Generated At: `{smoke_payload.get('generated_at')}`",
        f"- Timeout: `{smoke_payload.get('timeout_seconds')}s`",
        f"- Identity Provided: `{bool(smoke_payload.get('identity_provided'))}`",
        f"- Legacy URL: `{smoke_payload.get('legacy_url') or '-'}`",
        f"- Legacy Cutover Mode: `{smoke_payload.get('legacy_cutover_mode') or '-'}`",
        f"- Overall OK: `{smoke_payload.get('overall_ok')}`",
        f"- Passed: `{derived_passed_count}`",
        f"- Failed: `{smoke_payload.get('failed_count')}`",
    ]
    decision = smoke_payload.get("decision") or {}
    if decision.get("status") is not None:
        expected_markdown_snippets.append(f"- Status: `{decision.get('status')}`")
    if decision.get("headline"):
        expected_markdown_snippets.append(f"- Headline: {decision.get('headline')}")
    if "primary_blocker" in decision:
        expected_markdown_snippets.append(
            f"- Primary Blocker: {decision.get('primary_blocker') or '-'}"
        )
    if decision.get("recommended_next_step"):
        expected_markdown_snippets.append(
            f"- Recommended Next Step: {decision.get('recommended_next_step')}"
        )
    if decision.get("failing_checks") is not None:
        failing_checks_text = ", ".join(map(str, decision.get("failing_checks") or [])) or "-"
        expected_markdown_snippets.append(f"- Failing Checks: `{failing_checks_text}`")

    for snippet in expected_markdown_snippets:
        if snippet not in smoke_markdown:
            issues.append(f"pilot-smoke-live.md icinde beklenen smoke satiri eksik: {snippet}")
    actual_summary_bullets = [
        line.strip()
        for line in smoke_markdown.splitlines()
        if line.strip().startswith("- ") and not line.strip().startswith("- |")
    ]
    if actual_summary_bullets != expected_markdown_snippets:
        issues.append("pilot-smoke-live.md icinde summary/decision satirlari beklenen listeyle birebir uyusmuyor")

    actual_table_rows = [
        line.strip()
        for line in smoke_markdown.splitlines()
        if line.strip().startswith("| `")
    ]
    expected_table_rows: list[str] = []
    for result in smoke_results:
        result_label = "OK" if result.get("ok") else "FAIL"
        detail = str(result.get("detail") or "").replace("\n", " ").replace("|", "\\|")
        expected_row = f"| `{result.get('name')}` | **{result_label}** | {detail} |"
        expected_table_rows.append(expected_row)
    actual_row_counts = Counter(actual_table_rows)
    expected_row_counts = Counter(expected_table_rows)
    previous_row_position = -1
    for expected_row, result in zip(expected_table_rows, smoke_results):
        if actual_row_counts.get(expected_row, 0) < expected_row_counts.get(expected_row, 0):
            issues.append(f"pilot-smoke-live.md icinde beklenen check satiri eksik: {result.get('name')}")
            continue
        row_position = actual_table_rows.index(expected_row)
        if row_position < previous_row_position:
            issues.append(f"pilot-smoke-live.md icinde check satiri sirasi bozuk: {result.get('name')}")
        previous_row_position = row_position
    for row, count in actual_row_counts.items():
        expected_count = expected_row_counts.get(row, 0)
        if expected_count == 0:
            issues.append(f"pilot-smoke-live.md icinde beklenmeyen check satiri var: {row}")
        elif count > expected_count:
            issues.append(f"pilot-smoke-live.md icinde tekrarlanan check satiri var: {row}")

    return (not issues, issues, smoke_payload)


def _check_archive_members(*, archive_members: list[str], manifest: dict) -> list[str]:
    issues: list[str] = []
    output_dir = Path(str(manifest.get("output_dir") or "")).expanduser().resolve()
    expected_members = _expected_bundle_members(output_dir=output_dir, manifest=manifest)
    actual_archive_members = set(archive_members)

    if output_dir.exists():
        actual_output_members = {
            path.relative_to(output_dir).as_posix()
            for path in output_dir.rglob("*")
            if path.is_file()
        }
        for member in sorted(actual_output_members - expected_members):
            issues.append(f"Output klasorunde beklenmeyen dosya var: {member}")

    for member in sorted(expected_members):
        if member not in actual_archive_members:
            issues.append(f"Zip arsivinde {member} eksik")

    for member in sorted(actual_archive_members - expected_members):
        issues.append(f"Zip arsivinde beklenmeyen dosya var: {member}")

    return issues


def _check_archive_manifest_payload(
    *,
    manifest: dict,
    archive_payloads: dict[str, bytes],
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    manifest_member = "pilot-day-zero-manifest.json"
    archive_manifest_bytes = archive_payloads.get(manifest_member)
    if archive_manifest_bytes is None:
        return (False, [f"Zip arsivinde {manifest_member} okunamadi"])

    try:
        archive_manifest = json.loads(archive_manifest_bytes.decode("utf-8"))
    except Exception:
        return (True, [f"Zip icindeki {manifest_member} gecerli json degil"])

    if _canonicalize_manifest_payload(archive_manifest) != _canonicalize_manifest_payload(manifest):
        issues.append(f"Zip icindeki {manifest_member} disaridaki manifest ile uyusmuyor")

    return (True, issues)


def _check_integrity_manifest(
    *,
    output_dir: Path,
    manifest: dict,
    archive_checksums: dict[str, str],
) -> tuple[bool, str | None, int, list[str]]:
    issues: list[str] = []
    integrity = manifest.get("integrity") or {}
    if not integrity:
        return (False, None, 0, issues)

    algorithm = integrity.get("algorithm")
    if algorithm != "sha256":
        issues.append(f"Desteklenmeyen integrity algoritmasi: {algorithm}")

    recorded = integrity.get("files") or {}
    if not isinstance(recorded, dict):
        return (True, str(algorithm), 0, issues + ["Integrity files alani gecersiz"])

    expected_names = {"00-START-HERE.md"}
    for raw_path in (manifest.get("files") or {}).values():
        expected_names.add(Path(str(raw_path)).name)

    for name in sorted(expected_names):
        expected_checksum = recorded.get(name)
        if not expected_checksum:
            issues.append(f"Integrity kaydi eksik: {name}")
            continue

        path = output_dir / name
        if path.exists():
            actual_checksum = _sha256_path(path)
            if actual_checksum != expected_checksum:
                issues.append(f"Integrity checksum uyusmuyor: {name}")

        archive_checksum = archive_checksums.get(name)
        if archive_checksum is None:
            issues.append(f"Integrity icin zip kaydi eksik: {name}")
        elif archive_checksum != expected_checksum:
            issues.append(f"Zip icindeki checksum uyusmuyor: {name}")

    return (True, str(algorithm), len(recorded), issues)


def _check_release_snapshot(*, output_dir: Path, manifest: dict) -> tuple[bool, dict | None, list[str]]:
    issues: list[str] = []
    release_snapshot = manifest.get("release_snapshot") or {}
    if not release_snapshot:
        return (False, None, issues)

    status_json_path = output_dir / "pilot-status-live.json"
    if not status_json_path.exists():
        issues.append("Release snapshot icin pilot-status-live.json bulunamadi")
        return (True, None, issues)

    status_payload = _read_json(status_json_path)
    frontend = status_payload.get("frontend") or {}
    backend = status_payload.get("backend") or {}
    actual = {
        "frontend_release": frontend.get("releaseLabel") or None,
        "backend_release": backend.get("release_label") or None,
    }
    if actual["frontend_release"] and actual["backend_release"]:
        actual["release_alignment"] = (
            "aligned" if actual["frontend_release"] == actual["backend_release"] else "mismatch"
        )
    else:
        actual["release_alignment"] = "unknown"

    for key, label in [
        ("frontend_release", "Frontend release"),
        ("backend_release", "Backend release"),
        ("release_alignment", "Release alignment"),
    ]:
        if release_snapshot.get(key) != actual.get(key):
            issues.append(f"{label} manifest ile pilot-status-live.json uyusmuyor")

    return (True, actual, issues)


def _check_start_here_markdown(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    start_here_path = output_dir / "00-START-HERE.md"
    if not start_here_path.exists():
        issues.append("00-START-HERE.md bulunamadi")
        return (False, issues)

    content = start_here_path.read_text(encoding="utf-8")
    release_snapshot = manifest.get("release_snapshot") or {}
    smoke_included = bool(manifest.get("smoke_included"))
    verify_state = (
        "PASS"
        if manifest.get("verify_passed")
        else ("FAIL" if "verify_passed" in manifest else "BEKLENIYOR")
    )
    if smoke_included:
        smoke_state = (
            "PASS"
            if manifest.get("smoke_overall_ok")
            else ("FAIL" if "smoke_overall_ok" in manifest else "BEKLENIYOR")
        )
    else:
        smoke_state = "ATLANDI"

    expected_snippets = [
        f"- Frontend Release: `{release_snapshot.get('frontend_release') or '-'}`",
        f"- Backend Release: `{release_snapshot.get('backend_release') or '-'}`",
        f"- Release Alignment: `{release_snapshot.get('release_alignment') or '-'}`",
        f"- Verify: `{verify_state}`",
        f"- Smoke: `{smoke_state}`",
    ]

    for snippet in expected_snippets:
        if snippet not in content:
            issues.append(f"00-START-HERE.md icinde beklenen satir eksik: {snippet}")

    verify_next_step = manifest.get("verify_recommended_next_step")
    if verify_next_step and verify_next_step not in content:
        issues.append("00-START-HERE.md icinde verify sonrasi onerilen adim eksik")

    smoke_next_step = manifest.get("smoke_recommended_next_step")
    if smoke_included and smoke_next_step and smoke_next_step not in content:
        issues.append("00-START-HERE.md icinde smoke sonrasi onerilen adim eksik")

    return (True, issues)


def _check_env_payloads(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    service_names = manifest.get("service_names") or {}
    api_service = service_names.get("api")
    frontend_service = service_names.get("frontend")
    streamlit_service = service_names.get("streamlit")

    render_bundle_path = output_dir / "render-env-bundle.env"
    render_bundle_json_path = output_dir / "render-env-bundle.json"
    banner_env_path = output_dir / "streamlit-banner.env"
    redirect_env_path = output_dir / "streamlit-redirect.env"

    if not (
        render_bundle_path.exists()
        and render_bundle_json_path.exists()
        and banner_env_path.exists()
        and redirect_env_path.exists()
    ):
        return (False, ["Env dosyalari eksik oldugu icin env payload kontrolu yapilamadi"])

    render_bundle = _parse_env_bundle(render_bundle_path)
    render_bundle_json = _read_json(render_bundle_json_path)
    banner_bundle = _parse_env_bundle(banner_env_path)
    redirect_bundle = _parse_env_bundle(redirect_env_path)
    expected_render_services = {
        value
        for value in (api_service, frontend_service, streamlit_service)
        if value
    }
    actual_render_services = set(render_bundle.keys())
    if actual_render_services != expected_render_services:
        issues.append("render-env-bundle.env icindeki servis bolumleri manifest service_names ile uyusmuyor")
    actual_banner_services = set(banner_bundle.keys())
    if actual_banner_services != ({streamlit_service} if streamlit_service else set()):
        issues.append("streamlit-banner.env icinde beklenmeyen servis bolumu var")
    actual_redirect_services = set(redirect_bundle.keys())
    if actual_redirect_services != ({streamlit_service} if streamlit_service else set()):
        issues.append("streamlit-redirect.env icinde beklenmeyen servis bolumu var")

    expected_api_keys = {
        "CK_V2_APP_ENV",
        "CK_V2_RENDER_SERVICE_NAME",
        "CK_V2_DATABASE_URL",
        "CK_V2_FRONTEND_BASE_URL",
        "CK_V2_PUBLIC_APP_URL",
        "CK_V2_API_PUBLIC_URL",
        "CK_V2_DEFAULT_AUTH_PASSWORD",
        "AUTH_EBRU_PHONE",
        "AUTH_MERT_PHONE",
        "AUTH_MUHAMMED_PHONE",
        "SMS_PROVIDER",
        "SMS_API_URL",
        "SMS_NETGSM_USERNAME",
        "SMS_NETGSM_PASSWORD",
        "SMS_SENDER",
        "SMS_NETGSM_ENCODING",
    }
    expected_frontend_keys = {
        "CK_V2_FRONTEND_SERVICE_NAME",
        "NEXT_PUBLIC_V2_API_BASE_URL",
        "NEXT_TELEMETRY_DISABLED",
        "CK_V2_INTERNAL_API_HOSTPORT",
    }
    expected_streamlit_keys = {
        "CK_V2_PILOT_URL",
        "CK_V2_CUTOVER_MODE",
    }

    if api_service not in render_bundle:
        issues.append(f"render-env-bundle.env icinde API servisi eksik: {api_service}")
    if frontend_service not in render_bundle:
        issues.append(f"render-env-bundle.env icinde frontend servisi eksik: {frontend_service}")
    if streamlit_service not in render_bundle:
        issues.append(f"render-env-bundle.env icinde streamlit servisi eksik: {streamlit_service}")
    if api_service not in render_bundle_json:
        issues.append(f"render-env-bundle.json icinde API servisi eksik: {api_service}")
    if frontend_service not in render_bundle_json:
        issues.append(f"render-env-bundle.json icinde frontend servisi eksik: {frontend_service}")
    if streamlit_service not in render_bundle_json:
        issues.append(f"render-env-bundle.json icinde streamlit servisi eksik: {streamlit_service}")

    api_env = render_bundle.get(api_service or "", {})
    frontend_env = render_bundle.get(frontend_service or "", {})
    streamlit_env = render_bundle.get(streamlit_service or "", {})
    api_env_json = render_bundle_json.get(api_service or "", {})
    frontend_env_json = render_bundle_json.get(frontend_service or "", {})
    streamlit_env_json = render_bundle_json.get(streamlit_service or "", {})
    banner_env = banner_bundle.get(streamlit_service or "", {})
    redirect_env = redirect_bundle.get(streamlit_service or "", {})

    if api_env and set(api_env.keys()) != expected_api_keys:
        issues.append("render-env-bundle.env icindeki API env anahtarlari beklenen set ile uyusmuyor")
    if api_env_json and set(api_env_json.keys()) != expected_api_keys:
        issues.append("render-env-bundle.json icindeki API env anahtarlari beklenen set ile uyusmuyor")
    if frontend_env and set(frontend_env.keys()) != expected_frontend_keys:
        issues.append("render-env-bundle.env icindeki frontend env anahtarlari beklenen set ile uyusmuyor")
    if frontend_env_json and set(frontend_env_json.keys()) != expected_frontend_keys:
        issues.append("render-env-bundle.json icindeki frontend env anahtarlari beklenen set ile uyusmuyor")
    if streamlit_env and set(streamlit_env.keys()) != expected_streamlit_keys:
        issues.append("render-env-bundle.env icindeki streamlit env anahtarlari beklenen set ile uyusmuyor")
    if streamlit_env_json and set(streamlit_env_json.keys()) != expected_streamlit_keys:
        issues.append("render-env-bundle.json icindeki streamlit env anahtarlari beklenen set ile uyusmuyor")
    if banner_env and set(banner_env.keys()) != expected_streamlit_keys:
        issues.append("streamlit-banner.env icindeki env anahtarlari beklenen set ile uyusmuyor")
    if redirect_env and set(redirect_env.keys()) != expected_streamlit_keys:
        issues.append("streamlit-redirect.env icindeki env anahtarlari beklenen set ile uyusmuyor")

    if api_env.get("CK_V2_FRONTEND_BASE_URL") != manifest.get("frontend_url"):
        issues.append("render-env-bundle.env icinde CK_V2_FRONTEND_BASE_URL uyusmuyor")
    if api_env.get("CK_V2_PUBLIC_APP_URL") != manifest.get("frontend_url"):
        issues.append("render-env-bundle.env icinde CK_V2_PUBLIC_APP_URL uyusmuyor")
    if api_env.get("CK_V2_API_PUBLIC_URL") != manifest.get("api_url"):
        issues.append("render-env-bundle.env icinde CK_V2_API_PUBLIC_URL uyusmuyor")
    if api_env_json.get("CK_V2_FRONTEND_BASE_URL") != manifest.get("frontend_url"):
        issues.append("render-env-bundle.json icinde CK_V2_FRONTEND_BASE_URL uyusmuyor")
    if api_env_json.get("CK_V2_PUBLIC_APP_URL") != manifest.get("frontend_url"):
        issues.append("render-env-bundle.json icinde CK_V2_PUBLIC_APP_URL uyusmuyor")
    if api_env_json.get("CK_V2_API_PUBLIC_URL") != manifest.get("api_url"):
        issues.append("render-env-bundle.json icinde CK_V2_API_PUBLIC_URL uyusmuyor")
    if frontend_env.get("NEXT_PUBLIC_V2_API_BASE_URL") != "/v2-api":
        issues.append("render-env-bundle.env icinde NEXT_PUBLIC_V2_API_BASE_URL beklenen degerde degil")
    if frontend_env_json.get("NEXT_PUBLIC_V2_API_BASE_URL") != "/v2-api":
        issues.append("render-env-bundle.json icinde NEXT_PUBLIC_V2_API_BASE_URL beklenen degerde degil")
    if streamlit_env.get("CK_V2_PILOT_URL") != manifest.get("frontend_url"):
        issues.append("render-env-bundle.env icinde streamlit CK_V2_PILOT_URL uyusmuyor")
    if streamlit_env.get("CK_V2_CUTOVER_MODE") != "banner":
        issues.append("render-env-bundle.env icinde streamlit CK_V2_CUTOVER_MODE banner olmali")
    if streamlit_env_json.get("CK_V2_PILOT_URL") != manifest.get("frontend_url"):
        issues.append("render-env-bundle.json icinde streamlit CK_V2_PILOT_URL uyusmuyor")
    if streamlit_env_json.get("CK_V2_CUTOVER_MODE") != "banner":
        issues.append("render-env-bundle.json icinde streamlit CK_V2_CUTOVER_MODE banner olmali")

    for service_name, env_payload in [
        (api_service, api_env),
        (frontend_service, frontend_env),
        (streamlit_service, streamlit_env),
    ]:
        json_payload = render_bundle_json.get(service_name or "", {})
        if env_payload and json_payload and env_payload != json_payload:
            issues.append(f"render-env-bundle.env ile render-env-bundle.json uyusmuyor: {service_name}")

    if banner_env.get("CK_V2_PILOT_URL") != manifest.get("frontend_url"):
        issues.append("streamlit-banner.env icinde CK_V2_PILOT_URL uyusmuyor")
    if banner_env.get("CK_V2_CUTOVER_MODE") != "banner":
        issues.append("streamlit-banner.env icinde CK_V2_CUTOVER_MODE banner olmali")

    if redirect_env.get("CK_V2_PILOT_URL") != manifest.get("frontend_url"):
        issues.append("streamlit-redirect.env icinde CK_V2_PILOT_URL uyusmuyor")
    if redirect_env.get("CK_V2_CUTOVER_MODE") != "redirect":
        issues.append("streamlit-redirect.env icinde CK_V2_CUTOVER_MODE redirect olmali")

    return (True, issues)


def _check_launch_packets(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    frontend_url = manifest.get("frontend_url")
    api_url = manifest.get("api_url")
    streamlit_url = manifest.get("streamlit_url")
    service_names = manifest.get("service_names") or {}
    api_service = service_names.get("api") or ""
    frontend_service = service_names.get("frontend") or ""
    streamlit_service = service_names.get("streamlit") or ""

    expected_packets = {
        "pilot-launch.md": {
            "label": "pilot-launch.md",
            "cutover_mode": "banner",
        },
        "pilot-cutover.md": {
            "label": "pilot-cutover.md",
            "cutover_mode": "redirect",
        },
    }
    render_bundle_json_path = output_dir / "render-env-bundle.json"
    rendered_base_bundle = _read_json(render_bundle_json_path) if render_bundle_json_path.exists() else {}

    for filename, packet_meta in expected_packets.items():
        path = output_dir / filename
        if not path.exists():
            issues.append(f"{filename} bulunamadi")
            continue

        content = path.read_text(encoding="utf-8")
        expected_snippets = [
            f"- Frontend: `{frontend_url}`",
            f"- Backend: `{api_url}`",
            f"- Streamlit: `{streamlit_url}`",
            f"- Pilot Login: `{frontend_url}/login`",
            f"- Pilot Status: `{frontend_url}/status`",
            f"- Backend Health: `{api_url}/api/health`",
            f"--frontend-url {frontend_url}",
            f"--api-url {api_url}",
            f"--cutover-mode {packet_meta['cutover_mode']}",
            f"6. Streamlit tarafında `{packet_meta['cutover_mode']}` modunu hazırlayıp ofis geçişini başlat.",
            f"[{api_service}]",
            f"[{frontend_service}]",
            f"[{streamlit_service}]",
            f"CK_V2_RENDER_SERVICE_NAME={api_service}",
            f"CK_V2_FRONTEND_SERVICE_NAME={frontend_service}",
            f"CK_V2_FRONTEND_BASE_URL={frontend_url}",
            f"CK_V2_PUBLIC_APP_URL={frontend_url}",
            f"CK_V2_API_PUBLIC_URL={api_url}",
            f"CK_V2_PILOT_URL={frontend_url}",
            f"CK_V2_CUTOVER_MODE={packet_meta['cutover_mode']}",
        ]
        for snippet in expected_snippets:
            if snippet not in content:
                issues.append(f"{packet_meta['label']} icinde beklenen satir eksik: {snippet}")

        if rendered_base_bundle:
            packet_env_block = _extract_fenced_block(content, "dotenv")
            if not packet_env_block:
                issues.append(f"{packet_meta['label']} icinde dotenv blogu bulunamadi")
            else:
                expected_bundle = deepcopy(rendered_base_bundle)
                if streamlit_service in expected_bundle:
                    expected_bundle[streamlit_service]["CK_V2_CUTOVER_MODE"] = packet_meta["cutover_mode"]
                expected_env_block = _render_env_bundle(expected_bundle)
                if packet_env_block != expected_env_block:
                    issues.append(f"{packet_meta['label']} icindeki gomulu env blogu render bundle ile uyusmuyor")

    return (True, issues)


def _check_status_documents(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    frontend_url = manifest.get("frontend_url")
    release_snapshot = manifest.get("release_snapshot") or {}
    smoke_included = bool(manifest.get("smoke_included"))

    status_json_path = output_dir / "pilot-status-live.json"
    status_markdown_path = output_dir / "pilot-status-live.md"
    pilot_gate_json_path = output_dir / "pilot-gate-pilot.json"
    cutover_gate_json_path = output_dir / "pilot-gate-cutover.json"
    preflight_summary_path = output_dir / "pilot-preflight-summary.md"

    required_paths = [
        status_json_path,
        status_markdown_path,
        pilot_gate_json_path,
        cutover_gate_json_path,
        preflight_summary_path,
    ]
    if any(not path.exists() for path in required_paths):
        return (False, ["Status/preflight dosyalari eksik oldugu icin rapor kontrolu yapilamadi"])

    status_payload = _read_json(status_json_path)
    pilot_gate_payload = _read_json(pilot_gate_json_path)
    cutover_gate_payload = _read_json(cutover_gate_json_path)
    status_markdown = status_markdown_path.read_text(encoding="utf-8")
    preflight_summary = preflight_summary_path.read_text(encoding="utf-8")

    backend = status_payload.get("backend") or {}
    frontend = status_payload.get("frontend") or {}
    cutover = backend.get("cutover") or {}
    decision = backend.get("decision") or {}

    expected_status_snippets = [
        f"- Base URL: `{frontend_url}`",
        f"- Frontend Release: `{frontend.get('releaseLabel') or '-'}`",
        f"- Backend Release: `{backend.get('release_label') or '-'}`",
        f"- Release Alignment: `{'Uyumsuz' if release_snapshot.get('release_alignment') == 'mismatch' else ('Uyumlu' if release_snapshot.get('release_alignment') == 'aligned' else 'Eksik Bilgi')}`",
        "## Bugunun Karari",
        f"- Title: {decision.get('title') or '-'}",
        "## Cutover Ozet",
        f"- Phase: `{cutover.get('phase') or '-'}`",
    ]
    for snippet in expected_status_snippets:
        if snippet not in status_markdown:
            issues.append(f"pilot-status-live.md icinde beklenen satir eksik: {snippet}")

    expected_preflight_snippets = [
        f"- Base URL: `{frontend_url}`",
        f"- Decision: {decision.get('title') or '-'}",
        f"- Pilot Gate: `{'PASS' if pilot_gate_payload.get('passed') else 'FAIL'}`",
        f"- Cutover Gate: `{'PASS' if cutover_gate_payload.get('passed') else 'FAIL'}`",
        f"- Summary: {pilot_gate_payload.get('summary') or '-'}",
        f"- Summary: {cutover_gate_payload.get('summary') or '-'}",
        f"- Recommended Next Step: {pilot_gate_payload.get('recommended_next_step') or '-'}",
        f"- Recommended Next Step: {cutover_gate_payload.get('recommended_next_step') or '-'}",
    ]
    expected_preflight_snippets.append(
        f"- Smoke: `{'PASS' if manifest.get('smoke_overall_ok') else 'FAIL'}`" if smoke_included else "- Smoke: `ATLANDI`"
    )
    for snippet in expected_preflight_snippets:
        if snippet not in preflight_summary:
            issues.append(f"pilot-preflight-summary.md icinde beklenen satir eksik: {snippet}")

    return (True, issues)


def _check_embedded_verify_reports(
    *,
    output_dir: Path,
    manifest: dict,
    expected_release_snapshot_ok: bool | None = None,
    expected_env_ok: bool | None = None,
    expected_packet_ok: bool | None = None,
    expected_manifest_core_checked: bool | None = None,
    expected_manifest_core_ok: bool | None = None,
    expected_manifest_summary_checked: bool | None = None,
    expected_manifest_summary_ok: bool | None = None,
    expected_manifest_files_checked: bool | None = None,
    expected_manifest_files_ok: bool | None = None,
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    verify_json_path = output_dir / "pilot-day-zero-verify.json"
    verify_markdown_path = output_dir / "pilot-day-zero-verify.md"

    if not (verify_json_path.exists() and verify_markdown_path.exists()):
        return (False, [])

    verify_payload = _read_json(verify_json_path)
    verify_markdown = verify_markdown_path.read_text(encoding="utf-8")

    expected_status = "PASS" if manifest.get("verify_passed") else "FAIL"
    expected_archive = "OK" if manifest.get("verify_archive_exists") else "MISSING"
    expected_next_step = manifest.get("verify_recommended_next_step") or "-"

    if _canonicalize_path_text(verify_payload.get("output_dir")) != _canonicalize_path_text(manifest.get("output_dir")):
        issues.append("pilot-day-zero-verify.json icinde output_dir manifestle uyusmuyor")
    if _canonicalize_path_text(verify_payload.get("archive_path")) != _canonicalize_path_text(manifest.get("archive_path")):
        issues.append("pilot-day-zero-verify.json icinde archive_path manifestle uyusmuyor")
    if verify_payload.get("passed") != manifest.get("verify_passed"):
        issues.append("pilot-day-zero-verify.json icinde passed degeri manifestle uyusmuyor")
    if verify_payload.get("archive_exists") != manifest.get("verify_archive_exists"):
        issues.append("pilot-day-zero-verify.json icinde archive_exists manifestle uyusmuyor")
    if verify_payload.get("recommended_next_step") != manifest.get("verify_recommended_next_step"):
        issues.append("pilot-day-zero-verify.json icinde recommended_next_step manifestle uyusmuyor")

    if expected_release_snapshot_ok is not None and verify_payload.get("release_snapshot_ok") != expected_release_snapshot_ok:
        issues.append("pilot-day-zero-verify.json icinde release_snapshot_ok guncel verify sonucu ile uyusmuyor")
    if expected_env_ok is not None and verify_payload.get("env_ok") != expected_env_ok:
        issues.append("pilot-day-zero-verify.json icinde env_ok guncel verify sonucu ile uyusmuyor")
    if expected_packet_ok is not None and verify_payload.get("packet_ok") != expected_packet_ok:
        issues.append("pilot-day-zero-verify.json icinde packet_ok guncel verify sonucu ile uyusmuyor")

    if expected_manifest_core_checked is not None and verify_payload.get("manifest_core_checked") != expected_manifest_core_checked:
        issues.append("pilot-day-zero-verify.json icinde manifest_core_checked guncel verify sonucu ile uyusmuyor")
    if expected_manifest_core_ok is not None and verify_payload.get("manifest_core_ok") != expected_manifest_core_ok:
        issues.append("pilot-day-zero-verify.json icinde manifest_core_ok guncel verify sonucu ile uyusmuyor")
    if expected_manifest_summary_checked is not None and verify_payload.get("manifest_summary_checked") != expected_manifest_summary_checked:
        issues.append("pilot-day-zero-verify.json icinde manifest_summary_checked guncel verify sonucu ile uyusmuyor")
    if expected_manifest_summary_ok is not None and verify_payload.get("manifest_summary_ok") != expected_manifest_summary_ok:
        issues.append("pilot-day-zero-verify.json icinde manifest_summary_ok guncel verify sonucu ile uyusmuyor")
    if expected_manifest_files_checked is not None and verify_payload.get("manifest_files_checked") != expected_manifest_files_checked:
        issues.append("pilot-day-zero-verify.json icinde manifest_files_checked guncel verify sonucu ile uyusmuyor")
    if expected_manifest_files_ok is not None and verify_payload.get("manifest_files_ok") != expected_manifest_files_ok:
        issues.append("pilot-day-zero-verify.json icinde manifest_files_ok guncel verify sonucu ile uyusmuyor")

    if manifest.get("smoke_included"):
        if verify_payload.get("smoke_overall_ok") != manifest.get("smoke_overall_ok"):
            issues.append("pilot-day-zero-verify.json icinde smoke_overall_ok manifestle uyusmuyor")
        if verify_payload.get("smoke_failed_count") != manifest.get("smoke_failed_count"):
            issues.append("pilot-day-zero-verify.json icinde smoke_failed_count manifestle uyusmuyor")

    output_dir_variants = {
        f"- Output Dir: `{manifest.get('output_dir')}`",
    }
    canonical_output_dir = _canonicalize_path_text(manifest.get("output_dir"))
    if canonical_output_dir:
        output_dir_variants.add(f"- Output Dir: `{canonical_output_dir}`")

    expected_markdown_snippets = [
        f"- Status: `{expected_status}`",
        f"- Archive: `{expected_archive}`",
        f"- Recommended Next Step: {expected_next_step}",
    ]
    for label, value in [
        ("Release Snapshot", expected_release_snapshot_ok),
        ("Env Payloads", expected_env_ok),
        ("Launch Packets", expected_packet_ok),
    ]:
        if value is not None:
            expected_markdown_snippets.append(f"- {label}: `{'PASS' if value else 'FAIL'}`")
    if expected_manifest_core_checked is not None:
        expected_markdown_snippets.append(
            f"- Manifest Core: `{'PASS' if expected_manifest_core_ok else 'FAIL'}`"
        )
    if expected_manifest_summary_checked is not None:
        expected_markdown_snippets.append(
            f"- Manifest Summary: `{'PASS' if expected_manifest_summary_ok else 'FAIL'}`"
        )
    if expected_manifest_files_checked is not None:
        expected_markdown_snippets.append(
            f"- Manifest Files: `{'PASS' if expected_manifest_files_ok else 'FAIL'}`"
        )
    if not any(snippet in verify_markdown for snippet in output_dir_variants):
        issues.append("pilot-day-zero-verify.md icinde beklenen Output Dir satiri eksik")

    for snippet in expected_markdown_snippets:
        if snippet not in verify_markdown:
            issues.append(f"pilot-day-zero-verify.md icinde beklenen satir eksik: {snippet}")

    return (True, issues)


def _check_manifest_summary(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []

    pilot_gate_json_path = output_dir / "pilot-gate-pilot.json"
    cutover_gate_json_path = output_dir / "pilot-gate-cutover.json"
    banner_guard_json_path = output_dir / "streamlit-banner-guard.json"
    redirect_guard_json_path = output_dir / "streamlit-redirect-guard.json"
    verify_json_path = output_dir / "pilot-day-zero-verify.json"

    required_paths = [
        pilot_gate_json_path,
        cutover_gate_json_path,
        banner_guard_json_path,
        redirect_guard_json_path,
    ]
    if any(not path.exists() for path in required_paths):
        return (False, ["Manifest ozeti icin gerekli gate/guard dosyalari eksik"])

    pilot_gate_payload = _read_json(pilot_gate_json_path)
    cutover_gate_payload = _read_json(cutover_gate_json_path)
    banner_guard_payload = _read_json(banner_guard_json_path)
    redirect_guard_payload = _read_json(redirect_guard_json_path)

    if manifest.get("pilot_gate_passed") != pilot_gate_payload.get("passed"):
        issues.append("Manifest pilot_gate_passed degeri pilot-gate-pilot.json ile uyusmuyor")
    if manifest.get("cutover_gate_passed") != cutover_gate_payload.get("passed"):
        issues.append("Manifest cutover_gate_passed degeri pilot-gate-cutover.json ile uyusmuyor")
    if manifest.get("banner_guard_allowed") != banner_guard_payload.get("allowed"):
        issues.append("Manifest banner_guard_allowed degeri streamlit-banner-guard.json ile uyusmuyor")
    if manifest.get("redirect_guard_allowed") != redirect_guard_payload.get("allowed"):
        issues.append("Manifest redirect_guard_allowed degeri streamlit-redirect-guard.json ile uyusmuyor")

    if verify_json_path.exists():
        verify_payload = _read_json(verify_json_path)
        if "verify_passed" in manifest and manifest.get("verify_passed") != verify_payload.get("passed"):
            issues.append("Manifest verify_passed degeri pilot-day-zero-verify.json ile uyusmuyor")
        if "verify_missing_files_count" in manifest and manifest.get("verify_missing_files_count") != len(verify_payload.get("missing_files") or []):
            issues.append("Manifest verify_missing_files_count degeri pilot-day-zero-verify.json ile uyusmuyor")
        if "verify_consistency_issues_count" in manifest and manifest.get("verify_consistency_issues_count") != len(verify_payload.get("consistency_issues") or []):
            issues.append("Manifest verify_consistency_issues_count degeri pilot-day-zero-verify.json ile uyusmuyor")
        if "verify_archive_exists" in manifest and manifest.get("verify_archive_exists") != verify_payload.get("archive_exists"):
            issues.append("Manifest verify_archive_exists degeri pilot-day-zero-verify.json ile uyusmuyor")

    return (True, issues)


def _check_manifest_file_map(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    files = manifest.get("files") or {}
    expected_files = {
        "render_env_bundle_env": "render-env-bundle.env",
        "render_env_bundle_json": "render-env-bundle.json",
        "streamlit_banner_env": "streamlit-banner.env",
        "streamlit_redirect_env": "streamlit-redirect.env",
        "streamlit_banner_guard_json": "streamlit-banner-guard.json",
        "streamlit_redirect_guard_json": "streamlit-redirect-guard.json",
        "streamlit_banner_guarded_env": "streamlit-banner-guarded.env",
        "streamlit_redirect_guarded_env": "streamlit-redirect-guarded.env",
        "pilot_launch_packet": "pilot-launch.md",
        "pilot_cutover_packet": "pilot-cutover.md",
        "summary_markdown": "pilot-preflight-summary.md",
        "status_markdown": "pilot-status-live.md",
        "status_json": "pilot-status-live.json",
        "pilot_gate_json": "pilot-gate-pilot.json",
        "cutover_gate_json": "pilot-gate-cutover.json",
    }
    if manifest.get("smoke_included"):
        expected_files["smoke_markdown"] = "pilot-smoke-live.md"
        expected_files["smoke_json"] = "pilot-smoke-live.json"
    if "verify_json" in files or (output_dir / "pilot-day-zero-verify.json").exists():
        expected_files["verify_json"] = "pilot-day-zero-verify.json"
    if "verify_markdown" in files or (output_dir / "pilot-day-zero-verify.md").exists():
        expected_files["verify_markdown"] = "pilot-day-zero-verify.md"

    for label, expected_name in expected_files.items():
        raw_path = files.get(label)
        if not raw_path:
            issues.append(f"Manifest files icinde beklenen etiket eksik: {label}")
            continue
        actual_path = Path(str(raw_path))
        if actual_path.name != expected_name:
            issues.append(f"Manifest files icinde {label} beklenen dosyaya gitmiyor: {expected_name}")
        expected_path = output_dir / expected_name
        if _canonicalize_path_text(actual_path) != _canonicalize_path_text(expected_path):
            issues.append(f"Manifest files icinde {label} path uyusmuyor: {expected_path}")

    unexpected_labels = sorted(set(files.keys()) - set(expected_files.keys()))
    for label in unexpected_labels:
        issues.append(f"Manifest files icinde beklenmeyen etiket var: {label}")

    return (True, issues)


def _check_manifest_core(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []

    frontend_url = str(manifest.get("frontend_url") or "").strip()
    api_url = str(manifest.get("api_url") or "").strip()
    streamlit_url = str(manifest.get("streamlit_url") or "").strip()
    generated_at = str(manifest.get("generated_at") or "").strip()
    service_names = manifest.get("service_names") or {}
    archive_path = _canonicalize_path_text(manifest.get("archive_path")) or ""
    expected_archive_path = str((output_dir.parent / f"{output_dir.name}.zip").resolve())

    for label, value in [
        ("frontend_url", frontend_url),
        ("api_url", api_url),
        ("streamlit_url", streamlit_url),
    ]:
        if not value.startswith("https://"):
            issues.append(f"Manifest {label} https ile baslamiyor")

    if not generated_at:
        issues.append("Manifest generated_at bos")

    if archive_path != expected_archive_path:
        issues.append("Manifest archive_path beklenen zip yoluyla uyusmuyor")

    for label in ("api", "frontend", "streamlit"):
        value = str(service_names.get(label) or "").strip()
        if not value:
            issues.append(f"Manifest service_names icinde {label} eksik")
        elif any(ch.isspace() for ch in value):
            issues.append(f"Manifest service_names icinde {label} bosluk iceriyor")

    start_here_path = output_dir / "00-START-HERE.md"
    if start_here_path.exists():
        start_here = start_here_path.read_text(encoding="utf-8")
        expected_snippets = [
            f"- Frontend URL: `{frontend_url}`",
            f"- API URL: `{api_url}`",
            f"- Streamlit URL: `{streamlit_url}`",
        ]
        for snippet in expected_snippets:
            if snippet not in start_here:
                issues.append(f"00-START-HERE.md icinde cekirdek metadata eksik: {snippet}")

    render_env_bundle_json_path = output_dir / "render-env-bundle.json"
    if render_env_bundle_json_path.exists():
        render_env_bundle_json = _read_json(render_env_bundle_json_path)
        if set(render_env_bundle_json.keys()) != set(service_names.values()):
            issues.append("Manifest service_names ile render-env-bundle.json servisleri uyusmuyor")

    banner_guard_json_path = output_dir / "streamlit-banner-guard.json"
    redirect_guard_json_path = output_dir / "streamlit-redirect-guard.json"
    for guard_path in (banner_guard_json_path, redirect_guard_json_path):
        if not guard_path.exists():
            continue
        guard_payload = _read_json(guard_path)
        if guard_payload.get("base_url") != frontend_url:
            issues.append(f"{guard_path.name} icinde base_url manifest frontend_url ile uyusmuyor")
        if guard_payload.get("streamlit_service_name") != service_names.get("streamlit"):
            issues.append(f"{guard_path.name} icinde streamlit service name manifestle uyusmuyor")

    return (True, issues)


def verify_day_zero_bundle(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    manifest_path = output_dir / "pilot-day-zero-manifest.json"

    missing_files: list[str] = []
    consistency_issues: list[str] = []
    archive_members: list[str] = []
    archive_checksums: dict[str, str] = {}
    archive_payloads: dict[str, bytes] = {}

    if not output_dir.exists():
        missing_files.append(str(output_dir))
        return {
            "passed": False,
            "output_dir": str(output_dir),
            "missing_files": missing_files,
            "consistency_issues": ["Day-zero klasoru bulunamadi"],
            "archive_path": None,
            "archive_exists": False,
            "archive_members_count": 0,
            "recommended_next_step": "Önce pilot_day_zero.py ile kit olustur.",
        }

    for filename in REQUIRED_FILES:
        if not (output_dir / filename).exists():
            missing_files.append(str(output_dir / filename))

    if not manifest_path.exists():
        return {
            "passed": False,
            "output_dir": str(output_dir),
            "missing_files": missing_files + [str(manifest_path)],
            "consistency_issues": ["Manifest bulunamadigi icin ayrintili dogrulama yapilamadi"],
            "archive_path": None,
            "archive_exists": False,
            "archive_members_count": 0,
            "recommended_next_step": "pilot_day_zero.py komutunu yeniden calistir ve manifest olustugunu dogrula.",
        }

    manifest = _read_json(manifest_path)
    manifest_files = manifest.get("files") or {}

    for label, raw_path in manifest_files.items():
        path = Path(str(raw_path))
        if not path.exists():
            missing_files.append(str(path))
            consistency_issues.append(f"Manifest girdisi eksik dosyaya isaret ediyor: {label}")

    expected_output_dir = str(output_dir)
    if _canonicalize_path_text(manifest.get("output_dir")) != expected_output_dir:
        consistency_issues.append(
            f"Manifest output_dir uyusmuyor: {manifest.get('output_dir')} != {expected_output_dir}"
        )

    banner_ok, banner_issues = _check_guard_file(
        mode="banner",
        guard_json_path=output_dir / "streamlit-banner-guard.json",
        guarded_env_path=output_dir / "streamlit-banner-guarded.env",
        manifest=manifest,
        expected_allowed=manifest.get("banner_guard_allowed"),
    )
    redirect_ok, redirect_issues = _check_guard_file(
        mode="redirect",
        guard_json_path=output_dir / "streamlit-redirect-guard.json",
        guarded_env_path=output_dir / "streamlit-redirect-guarded.env",
        manifest=manifest,
        expected_allowed=manifest.get("redirect_guard_allowed"),
    )
    if not banner_ok:
        consistency_issues.extend(banner_issues)
    if not redirect_ok:
        consistency_issues.extend(redirect_issues)

    archive_path = manifest.get("archive_path")
    archive_exists = False
    if archive_path:
        archive_file = Path(str(archive_path)).resolve()
        archive_exists = archive_file.exists()
        if not archive_exists:
            missing_files.append(str(archive_file))
            consistency_issues.append("Manifest archive_path var ama zip arsivi bulunamadi")
        else:
            with zipfile.ZipFile(archive_file) as archive:
                archive_members = archive.namelist()
                archive_payloads = {
                    member: archive.read(member)
                    for member in archive_members
                    if not member.endswith("/")
                }
                archive_checksums = {
                    member: _sha256_bytes(payload)
                    for member, payload in archive_payloads.items()
                }
            consistency_issues.extend(_check_archive_members(archive_members=archive_members, manifest=manifest))

    smoke_ok, smoke_issues, smoke_payload = _check_smoke_consistency(
        output_dir=output_dir,
        manifest=manifest,
    )
    if not smoke_ok:
        consistency_issues.extend(smoke_issues)

    integrity_checked, integrity_algorithm, integrity_entries_count, integrity_issues = _check_integrity_manifest(
        output_dir=output_dir,
        manifest=manifest,
        archive_checksums=archive_checksums,
    )
    consistency_issues.extend(integrity_issues)

    archive_manifest_checked, archive_manifest_issues = _check_archive_manifest_payload(
        manifest=manifest,
        archive_payloads=archive_payloads,
    ) if archive_exists else (False, [])
    consistency_issues.extend(archive_manifest_issues)

    release_snapshot_checked, release_snapshot_actual, release_snapshot_issues = _check_release_snapshot(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(release_snapshot_issues)

    start_here_checked, start_here_issues = _check_start_here_markdown(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(start_here_issues)

    env_checked, env_issues = _check_env_payloads(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(env_issues)

    packet_checked, packet_issues = _check_launch_packets(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(packet_issues)

    reports_checked, report_issues = _check_status_documents(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(report_issues)

    manifest_summary_checked, manifest_summary_issues = _check_manifest_summary(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(manifest_summary_issues)

    manifest_file_map_checked, manifest_file_map_issues = _check_manifest_file_map(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(manifest_file_map_issues)

    manifest_core_checked, manifest_core_issues = _check_manifest_core(
        output_dir=output_dir,
        manifest=manifest,
    )
    consistency_issues.extend(manifest_core_issues)

    verify_reports_checked, verify_report_issues = _check_embedded_verify_reports(
        output_dir=output_dir,
        manifest=manifest,
        expected_release_snapshot_ok=(not release_snapshot_issues) if release_snapshot_checked else None,
        expected_env_ok=(not env_issues) if env_checked else None,
        expected_packet_ok=(not packet_issues) if packet_checked else None,
        expected_manifest_core_checked=manifest_core_checked,
        expected_manifest_core_ok=(not manifest_core_issues) if manifest_core_checked else None,
        expected_manifest_summary_checked=manifest_summary_checked,
        expected_manifest_summary_ok=(not manifest_summary_issues) if manifest_summary_checked else None,
        expected_manifest_files_checked=manifest_file_map_checked,
        expected_manifest_files_ok=(not manifest_file_map_issues) if manifest_file_map_checked else None,
    )
    consistency_issues.extend(verify_report_issues)

    passed = not missing_files and not consistency_issues
    recommended_next_step = (
        "Day-zero kiti kullanima hazir."
        if passed
        else "pilot_day_zero.py komutunu yeniden calistirip eksik dosyalari ve guard ciktilarini kontrol et."
    )

    return {
        "passed": passed,
        "output_dir": str(output_dir),
        "missing_files": missing_files,
        "consistency_issues": consistency_issues,
        "archive_path": archive_path,
        "archive_exists": archive_exists,
        "archive_members_count": len(archive_members),
        "smoke_included": bool(manifest.get("smoke_included")),
        "smoke_checked": bool(manifest.get("smoke_included")),
        "smoke_overall_ok": (smoke_payload or {}).get("overall_ok") if smoke_payload else None,
        "smoke_failed_count": (smoke_payload or {}).get("failed_count") if smoke_payload else None,
        "integrity_checked": integrity_checked,
        "integrity_ok": True if integrity_checked and not integrity_issues else (False if integrity_checked else None),
        "integrity_algorithm": integrity_algorithm,
        "integrity_entries_count": integrity_entries_count,
        "archive_manifest_checked": archive_manifest_checked,
        "archive_manifest_ok": True if archive_manifest_checked and not archive_manifest_issues else (False if archive_manifest_checked else None),
        "release_snapshot_checked": release_snapshot_checked,
        "release_snapshot_ok": True if release_snapshot_checked and not release_snapshot_issues else (False if release_snapshot_checked else None),
        "release_snapshot": manifest.get("release_snapshot"),
        "release_snapshot_actual": release_snapshot_actual,
        "start_here_checked": start_here_checked,
        "start_here_ok": True if start_here_checked and not start_here_issues else (False if start_here_checked else None),
        "env_checked": env_checked,
        "env_ok": True if env_checked and not env_issues else (False if env_checked else None),
        "packet_checked": packet_checked,
        "packet_ok": True if packet_checked and not packet_issues else (False if packet_checked else None),
        "reports_checked": reports_checked,
        "reports_ok": True if reports_checked and not report_issues else (False if reports_checked else None),
        "verify_reports_checked": verify_reports_checked,
        "verify_reports_ok": True if verify_reports_checked and not verify_report_issues else (False if verify_reports_checked else None),
        "manifest_summary_checked": manifest_summary_checked,
        "manifest_summary_ok": True if manifest_summary_checked and not manifest_summary_issues else (False if manifest_summary_checked else None),
        "manifest_files_checked": manifest_file_map_checked,
        "manifest_files_ok": True if manifest_file_map_checked and not manifest_file_map_issues else (False if manifest_file_map_checked else None),
        "manifest_core_checked": manifest_core_checked,
        "manifest_core_ok": True if manifest_core_checked and not manifest_core_issues else (False if manifest_core_checked else None),
        "recommended_next_step": recommended_next_step,
    }


def render_console_summary(result: dict) -> str:
    smoke_checked = bool(result.get("smoke_checked"))
    smoke_overall_ok = result.get("smoke_overall_ok")
    integrity_checked = bool(result.get("integrity_checked"))
    integrity_ok = result.get("integrity_ok")
    archive_manifest_checked = bool(result.get("archive_manifest_checked"))
    archive_manifest_ok = result.get("archive_manifest_ok")
    release_snapshot_checked = bool(result.get("release_snapshot_checked"))
    release_snapshot_ok = result.get("release_snapshot_ok")
    start_here_checked = bool(result.get("start_here_checked"))
    start_here_ok = result.get("start_here_ok")
    env_checked = bool(result.get("env_checked"))
    env_ok = result.get("env_ok")
    packet_checked = bool(result.get("packet_checked"))
    packet_ok = result.get("packet_ok")
    reports_checked = bool(result.get("reports_checked"))
    reports_ok = result.get("reports_ok")
    verify_reports_checked = bool(result.get("verify_reports_checked"))
    verify_reports_ok = result.get("verify_reports_ok")
    manifest_summary_checked = bool(result.get("manifest_summary_checked"))
    manifest_summary_ok = result.get("manifest_summary_ok")
    manifest_files_checked = bool(result.get("manifest_files_checked"))
    manifest_files_ok = result.get("manifest_files_ok")
    manifest_core_checked = bool(result.get("manifest_core_checked"))
    manifest_core_ok = result.get("manifest_core_ok")
    lines = [
        "Cat Kapinda CRM v2 Day Zero Verify",
        f"Output Dir: {result['output_dir']}",
        f"Status: {'PASS' if result['passed'] else 'FAIL'}",
        f"Archive: {'OK' if result['archive_exists'] else 'MISSING'}",
        f"Archive Members: {result['archive_members_count']}",
        (
            f"Integrity: {'PASS' if integrity_ok else 'FAIL'} ({result.get('integrity_algorithm')}, {result.get('integrity_entries_count')} kayit)"
            if integrity_checked
            else "Integrity: SKIPPED"
        ),
        (
            f"Archive Manifest: {'PASS' if archive_manifest_ok else 'FAIL'}"
            if archive_manifest_checked
            else "Archive Manifest: SKIPPED"
        ),
        (
            f"Release Snapshot: {'PASS' if release_snapshot_ok else 'FAIL'}"
            if release_snapshot_checked
            else "Release Snapshot: SKIPPED"
        ),
        (
            f"Start Here: {'PASS' if start_here_ok else 'FAIL'}"
            if start_here_checked
            else "Start Here: SKIPPED"
        ),
        (
            f"Env Payloads: {'PASS' if env_ok else 'FAIL'}"
            if env_checked
            else "Env Payloads: SKIPPED"
        ),
        (
            f"Launch Packets: {'PASS' if packet_ok else 'FAIL'}"
            if packet_checked
            else "Launch Packets: SKIPPED"
        ),
        (
            f"Status Reports: {'PASS' if reports_ok else 'FAIL'}"
            if reports_checked
            else "Status Reports: SKIPPED"
        ),
        (
            f"Embedded Verify Reports: {'PASS' if verify_reports_ok else 'FAIL'}"
            if verify_reports_checked
            else "Embedded Verify Reports: SKIPPED"
        ),
        (
            f"Manifest Summary: {'PASS' if manifest_summary_ok else 'FAIL'}"
            if manifest_summary_checked
            else "Manifest Summary: SKIPPED"
        ),
        (
            f"Manifest Files: {'PASS' if manifest_files_ok else 'FAIL'}"
            if manifest_files_checked
            else "Manifest Files: SKIPPED"
        ),
        (
            f"Manifest Core: {'PASS' if manifest_core_ok else 'FAIL'}"
            if manifest_core_checked
            else "Manifest Core: SKIPPED"
        ),
        (
            f"Smoke: {'PASS' if smoke_overall_ok else 'FAIL'}"
            if smoke_checked and smoke_overall_ok is not None
            else "Smoke: SKIPPED"
        ),
        f"Recommended Next Step: {result['recommended_next_step']}",
        "Missing Files:",
    ]
    lines.extend([f"- {item}" for item in result["missing_files"]] or ["- Yok"])
    lines.append("Consistency Issues:")
    lines.extend([f"- {item}" for item in result["consistency_issues"]] or ["- Yok"])
    return "\n".join(lines) + "\n"


def render_markdown_report(result: dict) -> str:
    smoke_checked = bool(result.get("smoke_checked"))
    smoke_overall_ok = result.get("smoke_overall_ok")
    integrity_checked = bool(result.get("integrity_checked"))
    integrity_ok = result.get("integrity_ok")
    archive_manifest_checked = bool(result.get("archive_manifest_checked"))
    archive_manifest_ok = result.get("archive_manifest_ok")
    release_snapshot_checked = bool(result.get("release_snapshot_checked"))
    release_snapshot_ok = result.get("release_snapshot_ok")
    start_here_checked = bool(result.get("start_here_checked"))
    start_here_ok = result.get("start_here_ok")
    env_checked = bool(result.get("env_checked"))
    env_ok = result.get("env_ok")
    packet_checked = bool(result.get("packet_checked"))
    packet_ok = result.get("packet_ok")
    reports_checked = bool(result.get("reports_checked"))
    reports_ok = result.get("reports_ok")
    verify_reports_checked = bool(result.get("verify_reports_checked"))
    verify_reports_ok = result.get("verify_reports_ok")
    manifest_summary_checked = bool(result.get("manifest_summary_checked"))
    manifest_summary_ok = result.get("manifest_summary_ok")
    manifest_files_checked = bool(result.get("manifest_files_checked"))
    manifest_files_ok = result.get("manifest_files_ok")
    manifest_core_checked = bool(result.get("manifest_core_checked"))
    manifest_core_ok = result.get("manifest_core_ok")
    lines = [
        "# Cat Kapinda CRM v2 Day Zero Verify",
        "",
        f"- Output Dir: `{result['output_dir']}`",
        f"- Status: `{'PASS' if result['passed'] else 'FAIL'}`",
        f"- Archive: `{'OK' if result['archive_exists'] else 'MISSING'}`",
        f"- Archive Members: `{result['archive_members_count']}`",
        (
            f"- Integrity: `{'PASS' if integrity_ok else 'FAIL'}` (`{result.get('integrity_algorithm')}`, `{result.get('integrity_entries_count')}` kayit)"
            if integrity_checked
            else "- Integrity: `SKIPPED`"
        ),
        (
            f"- Archive Manifest: `{'PASS' if archive_manifest_ok else 'FAIL'}`"
            if archive_manifest_checked
            else "- Archive Manifest: `SKIPPED`"
        ),
        (
            f"- Release Snapshot: `{'PASS' if release_snapshot_ok else 'FAIL'}`"
            if release_snapshot_checked
            else "- Release Snapshot: `SKIPPED`"
        ),
        (
            f"- Start Here: `{'PASS' if start_here_ok else 'FAIL'}`"
            if start_here_checked
            else "- Start Here: `SKIPPED`"
        ),
        (
            f"- Env Payloads: `{'PASS' if env_ok else 'FAIL'}`"
            if env_checked
            else "- Env Payloads: `SKIPPED`"
        ),
        (
            f"- Launch Packets: `{'PASS' if packet_ok else 'FAIL'}`"
            if packet_checked
            else "- Launch Packets: `SKIPPED`"
        ),
        (
            f"- Status Reports: `{'PASS' if reports_ok else 'FAIL'}`"
            if reports_checked
            else "- Status Reports: `SKIPPED`"
        ),
        (
            f"- Embedded Verify Reports: `{'PASS' if verify_reports_ok else 'FAIL'}`"
            if verify_reports_checked
            else "- Embedded Verify Reports: `SKIPPED`"
        ),
        (
            f"- Manifest Summary: `{'PASS' if manifest_summary_ok else 'FAIL'}`"
            if manifest_summary_checked
            else "- Manifest Summary: `SKIPPED`"
        ),
        (
            f"- Manifest Files: `{'PASS' if manifest_files_ok else 'FAIL'}`"
            if manifest_files_checked
            else "- Manifest Files: `SKIPPED`"
        ),
        (
            f"- Manifest Core: `{'PASS' if manifest_core_ok else 'FAIL'}`"
            if manifest_core_checked
            else "- Manifest Core: `SKIPPED`"
        ),
        (
            f"- Smoke: `{'PASS' if smoke_overall_ok else 'FAIL'}`"
            if smoke_checked and smoke_overall_ok is not None
            else "- Smoke: `SKIPPED`"
        ),
        f"- Recommended Next Step: {result['recommended_next_step']}",
        "",
        "## Missing Files",
        "",
        *([f"- `{item}`" for item in result["missing_files"]] or ["- Yok"]),
        "",
        "## Consistency Issues",
        "",
        *([f"- {item}" for item in result["consistency_issues"]] or ["- Yok"]),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that a Cat Kapinda CRM v2 day-zero bundle is complete and internally consistent."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory created by pilot_day_zero.py (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the verification result as JSON",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print the verification result as Markdown",
    )
    args = parser.parse_args()

    result = verify_day_zero_bundle(Path(args.output_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(render_markdown_report(result))
    else:
        print(render_console_summary(result), end="")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
