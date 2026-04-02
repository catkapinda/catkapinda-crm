from typing import Annotated

from fastapi import APIRouter, Depends, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.audit import AuditDashboardResponse, AuditManagementResponse, AuditModuleStatus
from app.services.audit import build_audit_dashboard, build_audit_management, build_audit_status

router = APIRouter()


@router.get("/status", response_model=AuditModuleStatus)
def get_audit_status() -> AuditModuleStatus:
    return build_audit_status()


@router.get("/dashboard", response_model=AuditDashboardResponse)
def get_audit_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("audit.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=12, ge=1, le=100),
) -> AuditDashboardResponse:
    return build_audit_dashboard(conn, limit=limit)


@router.get("/records", response_model=AuditManagementResponse)
def get_audit_records(
    _user: Annotated[AuthenticatedUser, Depends(require_action("audit.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=500),
    action_type: str | None = None,
    entity_type: str | None = None,
    actor_name: str | None = None,
    search: str | None = None,
) -> AuditManagementResponse:
    return build_audit_management(
        conn,
        limit=limit,
        action_type=action_type,
        entity_type=entity_type,
        actor_name=actor_name,
        search=search,
    )
