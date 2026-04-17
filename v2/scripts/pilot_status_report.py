#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import urllib.error
import urllib.request

from render_env_bundle import normalize_url


DEFAULT_TIMEOUT = 12


def fetch_pilot_status(base_url: str, timeout: int) -> dict:
    request = urllib.request.Request(
        f"{base_url}/api/pilot-status",
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Pilot status HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Pilot status baglantisi kurulamadi: {exc.reason}") from exc
    return payload


def _format_list(items: list[str], *, empty_text: str = "Yok") -> list[str]:
    if not items:
        return [f"- {empty_text}"]
    return [f"- {item}" for item in items]


def _build_release_alignment(frontend: dict, backend: dict | None) -> tuple[str, str]:
    frontend_release = frontend.get("releaseLabel") or "-"
    backend_release = (backend or {}).get("release_label") or "-"
    if frontend_release != "-" and backend_release != "-":
        if frontend_release == backend_release:
            return "Uyumlu", frontend_release
        return "Uyumsuz", f"frontend={frontend_release} | backend={backend_release}"
    return "Eksik Bilgi", f"frontend={frontend_release} | backend={backend_release}"


def build_markdown_report(*, base_url: str, payload: dict) -> str:
    generated_at = datetime.now(UTC).isoformat()
    frontend = payload.get("frontend") or {}
    backend = payload.get("backend") or {}
    auth = backend.get("auth") or {}
    cutover = backend.get("cutover") or {}
    go_live = backend.get("go_live") or {}
    decision = backend.get("decision") or {}
    pilot_links = backend.get("pilot_links") or []
    command_pack = backend.get("command_pack") or []
    smoke_commands = backend.get("smoke_commands") or []
    helper_commands = backend.get("helper_commands") or []
    pilot_accounts = backend.get("pilot_accounts") or []
    required_missing_env_vars = backend.get("required_missing_env_vars") or []
    optional_missing_env_vars = backend.get("optional_missing_env_vars") or []
    next_actions = backend.get("next_actions") or []
    services = backend.get("services") or []
    modules = backend.get("modules") or []
    active_modules = sum(1 for entry in modules if entry.get("status") == "active")
    release_alignment, release_detail = _build_release_alignment(frontend, backend)

    lines = [
        "# Cat Kapinda CRM v2 Pilot Status Report",
        "",
        f"- Base URL: `{base_url}`",
        f"- Generated At: `{generated_at}`",
        f"- Frontend Status: `{frontend.get('status', '-')}`",
        f"- Backend Status: `{backend.get('status', '-') if backend else '-'}`",
        f"- Frontend Release: `{frontend.get('releaseLabel') or '-'}`",
        f"- Backend Release: `{backend.get('release_label') or '-'}`",
        f"- Release Alignment: `{release_alignment}` ({release_detail})",
        "",
        "## Bugunun Karari",
        "",
        f"- Title: {decision.get('title') or '-'}",
        f"- Tone: `{decision.get('tone') or '-'}`",
        f"- Detail: {decision.get('detail') or '-'}",
        f"- Primary Action: `{decision.get('primary_label') or '-'}` -> `{decision.get('primary_href') or '-'}`",
        "",
        "## Cutover Ozet",
        "",
        f"- Phase: `{cutover.get('phase') or '-'}`",
        f"- Ready: `{cutover.get('ready')}`",
        f"- Summary: {cutover.get('summary') or '-'}",
        f"- Modules Ready: `{cutover.get('modules_ready_count', 0)}/{cutover.get('modules_total_count', 0)}`",
        f"- Active Modules: `{active_modules}/{len(modules)}`",
        "",
        "### Blocking Items",
        "",
        *_format_list(cutover.get("blocking_items") or []),
        "",
        "### Remaining Items",
        "",
        *_format_list(cutover.get("remaining_items") or []),
        "",
        "## Go-Live Karari",
        "",
        f"- Phase: `{go_live.get('phase') or '-'}`",
        f"- Label: {go_live.get('phase_label') or '-'}",
        f"- Pilot Ready: `{go_live.get('pilot_ready')}`",
        f"- Cutover Ready: `{go_live.get('cutover_ready')}`",
        f"- Summary: {go_live.get('summary') or '-'}",
        f"- Recommended Next Step: {go_live.get('recommended_next_step') or '-'}",
        "",
        "### Future Cutover Blocking Items",
        "",
        *_format_list(go_live.get("future_cutover_blocking_items") or []),
        "",
        "### Missing Env",
        "",
        "- Required:",
        *_format_list(required_missing_env_vars, empty_text="Yok"),
        "",
        "- Optional:",
        *_format_list(optional_missing_env_vars, empty_text="Yok"),
        "",
        "### Next Actions",
        "",
        *_format_list(next_actions),
        "",
        "## Auth Ozet",
        "",
        f"- Email Login: `{auth.get('email_login')}`",
        f"- Phone Login: `{auth.get('phone_login')}`",
        f"- SMS Login: `{auth.get('sms_login')}`",
        f"- Admin Users: `{auth.get('admin_user_count', 0)}`",
        f"- Mobile Ops Users: `{auth.get('mobile_ops_user_count', 0)}`",
        f"- Default Password Configured: `{auth.get('default_password_configured')}`",
        "",
        "## Pilot Hesaplar",
        "",
        "| Email | Ad Soyad | Rol | Telefon Hazir |",
        "| --- | --- | --- | --- |",
    ]

    if pilot_accounts:
        for account in pilot_accounts:
            lines.append(
                f"| `{account.get('email') or '-'}` | {account.get('full_name') or '-'} | "
                f"{account.get('role') or '-'} | `{account.get('has_phone')}` |"
            )
    else:
        lines.append("| `-` | - | - | `False` |")

    lines.extend(["", "## Pilot Linkleri", ""])
    lines.extend([f"- {entry.get('label')}: `{entry.get('href')}`" for entry in pilot_links] or ["- Yok"])
    lines.extend(["", "## Servisler", ""])

    if services:
        for service in services:
            lines.extend(
                [
                    f"### {service.get('name')}",
                    "",
                    f"- Type: `{service.get('service_type')}`",
                    f"- Public URL: `{service.get('public_url')}`",
                    f"- Health: `{service.get('health_path')}`",
                    "",
                ]
            )
    else:
        lines.extend(["- Servis bilgisi yok.", ""])

    lines.extend(["## Acilis Komut Paketi", ""])
    if command_pack:
        for entry in command_pack:
            lines.extend(
                [
                    f"### {entry.get('title')}",
                    "",
                    f"- Detail: {entry.get('detail') or '-'}",
                    "",
                    "```bash",
                    entry.get("command") or "",
                    "```",
                    "",
                ]
            )
    else:
        lines.extend(["- Komut paketi yok.", ""])

    lines.extend(["## Smoke Komutlari", ""])
    if smoke_commands:
        for entry in smoke_commands:
            lines.extend(
                [
                    f"- {entry.get('label')}",
                    "",
                    "```bash",
                    entry.get("command") or "",
                    "```",
                    "",
                ]
            )
    else:
        lines.extend(["- Smoke komutu yok.", ""])

    packet_commands = [entry for entry in helper_commands if entry.get("category") == "packet"]
    env_commands = [entry for entry in helper_commands if entry.get("category") == "env"]
    quick_commands = [entry for entry in helper_commands if entry.get("category") == "quick-check"]

    for title, entries in [
        ("Acilis Paketi Komutlari", packet_commands),
        ("Env Helper Komutlari", env_commands),
        ("Hizli Kontrol Komutlari", quick_commands),
    ]:
        lines.extend([f"## {title}", ""])
        if entries:
            for entry in entries:
                lines.extend(
                    [
                        f"- {entry.get('label')}",
                        "",
                        "```bash",
                        entry.get("command") or "",
                        "```",
                        "",
                    ]
                )
        else:
            lines.extend(["- Yok.", ""])

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch /api/pilot-status and export a shareable Cat Kapinda CRM v2 pilot report."
    )
    parser.add_argument("--base-url", required=True, help="Public v2 frontend URL")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write the raw /api/pilot-status payload as JSON instead of Markdown",
    )
    parser.add_argument("--output", default="", help="Optional output path for the generated report")
    args = parser.parse_args()

    base_url = normalize_url(args.base_url)
    payload = fetch_pilot_status(base_url, args.timeout)

    if args.json:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        rendered = build_markdown_report(base_url=base_url, payload=payload)

    if args.output.strip():
        output_path = Path(args.output.strip())
        output_path.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
