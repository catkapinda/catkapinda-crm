"""Bordro endpoint'leri."""
from fastapi import APIRouter, HTTPException

from app.services.payroll import get_personnel_payroll, list_payroll

router = APIRouter()


@router.get("")
async def get_payroll(period: str = "2026-03") -> dict:
    """Aylık bordro — tüm aktif kuryelerin brüt+kesinti+net özeti."""
    return list_payroll(period=period)


@router.get("/{personnel_id}")
async def get_personnel_payroll_detail(
    personnel_id: int,
    period: str = "2026-03",
) -> dict:
    """Tek kurye bordro detayı (PDF / yazdır için)."""
    row = get_personnel_payroll(personnel_id=personnel_id, period=period)
    if not row:
        raise HTTPException(status_code=404, detail="Bordro bulunamadı")
    return row
