#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile


DEFAULT_OUTPUT_DIR = "pilot-day-zero"

REQUIRED_FILES = (
    "00-START-HERE.md",
    "render-env-bundle.env",
    "render-env-bundle.json",
    "streamlit-banner.env",
    "streamlit-redirect.env",
    "streamlit-banner-guard.json",
    "streamlit-redirect-guard.json",
    "streamlit-banner-guarded.env",
    "streamlit-redirect-guarded.env",
    "pilot-launch.md",
    "pilot-cutover.md",
    "pilot-status-live.md",
    "pilot-status-live.json",
    "pilot-gate-pilot.json",
    "pilot-gate-cutover.json",
    "pilot-preflight-summary.md",
    "pilot-day-zero-manifest.json",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_guard_file(*, mode: str, guard_json_path: Path, guarded_env_path: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    guard_payload = _read_json(guard_json_path)
    content = guarded_env_path.read_text(encoding="utf-8")
    allowed = bool(guard_payload.get("allowed"))

    if allowed:
        expected_token = f"CK_V2_CUTOVER_MODE={mode}"
        if expected_token not in content:
            issues.append(f"{guarded_env_path.name} icinde {expected_token} bulunamadi")
        if "# guard blocked" in content:
            issues.append(f"{guarded_env_path.name} izin varken blok mesajı iceriyor")
    else:
        if "# guard blocked" not in content:
            issues.append(f"{guarded_env_path.name} guard blokluyken blok mesaji icermiyor")

    return (not issues, issues)


def verify_day_zero_bundle(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    manifest_path = output_dir / "pilot-day-zero-manifest.json"

    missing_files: list[str] = []
    consistency_issues: list[str] = []
    archive_members: list[str] = []

    if not output_dir.exists():
        missing_files.append(str(output_dir))
        return {
            "passed": False,
            "output_dir": str(output_dir),
            "missing_files": missing_files,
            "consistency_issues": ["Day-zero klasoru bulunamadi"],
            "archive_path": None,
            "archive_exists": False,
            "archive_members_count": 0,
            "recommended_next_step": "Önce pilot_day_zero.py ile kit olustur.",
        }

    for filename in REQUIRED_FILES:
        if not (output_dir / filename).exists():
            missing_files.append(str(output_dir / filename))

    if not manifest_path.exists():
        return {
            "passed": False,
            "output_dir": str(output_dir),
            "missing_files": missing_files + [str(manifest_path)],
            "consistency_issues": ["Manifest bulunamadigi icin ayrintili dogrulama yapilamadi"],
            "archive_path": None,
            "archive_exists": False,
            "archive_members_count": 0,
            "recommended_next_step": "pilot_day_zero.py komutunu yeniden calistir ve manifest olustugunu dogrula.",
        }

    manifest = _read_json(manifest_path)
    manifest_files = manifest.get("files") or {}

    for label, raw_path in manifest_files.items():
        path = Path(str(raw_path))
        if not path.exists():
            missing_files.append(str(path))
            consistency_issues.append(f"Manifest girdisi eksik dosyaya isaret ediyor: {label}")

    expected_output_dir = str(output_dir)
    if manifest.get("output_dir") != expected_output_dir:
        consistency_issues.append(
            f"Manifest output_dir uyusmuyor: {manifest.get('output_dir')} != {expected_output_dir}"
        )

    banner_ok, banner_issues = _check_guard_file(
        mode="banner",
        guard_json_path=output_dir / "streamlit-banner-guard.json",
        guarded_env_path=output_dir / "streamlit-banner-guarded.env",
    )
    redirect_ok, redirect_issues = _check_guard_file(
        mode="redirect",
        guard_json_path=output_dir / "streamlit-redirect-guard.json",
        guarded_env_path=output_dir / "streamlit-redirect-guarded.env",
    )
    if not banner_ok:
        consistency_issues.extend(banner_issues)
    if not redirect_ok:
        consistency_issues.extend(redirect_issues)

    archive_path = manifest.get("archive_path")
    archive_exists = False
    if archive_path:
        archive_file = Path(str(archive_path))
        archive_exists = archive_file.exists()
        if not archive_exists:
            missing_files.append(str(archive_file))
            consistency_issues.append("Manifest archive_path var ama zip arsivi bulunamadi")
        else:
            with zipfile.ZipFile(archive_file) as archive:
                archive_members = archive.namelist()
            for expected_member in ("00-START-HERE.md", "pilot-day-zero-manifest.json"):
                if expected_member not in archive_members:
                    consistency_issues.append(f"Zip arsivinde {expected_member} eksik")

    passed = not missing_files and not consistency_issues
    recommended_next_step = (
        "Day-zero kiti kullanima hazir."
        if passed
        else "pilot_day_zero.py komutunu yeniden calistirip eksik dosyalari ve guard ciktilarini kontrol et."
    )

    return {
        "passed": passed,
        "output_dir": str(output_dir),
        "missing_files": missing_files,
        "consistency_issues": consistency_issues,
        "archive_path": archive_path,
        "archive_exists": archive_exists,
        "archive_members_count": len(archive_members),
        "recommended_next_step": recommended_next_step,
    }


def render_console_summary(result: dict) -> str:
    lines = [
        "Cat Kapinda CRM v2 Day Zero Verify",
        f"Output Dir: {result['output_dir']}",
        f"Status: {'PASS' if result['passed'] else 'FAIL'}",
        f"Archive: {'OK' if result['archive_exists'] else 'MISSING'}",
        f"Archive Members: {result['archive_members_count']}",
        f"Recommended Next Step: {result['recommended_next_step']}",
        "Missing Files:",
    ]
    lines.extend([f"- {item}" for item in result["missing_files"]] or ["- Yok"])
    lines.append("Consistency Issues:")
    lines.extend([f"- {item}" for item in result["consistency_issues"]] or ["- Yok"])
    return "\n".join(lines) + "\n"


def render_markdown_report(result: dict) -> str:
    lines = [
        "# Cat Kapinda CRM v2 Day Zero Verify",
        "",
        f"- Output Dir: `{result['output_dir']}`",
        f"- Status: `{'PASS' if result['passed'] else 'FAIL'}`",
        f"- Archive: `{'OK' if result['archive_exists'] else 'MISSING'}`",
        f"- Archive Members: `{result['archive_members_count']}`",
        f"- Recommended Next Step: {result['recommended_next_step']}",
        "",
        "## Missing Files",
        "",
        *([f"- `{item}`" for item in result["missing_files"]] or ["- Yok"]),
        "",
        "## Consistency Issues",
        "",
        *([f"- {item}" for item in result["consistency_issues"]] or ["- Yok"]),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that a Cat Kapinda CRM v2 day-zero bundle is complete and internally consistent."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory created by pilot_day_zero.py (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the verification result as JSON",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print the verification result as Markdown",
    )
    args = parser.parse_args()

    result = verify_day_zero_bundle(Path(args.output_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(render_markdown_report(result))
    else:
        print(render_console_summary(result), end="")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
