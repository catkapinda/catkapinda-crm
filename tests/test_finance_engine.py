from __future__ import annotations

import calendar
import unittest
from datetime import date, datetime

import pandas as pd

from engines import finance_engine
from rules import reporting_rules


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


def _end_of_month(value: date) -> date:
    last_day = calendar.monthrange(value.year, value.month)[1]
    return date(value.year, value.month, last_day)


def _normalize_cost_model_value(value: str, role: str) -> str:
    return str(value or role or "").strip()


def _is_fixed_cost_model(value: str) -> bool:
    return str(value or "").strip().startswith("fixed_")


def _calculate_prorated_monthly_cost(monthly_cost: float, start_date: date, end_date: date) -> float:
    return float(monthly_cost or 0.0)


def setUpModule():
    reporting_rules.configure_reporting_rules(
        safe_int_fn=_safe_int,
        safe_float_fn=_safe_float,
        parse_date_value_fn=_parse_date_value,
        end_of_month_fn=_end_of_month,
        normalize_cost_model_value_fn=_normalize_cost_model_value,
        pricing_rule_cls=object,
        vat_rate_default=20.0,
        courier_hourly_cost=250.0,
        courier_package_cost_default_low=20.0,
        courier_package_cost_default_high=25.0,
        courier_package_cost_qc=25.0,
        package_threshold_default=390,
    )
    finance_engine.configure_finance_engine(
        safe_int_fn=_safe_int,
        safe_float_fn=_safe_float,
        is_fixed_cost_model_fn=_is_fixed_cost_model,
        calculate_prorated_monthly_cost_fn=_calculate_prorated_monthly_cost,
        shared_overhead_roles=set(),
        courier_hourly_cost=250.0,
    )


class FinanceEngineTests(unittest.TestCase):
    def test_personnel_cost_includes_hourly_plus_package_restaurant_packages(self):
        month_df = pd.DataFrame(
            [
                {
                    "actual_personnel_id": 1,
                    "restaurant_id": 10,
                    "brand": "Burger@",
                    "branch": "Kavacik",
                    "pricing_model": "hourly_plus_package",
                    "worked_hours": 218.0,
                    "package_count": 263.0,
                    "entry_date": "2026-01-21",
                }
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "full_name": "Beytullah Belen",
                    "role": "Kurye",
                    "status": "Aktif",
                    "cost_model": "standard_courier",
                    "monthly_fixed_cost": 0.0,
                }
            ]
        )

        result = finance_engine.calculate_personnel_cost(month_df, personnel_df, pd.DataFrame())

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result.iloc[0]["brut_maliyet"]), 59760.0)

    def test_personnel_cost_keeps_package_threshold_per_restaurant_not_month_total(self):
        month_df = pd.DataFrame(
            [
                {
                    "actual_personnel_id": 1,
                    "restaurant_id": 10,
                    "brand": "Burger@",
                    "branch": "Kavacik",
                    "pricing_model": "hourly_plus_package",
                    "worked_hours": 100.0,
                    "package_count": 385.0,
                    "entry_date": "2026-01-20",
                },
                {
                    "actual_personnel_id": 1,
                    "restaurant_id": 11,
                    "brand": "SushiCo",
                    "branch": "Beyoglu",
                    "pricing_model": "hourly_plus_package",
                    "worked_hours": 10.0,
                    "package_count": 40.0,
                    "entry_date": "2026-01-21",
                },
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "full_name": "Destek Kurye",
                    "role": "Kurye",
                    "status": "Aktif",
                    "cost_model": "standard_courier",
                    "monthly_fixed_cost": 0.0,
                }
            ]
        )

        result = finance_engine.calculate_personnel_cost(month_df, personnel_df, pd.DataFrame())

        # 110 saat * 250 + (385 + 40) paket * 20
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result.iloc[0]["brut_maliyet"]), 36000.0)


if __name__ == "__main__":
    unittest.main()
