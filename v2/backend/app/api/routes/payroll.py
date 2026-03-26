from typing import Annotated

from fastapi import APIRouter, Depends, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.payroll import PayrollDashboardResponse, PayrollModuleStatus
from app.services.payroll import build_payroll_dashboard, build_payroll_status

router = APIRouter()


@router.get("/status", response_model=PayrollModuleStatus)
def get_payroll_status() -> PayrollModuleStatus:
    return build_payroll_status()


@router.get("/dashboard", response_model=PayrollDashboardResponse)
def get_payroll_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("payroll.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    month: str | None = Query(default=None),
    role: str | None = Query(default=None),
    restaurant: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
) -> PayrollDashboardResponse:
    return build_payroll_dashboard(
        conn,
        selected_month=month,
        role_filter=role,
        restaurant_filter=restaurant,
        limit=limit,
    )
