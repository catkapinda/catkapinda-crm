from __future__ import annotations

import unittest
from dataclasses import dataclass

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


def _safe_float(value, default=0.0):
    try:
        return default if value is None else float(value)
    except Exception:
        return default


def setUpModule() -> None:
    reporting_rules.configure_reporting_rules(
        safe_int_fn=lambda value, default=0: default if value is None else int(float(value)),
        safe_float_fn=_safe_float,
        parse_date_value_fn=lambda value: value,
        end_of_month_fn=lambda value: value,
        normalize_cost_model_value_fn=lambda value, role: str(value or role or "").strip(),
        pricing_rule_cls=_PricingRule,
        vat_rate_default=20.0,
        courier_hourly_cost=250.0,
        courier_package_cost_default_low=20.0,
        courier_package_cost_default_high=25.0,
        courier_package_cost_qc=25.0,
        package_threshold_default=390,
    )


class ReportingInvoiceVatTests(unittest.TestCase):
    def test_restaurant_invoice_always_uses_twenty_percent_vat(self) -> None:
        month_df = pd.DataFrame(
            [
                {
                    "restaurant_id": 1,
                    "brand": "Test",
                    "branch": "Sube",
                    "pricing_model": "hourly_plus_package",
                    "worked_hours": 10.0,
                    "package_count": 20.0,
                    "hourly_rate": 100.0,
                    "package_rate": 10.0,
                    "package_rate_low": 10.0,
                    "package_rate_high": 10.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 0.0,
                }
            ]
        )

        invoice_df = reporting_rules.build_invoice_summary_df(month_df)

        self.assertEqual(len(invoice_df), 1)
        self.assertAlmostEqual(float(invoice_df.iloc[0]["kdv_haric"]), 1200.0)
        self.assertAlmostEqual(float(invoice_df.iloc[0]["kdv_dahil"]), 1440.0)


if __name__ == "__main__":
    unittest.main()
