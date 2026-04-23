from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Mapping


DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT = 13000.0
MOTOR_RENTAL_DEDUCTION_TYPE = "Motor Kirası"
MOTOR_RENTAL_DEDUCTION_TYPE_ALIASES = {"motor kirası", "motor kirasi"}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("ç", "c")
        .replace("ğ", "g")
        .replace("ı", "i")
        .replace("ö", "o")
        .replace("ş", "s")
        .replace("ü", "u")
    )


def _parse_date(value: object) -> date | None:
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


def _month_bounds(month_key: str) -> tuple[date, date]:
    year_text, month_text = str(month_key).split("-", 1)
    year = int(year_text)
    month = int(month_text)
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _is_yes(value: object) -> bool:
    return _normalize_text(value) in {"evet", "yes", "true", "1"}


def _is_active(value: object) -> bool:
    normalized = _normalize_text(value)
    return not normalized or normalized in {"aktif", "active", "acik", "open", "1", "true"}


def is_company_motor_rental(row: Mapping[str, object]) -> bool:
    vehicle_type = _normalize_text(row.get("vehicle_type"))
    motor_purchase = _is_yes(row.get("motor_purchase"))
    motor_rental = _is_yes(row.get("motor_rental"))
    return _is_active(row.get("status")) and not motor_purchase and (
        vehicle_type == "cat kapinda" or motor_rental
    )


def is_motor_rental_deduction_type(value: object) -> bool:
    return _normalize_text(value) in MOTOR_RENTAL_DEDUCTION_TYPE_ALIASES


def calculate_company_motor_rental_deduction(
    row: Mapping[str, object],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
) -> float:
    if not is_company_motor_rental(row):
        return 0.0

    monthly_amount = _safe_float(row.get("motor_rental_monthly_amount"), DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT)
    if monthly_amount <= 0:
        monthly_amount = DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT

    month_start, month_end = _month_bounds(selected_month)
    start_date = _parse_date(row.get("start_date"))
    if start_date is not None and start_date > month_end:
        return 0.0

    expected_amount = monthly_amount
    if start_date is not None and month_start <= start_date <= month_end:
        active_days = max(month_end.day - start_date.day + 1, 0)
        expected_amount = min(monthly_amount, monthly_amount / 30.0 * active_days)

    return max(round(expected_amount - _safe_float(existing_amount), 2), 0.0)
