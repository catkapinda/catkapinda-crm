from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.purchases_service import (
    build_purchase_selection_payload,
    create_purchase_and_commit,
    delete_purchase_and_commit,
    load_purchases_workspace_payload,
    update_purchase_and_commit,
)


class _DummyConn:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class PurchasesServiceTests(TestCase):
    def test_load_workspace_payload_returns_repository_data(self) -> None:
        purchases_df = pd.DataFrame([{"id": 1, "item_name": "Kask"}])

        with patch("services.purchases_service.fetch_purchases_management_df", return_value=purchases_df):
            payload = load_purchases_workspace_payload(_DummyConn())

        self.assertEqual(payload.purchases["id"].tolist(), [1])

    def test_build_purchase_selection_payload_maps_item_and_date(self) -> None:
        purchases = pd.DataFrame(
            [
                {
                    "id": 7,
                    "purchase_date": "2026-03-15",
                    "item_name": "Box",
                    "quantity": 5,
                }
            ]
        )

        payload = build_purchase_selection_payload(
            purchases,
            selected_id=7,
            item_options=["Kask", "Box", "Mont"],
        )

        self.assertEqual(payload.current_date, date(2026, 3, 15))
        self.assertEqual(payload.item_index, 1)
        self.assertEqual(int(payload.row["id"]), 7)

    def test_create_purchase_commits_and_formats_message(self) -> None:
        conn = _DummyConn()
        purchase_values = {"unit_cost": 250.0}

        with patch("services.purchases_service.insert_purchase_record") as insert_mock:
            message = create_purchase_and_commit(
                conn,
                purchase_values=purchase_values,
                fmt_try_fn=lambda value: f"{value:.2f} TL",
            )

        insert_mock.assert_called_once_with(conn, purchase_values)
        self.assertEqual(conn.commit_count, 1)
        self.assertIn("250.00 TL", message)

    def test_update_purchase_rolls_back_on_failure(self) -> None:
        conn = _DummyConn()
        purchase_values = {"unit_cost": 310.0}

        with patch("services.purchases_service.update_purchase_record", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                update_purchase_and_commit(
                    conn,
                    purchase_id=4,
                    purchase_values=purchase_values,
                    fmt_try_fn=str,
                )

        self.assertEqual(conn.commit_count, 0)
        self.assertEqual(conn.rollback_count, 1)

    def test_delete_purchase_commits(self) -> None:
        conn = _DummyConn()

        with patch("services.purchases_service.delete_purchase_record") as delete_mock:
            message = delete_purchase_and_commit(conn, purchase_id=9)

        delete_mock.assert_called_once_with(conn, 9)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(conn.rollback_count, 0)
        self.assertEqual(message, "Satın alma kaydı silindi.")
