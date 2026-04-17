#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from database_preflight import build_database_preflight_report
from pilot_gate import build_gate_result
from pilot_status_report import fetch_pilot_status
from render_env_bundle import build_validation_report, normalize_url


DEFAULT_TIMEOUT = 12


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw_item in items:
        item = str(raw_item or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def build_guard_result(
    *,
    base_url: str,
    api_url: str,
    mode: str,
    payload: dict,
    database_url: str,
    default_auth_password: str,
    database_preflight_builder=build_database_preflight_report,
) -> dict:
    gate_result = build_gate_result(mode=mode, payload=payload)
    env_validation = build_validation_report(
        frontend_url=base_url,
        api_url=api_url,
        database_url=database_url,
        default_auth_password=default_auth_password,
    )
    database_preflight_result: dict[str, object] | None = None
    database_preflight_passed = False
    database_preflight_mode_summary = "Atlandi"
    future_cutover_blocking_items: list[str] = []
    if bool(env_validation.get("passed")):
        try:
            database_preflight_result = database_preflight_builder(database_url=database_url)
        except Exception as exc:
            database_preflight_result = {
                "passed": False,
                "cutover_ready": False,
                "summary": "Veritabani preflight basarisiz.",
                "blocking_items": [str(exc)],
                "cutover_blocking_items": [str(exc)],
                "recommended_next_step": "Veritabani baglantisini ve tablo omurgasini yeniden kontrol et.",
                "cutover_recommended_next_step": "Canli domaine gecmeden once veritabani baglantisini ve veri kapsamini yeniden kontrol et.",
            }
        database_preflight_passed = bool(
            database_preflight_result.get("cutover_ready")
            if mode == "cutover"
            else database_preflight_result.get("passed")
        )
        database_preflight_mode_summary = str(
            database_preflight_result.get("summary")
            if mode == "pilot"
            else database_preflight_result.get("cutover_recommended_next_step")
            or database_preflight_result.get("summary")
            or "Veritabani preflight sonucu okunamadi."
        )
        if mode == "pilot":
            future_cutover_blocking_items = _dedupe_strings(
                [str(item) for item in database_preflight_result.get("cutover_blocking_items") or []]
            )

    database_preflight_blocking_items = (
        _dedupe_strings(
            [
                *[str(item) for item in (database_preflight_result or {}).get("blocking_items") or []],
                *(
                    [str(item) for item in (database_preflight_result or {}).get("cutover_blocking_items") or []]
                    if mode == "cutover"
                    else []
                ),
            ]
        )
        if database_preflight_result is not None
        else []
    )

    blocking_items = _dedupe_strings(
        [
            *[str(item) for item in gate_result.get("blocking_items") or []],
            *[str(item) for item in env_validation.get("blocking_items") or []],
            *database_preflight_blocking_items,
        ]
    )
    recommended_steps = _dedupe_strings(
        [
            str(gate_result.get("recommended_next_step") or "").strip(),
            "Render env validation blokajlarini kapat." if not bool(env_validation.get("passed")) else "",
            (
                str(
                    (
                        (database_preflight_result or {}).get("cutover_recommended_next_step")
                        if mode == "cutover"
                        else (database_preflight_result or {}).get("recommended_next_step")
                    )
                    or ""
                ).strip()
                if database_preflight_result and not database_preflight_passed
                else ""
            ),
            (
                f"Pilot acilsa da cutover oncesi: {str((database_preflight_result or {}).get('cutover_recommended_next_step') or '').strip()}"
                if mode == "pilot" and future_cutover_blocking_items
                else ""
            ),
        ]
    )
    passed = bool(gate_result.get("passed")) and bool(env_validation.get("passed")) and (
        database_preflight_passed if database_preflight_result is not None else False
    )

    if mode == "pilot":
        summary = (
            "Pilot deploy acilabilir, ancak cutover icin kalan blokajlar var."
            if passed and future_cutover_blocking_items
            else ("Pilot deploy acilabilir." if passed else "Pilot deploy bloklu.")
        )
    else:
        summary = "Cutover deploy acilabilir." if passed else "Cutover deploy bloklu."

    return {
        "mode": mode,
        "passed": passed,
        "summary": summary,
        "base_url": base_url,
        "api_url": api_url,
        "gate_passed": bool(gate_result.get("passed")),
        "env_passed": bool(env_validation.get("passed")),
        "database_preflight_passed": database_preflight_passed,
        "database_preflight_mode_summary": database_preflight_mode_summary,
        "gate_result": gate_result,
        "env_validation": env_validation,
        "database_preflight": database_preflight_result,
        "future_cutover_blocking_items": future_cutover_blocking_items,
        "blocking_items": blocking_items,
        "recommended_next_step": " / ".join(recommended_steps) if recommended_steps else "-",
    }


def render_text(result: dict) -> str:
    gate_result = result["gate_result"]
    env_validation = result["env_validation"]
    lines = [
        "Cat Kapinda CRM v2 Deploy Guard",
        f"Mode: {result['mode']}",
        f"Passed: {result['passed']}",
        f"Summary: {result['summary']}",
        f"Base URL: {result['base_url']}",
        f"API URL: {result['api_url']}",
        f"Gate Passed: {result['gate_passed']}",
        f"Gate Summary: {gate_result['summary']}",
        f"Env Passed: {result['env_passed']}",
        f"Env Summary: {env_validation['summary']}",
        f"Database Preflight Passed: {result['database_preflight_passed']}",
        f"Database Preflight Summary: {result['database_preflight_mode_summary']}",
        f"Recommended Next Step: {result['recommended_next_step']}",
    ]
    if result["blocking_items"]:
        lines.append("Blocking Items:")
        lines.extend([f"- {item}" for item in result["blocking_items"]])
    else:
        lines.append("Blocking Items: none")
    if result.get("future_cutover_blocking_items"):
        lines.append("Future Cutover Blocking Items:")
        lines.extend([f"- {item}" for item in result["future_cutover_blocking_items"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Combine live pilot gate and Render env validation into one deploy readiness decision."
    )
    parser.add_argument("--base-url", required=True, help="Public v2 frontend URL")
    parser.add_argument("--api-url", required=True, help="Public v2 backend URL")
    parser.add_argument(
        "--database-url",
        default="<mevcut-postgresql-url-sslmode-require>",
        help="Shared PostgreSQL URL placeholder or real value",
    )
    parser.add_argument(
        "--default-auth-password",
        default="<guclu-varsayilan-sifre>",
        help="Initial admin/mobile_ops password placeholder or real value",
    )
    parser.add_argument(
        "--mode",
        choices=["pilot", "cutover"],
        default="pilot",
        help="Deploy mode to evaluate",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the deploy guard result as JSON",
    )
    args = parser.parse_args()

    base_url = normalize_url(args.base_url)
    api_url = normalize_url(args.api_url)
    payload = fetch_pilot_status(base_url, args.timeout)
    result = build_guard_result(
        base_url=base_url,
        api_url=api_url,
        mode=args.mode,
        payload=payload,
        database_url=args.database_url,
        default_auth_password=args.default_auth_password,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result), end="")

    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
