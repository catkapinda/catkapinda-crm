"""Talep endpoint'leri (Avans / Motor Değişikliği / Muhasebe Değişimi)."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.requests import (
    REQUEST_TYPES,
    create_request,
    decide_request,
    delete_request,
    get_request,
    list_requests,
    request_counts,
)

router = APIRouter()


class RequestCreate(BaseModel):
    personnel_id: int
    request_type: str
    amount: float | None = 0
    reason: str | None = None


class RequestDecide(BaseModel):
    status: str  # "Onaylandı" | "Reddedildi"
    decided_by: str | None = None
    decision_notes: str | None = None


@router.get("/types")
async def get_types() -> list[str]:
    return sorted(REQUEST_TYPES)


@router.get("/counts")
async def counts() -> dict:
    return request_counts()


@router.get("")
async def list_all(
    status: str | None = None,
    request_type: str | None = None,
    personnel_id: int | None = None,
) -> list[dict]:
    return list_requests(
        status=status,
        request_type=request_type,
        personnel_id=personnel_id,
    )


@router.get("/{request_id}")
async def get_one(request_id: int) -> dict:
    row = get_request(request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    return row


@router.post("")
async def create_one(payload: RequestCreate) -> dict:
    fields: dict[str, Any] = payload.model_dump(exclude_unset=True)
    try:
        row = create_request(fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=500, detail="Talep oluşturulamadı")
    return row


@router.patch("/{request_id}/decide")
async def decide(request_id: int, payload: RequestDecide) -> dict:
    try:
        row = decide_request(
            request_id,
            status=payload.status,
            decided_by=payload.decided_by,
            decision_notes=payload.decision_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    return row


@router.delete("/{request_id}")
async def delete_one(request_id: int) -> dict:
    ok = delete_request(request_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    return {"ok": True}
