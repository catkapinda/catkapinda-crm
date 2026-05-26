"""Restoran endpoint'leri."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.hakedis import restaurant_monthly_breakdown
from app.services.restaurants import (
    create_restaurant,
    get_pricing_history,
    get_restaurant,
    last_pricing_change,
    list_restaurants,
    update_restaurant,
)

router = APIRouter()


class RestaurantUpdate(BaseModel):
    """Güncellenebilir alanlar — hepsi opsiyonel (PATCH semantiği)."""

    brand: str | None = None
    branch: str | None = None
    billing_group: str | None = None
    pricing_model: str | None = None
    hourly_rate: float | None = None
    package_rate: float | None = None
    package_threshold: int | None = None
    package_rate_low: float | None = None
    package_rate_high: float | None = None
    fixed_monthly_fee: float | None = None
    vat_rate: float | None = None
    target_headcount: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    company_title: str | None = None
    tax_number: str | None = None
    tax_office: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    active: int | None = None
    notes: str | None = None


@router.get("")
async def list_all(active: bool | None = True) -> list[dict]:
    """Tüm restoranları listele."""
    return list_restaurants(active=active)


@router.get("/{restaurant_id}")
async def get_one(restaurant_id: int) -> dict:
    """Tek restoran detayı."""
    row = get_restaurant(restaurant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Restoran bulunamadı")
    return row


@router.patch("/{restaurant_id}")
async def update_one(restaurant_id: int, payload: RestaurantUpdate) -> dict:
    """Restoran alanlarını güncelle."""
    # Sadece kullanıcının gönderdiği alanları al (None'ları yoksay)
    fields: dict[str, Any] = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None
    }
    row = update_restaurant(restaurant_id, fields)
    if not row:
        raise HTTPException(status_code=404, detail="Restoran bulunamadı")
    return row


@router.get("/{restaurant_id}/monthly")
async def monthly_breakdown(restaurant_id: int, period: str = "2026-03") -> dict:
    """Restoranın o aydaki kurye bazında detayı + fatura tutarı."""
    result = restaurant_monthly_breakdown(restaurant_id, period)
    if result.get("restaurant") is None:
        raise HTTPException(status_code=404, detail="Restoran bulunamadı")
    return result


@router.get("/{restaurant_id}/pricing-history")
async def pricing_history(restaurant_id: int) -> dict:
    """Restoranın tarife değişim geçmişi (yeni → eski) + son değişim özeti."""
    history = get_pricing_history(restaurant_id)
    last = last_pricing_change(restaurant_id)
    return {
        "restaurant_id": restaurant_id,
        "history": history,
        "last_change": last,
    }


class RestaurantCreate(BaseModel):
    """Yeni restoran — brand zorunlu, diğerleri opsiyonel."""

    brand: str
    branch: str | None = None
    billing_group: str | None = None
    pricing_model: str | None = None
    hourly_rate: float | None = None
    package_rate: float | None = None
    package_threshold: int | None = None
    package_rate_low: float | None = None
    package_rate_high: float | None = None
    fixed_monthly_fee: float | None = None
    vat_rate: float | None = 20
    target_headcount: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    company_title: str | None = None
    tax_number: str | None = None
    tax_office: str | None = None
    start_date: str | None = None
    notes: str | None = None
    active: int | None = 1


@router.post("")
async def create_one(payload: RestaurantCreate) -> dict:
    """Yeni restoran (müşteri) oluştur."""
    fields: dict[str, Any] = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items()
        if v is not None
    }
    try:
        row = create_restaurant(fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=500, detail="Restoran oluşturulamadı")
    return row
