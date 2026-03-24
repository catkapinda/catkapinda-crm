from __future__ import annotations

import calendar
import unittest
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from rules import reporting_rules


@dataclass
class _PricingRule:
    pricing_model: str
    hourly_rate: float
    package_rate: float
    package_threshold: int
    package_rate_low: float
    package_rate_high: float
    fixed_monthly_fee: float
    vat_rate: float


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


def setUpModule():
    reporting_rules.configure_reporting_rules(
        safe_int_fn=_safe_int,
        safe_float_fn=_safe_float,
        parse_date_value_fn=_parse_date_value,
        end_of_month_fn=_end_of_month,
        normalize_cost_model_value_fn=_normalize_cost_model_value,
        pricing_rule_cls=_PricingRule,
        vat_rate_default=20.0,
        courier_hourly_cost=250.0,
        courier_package_cost_default_low=20.0,
        courier_package_cost_default_high=25.0,
        courier_package_cost_qc=25.0,
        package_threshold_default=390,
    )


class ReportingRulesTests(unittest.TestCase):
    def test_month_bounds_returns_month_limits(self):
        self.assertEqual(reporting_rules.month_bounds("2026-02"), ("2026-02-01", "2026-02-28"))

    def test_threshold_package_uses_per_courier_threshold_in_invoice_summary(self):
        month_df = pd.DataFrame(
            [
                {
                    "restaurant_id": 10,
                    "brand": "Fasuli",
                    "branch": "Beyoglu",
                    "pricing_model": "threshold_package",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 33.75,
                    "package_rate_high": 54.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                    "worked_hours": 217.0,
                    "package_count": 362.0,
                    "actual_personnel_id": 1,
                },
                {
                    "restaurant_id": 10,
                    "brand": "Fasuli",
                    "branch": "Beyoglu",
                    "pricing_model": "threshold_package",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 33.75,
                    "package_rate_high": 54.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                    "worked_hours": 100.0,
                    "package_count": 50.0,
                    "actual_personnel_id": 2,
                },
            ]
        )

        invoice_df = reporting_rules.build_invoice_summary_df(month_df)
        self.assertEqual(len(invoice_df), 1)
        row = invoice_df.iloc[0]
        self.assertAlmostEqual(row["kdv_haric"], 100446.0)
        self.assertAlmostEqual(row["kdv_dahil"], 120535.2)

    def test_threshold_package_defaults_to_390_when_threshold_missing(self):
        group = pd.DataFrame(
            [
                {
                    "worked_hours": 156.0,
                    "package_count": 232.0,
                    "actual_personnel_id": 3,
                }
            ]
        )
        rule = _PricingRule(
            pricing_model="threshold_package",
            hourly_rate=273.0,
            package_rate=0.0,
            package_threshold=0,
            package_rate_low=33.75,
            package_rate_high=54.0,
            fixed_monthly_fee=0.0,
            vat_rate=20.0,
        )

        _, _, subtotal, grand_total = reporting_rules.calculate_customer_invoice(group, rule)
        self.assertAlmostEqual(subtotal, 50418.0)
        self.assertAlmostEqual(grand_total, 60501.6)

    def test_drilldown_map_keeps_each_courier_on_own_threshold(self):
        month_df = pd.DataFrame(
            [
                {
                    "restaurant_id": 11,
                    "brand": "Fasuli",
                    "branch": "Vatan",
                    "pricing_model": "threshold_package",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 33.75,
                    "package_rate_high": 54.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                    "worked_hours": 217.0,
                    "package_count": 362.0,
                    "actual_personnel_id": 1,
                },
                {
                    "restaurant_id": 11,
                    "brand": "Fasuli",
                    "branch": "Vatan",
                    "pricing_model": "threshold_package",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 33.75,
                    "package_rate_high": 54.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                    "worked_hours": 156.0,
                    "package_count": 232.0,
                    "actual_personnel_id": 2,
                },
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {"id": 1, "full_name": "Emre Cuma Atmaca", "role": "Kurye"},
                {"id": 2, "full_name": "Eyup Can Sahin", "role": "Kurye"},
            ]
        )

        drilldown_map = reporting_rules.build_restaurant_invoice_drilldown_map(month_df, personnel_df)
        detail_df = drilldown_map["Fasuli - Vatan"]
        emre_row = detail_df.loc[detail_df["personel"] == "Emre Cuma Atmaca"].iloc[0]
        eyup_row = detail_df.loc[detail_df["personel"] == "Eyup Can Sahin"].iloc[0]

        self.assertAlmostEqual(emre_row["kdv_haric"], 71458.5)
        self.assertAlmostEqual(emre_row["kdv_dahil"], 85750.2)
        self.assertAlmostEqual(eyup_row["kdv_haric"], 50418.0)
        self.assertAlmostEqual(eyup_row["kdv_dahil"], 60501.6)

    def test_attendance_export_includes_absence_reason_and_coverage_type(self):
        month_df = pd.DataFrame(
            [
                {
                    "brand": "Quick China",
                    "branch": "Ataşehir",
                    "entry_date": "2026-03-05",
                    "status": "Normal",
                    "worked_hours": 10.0,
                    "package_count": 24.0,
                    "planned_personnel_id": 1,
                    "actual_personnel_id": 2,
                    "absence_reason": "İzin",
                    "coverage_type": "Joker",
                }
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {"id": 1, "full_name": "Emine Ebru Aslan", "role": "Kurye"},
                {"id": 2, "full_name": "Recep Joker", "role": "Joker"},
            ]
        )

        export_map = reporting_rules.build_restaurant_attendance_export_map(
            month_df,
            personnel_df,
            "2026-03",
            {},
        )
        export_df = export_map["Quick China - Ataşehir"]
        emine_row = export_df.loc[export_df["Kurye"] == "Emine Ebru Aslan"].iloc[0]

        self.assertIn("İzin", emine_row["05"])
        self.assertIn("Joker: Recep Joker", emine_row["05"])
        self.assertIn("10 saat | 24 paket", emine_row["05"])

    def test_fixed_monthly_manual_override_supersedes_restaurant_fee(self):
        month_df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "restaurant_id": 20,
                    "brand": "Burger@",
                    "branch": "Kavacık",
                    "entry_date": "2026-03-05",
                    "pricing_model": "fixed_monthly",
                    "hourly_rate": 0.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 0.0,
                    "package_rate_high": 0.0,
                    "fixed_monthly_fee": 85000.0,
                    "monthly_invoice_amount": 0.0,
                    "vat_rate": 20.0,
                    "worked_hours": 160.0,
                    "package_count": 0.0,
                    "actual_personnel_id": 1,
                },
                {
                    "id": 2,
                    "restaurant_id": 20,
                    "brand": "Burger@",
                    "branch": "Kavacık",
                    "entry_date": "2026-03-20",
                    "pricing_model": "fixed_monthly",
                    "hourly_rate": 0.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 0.0,
                    "package_rate_high": 0.0,
                    "fixed_monthly_fee": 85000.0,
                    "monthly_invoice_amount": 92000.0,
                    "vat_rate": 20.0,
                    "worked_hours": 168.0,
                    "package_count": 0.0,
                    "actual_personnel_id": 1,
                },
            ]
        )

        invoice_df = reporting_rules.build_invoice_summary_df(month_df)
        self.assertEqual(len(invoice_df), 1)
        row = invoice_df.iloc[0]
        self.assertAlmostEqual(row["kdv_haric"], 92000.0)
        self.assertAlmostEqual(row["kdv_dahil"], 110400.0)


if __name__ == "__main__":
    unittest.main()
