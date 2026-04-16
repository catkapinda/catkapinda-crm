from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.audit import response_to_dict, safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.deductions import (
    DeductionBulkDeleteRequest,
    DeductionBulkDeleteResponse,
    DeductionCreateRequest,
    DeductionCreateResponse,
    DeductionDeleteResponse,
    DeductionDetailResponse,
    DeductionsDashboardResponse,
    DeductionsFormOptionsResponse,
    DeductionsManagementResponse,
    DeductionsModuleStatus,
    DeductionUpdateRequest,
    DeductionUpdateResponse,
)
from app.services.deductions import (
    bulk_delete_deduction_entries,
    build_deduction_detail,
    build_deductions_dashboard,
    build_deductions_form_options,
    build_deductions_management,
    build_deductions_status,
    create_deduction_entry,
    delete_deduction_entry,
    update_deduction_entry,
)

router = APIRouter()


@router.get("/status", response_model=DeductionsModuleStatus)
def get_deductions_status() -> DeductionsModuleStatus:
    return build_deductions_status()


@router.get("/dashboard", response_model=DeductionsDashboardResponse)
def get_deductions_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("deduction.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    reference_date: date | None = None,
    limit: int = Query(default=12, ge=1, le=100),
) -> DeductionsDashboardResponse:
    return build_deductions_dashboard(
        conn,
        reference_date=reference_date or date.today(),
        limit=limit,
    )


@router.get("/form-options", response_model=DeductionsFormOptionsResponse)
def get_deductions_form_options(
    _user: Annotated[AuthenticatedUser, Depends(require_action("deduction.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    personnel_id: int | None = None,
) -> DeductionsFormOptionsResponse:
    return build_deductions_form_options(conn, personnel_id=personnel_id)


@router.post("/records", response_model=DeductionCreateResponse, status_code=201)
def create_deduction_record_route(
    payload: DeductionCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("deduction.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> DeductionCreateResponse:
    try:
        response = create_deduction_entry(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="kesinti",
            action_type="oluştur",
            summary=str(response_data.get("message") or ""),
            entity_id=response_data.get("deduction_id"),
            details={**payload.model_dump(mode="json"), "deduction_id": response_data.get("deduction_id")},
        )
        return response
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/records", response_model=DeductionsManagementResponse)
def get_deduction_records(
    _user: Annotated[AuthenticatedUser, Depends(require_action("deduction.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=400),
    personnel_id: int | None = None,
    deduction_type: str | None = None,
    search: str | None = None,
) -> DeductionsManagementResponse:
    return build_deductions_management(
        conn,
        limit=limit,
        personnel_id=personnel_id,
        deduction_type=deduction_type,
        search=search,
    )


@router.delete("/records", response_model=DeductionBulkDeleteResponse)
def bulk_delete_deduction_records_route(
    payload: DeductionBulkDeleteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("deduction.bulk_delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> DeductionBulkDeleteResponse:
    try:
        response = bulk_delete_deduction_entries(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="kesinti",
            action_type="toplu sil",
            summary=str(response_data.get("message") or ""),
            entity_id=",".join(str(deduction_id) for deduction_id in response_data.get("deduction_ids") or []),
            details={**payload.model_dump(mode="json"), "deleted_count": response_data.get("deleted_count")},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/records/{deduction_id}", response_model=DeductionDetailResponse)
def get_deduction_record_detail(
    deduction_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("deduction.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> DeductionDetailResponse:
    try:
        return build_deduction_detail(conn, deduction_id=deduction_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/records/{deduction_id}", response_model=DeductionUpdateResponse)
def update_deduction_record_route(
    deduction_id: int,
    payload: DeductionUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("deduction.update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> DeductionUpdateResponse:
    try:
        response = update_deduction_entry(conn, deduction_id=deduction_id, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="kesinti",
            action_type="güncelle",
            summary=str(response_data.get("message") or ""),
            entity_id=deduction_id,
            details={**payload.model_dump(mode="json"), "deduction_id": deduction_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/records/{deduction_id}", response_model=DeductionDeleteResponse)
def delete_deduction_record_route(
    deduction_id: int,
    user: Annotated[AuthenticatedUser, Depends(require_action("deduction.delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> DeductionDeleteResponse:
    try:
        response = delete_deduction_entry(conn, deduction_id=deduction_id)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="kesinti",
            action_type="sil",
            summary=str(response_data.get("message") or ""),
            entity_id=deduction_id,
            details={"deduction_id": deduction_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
