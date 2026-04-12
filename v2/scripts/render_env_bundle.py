#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def normalize_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("URL bos olamaz.")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


def build_bundle(
    *,
    frontend_url: str,
    api_url: str,
    database_url: str,
    default_auth_password: str,
    api_service_name: str,
    frontend_service_name: str,
    streamlit_service_name: str,
    cutover_mode: str,
) -> dict[str, dict[str, str]]:
    return {
        api_service_name: {
            "CK_V2_APP_ENV": "production",
            "CK_V2_RENDER_SERVICE_NAME": api_service_name,
            "CK_V2_DATABASE_URL": database_url,
            "CK_V2_FRONTEND_BASE_URL": frontend_url,
            "CK_V2_PUBLIC_APP_URL": frontend_url,
            "CK_V2_API_PUBLIC_URL": api_url,
            "CK_V2_DEFAULT_AUTH_PASSWORD": default_auth_password,
            "AUTH_EBRU_PHONE": "<opsiyonel>",
            "AUTH_MERT_PHONE": "<opsiyonel>",
            "AUTH_MUHAMMED_PHONE": "<opsiyonel>",
            "SMS_PROVIDER": "netgsm",
            "SMS_API_URL": "https://api.netgsm.com.tr/sms/rest/v2/send",
            "SMS_NETGSM_USERNAME": "<opsiyonel>",
            "SMS_NETGSM_PASSWORD": "<opsiyonel>",
            "SMS_SENDER": "CATKAPINDA",
            "SMS_NETGSM_ENCODING": "TR",
        },
        frontend_service_name: {
            "CK_V2_FRONTEND_SERVICE_NAME": frontend_service_name,
            "NEXT_PUBLIC_V2_API_BASE_URL": "/v2-api",
            "NEXT_TELEMETRY_DISABLED": "1",
            "CK_V2_INTERNAL_API_HOSTPORT": "<render-backend-hostport>",
        },
        streamlit_service_name: {
            "CK_V2_PILOT_URL": frontend_url,
            "CK_V2_CUTOVER_MODE": cutover_mode,
        },
    }


def render_text(bundle: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for service_name, envs in bundle.items():
        lines.append(f"[{service_name}]")
        for key, value in envs.items():
            lines.append(f"{key}={value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def filter_bundle(
    bundle: dict[str, dict[str, str]],
    service: str,
    *,
    api_service_name: str,
    frontend_service_name: str,
    streamlit_service_name: str,
) -> dict[str, dict[str, str]]:
    normalized = service.strip().lower()
    if normalized == "all":
        return bundle

    service_alias_map = {
        "api": api_service_name,
        "frontend": frontend_service_name,
        "streamlit": streamlit_service_name,
        api_service_name.lower(): api_service_name,
        frontend_service_name.lower(): frontend_service_name,
        streamlit_service_name.lower(): streamlit_service_name,
    }
    resolved_service = service_alias_map.get(normalized, service)
    if resolved_service not in bundle:
        available = ", ".join(["all", "api", "frontend", "streamlit", *bundle.keys()])
        raise ValueError(f"Gecersiz service secimi: {service}. Gecerli degerler: {available}")
    return {resolved_service: bundle[resolved_service]}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Render env blocks for the Cat Kapinda CRM v2 pilot services."
    )
    parser.add_argument("--frontend-url", required=True, help="Public v2 frontend URL")
    parser.add_argument("--api-url", required=True, help="Public v2 backend URL")
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
        "--cutover-mode",
        choices=["banner", "redirect"],
        default="banner",
        help="Legacy Streamlit cutover mode to prepare",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the env bundle as JSON instead of dotenv-style blocks",
    )
    parser.add_argument(
        "--service",
        default="all",
        help="Optionally print only one service block: all, api, frontend, streamlit, or an exact service name",
    )
    args = parser.parse_args()

    frontend_url = normalize_url(args.frontend_url)
    api_url = normalize_url(args.api_url)
    bundle = build_bundle(
        frontend_url=frontend_url,
        api_url=api_url,
        database_url=args.database_url.strip(),
        default_auth_password=args.default_auth_password.strip(),
        api_service_name=args.api_service_name.strip(),
        frontend_service_name=args.frontend_service_name.strip(),
        streamlit_service_name=args.streamlit_service_name.strip(),
        cutover_mode=args.cutover_mode,
    )
    filtered_bundle = filter_bundle(
        bundle,
        args.service,
        api_service_name=args.api_service_name.strip(),
        frontend_service_name=args.frontend_service_name.strip(),
        streamlit_service_name=args.streamlit_service_name.strip(),
    )

    if args.json:
        print(json.dumps(filtered_bundle, ensure_ascii=False, indent=2))
        return 0

    print(render_text(filtered_bundle), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
