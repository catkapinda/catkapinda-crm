from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.restaurant_service import (
    create_restaurant_and_commit,
    delete_restaurant_with_guards,
    load_restaurant_workspace_payload,
    toggle_restaurant_status_and_commit,
    update_restaurant_and_commit,
)


class _DummyConn:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class RestaurantServiceTests(TestCase):
    def test_load_workspace_payload_adds_missing_optional_columns_with_repository_patch(self) -> None:
        df = pd.DataFrame([{"id": 1, "brand": "Fasuli", "branch": "Beyoglu"}])

        with patch("services.restaurant_service.fetch_restaurant_management_df", return_value=df):
            payload = load_restaurant_workspace_payload(
                _DummyConn(),
                ensure_dataframe_columns_fn=lambda frame, defaults: frame.assign(
                    **{key: frame[key] if key in frame.columns else value for key, value in defaults.items()}
                ),
            )

        self.assertIn("company_title", payload.df.columns)
        self.assertIn("tax_number", payload.df.columns)
        self.assertEqual(payload.df.iloc[0]["company_title"], "")

    def test_create_restaurant_commits(self) -> None:
        conn = _DummyConn()
        values = {"brand": "Fasuli", "branch": "Beyoglu"}

        with patch("services.restaurant_service.insert_restaurant_record") as insert_mock:
            message = create_restaurant_and_commit(conn, restaurant_values=values)

        insert_mock.assert_called_once_with(conn, values)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(message, "Restoran başarıyla eklendi.")

    def test_update_restaurant_rolls_back_on_failure(self) -> None:
        conn = _DummyConn()
        values = {"brand": "Fasuli", "branch": "Vatan"}

        with patch("services.restaurant_service.update_restaurant_record", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                update_restaurant_and_commit(conn, restaurant_id=8, restaurant_values=values)

        self.assertEqual(conn.commit_count, 0)
        self.assertEqual(conn.rollback_count, 1)

    def test_toggle_restaurant_status_switches_to_passive(self) -> None:
        conn = _DummyConn()

        with patch("services.restaurant_service.update_restaurant_status") as status_mock:
            message = toggle_restaurant_status_and_commit(conn, restaurant_id=3, current_active=1)

        status_mock.assert_called_once_with(conn, 3, 0)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(message, "Restoran başarıyla pasife alındı.")

    def test_delete_restaurant_with_guards_blocks_when_linked_records_exist(self) -> None:
        conn = _DummyConn()

        with patch("services.restaurant_service.count_restaurant_linked_personnel", return_value=1), \
             patch("services.restaurant_service.count_restaurant_linked_daily_entries", return_value=0), \
             patch("services.restaurant_service.count_restaurant_linked_deductions", return_value=0):
            with self.assertRaises(ValueError):
                delete_restaurant_with_guards(conn, restaurant_id=5)

        self.assertEqual(conn.commit_count, 0)

    def test_delete_restaurant_with_guards_deletes_when_clean(self) -> None:
        conn = _DummyConn()

        with patch("services.restaurant_service.count_restaurant_linked_personnel", return_value=0), \
             patch("services.restaurant_service.count_restaurant_linked_daily_entries", return_value=0), \
             patch("services.restaurant_service.count_restaurant_linked_deductions", return_value=0), \
             patch("services.restaurant_service.delete_restaurant_record") as delete_mock:
            message = delete_restaurant_with_guards(conn, restaurant_id=7)

        delete_mock.assert_called_once_with(conn, 7)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(message, "Restoran kaydı kalıcı olarak silindi.")
