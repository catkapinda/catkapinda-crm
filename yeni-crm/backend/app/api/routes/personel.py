"""Personel CRUD endpoint'leri."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.personel import (
    DeactivationError,
    create_personnel,
    deactivate_personnel,
    delete_personnel_cascade,
    get_personnel,
    list_personnel,
    list_personnel_stats,
    management_summary,
    next_person_code,
    page_insights,
    top_performers,
    update_personnel,
)

router = APIRouter()


class PersonnelUpdate(BaseModel):
    """Güncellenebilir alanlar — hepsi opsiyonel (PATCH)."""

    # Temel
    full_name: str | None = None
    person_code: str | None = None
    role: str | None = None
    status: str | None = None
    phone: str | None = None
    current_plate: str | None = None
    assigned_restaurant_id: int | None = None
    start_date: str | None = None
    exit_date: str | None = None
    # Hakediş & faturalandırma
    monthly_fixed_cost: float | None = None
    fixed_monthly_billing: float | None = None
    # Araç
    vehicle_type: str | None = None
    motor_purchase: str | None = None
    motor_purchase_sale_price: float | None = None
    motor_purchase_start_date: str | None = None
    motor_purchase_commitment_months: int | None = None
    motor_purchase_installment_count: int | None = None
    motor_purchase_monthly_amount: float | None = None
    motor_purchase_monthly_deduction: float | None = None
    motor_rental: str | None = None
    motor_rental_monthly_amount: float | None = None
    # Muhasebe
    accounting_type: str | None = None
    accountant_cost: float | None = None
    accounting_revenue: float | None = None
    accounting_effective_date: str | None = None
    # Şirket açılışı
    new_company_setup: str | None = None
    company_setup_cost: float | None = None
    company_setup_revenue: float | None = None
    company_setup_effective_date: str | None = None
    cost_model: str | None = None
    # Kimlik & banka
    tc_no: str | None = None
    iban: str | None = None
    tax_number: str | None = None
    tax_office: str | None = None
    # Adres & acil durum
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
    motor_purchase: str | None = None
    motor_rental: str | None = None
    accounting_type: str | None = None
    new_company_setup: str | None = None
    tc_no: str | None = None
    iban: str | None = None
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


@router.get("/top-performers")
async def get_top_performers(period: str = "2026-03", limit: int = 3) -> list[dict]:
    """Aya göre en çok paket atan personeller (podium için)."""
    return top_performers(period=period, limit=limit)


@router.get("/management")
async def get_management(period: str = "2026-03") -> list[dict]:
    """Yönetim & Yedek Operasyon — sabit maaşlı kişiler + cover özeti."""
    return management_summary(period=period)


@router.get("/insights")
async def get_insights(period: str = "2026-03") -> dict:
    """Akıllı içgörü hero kartları için aggregat veri."""
    return page_insights(period=period)


@router.get("/stats")
async def get_personnel_stats(period: str = "2026-03") -> list[dict]:
    """Personel listesi için aylık paket/saat/gün toplamları.

    /personel sayfasındaki kart bazlı 'Paket / Saat / Gün' alanları
    bu endpoint'in döndürdüğü {personnel_id, total_packages,
    total_hours, working_days} listesinden eşleşir.
    """
    return list_personnel_stats(period=period)


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


class DeactivatePayload(BaseModel):
    """Pasife alma — çıkış tarihi (YYYY-MM-DD) zorunlu."""

    exit_date: str


class HardDeletePayload(BaseModel):
    """Kalıcı sil — çift onay için kullanıcı kişinin tam adını yazar."""

    confirm_name: str


@router.post("/{personnel_id}/deactivate")
async def deactivate_one(
    personnel_id: int, payload: DeactivatePayload
) -> dict:
    """Personeli pasife al — bordro/imza/ödeme kontrolünden sonra.

    Hatalar:
      - 404: personel yok
      - 422: bordro yok / imzasız / ödenmemiş (DeactivationError)
    """
    try:
        return deactivate_personnel(personnel_id, payload.exit_date)
    except DeactivationError as e:
        if e.code == "bulunamadi":
            raise HTTPException(status_code=404, detail=e.detail) from e
        raise HTTPException(
            status_code=422,
            detail={
                "code": e.code,
                "message": e.detail,
                "context": e.context,
            },
        ) from e


@router.delete("/{personnel_id}")
async def delete_one(
    personnel_id: int, payload: HardDeletePayload
) -> dict:
    """Personeli ve tüm ilişkili kayıtlarını kalıcı olarak siler.

    - Body'de `confirm_name` kişinin `full_name`'iyle birebir eşleşmeli
      (fazladan boşluk silinerek karşılaştırılır).
    - Cascade: daily_entries, payroll_signatures, payroll_sms_log,
      advances, courier_requests, sonra personnel.
    """
    person = get_personnel(personnel_id)
    if not person:
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")

    expected = (person.get("full_name") or "").strip().lower()
    given = (payload.confirm_name or "").strip().lower()
    if not expected or expected != given:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ad_dogrulanmadi",
                "message": (
                    "Silmeyi onaylamak için kuryenin tam adını birebir yazmanız gerekiyor. "
                    f"Beklenen: {person.get('full_name')}"
                ),
            },
        )

    ok = delete_personnel_cascade(personnel_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Personel silinemedi.")
    return {"deleted": True, "id": personnel_id, "full_name": person.get("full_name")}


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
