from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from services.reporting_service import build_reports_workspace_payload, load_monthly_payroll_source_payload


class ReportingServiceTests(unittest.TestCase):
    @patch("services.reporting_service.fetch_reporting_role_history")
    @patch("services.reporting_service.fetch_reporting_personnel")
    @patch("services.reporting_service.fetch_reporting_all_deductions")
    @patch("services.reporting_service.fetch_reporting_entries")
    def test_load_monthly_payroll_source_payload_collects_month_options_from_entries_and_deductions(
        self,
        entries_mock,
        deductions_mock,
        personnel_mock,
        role_history_mock,
    ):
        entries_mock.return_value = pd.DataFrame(
            [
                {"entry_date": "2026-03-10", "worked_hours": 8},
                {"entry_date": "2026-02-15", "worked_hours": 7},
            ]
        )
        deductions_mock.return_value = pd.DataFrame(
            [
                {"deduction_date": "2026-03-31", "amount": 100},
                {"deduction_date": "2026-01-31", "amount": 50},
            ]
        )
        personnel_mock.return_value = pd.DataFrame([{"id": 1, "full_name": "Test"}])
        role_history_mock.return_value = pd.DataFrame([{"personnel_id": 1, "role": "Kurye"}])

        payload = load_monthly_payroll_source_payload(MagicMock())

        self.assertEqual(payload.month_options, ["2026-03", "2026-02", "2026-01"])
        self.assertEqual(payload.entries["entry_date"].dt.strftime("%Y-%m").tolist(), ["2026-03", "2026-02"])
        self.assertEqual(payload.deductions["deduction_date"].dt.strftime("%Y-%m").tolist(), ["2026-03", "2026-01"])

    @patch("services.reporting_service.fetch_reporting_role_history")
    @patch("services.reporting_service.fetch_reporting_personnel")
    @patch("services.reporting_service.fetch_reporting_all_deductions")
    @patch("services.reporting_service.fetch_reporting_entries")
    def test_load_monthly_payroll_source_payload_handles_empty_sources(
        self,
        entries_mock,
        deductions_mock,
        personnel_mock,
        role_history_mock,
    ):
        entries_mock.return_value = pd.DataFrame()
        deductions_mock.return_value = pd.DataFrame()
        personnel_mock.return_value = pd.DataFrame()
        role_history_mock.return_value = pd.DataFrame()

        payload = load_monthly_payroll_source_payload(MagicMock())

        self.assertEqual(payload.month_options, [])
        self.assertTrue(payload.entries.empty)
        self.assertTrue(payload.deductions.empty)

    @patch("services.reporting_service.get_operational_restaurant_names_for_period", return_value=["Fasuli - Beyoglu"])
    @patch("services.reporting_service.build_branch_profitability", return_value=(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    @patch("services.reporting_service.build_side_income_summary_df", return_value=pd.DataFrame())
    @patch("services.reporting_service.split_equipment_profit_categories", return_value=(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    @patch("services.reporting_service.build_equipment_profitability_frames", return_value=(pd.DataFrame(), pd.DataFrame()))
    @patch("services.reporting_service.calculate_personnel_cost", return_value=pd.DataFrame([{"net_maliyet": 600.0}]))
    @patch("services.reporting_service.build_restaurant_attendance_export_map", return_value={})
    @patch("services.reporting_service.build_restaurant_invoice_drilldown_map", return_value={})
    @patch("services.reporting_service.build_invoice_summary_df")
    @patch("services.reporting_service.fetch_reporting_deductions_for_period")
    @patch("services.reporting_service.fetch_reporting_role_history")
    @patch("services.reporting_service.fetch_reporting_personnel")
    @patch("services.reporting_service.fetch_reporting_restaurants")
    def test_build_reports_workspace_payload_adds_fuel_and_partner_discount_income_and_filters_payroll_deductions(
        self,
        restaurants_mock,
        personnel_mock,
        role_history_mock,
        deductions_mock,
        invoice_mock,
        drilldown_mock,
        export_mock,
        personnel_cost_mock,
        equipment_profitability_mock,
        split_profit_mock,
        side_income_mock,
        branch_profit_mock,
        operational_names_mock,
    ):
        month_entries = pd.DataFrame(
            [
                {
                    "entry_date": "2026-03-22",
                    "brand": "Fasuli",
                    "branch": "Beyoglu",
                    "actual_personnel_id": 1,
                    "worked_hours": 8.0,
                    "package_count": 24.0,
                    "restaurant_id": 10,
                }
            ]
        )
        restaurants_mock.return_value = pd.DataFrame([{"id": 10, "brand": "Fasuli", "branch": "Beyoglu"}])
        personnel_mock.return_value = pd.DataFrame(
            [
                {"id": 1, "vehicle_type": "Çat Kapında", "accountant_cost": 0.0, "company_setup_cost": 0.0},
                {"id": 2, "vehicle_type": "Kendi Motoru", "accountant_cost": 0.0, "company_setup_cost": 0.0},
            ]
        )
        role_history_mock.return_value = pd.DataFrame()
        deductions_mock.return_value = pd.DataFrame(
            [
                {"personnel_id": 1, "deduction_type": "Yakıt", "amount": 1200.0},
                {"personnel_id": 2, "deduction_type": "Yakıt", "amount": 800.0},
                {"personnel_id": 1, "deduction_type": "Avans", "amount": 15000.0},
                {"personnel_id": 1, "deduction_type": "İdari ceza", "amount": 2000.0},
                {"personnel_id": 2, "deduction_type": "Partner Kart İndirimi", "amount": 55.0},
            ]
        )
        invoice_mock.return_value = pd.DataFrame([{"restoran": "Fasuli - Beyoglu", "kdv_dahil": 1000.0}])

        payload = build_reports_workspace_payload(MagicMock(), month_entries, "2026-03")

        filtered_deductions = personnel_cost_mock.call_args.args[2]
        self.assertEqual(filtered_deductions["deduction_type"].tolist(), ["Yakıt", "Yakıt"])
        branch_profit_deductions = branch_profit_mock.call_args.args[2]
        self.assertEqual(branch_profit_deductions["deduction_type"].tolist(), ["Yakıt", "Yakıt"])

        side_income_kwargs = side_income_mock.call_args.kwargs
        self.assertEqual(side_income_kwargs["utts_fuel_discount_amount"], 84.0)
        self.assertEqual(side_income_kwargs["partner_card_discount_amount"], 55.0)

        self.assertEqual(payload.fuel_reflection_amount, 2000.0)
        self.assertEqual(payload.company_fuel_reflection_amount, 1200.0)
        self.assertEqual(payload.utts_fuel_discount_amount, 84.0)
        self.assertEqual(payload.partner_card_discount_amount, 55.0)
        self.assertEqual(payload.side_income_net, 139.0)


if __name__ == "__main__":
    unittest.main()
