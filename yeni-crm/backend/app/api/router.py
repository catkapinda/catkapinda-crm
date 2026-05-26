"""API ana router — tüm route'ları birleştirir."""
from fastapi import APIRouter

from app.api.routes import (
    box_returns, collections, courier, dashboard, data_health, deductions,
    equipment, health, invoices, payroll, personel, profile_changes, puantaj,
    requests as requests_route, restaurant_reports, restaurants, sidebar,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(personel.router, prefix="/personel", tags=["personel"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
api_router.include_router(sidebar.router, prefix="/sidebar", tags=["sidebar"])
api_router.include_router(courier.router, prefix="/courier", tags=["courier"])
api_router.include_router(puantaj.router, prefix="/puantaj", tags=["puantaj"])
api_router.include_router(deductions.router, prefix="/deductions", tags=["deductions"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
api_router.include_router(requests_route.router, prefix="/requests", tags=["requests"])
api_router.include_router(profile_changes.router, prefix="/profile-changes", tags=["profile-changes"])
api_router.include_router(restaurant_reports.router, prefix="/restaurant-reports", tags=["reports"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(box_returns.router, prefix="/box-returns", tags=["box-returns"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(data_health.router, prefix="/data-health", tags=["data-health"])
