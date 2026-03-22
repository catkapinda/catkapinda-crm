from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.dashboard_service import build_dashboard_workspace_payload


class DashboardServiceTests(TestCase):
    def test_build_dashboard_workspace_payload_computes_core_summary(self) -> None:
        today_value = date(2026, 3, 22)
        active_restaurants_df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "brand": "Fasuli",
                    "branch": "Beyoglu",
                    "target_headcount": 2,
                }
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {
                    "id": 10,
                    "full_name": "Ali Veli",
                    "role": "Kurye",
                    "status": "Aktif",
                    "phone": "",
                    "tc_no": "",
                    "iban": "",
                    "current_plate": "",
                    "assigned_restaurant_id": None,
                }
            ]
        )
        entries_df = pd.DataFrame(
            [
                {
                    "entry_date": "2026-03-22",
                    "restaurant_id": 1,
                    "actual_personnel_id": 10,
                    "status": "Çalıştı",
                    "worked_hours": 8.0,
                    "package_count": 15.0,
                    "brand": "Fasuli",
                    "branch": "Beyoglu",
                    "target_headcount": 2,
                    "pricing_model": "Hacimli Primli",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390.0,
                    "package_rate_low": 33.75,
                    "package_rate_high": 37.5,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                }
            ]
        )
        invoice_df = pd.DataFrame([{"kdv_dahil": 1200.0}])
        profit_df = pd.DataFrame([{"brut_fark": 250.0}])
        shared_overhead_df = pd.DataFrame([{"aylik_net_maliyet": 50.0}])
        month_deductions_df = pd.DataFrame(columns=["id"])
        empty_role_history_df = pd.DataFrame(columns=["id"])

        with patch("services.dashboard_service.fetch_dashboard_entries", return_value=entries_df), \
             patch("services.dashboard_service.fetch_dashboard_active_restaurants", return_value=active_restaurants_df), \
             patch("services.dashboard_service.fetch_dashboard_personnel", return_value=personnel_df), \
             patch("services.dashboard_service.fetch_dashboard_role_history", return_value=empty_role_history_df), \
             patch("services.dashboard_service.fetch_dashboard_deductions_for_period", return_value=month_deductions_df), \
             patch("services.dashboard_service.build_invoice_summary_df", return_value=invoice_df), \
             patch("services.dashboard_service.month_bounds", return_value=("2026-03-01", "2026-03-31")):
            payload = build_dashboard_workspace_payload(
                object(),
                today_value=today_value,
                parse_date_value_fn=lambda value: pd.to_datetime(value).date() if value else None,
                safe_int_fn=lambda value, default=0: int(value) if value not in (None, "") else default,
                safe_float_fn=lambda value, default=0.0: float(value) if value not in (None, "") else default,
                role_requires_primary_restaurant_fn=lambda role: role == "Kurye",
                fmt_try_fn=lambda value: f"{value:.2f}",
                build_branch_profitability_fn=lambda *args, **kwargs: (profit_df, pd.DataFrame(), shared_overhead_df),
                build_dashboard_profit_snapshots_fn=lambda *args, **kwargs: ([{"restoran": "Fasuli - Beyoglu"}], []),
                build_dashboard_priority_alerts_fn=lambda *args, **kwargs: [{"tip": "acik_kadro"}],
                build_dashboard_brand_summary_fn=lambda *args, **kwargs: pd.DataFrame([{"brand": "Fasuli"}]),
            )

        self.assertEqual(payload.active_restaurants, 1)
        self.assertEqual(payload.active_people, 1)
        self.assertEqual(payload.today_working_people, 1)
        self.assertEqual(payload.month_packages, 15.0)
        self.assertEqual(payload.month_revenue, 1200.0)
        self.assertEqual(payload.month_operation_gap, 250.0)
        self.assertEqual(payload.shared_overhead_total, 50.0)
        self.assertFalse(payload.entries_empty)
        self.assertEqual(payload.critical_alert_count, 3)
        self.assertEqual(len(payload.under_target_df), 1)
        self.assertEqual(len(payload.missing_personnel_df), 1)
        self.assertEqual(len(payload.missing_restaurant_df), 1)
