"""Puantaj endpoint'leri."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.puantaj import (
    available_periods,
    bulk_fill,
    daily_matrix,
    list_entries,
    summary_by_restaurant,
    upsert_cell,
)

router = APIRouter()


class CellPayload(BaseModel):
    personnel_id: int
    entry_date: str  # YYYY-MM-DD
    cell_type: str  # normal | izin | gelmedi | raporlu | ihbarsiz | empty
    worked_hours: float = 0
    package_count: int = 0
    coverage_type: str | None = None
    restaurant_id: int | None = None
    notes: str | None = None


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


@router.get("/matrix")
async def matrix(period: str = "2026-03") -> dict:
    """Personel × gün matrisi — grid sayfası için."""
    return daily_matrix(period=period)


class BulkFillPayload(BaseModel):
    period: str
    pattern: str  # weekdays | all | weekend_off | copy_previous
    hours: float = 9
    package_count: int = 0
    personnel_ids: list[int] | None = None
    restaurant_id: int | None = None


@router.post("/bulk-fill")
async def post_bulk_fill(payload: BulkFillPayload) -> dict:
    """Hızlı doldur (toplu giriş) — boş hücreleri varsayılan değerlerle doldurur."""
    return bulk_fill(
        period=payload.period,
        pattern=payload.pattern,
        hours=payload.hours,
        package_count=payload.package_count,
        personnel_ids=payload.personnel_ids,
        restaurant_id=payload.restaurant_id,
    )


@router.patch("/cell")
async def patch_cell(payload: CellPayload) -> dict:
    """Bir günü güncelle / oluştur (UPSERT)."""
    try:
        return upsert_cell(
            personnel_id=payload.personnel_id,
            entry_date=payload.entry_date,
            cell_type=payload.cell_type,
            worked_hours=payload.worked_hours,
            package_count=payload.package_count,
            coverage_type=payload.coverage_type,
            notes=payload.notes,
            restaurant_id=payload.restaurant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
