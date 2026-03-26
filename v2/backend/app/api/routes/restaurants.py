from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.deps.auth import require_action
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.restaurants import (
    RestaurantCreateRequest,
    RestaurantCreateResponse,
    RestaurantDeleteResponse,
    RestaurantDetailResponse,
    RestaurantsDashboardResponse,
    RestaurantsFormOptionsResponse,
    RestaurantsManagementResponse,
    RestaurantsModuleStatus,
    RestaurantStatusUpdateResponse,
    RestaurantUpdateRequest,
    RestaurantUpdateResponse,
)
from app.services.restaurants import (
    build_restaurant_detail,
    build_restaurants_dashboard,
    build_restaurants_form_options,
    build_restaurants_management,
    build_restaurants_status,
    create_restaurant_record,
    delete_restaurant_record_entry,
    toggle_restaurant_record_status,
    update_restaurant_record_entry,
)

router = APIRouter()


@router.get("/status", response_model=RestaurantsModuleStatus)
def get_restaurants_status() -> RestaurantsModuleStatus:
    return build_restaurants_status()


@router.get("/dashboard", response_model=RestaurantsDashboardResponse)
def get_restaurants_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=12, ge=1, le=100),
) -> RestaurantsDashboardResponse:
    return build_restaurants_dashboard(conn, limit=limit)


@router.get("/form-options", response_model=RestaurantsFormOptionsResponse)
def get_restaurants_form_options(
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.view"))],
    pricing_model: str | None = None,
) -> RestaurantsFormOptionsResponse:
    return build_restaurants_form_options(pricing_model=pricing_model)


@router.post("/records", response_model=RestaurantCreateResponse, status_code=201)
def create_restaurant_record_route(
    payload: RestaurantCreateRequest,
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.create"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> RestaurantCreateResponse:
    try:
        return create_restaurant_record(conn, payload=payload)
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/records", response_model=RestaurantsManagementResponse)
def get_restaurant_records(
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=400),
    pricing_model: str | None = None,
    active: bool | None = None,
    search: str | None = None,
) -> RestaurantsManagementResponse:
    return build_restaurants_management(
        conn,
        limit=limit,
        pricing_model=pricing_model,
        active=active,
        search=search,
    )


@router.get("/records/{restaurant_id}", response_model=RestaurantDetailResponse)
def get_restaurant_record_detail(
    restaurant_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.view"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> RestaurantDetailResponse:
    try:
        return build_restaurant_detail(conn, restaurant_id=restaurant_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/records/{restaurant_id}", response_model=RestaurantUpdateResponse)
def update_restaurant_record_route(
    restaurant_id: int,
    payload: RestaurantUpdateRequest,
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.update"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> RestaurantUpdateResponse:
    try:
        return update_restaurant_record_entry(conn, restaurant_id=restaurant_id, payload=payload)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/records/{restaurant_id}/toggle-status", response_model=RestaurantStatusUpdateResponse)
def toggle_restaurant_status_route(
    restaurant_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.status_change"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> RestaurantStatusUpdateResponse:
    try:
        return toggle_restaurant_record_status(conn, restaurant_id=restaurant_id)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/records/{restaurant_id}", response_model=RestaurantDeleteResponse)
def delete_restaurant_record_route(
    restaurant_id: int,
    _user: Annotated[AuthenticatedUser, Depends(require_action("restaurant.delete"))],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> RestaurantDeleteResponse:
    try:
        return delete_restaurant_record_entry(conn, restaurant_id=restaurant_id)
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
