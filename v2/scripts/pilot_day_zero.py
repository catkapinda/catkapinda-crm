#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import zipfile

from pilot_cutover_guard import build_guard_result, render_env_text as render_guard_env_text
from pilot_launch_packet import build_packet
from pilot_preflight import build_preflight_bundle
from pilot_status_report import fetch_pilot_status
from pilot_day_zero_verify import render_markdown_report as render_verify_markdown_report, verify_day_zero_bundle
from render_env_bundle import build_bundle, filter_bundle, normalize_url, render_text


DEFAULT_TIMEOUT = 12


def _derive_api_url(payload: dict) -> str | None:
    backend = payload.get("backend") or {}
    services = backend.get("services") or []
    for service in services:
        if service.get("service_type") == "backend" and service.get("public_url"):
            return normalize_url(service["public_url"])
    return None


def _build_start_here_markdown(
    *,
    generated_at: str,
    frontend_url: str,
    api_url: str,
    streamlit_url: str,
    pilot_gate_passed: bool,
    cutover_gate_passed: bool,
    banner_guard_allowed: bool,
    redirect_guard_allowed: bool,
    verify_passed: bool | None = None,
    verify_next_step: str | None = None,
    smoke_overall_ok: bool | None = None,
    smoke_next_step: str | None = None,
) -> str:
    lines = [
        "# Cat Kapinda CRM v2 Day Zero - Start Here",
        "",
        f"- Generated At: `{generated_at}`",
        f"- Frontend URL: `{frontend_url}`",
        f"- API URL: `{api_url}`",
        f"- Streamlit URL: `{streamlit_url}`",
        f"- Pilot Gate: `{'PASS' if pilot_gate_passed else 'FAIL'}`",
        f"- Cutover Gate: `{'PASS' if cutover_gate_passed else 'FAIL'}`",
        f"- Banner Guard: `{'PASS' if banner_guard_allowed else 'BLOCK'}`",
        f"- Redirect Guard: `{'PASS' if redirect_guard_allowed else 'BLOCK'}`",
        (
            f"- Verify: `{'PASS' if verify_passed else 'FAIL'}`"
            if verify_passed is not None
            else "- Verify: `BEKLENIYOR`"
        ),
        (
            f"- Smoke: `{'PASS' if smoke_overall_ok else 'FAIL'}`"
            if smoke_overall_ok is not None
            else "- Smoke: `ATLANDI`"
        ),
        "",
        "## Nereden Baslayacagiz",
        "",
        "1. `pilot-preflight-summary.md` dosyasini ac.",
        "2. `pilot-status-live.md` ile canli durumu oku.",
        "3. Render'a yapistirmak icin `render-env-bundle.env` dosyasini kullan.",
        "4. Eski panelde kontrollu gecis icin `streamlit-banner-guarded.env` dosyasina bak.",
        "5. Redirect only if `streamlit-redirect-guarded.env` bos degilse ve guard PASS ise gec.",
        "",
        "## Onemli Dosyalar",
        "",
        "- `render-env-bundle.env`: tum servisler icin temel env plani",
        "- `pilot-launch.md`: pilot acilis paketi",
        "- `pilot-cutover.md`: redirect provasi paketi",
        "- `pilot-status-live.md`: canli /api/pilot-status ozeti",
        "- `pilot-gate-pilot.json`: pilot karari",
        "- `pilot-gate-cutover.json`: redirect karari",
        "- `pilot-day-zero-verify.md`: kit dogrulama ozeti",
        "- `pilot-day-zero-verify.json`: kit dogrulama json ciktisi",
        "- `streamlit-banner-guarded.env`: guvenli banner gecisi",
        "- `streamlit-redirect-guarded.env`: guvenli redirect gecisi",
        "",
    ]
    if verify_next_step:
        lines.extend(
            [
                "## Verify Sonrasi Sonraki Adim",
                "",
                verify_next_step,
                "",
            ]
        )
    if smoke_next_step:
        lines.extend(
            [
                "## Smoke Sonrasi Sonraki Adim",
                "",
                smoke_next_step,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _zip_directory(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(source_dir))


def build_day_zero_bundle(
    *,
    frontend_url: str,
    api_url: str,
    streamlit_url: str,
    output_dir: Path,
    timeout: int,
    database_url: str,
    default_auth_password: str,
    identity: str,
    password_placeholder: str,
    api_service_name: str,
    frontend_service_name: str,
    streamlit_service_name: str,
    include_smoke: bool = False,
    smoke_identity: str | None = None,
    smoke_password: str | None = None,
    smoke_preset: str | None = None,
    smoke_legacy_url: str | None = None,
    smoke_legacy_cutover_mode: str | None = None,
) -> dict:
    generated_at = datetime.now(UTC).isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_payload = fetch_pilot_status(frontend_url, timeout)

    env_bundle = build_bundle(
        frontend_url=frontend_url,
        api_url=api_url,
        database_url=database_url,
        default_auth_password=default_auth_password,
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
        cutover_mode="banner",
    )

    (output_dir / "render-env-bundle.env").write_text(render_text(env_bundle), encoding="utf-8")
    (output_dir / "render-env-bundle.json").write_text(
        json.dumps(env_bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    streamlit_banner = filter_bundle(
        env_bundle,
        "streamlit",
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
    )
    (output_dir / "streamlit-banner.env").write_text(render_text(streamlit_banner), encoding="utf-8")

    redirect_bundle = build_bundle(
        frontend_url=frontend_url,
        api_url=api_url,
        database_url=database_url,
        default_auth_password=default_auth_password,
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
        cutover_mode="redirect",
    )
    streamlit_redirect = filter_bundle(
        redirect_bundle,
        "streamlit",
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
    )
    (output_dir / "streamlit-redirect.env").write_text(render_text(streamlit_redirect), encoding="utf-8")

    banner_guard = build_guard_result(
        base_url=frontend_url,
        mode="banner",
        payload=status_payload,
        streamlit_service_name=streamlit_service_name,
        force=False,
    )
    cutover_guard = build_guard_result(
        base_url=frontend_url,
        mode="redirect",
        payload=status_payload,
        streamlit_service_name=streamlit_service_name,
        force=False,
    )
    (output_dir / "streamlit-banner-guard.json").write_text(
        json.dumps(banner_guard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "streamlit-redirect-guard.json").write_text(
        json.dumps(cutover_guard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "streamlit-banner-guarded.env").write_text(
        render_guard_env_text(banner_guard["env_bundle"]) if banner_guard["allowed"] else "# guard blocked banner env\n",
        encoding="utf-8",
    )
    (output_dir / "streamlit-redirect-guarded.env").write_text(
        render_guard_env_text(cutover_guard["env_bundle"]) if cutover_guard["allowed"] else "# guard blocked redirect env\n",
        encoding="utf-8",
    )

    pilot_launch_packet = build_packet(
        frontend_url=frontend_url,
        api_url=api_url,
        streamlit_url=streamlit_url,
        identity=identity,
        password_placeholder=password_placeholder,
        cutover_mode="banner",
        database_url=database_url,
        default_auth_password=default_auth_password,
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
    )
    (output_dir / "pilot-launch.md").write_text(pilot_launch_packet, encoding="utf-8")

    pilot_cutover_packet = build_packet(
        frontend_url=frontend_url,
        api_url=api_url,
        streamlit_url=streamlit_url,
        identity=identity,
        password_placeholder=password_placeholder,
        cutover_mode="redirect",
        database_url=database_url,
        default_auth_password=default_auth_password,
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
    )
    (output_dir / "pilot-cutover.md").write_text(pilot_cutover_packet, encoding="utf-8")

    preflight_result = build_preflight_bundle(
        base_url=frontend_url,
        timeout=timeout,
        output_dir=output_dir,
        include_smoke=include_smoke,
        identity=smoke_identity,
        password=smoke_password,
        preset=smoke_preset,
        legacy_url=smoke_legacy_url,
        legacy_cutover_mode=smoke_legacy_cutover_mode,
    )
    smoke_report = preflight_result.get("smoke_report")

    manifest = {
        "generated_at": generated_at,
        "frontend_url": frontend_url,
        "api_url": api_url,
        "streamlit_url": streamlit_url,
        "output_dir": str(output_dir),
        "pilot_gate_passed": preflight_result["pilot_gate"]["passed"],
        "cutover_gate_passed": preflight_result["cutover_gate"]["passed"],
        "banner_guard_allowed": banner_guard["allowed"],
        "redirect_guard_allowed": cutover_guard["allowed"],
        "smoke_included": include_smoke,
        "files": {
            "render_env_bundle_env": str(output_dir / "render-env-bundle.env"),
            "render_env_bundle_json": str(output_dir / "render-env-bundle.json"),
            "streamlit_banner_env": str(output_dir / "streamlit-banner.env"),
            "streamlit_redirect_env": str(output_dir / "streamlit-redirect.env"),
            "streamlit_banner_guard_json": str(output_dir / "streamlit-banner-guard.json"),
            "streamlit_redirect_guard_json": str(output_dir / "streamlit-redirect-guard.json"),
            "streamlit_banner_guarded_env": str(output_dir / "streamlit-banner-guarded.env"),
            "streamlit_redirect_guarded_env": str(output_dir / "streamlit-redirect-guarded.env"),
            "pilot_launch_packet": str(output_dir / "pilot-launch.md"),
            "pilot_cutover_packet": str(output_dir / "pilot-cutover.md"),
            **preflight_result["files"],
        },
    }
    (output_dir / "pilot-day-zero-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "00-START-HERE.md").write_text(
        _build_start_here_markdown(
            generated_at=generated_at,
            frontend_url=frontend_url,
            api_url=api_url,
            streamlit_url=streamlit_url,
            pilot_gate_passed=preflight_result["pilot_gate"]["passed"],
            cutover_gate_passed=preflight_result["cutover_gate"]["passed"],
            banner_guard_allowed=banner_guard["allowed"],
            redirect_guard_allowed=cutover_guard["allowed"],
        ),
        encoding="utf-8",
    )
    archive_path = output_dir.parent / f"{output_dir.name}.zip"
    manifest["archive_path"] = str(archive_path)
    (output_dir / "pilot-day-zero-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _zip_directory(output_dir, archive_path)

    verify_result = verify_day_zero_bundle(output_dir)
    (output_dir / "pilot-day-zero-verify.json").write_text(
        json.dumps(verify_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "pilot-day-zero-verify.md").write_text(
        render_verify_markdown_report(verify_result) + "\n",
        encoding="utf-8",
    )
    manifest["files"]["verify_json"] = str(output_dir / "pilot-day-zero-verify.json")
    manifest["files"]["verify_markdown"] = str(output_dir / "pilot-day-zero-verify.md")
    manifest["verify_passed"] = verify_result["passed"]
    manifest["verify_missing_files_count"] = len(verify_result["missing_files"])
    manifest["verify_consistency_issues_count"] = len(verify_result["consistency_issues"])
    manifest["verify_recommended_next_step"] = verify_result["recommended_next_step"]
    manifest["verify_archive_exists"] = verify_result["archive_exists"]
    manifest["smoke_overall_ok"] = smoke_report["overall_ok"] if smoke_report else None
    manifest["smoke_failed_count"] = smoke_report["failed_count"] if smoke_report else None
    manifest["smoke_recommended_next_step"] = (
        smoke_report["decision"]["recommended_next_step"] if smoke_report else None
    )
    (output_dir / "pilot-day-zero-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "00-START-HERE.md").write_text(
        _build_start_here_markdown(
            generated_at=generated_at,
            frontend_url=frontend_url,
            api_url=api_url,
            streamlit_url=streamlit_url,
            pilot_gate_passed=preflight_result["pilot_gate"]["passed"],
            cutover_gate_passed=preflight_result["cutover_gate"]["passed"],
            banner_guard_allowed=banner_guard["allowed"],
            redirect_guard_allowed=cutover_guard["allowed"],
            verify_passed=verify_result["passed"],
            verify_next_step=verify_result["recommended_next_step"],
            smoke_overall_ok=smoke_report["overall_ok"] if smoke_report else None,
            smoke_next_step=smoke_report["decision"]["recommended_next_step"] if smoke_report else None,
        ),
        encoding="utf-8",
    )
    _zip_directory(output_dir, archive_path)
    return manifest


def render_console_summary(manifest: dict) -> str:
    lines = [
        "Cat Kapinda CRM v2 Day Zero Kit",
        f"Frontend URL: {manifest['frontend_url']}",
        f"API URL: {manifest['api_url']}",
        f"Streamlit URL: {manifest['streamlit_url']}",
        f"Output Dir: {manifest['output_dir']}",
        f"Pilot Gate: {'PASS' if manifest['pilot_gate_passed'] else 'FAIL'}",
        f"Cutover Gate: {'PASS' if manifest['cutover_gate_passed'] else 'FAIL'}",
        f"Banner Guard: {'PASS' if manifest['banner_guard_allowed'] else 'BLOCK'}",
        f"Redirect Guard: {'PASS' if manifest['redirect_guard_allowed'] else 'BLOCK'}",
        f"Verify: {'PASS' if manifest.get('verify_passed') else 'FAIL'}",
        f"Verify Next Step: {manifest.get('verify_recommended_next_step', 'Yok')}",
        *(
            [
                f"Smoke: {'PASS' if manifest.get('smoke_overall_ok') else 'FAIL'}",
                f"Smoke Next Step: {manifest.get('smoke_recommended_next_step', 'Yok')}",
            ]
            if manifest.get("smoke_included")
            else []
        ),
        "Files:",
    ]
    lines.extend([f"- {label}: {path}" for label, path in manifest["files"].items()])
    return "\n".join(lines) + "\n"


def compute_exit_code(manifest: dict, *, strict: bool, strict_smoke: bool) -> int:
    if not manifest["pilot_gate_passed"]:
        return 2
    if strict and not manifest.get("verify_passed", False):
        return 2
    if strict_smoke and manifest.get("smoke_included") and not manifest.get("smoke_overall_ok", False):
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the full Cat Kapinda CRM v2 day-zero kit for pilot launch."
    )
    parser.add_argument("--base-url", required=True, help="Public v2 frontend URL")
    parser.add_argument(
        "--api-url",
        default="",
        help="Public v2 backend URL. If omitted, the script will try to derive it from /api/pilot-status.",
    )
    parser.add_argument(
        "--streamlit-url",
        default="https://crmcatkapinda.com",
        help="Current Streamlit public URL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--output-dir",
        default="pilot-day-zero",
        help="Directory where all artifacts will be written",
    )
    parser.add_argument(
        "--database-url",
        default="<mevcut-postgresql-url>",
        help="Shared PostgreSQL URL placeholder or real value",
    )
    parser.add_argument(
        "--default-auth-password",
        default="<pilot-sifresi>",
        help="Initial admin/mobile_ops password placeholder or real value",
    )
    parser.add_argument(
        "--identity",
        default="ebru@catkapinda.com",
        help="Pilot login identity placeholder",
    )
    parser.add_argument(
        "--password-placeholder",
        default="<sifre>",
        help="Password placeholder for launch packets",
    )
    parser.add_argument(
        "--api-service-name",
        default="crmcatkapinda-v2-api",
        help="Render backend service name",
    )
    parser.add_argument(
        "--frontend-service-name",
        default="crmcatkapinda-v2",
        help="Render frontend service name",
    )
    parser.add_argument(
        "--streamlit-service-name",
        default="crmcatkapinda",
        help="Current Streamlit service name",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the manifest as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if the embedded day-zero verify result also fails.",
    )
    parser.add_argument(
        "--include-smoke",
        action="store_true",
        help="Also embed a live pilot_smoke report into the day-zero kit.",
    )
    parser.add_argument("--smoke-identity", default="", help="Optional login identity for embedded smoke")
    parser.add_argument("--smoke-password", default="", help="Optional login password for embedded smoke")
    parser.add_argument("--smoke-preset", choices=("pilot", "cutover"), default=None, help="Optional pilot_smoke preset")
    parser.add_argument("--smoke-legacy-url", default="", help="Optional legacy Streamlit URL for embedded smoke")
    parser.add_argument(
        "--smoke-legacy-cutover-mode",
        choices=("banner", "redirect"),
        default=None,
        help="Optional legacy cutover mode for embedded smoke",
    )
    parser.add_argument(
        "--strict-smoke",
        action="store_true",
        help="Exit non-zero if embedded smoke is enabled and fails.",
    )
    args = parser.parse_args()

    frontend_url = normalize_url(args.base_url)
    payload = fetch_pilot_status(frontend_url, args.timeout)
    api_url = normalize_url(args.api_url) if args.api_url.strip() else _derive_api_url(payload)
    if not api_url:
        raise SystemExit("API URL belirlenemedi. --api-url ver veya /api/pilot-status servis bilgisini kontrol et.")

    manifest = build_day_zero_bundle(
        frontend_url=frontend_url,
        api_url=api_url,
        streamlit_url=normalize_url(args.streamlit_url),
        output_dir=Path(args.output_dir),
        timeout=args.timeout,
        database_url=args.database_url.strip(),
        default_auth_password=args.default_auth_password.strip(),
        identity=args.identity.strip(),
        password_placeholder=args.password_placeholder.strip(),
        api_service_name=args.api_service_name.strip(),
        frontend_service_name=args.frontend_service_name.strip(),
        streamlit_service_name=args.streamlit_service_name.strip(),
        include_smoke=args.include_smoke,
        smoke_identity=args.smoke_identity.strip() or None,
        smoke_password=args.smoke_password.strip() or None,
        smoke_preset=args.smoke_preset,
        smoke_legacy_url=args.smoke_legacy_url.strip() or None,
        smoke_legacy_cutover_mode=args.smoke_legacy_cutover_mode,
    )

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_console_summary(manifest), end="")

    return compute_exit_code(manifest, strict=args.strict, strict_smoke=args.strict_smoke)


if __name__ == "__main__":
    raise SystemExit(main())
