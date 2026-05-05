"""Profil değişiklik talepleri endpoint'leri (admin tarafı)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.profile_changes import (
    count_pending_changes,
    decide_change,
    delete_change,
    get_change,
    list_changes,
)

router = APIRouter()


class DecideProfileChange(BaseModel):
    """Profil değişikliği onayla/reddet."""

    status: str  # "Onaylandı" | "Reddedildi"
    decided_by: str | None = None
    decision_notes: str | None = None


@router.get("")
async def list_all(
    status: str | None = None,
    personnel_id: int | None = None,
) -> list[dict]:
    """Profil değişiklik taleplerini listele."""
    return list_changes(status=status, personnel_id=personnel_id)


@router.get("/counts")
async def counts() -> dict:
    """Sidebar badge için bekleyen talep sayısı."""
    return {"pending": count_pending_changes()}


@router.get("/{change_id}")
async def get_one(change_id: int) -> dict:
    """Profil değişiklik talebini getir."""
    row = get_change(change_id)
    if not row:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    return row


@router.patch("/{change_id}/decide")
async def decide(change_id: int, payload: DecideProfileChange) -> dict:
    """Profil değişiklik talebini onayla/reddet."""
    try:
        row = decide_change(
            change_id,
            status=payload.status,
            decided_by=payload.decided_by,
            decision_notes=payload.decision_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not row:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    return row


@router.delete("/{change_id}")
async def delete_one(change_id: int) -> dict:
    """Profil değişiklik talebini sil."""
    if not delete_change(change_id):
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    return {"ok": True}
