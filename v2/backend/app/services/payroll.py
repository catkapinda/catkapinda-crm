from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.core.database import is_sqlite_backend
from app.services.motor_rental import (
    MOTOR_PURCHASE_DEDUCTION_TYPE,
    MOTOR_RENTAL_DEDUCTION_TYPE,
    calculate_company_motor_purchase_deduction,
    calculate_company_motor_rental_deduction,
    is_motor_purchase_deduction_type,
    is_motor_rental_deduction_type,
)
from app.schemas.payroll import (
    PayrollCostModelBreakdownEntry,
    PayrollDashboardResponse,
    PayrollEntry,
    PayrollModuleStatus,
    PayrollRoleBreakdownEntry,
    PayrollSummary,
    PayrollTopPersonnelEntry,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_repo_root_on_path() -> None:
    repo_root = str(_repo_root())
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _build_compat_connection(conn: psycopg.Connection):
    _ensure_repo_root_on_path()
    from infrastructure.db_engine import CompatConnection

    info = getattr(conn, "info", None)
    host = getattr(info, "host", "?") if info else "?"
    port = getattr(info, "port", 5432) if info else 5432
    dbname = getattr(info, "dbname", "postgres") if info else "postgres"
    user = getattr(info, "user", "?") if info else "?"
    cache_key = f"postgres:{host}:{port}/{dbname}:{user}"
    return CompatConnection(conn, "postgres", cache_key=cache_key)


def _safe_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return 0.0


def _month_key_sql(column: str) -> str:
    return f"substr(COALESCE(CAST({column} AS TEXT), ''), 1, 7)"


_COST_MODEL_LABELS = {
    "standard_courier": "Standart Kurye",
    "fixed_monthly": "Sabit Aylık",
    "fixed_kurye": "Kurye Sabit",
    "fixed_bolge_muduru": "Bölge Müdürü",
    "fixed_saha_denetmen_sefi": "Saha Denetmen Şefi",
    "fixed_restoran_takim_sefi": "Restoran Takım Şefi",
    "fixed_joker": "Joker Sabit",
    "hourly_only": "Sadece Saatlik",
    "hourly_plus_package": "Saat + Paket",
    "threshold_package": "Eşikli Paket",
}

_COURIER_HOURLY_COST = 250.0
_COURIER_HOURLY_COST_DOGU_OTOMOTIV = 295.0
_COURIER_PACKAGE_COST_DEFAULT_LOW = 20.0
_COURIER_PACKAGE_COST_DEFAULT_HIGH = 25.0
_COURIER_PACKAGE_COST_QC = 25.0
_PACKAGE_THRESHOLD_DEFAULT = 390
_PAYROLL_VAT_RATE = 0.20
_PAYROLL_TEVKIFAT_RATE = 0.20
_PAYROLL_TEVKIFAT_THRESHOLD = 12000.0
_SUPPORT_HOLIDAY_DAY_DIVISOR = 30.0
_PAYROLL_IGNORED_DEDUCTION_SQL = "('Partner Kart Indirimi', 'Partner Kart İndirimi')"
_MOTOR_RENTAL_DEDUCTION_SQL = "('Motor Kirası', 'Motor Kirasi')"
_MOTOR_PURCHASE_DEDUCTION_SQL = "('Motor Satış Taksiti', 'Motor Satis Taksiti', 'Motor Satın Alım', 'Motor Satin Alim')"
_INVOICE_BASE_REDUCING_DEDUCTION_TYPES = {"Fatura Edilmeyen Tutar"}
_SUPPORT_HOLIDAY_DOUBLE_COST_MODELS = {"fixed_joker", "fixed_bolge_muduru"}
_SUPPORT_HOLIDAY_DOUBLE_ROLES = {"Joker", "Bölge Müdürü", "Bolge Muduru"}
_RELIGIOUS_HOLIDAY_DOUBLE_DATES = {
    date(2025, 3, 30),
    date(2025, 3, 31),
    date(2025, 6, 6),
    date(2025, 6, 7),
    date(2026, 3, 20),
    date(2026, 3, 21),
    date(2026, 5, 28),
    date(2026, 5, 29),
}


@dataclass(frozen=True)
class PayrollTevkifatBreakdown:
    invoice_base_amount: float
    vat_amount: float
    tevkifat_amount: float


@dataclass
class PayrollDocumentPayload:
    selected_month: str
    personnel_id: int
    personnel: str
    person_code: str
    role: str
    status: str
    total_hours: float
    total_packages: float
    gross_pay: float
    total_deductions: float
    net_payment: float
    invoice_base_amount: float
    invoice_vat_amount: float
    tevkifat_amount: float
    restaurant_names: list[str]
    deduction_items: list[tuple[str, float]]


def _normalized_brand_key(brand: object) -> str:
    return str(brand or "").strip().lower()


def _is_quick_china_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) == "quick china"


def _is_dogu_otomotiv_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) in {"doğu otomotiv", "dogu otomotiv"}


def _calculate_standard_package_cost(total_packages: float, *, brand: object = "") -> float:
    package_total = _safe_float(total_packages)
    if _is_dogu_otomotiv_brand(brand):
        return 0.0
    if _is_quick_china_brand(brand):
        return package_total * _COURIER_PACKAGE_COST_QC
    package_rate = (
        _COURIER_PACKAGE_COST_DEFAULT_LOW
        if package_total <= float(_PACKAGE_THRESHOLD_DEFAULT)
        else _COURIER_PACKAGE_COST_DEFAULT_HIGH
    )
    return package_total * package_rate


def _calculate_standard_courier_cost(
    total_hours: float,
    total_packages: float,
    *,
    brand: object = "",
) -> float:
    hourly_cost = _COURIER_HOURLY_COST_DOGU_OTOMOTIV if _is_dogu_otomotiv_brand(brand) else _COURIER_HOURLY_COST
    return _safe_float(total_hours) * hourly_cost + _calculate_standard_package_cost(
        total_packages,
        brand=brand,
    )


def _calculate_variable_courier_gross_cost(segments: list[dict[str, object]]) -> float:
    standard_threshold_packages = 0.0
    gross_cost = 0.0

    for segment in segments:
        brand = segment.get("brand")
        total_hours = _safe_float(segment.get("total_hours"))
        total_packages = _safe_float(segment.get("total_packages"))

        if _is_dogu_otomotiv_brand(brand):
            gross_cost += total_hours * _COURIER_HOURLY_COST_DOGU_OTOMOTIV
            continue

        gross_cost += total_hours * _COURIER_HOURLY_COST
        if _is_quick_china_brand(brand):
            gross_cost += total_packages * _COURIER_PACKAGE_COST_QC
        else:
            standard_threshold_packages += total_packages

    if standard_threshold_packages > 0:
        package_rate = (
            _COURIER_PACKAGE_COST_DEFAULT_HIGH
            if standard_threshold_packages > float(_PACKAGE_THRESHOLD_DEFAULT)
            else _COURIER_PACKAGE_COST_DEFAULT_LOW
        )
        gross_cost += standard_threshold_packages * package_rate

    return _safe_float(gross_cost)


def _parse_attendance_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _count_support_holiday_bonus_days(attendance_dates: set[date]) -> int:
    return sum(1 for entry_date in attendance_dates if entry_date in _RELIGIOUS_HOLIDAY_DOUBLE_DATES)


def _calculate_support_holiday_bonus(
    *,
    selected_month: str,
    cost_model: object,
    role: object,
    monthly_fixed_cost: float,
    start_date: object = None,
    attendance_dates: set[date],
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    if fixed_cost <= 0:
        return 0.0
    normalized_cost_model = str(cost_model or "").strip()
    normalized_role = str(role or "").strip()
    if (
        normalized_cost_model not in _SUPPORT_HOLIDAY_DOUBLE_COST_MODELS
        and normalized_role not in _SUPPORT_HOLIDAY_DOUBLE_ROLES
    ):
        return 0.0
    start_month_prefix = str(selected_month or "").strip()
    eligible_holiday_dates = [
        holiday_date for holiday_date in _RELIGIOUS_HOLIDAY_DOUBLE_DATES if holiday_date.isoformat().startswith(start_month_prefix)
    ]
    if not eligible_holiday_dates:
        return 0.0
    parsed_start_date = _parse_attendance_date(start_date)
    active_holiday_dates = [
        holiday_date
        for holiday_date in eligible_holiday_dates
        if parsed_start_date is None or parsed_start_date <= holiday_date
    ]
    if not active_holiday_dates:
        return 0.0
    bonus_days = len(active_holiday_dates)
    if attendance_dates:
        bonus_days = max(bonus_days, _count_support_holiday_bonus_days(attendance_dates))
    if bonus_days <= 0:
        return 0.0
    return _safe_float((fixed_cost / _SUPPORT_HOLIDAY_DAY_DIVISOR) * bonus_days)


def _is_fixed_cost_model(cost_model: object) -> bool:
    model = str(cost_model or "").strip()
    return model == "fixed_monthly" or model.startswith("fixed_")


def _calculate_personnel_gross_pay(
    *,
    selected_month: str,
    cost_model: object,
    role: object,
    monthly_fixed_cost: float,
    start_date: object = None,
    total_hours: float,
    total_packages: float,
    segments: list[dict[str, object]],
    attendance_dates: set[date] | None = None,
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    has_attendance = total_hours > 0 or total_packages > 0
    holiday_bonus = _calculate_support_holiday_bonus(
        selected_month=selected_month,
        cost_model=cost_model,
        role=role,
        monthly_fixed_cost=fixed_cost,
        start_date=start_date,
        attendance_dates=attendance_dates or set(),
    )
    if _is_fixed_cost_model(cost_model) and fixed_cost > 0:
        return fixed_cost + holiday_bonus
    if not has_attendance:
        return fixed_cost + holiday_bonus
    return _calculate_variable_courier_gross_cost(segments)


def build_payroll_status() -> PayrollModuleStatus:
    return PayrollModuleStatus(
        module="payroll",
        status="active",
        next_slice="payroll-dashboard",
    )


def _format_currency_pdf(value: float) -> str:
    amount = _safe_float(value)
    sign = "-" if amount < 0 else ""
    normalized = abs(amount)
    formatted = f"{normalized:,.2f}"
    whole, decimal = formatted.split(".")
    return f"{sign}{whole.replace(',', '.')},{decimal} ₺"


def _format_number_pdf(value: float, decimals: int = 0) -> str:
    normalized = _safe_float(value)
    formatted = f"{normalized:,.{decimals}f}"
    if decimals <= 0:
        return formatted.replace(",", ".")
    whole, decimal = formatted.split(".")
    return f"{whole.replace(',', '.')},{decimal}"


def _calculate_payroll_tevkifat_breakdown(invoice_total: float) -> PayrollTevkifatBreakdown:
    normalized_total = max(_safe_float(invoice_total), 0.0)
    if normalized_total <= 0:
        return PayrollTevkifatBreakdown(0.0, 0.0, 0.0)

    invoice_base_amount = normalized_total / (1 + _PAYROLL_VAT_RATE)
    vat_amount = normalized_total - invoice_base_amount
    tevkifat_amount = (
        vat_amount * _PAYROLL_TEVKIFAT_RATE
        if normalized_total >= _PAYROLL_TEVKIFAT_THRESHOLD
        else 0.0
    )
    return PayrollTevkifatBreakdown(
        invoice_base_amount=_safe_float(invoice_base_amount),
        vat_amount=_safe_float(vat_amount),
        tevkifat_amount=_safe_float(tevkifat_amount),
    )


def _deduction_reduces_invoice_base(deduction_type: object) -> bool:
    normalized_type = str(deduction_type or "").strip()
    if not normalized_type:
        return False
    return (
        normalized_type in _INVOICE_BASE_REDUCING_DEDUCTION_TYPES
        or is_motor_rental_deduction_type(normalized_type)
        or is_motor_purchase_deduction_type(normalized_type)
    )


def _apply_payroll_tevkifat_as_deduction(
    *,
    gross_pay: float,
    base_deductions: float,
    invoice_base_reducing_deductions: float,
) -> tuple[float, PayrollTevkifatBreakdown, float]:
    # Payroll net payment is computed after withholding is added as a real deduction line.
    normalized_gross = max(_safe_float(gross_pay), 0.0)
    normalized_base_deductions = max(_safe_float(base_deductions), 0.0)
    normalized_invoice_base_reducing_deductions = max(_safe_float(invoice_base_reducing_deductions), 0.0)
    invoice_total = max(normalized_gross - normalized_invoice_base_reducing_deductions, 0.0)
    tevkifat = _calculate_payroll_tevkifat_breakdown(invoice_total)
    total_deductions = normalized_base_deductions + tevkifat.tevkifat_amount
    net_payment = max(normalized_gross - total_deductions, 0.0)
    return total_deductions, tevkifat, net_payment


def _format_month_label(value: str) -> str:
    month_map = {
        "01": "Ocak",
        "02": "Şubat",
        "03": "Mart",
        "04": "Nisan",
        "05": "Mayıs",
        "06": "Haziran",
        "07": "Temmuz",
        "08": "Ağustos",
        "09": "Eylül",
        "10": "Ekim",
        "11": "Kasım",
        "12": "Aralık",
    }
    parts = str(value or "").split("-")
    if len(parts) != 2:
        return str(value or "-")
    year, month = parts
    return f"{month_map.get(month, month)} {year}"


def _payroll_template_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "templates"


def _read_payroll_template_file(file_name: str) -> str:
    return (_payroll_template_dir() / file_name).read_text(encoding="utf-8")


def _build_payroll_document_html(payload: PayrollDocumentPayload) -> str:
    from jinja2 import BaseLoader, Environment, select_autoescape

    def format_value(value: float, *, decimals: int = 1) -> str:
        normalized = _safe_float(value)
        return _format_number_pdf(normalized, decimals)

    def format_currency(value: float) -> str:
        return _format_currency_pdf(value)

    def negative_currency(value: float) -> str:
        formatted = format_currency(abs(_safe_float(value)))
        return f"-{formatted}"

    def initials(value: str) -> str:
        parts = [part for part in str(value or "").strip().split() if part]
        if not parts:
            return "CK"
        return "".join(part[0] for part in parts[:2]).upper()

    restaurant_names = [str(value).strip() for value in payload.restaurant_names if str(value).strip()]
    if not restaurant_names:
        restaurant_names = ["—"]
    restaurant_count = len(restaurant_names) if restaurant_names != ["—"] else 0

    deduction_rows = []
    for deduction_type, amount in payload.deduction_items:
        label = str(deduction_type or "—").strip() or "—"
        normalized_amount = _safe_float(amount)
        deduction_rows.append(
            {
                "label": label,
                "amount": negative_currency(normalized_amount),
            }
        )
    if not deduction_rows:
        deduction_rows = [{"label": "—", "amount": "—"}]

    environment = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(default_for_string=True, enabled_extensions=("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.from_string(_read_payroll_template_file("payroll_document.html.j2"))
    return template.render(
        period=_format_month_label(payload.selected_month),
        created_at=date.today().strftime("%d.%m.%Y"),
        courier_name=str(payload.personnel or "—"),
        courier_initials=initials(payload.personnel),
        courier_role=str(payload.role or "—"),
        courier_code=str(payload.person_code or "—"),
        courier_status=str(payload.status or "—"),
        total_hours=format_value(payload.total_hours, decimals=1),
        total_packages=format_value(payload.total_packages, decimals=0),
        total_branches=str(restaurant_count),
        net_payment=format_currency(payload.net_payment),
        gross_earning=format_currency(payload.gross_pay),
        total_deduction=format_currency(payload.total_deductions),
        invoice_base=format_currency(payload.invoice_base_amount),
        invoice_vat=format_currency(payload.invoice_vat_amount),
        tevkifat=format_currency(payload.tevkifat_amount),
        invoice_total=format_currency(payload.invoice_base_amount + payload.invoice_vat_amount),
        restaurants=restaurant_names,
        deduction_rows=deduction_rows,
    )


def _build_payroll_document_full_html(payload: PayrollDocumentPayload) -> str:
    html_output = _build_payroll_document_html(payload)
    css_output = _read_payroll_template_file("payroll_document.css")
    return html_output.replace("</head>", f"<style>{css_output}</style></head>", 1)


def _render_payroll_document_pdf(payload: PayrollDocumentPayload) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright PDF motoru kullanılamadı.") from exc

    html_output = _build_payroll_document_full_html(payload)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": 1240, "height": 1754},
                device_scale_factor=1,
            )
            page.set_content(html_output, wait_until="load")
            page.emulate_media(media="print")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
            return pdf_bytes
    except Exception as exc:
        raise RuntimeError("Hakediş PDF'i Playwright ile oluşturulamadı.") from exc


def _resolve_month_key(month_options: list[str], selected_month: str | None) -> str:
    if not month_options:
        raise ValueError("Belge oluşturmak için önce hakediş verisi oluşmalı.")
    return selected_month if selected_month in month_options else month_options[0]


def _fetch_payroll_month_options(conn: psycopg.Connection) -> tuple[list[str], list[str]]:
    attendance_rows = conn.execute(
        f"""
        SELECT DISTINCT {_month_key_sql('entry_date')} AS month_key
        FROM daily_entries
        WHERE COALESCE(CAST(entry_date AS TEXT), '') <> ''
        ORDER BY month_key DESC
        """
    ).fetchall()
    deduction_rows = conn.execute(
        f"""
        SELECT DISTINCT {_month_key_sql('deduction_date')} AS month_key
        FROM deductions
        WHERE COALESCE(CAST(deduction_date AS TEXT), '') <> ''
        ORDER BY month_key DESC
        """
    ).fetchall()
    attendance_month_options = [str(row["month_key"]) for row in attendance_rows if row["month_key"]]
    deduction_month_options = [str(row["month_key"]) for row in deduction_rows if row["month_key"]]
    month_options = sorted(set(attendance_month_options) | set(deduction_month_options), reverse=True)
    return month_options, attendance_month_options


def _resolve_payroll_dashboard_month(
    month_options: list[str],
    attendance_month_options: list[str],
    selected_month: str | None,
) -> str:
    if selected_month in month_options:
        return str(selected_month)
    if attendance_month_options:
        return attendance_month_options[0]
    return _resolve_month_key(month_options, selected_month)


def build_payroll_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None = None,
    role_filter: str | None = None,
    restaurant_filter: str | None = None,
    limit: int = 300,
) -> PayrollDashboardResponse:
    return _build_local_payroll_dashboard(
        conn,
        selected_month=selected_month,
        role_filter=role_filter,
        restaurant_filter=restaurant_filter,
        limit=limit,
    )


def build_payroll_document_file(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    personnel_id: int,
) -> tuple[str, bytes]:
    payload = _build_local_payroll_document_payload(
        conn,
        selected_month=selected_month,
        personnel_id=personnel_id,
    )
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", payload.personnel).strip("_") or f"personel_{payload.personnel_id}"
    file_name = f"hakedis_{safe_name}_{payload.selected_month}.pdf"
    return file_name, _render_payroll_document_pdf(payload)


def _build_remote_payroll_document_payload(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    personnel_id: int,
) -> PayrollDocumentPayload:
    _ensure_repo_root_on_path()
    from engines.finance_engine import calculate_personnel_cost
    from rules.deduction_rules import filter_payroll_effective_deductions_df
    from rules.reporting_rules import month_bounds
    from services.reporting_service import load_monthly_payroll_source_payload

    compat_conn = _build_compat_connection(conn)
    payload = load_monthly_payroll_source_payload(compat_conn)
    month_options = payload.month_options
    resolved_month = _resolve_month_key(month_options, selected_month)

    entries = payload.entries.copy() if not payload.entries.empty else pd.DataFrame()
    deductions = payload.deductions.copy() if not payload.deductions.empty else pd.DataFrame()
    personnel_df = payload.personnel_df.copy() if not payload.personnel_df.empty else pd.DataFrame()
    role_history_df = (
        payload.role_history_df.copy()
        if payload.role_history_df is not None and not payload.role_history_df.empty
        else pd.DataFrame()
    )

    start_date, end_date = month_bounds(resolved_month)
    month_entries = (
        entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy()
        if not entries.empty
        else pd.DataFrame()
    )
    month_deductions = (
        deductions[(deductions["deduction_date"] >= start_date) & (deductions["deduction_date"] <= end_date)].copy()
        if not deductions.empty
        else pd.DataFrame()
    )
    payroll_deductions = filter_payroll_effective_deductions_df(month_deductions, personnel_df)
    cost_df = calculate_personnel_cost(
        month_entries,
        personnel_df,
        payroll_deductions,
        role_history_df=role_history_df if not role_history_df.empty else None,
    )
    if cost_df.empty or "personnel_id" not in cost_df.columns:
        raise LookupError("Belgesi oluşturulacak personel için hakediş kaydı bulunamadı.")

    match_rows = cost_df[cost_df["personnel_id"] == personnel_id]
    if match_rows.empty:
        raise LookupError("Belgesi oluşturulacak personel için hakediş kaydı bulunamadı.")
    payroll_row = match_rows.iloc[0]

    person_match = personnel_df[personnel_df["id"] == personnel_id] if not personnel_df.empty else pd.DataFrame()
    person_code = str(person_match.iloc[0]["person_code"] or "") if not person_match.empty and "person_code" in person_match.columns else ""

    deduction_items: list[tuple[str, float]] = []
    if not payroll_deductions.empty:
        person_deductions = payroll_deductions[payroll_deductions["personnel_id"] == personnel_id].copy()
        if not person_deductions.empty:
            grouped = (
                person_deductions.groupby("deduction_type", dropna=False)["amount"]
                .sum()
                .reset_index()
            )
            deduction_items = [
                (str(row["deduction_type"] or "Kesinti"), _safe_float(row["amount"]))
                for _, row in grouped.iterrows()
            ]

    restaurant_names: list[str] = []
    if not month_entries.empty:
        personnel_match_mask = (
            month_entries["actual_personnel_id"].fillna(month_entries["planned_personnel_id"]) == personnel_id
        )
        rest_series = (
            month_entries.loc[personnel_match_mask, "brand"].fillna("").astype(str)
            + " - "
            + month_entries.loc[personnel_match_mask, "branch"].fillna("").astype(str)
        )
        restaurant_names = [value.strip(" -") for value in sorted(rest_series.unique().tolist()) if value.strip(" -")]

    attendance_dates = {
        parsed_date
        for entry_value in month_entries.loc[
            month_entries["actual_personnel_id"].fillna(month_entries["planned_personnel_id"]) == personnel_id, "entry_date"
        ].tolist()
        if (parsed_date := _parse_attendance_date(entry_value)) is not None
    }
    person_cost_model = (
        str(person_match.iloc[0]["cost_model"] or "")
        if not person_match.empty and "cost_model" in person_match.columns
        else ""
    )
    person_fixed_cost = (
        _safe_float(person_match.iloc[0]["monthly_fixed_cost"])
        if not person_match.empty and "monthly_fixed_cost" in person_match.columns
        else 0.0
    )
    gross_pay = _safe_float(payroll_row.get("brut_maliyet")) + _calculate_support_holiday_bonus(
        selected_month=resolved_month,
        cost_model=person_cost_model,
        role=payroll_row.get("rol"),
        monthly_fixed_cost=person_fixed_cost,
        start_date=person_match.iloc[0]["start_date"] if not person_match.empty and "start_date" in person_match.columns else None,
        attendance_dates=attendance_dates,
    )
    base_deductions = _safe_float(payroll_row.get("kesinti"))
    invoice_base_reducing_deductions = _safe_float(
        sum(
            amount
            for deduction_type, amount in deduction_items
            if _deduction_reduces_invoice_base(deduction_type)
        )
    )
    total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
        gross_pay=gross_pay,
        base_deductions=base_deductions,
        invoice_base_reducing_deductions=invoice_base_reducing_deductions,
    )
    if tevkifat.tevkifat_amount > 0:
        deduction_items.append(("Tevkifat", tevkifat.tevkifat_amount))

    return PayrollDocumentPayload(
        selected_month=resolved_month,
        personnel_id=personnel_id,
        personnel=str(payroll_row.get("personel") or "-"),
        person_code=person_code,
        role=str(payroll_row.get("rol") or "-"),
        status=str(payroll_row.get("durum") or "-"),
        total_hours=_safe_float(payroll_row.get("calisma_saati")),
        total_packages=_safe_float(payroll_row.get("paket")),
        gross_pay=gross_pay,
        total_deductions=total_deductions,
        net_payment=net_payment,
        invoice_base_amount=tevkifat.invoice_base_amount,
        invoice_vat_amount=tevkifat.vat_amount,
        tevkifat_amount=tevkifat.tevkifat_amount,
        restaurant_names=restaurant_names,
        deduction_items=deduction_items,
    )


def _build_local_payroll_document_payload(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    personnel_id: int,
) -> PayrollDocumentPayload:
    month_options, attendance_month_options = _fetch_payroll_month_options(conn)
    resolved_month = _resolve_payroll_dashboard_month(month_options, attendance_month_options, selected_month)

    person_row = conn.execute(
        """
        SELECT
            id,
            COALESCE(full_name, '-') AS full_name,
            COALESCE(person_code, '') AS person_code,
            COALESCE(role, '-') AS role,
            COALESCE(status, '-') AS status,
            COALESCE(cost_model, '-') AS cost_model,
            COALESCE(monthly_fixed_cost, 0) AS monthly_fixed_cost,
            start_date,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, 'Hayır') AS motor_rental,
            COALESCE(motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            motor_purchase_start_date,
            COALESCE(motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction
        FROM personnel
        WHERE id = %s
        """,
        (personnel_id,),
    ).fetchone()
    if person_row is None:
        raise LookupError("Belgesi oluşturulacak personel bulunamadı.")
    person_data = dict(person_row)

    attendance_rows = conn.execute(
        f"""
        SELECT
            d.restaurant_id,
            COALESCE(r.brand, '') AS brand,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
        GROUP BY
            d.restaurant_id,
            COALESCE(r.brand, '')
        """,
        (resolved_month, personnel_id),
    ).fetchall()

    deduction_rows = conn.execute(
        f"""
        SELECT
            COALESCE(deduction_type, 'Kesinti') AS deduction_type,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id = %s
          AND COALESCE(deduction_type, '') NOT IN {_PAYROLL_IGNORED_DEDUCTION_SQL}
        GROUP BY COALESCE(deduction_type, 'Kesinti')
        ORDER BY deduction_type
        """,
        (resolved_month, personnel_id),
    ).fetchall()

    restaurant_rows = conn.execute(
        f"""
        SELECT DISTINCT COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
        ORDER BY restaurant_label
        """,
        (resolved_month, personnel_id),
    ).fetchall()
    attendance_date_rows = conn.execute(
        f"""
        SELECT DISTINCT substr(COALESCE(d.entry_date, ''), 1, 10) AS entry_date
        FROM daily_entries d
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
        """,
        (resolved_month, personnel_id),
    ).fetchall()

    attendance_segments = [
        {
            "brand": str(row["brand"] or ""),
            "total_hours": _safe_float(row["total_hours"]),
            "total_packages": _safe_float(row["total_packages"]),
        }
        for row in attendance_rows
    ]
    total_hours = _safe_float(sum(_safe_float(row["total_hours"]) for row in attendance_rows))
    total_packages = _safe_float(sum(_safe_float(row["total_packages"]) for row in attendance_rows))
    gross_pay = _calculate_personnel_gross_pay(
        selected_month=resolved_month,
        cost_model=person_data["cost_model"],
        role=person_data["role"],
        monthly_fixed_cost=_safe_float(person_data["monthly_fixed_cost"]),
        start_date=person_data.get("start_date"),
        total_hours=total_hours,
        total_packages=total_packages,
        segments=attendance_segments,
        attendance_dates={
            parsed_date
            for row in attendance_date_rows
            if (parsed_date := _parse_attendance_date(row["entry_date"])) is not None
        },
    )
    base_deductions = _safe_float(sum(_safe_float(row["total_amount"]) for row in deduction_rows))
    invoice_base_reducing_deductions = _safe_float(
        sum(
            _safe_float(row["total_amount"])
            for row in deduction_rows
            if _deduction_reduces_invoice_base(row["deduction_type"])
        )
    )
    existing_motor_rental = sum(
        _safe_float(row["total_amount"])
        for row in deduction_rows
        if is_motor_rental_deduction_type(row["deduction_type"])
    )
    existing_motor_purchase = sum(
        _safe_float(row["total_amount"])
        for row in deduction_rows
        if is_motor_purchase_deduction_type(row["deduction_type"])
    )
    auto_motor_rental = calculate_company_motor_rental_deduction(
        person_data,
        resolved_month,
        existing_amount=existing_motor_rental,
    )
    auto_motor_purchase = calculate_company_motor_purchase_deduction(
        person_data,
        resolved_month,
        existing_amount=existing_motor_purchase,
    )
    base_deductions += auto_motor_rental
    base_deductions += auto_motor_purchase
    invoice_base_reducing_deductions += auto_motor_rental
    invoice_base_reducing_deductions += auto_motor_purchase
    total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
        gross_pay=gross_pay,
        base_deductions=base_deductions,
        invoice_base_reducing_deductions=invoice_base_reducing_deductions,
    )
    restaurant_names = [str(row["restaurant_label"]) for row in restaurant_rows if str(row["restaurant_label"]).strip()]
    deduction_items = [(str(row["deduction_type"]), _safe_float(row["total_amount"])) for row in deduction_rows]
    if auto_motor_rental > 0:
        deduction_items.append((MOTOR_RENTAL_DEDUCTION_TYPE, auto_motor_rental))
    if auto_motor_purchase > 0:
        deduction_items.append((MOTOR_PURCHASE_DEDUCTION_TYPE, auto_motor_purchase))
    if tevkifat.tevkifat_amount > 0:
        deduction_items.append(("Tevkifat", tevkifat.tevkifat_amount))

    return PayrollDocumentPayload(
        selected_month=resolved_month,
        personnel_id=personnel_id,
        personnel=str(person_data["full_name"] or "-"),
        person_code=str(person_data["person_code"] or ""),
        role=str(person_data["role"] or "-"),
        status=str(person_data["status"] or "-"),
        total_hours=total_hours,
        total_packages=total_packages,
        gross_pay=gross_pay,
        total_deductions=total_deductions,
        net_payment=net_payment,
        invoice_base_amount=tevkifat.invoice_base_amount,
        invoice_vat_amount=tevkifat.vat_amount,
        tevkifat_amount=tevkifat.tevkifat_amount,
        restaurant_names=restaurant_names,
        deduction_items=deduction_items,
    )


def _build_local_payroll_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    role_filter: str | None,
    restaurant_filter: str | None,
    limit: int,
) -> PayrollDashboardResponse:
    month_options, attendance_month_options = _fetch_payroll_month_options(conn)
    if not month_options:
        return PayrollDashboardResponse(
            module="payroll",
            status="active",
            month_options=[],
            selected_month=None,
            role_options=[],
            restaurant_options=[],
            selected_role="Tümü",
            selected_restaurant="Tümü",
            summary=None,
            entries=[],
            cost_model_breakdown=[],
            role_breakdown=[],
            top_personnel=[],
        )

    resolved_month = _resolve_payroll_dashboard_month(month_options, attendance_month_options, selected_month)
    selected_role = role_filter or "Tümü"
    selected_restaurant = restaurant_filter or "Tümü"

    role_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(role, '-') AS role
        FROM personnel
        WHERE COALESCE(role, '') <> ''
        ORDER BY role
        """
    ).fetchall()
    role_options = ["Tümü", *[str(row["role"]) for row in role_rows if row["role"]]]
    role_options = list(dict.fromkeys(role_options))
    if selected_role not in role_options:
        selected_role = "Tümü"

    restaurant_rows = conn.execute(
        f"""
        SELECT DISTINCT COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
        ORDER BY restaurant_label
        """,
        (resolved_month,),
    ).fetchall()
    restaurant_options = ["Tümü", *[str(row["restaurant_label"]) for row in restaurant_rows if row["restaurant_label"]]]
    restaurant_options = list(dict.fromkeys(restaurant_options))
    if selected_restaurant not in restaurant_options:
        selected_restaurant = "Tümü"

    attendance_query = """
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            d.restaurant_id,
            COALESCE(r.brand, '') AS brand,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {month_key_sql} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
    """.format(month_key_sql=_month_key_sql("d.entry_date"))
    attendance_params: list[object] = [resolved_month]
    if selected_restaurant != "Tümü":
        attendance_query += """
          AND COALESCE(r.brand || ' - ' || r.branch, '-') = %s
        """
        attendance_params.append(selected_restaurant)
    attendance_query += """
        GROUP BY
            COALESCE(d.actual_personnel_id, d.planned_personnel_id),
            d.restaurant_id,
            COALESCE(r.brand, '')
    """
    attendance_rows = conn.execute(attendance_query, tuple(attendance_params)).fetchall()
    attendance_date_rows = conn.execute(
        """
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            substr(COALESCE(d.entry_date, ''), 1, 10) AS entry_date
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {month_key_sql} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
        {restaurant_filter_clause}
        GROUP BY
            COALESCE(d.actual_personnel_id, d.planned_personnel_id),
            substr(COALESCE(d.entry_date, ''), 1, 10)
        """.format(
            month_key_sql=_month_key_sql("d.entry_date"),
            restaurant_filter_clause="" if selected_restaurant == "Tümü" else "AND COALESCE(r.brand || ' - ' || r.branch, '-') = %s",
        ),
        tuple(attendance_params),
    ).fetchall()

    deduction_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(deduction_type, 'Kesinti') AS deduction_type,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') NOT IN {_PAYROLL_IGNORED_DEDUCTION_SQL}
        GROUP BY personnel_id, COALESCE(deduction_type, 'Kesinti')
        """,
        (resolved_month,),
    ).fetchall()
    existing_motor_rental_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_motor_rental
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') IN {_MOTOR_RENTAL_DEDUCTION_SQL}
        GROUP BY personnel_id
        """,
        (resolved_month,),
    ).fetchall()

    personnel_rows = conn.execute(
        """
        SELECT
            id,
            COALESCE(full_name, '-') AS full_name,
            COALESCE(role, '-') AS role,
            COALESCE(status, '-') AS status,
            COALESCE(cost_model, '-') AS cost_model,
            COALESCE(monthly_fixed_cost, 0) AS monthly_fixed_cost,
            start_date,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, 'Hayır') AS motor_rental,
            COALESCE(motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            motor_purchase_start_date,
            COALESCE(motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction
        FROM personnel
        """
    ).fetchall()

    attendance_by_person: dict[int, dict[str, object]] = {}
    for row in attendance_rows:
        if row["personnel_id"] is None:
            continue
        person_id = int(row["personnel_id"])
        bucket = attendance_by_person.setdefault(
            person_id,
            {
                "total_hours": 0.0,
                "total_packages": 0.0,
                "restaurant_ids": set(),
                "segments": [],
            },
        )
        total_hours = _safe_float(row["total_hours"])
        total_packages = _safe_float(row["total_packages"])
        bucket["total_hours"] = _safe_float(bucket.get("total_hours")) + total_hours
        bucket["total_packages"] = _safe_float(bucket.get("total_packages")) + total_packages
        restaurant_ids = bucket["restaurant_ids"]
        if isinstance(restaurant_ids, set) and row["restaurant_id"] is not None:
            restaurant_ids.add(int(row["restaurant_id"]))
        segments = bucket["segments"]
        if isinstance(segments, list):
            segments.append(
                {
                    "brand": str(row["brand"] or ""),
                    "total_hours": total_hours,
                    "total_packages": total_packages,
                }
            )
    for bucket in attendance_by_person.values():
        restaurant_ids = bucket.get("restaurant_ids")
        bucket["restaurant_count"] = len(restaurant_ids) if isinstance(restaurant_ids, set) else 0
        bucket.pop("restaurant_ids", None)
    attendance_dates_by_person: dict[int, set[date]] = {}
    for row in attendance_date_rows:
        if row["personnel_id"] is None:
            continue
        parsed_date = _parse_attendance_date(row["entry_date"])
        if parsed_date is None:
            continue
        attendance_dates_by_person.setdefault(int(row["personnel_id"]), set()).add(parsed_date)
    deductions_by_person: dict[int, float] = {}
    invoice_base_reducing_deductions_by_person: dict[int, float] = {}
    for row in deduction_rows:
        if row["personnel_id"] is None:
            continue
        person_id = int(row["personnel_id"])
        amount = _safe_float(row["total_amount"])
        deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + amount
        if _deduction_reduces_invoice_base(row["deduction_type"]):
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + amount
            )
    existing_motor_rental_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_motor_rental"])
        for row in existing_motor_rental_rows
        if row["personnel_id"] is not None
    }
    existing_motor_purchase_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_motor_purchase
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') IN {_MOTOR_PURCHASE_DEDUCTION_SQL}
        GROUP BY personnel_id
        """,
        (resolved_month,),
    ).fetchall()
    existing_motor_purchase_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_motor_purchase"])
        for row in existing_motor_purchase_rows
        if row["personnel_id"] is not None
    }

    personnel_index = {int(row["id"]): row for row in personnel_rows if row["id"] is not None}
    auto_motor_rental_by_person: dict[int, float] = {}
    auto_motor_purchase_by_person: dict[int, float] = {}
    for person_id, person in personnel_index.items():
        auto_motor_rental = calculate_company_motor_rental_deduction(
            dict(person),
            resolved_month,
            existing_amount=existing_motor_rental_by_person.get(person_id, 0.0),
        )
        if auto_motor_rental > 0:
            auto_motor_rental_by_person[person_id] = auto_motor_rental
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_rental
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + auto_motor_rental
            )
        auto_motor_purchase = calculate_company_motor_purchase_deduction(
            dict(person),
            resolved_month,
            existing_amount=existing_motor_purchase_by_person.get(person_id, 0.0),
        )
        if auto_motor_purchase > 0:
            auto_motor_purchase_by_person[person_id] = auto_motor_purchase
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_purchase
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + auto_motor_purchase
            )

    relevant_personnel_ids = sorted(
        set(attendance_by_person)
        | set(deductions_by_person)
        | set(auto_motor_rental_by_person)
        | set(auto_motor_purchase_by_person)
    )

    entries_payload: list[PayrollEntry] = []
    for person_id in relevant_personnel_ids:
        person = personnel_index.get(person_id)
        if person is None:
            continue
        role = str(person["role"] or "-")
        if selected_role != "Tümü" and role != selected_role:
            continue

        attendance = attendance_by_person.get(person_id, {})
        total_hours = _safe_float(attendance.get("total_hours"))
        total_packages = _safe_float(attendance.get("total_packages"))
        restaurant_count = int(attendance.get("restaurant_count") or 0)
        segments = attendance.get("segments")
        gross_pay = _calculate_personnel_gross_pay(
            selected_month=resolved_month,
            cost_model=person["cost_model"],
            role=person["role"],
            monthly_fixed_cost=_safe_float(person["monthly_fixed_cost"]),
            start_date=person["start_date"],
            total_hours=total_hours,
            total_packages=total_packages,
            segments=segments if isinstance(segments, list) else [],
            attendance_dates=attendance_dates_by_person.get(person_id, set()),
        )
        base_deductions = _safe_float(deductions_by_person.get(person_id))
        invoice_base_reducing_deductions = _safe_float(invoice_base_reducing_deductions_by_person.get(person_id))
        total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
            gross_pay=gross_pay,
            base_deductions=base_deductions,
            invoice_base_reducing_deductions=invoice_base_reducing_deductions,
        )
        cost_model_key = str(person["cost_model"] or "-")

        entries_payload.append(
            PayrollEntry(
                personnel_id=person_id,
                personnel=str(person["full_name"] or "-"),
                role=role,
                status=str(person["status"] or "-"),
                total_hours=total_hours,
                total_packages=total_packages,
                gross_pay=gross_pay,
                total_deductions=total_deductions,
                tevkifat_amount=tevkifat.tevkifat_amount,
                net_payment=net_payment,
                restaurant_count=restaurant_count,
                cost_model=_COST_MODEL_LABELS.get(cost_model_key, cost_model_key),
            )
        )

    entries_payload.sort(key=lambda row: (-row.net_payment, row.personnel))
    entries_payload = entries_payload[:limit]

    cost_model_breakdown: list[PayrollCostModelBreakdownEntry] = []
    if entries_payload:
        grouped_entries: dict[str, dict[str, float | int]] = {}
        for entry in entries_payload:
            bucket = grouped_entries.setdefault(
                entry.cost_model,
                {
                    "personnel_count": 0,
                    "total_hours": 0.0,
                    "total_packages": 0.0,
                    "net_payment": 0.0,
                },
            )
            bucket["personnel_count"] = int(bucket["personnel_count"]) + 1
            bucket["total_hours"] = float(bucket["total_hours"]) + entry.total_hours
            bucket["total_packages"] = float(bucket["total_packages"]) + entry.total_packages
            bucket["net_payment"] = float(bucket["net_payment"]) + entry.net_payment

        cost_model_breakdown = [
            PayrollCostModelBreakdownEntry(
                cost_model=cost_model,
                personnel_count=int(values["personnel_count"]),
                total_hours=float(values["total_hours"]),
                total_packages=float(values["total_packages"]),
                net_payment=float(values["net_payment"]),
            )
            for cost_model, values in sorted(
                grouped_entries.items(),
                key=lambda item: float(item[1]["net_payment"]),
                reverse=True,
            )
        ]

    role_breakdown: list[PayrollRoleBreakdownEntry] = []
    if entries_payload:
        grouped_roles: dict[str, dict[str, float | int]] = {}
        for entry in entries_payload:
            bucket = grouped_roles.setdefault(
                entry.role,
                {
                    "personnel_count": 0,
                    "total_hours": 0.0,
                    "total_packages": 0.0,
                    "net_payment": 0.0,
                },
            )
            bucket["personnel_count"] = int(bucket["personnel_count"]) + 1
            bucket["total_hours"] = float(bucket["total_hours"]) + entry.total_hours
            bucket["total_packages"] = float(bucket["total_packages"]) + entry.total_packages
            bucket["net_payment"] = float(bucket["net_payment"]) + entry.net_payment

        role_breakdown = [
            PayrollRoleBreakdownEntry(
                role=role,
                personnel_count=int(values["personnel_count"]),
                total_hours=float(values["total_hours"]),
                total_packages=float(values["total_packages"]),
                net_payment=float(values["net_payment"]),
            )
            for role, values in sorted(
                grouped_roles.items(),
                key=lambda item: float(item[1]["net_payment"]),
                reverse=True,
            )
        ]

    top_personnel = [
        PayrollTopPersonnelEntry(
            personnel_id=entry.personnel_id,
            personnel=entry.personnel,
            role=entry.role,
            total_hours=entry.total_hours,
            total_packages=entry.total_packages,
            total_deductions=entry.total_deductions,
            net_payment=entry.net_payment,
            restaurant_count=entry.restaurant_count,
            cost_model=entry.cost_model,
        )
        for entry in entries_payload[:8]
    ]

    summary = None
    if entries_payload:
        summary = PayrollSummary(
            selected_month=resolved_month,
            personnel_count=len(entries_payload),
            total_hours=_safe_float(sum(entry.total_hours for entry in entries_payload)),
            total_packages=_safe_float(sum(entry.total_packages for entry in entries_payload)),
            gross_payroll=_safe_float(sum(entry.gross_pay for entry in entries_payload)),
            total_deductions=_safe_float(sum(entry.total_deductions for entry in entries_payload)),
            total_tevkifat=_safe_float(sum(entry.tevkifat_amount for entry in entries_payload)),
            net_payment=_safe_float(sum(entry.net_payment for entry in entries_payload)),
        )

    return PayrollDashboardResponse(
        module="payroll",
        status="active",
        month_options=month_options,
        selected_month=resolved_month,
        role_options=role_options,
        restaurant_options=restaurant_options,
        selected_role=selected_role,
        selected_restaurant=selected_restaurant,
        summary=summary,
        entries=entries_payload,
        cost_model_breakdown=cost_model_breakdown,
        role_breakdown=role_breakdown,
        top_personnel=top_personnel,
    )
