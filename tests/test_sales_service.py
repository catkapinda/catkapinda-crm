from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.sales_service import (
    build_sales_hero_stats,
    build_sales_selection_payload,
    create_sales_lead_and_commit,
    delete_sales_lead_and_commit,
    load_sales_workspace_payload,
    update_sales_lead_and_commit,
    validate_sales_lead_values,
)


class _DummyConn:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class SalesServiceTests(TestCase):
    def test_load_workspace_payload_adds_defaults(self) -> None:
        df = pd.DataFrame([{"id": 1, "restaurant_name": "Burger House"}])

        with patch("services.sales_service.fetch_sales_leads_df", return_value=df):
            payload = load_sales_workspace_payload(
                _DummyConn(),
                ensure_dataframe_columns_fn=lambda frame, defaults: frame.assign(
                    **{key: frame[key] if key in frame.columns else value for key, value in defaults.items()}
                ),
            )

        self.assertIn("city", payload.df.columns)
        self.assertEqual(payload.df.iloc[0]["city"], "")

    def test_build_sales_hero_stats_counts_pipeline(self) -> None:
        df = pd.DataFrame(
            [
                {"status": "Yeni Talep"},
                {"status": "Teklif İletildi"},
                {"status": "Sözleşme İmzalandı"},
            ]
        )
        stats = build_sales_hero_stats(df, safe_int_fn=lambda value, default=0: int(value if value is not None else default))
        self.assertEqual(stats[0][1], 3)
        self.assertEqual(stats[1][1], 2)
        self.assertEqual(stats[3][1], 1)

    def test_validate_sales_lead_values_requires_core_fields(self) -> None:
        errors = validate_sales_lead_values(
            restaurant_name="",
            city="",
            district="",
            contact_name="",
            contact_phone="",
            status="",
        )
        self.assertGreaterEqual(len(errors), 5)

    def test_build_sales_selection_payload_resolves_indexes(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "id": 7,
                    "status": "Teklif İletildi",
                    "lead_source": "Telefon",
                }
            ]
        )
        payload = build_sales_selection_payload(
            df,
            selected_id=7,
            status_options=["Yeni Talep", "Teklif İletildi"],
            source_options=["Mail", "Telefon"],
        )
        self.assertEqual(payload.status_index, 1)
        self.assertEqual(payload.source_index, 1)

    def test_create_sales_lead_commits(self) -> None:
        conn = _DummyConn()
        values = {"restaurant_name": "Burger House", "status": "Yeni Talep", "lead_source": "Telefon"}

        with patch("services.sales_service.insert_sales_lead_record") as insert_mock:
            message = create_sales_lead_and_commit(conn, sales_values=values)

        insert_mock.assert_called_once()
        inserted_payload = insert_mock.call_args.args[1]
        self.assertEqual(inserted_payload["restaurant_name"], "Burger House")
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(message, "Satış fırsatı başarıyla eklendi.")

    def test_update_sales_lead_rolls_back_on_failure(self) -> None:
        conn = _DummyConn()
        values = {"restaurant_name": "Burger House", "status": "Teklif İletildi", "lead_source": "Telefon"}

        with patch("services.sales_service.update_sales_lead_record", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                update_sales_lead_and_commit(conn, lead_id=5, sales_values=values)

        self.assertEqual(conn.commit_count, 0)
        self.assertEqual(conn.rollback_count, 1)

    def test_delete_sales_lead_commits(self) -> None:
        conn = _DummyConn()

        with patch("services.sales_service.delete_sales_lead_record") as delete_mock:
            message = delete_sales_lead_and_commit(conn, lead_id=9)

        delete_mock.assert_called_once_with(conn, 9)
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(message, "Satış fırsatı silindi.")
