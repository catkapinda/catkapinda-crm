#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from pilot_deploy_guard import build_guard_result
from pilot_status_report import fetch_pilot_status
from render_env_bundle import normalize_url


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


def build_report(
    *,
    base_url: str,
    api_url: str,
    payload: dict,
    database_url: str,
    default_auth_password: str,
    guard_builder=build_guard_result,
) -> dict[str, object]:
    pilot_result = guard_builder(
        base_url=base_url,
        api_url=api_url,
        mode="pilot",
        payload=payload,
        database_url=database_url,
        default_auth_password=default_auth_password,
    )
    cutover_result = guard_builder(
        base_url=base_url,
        api_url=api_url,
        mode="cutover",
        payload=payload,
        database_url=database_url,
        default_auth_password=default_auth_password,
    )

    pilot_blocking_items = [str(item) for item in pilot_result.get("blocking_items") or []]
    cutover_blocking_items = [str(item) for item in cutover_result.get("blocking_items") or []]
    future_cutover_blocking_items = _dedupe_strings(
        [
            *[str(item) for item in pilot_result.get("future_cutover_blocking_items") or []],
            *cutover_blocking_items,
        ]
    )

    if bool(cutover_result.get("passed")):
        phase = "ready_for_cutover"
        summary = "Pilot ve cutover acilisa hazir."
        recommended_next_step = str(cutover_result.get("recommended_next_step") or "Canli domaine gecis planini uygula.")
    elif bool(pilot_result.get("passed")):
        phase = "ready_for_pilot"
        summary = "Pilot acilabilir, ancak cutover icin kalan blokajlar var."
        recommended_next_step = str(
            cutover_result.get("recommended_next_step")
            or pilot_result.get("recommended_next_step")
            or "Pilotu ac, sonra cutover blokajlarini temizle."
        )
    else:
        phase = "blocked"
        summary = "Pilot acilis bloklu."
        recommended_next_step = str(
            pilot_result.get("recommended_next_step")
            or cutover_result.get("recommended_next_step")
            or "Guard blokajlarini temizle."
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "api_url": api_url,
        "phase": phase,
        "summary": summary,
        "recommended_next_step": recommended_next_step,
        "pilot_passed": bool(pilot_result.get("passed")),
        "cutover_passed": bool(cutover_result.get("passed")),
        "pilot_blocking_items": pilot_blocking_items,
        "future_cutover_blocking_items": future_cutover_blocking_items,
        "cutover_blocking_items": cutover_blocking_items,
        "pilot_result": pilot_result,
        "cutover_result": cutover_result,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Cat Kapinda CRM v2 Go-Live Decision Report",
        "",
        f"- Generated At: `{report.get('generated_at') or '-'}`",
        f"- Base URL: `{report.get('base_url') or '-'}`",
        f"- API URL: `{report.get('api_url') or '-'}`",
        f"- Phase: `{report.get('phase') or '-'}`",
        f"- Summary: {report.get('summary') or '-'}",
        f"- Recommended Next Step: {report.get('recommended_next_step') or '-'}",
        "",
        "## Pilot Karari",
        "",
        f"- Passed: `{report.get('pilot_passed')}`",
        f"- Summary: {((report.get('pilot_result') or {}).get('summary')) or '-'}",
        "",
        "### Pilot Blocking Items",
        "",
        *([f"- {item}" for item in report.get("pilot_blocking_items") or []] or ["- Yok"]),
        "",
        "## Cutover Karari",
        "",
        f"- Passed: `{report.get('cutover_passed')}`",
        f"- Summary: {((report.get('cutover_result') or {}).get('summary')) or '-'}",
        "",
        "### Future Cutover Blocking Items",
        "",
        *([f"- {item}" for item in report.get("future_cutover_blocking_items") or []] or ["- Yok"]),
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize pilot and cutover readiness into a single go-live decision report."
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
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument("--json", action="store_true", help="Print the decision report as JSON")
    parser.add_argument("--output", default="", help="Optional output path")
    args = parser.parse_args()

    base_url = normalize_url(args.base_url)
    api_url = normalize_url(args.api_url)
    payload = fetch_pilot_status(base_url, args.timeout)
    report = build_report(
        base_url=base_url,
        api_url=api_url,
        payload=payload,
        database_url=args.database_url,
        default_auth_password=args.default_auth_password,
    )

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(report)
    if args.output.strip():
        Path(args.output.strip()).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if bool(report.get("pilot_passed")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
