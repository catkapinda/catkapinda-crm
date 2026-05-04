"""Fatura endpoint'leri — restoranlara aylık kesilen faturalar."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.invoices import (
    get_invoice_summary,
    list_invoices,
    mark_paid,
    upsert_invoice,
)

router = APIRouter()


class InvoiceUpsert(BaseModel):
    invoice_no: str | None = None
    amount_excl_vat: float | None = None
    vat_amount: float | None = None
    amount_incl_vat: float | None = None
    status: str | None = None
    paid_amount: float | None = None
    notes: str | None = None


class MarkPaidPayload(BaseModel):
    amount: float | None = None  # None ise toplam fatura tutarı


@router.get("")
async def list_all(period: str = "2026-03") -> list[dict]:
    """Belirli bir aya ait tüm restoran faturaları."""
    return list_invoices(period=period)


@router.get("/summary")
async def summary(period: str = "2026-03") -> dict:
    """Aya ait özet metrikler — toplam, ödenen, bekleyen, koleksiyon %."""
    return get_invoice_summary(period=period)


@router.put("/{restaurant_id}")
async def upsert_one(
    restaurant_id: int,
    period: str,
    payload: InvoiceUpsert,
) -> dict:
    """Bir fatura kaydı oluştur veya güncelle (restaurant + period unique)."""
    fields = payload.model_dump(exclude_unset=True)
    row = upsert_invoice(restaurant_id, period, fields)
    if not row:
        raise HTTPException(status_code=500, detail="Fatura kaydı oluşturulamadı")
    return row


@router.post("/{restaurant_id}/mark-paid")
async def mark_paid_route(
    restaurant_id: int,
    period: str,
    payload: MarkPaidPayload,
) -> dict:
    """Faturayı ödendi (veya kısmi) işaretle."""
    row = mark_paid(restaurant_id, period, amount=payload.amount)
    if not row:
        raise HTTPException(status_code=404, detail="Fatura bulunamadı")
    return row
