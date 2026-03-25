from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.core.database import get_db
from app.schemas.attendance import (
    AttendanceCreateRequest,
    AttendanceCreateResponse,
    AttendanceDashboardResponse,
    AttendanceFormOptionsResponse,
    AttendanceModuleStatus,
)
from app.services.attendance import (
    build_attendance_dashboard,
    build_attendance_form_options,
    build_attendance_status,
    create_attendance_entry,
)

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


@router.get("/form-options", response_model=AttendanceFormOptionsResponse)
def get_attendance_form_options(
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    restaurant_id: int | None = None,
) -> AttendanceFormOptionsResponse:
    return build_attendance_form_options(conn, restaurant_id=restaurant_id)


@router.post("/entries", response_model=AttendanceCreateResponse, status_code=201)
def create_attendance_entry_route(
    payload: AttendanceCreateRequest,
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceCreateResponse:
    try:
        return create_attendance_entry(conn, payload=payload)
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
