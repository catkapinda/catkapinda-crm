from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.equipment import (
    BoxReturnCreateRequest,
    BoxReturnCreateResponse,
    BoxReturnDeleteResponse,
    BoxReturnDetailResponse,
    BoxReturnUpdateRequest,
    BoxReturnUpdateResponse,
    BoxReturnsManagementResponse,
    EquipmentDashboardResponse,
    EquipmentFormOptionsResponse,
    EquipmentIssueCreateRequest,
    EquipmentIssueCreateResponse,
    EquipmentIssueDeleteResponse,
    EquipmentIssueDetailResponse,
    EquipmentIssuesManagementResponse,
    EquipmentIssueUpdateRequest,
    EquipmentIssueUpdateResponse,
    EquipmentModuleStatus,
)
from app.services.equipment import (
    build_box_return_detail,
    build_box_return_management,
    build_equipment_dashboard,
    build_equipment_form_options,
    build_equipment_issue_detail,
    build_equipment_issue_management,
    build_equipment_status,
    create_box_return_entry,
    create_equipment_issue_entry,
    delete_box_return_entry,
    delete_equipment_issue_entry,
    update_box_return_entry,
    update_equipment_issue_entry,
)

router = APIRouter()


@router.get("/status", response_model=EquipmentModuleStatus)
def get_equipment_status() -> EquipmentModuleStatus:
    return build_equipment_status()


@router.get("/dashboard", response_model=EquipmentDashboardResponse)
def get_equipment_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    reference_date: date | None = None,
    limit: int = Query(default=10, ge=1, le=100),
) -> EquipmentDashboardResponse:
    return build_equipment_dashboard(
        conn,
        reference_date=reference_date or date.today(),
        limit=limit,
    )


@router.get("/form-options", response_model=EquipmentFormOptionsResponse)
def get_equipment_form_options(
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> EquipmentFormOptionsResponse:
    return build_equipment_form_options(conn)


@router.post("/issues", response_model=EquipmentIssueCreateResponse, status_code=201)
def create_equipment_issue_route(
    payload: EquipmentIssueCreateRequest,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> EquipmentIssueCreateResponse:
    try:
        return create_equipment_issue_entry(conn, payload=payload)
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/issues", response_model=EquipmentIssuesManagementResponse)
def get_equipment_issues(
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=120, ge=1, le=400),
    personnel_id: int | None = None,
    item_name: str | None = None,
    search: str | None = None,
) -> EquipmentIssuesManagementResponse:
    return build_equipment_issue_management(
        conn,
        limit=limit,
        personnel_id=personnel_id,
        item_name=item_name,
        search=search,
    )


@router.get("/issues/{issue_id}", response_model=EquipmentIssueDetailResponse)
def get_equipment_issue_detail_route(
    issue_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> EquipmentIssueDetailResponse:
    try:
        return build_equipment_issue_detail(conn, issue_id=issue_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/issues/{issue_id}", response_model=EquipmentIssueUpdateResponse)
def update_equipment_issue_route(
    issue_id: int,
    payload: EquipmentIssueUpdateRequest,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.bulk_update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> EquipmentIssueUpdateResponse:
    try:
        return update_equipment_issue_entry(conn, issue_id=issue_id, payload=payload)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/issues/{issue_id}", response_model=EquipmentIssueDeleteResponse)
def delete_equipment_issue_route(
    issue_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.bulk_delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> EquipmentIssueDeleteResponse:
    try:
        return delete_equipment_issue_entry(conn, issue_id=issue_id)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/box-returns", response_model=BoxReturnCreateResponse, status_code=201)
def create_box_return_route(
    payload: BoxReturnCreateRequest,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.box_return"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> BoxReturnCreateResponse:
    try:
        return create_box_return_entry(conn, payload=payload)
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/box-returns", response_model=BoxReturnsManagementResponse)
def get_box_returns(
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=120, ge=1, le=400),
    personnel_id: int | None = None,
    search: str | None = None,
) -> BoxReturnsManagementResponse:
    return build_box_return_management(
        conn,
        limit=limit,
        personnel_id=personnel_id,
        search=search,
    )


@router.get("/box-returns/{box_return_id}", response_model=BoxReturnDetailResponse)
def get_box_return_detail_route(
    box_return_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> BoxReturnDetailResponse:
    try:
        return build_box_return_detail(conn, box_return_id=box_return_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/box-returns/{box_return_id}", response_model=BoxReturnUpdateResponse)
def update_box_return_route(
    box_return_id: int,
    payload: BoxReturnUpdateRequest,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.box_return"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> BoxReturnUpdateResponse:
    try:
        return update_box_return_entry(conn, box_return_id=box_return_id, payload=payload)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/box-returns/{box_return_id}", response_model=BoxReturnDeleteResponse)
def delete_box_return_route(
    box_return_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("equipment.box_return"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> BoxReturnDeleteResponse:
    try:
        return delete_box_return_entry(conn, box_return_id=box_return_id)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
