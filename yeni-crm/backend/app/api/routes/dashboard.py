"""Genel Bakış (Dashboard) endpoint'leri."""
from fastapi import APIRouter

from app.services.dashboard import (
    get_dashboard_summary,
    get_dashboard_analytics,
    get_available_periods,
)

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(period: str = "current") -> dict:
    """Genel bakış özet metrikleri.

    period: 'current' (bu ay), 'previous' (geçen ay), '2026-03' (specific)
    """
    return get_dashboard_summary(period=period)


@router.get("/analytics")
async def dashboard_analytics(period: str = "2026-03") -> dict:
    """Kapsamlı dashboard analytics — gerçek veriye bağlı."""
    return get_dashboard_analytics(period=period)


@router.get("/available-periods")
async def dashboard_available_periods() -> list[str]:
    """Sistemde puantaj/fatura verisi olan ayların listesi (en yeniden eskiye)."""
    return get_available_periods()
