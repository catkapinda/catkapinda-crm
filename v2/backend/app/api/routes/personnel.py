from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.audit import response_to_dict, safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.personnel import (
    PersonnelCreateRequest,
    PersonnelCreateResponse,
    PersonnelDeleteResponse,
    PersonnelDashboardResponse,
    PersonnelDetailResponse,
    PersonnelFormOptionsResponse,
    PersonnelManagementResponse,
    PersonnelModuleStatus,
    PersonnelStatusUpdateResponse,
    PersonnelUpdateRequest,
    PersonnelUpdateResponse,
)
from app.services.personnel import (
    build_personnel_dashboard,
    build_personnel_detail,
    build_personnel_form_options,
    build_personnel_management,
    build_personnel_status,
    create_personnel_record,
    delete_personnel_record_entry,
    toggle_personnel_record_status,
    update_personnel_record_entry,
)

router = APIRouter()


@router.get("/status", response_model=PersonnelModuleStatus)
def get_personnel_status() -> PersonnelModuleStatus:
    return build_personnel_status()


@router.get("/dashboard", response_model=PersonnelDashboardResponse)
def get_personnel_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("personnel.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=12, ge=1, le=100),
) -> PersonnelDashboardResponse:
    return build_personnel_dashboard(conn, limit=limit)


@router.get("/form-options", response_model=PersonnelFormOptionsResponse)
def get_personnel_form_options(
    _user: Annotated[AuthenticatedUser, Depends(require_action("personnel.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    restaurant_id: int | None = None,
) -> PersonnelFormOptionsResponse:
    return build_personnel_form_options(conn, restaurant_id=restaurant_id)


@router.post("/records", response_model=PersonnelCreateResponse, status_code=201)
def create_personnel_record_route(
    payload: PersonnelCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("personnel.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PersonnelCreateResponse:
    try:
        response = create_personnel_record(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="personel",
            action_type="oluştur",
            summary=str(response_data.get("message") or ""),
            entity_id=response_data.get("person_id"),
            details={**payload.model_dump(mode="json"), "person_id": response_data.get("person_id"), "person_code": response_data.get("person_code")},
        )
        return response
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/records", response_model=PersonnelManagementResponse)
def get_personnel_records(
    _user: Annotated[AuthenticatedUser, Depends(require_action("personnel.list"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=80, ge=1, le=300),
    restaurant_id: int | None = None,
    role: str | None = None,
    search: str | None = None,
) -> PersonnelManagementResponse:
    return build_personnel_management(
        conn,
        limit=limit,
        restaurant_id=restaurant_id,
        role=role,
        search=search,
    )


@router.get("/records/{person_id}", response_model=PersonnelDetailResponse)
def get_personnel_record_detail(
    person_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("personnel.list"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PersonnelDetailResponse:
    try:
        return build_personnel_detail(conn, person_id=person_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/records/{person_id}", response_model=PersonnelUpdateResponse)
def update_personnel_record_route(
    person_id: int,
    payload: PersonnelUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("personnel.update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PersonnelUpdateResponse:
    try:
        response = update_personnel_record_entry(conn, person_id=person_id, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="personel",
            action_type="güncelle",
            summary=str(response_data.get("message") or ""),
            entity_id=person_id,
            details={**payload.model_dump(mode="json"), "person_id": person_id, "person_code": response_data.get("person_code")},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/records/{person_id}/toggle-status", response_model=PersonnelStatusUpdateResponse)
def toggle_personnel_status_route(
    person_id: int,
    user: Annotated[AuthenticatedUser, Depends(require_action("personnel.status_change"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PersonnelStatusUpdateResponse:
    try:
        response = toggle_personnel_record_status(conn, person_id=person_id)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="personel",
            action_type="durum değiştir",
            summary=str(response_data.get("message") or ""),
            entity_id=person_id,
            details={"person_id": person_id, "status": response_data.get("status")},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/records/{person_id}", response_model=PersonnelDeleteResponse)
def delete_personnel_record_route(
    person_id: int,
    user: Annotated[AuthenticatedUser, Depends(require_action("personnel.delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PersonnelDeleteResponse:
    try:
        response = delete_personnel_record_entry(conn, person_id=person_id)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="personel",
            action_type="sil",
            summary=str(response_data.get("message") or ""),
            entity_id=person_id,
            details={"person_id": person_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
