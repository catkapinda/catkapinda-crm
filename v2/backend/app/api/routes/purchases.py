from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.audit import response_to_dict, safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.purchases import (
    PurchaseCreateRequest,
    PurchaseCreateResponse,
    PurchaseDeleteResponse,
    PurchaseDetailResponse,
    PurchasesDashboardResponse,
    PurchasesFormOptionsResponse,
    PurchasesManagementResponse,
    PurchasesModuleStatus,
    PurchaseUpdateRequest,
    PurchaseUpdateResponse,
)
from app.services.purchases import (
    build_purchase_detail,
    build_purchases_dashboard,
    build_purchases_form_options,
    build_purchases_management,
    build_purchases_status,
    create_purchase_record,
    delete_purchase_record_entry,
    update_purchase_record_entry,
)

router = APIRouter()


@router.get("/status", response_model=PurchasesModuleStatus)
def get_purchases_status() -> PurchasesModuleStatus:
    return build_purchases_status()


@router.get("/dashboard", response_model=PurchasesDashboardResponse)
def get_purchases_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("purchase.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    reference_date: date | None = None,
    limit: int = Query(default=12, ge=1, le=100),
) -> PurchasesDashboardResponse:
    return build_purchases_dashboard(
        conn,
        reference_date=reference_date or date.today(),
        limit=limit,
    )


@router.get("/form-options", response_model=PurchasesFormOptionsResponse)
def get_purchases_form_options(
    _user: Annotated[AuthenticatedUser, Depends(require_action("purchase.view"))],
    item_name: str | None = None,
) -> PurchasesFormOptionsResponse:
    return build_purchases_form_options(item_name=item_name)


@router.post("/records", response_model=PurchaseCreateResponse, status_code=201)
def create_purchase_record_route(
    payload: PurchaseCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("purchase.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PurchaseCreateResponse:
    try:
        response = create_purchase_record(conn, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="satın alma",
            action_type="oluştur",
            summary=str(response_data.get("message") or ""),
            entity_id=response_data.get("purchase_id"),
            details={**payload.model_dump(mode="json"), "purchase_id": response_data.get("purchase_id")},
        )
        return response
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/records", response_model=PurchasesManagementResponse)
def get_purchase_records(
    _user: Annotated[AuthenticatedUser, Depends(require_action("purchase.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=400),
    item_name: str | None = None,
    search: str | None = None,
) -> PurchasesManagementResponse:
    return build_purchases_management(
        conn,
        limit=limit,
        item_name=item_name,
        search=search,
    )


@router.get("/records/{purchase_id}", response_model=PurchaseDetailResponse)
def get_purchase_record_detail(
    purchase_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("purchase.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PurchaseDetailResponse:
    try:
        return build_purchase_detail(conn, purchase_id=purchase_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/records/{purchase_id}", response_model=PurchaseUpdateResponse)
def update_purchase_record_route(
    purchase_id: int,
    payload: PurchaseUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("purchase.update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PurchaseUpdateResponse:
    try:
        response = update_purchase_record_entry(conn, purchase_id=purchase_id, payload=payload)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="satın alma",
            action_type="güncelle",
            summary=str(response_data.get("message") or ""),
            entity_id=purchase_id,
            details={**payload.model_dump(mode="json"), "purchase_id": purchase_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/records/{purchase_id}", response_model=PurchaseDeleteResponse)
def delete_purchase_record_route(
    purchase_id: int,
    user: Annotated[AuthenticatedUser, Depends(require_action("purchase.delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PurchaseDeleteResponse:
    try:
        response = delete_purchase_record_entry(conn, purchase_id=purchase_id)
        response_data = response_to_dict(response)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="satın alma",
            action_type="sil",
            summary=str(response_data.get("message") or ""),
            entity_id=purchase_id,
            details={"purchase_id": purchase_id},
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
