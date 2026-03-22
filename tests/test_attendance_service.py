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
        self.assertIn("Kaynak: Toplu Puantaj", inserted_payload["notes"])
        sync_mock.assert_called_once_with(conn, [2], create_onboarding=False, full_history=True)
        self.assertEqual(conn.commit_calls, 1)


if __name__ == "__main__":
    unittest.main()
