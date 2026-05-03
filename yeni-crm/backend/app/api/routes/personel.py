"""Personel CRUD endpoint'leri."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.personel import (
    create_personnel,
    get_personnel,
    list_personnel,
    next_person_code,
    update_personnel,
)

router = APIRouter()


class PersonnelUpdate(BaseModel):
    """Güncellenebilir alanlar — hepsi opsiyonel (PATCH)."""

    full_name: str | None = None
    person_code: str | None = None
    role: str | None = None
    status: str | None = None
    phone: str | None = None
    current_plate: str | None = None
    assigned_restaurant_id: int | None = None
    start_date: str | None = None
    exit_date: str | None = None
    monthly_fixed_cost: float | None = None
    fixed_monthly_billing: float | None = None
    vehicle_type: str | None = None
    tc_no: str | None = None
    iban: str | None = None
    tax_number: str | None = None
    tax_office: str | None = None
    accounting_type: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    notes: str | None = None


class PersonnelCreate(BaseModel):
    """Yeni personel — full_name ve role zorunlu, diğerleri opsiyonel."""

    full_name: str
    role: str
    person_code: str | None = None
    status: str | None = "Aktif"
    phone: str | None = None
    current_plate: str | None = None
    assigned_restaurant_id: int | None = None
    start_date: str | None = None
    monthly_fixed_cost: float | None = None
    fixed_monthly_billing: float | None = None
    vehicle_type: str | None = None
    tc_no: str | None = None
    iban: str | None = None
    accounting_type: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    notes: str | None = None


@router.get("")
async def list_all(status: str | None = None) -> list[dict]:
    """Tüm personeli listele."""
    return list_personnel(status=status)


@router.get("/next-code")
async def get_next_code(role: str) -> dict:
    """Role göre bir sonraki uygun person_code'u öner."""
    return {"person_code": next_person_code(role)}


@router.get("/{personnel_id}")
async def get_one(personnel_id: int) -> dict:
    """Tek personel detayı."""
    row = get_personnel(personnel_id)
    if not row:
        raise HTTPException(status_code=404, detail="Personel bulunamadı")
    return row


@router.patch("/{personnel_id}")
async def update_one(personnel_id: int, payload: PersonnelUpdate) -> dict:
    """Personel alanlarını güncelle."""
    fields: dict[str, Any] = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items()
        if v is not None
    }
    row = update_personnel(personnel_id, fields)
    if not row:
        raise HTTPException(status_code=404, detail="Personel bulunamadı")
    return row


@router.post("")
async def create_one(payload: PersonnelCreate) -> dict:
    """Yeni personel oluştur."""
    fields: dict[str, Any] = {
        k: v for k, v in payload.model_dump(exclude_unset=True).items()
        if v is not None
    }
    # Person code verilmediyse otomatik oluştur
    if not fields.get("person_code"):
        fields["person_code"] = next_person_code(fields["role"])

    try:
        row = create_personnel(fields)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=500, detail="Personel oluşturulamadı")
    return row
