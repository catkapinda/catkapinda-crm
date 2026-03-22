from __future__ import annotations

import unittest
from unittest.mock import ANY, MagicMock, patch

from services import personnel_service
from services.permission_service import PermissionDeniedError


class _DummyConn:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class PersonnelServiceTests(unittest.TestCase):
    @patch("services.personnel_service.fetch_person_code_values")
    def test_build_next_person_code_uses_highest_matching_suffix(self, fetch_codes_mock):
        fetch_codes_mock.return_value = ["CK-K01", "CK-K09", "CK-K11", "CK-BM03", "INVALID"]

        result = personnel_service.build_next_person_code(object(), "Kurye")

        self.assertEqual(result, "CK-K12")

    @patch("services.personnel_service.build_next_person_code")
    def test_build_personnel_code_display_values_keeps_existing_code_when_role_same(self, next_code_mock):
        next_code_mock.return_value = "CK-K12"

        suggested_code, display_code = personnel_service.build_personnel_code_display_values(
            object(),
            current_person_code="CK-K03",
            original_role="Kurye",
            effective_role="Kurye",
        )

        self.assertEqual(suggested_code, "CK-K12")
        self.assertEqual(display_code, "CK-K03")

    @patch("services.personnel_service.fetch_personnel_by_code")
    @patch("services.personnel_service.insert_personnel_record")
    @patch("services.personnel_service.build_next_person_code")
    def test_create_person_with_onboarding_returns_summary_and_runs_side_effects(
        self,
        next_code_mock,
        insert_person_mock,
        fetch_person_by_code_mock,
    ):
        conn = _DummyConn()
        next_code_mock.return_value = "CK-K99"
        fetch_person_by_code_mock.return_value = {"id": 9, "full_name": "Test Kurye"}
        insert_issue_mock = MagicMock(return_value=101)
        post_installments_mock = MagicMock()
        sync_role_snapshot_mock = MagicMock()
        sync_business_rules_mock = MagicMock()

        result = personnel_service.create_person_with_onboarding(
            conn,
            role="Kurye",
            person_values={
                "full_name": "Test Kurye",
                "phone": "555",
                "address": "",
                "tc_no": "1",
                "iban": "TR",
                "emergency_contact_name": "",
                "emergency_contact_phone": "",
                "accounting_type": "Kendi Muhasebecisi",
                "new_company_setup": "Hayır",
                "accounting_revenue": 0.0,
                "accountant_cost": 0.0,
                "company_setup_revenue": 0.0,
                "company_setup_cost": 0.0,
                "assigned_restaurant_id": None,
                "vehicle_type": "Kendi Motoru",
                "motor_rental": "Hayır",
                "motor_purchase": "Hayır",
                "motor_purchase_start_date": None,
                "motor_purchase_commitment_months": 0,
                "motor_rental_monthly_amount": 0.0,
                "motor_purchase_sale_price": 0.0,
                "motor_purchase_monthly_amount": 0.0,
                "motor_purchase_installment_count": 0,
                "current_plate": "34ABC34",
                "start_date": "2026-03-22",
                "cost_model": "standard_courier",
                "monthly_fixed_cost": 0.0,
                "notes": "",
            },
            onboarding_issue_payloads=[
                {
                    "issue_date": personnel_service.date(2026, 3, 22),
                    "item_name": "Kask",
                    "quantity": 1,
                    "unit_cost": 100.0,
                    "unit_sale_price": 150.0,
                    "installment_count": 2,
                    "vat_rate": 20.0,
                    "notes": "test",
                }
            ],
            safe_int_fn=lambda value, default=0: int(value if value is not None else default),
            safe_float_fn=lambda value, default=0.0: float(value if value is not None else default),
            insert_equipment_issue_and_get_id_fn=insert_issue_mock,
            post_equipment_installments_fn=post_installments_mock,
            sync_person_current_role_snapshot_fn=sync_role_snapshot_mock,
            sync_person_business_rules_fn=sync_business_rules_mock,
        )

        insert_person_mock.assert_called_once()
        insert_issue_mock.assert_called_once()
        post_installments_mock.assert_called_once()
        sync_role_snapshot_mock.assert_called_once()
        sync_business_rules_mock.assert_called_once()
        self.assertEqual(conn.commit_calls, 2)
        self.assertEqual(result.created_person_id, 9)
        self.assertEqual(result.auto_code, "CK-K99")
        self.assertIn("1 onboarding ekipmanı kaydedildi", result.success_text)

    @patch("services.personnel_service.fetch_personnel_by_id")
    @patch("services.personnel_service.update_personnel_status")
    def test_toggle_person_status_and_sync_updates_exit_date_and_calls_sync(
        self,
        update_status_mock,
        fetch_person_mock,
    ):
        conn = _DummyConn()
        fetch_person_mock.return_value = {"id": 5}
        sync_business_rules_mock = MagicMock()

        result = personnel_service.toggle_person_status_and_sync(
            conn,
            person_id=5,
            current_status="Aktif",
            sync_person_business_rules_fn=sync_business_rules_mock,
        )

        update_status_mock.assert_called_once_with(conn, 5, "Pasif", ANY)
        fetch_person_mock.assert_called_once_with(conn, 5)
        sync_business_rules_mock.assert_called_once_with(conn, {"id": 5}, create_onboarding=False)
        self.assertEqual(conn.commit_calls, 1)
        self.assertIn("pasife", result.success_text)

    def test_delete_person_with_dependencies_rejects_sef_role(self):
        conn = _DummyConn()
        dependency_mock = MagicMock(return_value={"puantaj": 0, "kesinti": 0, "rol_gecmisi": 0, "plaka": 0, "zimmet": 0, "box_iade": 0})
        delete_mock = MagicMock()

        with self.assertRaises(PermissionDeniedError):
            personnel_service.delete_person_with_dependencies(
                conn,
                person_id=4,
                get_personnel_dependency_counts_fn=dependency_mock,
                delete_personnel_and_dependencies_fn=delete_mock,
                actor_role="sef",
            )

        dependency_mock.assert_not_called()
        delete_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
