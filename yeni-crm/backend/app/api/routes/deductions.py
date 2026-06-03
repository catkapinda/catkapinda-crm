"""Kesinti endpoint'leri."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.deductions import (
    DEDUCTION_TYPES,
    create_deduction,
    deductions_summary_by_personnel,
    deductions_summary_by_type,
    delete_deduction,
    list_deductions,
    update_deduction,
)

router = APIRouter()


class DeductionCreate(BaseModel):
    personnel_id: int
    deduction_type: str
    amount: float
    deduction_date: str | None = None
    notes: str | None = None


class DeductionUpdate(BaseModel):
    """Kesinti düzenleme — alanlar opsiyonel (PATCH)."""

    personnel_id: int | None = None
    deduction_type: str | None = None
    amount: float | None = None
    deduction_date: str | None = None
    notes: str | None = None


@router.get("/types")
async def get_types() -> list[str]:
    return DEDUCTION_TYPES


@router.get("")
async def list_all(
    period: str | None = None,
    personnel_id: int | None = None,
    deduction_type: str | None = None,
) -> list[dict]:
    return list_deductions(
        period=period,
        personnel_id=personnel_id,
        deduction_type=deduction_type,
    )


@router.post("")
async def create_one(payload: DeductionCreate) -> dict:
    fields: dict[str, Any] = payload.model_dump(exclude_unset=True)
    try:
        row = create_deduction(fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=500, detail="Kesinti oluşturulamadı")
    return row


@router.patch("/{deduction_id}")
async def update_one(deduction_id: int, payload: DeductionUpdate) -> dict:
    fields: dict[str, Any] = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items()
        if v is not None
    }
    try:
        row = update_deduction(deduction_id, fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=404, detail="Kesinti bulunamadı")
    return row


@router.delete("/{deduction_id}")
async def delete_one(deduction_id: int) -> dict:
    ok = delete_deduction(deduction_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Kesinti bulunamadı")
    return {"deleted": True, "id": deduction_id}


@router.get("/summary/by-personnel")
async def summary_personnel(period: str = "2026-03") -> list[dict]:
    return deductions_summary_by_personnel(period=period)


@router.get("/summary/by-type")
async def summary_type(period: str = "2026-03") -> list[dict]:
    return deductions_summary_by_type(period=period)
