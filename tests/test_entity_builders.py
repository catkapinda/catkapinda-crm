from __future__ import annotations

import unittest

import pandas as pd

from builders.entity_builders import build_restaurant_pricing_summary
from ui.ui_helpers import fmt_number


class RestaurantPricingSummaryTests(unittest.TestCase):
    def test_threshold_package_defaults_to_390_when_threshold_is_nan(self) -> None:
        row = pd.Series(
            {
                "pricing_model": "threshold_package",
                "hourly_rate": 273.0,
                "package_rate": 0.0,
                "package_threshold": float("nan"),
                "package_rate_low": 33.75,
                "package_rate_high": 47.25,
                "fixed_monthly_fee": 0.0,
            }
        )

        summary = build_restaurant_pricing_summary(row, fmt_number_fn=fmt_number)

        self.assertEqual(summary, "273₺/saat | 390 altı 33,75₺ | üstü 47,25₺")


if __name__ == "__main__":
    unittest.main()
