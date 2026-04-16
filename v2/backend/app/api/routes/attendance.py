from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.audit import response_to_dict, safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.attendance import (
    AttendanceBulkCreateRequest,
    AttendanceBulkCreateResponse,
    AttendanceBulkDeleteRequest,
    AttendanceBulkDeleteResponse,
    AttendanceCreateRequest,
    AttendanceCreateResponse,
    AttendanceDashboardResponse,
    AttendanceDeleteResponse,
    AttendanceEntryDetailResponse,
    AttendanceFilteredDeleteRequest,
    AttendanceFilteredDeleteResponse,
    AttendanceFormOptionsResponse,
    AttendanceManagementResponse,
    AttendanceModuleStatus,
    AttendanceUpdateRequest,
    AttendanceUpdateResponse,
)
from app.services.attendance import (
    bulk_delete_attendance_entries,
    create_attendance_entries_bulk,
    build_attendance_entry_detail,
    build_attendance_management,
    build_attendance_dashboard,
    build_attendance_form_options,
    build_attendance_status,
    create_attendance_entry,
    delete_attendance_entries_by_filter,
    delete_attendance_entry_record,
    update_attendance_entry_record,
)

router = APIRouter()


@router.get("/status", response_model=AttendanceModuleStatus)
def get_attendance_status() -> AttendanceModuleStatus:
    return build_attendance_status()


@router.get("/dashboard", response_model=AttendanceDashboardResponse)
def get_attendance_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("attendance.view"))],
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
    _user: Annotated[AuthenticatedUser, Depends(require_action("attendance.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    restaurant_id: int | None = None,
    include_all_active: bool = False,
) -> AttendanceFormOptionsResponse:
    return build_attendance_form_options(
        conn,
        restaurant_id=restaurant_id,
        include_all_active=include_all_active,
    )


@router.post("/entries", response_model=AttendanceCreateResponse, status_code=201)
def create_attendance_entry_route(
    payload: AttendanceCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("attendance.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceCreateResponse:
    try:
        response = create_attendance_entry(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="puantaj",
            action_type="oluştur",
            summary=str(response_data.get("message") or ""),
            entity_id=response_data.get("entry_id"),
            details={**payload.model_dump(mode="json"), "entry_id": response_data.get("entry_id")},
        )
        return response
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/entries/bulk", response_model=AttendanceBulkCreateResponse, status_code=201)
def create_attendance_entries_bulk_route(
    payload: AttendanceBulkCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("attendance.bulk_create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceBulkCreateResponse:
    try:
        response = create_attendance_entries_bulk(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="puantaj",
            action_type="toplu oluştur",
            summary=str(response_data.get("message") or ""),
            entity_id=",".join(str(entry_id) for entry_id in response_data.get("entry_ids") or []),
            details={**payload.model_dump(mode="json"), "created_count": response_data.get("created_count")},
        )
        return response
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/entries", response_model=AttendanceManagementResponse)
def get_attendance_entries(
    _user: Annotated[AuthenticatedUser, Depends(require_action("attendance.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=60, ge=1, le=300),
    restaurant_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AttendanceManagementResponse:
    return build_attendance_management(
        conn,
        limit=limit,
        restaurant_id=restaurant_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.delete("/entries", response_model=AttendanceBulkDeleteResponse)
def bulk_delete_attendance_entries_route(
    payload: AttendanceBulkDeleteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("attendance.bulk_delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceBulkDeleteResponse:
    try:
        response = bulk_delete_attendance_entries(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="puantaj",
            action_type="toplu sil",
            summary=str(response_data.get("message") or ""),
            entity_id=",".join(str(entry_id) for entry_id in response_data.get("entry_ids") or []),
            details={**payload.model_dump(mode="json"), "deleted_count": response_data.get("deleted_count")},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/entries/filter", response_model=AttendanceFilteredDeleteResponse)
def delete_attendance_entries_by_filter_route(
    payload: AttendanceFilteredDeleteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("attendance.bulk_delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceFilteredDeleteResponse:
    try:
        response = delete_attendance_entries_by_filter(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="puantaj",
            action_type="toplu sil",
            summary=str(response_data.get("message") or ""),
            details={**payload.model_dump(mode="json"), "deleted_count": response_data.get("deleted_count")},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/entries/{entry_id}", response_model=AttendanceEntryDetailResponse)
def get_attendance_entry_detail(
    entry_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("attendance.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceEntryDetailResponse:
    try:
        return build_attendance_entry_detail(conn, entry_id=entry_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/entries/{entry_id}", response_model=AttendanceUpdateResponse)
def update_attendance_entry_route(
    entry_id: int,
    payload: AttendanceUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("attendance.update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceUpdateResponse:
    try:
        response = update_attendance_entry_record(conn, entry_id=entry_id, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="puantaj",
            action_type="güncelle",
            summary=str(response_data.get("message") or ""),
            entity_id=entry_id,
            details={**payload.model_dump(mode="json"), "entry_id": entry_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/entries/{entry_id}", response_model=AttendanceDeleteResponse)
def delete_attendance_entry_route(
    entry_id: int,
    user: Annotated[AuthenticatedUser, Depends(require_action("attendance.delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AttendanceDeleteResponse:
    try:
        response = delete_attendance_entry_record(conn, entry_id=entry_id)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="puantaj",
            action_type="sil",
            summary=str(response_data.get("message") or ""),
            entity_id=entry_id,
            details={"entry_id": entry_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
