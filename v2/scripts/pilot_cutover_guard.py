#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pilot_gate import build_gate_result
from pilot_status_report import fetch_pilot_status
from render_env_bundle import normalize_url


DEFAULT_TIMEOUT = 12


def build_streamlit_env_block(*, frontend_url: str, mode: str, streamlit_service_name: str) -> dict[str, dict[str, str]]:
    return {
        streamlit_service_name: {
            "CK_V2_PILOT_URL": frontend_url,
            "CK_V2_CUTOVER_MODE": mode,
        }
    }


def render_env_text(bundle: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for service_name, envs in bundle.items():
        lines.append(f"[{service_name}]")
        for key, value in envs.items():
            lines.append(f"{key}={value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_guard_result(*, base_url: str, mode: str, payload: dict, streamlit_service_name: str, force: bool) -> dict:
    gate_mode = "pilot" if mode == "banner" else "cutover"
    gate_result = build_gate_result(mode=gate_mode, payload=payload)
    allowed = gate_result["passed"] or force
    env_bundle = build_streamlit_env_block(
        frontend_url=base_url,
        mode=mode,
        streamlit_service_name=streamlit_service_name,
    )

    return {
        "mode": mode,
        "allowed": allowed,
        "forced": force,
        "streamlit_service_name": streamlit_service_name,
        "base_url": base_url,
        "gate_mode": gate_mode,
        "gate_result": gate_result,
        "env_bundle": env_bundle,
    }


def render_text(result: dict) -> str:
    gate = result["gate_result"]
    lines = [
        "Cat Kapinda CRM v2 Cutover Guard",
        f"Mode: {result['mode']}",
        f"Allowed: {result['allowed']}",
        f"Forced: {result['forced']}",
        f"Gate Mode: {result['gate_mode']}",
        f"Gate Summary: {gate['summary']}",
        f"Gate Decision: {gate['decision_title']}",
        f"Recommended Next Step: {gate['recommended_next_step']}",
        "",
        "Env Block:",
        "",
        "```dotenv",
        render_env_text(result["env_bundle"]).rstrip(),
        "```",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely emit Streamlit banner/redirect env only when the live v2 pilot gate allows it."
    )
    parser.add_argument("--base-url", required=True, help="Public v2 frontend URL")
    parser.add_argument(
        "--mode",
        choices=["banner", "redirect"],
        default="banner",
        help="Legacy Streamlit cutover mode to prepare",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--streamlit-service-name",
        default="crmcatkapinda",
        help="Current Streamlit service name",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the guard result as JSON",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Emit the env block even if the live gate is not ready",
    )
    args = parser.parse_args()

    base_url = normalize_url(args.base_url)
    payload = fetch_pilot_status(base_url, args.timeout)
    result = build_guard_result(
        base_url=base_url,
        mode=args.mode,
        payload=payload,
        streamlit_service_name=args.streamlit_service_name.strip(),
        force=args.force,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result), end="")

    return 0 if result["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
