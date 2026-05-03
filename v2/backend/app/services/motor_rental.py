from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Mapping, Sequence


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


def _history_effective_date_for_payroll(row: Mapping[str, object]) -> date | None:
    effective_date = _parse_date(row.get("effective_date")) or _parse_date(row.get("changed_at"))
    motor_start_date = _parse_date(row.get("motor_purchase_start_date"))
    if (is_company_motor_purchase(row) or is_company_motor_rental_history(row)) and motor_start_date is not None:
        if effective_date is None:
            return motor_start_date
        return min(effective_date, motor_start_date)
    return effective_date


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


def is_company_motor_rental_history(row: Mapping[str, object]) -> bool:
    motor_purchase = _is_yes(row.get("motor_purchase"))
    motor_rental = _is_yes(row.get("motor_rental"))
    return not motor_purchase and motor_rental


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
    vehicle_type = _normalize_text(row.get("vehicle_type"))
    motor_purchase = _is_yes(row.get("motor_purchase"))
    motor_rental = _is_yes(row.get("motor_rental"))
    if motor_purchase or not (vehicle_type == "cat kapinda" or motor_rental):
        return None

    monthly_amount = _safe_float(row.get("motor_rental_monthly_amount"), DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT)
    if monthly_amount <= 0:
        monthly_amount = DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT

    month_start, month_end = _month_bounds(selected_month)
    start_date = _parse_date(row.get("start_date"))
    exit_date = _parse_date(row.get("exit_date")) or _parse_date(row.get("end_date"))
    if start_date is not None and start_date > month_end:
        return None
    if exit_date is not None and exit_date < month_start:
        return None

    active_start = max(month_start, start_date) if start_date is not None else month_start
    active_end = min(month_end, exit_date) if exit_date is not None else month_end
    if active_end < active_start:
        return None

    active_days = max((active_end - active_start).days + 1, 0)
    is_full_month_active = active_start == month_start and active_end == month_end
    expected_amount = monthly_amount
    if not is_full_month_active:
        expected_amount = min(monthly_amount, monthly_amount / 30.0 * active_days)

    amount = max(round(expected_amount - _safe_float(existing_amount), 2), 0.0)
    if amount <= 0:
        return None

    note_parts = [f"Aylık kira {_format_currency_note(monthly_amount)}"]
    if not is_full_month_active:
        note_parts.append(f"{active_days} gün prorata {_format_currency_note(expected_amount)}")
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


def build_company_motor_rental_plan_from_history(
    history_rows: Sequence[Mapping[str, object]],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
    exit_date: object = None,
) -> MotorPaymentPlan | None:
    month_start, month_end = _month_bounds(selected_month)
    month_end_exclusive = month_end + timedelta(days=1)
    exit_day = _parse_date(exit_date)
    if exit_day is not None and exit_day < month_start:
        return None
    capped_month_end_exclusive = (
        min(month_end_exclusive, exit_day + timedelta(days=1))
        if exit_day is not None
        else month_end_exclusive
    )

    ordered_history: list[tuple[date, int, Mapping[str, object]]] = []
    for index, row in enumerate(history_rows):
        effective_date = _history_effective_date_for_payroll(row)
        if effective_date is None or effective_date > month_end:
            continue
        row_id = int(_safe_float(row.get("id"), 0))
        ordered_history.append((effective_date, row_id or index, row))

    if not ordered_history:
        return None

    ordered_history.sort(key=lambda item: (item[0], item[1]))

    rental_segments: list[dict[str, object]] = []
    for idx, (effective_date, _, row) in enumerate(ordered_history):
        next_effective_date = (
            ordered_history[idx + 1][0]
            if idx + 1 < len(ordered_history)
            else capped_month_end_exclusive
        )
        interval_start = max(month_start, effective_date)
        interval_end_exclusive = min(capped_month_end_exclusive, next_effective_date)
        if interval_end_exclusive <= interval_start or not is_company_motor_rental_history(row):
            continue

        monthly_amount = _safe_float(row.get("motor_rental_monthly_amount"), DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT)
        if monthly_amount <= 0:
            monthly_amount = DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT

        previous_segment = rental_segments[-1] if rental_segments else None
        if (
            previous_segment is not None
            and previous_segment["monthly_amount"] == monthly_amount
            and previous_segment["end_exclusive"] == interval_start
        ):
            previous_segment["end_exclusive"] = interval_end_exclusive
            continue

        rental_segments.append(
            {
                "start": interval_start,
                "end_exclusive": interval_end_exclusive,
                "monthly_amount": monthly_amount,
            }
        )

    if not rental_segments:
        return None

    expected_amount = 0.0
    total_active_days = 0
    note_parts: list[str] = []
    for segment in rental_segments:
        segment_start = segment["start"]
        segment_end_exclusive = segment["end_exclusive"]
        monthly_amount = _safe_float(segment["monthly_amount"], DEFAULT_MOTOR_RENTAL_MONTHLY_AMOUNT)
        active_days = max((segment_end_exclusive - segment_start).days, 0)
        if active_days <= 0:
            continue
        total_active_days += active_days
        full_month_segment = (
            len(rental_segments) == 1
            and segment_start == month_start
            and segment_end_exclusive == capped_month_end_exclusive
            and capped_month_end_exclusive == month_end_exclusive
        )
        segment_expected_amount = monthly_amount if full_month_segment else min(
            monthly_amount,
            monthly_amount / 30.0 * active_days,
        )
        expected_amount += segment_expected_amount
        if not full_month_segment:
            note_parts.append(f"{active_days} gün prorata {_format_currency_note(segment_expected_amount)}")

    amount = max(round(expected_amount - _safe_float(existing_amount), 2), 0.0)
    if amount <= 0:
        return None

    if not note_parts:
        note_parts = [f"Aylık kira {_format_currency_note(expected_amount)}"]
    else:
        note_parts.insert(0, f"Aylık kira {_format_currency_note(sum(_safe_float(seg['monthly_amount']) for seg in rental_segments[:1]))}")
        note_parts.append(f"toplam {total_active_days} gün")
    if existing_amount > 0:
        note_parts.append(f"manuel kayıt {_format_currency_note(existing_amount)} düşüldü")

    history_person_id = ordered_history[0][2].get("personnel_id") or ordered_history[0][2].get("id") or "person"
    return MotorPaymentPlan(
        deduction_type=MOTOR_RENTAL_DEDUCTION_TYPE,
        deduction_date=month_end,
        amount=amount,
        expected_amount=round(expected_amount, 2),
        existing_amount=round(_safe_float(existing_amount), 2),
        monthly_amount=round(_safe_float(rental_segments[-1]["monthly_amount"]), 2),
        auto_source_key=f"auto:motor-rental-history:{history_person_id}:{selected_month}",
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


def calculate_company_motor_rental_deduction_from_history(
    history_rows: Sequence[Mapping[str, object]],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
    exit_date: object = None,
) -> float:
    plan = build_company_motor_rental_plan_from_history(
        history_rows,
        selected_month,
        existing_amount=existing_amount,
        exit_date=exit_date,
    )
    return plan.amount if plan is not None else 0.0


def calculate_company_motor_purchase_deduction_from_history(
    history_rows: Sequence[Mapping[str, object]],
    selected_month: str,
    *,
    existing_amount: float = 0.0,
) -> float:
    month_start, month_end = _month_bounds(selected_month)
    latest_row: Mapping[str, object] | None = None
    latest_effective_date: date | None = None
    latest_row_id = -1
    for index, row in enumerate(history_rows):
        effective_date = _history_effective_date_for_payroll(row)
        if effective_date is None or effective_date > month_end:
            continue
        row_id = int(_safe_float(row.get("id"), index))
        if latest_row is None or (effective_date, row_id) > (latest_effective_date or month_start, latest_row_id):
            latest_row = row
            latest_effective_date = effective_date
            latest_row_id = row_id
    if latest_row is None:
        return 0.0
    plan = build_company_motor_purchase_plan(
        latest_row,
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
