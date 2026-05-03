"""Genel Bakış (Dashboard) endpoint'leri."""
from fastapi import APIRouter

from app.services.dashboard import get_dashboard_summary

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(period: str = "current") -> dict:
    """Genel bakış özet metrikleri.

    period: 'current' (bu ay), 'previous' (geçen ay), '2026-03' (specific)
    """
    return get_dashboard_summary(period=period)
