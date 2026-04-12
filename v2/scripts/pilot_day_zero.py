#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

from pilot_cutover_guard import build_guard_result, render_env_text as render_guard_env_text
from pilot_launch_packet import build_packet
from pilot_preflight import build_preflight_bundle
from pilot_status_report import fetch_pilot_status
from render_env_bundle import build_bundle, filter_bundle, normalize_url, render_text


DEFAULT_TIMEOUT = 12


def _derive_api_url(payload: dict) -> str | None:
    backend = payload.get("backend") or {}
    services = backend.get("services") or []
    for service in services:
        if service.get("service_type") == "backend" and service.get("public_url"):
            return normalize_url(service["public_url"])
    return None


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
    )

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
        "Files:",
    ]
    lines.extend([f"- {label}: {path}" for label, path in manifest["files"].items()])
    return "\n".join(lines) + "\n"


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
    )

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_console_summary(manifest), end="")

    return 0 if manifest["pilot_gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
