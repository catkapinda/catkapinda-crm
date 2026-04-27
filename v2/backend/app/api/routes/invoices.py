from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.audit import safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.invoices import (
    InvoiceCollectionUpsertRequest,
    InvoiceCollectionUpsertResponse,
    InvoicesDashboardResponse,
)
from app.services.invoices import build_invoices_dashboard, upsert_invoice_collection

router = APIRouter()


@router.get("/dashboard", response_model=InvoicesDashboardResponse)
def get_invoices_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("reporting.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    month: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> InvoicesDashboardResponse:
    return build_invoices_dashboard(
        conn,
        selected_month=month,
        limit=limit,
    )


@router.post("/collections", response_model=InvoiceCollectionUpsertResponse)
def upsert_invoice_collection_route(
    payload: InvoiceCollectionUpsertRequest,
    user: Annotated[AuthenticatedUser, Depends(require_action("reporting.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> InvoiceCollectionUpsertResponse:
    try:
        response = upsert_invoice_collection(conn, payload=payload)
        safe_record_audit_event(
            conn,
            user=user,
            entity_type="tahsilat",
            action_type="güncelle",
            summary=response.message,
            entity_id=payload.restaurant_id,
            details=payload.model_dump(mode="json"),
        )
        return response
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
