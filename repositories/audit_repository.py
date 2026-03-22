from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, fetch_df


def insert_audit_log_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (
            created_at, actor_username, actor_full_name, actor_role,
            entity_type, entity_id, action_type, summary, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["created_at"],
            values["actor_username"],
            values["actor_full_name"],
            values["actor_role"],
            values["entity_type"],
            values["entity_id"],
            values["action_type"],
            values["summary"],
            values["details_json"],
        ),
    )


def fetch_audit_log_df(conn: CompatConnection, *, limit: int = 500):
    return fetch_df(
        conn,
        """
        SELECT id, created_at, actor_username, actor_full_name, actor_role,
               entity_type, entity_id, action_type, summary, details_json
        FROM audit_logs
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
