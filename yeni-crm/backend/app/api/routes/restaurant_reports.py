"""Restoran Raporları endpoint'leri."""
from fastapi import APIRouter

from app.services.restaurant_reports import get_restaurant_reports

router = APIRouter()


@router.get("")
async def get_reports(period: str = "2026-03") -> dict:
    """Tüm restoran raporlarını getir (turnover, efficiency, cost, growth).

    Query params:
    - period: "YYYY-MM" (default: "2026-03")

    Returns:
    {
        "period": "2026-03",
        "previous_period": "2026-02",
        "turnover": [...],
        "courier_efficiency": [...],
        "cost_per_package": {...},
        "package_growth": [...]
    }
    """
    return get_restaurant_reports(period)
