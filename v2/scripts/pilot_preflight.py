#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

from pilot_gate import build_gate_result
from pilot_smoke import build_markdown_report as build_smoke_markdown_report, build_report as build_smoke_report, run_smoke_checks
from pilot_status_report import build_markdown_report, fetch_pilot_status
from render_env_bundle import normalize_url


DEFAULT_TIMEOUT = 12


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_summary_markdown(
    *,
    base_url: str,
    generated_at: str,
    payload: dict,
    pilot_gate: dict,
    cutover_gate: dict,
    output_dir: Path,
    smoke_report: dict | None = None,
) -> str:
    backend = payload.get("backend") or {}
    frontend = payload.get("frontend") or {}
    cutover = backend.get("cutover") or {}
    decision = backend.get("decision") or {}

    lines = [
        "# Cat Kapinda CRM v2 Pilot Preflight Summary",
        "",
        f"- Base URL: `{base_url}`",
        f"- Generated At: `{generated_at}`",
        f"- Frontend Status: `{frontend.get('status', '-')}`",
        f"- Backend Status: `{backend.get('status', '-')}`",
        f"- Phase: `{cutover.get('phase', '-')}`",
        f"- Decision: {decision.get('title') or '-'}",
        f"- Pilot Gate: `{'PASS' if pilot_gate['passed'] else 'FAIL'}`",
        f"- Cutover Gate: `{'PASS' if cutover_gate['passed'] else 'FAIL'}`",
        (
            f"- Smoke: `{'PASS' if smoke_report['overall_ok'] else 'FAIL'}`"
            if smoke_report
            else "- Smoke: `ATLANDI`"
        ),
        "",
        "## Dosyalar",
        "",
        f"- [Status Markdown]({(output_dir / 'pilot-status-live.md').name})",
        f"- [Status JSON]({(output_dir / 'pilot-status-live.json').name})",
        f"- [Pilot Gate JSON]({(output_dir / 'pilot-gate-pilot.json').name})",
        f"- [Cutover Gate JSON]({(output_dir / 'pilot-gate-cutover.json').name})",
        *(
            [
                f"- [Smoke Markdown]({(output_dir / 'pilot-smoke-live.md').name})",
                f"- [Smoke JSON]({(output_dir / 'pilot-smoke-live.json').name})",
            ]
            if smoke_report
            else []
        ),
        "",
        "## Pilot Gate",
        "",
        f"- Summary: {pilot_gate['summary']}",
        f"- Recommended Next Step: {pilot_gate['recommended_next_step']}",
        "",
        "### Blocking Items",
        "",
        *([f"- {item}" for item in pilot_gate["blocking_items"]] or ["- Yok"]),
        "",
        "## Cutover Gate",
        "",
        f"- Summary: {cutover_gate['summary']}",
        f"- Recommended Next Step: {cutover_gate['recommended_next_step']}",
        "",
        "### Blocking Items",
        "",
        *([f"- {item}" for item in cutover_gate["blocking_items"]] or ["- Yok"]),
        "",
    ]
    if smoke_report:
        decision = smoke_report["decision"]
        lines.extend(
            [
                "## Smoke",
                "",
                f"- Status: `{'PASS' if smoke_report['overall_ok'] else 'FAIL'}`",
                f"- Headline: {decision['headline']}",
                f"- Recommended Next Step: {decision['recommended_next_step']}",
                "",
                "### Failing Checks",
                "",
                *([f"- `{item}`" for item in decision["failing_checks"]] or ["- Yok"]),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_preflight_bundle(
    *,
    base_url: str,
    timeout: int,
    output_dir: Path,
    include_smoke: bool = False,
    identity: str | None = None,
    password: str | None = None,
    preset: str | None = None,
    legacy_url: str | None = None,
    legacy_cutover_mode: str | None = None,
) -> dict:
    payload = fetch_pilot_status(base_url, timeout)
    pilot_gate = build_gate_result(mode="pilot", payload=payload)
    cutover_gate = build_gate_result(mode="cutover", payload=payload)
    generated_at = datetime.now(UTC).isoformat()

    output_dir.mkdir(parents=True, exist_ok=True)
    status_markdown = build_markdown_report(base_url=base_url, payload=payload)

    smoke_report: dict | None = None
    if include_smoke:
        smoke_results = run_smoke_checks(
            base_url=base_url,
            timeout=timeout,
            identity=identity,
            password=password,
            legacy_url=legacy_url,
            legacy_cutover_mode=legacy_cutover_mode,
        )
        smoke_report = build_smoke_report(
            base_url=base_url,
            timeout=timeout,
            preset=preset,
            identity=identity,
            legacy_url=legacy_url,
            legacy_cutover_mode=legacy_cutover_mode,
            results=smoke_results,
        )
        _write_json(output_dir / "pilot-smoke-live.json", smoke_report)
        (output_dir / "pilot-smoke-live.md").write_text(
            build_smoke_markdown_report(smoke_report),
            encoding="utf-8",
        )

    summary_markdown = _build_summary_markdown(
        base_url=base_url,
        generated_at=generated_at,
        payload=payload,
        pilot_gate=pilot_gate,
        cutover_gate=cutover_gate,
        output_dir=output_dir,
        smoke_report=smoke_report,
    )

    (output_dir / "pilot-status-live.md").write_text(status_markdown, encoding="utf-8")
    _write_json(output_dir / "pilot-status-live.json", payload)
    _write_json(output_dir / "pilot-gate-pilot.json", pilot_gate)
    _write_json(output_dir / "pilot-gate-cutover.json", cutover_gate)
    (output_dir / "pilot-preflight-summary.md").write_text(summary_markdown, encoding="utf-8")

    result = {
        "generated_at": generated_at,
        "base_url": base_url,
        "output_dir": str(output_dir),
        "pilot_gate": pilot_gate,
        "cutover_gate": cutover_gate,
        "files": {
            "summary_markdown": str(output_dir / "pilot-preflight-summary.md"),
            "status_markdown": str(output_dir / "pilot-status-live.md"),
            "status_json": str(output_dir / "pilot-status-live.json"),
            "pilot_gate_json": str(output_dir / "pilot-gate-pilot.json"),
            "cutover_gate_json": str(output_dir / "pilot-gate-cutover.json"),
        },
    }
    if smoke_report:
        result["smoke_report"] = smoke_report
        result["files"]["smoke_markdown"] = str(output_dir / "pilot-smoke-live.md")
        result["files"]["smoke_json"] = str(output_dir / "pilot-smoke-live.json")
    return result


def render_console_summary(result: dict) -> str:
    lines = [
        "Cat Kapinda CRM v2 Preflight Bundle",
        f"Base URL: {result['base_url']}",
        f"Output Dir: {result['output_dir']}",
        f"Generated At: {result['generated_at']}",
        f"Pilot Gate: {'PASS' if result['pilot_gate']['passed'] else 'FAIL'} - {result['pilot_gate']['summary']}",
        f"Cutover Gate: {'PASS' if result['cutover_gate']['passed'] else 'FAIL'} - {result['cutover_gate']['summary']}",
        *(
            [
                (
                    f"Smoke: {'PASS' if result['smoke_report']['overall_ok'] else 'FAIL'} - "
                    f"{result['smoke_report']['decision']['headline']}"
                )
            ]
            if result.get("smoke_report")
            else []
        ),
        "Files:",
    ]
    lines.extend([f"- {label}: {path}" for label, path in result["files"].items()])
    return "\n".join(lines) + "\n"


def compute_exit_code(result: dict, *, strict_smoke: bool) -> int:
    if not result["pilot_gate"]["passed"]:
        return 2
    if strict_smoke and result.get("smoke_report") and not result["smoke_report"]["overall_ok"]:
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a full Cat Kapinda CRM v2 pilot preflight bundle from live /api/pilot-status."
    )
    parser.add_argument("--base-url", required=True, help="Public v2 frontend URL")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--output-dir",
        default="pilot-preflight",
        help="Directory where markdown/json outputs will be written",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print bundle summary as JSON",
    )
    parser.add_argument(
        "--include-smoke",
        action="store_true",
        help="Also run pilot_smoke and embed smoke markdown/json into the preflight bundle.",
    )
    parser.add_argument("--identity", default="", help="Optional login identity for embedded smoke")
    parser.add_argument("--password", default="", help="Optional login password for embedded smoke")
    parser.add_argument("--preset", choices=("pilot", "cutover"), default=None, help="Optional pilot_smoke preset")
    parser.add_argument("--legacy-url", default="", help="Optional legacy Streamlit URL for embedded smoke")
    parser.add_argument(
        "--legacy-cutover-mode",
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

    base_url = normalize_url(args.base_url)
    result = build_preflight_bundle(
        base_url=base_url,
        timeout=args.timeout,
        output_dir=Path(args.output_dir),
        include_smoke=args.include_smoke,
        identity=args.identity.strip() or None,
        password=args.password.strip() or None,
        preset=args.preset,
        legacy_url=args.legacy_url.strip() or None,
        legacy_cutover_mode=args.legacy_cutover_mode,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_console_summary(result), end="")

    return compute_exit_code(result, strict_smoke=args.strict_smoke)


if __name__ == "__main__":
    raise SystemExit(main())
