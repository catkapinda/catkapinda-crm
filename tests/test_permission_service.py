from __future__ import annotations

from unittest import TestCase

from services.permission_service import (
    PermissionDeniedError,
    can_access_menu,
    can_perform_action,
    get_allowed_menu_items,
    require_action_access,
    require_menu_access,
)


class PermissionServiceTests(TestCase):
    def test_admin_menu_contains_admin_sections(self) -> None:
        menu_items = get_allowed_menu_items("admin")

        self.assertIn("Genel Bakış", menu_items)
        self.assertIn("Sistem Kayıtları", menu_items)
        self.assertIn("Raporlar ve Karlılık", menu_items)

    def test_sef_menu_is_limited(self) -> None:
        menu_items = get_allowed_menu_items("sef")

        self.assertIn("Satış", menu_items)
        self.assertIn("Personel Yönetimi", menu_items)
        self.assertIn("Puantaj", menu_items)
        self.assertNotIn("Restoran Yönetimi", menu_items)
        self.assertNotIn("Sistem Kayıtları", menu_items)

    def test_sef_can_manage_deductions(self) -> None:
        self.assertTrue(can_perform_action("sef", "deduction.create"))
        self.assertTrue(can_perform_action("sef", "deduction.bulk_delete"))

    def test_sef_cannot_delete_personnel(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            require_action_access("sef", "personnel.delete")

    def test_require_menu_access_rejects_admin_only_menu_for_sef(self) -> None:
        self.assertFalse(can_access_menu("sef", "Raporlar ve Karlılık"))
        with self.assertRaises(PermissionDeniedError):
            require_menu_access("sef", "Raporlar ve Karlılık")

    def test_mobile_ops_menu_only_contains_operational_items(self) -> None:
        menu_items = get_allowed_menu_items("mobile_ops")

        self.assertEqual(menu_items, ["Personel Yönetimi", "Puantaj"])

    def test_mobile_ops_cannot_view_personnel_list_or_plate_workspace(self) -> None:
        self.assertFalse(can_perform_action("mobile_ops", "personnel.list"))
        self.assertFalse(can_perform_action("mobile_ops", "personnel.plate"))

    def test_sef_can_view_personnel_list_and_plate_workspace(self) -> None:
        self.assertTrue(can_perform_action("sef", "personnel.list"))
        self.assertTrue(can_perform_action("sef", "personnel.plate"))

    def test_sef_cannot_delete_sales_lead(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            require_action_access("sef", "sales.delete")
