from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from services.reporting_service import load_monthly_payroll_source_payload


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


if __name__ == "__main__":
    unittest.main()
