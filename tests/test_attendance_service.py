from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from services import attendance_service


class _DummyConn:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class AttendanceServiceTests(unittest.TestCase):
    def test_resolve_daily_entry_values_builds_replacement_payload(self):
        values = attendance_service.resolve_daily_entry_values(
            entry_mode="Joker",
            primary_person_id=None,
            planned_personnel_id=11,
            actual_personnel_id=42,
            absence_reason="İzin",
            coverage_type="Joker",
            worked_hours=10.0,
            package_count=24.0,
            notes="Destek edildi",
        )

        self.assertEqual(values["planned_personnel_id"], 11)
        self.assertEqual(values["actual_personnel_id"], 42)
        self.assertEqual(values["status"], "Normal")
        self.assertEqual(values["absence_reason"], "İzin")
        self.assertEqual(values["coverage_type"], "Joker")
        self.assertEqual(values["package_count"], 24.0)

    def test_infer_daily_entry_mode_prefers_coverage_type_for_replacement_rows(self):
        entry_mode = attendance_service.infer_daily_entry_mode(
            status="Normal",
            planned_personnel_id=11,
            actual_personnel_id=42,
            coverage_type="Destek",
        )

        self.assertEqual(entry_mode, "Destek")

    def test_infer_daily_entry_mode_maps_missing_actual_to_weekly_off(self):
        entry_mode = attendance_service.infer_daily_entry_mode(
            status="İzin",
            planned_personnel_id=11,
            actual_personnel_id=None,
            coverage_type="",
        )

        self.assertEqual(entry_mode, "Haftalık İzin")

    def test_resolve_daily_entry_values_builds_weekly_off_payload(self):
        values = attendance_service.resolve_daily_entry_values(
            entry_mode="Haftalık İzin",
            primary_person_id=None,
            planned_personnel_id=11,
            actual_personnel_id=None,
            absence_reason="Raporlu",
            coverage_type="",
            worked_hours=10.0,
            package_count=24.0,
            notes="Doktor raporu",
        )

        self.assertEqual(values["planned_personnel_id"], 11)
        self.assertIsNone(values["actual_personnel_id"])
        self.assertEqual(values["status"], "Raporlu")
        self.assertEqual(values["worked_hours"], 0.0)
        self.assertEqual(values["package_count"], 0.0)

    def test_build_bulk_rows_from_parsed_maps_known_names_and_normalizes_status(self):
        rows = attendance_service.build_bulk_rows_from_parsed(
            [
                {
                    "person_label": "ali veli",
                    "worked_hours": 8,
                    "package_count": 24,
                    "entry_status": "normal",
                    "notes": "tamam",
                },
                {
                    "person_label": "tanimsiz kisi",
                    "worked_hours": 0,
                    "package_count": 0,
                    "entry_status": "izin",
                    "notes": "",
                },
            ],
            name_to_label={"ali veli": "Ali Veli (Kurye)"},
            normalize_entry_status_fn=lambda value: value.capitalize(),
        )

        self.assertEqual(rows[0]["Personel"], "Ali Veli (Kurye)")
        self.assertEqual(rows[0]["Durum"], "Normal")
        self.assertEqual(rows[1]["Personel"], "tanimsiz kisi")
        self.assertEqual(rows[1]["Durum"], "Izin")

    @patch("services.attendance_service.insert_daily_entry")
    def test_create_daily_entry_and_sync_commits_and_calls_sync(self, insert_entry_mock):
        conn = _DummyConn()
        sync_mock = MagicMock()

        result = attendance_service.create_daily_entry_and_sync(
            conn,
            entry_values={"entry_date": "2026-03-22"},
            affected_person_id=4,
            sync_personnel_business_rules_for_ids_fn=sync_mock,
        )

        insert_entry_mock.assert_called_once_with(conn, {"entry_date": "2026-03-22"})
        sync_mock.assert_called_once_with(conn, [4], create_onboarding=False, full_history=True)
        self.assertEqual(conn.commit_calls, 1)
        self.assertEqual(result, "Günlük kayıt eklendi.")

    @patch("services.attendance_service.update_daily_entry")
    def test_update_daily_entry_and_sync_uses_previous_and_new_actual_ids(self, update_entry_mock):
        conn = _DummyConn()
        sync_mock = MagicMock()

        result = attendance_service.update_daily_entry_and_sync(
            conn,
            entry_id=12,
            entry_values={"status": "Normal"},
            previous_actual_id=2,
            actual_id=5,
            sync_personnel_business_rules_for_ids_fn=sync_mock,
        )

        update_entry_mock.assert_called_once_with(conn, 12, {"status": "Normal"})
        sync_mock.assert_called_once_with(conn, [2, 5], create_onboarding=False, full_history=True)
        self.assertEqual(conn.commit_calls, 1)
        self.assertEqual(result, "Günlük puantaj kaydı güncellendi.")

    @patch("services.attendance_service.insert_daily_entry")
    def test_save_bulk_entries_and_sync_skips_empty_rows_and_inserts_actionable_rows(self, insert_entry_mock):
        conn = _DummyConn()
        sync_mock = MagicMock()
        edited_df = pd.DataFrame(
            [
                {"Personel": "Ali Veli (Kurye)", "Saat": 0.0, "Paket": 0, "Durum": "Normal", "Not": ""},
                {"Personel": "Ayse Test (Kurye)", "Saat": 8.0, "Paket": 24, "Durum": "normal", "Not": "tamam"},
            ]
        )

        inserted_count = attendance_service.save_bulk_entries_and_sync(
            conn,
            edited_df=edited_df,
            selected_date_iso="2026-03-22",
            restaurant_id=7,
            person_label_map={"Ali Veli (Kurye)": 1, "Ayse Test (Kurye)": 2},
            username="ebru",
            normalize_entry_status_fn=lambda value: value.capitalize(),
            sync_personnel_business_rules_for_ids_fn=sync_mock,
        )

        self.assertEqual(inserted_count, 1)
        insert_entry_mock.assert_called_once()
        inserted_payload = insert_entry_mock.call_args.args[1]
        self.assertEqual(inserted_payload["planned_personnel_id"], 2)
        self.assertEqual(inserted_payload["actual_personnel_id"], 2)
        self.assertEqual(inserted_payload["status"], "Normal")
        self.assertEqual(inserted_payload["absence_reason"], "")
        self.assertEqual(inserted_payload["coverage_type"], "")
        self.assertIn("Kaynak: Toplu Puantaj", inserted_payload["notes"])
        sync_mock.assert_called_once_with(conn, [2], create_onboarding=False, full_history=True)
        self.assertEqual(conn.commit_calls, 1)


if __name__ == "__main__":
    unittest.main()
