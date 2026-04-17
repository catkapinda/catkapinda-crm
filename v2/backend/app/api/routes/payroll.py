from typing import Annotated
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg
from starlette.responses import StreamingResponse

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.payroll import PayrollDashboardResponse, PayrollModuleStatus
from app.services.payroll import build_payroll_dashboard, build_payroll_document_file, build_payroll_status

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


@router.get("/document")
def download_payroll_document(
    _user: Annotated[AuthenticatedUser, Depends(require_action("payroll.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    personnel_id: int = Query(..., ge=1),
    month: str | None = Query(default=None),
) -> StreamingResponse:
    try:
        file_name, file_bytes = build_payroll_document_file(
            conn,
            selected_month=month,
            personnel_id=personnel_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response = StreamingResponse(BytesIO(file_bytes), media_type="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response
