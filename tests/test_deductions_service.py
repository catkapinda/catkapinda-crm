from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.deductions_service import (
    build_deduction_selection_payload,
    bulk_delete_deductions_and_commit,
    create_deduction_and_commit,
    delete_deduction_and_commit,
    load_deductions_workspace_payload,
    normalize_deduction_amount_for_form,
    normalize_deduction_amount_for_storage,
    update_deduction_and_commit,
)


class _DummyConn:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class DeductionsServiceTests(TestCase):
    def test_load_workspace_payload_filters_manual_rows(self) -> None:
        raw_df = pd.DataFrame(
            [
                {"id": 1, "auto_source_key": ""},
                {"id": 2, "auto_source_key": "auto:motor_rental"},
                {"id": 3, "auto_source_key": None},
            ]
        )
        with patch("services.deductions_service.fetch_deduction_management_df", return_value=raw_df):
            payload = load_deductions_workspace_payload(_DummyConn())

        self.assertEqual(len(payload.raw_df), 3)
        self.assertEqual(payload.manual_deductions_df["id"].tolist(), [1, 3])

    def test_build_selection_payload_maps_person_and_type(self) -> None:
        raw_df = pd.DataFrame(
            [
                {
                    "id": 17,
                    "personnel_id": 5,
                    "deduction_type": "Yakıt",
                    "deduction_date": "2026-03-22",
                    "amount": "1250.50",
                    "auto_source_key": "",
                }
            ]
        )
        payload = build_deduction_selection_payload(
            raw_df,
            selected_id=17,
            person_opts={"Ali Veli": 5, "Ayse Yilmaz": 6},
            deduction_types=["Yakıt", "HGS", "İdari Ceza"],
            safe_float_fn=lambda value, default=0.0: float(value or default),
            is_system_personnel_auto_deduction_key_fn=lambda value: str(value or "").startswith("auto:"),
        )

        self.assertEqual(payload.current_person, "Ali Veli")
        self.assertEqual(payload.person_index, 0)
        self.assertEqual(payload.type_index, 0)
        self.assertEqual(payload.current_date, date(2026, 3, 22))
        self.assertFalse(payload.is_auto_record)
        self.assertEqual(payload.row["amount"], 1250.50)
        self.assertEqual(payload.display_amount, 1250.50)

    def test_build_selection_payload_returns_base_amount_for_hgs(self) -> None:
        raw_df = pd.DataFrame(
            [
                {
                    "id": 22,
                    "personnel_id": 6,
                    "deduction_type": "HGS",
                    "deduction_date": "2026-03-22",
                    "amount": 1200.0,
                    "auto_source_key": "",
                }
            ]
        )
        payload = build_deduction_selection_payload(
            raw_df,
            selected_id=22,
            person_opts={"Ayse Yilmaz": 6},
            deduction_types=["Yakıt", "HGS", "İdari Ceza"],
            safe_float_fn=lambda value, default=0.0: float(value or default),
            is_system_personnel_auto_deduction_key_fn=lambda value: str(value or "").startswith("auto:"),
        )

        self.assertEqual(payload.display_amount, 1000.0)

    def test_create_deduction_commits_and_returns_message(self) -> None:
        conn = _DummyConn()
        deduction_values = {"deduction_date": "2026-03-31", "amount": 750.0}

        with patch("services.deductions_service.insert_deduction_record") as insert_mock:
            message = create_deduction_and_commit(conn, deduction_values=deduction_values)

        insert_mock.assert_called_once_with(conn, deduction_values)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(conn.rollback_count, 0)
        self.assertIn("2026-03-31", message)

    def test_create_hgs_deduction_stores_vat_included_amount(self) -> None:
        conn = _DummyConn()
        deduction_values = {"deduction_date": "2026-03-31", "deduction_type": "HGS", "amount": 1000.0}

        with patch("services.deductions_service.insert_deduction_record") as insert_mock:
            create_deduction_and_commit(conn, deduction_values=deduction_values)

        inserted_payload = insert_mock.call_args.args[1]
        self.assertEqual(inserted_payload["amount"], 1200.0)

    def test_update_hgs_deduction_stores_vat_included_amount(self) -> None:
        conn = _DummyConn()
        deduction_values = {"deduction_date": "2026-03-31", "deduction_type": "HGS", "amount": 250.0}

        with patch("services.deductions_service.update_deduction_record") as update_mock:
            update_deduction_and_commit(conn, deduction_id=8, deduction_values=deduction_values)

        updated_payload = update_mock.call_args.args[2]
        self.assertEqual(updated_payload["amount"], 300.0)

    def test_update_deduction_rolls_back_on_failure(self) -> None:
        conn = _DummyConn()
        deduction_values = {"deduction_date": "2026-03-31", "amount": 900.0}

        with patch("services.deductions_service.update_deduction_record", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                update_deduction_and_commit(conn, deduction_id=8, deduction_values=deduction_values)

        self.assertEqual(conn.commit_count, 0)
        self.assertEqual(conn.rollback_count, 1)

    def test_delete_deduction_commits(self) -> None:
        conn = _DummyConn()

        with patch("services.deductions_service.delete_deduction_record") as delete_mock:
            message = delete_deduction_and_commit(conn, deduction_id=11)

        delete_mock.assert_called_once_with(conn, 11)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(conn.rollback_count, 0)
        self.assertEqual(message, "Kesinti silindi.")

    def test_bulk_delete_returns_deleted_count_message(self) -> None:
        conn = _DummyConn()

        with patch("services.deductions_service.delete_deduction_records", return_value=3) as delete_mock:
            message = bulk_delete_deductions_and_commit(conn, deduction_ids=[1, 2, 3])

        delete_mock.assert_called_once_with(conn, [1, 2, 3])
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(message, "3 manuel kesinti kaydı toplu olarak silindi.")

    def test_hgs_amount_helpers_round_trip(self) -> None:
        self.assertEqual(
            normalize_deduction_amount_for_storage("HGS", 100.0, safe_float_fn=lambda value, default=0.0: float(value or default)),
            120.0,
        )
        self.assertEqual(
            normalize_deduction_amount_for_form("HGS", 120.0, safe_float_fn=lambda value, default=0.0: float(value or default)),
            100.0,
        )
