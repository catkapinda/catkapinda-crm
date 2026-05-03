"""API ana router — tüm route'ları birleştirir."""
from fastapi import APIRouter

from app.api.routes import dashboard, health, personel

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(personel.router, prefix="/personel", tags=["personel"])
