from __future__ import annotations

from calendar import monthrange
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
    calculate_company_motor_purchase_deduction_from_history,
    calculate_company_motor_rental_deduction,
    calculate_company_motor_rental_deduction_from_history,
    is_motor_purchase_deduction_type,
    is_motor_rental_deduction_type,
)
from app.schemas.payroll import (
    PayrollCostModelBreakdownEntry,
    PayrollDashboardResponse,
    PayrollDeductionItem,
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


def _table_columns(conn: psycopg.Connection, table_name: str) -> set[str]:
    if is_sqlite_backend(conn):
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
        """,
        (table_name,),
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def _coalesced_history_date_sql(date_column: str, changed_at_column: str) -> str:
    return (
        f"COALESCE(NULLIF(CAST({date_column} AS TEXT), ''), "
        f"SUBSTR(CAST({changed_at_column} AS TEXT), 1, 10))"
    )


def _fetch_vehicle_history_rows_by_person_for_month(
    conn: psycopg.Connection,
    *,
    personnel_ids: list[int],
    selected_month: str,
) -> dict[int, list[dict[str, object]]]:
    if not personnel_ids or not _table_columns(conn, "personnel_vehicle_history"):
        return {}

    year_text, month_text = str(selected_month).split("-", 1)
    month_end = f"{int(year_text):04d}-{int(month_text):02d}-{monthrange(int(year_text), int(month_text))[1]:02d}"
    resolved_effective_date_sql = _coalesced_history_date_sql(
        "effective_date",
        "changed_at",
    )
    placeholders = ", ".join(["%s"] * len(personnel_ids))
    rows = conn.execute(
        f"""
        SELECT
            id,
            personnel_id,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, 'Hayır') AS motor_rental,
            COALESCE(motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            motor_purchase_start_date,
            COALESCE(motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            {resolved_effective_date_sql} AS effective_date,
            changed_at
        FROM personnel_vehicle_history
        WHERE personnel_id IN ({placeholders})
          AND {resolved_effective_date_sql} <= %s
        ORDER BY personnel_id, {resolved_effective_date_sql}, id
        """,
        (*personnel_ids, month_end),
    ).fetchall()
    history_by_person: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        if row["personnel_id"] is None:
            continue
        history_by_person.setdefault(int(row["personnel_id"]), []).append(dict(row))
    return history_by_person


def _fetch_vehicle_history_person_ids(conn: psycopg.Connection) -> set[int]:
    if not _table_columns(conn, "personnel_vehicle_history"):
        return set()
    rows = conn.execute(
        """
        SELECT DISTINCT personnel_id
        FROM personnel_vehicle_history
        WHERE personnel_id IS NOT NULL
        """
    ).fetchall()
    return {int(row["personnel_id"]) for row in rows if row["personnel_id"] is not None}


def _payroll_optional_personnel_select(conn: psycopg.Connection) -> str:
    columns = _table_columns(conn, "personnel")
    optional_fields = []
    if "exit_date" in columns:
        optional_fields.append("exit_date")
    else:
        optional_fields.append("NULL AS exit_date")
    for column_name in (
        "accounting_revenue",
        "accountant_cost",
        "company_setup_revenue",
        "company_setup_cost",
        "accounting_effective_date",
        "company_setup_effective_date",
    ):
        if column_name in columns:
            if column_name.endswith("_date"):
                optional_fields.append(f"{column_name}")
            else:
                optional_fields.append(f"COALESCE({column_name}, 0) AS {column_name}")
        else:
            optional_fields.append(f"{'NULL' if column_name.endswith('_date') else '0'} AS {column_name}")
    return ",\n            ".join(optional_fields)


def _row_value(source: object, key: str) -> object:
    if source is None:
        return None
    getter = getattr(source, "get", None)
    if callable(getter):
        try:
            return getter(key)
        except Exception:
            pass
    try:
        return source[key]  # type: ignore[index]
    except Exception:
        return None


def _parse_date_value(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def _selected_month_end(selected_month: str) -> date:
    year_text, month_text = str(selected_month).split("-", 1)
    year = int(year_text)
    month = int(month_text)
    last_day = monthrange(year, month)[1]
    return date(year, month, last_day)


def _fetch_effective_accounting_history_for_month(
    conn: psycopg.Connection,
    *,
    selected_month: str,
) -> dict[int, dict]:
    if not _table_columns(conn, "personnel_accounting_history"):
        return {}
    month_end = _selected_month_end(selected_month)
    rows = conn.execute(
        """
        SELECT
            id,
            personnel_id,
            accounting_type,
            new_company_setup,
            accounting_revenue,
            accountant_cost,
            company_setup_revenue,
            company_setup_cost,
            accounting_effective_date,
            company_setup_effective_date,
            effective_date,
            changed_at,
            notes
        FROM personnel_accounting_history
        """
    ).fetchall()
    latest_by_person: dict[int, tuple[date, int, dict]] = {}
    for row in rows:
        person_id = _row_value(row, "personnel_id")
        if person_id is None:
            continue
        effective_date = _parse_date_value(_row_value(row, "effective_date")) or _parse_date_value(_row_value(row, "changed_at"))
        if effective_date is None or effective_date > month_end:
            continue
        payload = dict(row)
        key = (effective_date, int(_row_value(row, "id") or 0), payload)
        existing = latest_by_person.get(int(person_id))
        if existing is None or (effective_date, int(_row_value(row, "id") or 0)) > (existing[0], existing[1]):
            latest_by_person[int(person_id)] = key
    return {person_id: item[2] for person_id, item in latest_by_person.items()}


def _fetch_accounting_history_person_ids(conn: psycopg.Connection) -> set[int]:
    if not _table_columns(conn, "personnel_accounting_history"):
        return set()
    rows = conn.execute(
        """
        SELECT DISTINCT personnel_id
        FROM personnel_accounting_history
        WHERE personnel_id IS NOT NULL
        """
    ).fetchall()
    return {int(row["personnel_id"]) for row in rows if row["personnel_id"] is not None}


def _build_personnel_profile_deduction_items(source: object, *, selected_month: str) -> list[tuple[str, float]]:
    items: list[tuple[str, float]] = []
    month_end = _selected_month_end(selected_month)
    accounting_effective_date = _parse_date_value(_row_value(source, "accounting_effective_date"))
    company_setup_effective_date = _parse_date_value(_row_value(source, "company_setup_effective_date"))
    accounting_revenue = _safe_float(_row_value(source, "accounting_revenue"))
    company_setup_revenue = _safe_float(_row_value(source, "company_setup_revenue"))
    accounting_type = _row_value(source, "accounting_type")
    new_company_setup = _row_value(source, "new_company_setup")
    if (
        (accounting_type is None or str(accounting_type) == "Çat Kapında Muhasebe")
        and accounting_revenue > 0
        and (accounting_effective_date is None or accounting_effective_date <= month_end)
    ):
        items.append((_ACCOUNTANT_COST_DEDUCTION_TYPE, accounting_revenue))
    if (
        (new_company_setup is None or str(new_company_setup) == "Evet")
        and company_setup_revenue > 0
        and (company_setup_effective_date is None or company_setup_effective_date <= month_end)
    ):
        items.append((_COMPANY_SETUP_COST_DEDUCTION_TYPE, company_setup_revenue))
    return items


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
_FIXED_MONTHLY_BRAND_KEYS = {"sushi inn", "sushiinn", "sc petshop", "sc pet shop"}
_FIXED_MONTHLY_BRAND_COURIER_PAY = 73600.0
_PAYROLL_VAT_RATE = 0.20
_PAYROLL_TEVKIFAT_RATE = 0.20
_PAYROLL_TEVKIFAT_THRESHOLD = 12000.0
_SUPPORT_HOLIDAY_DAY_DIVISOR = 30.0
_PAYROLL_IGNORED_DEDUCTION_SQL = "('Partner Kart Indirimi', 'Partner Kart İndirimi')"
_ACCOUNTANT_COST_DEDUCTION_TYPE = "Muhasebe Kesintisi"
_COMPANY_SETUP_COST_DEDUCTION_TYPE = "Şirket Açılışı Kesintisi"
_CAPTAIN_BONUS_LABEL = "Kaptanlık Hakedişi"
_CAPTAIN_BONUS_AMOUNT = 3000.0
_FIXED_MONTHLY_OVERTIME_BONUS_LABEL = "Ek Mesai Hakedişi"
_FIXED_MONTHLY_BASE_HOURS = 260.0
_FIXED_MONTHLY_EXTRA_DAY_HOURS = 10.0
_MOTOR_RENTAL_DEDUCTION_SQL = "('Motor Kirası', 'Motor Kirasi')"
_MOTOR_PURCHASE_DEDUCTION_SQL = "('Motor Satış Taksiti', 'Motor Satis Taksiti', 'Motor Satın Alım', 'Motor Satin Alim')"
_INVOICE_BASE_REDUCING_DEDUCTION_TYPES = {"Fatura Edilmeyen Tutar"}
_SUPPORT_HOLIDAY_DOUBLE_COST_MODELS = {
    "fixed_joker",
    "fixed_bolge_muduru",
    "fixed_restoran_takim_sefi",
}
_SUPPORT_HOLIDAY_DOUBLE_ROLES = {
    "Joker",
    "Bölge Müdürü",
    "Bolge Muduru",
    "Takım Şefi",
    "Takim Sefi",
    "Restoran Takım Şefi",
    "Restoran Takim Sefi",
}
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
    earning_items: list[tuple[str, float]]
    deduction_items: list[tuple[str, float]]


def _normalized_brand_key(brand: object) -> str:
    return str(brand or "").strip().lower()


def _is_quick_china_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) == "quick china"


def _is_dogu_otomotiv_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) in {"doğu otomotiv", "dogu otomotiv"}


def _is_fixed_monthly_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) in _FIXED_MONTHLY_BRAND_KEYS


def _is_fixed_monthly_courier_cost_model(cost_model: object) -> bool:
    return str(cost_model or "").strip() in {"fixed_monthly", "fixed_kurye"}


def _has_only_fixed_monthly_brand_segments(segments: list[dict[str, object]]) -> bool:
    primary_segments = [segment for segment in segments if not bool(segment.get("is_support_assignment"))]
    if not primary_segments:
        return False
    return all(_is_fixed_monthly_brand(segment.get("brand")) for segment in primary_segments)


def _uses_fixed_monthly_brand_courier_pay(
    *,
    role: object,
    cost_model: object,
    fixed_cost: float,
    segments: list[dict[str, object]],
) -> bool:
    if str(role or "").strip() != "Kurye":
        return False
    if _safe_float(fixed_cost) <= 0:
        return False
    return _is_fixed_monthly_courier_cost_model(cost_model) or _has_only_fixed_monthly_brand_segments(segments)


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
    gross_cost = 0.0
    standard_threshold_packages = _safe_float(
        sum(
            _safe_float(segment.get("total_packages"))
            for segment in segments
            if not _is_dogu_otomotiv_brand(segment.get("brand"))
            and not _is_quick_china_brand(segment.get("brand"))
            and not _is_fixed_monthly_brand(segment.get("brand"))
        )
    )
    standard_package_rate = (
        _COURIER_PACKAGE_COST_DEFAULT_HIGH
        if standard_threshold_packages > float(_PACKAGE_THRESHOLD_DEFAULT)
        else _COURIER_PACKAGE_COST_DEFAULT_LOW
    )

    for segment in segments:
        brand = segment.get("brand")
        total_hours = _safe_float(segment.get("total_hours"))
        total_packages = _safe_float(segment.get("total_packages"))
        restaurant_total_packages = _safe_float(segment.get("restaurant_total_packages", total_packages))
        support_day_count = max(int(segment.get("support_day_count") or 0), 0)
        is_support_assignment = bool(segment.get("is_support_assignment"))

        if _is_dogu_otomotiv_brand(brand):
            gross_cost += total_hours * _COURIER_HOURLY_COST_DOGU_OTOMOTIV
            continue

        if _is_fixed_monthly_brand(brand) and is_support_assignment and support_day_count > 0:
            gross_cost += (_FIXED_MONTHLY_BRAND_COURIER_PAY / _SUPPORT_HOLIDAY_DAY_DIVISOR) * support_day_count
            continue

        gross_cost += total_hours * _COURIER_HOURLY_COST
        if _is_quick_china_brand(brand):
            gross_cost += total_packages * _COURIER_PACKAGE_COST_QC
        else:
            gross_cost += total_packages * standard_package_rate

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


def _build_personnel_earning_items(
    *,
    role: object,
    cost_model: object = None,
    total_hours: float = 0.0,
    fixed_cost: float = 0.0,
    segments: list[dict[str, object]] | None = None,
) -> list[tuple[str, float]]:
    items: list[tuple[str, float]] = []
    normalized_role = str(role or "").strip()
    if normalized_role == "Kaptan":
        items.append((_CAPTAIN_BONUS_LABEL, _CAPTAIN_BONUS_AMOUNT))

    if _uses_fixed_monthly_brand_courier_pay(
        role=role,
        cost_model=cost_model,
        fixed_cost=fixed_cost,
        segments=segments or [],
    ):
        overtime_hours = max(_safe_float(total_hours) - _FIXED_MONTHLY_BASE_HOURS, 0.0)
        extra_days = int(overtime_hours // _FIXED_MONTHLY_EXTRA_DAY_HOURS)
        if extra_days > 0:
            items.append(
                (
                    _FIXED_MONTHLY_OVERTIME_BONUS_LABEL,
                    _safe_float(fixed_cost) / _SUPPORT_HOLIDAY_DAY_DIVISOR * extra_days,
                )
            )
    return items


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


def _resolve_fixed_monthly_courier_pay(
    *,
    role: object = None,
    cost_model: object,
    monthly_fixed_cost: float,
    segments: list[dict[str, object]],
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    if fixed_cost > 0:
        return fixed_cost
    if str(role or "").strip() != "Kurye":
        return fixed_cost
    if not _is_fixed_monthly_courier_cost_model(cost_model) and not _has_only_fixed_monthly_brand_segments(segments):
        return fixed_cost

    for segment in segments:
        if bool(segment.get("is_support_assignment")):
            continue
        if _is_fixed_monthly_brand(segment.get("brand")):
            return _FIXED_MONTHLY_BRAND_COURIER_PAY
    return fixed_cost


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
    fixed_cost = _resolve_fixed_monthly_courier_pay(
        role=role,
        cost_model=cost_model,
        monthly_fixed_cost=monthly_fixed_cost,
        segments=segments,
    )
    earning_item_total = _safe_float(
        sum(
            amount
            for _, amount in _build_personnel_earning_items(
                role=role,
                cost_model=cost_model,
                total_hours=total_hours,
                fixed_cost=fixed_cost,
                segments=segments,
            )
        )
    )
    has_attendance = total_hours > 0 or total_packages > 0
    holiday_bonus = _calculate_support_holiday_bonus(
        selected_month=selected_month,
        cost_model=cost_model,
        role=role,
        monthly_fixed_cost=fixed_cost,
        start_date=start_date,
        attendance_dates=attendance_dates or set(),
    )
    if _uses_fixed_monthly_brand_courier_pay(
        role=role,
        cost_model=cost_model,
        fixed_cost=fixed_cost,
        segments=segments,
    ) or (_is_fixed_cost_model(cost_model) and fixed_cost > 0):
        return fixed_cost + holiday_bonus + earning_item_total
    if not has_attendance:
        return fixed_cost + holiday_bonus + earning_item_total
    return _calculate_variable_courier_gross_cost(segments) + earning_item_total


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

    earning_rows = []
    for earning_type, amount in payload.earning_items:
        label = str(earning_type or "—").strip() or "—"
        normalized_amount = _safe_float(amount)
        earning_rows.append(
            {
                "label": label,
                "amount": format_currency(normalized_amount),
            }
        )

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
        earning_rows=earning_rows,
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
    deduction_items.extend(_build_personnel_profile_deduction_items(person_match.iloc[0] if not person_match.empty else None))

    restaurant_names: list[str] = []
    attendance_segments: list[dict[str, object]] = []
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
        person_entries = month_entries.loc[personnel_match_mask].copy()
        if not person_entries.empty:
            if "is_support_assignment" not in person_entries.columns:
                person_entries["is_support_assignment"] = (
                    person_entries["planned_personnel_id"].notna()
                    & person_entries["actual_personnel_id"].notna()
                    & (person_entries["planned_personnel_id"] != person_entries["actual_personnel_id"])
                )
            grouped_segments = (
                person_entries.groupby(
                    ["brand", "restaurant_id", "is_support_assignment"],
                    dropna=False,
                )
                .agg(
                    total_hours=("worked_hours", "sum"),
                    total_packages=("package_count", "sum"),
                    support_day_count=("entry_date", lambda values: len({str(value)[:10] for value in values if str(value or '').strip()})),
                )
                .reset_index()
            )
            attendance_segments = [
                {
                    "brand": str(row["brand"] or ""),
                    "total_hours": _safe_float(row["total_hours"]),
                    "total_packages": _safe_float(row["total_packages"]),
                    "is_support_assignment": bool(row["is_support_assignment"]),
                    "support_day_count": int(row["support_day_count"] or 0),
                }
                for _, row in grouped_segments.iterrows()
            ]

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
    resolved_person_fixed_cost = _resolve_fixed_monthly_courier_pay(
        role=payroll_row.get("rol"),
        cost_model=person_cost_model,
        monthly_fixed_cost=person_fixed_cost,
        segments=attendance_segments,
    )
    profile_deduction_total = _safe_float(sum(amount for _, amount in _build_personnel_profile_deduction_items(
        person_match.iloc[0] if not person_match.empty else None
    )))
    base_deductions = _safe_float(payroll_row.get("kesinti")) + profile_deduction_total
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
        earning_items=_build_personnel_earning_items(
            role=payroll_row.get("rol"),
            cost_model=person_cost_model,
            total_hours=_safe_float(payroll_row.get("calisma_saati")),
            fixed_cost=resolved_person_fixed_cost,
            segments=attendance_segments,
        ),
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
    optional_personnel_select = _payroll_optional_personnel_select(conn)

    person_row = conn.execute(
        f"""
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
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            {optional_personnel_select}
        FROM personnel
        WHERE id = %s
        """,
        (personnel_id,),
    ).fetchone()
    if person_row is None:
        raise LookupError("Belgesi oluşturulacak personel bulunamadı.")
    person_data = dict(person_row)
    accounting_history_by_person = _fetch_effective_accounting_history_for_month(
        conn,
        selected_month=resolved_month,
    )
    accounting_history_person_ids = _fetch_accounting_history_person_ids(conn)
    profile_source = (
        accounting_history_by_person.get(personnel_id)
        if personnel_id in accounting_history_person_ids
        else person_data
    )

    attendance_rows = conn.execute(
        f"""
        SELECT
            d.restaurant_id,
            COALESCE(r.brand, '') AS brand,
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                 AND d.actual_personnel_id IS NOT NULL
                 AND d.actual_personnel_id <> d.planned_personnel_id
                THEN 1 ELSE 0
            END AS is_support_assignment,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COUNT(DISTINCT substr(COALESCE(d.entry_date, ''), 1, 10)) AS support_day_count
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
        GROUP BY
            d.restaurant_id,
            COALESCE(r.brand, ''),
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                 AND d.actual_personnel_id IS NOT NULL
                 AND d.actual_personnel_id <> d.planned_personnel_id
                THEN 1 ELSE 0
            END
        """,
        (resolved_month, personnel_id),
    ).fetchall()
    restaurant_package_total_rows = conn.execute(
        f"""
        SELECT
            d.restaurant_id,
            COALESCE(SUM(d.package_count), 0) AS restaurant_total_packages
        FROM daily_entries d
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND d.restaurant_id IS NOT NULL
        GROUP BY d.restaurant_id
        """,
        (resolved_month,),
    ).fetchall()
    restaurant_package_totals = {
        int(row["restaurant_id"]): _safe_float(row["restaurant_total_packages"])
        for row in restaurant_package_total_rows
        if row["restaurant_id"] is not None
    }

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
            "is_support_assignment": bool(row["is_support_assignment"]),
            "support_day_count": int(row["support_day_count"] or 0),
            "restaurant_total_packages": (
                _safe_float(restaurant_package_totals.get(int(row["restaurant_id"])))
                if row["restaurant_id"] is not None
                else _safe_float(row["total_packages"])
            )
            or _safe_float(row["total_packages"]),
        }
        for row in attendance_rows
    ]
    total_hours = _safe_float(sum(_safe_float(row["total_hours"]) for row in attendance_rows))
    total_packages = _safe_float(sum(_safe_float(row["total_packages"]) for row in attendance_rows))
    resolved_fixed_cost = _resolve_fixed_monthly_courier_pay(
        role=person_data["role"],
        cost_model=person_data["cost_model"],
        monthly_fixed_cost=_safe_float(person_data["monthly_fixed_cost"]),
        segments=attendance_segments,
    )
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
    non_motor_deduction_rows = [
        row
        for row in deduction_rows
        if not is_motor_rental_deduction_type(row["deduction_type"])
        and not is_motor_purchase_deduction_type(row["deduction_type"])
    ]
    base_deductions = _safe_float(sum(_safe_float(row["total_amount"]) for row in non_motor_deduction_rows))
    invoice_base_reducing_deductions = _safe_float(
        sum(
            _safe_float(row["total_amount"])
            for row in non_motor_deduction_rows
            if _deduction_reduces_invoice_base(row["deduction_type"])
        )
    )
    vehicle_history_rows = _fetch_vehicle_history_rows_by_person_for_month(
        conn,
        personnel_ids=[personnel_id],
        selected_month=resolved_month,
    ).get(personnel_id, [])
    vehicle_history_person_ids = _fetch_vehicle_history_person_ids(conn)
    has_vehicle_history = personnel_id in vehicle_history_person_ids
    auto_motor_rental = (
        calculate_company_motor_rental_deduction_from_history(
            vehicle_history_rows,
            resolved_month,
            exit_date=_row_value(person_data, "exit_date"),
        )
        if has_vehicle_history
        else calculate_company_motor_rental_deduction(
            person_data,
            resolved_month,
        )
    )
    auto_motor_purchase = (
        calculate_company_motor_purchase_deduction_from_history(
            vehicle_history_rows,
            resolved_month,
        )
        if has_vehicle_history
        else calculate_company_motor_purchase_deduction(
            person_data,
            resolved_month,
        )
    )
    base_deductions += auto_motor_rental
    base_deductions += auto_motor_purchase
    invoice_base_reducing_deductions += auto_motor_purchase
    profile_deduction_items = _build_personnel_profile_deduction_items(profile_source, selected_month=resolved_month)
    profile_deduction_total = _safe_float(sum(amount for _, amount in profile_deduction_items))
    base_deductions += profile_deduction_total
    total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
        gross_pay=gross_pay,
        base_deductions=base_deductions,
        invoice_base_reducing_deductions=invoice_base_reducing_deductions,
    )
    restaurant_names = [str(row["restaurant_label"]) for row in restaurant_rows if str(row["restaurant_label"]).strip()]
    deduction_items = [(str(row["deduction_type"]), _safe_float(row["total_amount"])) for row in non_motor_deduction_rows]
    if auto_motor_rental > 0:
        deduction_items.append((MOTOR_RENTAL_DEDUCTION_TYPE, auto_motor_rental))
    if auto_motor_purchase > 0:
        deduction_items.append((MOTOR_PURCHASE_DEDUCTION_TYPE, auto_motor_purchase))
    deduction_items.extend(profile_deduction_items)
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
        earning_items=_build_personnel_earning_items(
            role=person_data["role"],
            cost_model=person_data["cost_model"],
            total_hours=total_hours,
            fixed_cost=resolved_fixed_cost,
            segments=attendance_segments,
        ),
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
    optional_personnel_select = _payroll_optional_personnel_select(conn)
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
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                 AND d.actual_personnel_id IS NOT NULL
                 AND d.actual_personnel_id <> d.planned_personnel_id
                THEN 1 ELSE 0
            END AS is_support_assignment,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COUNT(DISTINCT substr(COALESCE(d.entry_date, ''), 1, 10)) AS support_day_count
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
            COALESCE(r.brand, ''),
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                 AND d.actual_personnel_id IS NOT NULL
                 AND d.actual_personnel_id <> d.planned_personnel_id
                THEN 1 ELSE 0
            END
    """
    attendance_rows = conn.execute(attendance_query, tuple(attendance_params)).fetchall()
    restaurant_package_totals_query = """
        SELECT
            d.restaurant_id,
            COALESCE(SUM(d.package_count), 0) AS restaurant_total_packages
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {month_key_sql} = %s
          AND d.restaurant_id IS NOT NULL
    """.format(month_key_sql=_month_key_sql("d.entry_date"))
    restaurant_package_totals_params: list[object] = [resolved_month]
    if selected_restaurant != "Tümü":
        restaurant_package_totals_query += """
          AND COALESCE(r.brand || ' - ' || r.branch, '-') = %s
        """
        restaurant_package_totals_params.append(selected_restaurant)
    restaurant_package_totals_query += """
        GROUP BY d.restaurant_id
    """
    restaurant_package_total_rows = conn.execute(
        restaurant_package_totals_query,
        tuple(restaurant_package_totals_params),
    ).fetchall()
    restaurant_package_totals = {
        int(row["restaurant_id"]): _safe_float(row["restaurant_total_packages"])
        for row in restaurant_package_total_rows
        if row["restaurant_id"] is not None
    }
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

    personnel_rows = conn.execute(
        f"""
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
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            {optional_personnel_select}
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
                    "is_support_assignment": bool(row["is_support_assignment"]),
                    "support_day_count": int(row["support_day_count"] or 0),
                    "restaurant_total_packages": (
                        _safe_float(restaurant_package_totals.get(int(row["restaurant_id"])))
                        if row["restaurant_id"] is not None
                        else total_packages
                    )
                    or total_packages,
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
    deduction_items_by_person: dict[int, list[tuple[str, float]]] = {}
    invoice_base_reducing_deductions_by_person: dict[int, float] = {}
    for row in deduction_rows:
        if row["personnel_id"] is None:
            continue
        if is_motor_rental_deduction_type(row["deduction_type"]) or is_motor_purchase_deduction_type(row["deduction_type"]):
            continue
        person_id = int(row["personnel_id"])
        amount = _safe_float(row["total_amount"])
        deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + amount
        deduction_items_by_person.setdefault(person_id, []).append((str(row["deduction_type"] or "Kesinti"), amount))
        if _deduction_reduces_invoice_base(row["deduction_type"]):
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + amount
            )

    personnel_index = {int(row["id"]): row for row in personnel_rows if row["id"] is not None}
    vehicle_history_by_person = _fetch_vehicle_history_rows_by_person_for_month(
        conn,
        personnel_ids=sorted(personnel_index.keys()),
        selected_month=resolved_month,
    )
    vehicle_history_person_ids = _fetch_vehicle_history_person_ids(conn)
    accounting_history_by_person = _fetch_effective_accounting_history_for_month(
        conn,
        selected_month=resolved_month,
    )
    accounting_history_person_ids = _fetch_accounting_history_person_ids(conn)
    auto_motor_rental_by_person: dict[int, float] = {}
    auto_motor_purchase_by_person: dict[int, float] = {}
    for person_id, person in personnel_index.items():
        person_vehicle_history = vehicle_history_by_person.get(person_id, [])
        has_vehicle_history = person_id in vehicle_history_person_ids
        auto_motor_rental = (
            calculate_company_motor_rental_deduction_from_history(
                person_vehicle_history,
                resolved_month,
                exit_date=_row_value(person, "exit_date"),
            )
            if has_vehicle_history
            else calculate_company_motor_rental_deduction(
                dict(person),
                resolved_month,
            )
        )
        if auto_motor_rental > 0:
            auto_motor_rental_by_person[person_id] = auto_motor_rental
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_rental
            deduction_items_by_person.setdefault(person_id, []).append((MOTOR_RENTAL_DEDUCTION_TYPE, auto_motor_rental))
        auto_motor_purchase = (
            calculate_company_motor_purchase_deduction_from_history(
                person_vehicle_history,
                resolved_month,
            )
            if has_vehicle_history
            else calculate_company_motor_purchase_deduction(
                dict(person),
                resolved_month,
            )
        )
        if auto_motor_purchase > 0:
            auto_motor_purchase_by_person[person_id] = auto_motor_purchase
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_purchase
            deduction_items_by_person.setdefault(person_id, []).append((MOTOR_PURCHASE_DEDUCTION_TYPE, auto_motor_purchase))
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + auto_motor_purchase
            )
        profile_source = accounting_history_by_person.get(person_id) if person_id in accounting_history_person_ids else person
        profile_deduction_items = _build_personnel_profile_deduction_items(profile_source, selected_month=resolved_month)
        if profile_deduction_items:
            profile_deduction_total = _safe_float(sum(amount for _, amount in profile_deduction_items))
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + profile_deduction_total
            deduction_items_by_person.setdefault(person_id, []).extend(profile_deduction_items)

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
        entry_deduction_items = list(deduction_items_by_person.get(person_id, []))
        if tevkifat.tevkifat_amount > 0:
            entry_deduction_items.append(("Tevkifat", tevkifat.tevkifat_amount))
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
                deduction_items=[
                    PayrollDeductionItem(label=label, amount=_safe_float(amount))
                    for label, amount in entry_deduction_items
                ],
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
