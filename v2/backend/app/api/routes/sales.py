from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.audit import response_to_dict, safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.sales import (
    SalesCreateRequest,
    SalesCreateResponse,
    SalesDashboardResponse,
    SalesDeleteResponse,
    SalesDetailResponse,
    SalesFormOptionsResponse,
    SalesManagementResponse,
    SalesModuleStatus,
    SalesUpdateRequest,
    SalesUpdateResponse,
)
from app.services.sales import (
    build_sales_dashboard,
    build_sales_detail,
    build_sales_form_options,
    build_sales_management,
    build_sales_status,
    create_sales_record,
    delete_sales_record_entry,
    update_sales_record_entry,
)

router = APIRouter()


@router.get("/status", response_model=SalesModuleStatus)
def get_sales_status() -> SalesModuleStatus:
    return build_sales_status()


@router.get("/dashboard", response_model=SalesDashboardResponse)
def get_sales_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("sales.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=12, ge=1, le=100),
) -> SalesDashboardResponse:
    return build_sales_dashboard(conn, limit=limit)


@router.get("/form-options", response_model=SalesFormOptionsResponse)
def get_sales_form_options(
    _user: Annotated[AuthenticatedUser, Depends(require_action("sales.view"))],
    pricing_model: str | None = None,
) -> SalesFormOptionsResponse:
    return build_sales_form_options(pricing_model=pricing_model)


@router.post("/records", response_model=SalesCreateResponse, status_code=201)
def create_sales_record_route(
    payload: SalesCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("sales.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> SalesCreateResponse:
    try:
        response = create_sales_record(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="satış",
            action_type="oluştur",
            summary=str(response_data.get("message") or ""),
            entity_id=response_data.get("entry_id"),
            details={**payload.model_dump(mode="json"), "entry_id": response_data.get("entry_id")},
        )
        return response
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/records", response_model=SalesManagementResponse)
def get_sales_records(
    _user: Annotated[AuthenticatedUser, Depends(require_action("sales.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=120, ge=1, le=400),
    status: str | None = None,
    search: str | None = None,
) -> SalesManagementResponse:
    return build_sales_management(conn, limit=limit, status=status, search=search)


@router.get("/records/{sales_id}", response_model=SalesDetailResponse)
def get_sales_record_detail(
    sales_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("sales.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> SalesDetailResponse:
    try:
        return build_sales_detail(conn, sales_id=sales_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/records/{sales_id}", response_model=SalesUpdateResponse)
def update_sales_record_route(
    sales_id: int,
    payload: SalesUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("sales.update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> SalesUpdateResponse:
    try:
        response = update_sales_record_entry(conn, sales_id=sales_id, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="satış",
            action_type="güncelle",
            summary=str(response_data.get("message") or ""),
            entity_id=sales_id,
            details={**payload.model_dump(mode="json"), "entry_id": sales_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/records/{sales_id}", response_model=SalesDeleteResponse)
def delete_sales_record_route(
    sales_id: int,
    user: Annotated[AuthenticatedUser, Depends(require_action("sales.delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> SalesDeleteResponse:
    try:
        response = delete_sales_record_entry(conn, sales_id=sales_id)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="satış",
            action_type="sil",
            summary=str(response_data.get("message") or ""),
            entity_id=sales_id,
            details={"entry_id": sales_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
