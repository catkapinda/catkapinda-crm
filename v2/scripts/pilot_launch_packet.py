#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from render_env_bundle import build_bundle, normalize_url, render_text


def build_packet(
    *,
    frontend_url: str,
    api_url: str,
    streamlit_url: str,
    identity: str,
    password_placeholder: str,
    cutover_mode: str,
    database_url: str,
    default_auth_password: str,
    api_service_name: str,
    frontend_service_name: str,
    streamlit_service_name: str,
) -> str:
    env_bundle = build_bundle(
        frontend_url=frontend_url,
        api_url=api_url,
        database_url=database_url,
        default_auth_password=default_auth_password,
        api_service_name=api_service_name,
        frontend_service_name=frontend_service_name,
        streamlit_service_name=streamlit_service_name,
        cutover_mode=cutover_mode,
    )
    lines = [
        "# Cat Kapinda CRM v2 Pilot Acilis Paketi",
        "",
        "## Servisler",
        "",
        f"- Frontend: `{frontend_url}`",
        f"- Backend: `{api_url}`",
        f"- Streamlit: `{streamlit_url}`",
        "",
        "## Hızlı Linkler",
        "",
        f"- Pilot Login: `{frontend_url}/login`",
        f"- Pilot Dashboard: `{frontend_url}/`",
        f"- Pilot Status: `{frontend_url}/status`",
        f"- Pilot Puantaj: `{frontend_url}/attendance`",
        f"- Frontend Health: `{frontend_url}/api/health`",
        f"- Frontend Ready: `{frontend_url}/api/ready`",
        f"- Backend Health: `{api_url}/api/health`",
        f"- Backend Pilot: `{api_url}/api/health/pilot`",
        "",
        "## Env Komutları",
        "",
        "```bash",
        f"python v2/scripts/render_env_bundle.py --frontend-url {frontend_url} --api-url {api_url}",
        f"python v2/scripts/render_env_bundle.py --frontend-url {frontend_url} --api-url {api_url} --service api",
        f"python v2/scripts/render_env_bundle.py --frontend-url {frontend_url} --api-url {api_url} --service frontend",
        f"python v2/scripts/render_env_bundle.py --frontend-url {frontend_url} --api-url {api_url} --service streamlit --cutover-mode {cutover_mode}",
        "```",
        "",
        "## Hazır Env Blokları",
        "",
        "```dotenv",
        render_text(env_bundle).rstrip(),
        "```",
        "",
        "## Hızlı Kontrol Komutları",
        "",
        "```bash",
        f"curl -fsSL {frontend_url}/api/health",
        f"curl -fsSL {frontend_url}/api/ready",
        f"curl -fsSL {api_url}/api/health",
        f"curl -fsSL {api_url}/api/health/pilot",
        "```",
        "",
        "## Smoke Komutları",
        "",
        "```bash",
        f"python v2/scripts/pilot_smoke.py --base-url {frontend_url}",
        f"python v2/scripts/pilot_smoke.py --base-url {frontend_url} --preset pilot",
        (
            f"python v2/scripts/pilot_smoke.py --base-url {frontend_url} "
            f"--identity {identity} --password {password_placeholder}"
        ),
        (
            f"python v2/scripts/pilot_smoke.py --base-url {frontend_url} "
            "--json --output pilot-report.json"
        ),
        (
            f"python v2/scripts/pilot_smoke.py --base-url {frontend_url} "
            "--markdown --output pilot-report.md"
        ),
        "```",
        "",
        "## Açılış Sırası",
        "",
        "1. Render env bloklarını üret ve servislere gir.",
        "2. Frontend ve backend health endpointlerini kontrol et.",
        "3. `/status` ekranını açıp blokaj kalmadığını gör.",
        "4. `--preset pilot` ile smoke çalıştır.",
        "5. Gerekirse gerçek login smoke ile admin girişini doğrula.",
        f"6. Streamlit tarafında `{cutover_mode}` modunu hazırlayıp ofis geçişini başlat.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a shareable Markdown launch packet for the Cat Kapinda CRM v2 pilot."
    )
    parser.add_argument("--frontend-url", required=True, help="Public v2 frontend URL")
    parser.add_argument("--api-url", required=True, help="Public v2 backend URL")
    parser.add_argument(
        "--streamlit-url",
        default="https://crmcatkapinda.com",
        help="Current Streamlit public URL",
    )
    parser.add_argument(
        "--identity",
        default="ebru@catkapinda.com",
        help="Default pilot login identity placeholder",
    )
    parser.add_argument(
        "--password-placeholder",
        default="<sifre>",
        help="Password placeholder to show in the launch packet",
    )
    parser.add_argument(
        "--cutover-mode",
        choices=["banner", "redirect"],
        default="banner",
        help="Which Streamlit cutover mode the packet should prepare for",
    )
    parser.add_argument(
        "--database-url",
        default="<mevcut-postgresql-url>",
        help="Shared PostgreSQL URL placeholder or real value to embed in env blocks",
    )
    parser.add_argument(
        "--default-auth-password",
        default="<pilot-sifresi>",
        help="Initial admin/mobile_ops password placeholder or real value to embed in env blocks",
    )
    parser.add_argument(
        "--api-service-name",
        default="crmcatkapinda-v2-api",
        help="Render backend service name for env blocks",
    )
    parser.add_argument(
        "--frontend-service-name",
        default="crmcatkapinda-v2",
        help="Render frontend service name for env blocks",
    )
    parser.add_argument(
        "--streamlit-service-name",
        default="crmcatkapinda",
        help="Current Streamlit service name for env blocks",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional markdown output path",
    )
    args = parser.parse_args()

    packet = build_packet(
        frontend_url=normalize_url(args.frontend_url),
        api_url=normalize_url(args.api_url),
        streamlit_url=normalize_url(args.streamlit_url),
        identity=args.identity.strip(),
        password_placeholder=args.password_placeholder.strip(),
        cutover_mode=args.cutover_mode,
        database_url=args.database_url.strip(),
        default_auth_password=args.default_auth_password.strip(),
        api_service_name=args.api_service_name.strip(),
        frontend_service_name=args.frontend_service_name.strip(),
        streamlit_service_name=args.streamlit_service_name.strip(),
    )

    if args.output.strip():
        output_path = Path(args.output.strip())
        output_path.write_text(packet, encoding="utf-8")

    print(packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
