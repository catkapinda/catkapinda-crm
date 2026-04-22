from __future__ import annotations

import unittest
from datetime import date, datetime

import pandas as pd

from rules import equipment_rules


def _first_row_value(row, default=None):
    if row is None:
        return default
    try:
        return row[0]
    except Exception:
        return default


def _get_row_value(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return float(value)
    except Exception:
        return default


def _parse_date_value(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    return datetime.strptime(text, "%Y-%m-%d").date()


def _fetch_df(*_args, **_kwargs):
    return pd.DataFrame()


def setUpModule():
    equipment_rules.configure_equipment_rules(
        first_row_value_fn=_first_row_value,
        get_row_value_fn=_get_row_value,
        safe_int_fn=_safe_int,
        safe_float_fn=_safe_float,
        parse_date_value_fn=_parse_date_value,
        fetch_df_fn=_fetch_df,
        equipment_always_standard_vat_items={"Kask"},
        equipment_vat_rate_before_reduction=20.0,
        equipment_vat_rate_after_reduction=10.0,
        equipment_reduced_vat_start_date=date(2026, 3, 1),
        auto_motor_rental_deduction=13000.0,
        auto_motor_purchase_monthly_deduction=11250.0,
        auto_motor_purchase_installment_count=12,
        auto_equipment_installment_count=2,
        auto_onboarding_items=[],
    )


class EquipmentRulesTests(unittest.TestCase):
    def test_non_sale_installment_count_is_forced_to_one(self):
        self.assertEqual(equipment_rules.normalize_equipment_issue_installment_count("Depozit / Teslim", 6), 1)

    def test_sale_installment_count_keeps_positive_value(self):
        self.assertEqual(equipment_rules.normalize_equipment_issue_installment_count("Satış", 6), 6)

    def test_installments_only_generated_for_positive_sales(self):
        self.assertTrue(equipment_rules.equipment_issue_generates_installments("Satış", 500.0, 2))
        self.assertFalse(equipment_rules.equipment_issue_generates_installments("Depozit / Teslim", 500.0, 2))
        self.assertFalse(equipment_rules.equipment_issue_generates_installments("Satış", 0.0, 2))

    def test_equipment_vat_rate_is_zero_for_all_items(self):
        self.assertEqual(equipment_rules.get_equipment_vat_rate("Box", "2026-03-15"), 0.0)
        self.assertEqual(equipment_rules.get_equipment_vat_rate("Kask", "2026-02-15"), 0.0)


if __name__ == "__main__":
    unittest.main()
