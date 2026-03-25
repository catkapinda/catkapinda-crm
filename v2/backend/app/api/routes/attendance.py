from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
import psycopg

from app.core.database import get_db
from app.schemas.attendance import AttendanceDashboardResponse
from app.schemas.attendance import AttendanceModuleStatus
from app.services.attendance import build_attendance_dashboard, build_attendance_status

router = APIRouter()


@router.get("/status", response_model=AttendanceModuleStatus)
def get_attendance_status() -> AttendanceModuleStatus:
    return build_attendance_status()


@router.get("/dashboard", response_model=AttendanceDashboardResponse)
def get_attendance_dashboard(
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    reference_date: date | None = None,
    limit: int = Query(default=12, ge=1, le=100),
) -> AttendanceDashboardResponse:
    return build_attendance_dashboard(
        conn,
        reference_date=reference_date or date.today(),
        limit=limit,
    )
