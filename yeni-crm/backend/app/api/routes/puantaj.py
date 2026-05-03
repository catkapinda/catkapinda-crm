"""Puantaj endpoint'leri."""
from fastapi import APIRouter

from app.services.puantaj import (
    available_periods,
    list_entries,
    summary_by_restaurant,
)

router = APIRouter()


@router.get("/periods")
async def periods() -> list[str]:
    """Veride mevcut tüm aylar (YYYY-MM) — yeni → eski."""
    return available_periods()


@router.get("/entries")
async def entries(
    period: str,
    restaurant_id: int | None = None,
    personnel_id: int | None = None,
    limit: int = 5000,
) -> list[dict]:
    """Belirli ay için puantaj girişleri."""
    return list_entries(
        period=period,
        restaurant_id=restaurant_id,
        personnel_id=personnel_id,
        limit=limit,
    )


@router.get("/summary-by-restaurant")
async def summary_restaurant(period: str) -> list[dict]:
    """Restoran bazında aylık özet."""
    return summary_by_restaurant(period=period)
