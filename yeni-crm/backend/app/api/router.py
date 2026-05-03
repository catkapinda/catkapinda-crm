"""API ana router — tüm route'ları birleştirir."""
from fastapi import APIRouter

from app.api.routes import (
    dashboard, deductions, equipment, health,
    payroll, personel, puantaj, restaurants, sidebar,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(personel.router, prefix="/personel", tags=["personel"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
api_router.include_router(sidebar.router, prefix="/sidebar", tags=["sidebar"])
api_router.include_router(puantaj.router, prefix="/puantaj", tags=["puantaj"])
api_router.include_router(deductions.router, prefix="/deductions", tags=["deductions"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
