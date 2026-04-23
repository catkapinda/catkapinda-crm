from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping


DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT = 13000.0
DEFAULT_MOTOR_PURCHASE_TOTAL_PRICE = 135000.0
DEFAULT_MOTOR_PURCHASE_INSTALLMENT_COUNT = 12
MOTOR_RENTAL_DEDUCTION_TYPE = "Motor Kirası"
MOTOR_PURCHASE_DEDUCTION_TYPE = "Motor Satış Taksiti"
MOTOR_RENTAL_DEDUCTION_TYPE_ALIASES = {"motor kirası", "motor kirasi"}
MOTOR_PURCHASE_DEDUCTION_TYPE_ALIASES = {
    "motor satis taksiti",
    "motor satış taksiti",
    "motor satin alim",
    "motor satın alım",
}


@dataclass(frozen=True)
class MotorPaymentPlan:
    deduction_type: str
    deduction_date: date
    amount: float
    expected_amount: float
    existing_amount: float
    monthly_amount: float
    auto_source_key: str
    notes: str
    installment_index: int = 1
    installment_count: int = 1
    sale_price: float = 0.0


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


def is_company_motor_purchase(row: Mapping[str, object]) -> bool:
    vehicle_type = _normalize_text(row.get("vehicle_type"))
    motor_purchase = _is_yes(row.get("motor_purchase"))
    return _is_active(row.get("status")) and motor_purchase and vehicle_type == "cat kapinda"


def is_motor_purchase_deduction_type(value: object) -> bool:
    return _normalize_text(value) in MOTOR_PURCHASE_DEDUCTION_TYPE_ALIASES


def _format_currency_note(value: float) -> str:
    return f"{round(_safe_float(value)):,.0f}".replace(",", ".") + " TL"


def _month_payment_date(month_start: date, month_end: date, preferred_day: int | None = None) -> date:
    if preferred_day is None or preferred_day <= 0:
        return month_end
    return date(month_start.year, month_start.month, min(preferred_day, month_end.day))


def build_company_motor_rental_plan(
    row: Mapping[str, object],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
) -> MotorPaymentPlan | None:
    if not is_company_motor_rental(row):
        return None

    monthly_amount = _safe_float(row.get("motor_rental_monthly_amount"), DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT)
    if monthly_amount <= 0:
        monthly_amount = DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT

    month_start, month_end = _month_bounds(selected_month)
    start_date = _parse_date(row.get("start_date"))
    if start_date is not None and start_date > month_end:
        return None

    expected_amount = monthly_amount
    if start_date is not None and month_start <= start_date <= month_end:
        active_days = max(month_end.day - start_date.day + 1, 0)
        expected_amount = min(monthly_amount, monthly_amount / 30.0 * active_days)

    amount = max(round(expected_amount - _safe_float(existing_amount), 2), 0.0)
    if amount <= 0:
        return None

    note_parts = [f"Aylık kira {_format_currency_note(monthly_amount)}"]
    if start_date is not None and month_start <= start_date <= month_end:
        note_parts.append(f"ilk ay prorata {_format_currency_note(expected_amount)}")
    if existing_amount > 0:
        note_parts.append(f"manuel kayıt {_format_currency_note(existing_amount)} düşüldü")
    return MotorPaymentPlan(
        deduction_type=MOTOR_RENTAL_DEDUCTION_TYPE,
        deduction_date=month_end,
        amount=amount,
        expected_amount=round(expected_amount, 2),
        existing_amount=round(_safe_float(existing_amount), 2),
        monthly_amount=round(monthly_amount, 2),
        auto_source_key=f"auto:motor-rental:{row.get('id') or 'person'}:{selected_month}",
        notes=" · ".join(note_parts),
    )


def calculate_company_motor_rental_deduction(
    row: Mapping[str, object],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
) -> float:
    plan = build_company_motor_rental_plan(
        row,
        selected_month,
        existing_amount=existing_amount,
    )
    return plan.amount if plan is not None else 0.0


def build_company_motor_purchase_plan(
    row: Mapping[str, object],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
) -> MotorPaymentPlan | None:
    if not is_company_motor_purchase(row):
        return None

    month_start, month_end = _month_bounds(selected_month)
    start_date = _parse_date(row.get("motor_purchase_start_date")) or _parse_date(row.get("start_date")) or month_start
    if start_date > month_end:
        return None

    installment_count = int(_safe_float(row.get("motor_purchase_commitment_months"), DEFAULT_MOTOR_PURCHASE_INSTALLMENT_COUNT))
    if installment_count <= 0:
        installment_count = DEFAULT_MOTOR_PURCHASE_INSTALLMENT_COUNT

    sale_price = _safe_float(row.get("motor_purchase_sale_price"), DEFAULT_MOTOR_PURCHASE_TOTAL_PRICE)
    if sale_price <= 0:
        sale_price = DEFAULT_MOTOR_PURCHASE_TOTAL_PRICE

    monthly_amount = _safe_float(row.get("motor_purchase_monthly_deduction"), 0.0)
    if monthly_amount <= 0:
        monthly_amount = round(sale_price / installment_count, 2)

    month_index = (month_start.year - start_date.year) * 12 + (month_start.month - start_date.month)
    if month_index < 0 or month_index >= installment_count:
        return None

    expected_amount = monthly_amount
    amount = max(round(expected_amount - _safe_float(existing_amount), 2), 0.0)
    if amount <= 0:
        return None

    installment_index = month_index + 1
    note_parts = [
        f"Satış bedeli {_format_currency_note(sale_price)}",
        f"taahhüt {installment_count} ay",
        f"taksit {installment_index}/{installment_count}",
    ]
    if existing_amount > 0:
        note_parts.append(f"manuel kayıt {_format_currency_note(existing_amount)} düşüldü")

    return MotorPaymentPlan(
        deduction_type=MOTOR_PURCHASE_DEDUCTION_TYPE,
        deduction_date=_month_payment_date(month_start, month_end, start_date.day),
        amount=amount,
        expected_amount=round(expected_amount, 2),
        existing_amount=round(_safe_float(existing_amount), 2),
        monthly_amount=round(monthly_amount, 2),
        auto_source_key=f"auto:motor-purchase:{row.get('id') or 'person'}:{selected_month}",
        notes=" · ".join(note_parts),
        installment_index=installment_index,
        installment_count=installment_count,
        sale_price=round(sale_price, 2),
    )


def calculate_company_motor_purchase_deduction(
    row: Mapping[str, object],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
) -> float:
    plan = build_company_motor_purchase_plan(
        row,
        selected_month,
        existing_amount=existing_amount,
    )
    return plan.amount if plan is not None else 0.0
