#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pilot_status_report import fetch_pilot_status
from render_env_bundle import normalize_url


DEFAULT_TIMEOUT = 12
PILOT_READY_PHASES = {"ready_for_pilot", "ready_for_cutover"}


def build_gate_result(*, mode: str, payload: dict) -> dict:
    backend = payload.get("backend") or {}
    frontend = payload.get("frontend") or {}
    cutover = backend.get("cutover") or {}
    decision = backend.get("decision") or {}
    required_missing_env_vars = backend.get("required_missing_env_vars") or []
    optional_missing_env_vars = backend.get("optional_missing_env_vars") or []
    blocking_items = cutover.get("blocking_items") or []
    remaining_items = cutover.get("remaining_items") or []
    phase = cutover.get("phase") or "unknown"
    ready_flag = bool(cutover.get("ready"))
    frontend_ok = frontend.get("status") == "ok"
    backend_ok = backend.get("status") == "ok"

    if mode == "pilot":
        passed = (
            frontend_ok
            and backend_ok
            and phase in PILOT_READY_PHASES
            and not required_missing_env_vars
        )
        summary = "Pilot acilabilir." if passed else "Pilot acilamaz."
        expected = "ready_for_pilot veya ready_for_cutover"
    else:
        passed = (
            frontend_ok
            and backend_ok
            and ready_flag
            and phase == "ready_for_cutover"
            and not required_missing_env_vars
        )
        summary = "Redirect cutover'a gecilebilir." if passed else "Redirect cutover'a gecilemez."
        expected = "ready_for_cutover"

    return {
        "mode": mode,
        "passed": passed,
        "summary": summary,
        "expected_phase": expected,
        "actual_phase": phase,
        "frontend_status": frontend.get("status") or "unknown",
        "backend_status": backend.get("status") or "unknown",
        "decision_title": decision.get("title") or "-",
        "decision_detail": decision.get("detail") or "-",
        "required_missing_env_vars": required_missing_env_vars,
        "optional_missing_env_vars": optional_missing_env_vars,
        "blocking_items": blocking_items,
        "remaining_items": remaining_items,
        "recommended_next_step": decision.get("detail") or "-",
    }


def render_text(result: dict) -> str:
    lines = [
        "Cat Kapinda CRM v2 Gate Result",
        f"Mode: {result['mode']}",
        f"Passed: {result['passed']}",
        f"Summary: {result['summary']}",
        f"Expected Phase: {result['expected_phase']}",
        f"Actual Phase: {result['actual_phase']}",
        f"Frontend Status: {result['frontend_status']}",
        f"Backend Status: {result['backend_status']}",
        f"Decision: {result['decision_title']}",
        f"Decision Detail: {result['decision_detail']}",
    ]
    if result["required_missing_env_vars"]:
        lines.append("Required Missing Env:")
        lines.extend([f"- {item}" for item in result["required_missing_env_vars"]])
    else:
        lines.append("Required Missing Env: none")
    if result["blocking_items"]:
        lines.append("Blocking Items:")
        lines.extend([f"- {item}" for item in result["blocking_items"]])
    else:
        lines.append("Blocking Items: none")
    if result["remaining_items"]:
        lines.append("Remaining Items:")
        lines.extend([f"- {item}" for item in result["remaining_items"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate if Cat Kapinda CRM v2 is ready for pilot or redirect cutover."
    )
    parser.add_argument("--base-url", required=True, help="Public v2 frontend URL")
    parser.add_argument(
        "--mode",
        choices=["pilot", "cutover"],
        default="pilot",
        help="Gate mode to evaluate",
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
        help="Print the gate result as JSON",
    )
    args = parser.parse_args()

    base_url = normalize_url(args.base_url)
    payload = fetch_pilot_status(base_url, args.timeout)
    result = build_gate_result(mode=args.mode, payload=payload)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result), end="")

    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
