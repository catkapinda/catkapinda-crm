from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from infrastructure.audit_engine import build_audit_actor_payload, serialize_audit_details, utc_now_iso
from repositories.audit_repository import fetch_audit_log_df, insert_audit_log_record
from services.permission_service import require_action_access


@dataclass
class AuditWorkspacePayload:
    raw_df: Any
    filtered_df: Any
    action_options: list[str]
    entity_options: list[str]
    actor_options: list[str]


def record_audit_event(
    conn,
    *,
    entity_type: str,
    action_type: str,
    summary: str,
    entity_id: Any = None,
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> bool:
    if not hasattr(conn, "execute"):
        return False
    actor = build_audit_actor_payload()
    savepoint_created = False
    savepoint_name = "audit_event_write"
    try:
        if not commit:
            conn.execute(f"SAVEPOINT {savepoint_name}")
            savepoint_created = True
        insert_audit_log_record(
            conn,
            {
                "created_at": utc_now_iso(),
                "actor_username": actor["actor_username"],
                "actor_full_name": actor["actor_full_name"],
                "actor_role": actor["actor_role"],
                "entity_type": str(entity_type or ""),
                "entity_id": "" if entity_id is None else str(entity_id),
                "action_type": str(action_type or ""),
                "summary": str(summary or ""),
                "details_json": serialize_audit_details(details),
            },
        )
        if commit:
            conn.commit()
        elif savepoint_created:
            conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        return True
    except Exception:
        try:
            if commit:
                conn.rollback()
            elif savepoint_created:
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        except Exception:
            pass
        return False


def load_audit_workspace_payload(
    conn,
    *,
    actor_role: str = "admin",
    search_query: str = "",
    action_filter: str = "Tümü",
    entity_filter: str = "Tümü",
    actor_filter: str = "Tümü",
    limit: int = 500,
) -> AuditWorkspacePayload:
    require_action_access(actor_role, "audit.view")
    raw_df = fetch_audit_log_df(conn, limit=limit)
    if raw_df.empty:
        return AuditWorkspacePayload(
            raw_df=raw_df,
            filtered_df=raw_df,
            action_options=["Tümü"],
            entity_options=["Tümü"],
            actor_options=["Tümü"],
        )

    filtered_df = raw_df.copy()
    if action_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["action_type"] == action_filter].copy()
    if entity_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["entity_type"] == entity_filter].copy()
    if actor_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["actor_full_name"] == actor_filter].copy()
    query = str(search_query or "").strip().lower()
    if query:
        search_series = (
            filtered_df["summary"].fillna("").astype(str) + " "
            + filtered_df["details_json"].fillna("").astype(str) + " "
            + filtered_df["entity_id"].fillna("").astype(str)
        ).str.lower()
        filtered_df = filtered_df[search_series.str.contains(query, na=False)].copy()

    return AuditWorkspacePayload(
        raw_df=raw_df,
        filtered_df=filtered_df,
        action_options=["Tümü"] + sorted(raw_df["action_type"].dropna().astype(str).unique().tolist()),
        entity_options=["Tümü"] + sorted(raw_df["entity_type"].dropna().astype(str).unique().tolist()),
        actor_options=["Tümü"] + sorted(raw_df["actor_full_name"].dropna().astype(str).unique().tolist()),
    )
