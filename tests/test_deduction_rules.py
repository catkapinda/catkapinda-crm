from __future__ import annotations

import unittest

import pandas as pd

from rules.deduction_rules import (
    DEDUCTION_TYPE_OPTIONS,
    MOTOR_DAMAGE_DEDUCTION_TYPE,
    MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    calculate_fuel_discount_summary,
    filter_payroll_effective_deductions_df,
    get_deduction_type_caption,
)


class DeductionRulesTests(unittest.TestCase):
    def test_deduction_type_options_include_avans_and_partner_discount(self) -> None:
        self.assertIn("Avans", DEDUCTION_TYPE_OPTIONS)
        self.assertIn("Partner Kart İndirimi", DEDUCTION_TYPE_OPTIONS)
        self.assertIn(MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE, DEDUCTION_TYPE_OPTIONS)
        self.assertIn(MOTOR_DAMAGE_DEDUCTION_TYPE, DEDUCTION_TYPE_OPTIONS)

    def test_filter_payroll_effective_deductions_excludes_side_income_only_rows(self) -> None:
        deductions_df = pd.DataFrame(
            [
                {"deduction_type": "Yakıt", "amount": 1200.0},
                {"deduction_type": "Avans", "amount": 800.0},
                {"deduction_type": "Partner Kart İndirimi", "amount": 95.0},
            ]
        )

        filtered_df = filter_payroll_effective_deductions_df(deductions_df)

        self.assertEqual(filtered_df["deduction_type"].tolist(), ["Yakıt", "Avans"])

    def test_filter_payroll_effective_deductions_excludes_maintenance_for_company_rental_motor(self) -> None:
        deductions_df = pd.DataFrame(
            [
                {"personnel_id": 1, "deduction_type": MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE, "amount": 900.0},
                {"personnel_id": 1, "deduction_type": MOTOR_DAMAGE_DEDUCTION_TYPE, "amount": 350.0},
                {"personnel_id": 2, "deduction_type": MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE, "amount": 1200.0},
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {"id": 1, "vehicle_type": "Çat Kapında", "motor_purchase": "Hayır"},
                {"id": 2, "vehicle_type": "Çat Kapında", "motor_purchase": "Evet"},
            ]
        )

        filtered_df = filter_payroll_effective_deductions_df(deductions_df, personnel_df)

        self.assertEqual(
            filtered_df[["personnel_id", "deduction_type"]].to_dict("records"),
            [
                {"personnel_id": 1, "deduction_type": MOTOR_DAMAGE_DEDUCTION_TYPE},
                {"personnel_id": 2, "deduction_type": MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE},
            ],
        )

    def test_filter_payroll_effective_deductions_normalizes_legacy_types(self) -> None:
        deductions_df = pd.DataFrame(
            [
                {"personnel_id": 1, "deduction_type": "Bakım", "amount": 900.0},
                {"personnel_id": 1, "deduction_type": "Hasar", "amount": 350.0},
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {"id": 1, "vehicle_type": "Çat Kapında", "motor_purchase": "Hayır"},
            ]
        )

        filtered_df = filter_payroll_effective_deductions_df(deductions_df, personnel_df)

        self.assertEqual(filtered_df["deduction_type"].tolist(), ["Hasar"])

    def test_get_deduction_type_caption_explains_maintenance_rule(self) -> None:
        caption = get_deduction_type_caption(MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE)

        self.assertIn("Çat Kapında kiralık motorları şirket öder", caption)
        self.assertIn("satılık motor ve kendi motorunda bakım kuryeden kesilir", caption)

    def test_get_deduction_type_caption_explains_damage_rule(self) -> None:
        caption = get_deduction_type_caption(MOTOR_DAMAGE_DEDUCTION_TYPE)

        self.assertIn("tüm motor tiplerinde kuryeye yansıtılır", caption)

    def test_calculate_fuel_discount_summary_uses_company_motor_rows_only_for_utts_discount(self) -> None:
        deductions_df = pd.DataFrame(
            [
                {"personnel_id": 1, "deduction_type": "Yakıt", "amount": 1200.0},
                {"personnel_id": 2, "deduction_type": "Yakıt", "amount": 800.0},
                {"personnel_id": 2, "deduction_type": "Partner Kart İndirimi", "amount": 55.0},
            ]
        )
        personnel_df = pd.DataFrame(
            [
                {"id": 1, "vehicle_type": "Çat Kapında"},
                {"id": 2, "vehicle_type": "Kendi Motoru"},
            ]
        )

        summary = calculate_fuel_discount_summary(deductions_df, personnel_df)

        self.assertEqual(summary["fuel_reflection_amount"], 2000.0)
        self.assertEqual(summary["company_fuel_reflection_amount"], 1200.0)
        self.assertEqual(summary["utts_fuel_discount_amount"], 84.0)
        self.assertEqual(summary["partner_card_discount_amount"], 55.0)


if __name__ == "__main__":
    unittest.main()
