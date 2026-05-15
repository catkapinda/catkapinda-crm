"""Tahsilat (restaurant_invoices) endpoint'leri."""
from fastapi import APIRouter, HTTPException

from app.services import collections as svc

router = APIRouter()


@router.get("")
async def list_collections(
    period: str,
    status: str | None = None,
    search: str | None = None,
) -> dict:
    """Bir dönem için tahsilat listesi + KPI özet.

    Her aktif restoran için bir satır döner; tahsilat henüz girilmemişse
    sanal 'Bekliyor' kaydı gösterilir.
    """
    try:
        items = svc.list_collections(
            period=period, status=status, search=search,
        )
        summary = svc.summary(period=period)
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e

    return {
        "period": period,
        "items": items,
        "summary": summary,
        "status_options": svc.STATUS_OPTIONS,
    }


@router.post("")
async def upsert_collection(payload: dict) -> dict:
    """Tahsilat oluştur / güncelle (restaurant_id + collection_month bazında)."""
    try:
        return svc.upsert_collection(payload)
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: int) -> None:
    try:
        svc.delete_collection(collection_id)
    except LookupError as e:
        raise HTTPException(404, detail=str(e)) from e
