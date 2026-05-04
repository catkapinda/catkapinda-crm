"""Genel Bakış (Dashboard) endpoint'leri."""
from fastapi import APIRouter

from app.services.dashboard import get_dashboard_summary, get_dashboard_analytics

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(period: str = "current") -> dict:
    """Genel bakış özet metrikleri.

    period: 'current' (bu ay), 'previous' (geçen ay), '2026-03' (specific)
    """
    return get_dashboard_summary(period=period)


@router.get("/analytics")
async def dashboard_analytics(period: str = "2026-03") -> dict:
    """Kapsamlı dashboard analytics — tüm mock'ları gerçek veriye bağla.

    Dönen: invoiced_kdv_haric, invoiced_kdv_dahil, tevkifat_total,
           total_courier_net, total_management_salary, margin_pct,
           revenue_trend (son 6 ay), by_restaurant (top 8),
           deduction_breakdown, personnel_performance, ai_insights
    """
    return get_dashboard_analytics(period=period)
