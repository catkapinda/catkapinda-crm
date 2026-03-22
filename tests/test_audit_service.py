from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from services.audit_service import load_audit_workspace_payload, record_audit_event
from services.permission_service import PermissionDeniedError


class _DummyConn:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    def execute(self, *args, **kwargs):
        return None

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class AuditServiceTests(TestCase):
    def test_record_audit_event_commits_when_insert_succeeds(self) -> None:
        conn = _DummyConn()
        with patch("services.audit_service.insert_audit_log_record") as insert_mock, \
             patch("services.audit_service.build_audit_actor_payload", return_value={"actor_username": "ebru", "actor_full_name": "Ebru Aslan", "actor_role": "admin"}), \
             patch("services.audit_service.utc_now_iso", return_value="2026-03-22T18:00:00+00:00"):
            result = record_audit_event(
                conn,
                entity_type="personnel",
                entity_id=7,
                action_type="create",
                summary="Personel eklendi.",
                details={"role": "Kurye"},
            )

        self.assertTrue(result)
        insert_mock.assert_called_once()
        self.assertEqual(conn.commit_count, 1)
        self.assertEqual(conn.rollback_count, 0)

    def test_record_audit_event_returns_false_when_insert_fails(self) -> None:
        conn = _DummyConn()
        with patch("services.audit_service.insert_audit_log_record", side_effect=RuntimeError("boom")), \
             patch("services.audit_service.build_audit_actor_payload", return_value={"actor_username": "ebru", "actor_full_name": "Ebru Aslan", "actor_role": "admin"}):
            result = record_audit_event(
                conn,
                entity_type="purchase",
                action_type="delete",
                summary="Satın alma silindi.",
            )

        self.assertFalse(result)
        self.assertEqual(conn.rollback_count, 1)

    def test_load_audit_workspace_payload_filters_rows(self) -> None:
        raw_df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "created_at": "2026-03-22T18:00:00+00:00",
                    "actor_username": "ebru",
                    "actor_full_name": "Ebru Aslan",
                    "actor_role": "admin",
                    "entity_type": "personnel",
                    "entity_id": "7",
                    "action_type": "create",
                    "summary": "Personel eklendi",
                    "details_json": "{\"role\": \"Kurye\"}",
                },
                {
                    "id": 2,
                    "created_at": "2026-03-22T18:05:00+00:00",
                    "actor_username": "mert",
                    "actor_full_name": "Mert Kurtuluş",
                    "actor_role": "admin",
                    "entity_type": "purchase",
                    "entity_id": "3",
                    "action_type": "delete",
                    "summary": "Satın alma silindi",
                    "details_json": "{}",
                },
            ]
        )
        with patch("services.audit_service.fetch_audit_log_df", return_value=raw_df):
            payload = load_audit_workspace_payload(
                object(),
                search_query="kurye",
                action_filter="create",
                entity_filter="personnel",
                actor_filter="Ebru Aslan",
            )

        self.assertEqual(len(payload.filtered_df), 1)
        self.assertEqual(payload.filtered_df.iloc[0]["id"], 1)
        self.assertIn("create", payload.action_options)
        self.assertIn("personnel", payload.entity_options)
        self.assertIn("Ebru Aslan", payload.actor_options)

    def test_load_audit_workspace_payload_rejects_sef_role(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            load_audit_workspace_payload(object(), actor_role="sef")
