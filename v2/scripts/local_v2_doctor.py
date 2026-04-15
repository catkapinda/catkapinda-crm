from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).absolute().parent
V2_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = V2_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.local_doctor import (  # noqa: E402
    build_local_doctor_report,
    discover_current_app_seed_values,
    write_backend_env_file,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local v2 icin env ve backend readiness doktoru.",
    )
    parser.add_argument("--json", action="store_true", help="Raporu JSON olarak yazdir.")
    parser.add_argument(
        "--write-backend-env",
        action="store_true",
        help="Shell env icindeki degerlerle backend/.env dosyasini olustur.",
    )
    parser.add_argument(
        "--sync-from-current-app",
        action="store_true",
        help="Shell env eksikse mevcut app kaynaklarindaki gercek degerleri fallback olarak kullan.",
    )
    parser.add_argument(
        "--overwrite-backend-env",
        action="store_true",
        help="Var olan backend/.env dosyasini ezmeye izin ver.",
    )
    parser.add_argument(
        "--frontend-url",
        default="http://127.0.0.1:3000",
        help="Otomatik yazilacak backend/.env icin frontend public URL'i.",
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Otomatik yazilacak backend/.env icin API public URL'i.",
    )
    return parser


def _print_human_report(report: dict[str, object], *, wrote_env: str | None = None) -> None:
    print("Local v2 doctor")
    print(f"- Backend .env: {'var' if report['backend_env_exists'] else 'yok'} -> {report['backend_env_path']}")
    print(f"- Frontend .env.local: {'var' if report['frontend_env_exists'] else 'yok'} -> {report['frontend_env_path']}")
    print(
        "- Database URL: "
        + ("hazir" if report["database_url_present"] else "eksik")
        + (f" ({report['database_url_source']})" if report["database_url_source"] else "")
    )
    print(
        "- Frontend proxy: "
        + (str(report["frontend_proxy_target"]) if report["frontend_proxy_target"] else "eksik")
        + (f" ({report['frontend_proxy_source']})" if report["frontend_proxy_source"] else "")
    )
    print(
        "- Varsayilan sifre: "
        + (
            "varsayilan 123456"
            if report["default_auth_password_is_default"]
            else "ozellestirilmis"
            if report["default_auth_password_present"]
            else "acik tanimli degil"
        )
    )
    print(
        "- SMS telefonlari: "
        + ("eksik yok" if not report["missing_phone_keys"] else ", ".join(report["missing_phone_keys"]))
    )
    if report["current_app_seed_detected"]:
        print("- Current app kaynagi: bulundu")
    elif report["current_app_seed_placeholders"]:
        print("- Current app kaynagi: sadece placeholder/template degerler bulundu")
    else:
        print("- Current app kaynagi: kullanilabilir seed bulunamadi")

    if wrote_env:
        print(f"- backend/.env yazildi: {wrote_env}")

    blocking_items = report["blocking_items"]
    if blocking_items:
        print("\nBlokajlar:")
        for item in blocking_items:
            print(f"- {item}")

    warnings = report["warnings"]
    if warnings:
        print("\nUyarilar:")
        for item in warnings:
            print(f"- {item}")

    if report["current_app_seed_sources"]:
        print("\nCurrent app kaynaklari:")
        for item in report["current_app_seed_sources"]:
            print(f"- {item}")

    if report["current_app_seed_placeholders"]:
        print("\nTemplate / placeholder kaynaklar:")
        for item in report["current_app_seed_placeholders"]:
            print(f"- {item}")

    next_actions = report["next_actions"]
    if next_actions:
        print("\nSonraki adimlar:")
        for index, item in enumerate(next_actions, start=1):
            print(f"{index}. {item}")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    wrote_env_path: str | None = None
    current_app_seed_values: dict[str, str] | None = None
    if args.sync_from_current_app:
        current_app_seed = discover_current_app_seed_values(V2_ROOT.parent)
        current_app_seed_values = current_app_seed["values"]

    if args.write_backend_env:
        try:
            wrote_env_path = str(
                write_backend_env_file(
                    V2_ROOT,
                    os.environ,
                    overwrite=args.overwrite_backend_env,
                    current_app_seed_values=current_app_seed_values,
                    frontend_url=args.frontend_url,
                    api_url=args.api_url,
                )
            )
        except (FileExistsError, ValueError) as exc:
            if args.json:
                print(json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=True, indent=2))
            else:
                print(str(exc), file=sys.stderr)
            return 2

    report = build_local_doctor_report(V2_ROOT, os.environ)

    if args.json:
        payload = {**report, "written_backend_env_path": wrote_env_path}
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        _print_human_report(report, wrote_env=wrote_env_path)

    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
