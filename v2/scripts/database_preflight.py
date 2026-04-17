#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from render_env_bundle import validate_database_url


APPLICATION_NAME = "catkapinda-crm-v2-db-preflight"
CONNECT_TIMEOUT = 5

REQUIRED_TABLES: tuple[tuple[str, str], ...] = (
    ("restaurants", "Restoran kartlari"),
    ("personnel", "Personel kartlari"),
    ("daily_entries", "Gunluk puantaj"),
    ("deductions", "Kesinti kayitlari"),
    ("inventory_purchases", "Satin alma kayitlari"),
    ("sales_leads", "Satis firsatlari"),
    ("courier_equipment_issues", "Zimmet kayitlari"),
    ("box_returns", "Box geri alim kayitlari"),
)

BOOTSTRAP_TABLES: tuple[tuple[str, str], ...] = (
    ("auth_users", "Auth kullanicilari"),
    ("auth_sessions", "Auth oturumlari"),
    ("auth_phone_codes", "SMS giris kodlari"),
    ("auth_login_attempts", "Login deneme kayitlari"),
    ("audit_logs", "Sistem kayitlari"),
    ("personnel_role_history", "Rol gecmisi"),
    ("personnel_vehicle_history", "Motor gecmisi"),
    ("plate_history", "Plaka gecmisi"),
)


def _is_placeholder(value: str) -> bool:
    normalized = str(value or "").strip()
    return normalized.startswith("<") and normalized.endswith(">")


def resolve_database_url(explicit_value: str | None = None) -> str:
    candidates = (
        explicit_value,
        os.getenv("CK_V2_DATABASE_URL"),
        os.getenv("DATABASE_URL"),
    )
    for item in candidates:
        value = str(item or "").strip()
        if value:
            return value
    raise ValueError("CK_V2_DATABASE_URL veya DATABASE_URL tanimli degil.")


def mask_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    user = parsed.username or ""
    database_name = parsed.path.lstrip("/") or "-"
    query = f"?{parsed.query}" if parsed.query else ""
    auth = f"{user}:***@" if user else ""
    return f"{parsed.scheme}://{auth}{host}{port}/{database_name}{query}"


def _row_to_mapping(row: object) -> dict[str, object]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return {}


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    cursor = conn.execute("SELECT to_regclass(%s) AS table_name", (table_name,))
    row = _row_to_mapping(cursor.fetchone())
    return bool(row.get("table_name"))


def _table_count(conn: psycopg.Connection, table_name: str) -> int | None:
    cursor = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
    row = _row_to_mapping(cursor.fetchone())
    count = row.get("count")
    if count is None:
        return None
    return int(count)


def _inspect_group(
    conn: psycopg.Connection,
    table_specs: tuple[tuple[str, str], ...],
) -> tuple[list[dict[str, object]], list[str]]:
    entries: list[dict[str, object]] = []
    missing_tables: list[str] = []

    for table_name, label in table_specs:
        present = _table_exists(conn, table_name)
        row_count: int | None = None
        detail = "Tablo bulundu."
        if present:
            try:
                row_count = _table_count(conn, table_name)
                detail = (
                    f"Tablo bulundu. Satir sayisi: {row_count}."
                    if row_count is not None
                    else "Tablo bulundu. Satir sayisi okunamadi."
                )
            except Exception as exc:  # pragma: no cover
                detail = f"Tablo bulundu ancak satir sayisi alinamadi: {exc}"
        else:
            missing_tables.append(table_name)
            detail = "Tablo eksik."

        entries.append(
            {
                "table": table_name,
                "label": label,
                "present": present,
                "row_count": row_count,
                "detail": detail,
            }
        )

    return entries, missing_tables


def build_database_preflight_report(
    *,
    database_url: str,
    connect_fn=psycopg.connect,
) -> dict[str, object]:
    normalized_database_url = str(database_url or "").strip()
    if not normalized_database_url:
        raise ValueError("Veritabani URL'i bos olamaz.")
    if _is_placeholder(normalized_database_url):
        raise ValueError("Veritabani URL'i icin gercek bir deger girilmeli.")

    validated_database_url = validate_database_url(normalized_database_url)

    with connect_fn(
        validated_database_url,
        row_factory=dict_row,
        connect_timeout=CONNECT_TIMEOUT,
        application_name=APPLICATION_NAME,
    ) as conn:
        required_entries, required_missing = _inspect_group(conn, REQUIRED_TABLES)
        bootstrap_entries, bootstrap_missing = _inspect_group(conn, BOOTSTRAP_TABLES)

    warnings: list[str] = []
    row_count_map = {entry["table"]: entry["row_count"] for entry in required_entries if entry["present"]}
    for table_name in ("restaurants", "personnel", "daily_entries"):
        count = row_count_map.get(table_name)
        if count == 0:
            warnings.append(
                f"`{table_name}` tablosu bos gorunuyor; ayni canli PostgreSQL baglantisini kullandigini tekrar dogrula."
            )

    if bootstrap_missing:
        warnings.append(
            "Auth ve gecmis tablolarinin bir kismi eksik; v2 bootstrap bunlari acilista tamamlayabilir."
        )

    passed = not required_missing
    blocking_items = [f"`{table_name}` tablosu eksik." for table_name in required_missing]
    summary = (
        "Veritabani omurgasi v2 pilotu icin hazir."
        if passed
        else "Veritabani omurgasinda pilotu durduran eksikler var."
    )
    recommended_next_step = (
        "Ayni PostgreSQL ile pilot acilabilir; yine de deploy oncesi tam yedek al."
        if passed
        else "Eksik tablolari tamamla veya dogru canli PostgreSQL baglantisini gir."
    )

    return {
        "passed": passed,
        "summary": summary,
        "recommended_next_step": recommended_next_step,
        "database_url_masked": mask_database_url(validated_database_url),
        "required_tables": required_entries,
        "bootstrap_tables": bootstrap_entries,
        "blocking_items": blocking_items,
        "warnings": warnings,
    }


def render_report_text(report: dict[str, object]) -> str:
    lines = [
        "Cat Kapinda CRM v2 Database Preflight",
        f"Passed: {report['passed']}",
        f"Summary: {report['summary']}",
        f"Database: {report['database_url_masked']}",
        "",
        "Required Tables:",
    ]
    for entry in report.get("required_tables") or []:
        item = entry if isinstance(entry, dict) else {}
        status = "OK" if item.get("present") else "MISSING"
        lines.append(f"- [{status}] {item.get('table')}: {item.get('detail')}")

    lines.extend(["", "Bootstrap Tables:"])
    for entry in report.get("bootstrap_tables") or []:
        item = entry if isinstance(entry, dict) else {}
        status = "OK" if item.get("present") else "OPTIONAL"
        lines.append(f"- [{status}] {item.get('table')}: {item.get('detail')}")

    lines.extend(["", "Blocking Items:"])
    lines.extend([f"- {item}" for item in report.get("blocking_items") or []] or ["- Yok"])
    lines.extend(["", "Warnings:"])
    lines.extend([f"- {item}" for item in report.get("warnings") or []] or ["- Yok"])
    lines.extend(["", f"Recommended Next Step: {report['recommended_next_step']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect the target PostgreSQL schema before Cat Kapinda CRM v2 pilot deploy."
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL URL to inspect. Defaults to CK_V2_DATABASE_URL or DATABASE_URL.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of plain text.",
    )
    args = parser.parse_args()

    try:
        database_url = resolve_database_url(args.database_url)
        report = build_database_preflight_report(database_url=database_url)
    except Exception as exc:
        payload = {
            "passed": False,
            "summary": "Veritabani preflight basarisiz.",
            "blocking_items": [str(exc)],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("Cat Kapinda CRM v2 Database Preflight")
            print("Passed: False")
            print("Summary: Veritabani preflight basarisiz.")
            print(f"Blocking Items: {exc}")
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_report_text(report), end="")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
