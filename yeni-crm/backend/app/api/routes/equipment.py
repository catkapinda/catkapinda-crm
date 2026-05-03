"""Ekipman & Zimmet endpoint'leri."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.equipment import (
    EQUIPMENT_CATALOG,
    create_assignment,
    list_assignments,
)

router = APIRouter()


class AssignmentCreate(BaseModel):
    personnel_id: int
    item_name: str
    quantity: int = 1
    unit_sale_price: float
    unit_cost: float | None = 0
    vat_rate: float | None = 10
    sale_type: str | None = "Satış"
    installment_count: int = 1
    issue_date: str | None = None
    notes: str | None = None


@router.get("/catalog")
async def get_catalog() -> list[dict]:
    """Zimmet edilebilir ekipman kataloğu."""
    return EQUIPMENT_CATALOG


@router.get("/assignments")
async def list_all(
    personnel_id: int | None = None,
    period: str | None = None,
) -> list[dict]:
    return list_assignments(personnel_id=personnel_id, period=period)


@router.post("/assignments")
async def create_one(payload: AssignmentCreate) -> dict:
    fields: dict[str, Any] = payload.model_dump(exclude_unset=True)
    try:
        row = create_assignment(fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=500, detail="Zimmet oluşturulamadı")
    return row
