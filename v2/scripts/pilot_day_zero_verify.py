#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

OPTIONAL_SMOKE_FILES = (
    "pilot-smoke-live.md",
    "pilot-smoke-live.json",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _check_smoke_consistency(*, output_dir: Path, manifest: dict) -> tuple[bool, list[str], dict | None]:
    issues: list[str] = []
    smoke_payload: dict | None = None
    smoke_included = bool(manifest.get("smoke_included"))

    if not smoke_included:
        return (True, issues, None)

    smoke_json_path = output_dir / "pilot-smoke-live.json"
    smoke_markdown_path = output_dir / "pilot-smoke-live.md"

    for path in (smoke_json_path, smoke_markdown_path):
        if not path.exists():
            issues.append(f"Smoke acikken {path.name} bulunamadi")

    if issues:
        return (False, issues, None)

    smoke_payload = _read_json(smoke_json_path)

    expected_overall_ok = manifest.get("smoke_overall_ok")
    if expected_overall_ok is not None and bool(smoke_payload.get("overall_ok")) != bool(expected_overall_ok):
        issues.append(
            "Manifest smoke_overall_ok degeri ile pilot-smoke-live.json uyusmuyor"
        )

    expected_failed_count = manifest.get("smoke_failed_count")
    if expected_failed_count is not None and int(smoke_payload.get("failed_count") or 0) != int(expected_failed_count):
        issues.append(
            "Manifest smoke_failed_count degeri ile pilot-smoke-live.json uyusmuyor"
        )

    expected_next_step = manifest.get("smoke_recommended_next_step")
    actual_next_step = ((smoke_payload.get("decision") or {}).get("recommended_next_step") or "").strip()
    if expected_next_step and actual_next_step != expected_next_step:
        issues.append(
            "Manifest smoke_recommended_next_step degeri ile pilot-smoke-live.json uyusmuyor"
        )

    return (not issues, issues, smoke_payload)


def _check_archive_members(*, archive_members: list[str], manifest: dict) -> list[str]:
    issues: list[str] = []
    expected_members = {"00-START-HERE.md", "pilot-day-zero-manifest.json"}

    for raw_path in (manifest.get("files") or {}).values():
        expected_members.add(Path(str(raw_path)).name)

    if manifest.get("smoke_included"):
        expected_members.update(OPTIONAL_SMOKE_FILES)

    for member in sorted(expected_members):
        if member not in archive_members:
            issues.append(f"Zip arsivinde {member} eksik")

    return issues


def _check_integrity_manifest(
    *,
    output_dir: Path,
    manifest: dict,
    archive_checksums: dict[str, str],
) -> tuple[bool, str | None, int, list[str]]:
    issues: list[str] = []
    integrity = manifest.get("integrity") or {}
    if not integrity:
        return (False, None, 0, issues)

    algorithm = integrity.get("algorithm")
    if algorithm != "sha256":
        issues.append(f"Desteklenmeyen integrity algoritmasi: {algorithm}")

    recorded = integrity.get("files") or {}
    if not isinstance(recorded, dict):
        return (True, str(algorithm), 0, issues + ["Integrity files alani gecersiz"])

    expected_names = {"00-START-HERE.md"}
    for raw_path in (manifest.get("files") or {}).values():
        expected_names.add(Path(str(raw_path)).name)

    for name in sorted(expected_names):
        expected_checksum = recorded.get(name)
        if not expected_checksum:
            issues.append(f"Integrity kaydi eksik: {name}")
            continue

        path = output_dir / name
        if path.exists():
            actual_checksum = _sha256_path(path)
            if actual_checksum != expected_checksum:
                issues.append(f"Integrity checksum uyusmuyor: {name}")

        archive_checksum = archive_checksums.get(name)
        if archive_checksum is None:
            issues.append(f"Integrity icin zip kaydi eksik: {name}")
        elif archive_checksum != expected_checksum:
            issues.append(f"Zip icindeki checksum uyusmuyor: {name}")

    return (True, str(algorithm), len(recorded), issues)


def verify_day_zero_bundle(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    manifest_path = output_dir / "pilot-day-zero-manifest.json"

    missing_files: list[str] = []
    consistency_issues: list[str] = []
    archive_members: list[str] = []
    archive_checksums: dict[str, str] = {}

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
                archive_checksums = {
                    member: _sha256_bytes(archive.read(member))
                    for member in archive_members
                    if not member.endswith("/")
                }
            consistency_issues.extend(_check_archive_members(archive_members=archive_members, manifest=manifest))

    smoke_ok, smoke_issues, smoke_payload = _check_smoke_consistency(
        output_dir=output_dir,
        manifest=manifest,
    )
    if not smoke_ok:
        consistency_issues.extend(smoke_issues)

    integrity_checked, integrity_algorithm, integrity_entries_count, integrity_issues = _check_integrity_manifest(
        output_dir=output_dir,
        manifest=manifest,
        archive_checksums=archive_checksums,
    )
    consistency_issues.extend(integrity_issues)

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
        "smoke_included": bool(manifest.get("smoke_included")),
        "smoke_checked": bool(manifest.get("smoke_included")),
        "smoke_overall_ok": (smoke_payload or {}).get("overall_ok") if smoke_payload else None,
        "smoke_failed_count": (smoke_payload or {}).get("failed_count") if smoke_payload else None,
        "integrity_checked": integrity_checked,
        "integrity_ok": True if integrity_checked and not integrity_issues else (False if integrity_checked else None),
        "integrity_algorithm": integrity_algorithm,
        "integrity_entries_count": integrity_entries_count,
        "recommended_next_step": recommended_next_step,
    }


def render_console_summary(result: dict) -> str:
    smoke_checked = bool(result.get("smoke_checked"))
    smoke_overall_ok = result.get("smoke_overall_ok")
    integrity_checked = bool(result.get("integrity_checked"))
    integrity_ok = result.get("integrity_ok")
    lines = [
        "Cat Kapinda CRM v2 Day Zero Verify",
        f"Output Dir: {result['output_dir']}",
        f"Status: {'PASS' if result['passed'] else 'FAIL'}",
        f"Archive: {'OK' if result['archive_exists'] else 'MISSING'}",
        f"Archive Members: {result['archive_members_count']}",
        (
            f"Integrity: {'PASS' if integrity_ok else 'FAIL'} ({result.get('integrity_algorithm')}, {result.get('integrity_entries_count')} kayit)"
            if integrity_checked
            else "Integrity: SKIPPED"
        ),
        (
            f"Smoke: {'PASS' if smoke_overall_ok else 'FAIL'}"
            if smoke_checked and smoke_overall_ok is not None
            else "Smoke: SKIPPED"
        ),
        f"Recommended Next Step: {result['recommended_next_step']}",
        "Missing Files:",
    ]
    lines.extend([f"- {item}" for item in result["missing_files"]] or ["- Yok"])
    lines.append("Consistency Issues:")
    lines.extend([f"- {item}" for item in result["consistency_issues"]] or ["- Yok"])
    return "\n".join(lines) + "\n"


def render_markdown_report(result: dict) -> str:
    smoke_checked = bool(result.get("smoke_checked"))
    smoke_overall_ok = result.get("smoke_overall_ok")
    integrity_checked = bool(result.get("integrity_checked"))
    integrity_ok = result.get("integrity_ok")
    lines = [
        "# Cat Kapinda CRM v2 Day Zero Verify",
        "",
        f"- Output Dir: `{result['output_dir']}`",
        f"- Status: `{'PASS' if result['passed'] else 'FAIL'}`",
        f"- Archive: `{'OK' if result['archive_exists'] else 'MISSING'}`",
        f"- Archive Members: `{result['archive_members_count']}`",
        (
            f"- Integrity: `{'PASS' if integrity_ok else 'FAIL'}` (`{result.get('integrity_algorithm')}`, `{result.get('integrity_entries_count')}` kayit)"
            if integrity_checked
            else "- Integrity: `SKIPPED`"
        ),
        (
            f"- Smoke: `{'PASS' if smoke_overall_ok else 'FAIL'}`"
            if smoke_checked and smoke_overall_ok is not None
            else "- Smoke: `SKIPPED`"
        ),
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
