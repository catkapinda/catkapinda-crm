"""Bordro endpoint'leri."""
from fastapi import APIRouter

from app.services.payroll import list_payroll

router = APIRouter()


@router.get("")
async def get_payroll(period: str = "2026-03") -> dict:
    """Aylık bordro — tüm aktif kuryelerin brüt+kesinti+net özeti."""
    return list_payroll(period=period)
