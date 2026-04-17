#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, UTC
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


DEFAULT_TIMEOUT = 12
DEFAULT_LEGACY_URL = "https://crmcatkapinda.com"
PROTECTED_PAGES = [
    ("/announcements", "protected_announcements_page"),
    ("/attendance", "protected_attendance_page"),
    ("/personnel", "protected_personnel_page"),
    ("/deductions", "protected_deductions_page"),
    ("/restaurants", "protected_restaurants_page"),
    ("/sales", "protected_sales_page"),
    ("/purchases", "protected_purchases_page"),
    ("/payroll", "protected_payroll_page"),
    ("/equipment", "protected_equipment_page"),
    ("/audit", "protected_audit_page"),
    ("/reports", "protected_reports_page"),
]
AUTH_JSON_ENDPOINTS = [
    {
        "path": "/v2-api/announcements/dashboard",
        "check_name": "announcements_dashboard_data",
        "required_keys": (
            "module",
            "status",
            "kicker",
            "title",
            "description",
            "metrics",
            "snapshots",
            "notes_title",
            "notes_body",
            "footer_note",
        ),
        "list_keys": ("metrics", "snapshots"),
    },
    {
        "path": "/v2-api/overview/dashboard",
        "check_name": "overview_dashboard_data",
        "required_keys": ("module", "status", "hero", "finance", "hygiene", "operations", "modules", "recent_activity"),
        "list_keys": ("modules", "recent_activity"),
        "nested_dict_keys": {
            "hero": ("active_restaurants", "active_personnel", "month_attendance_entries", "month_deduction_entries"),
            "finance": ("total_revenue", "gross_profit", "total_personnel_cost", "side_income_net", "top_restaurants", "risk_restaurants"),
            "hygiene": ("missing_personnel_cards", "missing_restaurant_cards", "personnel_samples", "restaurant_samples"),
            "operations": ("missing_attendance_count", "under_target_count", "joker_usage_count", "critical_signal_count", "profitable_restaurant_count", "risky_restaurant_count", "shared_operation_total", "action_alerts", "brand_summary", "daily_trend", "top_restaurants", "joker_restaurants"),
        },
    },
    {
        "path": "/v2-api/attendance/dashboard",
        "check_name": "attendance_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries"),
        "list_keys": ("recent_entries",),
        "nested_dict_keys": {"summary": ("total_entries", "today_entries", "month_entries", "active_restaurants")},
    },
    {
        "path": "/v2-api/attendance/entries",
        "check_name": "attendance_entries_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/personnel/dashboard",
        "check_name": "personnel_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries"),
        "list_keys": ("recent_entries",),
        "nested_dict_keys": {"summary": ("total_personnel", "active_personnel", "passive_personnel", "assigned_restaurants")},
    },
    {
        "path": "/v2-api/personnel/records",
        "check_name": "personnel_records_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/deductions/dashboard",
        "check_name": "deductions_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries"),
        "list_keys": ("recent_entries",),
        "nested_dict_keys": {"summary": ("total_entries", "this_month_entries", "manual_entries", "auto_entries")},
    },
    {
        "path": "/v2-api/deductions/records",
        "check_name": "deductions_records_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/restaurants/dashboard",
        "check_name": "restaurants_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries"),
        "list_keys": ("recent_entries",),
        "nested_dict_keys": {"summary": ("total_restaurants", "active_restaurants", "passive_restaurants", "fixed_monthly_restaurants")},
    },
    {
        "path": "/v2-api/restaurants/records",
        "check_name": "restaurants_records_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/sales/dashboard",
        "check_name": "sales_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries"),
        "list_keys": ("recent_entries",),
        "nested_dict_keys": {"summary": ("total_entries", "open_follow_up", "proposal_stage", "won_count")},
    },
    {
        "path": "/v2-api/sales/records",
        "check_name": "sales_records_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/purchases/dashboard",
        "check_name": "purchases_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries"),
        "list_keys": ("recent_entries",),
        "nested_dict_keys": {"summary": ("total_entries", "this_month_entries", "this_month_total_invoice", "distinct_suppliers")},
    },
    {
        "path": "/v2-api/purchases/records",
        "check_name": "purchases_records_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/payroll/dashboard",
        "check_name": "payroll_dashboard_data",
        "required_keys": ("module", "status", "month_options", "entries", "cost_model_breakdown", "top_personnel"),
        "list_keys": ("month_options", "entries", "cost_model_breakdown", "top_personnel"),
        "optional_nested_dict_keys": {"summary": ("selected_month", "personnel_count", "total_hours", "net_payment")},
    },
    {
        "path": "/v2-api/equipment/dashboard",
        "check_name": "equipment_dashboard_data",
        "required_keys": (
            "module",
            "status",
            "summary",
            "recent_issues",
            "recent_box_returns",
            "installment_entries",
            "sales_profit",
            "purchase_summary",
        ),
        "list_keys": ("recent_issues", "recent_box_returns", "installment_entries", "sales_profit", "purchase_summary"),
        "nested_dict_keys": {"summary": ("total_issues", "this_month_issues", "installment_rows", "total_box_returns")},
    },
    {
        "path": "/v2-api/equipment/issues",
        "check_name": "equipment_issues_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/equipment/box-returns",
        "check_name": "equipment_box_returns_data",
        "required_keys": ("total_entries", "entries"),
        "list_keys": ("entries",),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/audit/dashboard",
        "check_name": "audit_dashboard_data",
        "required_keys": ("module", "status", "summary", "recent_entries", "action_options", "entity_options", "actor_options"),
        "list_keys": ("recent_entries", "action_options", "entity_options", "actor_options"),
        "nested_dict_keys": {"summary": ("total_entries", "last_7_days", "unique_actors", "unique_entities")},
    },
    {
        "path": "/v2-api/audit/records",
        "check_name": "audit_records_data",
        "required_keys": ("total_entries", "entries", "action_options", "entity_options", "actor_options"),
        "list_keys": ("entries", "action_options", "entity_options", "actor_options"),
        "non_negative_int_keys": ("total_entries",),
    },
    {
        "path": "/v2-api/reports/dashboard",
        "check_name": "reports_dashboard_data",
        "required_keys": ("module", "status", "month_options", "invoice_entries", "cost_entries", "model_breakdown", "top_restaurants", "top_couriers"),
        "list_keys": ("month_options", "invoice_entries", "cost_entries", "model_breakdown", "top_restaurants", "top_couriers"),
        "optional_nested_dict_keys": {"summary": ("selected_month", "restaurant_count", "courier_count", "gross_profit")},
    },
]
LEGACY_BANNER_MARKERS = ("Yeni sisteme gecis basladi", "v2 pilotu ac")
LEGACY_REDIRECT_MARKERS = ("YENI SISTEM ACILIYOR", "Cat Kapinda CRM v2'ye geciliyor")
WARNING_ONLY_CHECKS = {"legacy_banner_bridge", "legacy_redirect_bridge"}
CHECK_GUIDANCE: dict[str, tuple[str, str]] = {
    "frontend_health": (
        "v2 frontend ayaga kalkmamis gorunuyor.",
        "Render frontend servisini ve /api/health yanitini once duzeltelim.",
    ),
    "frontend_ready": (
        "Frontend backend'e saglikli baglanamiyor.",
        "CK_V2_INTERNAL_API_HOSTPORT veya yerel base URL ayarlarini kontrol edelim.",
    ),
    "frontend_pilot_status": (
        "Pilot status koprusu eksik ya da backend pilot verisi gelmiyor.",
        "Once /api/pilot-status ve backend /health/pilot hattini dogrulayalim.",
    ),
    "release_alignment": (
        "Frontend ve backend farkli release ile ayakta.",
        "Iki servisi de ayni commit ile yeniden deploy edelim.",
    ),
    "status_page": (
        "Pilot durum ekrani acilmiyor.",
        "Frontend routing ve /status sayfasini kontrol edelim.",
    ),
    "login_page": (
        "Login ekrani erisilebilir degil.",
        "Frontend login route'unu ve middleware akisini kontrol edelim.",
    ),
    "backend_health": (
        "v2 backend ayaga kalkmamis gorunuyor.",
        "Render API servisini ve /api/health yanitini duzeltelim.",
    ),
    "backend_ready": (
        "Backend readiness kontrolu temiz donmuyor.",
        "Database ve temel bootstrap kontrollerini inceleyelim.",
    ),
    "backend_pilot": (
        "Pilot readiness hala bloklu.",
        "Eksik env'leri ve cutover phase detaylarini /status uzerinden kapatalim.",
    ),
    "auth_login": (
        "Verilen pilot hesapla giris basarisiz.",
        "Pilot kullanici sifresini ve auth senkronunu kontrol edelim.",
    ),
    "auth_me": (
        "Login sonrasi auth/me dogrulanamadi.",
        "Token/cookie akisini ve backend auth endpointlerini kontrol edelim.",
    ),
    "protected_announcements_page": (
        "Giris sonrasi Duyurular sayfasi acilmadi.",
        "Announcements route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_attendance_page": (
        "Giris sonrasi Puantaj sayfasi acilmadi.",
        "Attendance route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_personnel_page": (
        "Giris sonrasi Personel sayfasi acilmadi.",
        "Personnel route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_deductions_page": (
        "Giris sonrasi Kesintiler sayfasi acilmadi.",
        "Deductions route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_restaurants_page": (
        "Giris sonrasi Restoranlar sayfasi acilmadi.",
        "Restaurants route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_sales_page": (
        "Giris sonrasi Satis sayfasi acilmadi.",
        "Sales route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_purchases_page": (
        "Giris sonrasi Satin Alma sayfasi acilmadi.",
        "Purchases route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_payroll_page": (
        "Giris sonrasi Aylik Hakedis sayfasi acilmadi.",
        "Payroll route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_equipment_page": (
        "Giris sonrasi Ekipman sayfasi acilmadi.",
        "Equipment route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_audit_page": (
        "Giris sonrasi Sistem Kayitlari sayfasi acilmadi.",
        "Audit route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "protected_reports_page": (
        "Giris sonrasi Raporlar sayfasi acilmadi.",
        "Reports route ve korumali sayfa cookie akisini kontrol edelim.",
    ),
    "announcements_dashboard_data": (
        "Duyurular veri omurgasi acilmadi.",
        "Announcements dashboard endpoint'ini ve sabit pano verisini kontrol edelim.",
    ),
    "overview_dashboard_data": (
        "Genel Bakis veri omurgasi cevap vermiyor.",
        "Overview dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "attendance_dashboard_data": (
        "Puantaj ozet verisi acilmadi.",
        "Attendance dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "attendance_entries_data": (
        "Puantaj liste verisi acilmadi.",
        "Attendance entries endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "personnel_dashboard_data": (
        "Personel ozet verisi acilmadi.",
        "Personnel dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "personnel_records_data": (
        "Personel liste verisi acilmadi.",
        "Personnel records endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "deductions_dashboard_data": (
        "Kesinti ozet verisi acilmadi.",
        "Deductions dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "deductions_records_data": (
        "Kesinti liste verisi acilmadi.",
        "Deductions records endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "restaurants_dashboard_data": (
        "Restoran ozet verisi acilmadi.",
        "Restaurants dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "restaurants_records_data": (
        "Restoran liste verisi acilmadi.",
        "Restaurants records endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "sales_dashboard_data": (
        "Satis ozet verisi acilmadi.",
        "Sales dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "sales_records_data": (
        "Satis liste verisi acilmadi.",
        "Sales records endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "purchases_dashboard_data": (
        "Satin Alma ozet verisi acilmadi.",
        "Purchases dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "purchases_records_data": (
        "Satin Alma liste verisi acilmadi.",
        "Purchases records endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "payroll_dashboard_data": (
        "Aylik Hakedis ozet verisi acilmadi.",
        "Payroll dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "equipment_dashboard_data": (
        "Ekipman ozet verisi acilmadi.",
        "Equipment dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "equipment_issues_data": (
        "Zimmet liste verisi acilmadi.",
        "Equipment issues endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "equipment_box_returns_data": (
        "Box geri alim liste verisi acilmadi.",
        "Equipment box-returns endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "audit_dashboard_data": (
        "Sistem kayitlari ozet verisi acilmadi.",
        "Audit dashboard endpoint'ini ve ozet sorgularini kontrol edelim.",
    ),
    "audit_records_data": (
        "Sistem kayitlari liste verisi acilmadi.",
        "Audit records endpoint'ini ve liste sorgularini kontrol edelim.",
    ),
    "reports_dashboard_data": (
        "Raporlar veri omurgasi acilmadi.",
        "Reports dashboard endpoint'ini ve rapor sorgularini kontrol edelim.",
    ),
    "legacy_banner_bridge": (
        "Eski Streamlit panelde banner koprusu gorunmuyor.",
        "CK_V2_PILOT_URL ve CK_V2_CUTOVER_MODE=banner ayarlarini kontrol edelim.",
    ),
    "legacy_redirect_bridge": (
        "Eski Streamlit panelde redirect koprusu gorunmuyor.",
        "CK_V2_PILOT_URL ve CK_V2_CUTOVER_MODE=redirect ayarlarini kontrol edelim.",
    ),
}
CHECK_PRIORITY = [
    "frontend_health",
    "frontend_ready",
    "backend_health",
    "backend_ready",
    "backend_pilot",
    "frontend_pilot_status",
    "release_alignment",
    "status_page",
    "login_page",
    "auth_login",
    "auth_me",
    "protected_announcements_page",
    "protected_attendance_page",
    "protected_personnel_page",
    "protected_deductions_page",
    "protected_restaurants_page",
    "protected_sales_page",
    "protected_purchases_page",
    "protected_payroll_page",
    "protected_equipment_page",
    "protected_audit_page",
    "protected_reports_page",
    "announcements_dashboard_data",
    "overview_dashboard_data",
    "attendance_dashboard_data",
    "attendance_entries_data",
    "personnel_dashboard_data",
    "personnel_records_data",
    "deductions_dashboard_data",
    "deductions_records_data",
    "restaurants_dashboard_data",
    "restaurants_records_data",
    "sales_dashboard_data",
    "sales_records_data",
    "purchases_dashboard_data",
    "purchases_records_data",
    "payroll_dashboard_data",
    "equipment_dashboard_data",
    "equipment_issues_data",
    "equipment_box_returns_data",
    "audit_dashboard_data",
    "audit_records_data",
    "reports_dashboard_data",
    "legacy_banner_bridge",
    "legacy_redirect_bridge",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_json_endpoint_payload(endpoint: dict[str, object], payload: dict) -> tuple[bool, str]:
    issues: list[str] = []

    if not isinstance(payload, dict):
        return False, "payload=nesne degil"

    required_keys = endpoint.get("required_keys", ())
    list_keys = endpoint.get("list_keys", ())
    nested_dict_keys = endpoint.get("nested_dict_keys", {})
    optional_nested_dict_keys = endpoint.get("optional_nested_dict_keys", {})
    non_negative_int_keys = endpoint.get("non_negative_int_keys", ())

    for key in required_keys:
        if key not in payload:
            issues.append(f"{key}=eksik")

    for key in list_keys:
        if key in payload and not isinstance(payload.get(key), list):
            issues.append(f"{key}=liste degil")

    for key, child_keys in nested_dict_keys.items():
        value = payload.get(key)
        if not isinstance(value, dict):
            issues.append(f"{key}=nesne degil")
            continue
        for child_key in child_keys:
            if child_key not in value:
                issues.append(f"{key}.{child_key}=eksik")

    for key, child_keys in optional_nested_dict_keys.items():
        value = payload.get(key)
        if value is None:
            continue
        if not isinstance(value, dict):
            issues.append(f"{key}=nesne degil")
            continue
        for child_key in child_keys:
            if child_key not in value:
                issues.append(f"{key}.{child_key}=eksik")

    for key in non_negative_int_keys:
        if key in payload and not _is_non_negative_int(payload.get(key)):
            issues.append(f"{key}=gecersiz")

    if issues:
        return False, " • ".join(issues[:4])
    return True, "sekil=uygun"


def is_local_base_url(raw: str) -> bool:
    parsed = urllib.parse.urlparse(raw)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost"}


def build_decision_summary(report: dict) -> dict:
    failed_names = [result["name"] for result in report["results"] if not result["ok"]]
    legacy_mode = report.get("legacy_cutover_mode") or None

    if not failed_names:
        next_step = "Pilot login ekranini acip ofisle ilk pilot senaryolarina gecebiliriz."
        if legacy_mode == "banner":
            next_step = "Banner koprusu de temiz. Ofis pilotunu acip gozlem turune gecebiliriz."
        elif legacy_mode == "redirect":
            next_step = "Redirect koprusu de temiz. Streamlit'ten cikis provasi yapmaya haziriz."
        return {
            "status": "pass",
            "headline": "Pilot smoke temiz.",
            "primary_blocker": None,
            "recommended_next_step": next_step,
            "failing_checks": [],
        }

    ordered_failures = sorted(
        failed_names,
        key=lambda name: CHECK_PRIORITY.index(name) if name in CHECK_PRIORITY else len(CHECK_PRIORITY),
    )
    blocking_failures = [name for name in ordered_failures if name not in WARNING_ONLY_CHECKS]
    primary_name = blocking_failures[0] if blocking_failures else ordered_failures[0]
    headline, next_step = CHECK_GUIDANCE.get(
        primary_name,
        ("Pilot smoke blokaj verdi.", "Ilk failing check'i inceleyip blokaji kapatalim."),
    )
    primary_blocker = CHECK_GUIDANCE.get(primary_name, ("", ""))[0]
    status = "blocking" if blocking_failures else "warning"

    if status == "warning":
        headline = "v2 pilot cekirdek olarak hazir, ama gecis koprusu eksik."
        if legacy_mode == "banner":
            next_step = "Banner env'lerini tamamlayip eski panelden gecis kartini gorunur hale getirelim."
        elif legacy_mode == "redirect":
            next_step = "Redirect env'lerini tamamlayip kontrollu yonlendirme provasini yapalim."

    return {
        "status": status,
        "headline": headline,
        "primary_blocker": primary_blocker,
        "recommended_next_step": next_step,
        "failing_checks": ordered_failures,
    }


def build_markdown_report(report: dict) -> str:
    decision = report["decision"]
    lines = [
        "# v2 Pilot Smoke Report",
        "",
        f"- Base URL: `{report['base_url']}`",
        f"- Preset: `{report['preset'] or '-'}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Timeout: `{report['timeout_seconds']}s`",
        f"- Identity Provided: `{report['identity_provided']}`",
        f"- Legacy URL: `{report['legacy_url'] or '-'}`",
        f"- Legacy Cutover Mode: `{report['legacy_cutover_mode'] or '-'}`",
        f"- Overall OK: `{report['overall_ok']}`",
        f"- Passed: `{report['passed_count']}`",
        f"- Failed: `{report['failed_count']}`",
        "",
        "## Decision",
        "",
        f"- Status: `{decision['status']}`",
        f"- Headline: {decision['headline']}",
        f"- Primary Blocker: {decision['primary_blocker'] or '-'}",
        f"- Recommended Next Step: {decision['recommended_next_step']}",
        f"- Failing Checks: `{', '.join(decision['failing_checks']) if decision['failing_checks'] else '-'}`",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]

    for result in report["results"]:
        result_label = "OK" if result["ok"] else "FAIL"
        detail = str(result["detail"]).replace("\n", " ").replace("|", "\\|")
        lines.append(f"| `{result['name']}` | **{result_label}** | {detail} |")

    return "\n".join(lines) + "\n"


def build_report(
    *,
    base_url: str,
    timeout: int,
    preset: str | None,
    identity: str | None,
    legacy_url: str | None,
    legacy_cutover_mode: str | None,
    results: list[CheckResult],
) -> dict:
    passed_count = sum(1 for result in results if result.ok)
    failed_count = sum(1 for result in results if not result.ok)
    result_entries = [
        {
            "name": result.name,
            "ok": result.ok,
            "detail": result.detail,
        }
        for result in results
    ]
    decision = build_decision_summary(
        {
            "base_url": base_url,
            "preset": preset,
            "identity_provided": bool(identity),
            "legacy_url": legacy_url,
            "legacy_cutover_mode": legacy_cutover_mode,
            "results": result_entries,
        }
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "preset": preset,
        "timeout_seconds": timeout,
        "identity_provided": bool(identity),
        "legacy_url": legacy_url,
        "legacy_cutover_mode": legacy_cutover_mode,
        "overall_ok": failed_count == 0,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "decision": decision,
        "results": result_entries,
    }


def normalize_base_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("Base URL bos olamaz.")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


def resolve_preset(
    preset: str | None,
    *,
    legacy_url: str | None,
    legacy_cutover_mode: str | None,
) -> tuple[str | None, str | None]:
    normalized_preset = (preset or "").strip().lower() or None
    resolved_legacy_url = legacy_url
    resolved_legacy_cutover_mode = legacy_cutover_mode

    if normalized_preset == "pilot":
        resolved_legacy_cutover_mode = resolved_legacy_cutover_mode or "banner"
        resolved_legacy_url = resolved_legacy_url or normalize_base_url(
            os.getenv("CK_V2_SMOKE_LEGACY_URL", DEFAULT_LEGACY_URL)
        )
    elif normalized_preset == "cutover":
        resolved_legacy_cutover_mode = resolved_legacy_cutover_mode or "redirect"
        resolved_legacy_url = resolved_legacy_url or normalize_base_url(
            os.getenv("CK_V2_SMOKE_LEGACY_URL", DEFAULT_LEGACY_URL)
        )

    return resolved_legacy_url, resolved_legacy_cutover_mode


def fetch_json(base_url: str, path: str, timeout: int) -> tuple[int, dict]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        payload = json.loads(response.read().decode("utf-8"))
        return status, payload


def post_json(base_url: str, path: str, payload: dict, timeout: int, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        response_payload = json.loads(response.read().decode("utf-8"))
        return status, response_payload


def fetch_text(base_url: str, path: str, timeout: int) -> tuple[int, str, str]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        content_type = response.headers.get("Content-Type", "")
        payload = response.read().decode("utf-8", errors="replace")
        return status, content_type, payload


def fetch_text_with_headers(base_url: str, path: str, timeout: int, headers: dict[str, str]) -> tuple[int, str, str]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", **headers})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        content_type = response.headers.get("Content-Type", "")
        payload = response.read().decode("utf-8", errors="replace")
        return status, content_type, payload


def run_smoke_checks(
    base_url: str,
    timeout: int,
    identity: str | None = None,
    password: str | None = None,
    legacy_url: str | None = None,
    legacy_cutover_mode: str | None = None,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    local_run = is_local_base_url(base_url)

    try:
        status, payload = fetch_json(base_url, "/api/health", timeout)
        ok = status == 200 and payload.get("status") == "ok"
        results.append(
            CheckResult(
                name="frontend_health",
                ok=ok,
                detail=f"HTTP {status} • service={payload.get('service', '-')}",
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("frontend_health", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/api/ready", timeout)
        ok = status == 200 and bool(payload.get("proxyConfigured")) and bool(payload.get("backendReachable"))
        results.append(
            CheckResult(
                name="frontend_ready",
                ok=ok,
                detail=(
                    f"HTTP {status} • proxyConfigured={payload.get('proxyConfigured')} • "
                    f"proxyMode={payload.get('proxyMode')} • "
                    f"source={payload.get('sourceEnvKey')} • "
                    f"backendReachable={payload.get('backendReachable')} • backendStatus={payload.get('backendStatus')}"
                ),
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("frontend_ready", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/api/pilot-status", timeout)
        frontend_payload = payload.get("frontend", {})
        backend_payload = payload.get("backend", {})
        go_live_payload = backend_payload.get("go_live", {}) if isinstance(backend_payload, dict) else {}
        frontend_release = frontend_payload.get("releaseLabel") if isinstance(frontend_payload, dict) else None
        backend_release = backend_payload.get("release_label") if isinstance(backend_payload, dict) else None
        ok = (
            status == 200
            and bool(frontend_payload.get("proxyConfigured"))
            and bool(frontend_payload.get("backendReachable"))
            and bool(backend_payload)
            and bool(go_live_payload.get("phase"))
        )
        results.append(
            CheckResult(
                name="frontend_pilot_status",
                ok=ok,
                detail=(
                    f"HTTP {status} • proxyMode={frontend_payload.get('proxyMode')} • "
                    f"backend={frontend_payload.get('backendStatus')} • "
                    f"pilotPhase={backend_payload.get('cutover', {}).get('phase') if isinstance(backend_payload, dict) else '-'} • "
                    f"goLivePhase={go_live_payload.get('phase', '-')}"
                ),
            )
        )
        release_ok = True
        if frontend_release and backend_release:
            release_ok = frontend_release == backend_release
        results.append(
            CheckResult(
                name="release_alignment",
                ok=release_ok,
                detail=(
                    f"frontend={frontend_release or '-'} • "
                    f"backend={backend_release or '-'}"
                ),
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("frontend_pilot_status", False, str(exc)))
        results.append(CheckResult("release_alignment", False, str(exc)))

    try:
        status, content_type, _ = fetch_text(base_url, "/status", timeout)
        ok = status == 200 and "text/html" in content_type.lower()
        results.append(
            CheckResult(
                name="status_page",
                ok=ok,
                detail=f"HTTP {status} • content-type={content_type or '-'}",
            )
        )
    except urllib.error.URLError as exc:
        results.append(CheckResult("status_page", False, str(exc)))

    try:
        status, content_type, _ = fetch_text(base_url, "/login", timeout)
        ok = status == 200 and "text/html" in content_type.lower()
        results.append(
            CheckResult(
                name="login_page",
                ok=ok,
                detail=f"HTTP {status} • content-type={content_type or '-'}",
            )
        )
    except urllib.error.URLError as exc:
        results.append(CheckResult("login_page", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/v2-api/health", timeout)
        ok = status == 200 and payload.get("status") == "ok"
        results.append(
            CheckResult(
                name="backend_health",
                ok=ok,
                detail=f"HTTP {status} • service={payload.get('service', '-')}",
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_health", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/v2-api/health/ready", timeout)
        check_count = len(payload.get("checks", []))
        ok = status == 200 and payload.get("status") in {"ok", "degraded"} and check_count > 0
        results.append(
            CheckResult(
                name="backend_ready",
                ok=ok,
                detail=f"HTTP {status} • status={payload.get('status')} • checks={check_count}",
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_ready", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/v2-api/health/pilot", timeout)
        module_count = len(payload.get("modules", []))
        auth = payload.get("auth", {})
        cutover = payload.get("cutover", {})
        required_missing_envs = payload.get("required_missing_env_vars", [])
        optional_missing_envs = payload.get("optional_missing_env_vars", [])
        checks = payload.get("checks", [])
        modules_ready_count = int(cutover.get("modules_ready_count") or 0)
        local_sqlite_fallback = any(
            isinstance(item, dict)
            and item.get("name") == "database_url"
            and "sqlite fallback" in str(item.get("detail") or "").lower()
            for item in checks
        )
        pilot_ready = (
            status == 200
            and payload.get("status") in {"ok", "degraded"}
            and module_count >= 8
            and bool(auth.get("email_login"))
            and bool(auth.get("phone_login"))
            and len(required_missing_envs) == 0
            and cutover.get("phase") in {"ready_for_pilot", "ready_for_cutover"}
            and bool(cutover.get("ready"))
        )
        local_ready = (
            local_run
            and status == 200
            and payload.get("status") in {"ok", "degraded"}
            and module_count >= 8
            and bool(auth.get("email_login"))
            and bool(auth.get("phone_login"))
            and local_sqlite_fallback
            and required_missing_envs == ["CK_V2_DATABASE_URL"]
            and cutover.get("phase") == "not_ready"
        )
        ok = pilot_ready or local_ready
        detail = (
            f"HTTP {status} • status={payload.get('status')} • "
            f"phase={cutover.get('phase', '-')} • "
            f"modules={modules_ready_count}/{module_count} • "
            f"sms={auth.get('sms_login')} • "
            f"required_missing={len(required_missing_envs)} • "
            f"optional_missing={len(optional_missing_envs)}"
        )
        if local_ready:
            detail = f"{detail} • local_sqlite_hazir=True"
        results.append(
            CheckResult(
                name="backend_pilot",
                ok=ok,
                detail=detail,
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_pilot", False, str(exc)))

    if identity and password:
        try:
            status, payload = post_json(
                base_url,
                "/v2-api/auth/login",
                {"identity": identity, "password": password},
                timeout,
            )
            token = str(payload.get("access_token") or "")
            login_ok = status == 200 and bool(token)
            results.append(
                CheckResult(
                    name="auth_login",
                    ok=login_ok,
                    detail=f"HTTP {status} • token={'var' if token else 'yok'} • must_change={payload.get('user', {}).get('must_change_password')}",
                )
            )
            if login_ok:
                me_status, me_payload = fetch_json_with_headers(
                    base_url,
                    "/v2-api/auth/me",
                    timeout,
                    headers={"Authorization": f"Bearer {token}"},
                )
                me_ok = me_status == 200 and bool(me_payload.get("email"))
                results.append(
                    CheckResult(
                        name="auth_me",
                        ok=me_ok,
                        detail=f"HTTP {me_status} • user={me_payload.get('email', '-')}",
                    )
                )
                cookie_headers = {"Cookie": f"ck_v2_auth_token={token}"}
                for path, check_name in PROTECTED_PAGES:
                    page_status, page_content_type, _ = fetch_text_with_headers(
                        base_url,
                        path,
                        timeout,
                        headers=cookie_headers,
                    )
                    page_ok = page_status == 200 and "text/html" in page_content_type.lower()
                    results.append(
                        CheckResult(
                            name=check_name,
                            ok=page_ok,
                            detail=f"HTTP {page_status} • content-type={page_content_type or '-'} • path={path}",
                        )
                    )
                for endpoint in AUTH_JSON_ENDPOINTS:
                    path = str(endpoint["path"])
                    check_name = str(endpoint["check_name"])
                    data_status, data_payload = fetch_json_with_headers(
                        base_url,
                        path,
                        timeout,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    payload_ok, payload_detail = validate_json_endpoint_payload(endpoint, data_payload)
                    data_ok = data_status == 200 and payload_ok
                    detail = f"HTTP {data_status} • path={path} • {payload_detail}"
                    results.append(
                        CheckResult(
                            name=check_name,
                            ok=data_ok,
                            detail=detail,
                        )
                    )
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            results.append(CheckResult("auth_login", False, str(exc)))

    if legacy_url and legacy_cutover_mode in {"banner", "redirect"}:
        if local_run:
            results.append(
                CheckResult(
                    name=f"legacy_{legacy_cutover_mode}_bridge",
                    ok=True,
                    detail=f"Yerel calismada legacy {legacy_cutover_mode} koprusu atlandi.",
                )
            )
            return results
        try:
            status, content_type, payload = fetch_text(legacy_url, "/", timeout)
            markers = LEGACY_BANNER_MARKERS if legacy_cutover_mode == "banner" else LEGACY_REDIRECT_MARKERS
            ok = status == 200 and "text/html" in content_type.lower() and all(marker in payload for marker in markers)
            results.append(
                CheckResult(
                    name=f"legacy_{legacy_cutover_mode}_bridge",
                    ok=ok,
                    detail=f"HTTP {status} • mode={legacy_cutover_mode} • content-type={content_type or '-'}",
                )
            )
        except urllib.error.URLError as exc:
            results.append(CheckResult(f"legacy_{legacy_cutover_mode}_bridge", False, str(exc)))

    return results


def fetch_json_with_headers(base_url: str, path: str, timeout: int, headers: dict[str, str]) -> tuple[int, dict]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", **headers})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        payload = json.loads(response.read().decode("utf-8"))
        return status, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run basic pilot smoke checks against a deployed v2 frontend URL.")
    parser.add_argument("--base-url", required=True, help="Public frontend URL, e.g. https://crmcatkapinda-v2.onrender.com")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds")
    parser.add_argument(
        "--preset",
        default=os.getenv("CK_V2_SMOKE_PRESET", ""),
        choices=["", "pilot", "cutover"],
        help="Optional smoke bundle preset. 'pilot' adds legacy banner bridge, 'cutover' adds legacy redirect bridge.",
    )
    parser.add_argument("--identity", default=os.getenv("CK_V2_SMOKE_IDENTITY", ""), help="Optional login identity for end-to-end auth smoke")
    parser.add_argument("--password", default=os.getenv("CK_V2_SMOKE_PASSWORD", ""), help="Optional login password for end-to-end auth smoke")
    parser.add_argument("--legacy-url", default=os.getenv("CK_V2_SMOKE_LEGACY_URL", ""), help="Optional legacy Streamlit URL for banner/redirect smoke")
    parser.add_argument("--json", action="store_true", help="Print the smoke result as JSON instead of a text table")
    parser.add_argument("--markdown", action="store_true", help="Print the smoke result as Markdown instead of a text table")
    parser.add_argument("--output", default="", help="Optional file path to write the JSON smoke report")
    parser.add_argument(
        "--legacy-cutover-mode",
        default="",
        choices=["", "banner", "redirect"],
        help="Optional legacy cutover mode to verify on the old Streamlit app",
    )
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    preset = args.preset.strip() or None
    identity = args.identity.strip() or None
    password = args.password.strip() or None
    legacy_url = normalize_base_url(args.legacy_url) if args.legacy_url.strip() else None
    legacy_cutover_mode = args.legacy_cutover_mode.strip() or None
    legacy_url, legacy_cutover_mode = resolve_preset(
        preset,
        legacy_url=legacy_url,
        legacy_cutover_mode=legacy_cutover_mode,
    )
    results = run_smoke_checks(
        base_url,
        args.timeout,
        identity=identity,
        password=password,
        legacy_url=legacy_url,
        legacy_cutover_mode=legacy_cutover_mode,
    )
    report = build_report(
        base_url=base_url,
        timeout=args.timeout,
        preset=preset,
        identity=identity,
        legacy_url=legacy_url,
        legacy_cutover_mode=legacy_cutover_mode,
        results=results,
    )

    failed = False
    for result in results:
        failed = failed or not result.ok

    if args.output.strip():
        output_path = args.output.strip()
        if output_path.lower().endswith(".md"):
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(build_markdown_report(report))
        else:
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if failed else 0

    if args.markdown:
        print(build_markdown_report(report))
        return 1 if failed else 0

    decision = report["decision"]
    print(f"v2 pilot smoke • {base_url}")
    print("-" * 72)
    if preset:
        print(f"Preset    {preset}")
    print(f"Decision  {decision['status'].upper():<10}  {decision['headline']}")
    if decision["primary_blocker"]:
        print(f"Blocker   {decision['primary_blocker']}")
    print(f"Next Step {decision['recommended_next_step']}")
    if decision["failing_checks"]:
        print(f"Failures  {', '.join(decision['failing_checks'])}")
    print("-" * 72)
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"{status:>4}  {result.name:<18}  {result.detail}")

    print("-" * 72)
    if args.output.strip():
        print(f"JSON report written to: {args.output.strip()}")
    if failed:
        print("Pilot smoke check failed.")
        return 1

    print("Pilot smoke check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
