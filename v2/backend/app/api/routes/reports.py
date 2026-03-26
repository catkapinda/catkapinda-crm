from typing import Annotated

from fastapi import APIRouter, Depends, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.reports import ReportsDashboardResponse, ReportsModuleStatus
from app.services.reports import build_reports_dashboard, build_reports_status

router = APIRouter()


@router.get("/status", response_model=ReportsModuleStatus)
def get_reports_status() -> ReportsModuleStatus:
    return build_reports_status()


@router.get("/dashboard", response_model=ReportsDashboardResponse)
def get_reports_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("reporting.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    month: str | None = Query(default=None),
    limit: int = Query(default=24, ge=1, le=200),
) -> ReportsDashboardResponse:
    return build_reports_dashboard(
        conn,
        selected_month=month,
        limit=limit,
    )
