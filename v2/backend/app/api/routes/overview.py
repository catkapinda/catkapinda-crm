from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
import psycopg

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.overview import OverviewDashboardResponse
from app.services.overview import build_overview_dashboard

router = APIRouter()


@router.get("/dashboard", response_model=OverviewDashboardResponse)
def get_overview_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("dashboard.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> OverviewDashboardResponse:
    return build_overview_dashboard(conn, reference_date=date.today())
