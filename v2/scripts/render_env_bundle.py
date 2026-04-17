#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import parse_qs, urlparse


def normalize_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("URL bos olamaz.")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


def _is_placeholder(value: str) -> bool:
    return value.startswith("<") and value.endswith(">")


def _is_local_hostname(hostname: str) -> bool:
    normalized = str(hostname or "").strip().lower()
    return normalized in {"127.0.0.1", "localhost"}


def _is_strong_password(value: str) -> bool:
    if len(value) < 12:
        return False
    has_upper = any(ch.isupper() for ch in value)
    has_lower = any(ch.islower() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    has_symbol = any(not ch.isalnum() for ch in value)
    return has_upper and has_lower and has_digit and has_symbol


def validate_public_url(url: str, *, label: str) -> str:
    value = normalize_url(url)
    parsed = urlparse(value)
    if not parsed.hostname:
        raise ValueError(f"{label} gecerli bir host icermeli.")
    if parsed.scheme != "https" and not _is_local_hostname(parsed.hostname):
        raise ValueError(f"{label} canli kullanim icin https olmali.")
    return value


def validate_database_url(database_url: str) -> str:
    value = database_url.strip()
    if not value:
        raise ValueError("Veritabani URL'i bos olamaz.")
    if _is_placeholder(value):
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("Veritabani URL'i PostgreSQL baglantisi olmali.")
    if not parsed.hostname:
        raise ValueError("Veritabani URL'i host icermeli.")
    if _is_local_hostname(parsed.hostname):
        return value
    query = parse_qs(parsed.query)
    sslmode = (query.get("sslmode") or [""])[0].strip().lower()
    if sslmode != "require":
        raise ValueError("Canli PostgreSQL baglantisi icin sslmode=require kullanilmali.")
    return value


def validate_default_auth_password(default_auth_password: str) -> str:
    value = default_auth_password.strip()
    if not value:
        raise ValueError("Varsayilan giris sifresi bos olamaz.")
    if _is_placeholder(value):
        return value
    if not _is_strong_password(value):
        raise ValueError("Varsayilan giris sifresi en az 12 karakterli, buyuk-kucuk harf, rakam ve sembol icermeli.")
    return value


def build_validation_report(
    *,
    frontend_url: str,
    api_url: str,
    database_url: str,
    default_auth_password: str,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    normalized_frontend_url = ""
    normalized_api_url = ""

    for name, label, raw_value, validator in (
        ("frontend_url", "Frontend URL", frontend_url, lambda value: validate_public_url(value, label="Frontend URL")),
        ("api_url", "API URL", api_url, lambda value: validate_public_url(value, label="API URL")),
        ("database_url", "Veritabani URL", database_url, validate_database_url),
        ("default_auth_password", "Varsayilan giris sifresi", default_auth_password, validate_default_auth_password),
    ):
        value = str(raw_value or "").strip()
        if not value:
            checks.append(
                {
                    "name": name,
                    "label": label,
                    "ok": False,
                    "detail": f"{label} bos birakilamaz.",
                }
            )
            continue
        if _is_placeholder(value):
            checks.append(
                {
                    "name": name,
                    "label": label,
                    "ok": False,
                    "detail": f"{label} icin gercek bir deger girilmeli.",
                }
            )
            continue
        try:
            normalized_value = validator(value)
            checks.append(
                {
                    "name": name,
                    "label": label,
                    "ok": True,
                    "detail": "Hazir",
                }
            )
            if name == "frontend_url":
                normalized_frontend_url = str(normalized_value)
            elif name == "api_url":
                normalized_api_url = str(normalized_value)
        except ValueError as exc:
            checks.append(
                {
                    "name": name,
                    "label": label,
                    "ok": False,
                    "detail": str(exc),
                }
            )

    passed = all(bool(check["ok"]) for check in checks)
    blocking_items = [str(check["detail"]) for check in checks if not bool(check["ok"])]
    return {
        "passed": passed,
        "normalized_frontend_url": normalized_frontend_url,
        "normalized_api_url": normalized_api_url,
        "checks": checks,
        "blocking_items": blocking_items,
        "summary": "Render env degerleri canliya hazir." if passed else "Render env degerlerinde canliya cikisi durduran maddeler var.",
    }


def render_validation_text(report: dict[str, object]) -> str:
    lines = [
        "Cat Kapinda CRM v2 Render Env Validation",
        f"Passed: {report['passed']}",
        f"Summary: {report['summary']}",
    ]
    frontend_url = str(report.get("normalized_frontend_url") or "").strip()
    api_url = str(report.get("normalized_api_url") or "").strip()
    if frontend_url:
        lines.append(f"Frontend URL: {frontend_url}")
    if api_url:
        lines.append(f"API URL: {api_url}")
    lines.append("Checks:")
    for entry in report.get("checks") or []:
        item = entry if isinstance(entry, dict) else {}
        status = "OK" if item.get("ok") else "BLOCKED"
        lines.append(f"- [{status}] {item.get('label')}: {item.get('detail')}")
    return "\n".join(lines) + "\n"


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
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the supplied production values and print a readiness report",
    )
    args = parser.parse_args()

    try:
        if args.validate_only:
            report = build_validation_report(
                frontend_url=args.frontend_url,
                api_url=args.api_url,
                database_url=args.database_url,
                default_auth_password=args.default_auth_password,
            )
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(render_validation_text(report), end="")
            return 0 if bool(report["passed"]) else 2

        frontend_url = validate_public_url(args.frontend_url, label="Frontend URL")
        api_url = validate_public_url(args.api_url, label="API URL")
        database_url = validate_database_url(args.database_url.strip())
        default_auth_password = validate_default_auth_password(args.default_auth_password.strip())
        bundle = build_bundle(
            frontend_url=frontend_url,
            api_url=api_url,
            database_url=database_url,
            default_auth_password=default_auth_password,
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
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
