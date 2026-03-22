from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd


_FIRST_ROW_VALUE: Callable[[Any, Any], Any] | None = None
_GET_ROW_VALUE: Callable[[Any, str, Any], Any] | None = None
_SAFE_INT: Callable[[Any, int], int] | None = None
_SAFE_FLOAT: Callable[[Any, float], float] | None = None
_PARSE_DATE_VALUE: Callable[[Any], date | None] | None = None
_FETCH_DF: Callable[..., pd.DataFrame] | None = None

_EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS: set[str] = set()
_EQUIPMENT_VAT_RATE_BEFORE_REDUCTION = 20.0
_EQUIPMENT_VAT_RATE_AFTER_REDUCTION = 10.0
_EQUIPMENT_REDUCED_VAT_START_DATE = date(2026, 3, 1)
_AUTO_MOTOR_RENTAL_DEDUCTION = 13000.0
_AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION = 11250.0
_AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = 12
_AUTO_EQUIPMENT_INSTALLMENT_COUNT = 2
_AUTO_ONBOARDING_ITEMS: list[dict[str, Any]] = []


def configure_equipment_rules(
    *,
    first_row_value_fn: Callable[[Any, Any], Any],
    get_row_value_fn: Callable[[Any, str, Any], Any],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    parse_date_value_fn: Callable[[Any], date | None],
    fetch_df_fn: Callable[..., pd.DataFrame],
    equipment_always_standard_vat_items: set[str],
    equipment_vat_rate_before_reduction: float,
    equipment_vat_rate_after_reduction: float,
    equipment_reduced_vat_start_date: date,
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
    auto_motor_purchase_installment_count: int,
    auto_equipment_installment_count: int,
    auto_onboarding_items: list[dict[str, Any]],
) -> None:
    global _FIRST_ROW_VALUE
    global _GET_ROW_VALUE
    global _SAFE_INT
    global _SAFE_FLOAT
    global _PARSE_DATE_VALUE
    global _FETCH_DF
    global _EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS
    global _EQUIPMENT_VAT_RATE_BEFORE_REDUCTION
    global _EQUIPMENT_VAT_RATE_AFTER_REDUCTION
    global _EQUIPMENT_REDUCED_VAT_START_DATE
    global _AUTO_MOTOR_RENTAL_DEDUCTION
    global _AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION
    global _AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT
    global _AUTO_EQUIPMENT_INSTALLMENT_COUNT
    global _AUTO_ONBOARDING_ITEMS

    _FIRST_ROW_VALUE = first_row_value_fn
    _GET_ROW_VALUE = get_row_value_fn
    _SAFE_INT = safe_int_fn
    _SAFE_FLOAT = safe_float_fn
    _PARSE_DATE_VALUE = parse_date_value_fn
    _FETCH_DF = fetch_df_fn
    _EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS = set(equipment_always_standard_vat_items)
    _EQUIPMENT_VAT_RATE_BEFORE_REDUCTION = float(equipment_vat_rate_before_reduction)
    _EQUIPMENT_VAT_RATE_AFTER_REDUCTION = float(equipment_vat_rate_after_reduction)
    _EQUIPMENT_REDUCED_VAT_START_DATE = equipment_reduced_vat_start_date
    _AUTO_MOTOR_RENTAL_DEDUCTION = float(auto_motor_rental_deduction)
    _AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION = float(auto_motor_purchase_monthly_deduction)
    _AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = int(auto_motor_purchase_installment_count)
    _AUTO_EQUIPMENT_INSTALLMENT_COUNT = int(auto_equipment_installment_count)
    _AUTO_ONBOARDING_ITEMS = list(auto_onboarding_items)


def latest_average_cost(conn, item_name: str) -> float:
    row = conn.execute(
        """
        SELECT CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount) / SUM(quantity) ELSE 0 END AS avg_cost
        FROM inventory_purchases
        WHERE item_name = ?
        """,
        (item_name,),
    ).fetchone()
    return float(_FIRST_ROW_VALUE(row, 0) or 0)


def get_equipment_cost_snapshot(conn, item_name: str) -> tuple[int, float, int, float]:
    row = conn.execute(
        """
        SELECT COUNT(*) AS row_count, COALESCE(SUM(total_invoice_amount), 0) AS total_invoice_amount, COALESCE(SUM(quantity), 0) AS total_quantity, COALESCE(MAX(id), 0) AS max_id
        FROM inventory_purchases
        WHERE item_name = ?
        """,
        ((item_name or "").strip(),),
    ).fetchone()
    row_count = _SAFE_INT(_GET_ROW_VALUE(row, "row_count", 0), 0)
    total_invoice_amount = _SAFE_FLOAT(_GET_ROW_VALUE(row, "total_invoice_amount", 0.0), 0.0)
    total_quantity = _SAFE_INT(_GET_ROW_VALUE(row, "total_quantity", 0), 0)
    weighted_average = round(total_invoice_amount / total_quantity, 2) if total_quantity > 0 else 0.0
    max_id = _SAFE_INT(_GET_ROW_VALUE(row, "max_id", 0), 0)
    return row_count, total_invoice_amount, max_id, weighted_average


def get_default_equipment_unit_cost(conn, item_name: str) -> float:
    *_, weighted_average = get_equipment_cost_snapshot(conn, item_name)
    if weighted_average > 0:
        return weighted_average
    return latest_average_cost(conn, item_name)


def get_equipment_vat_rate(item_name: str, issue_date: date | str | None = None) -> float:
    normalized_item_name = str(item_name or "").strip()
    if normalized_item_name in _EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS:
        return _EQUIPMENT_VAT_RATE_BEFORE_REDUCTION
    effective_date = _PARSE_DATE_VALUE(issue_date) or date.today()
    if effective_date >= _EQUIPMENT_REDUCED_VAT_START_DATE:
        return _EQUIPMENT_VAT_RATE_AFTER_REDUCTION
    return _EQUIPMENT_VAT_RATE_BEFORE_REDUCTION


def get_default_equipment_sale_price(item_name: str) -> float:
    manual_item_defaults = {
        "Motor Kirası": _AUTO_MOTOR_RENTAL_DEDUCTION,
        "Motor Satın Alım": _AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION * _AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT,
    }
    normalized_item_name = (item_name or "").strip()
    if normalized_item_name in manual_item_defaults:
        return float(manual_item_defaults[normalized_item_name])
    for item in _AUTO_ONBOARDING_ITEMS:
        if item["item_name"] == normalized_item_name:
            return float(item["unit_sale_price"])
    return 0.0


def get_default_issue_installment_count(item_name: str) -> int:
    normalized_item_name = (item_name or "").strip()
    if normalized_item_name == "Motor Satın Alım":
        return _AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT
    if normalized_item_name == "Motor Kirası":
        return 1
    return _AUTO_EQUIPMENT_INSTALLMENT_COUNT


def normalize_equipment_issue_installment_count(sale_type: str, installment_count: int) -> int:
    if str(sale_type or "Satış").strip() != "Satış":
        return 1
    return max(_SAFE_INT(installment_count, 1), 1)


def equipment_issue_generates_installments(sale_type: str, total_sale_amount: float, installment_count: int) -> bool:
    return (
        str(sale_type or "Satış").strip() == "Satış"
        and _SAFE_FLOAT(total_sale_amount, 0.0) > 0
        and normalize_equipment_issue_installment_count(sale_type, installment_count) > 0
    )


def describe_auto_source_key(auto_source_key: Any) -> str:
    key = str(auto_source_key or "").strip()
    if not key:
        return "Manuel"
    if key.startswith("auto:motor_rental:"):
        return "Eski sistem | Motor kirası"
    if key.startswith("auto:motor_purchase:"):
        return "Eski sistem | Motor satış taksiti"
    if key.startswith("auto:accounting:"):
        return "Eski sistem | Muhasebe"
    if key.startswith("auto:company_setup"):
        return "Eski sistem | Şirket açılışı"
    if key.startswith("auto:onboarding:"):
        return "Eski sistem | İşe giriş zimmeti"
    return "Eski sistem"


def build_equipment_profitability_frames(conn, start_date: date | str | None = None, end_date: date | str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    start_value = _PARSE_DATE_VALUE(start_date)
    end_value = _PARSE_DATE_VALUE(end_date)
    sales_query = """
        SELECT item_name,
               SUM(quantity) AS sold_qty,
               SUM(quantity * unit_cost) AS total_cost,
               SUM(quantity * unit_sale_price) AS total_sale,
               SUM((quantity * unit_sale_price) - (quantity * unit_cost)) AS gross_profit
        FROM courier_equipment_issues
        WHERE sale_type = 'Satış'
    """
    sales_params: tuple[Any, ...] = ()
    if start_value and end_value:
        sales_query += " AND issue_date BETWEEN ? AND ?"
        sales_params = (start_value.isoformat(), end_value.isoformat())
    sales_query += " GROUP BY item_name ORDER BY total_sale DESC"
    sales_profit = _FETCH_DF(conn, sales_query, sales_params)

    stock_purchase = _FETCH_DF(
        conn,
        """
        SELECT item_name,
               SUM(quantity) AS purchased_qty,
               SUM(total_invoice_amount) AS purchased_total,
               CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount)/SUM(quantity) ELSE 0 END AS weighted_unit_cost
        FROM inventory_purchases
        GROUP BY item_name
        ORDER BY item_name
        """,
    )
    return sales_profit, stock_purchase
