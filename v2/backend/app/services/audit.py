from __future__ import annotations

import psycopg

from app.repositories.audit import (
    count_audit_management_records,
    fetch_audit_filter_options,
    fetch_audit_management_records,
    fetch_audit_summary,
    fetch_recent_audit_records,
)
from app.schemas.audit import (
    AuditDashboardResponse,
    AuditEntry,
    AuditManagementResponse,
    AuditModuleStatus,
    AuditSummary,
)


def _build_audit_entry(row: dict[str, object]) -> AuditEntry:
    return AuditEntry(
        id=int(row["id"]),
        created_at=row["created_at"],
        actor_username=str(row.get("actor_username") or ""),
        actor_full_name=str(row.get("actor_full_name") or ""),
        actor_role=str(row.get("actor_role") or ""),
        entity_type=str(row.get("entity_type") or ""),
        entity_id=str(row.get("entity_id") or ""),
        action_type=str(row.get("action_type") or ""),
        summary=str(row.get("summary") or ""),
        details_json=str(row.get("details_json") or ""),
    )


def build_audit_status() -> AuditModuleStatus:
    return AuditModuleStatus(
        module="audit",
        status="active",
        next_slice="audit-management",
    )


def build_audit_dashboard(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> AuditDashboardResponse:
    summary_values = fetch_audit_summary(conn)
    recent_rows = fetch_recent_audit_records(conn, limit=limit)
    options = fetch_audit_filter_options(conn)
    return AuditDashboardResponse(
        module="audit",
        status="active",
        summary=AuditSummary(**summary_values),
        recent_entries=[_build_audit_entry(row) for row in recent_rows],
        action_options=options["action_options"],
        entity_options=options["entity_options"],
        actor_options=options["actor_options"],
    )


def build_audit_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    action_type: str | None = None,
    entity_type: str | None = None,
    actor_name: str | None = None,
    search: str | None = None,
) -> AuditManagementResponse:
    rows = fetch_audit_management_records(
        conn,
        limit=limit,
        action_type=action_type or None,
        entity_type=entity_type or None,
        actor_name=actor_name or None,
        search=search,
    )
    options = fetch_audit_filter_options(conn)
    return AuditManagementResponse(
        total_entries=count_audit_management_records(
            conn,
            action_type=action_type or None,
            entity_type=entity_type or None,
            actor_name=actor_name or None,
            search=search,
        ),
        entries=[_build_audit_entry(row) for row in rows],
        action_options=options["action_options"],
        entity_options=options["entity_options"],
        actor_options=options["actor_options"],
    )
