from __future__ import annotations

import psycopg

from app.repositories.restaurants import (
    count_restaurant_linked_daily_entries,
    count_restaurant_linked_deductions,
    count_restaurant_linked_personnel,
    count_restaurant_management_records,
    delete_restaurant_record,
    fetch_recent_restaurant_records,
    fetch_restaurant_management_records,
    fetch_restaurant_record_by_id,
    fetch_restaurant_summary,
    insert_restaurant_record,
    update_restaurant_record,
    update_restaurant_status,
)
from app.schemas.restaurants import (
    RestaurantCreateRequest,
    RestaurantCreateResponse,
    RestaurantDeleteResponse,
    RestaurantDetailResponse,
    RestaurantsDashboardResponse,
    RestaurantsFormOptionsResponse,
    RestaurantsManagementResponse,
    RestaurantsModuleStatus,
    RestaurantManagementEntry,
    RestaurantPricingModelOption,
    RestaurantStatusUpdateResponse,
    RestaurantSummary,
    RestaurantUpdateRequest,
    RestaurantUpdateResponse,
)

PRICING_MODEL_LABELS = {
    "hourly_plus_package": "Hacimsiz Primli",
    "threshold_package": "Hacimli Primli",
    "hourly_only": "Sadece Saatlik",
    "fixed_monthly": "Sabit Aylık Ücret",
}
STATUS_OPTIONS = ["Aktif", "Pasif"]


def _display_pricing_model(value: str) -> str:
    return PRICING_MODEL_LABELS.get(value, value or "-")


def _normalize_pricing_model(value: str) -> str:
    normalized = str(value or "").strip()
    return normalized if normalized in PRICING_MODEL_LABELS else "hourly_plus_package"


def _status_to_active(status: str) -> bool:
    return str(status or "").strip() != "Pasif"


def _active_to_status(active: bool) -> str:
    return "Aktif" if bool(active) else "Pasif"


def _build_management_entry(row: dict[str, object]) -> RestaurantManagementEntry:
    return RestaurantManagementEntry(
        id=int(row["id"]),
        brand=str(row["brand"] or ""),
        branch=str(row["branch"] or ""),
        pricing_model=str(row["pricing_model"] or ""),
        pricing_model_label=_display_pricing_model(str(row["pricing_model"] or "")),
        hourly_rate=float(row["hourly_rate"] or 0),
        package_rate=float(row["package_rate"] or 0),
        package_threshold=int(row["package_threshold"] or 390),
        package_rate_low=float(row["package_rate_low"] or 0),
        package_rate_high=float(row["package_rate_high"] or 0),
        fixed_monthly_fee=float(row["fixed_monthly_fee"] or 0),
        vat_rate=float(row["vat_rate"] or 20),
        target_headcount=int(row["target_headcount"] or 0),
        start_date=row["start_date"],
        end_date=row["end_date"],
        extra_headcount_request=int(row["extra_headcount_request"] or 0),
        extra_headcount_request_date=row["extra_headcount_request_date"],
        reduce_headcount_request=int(row["reduce_headcount_request"] or 0),
        reduce_headcount_request_date=row["reduce_headcount_request_date"],
        contact_name=str(row["contact_name"] or ""),
        contact_phone=str(row["contact_phone"] or ""),
        contact_email=str(row["contact_email"] or ""),
        company_title=str(row["company_title"] or ""),
        address=str(row["address"] or ""),
        tax_office=str(row["tax_office"] or ""),
        tax_number=str(row["tax_number"] or ""),
        active=bool(row["active"]),
        notes=str(row["notes"] or ""),
    )


def _validate_restaurant_payload(payload: RestaurantCreateRequest | RestaurantUpdateRequest) -> list[str]:
    errors: list[str] = []
    if not str(payload.brand or "").strip():
        errors.append("Marka alanı zorunlu.")
    if not str(payload.branch or "").strip():
        errors.append("Şube alanı zorunlu.")
    if not str(payload.contact_name or "").strip():
        errors.append("Yetkili ad soyad alanı zorunlu.")
    if not str(payload.contact_phone or "").strip():
        errors.append("Yetkili telefon alanı zorunlu.")
    if not str(payload.contact_email or "").strip():
        errors.append("Yetkili e-posta alanı zorunlu.")
    if not str(payload.tax_office or "").strip():
        errors.append("Vergi dairesi alanı zorunlu.")
    if not str(payload.tax_number or "").strip():
        errors.append("Vergi numarası alanı zorunlu.")
    if int(payload.target_headcount or 0) <= 0:
        errors.append("Hedef kadro 0'dan büyük olmalı.")
    if payload.start_date is None:
        errors.append("Başlangıç tarihi zorunlu.")
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        errors.append("Bitiş tarihi başlangıç tarihinden önce olamaz.")
    if int(payload.extra_headcount_request or 0) > 0 and payload.extra_headcount_request_date is None:
        errors.append("Ek kurye talebi girildiğinde ek talep tarihi de seçilmeli.")
    if int(payload.reduce_headcount_request or 0) > 0 and payload.reduce_headcount_request_date is None:
        errors.append("Kurye azaltma talebi girildiğinde azaltma talep tarihi de seçilmeli.")

    pricing_model = _normalize_pricing_model(payload.pricing_model)
    if pricing_model == "hourly_plus_package":
        if float(payload.hourly_rate or 0) <= 0:
            errors.append("Hacimsiz Primli modelde saatlik ücret zorunlu.")
        if float(payload.package_rate or 0) <= 0:
            errors.append("Hacimsiz Primli modelde paket primi zorunlu.")
    elif pricing_model == "threshold_package":
        if float(payload.hourly_rate or 0) <= 0:
            errors.append("Hacimli Primli modelde saatlik ücret zorunlu.")
        if int(payload.package_threshold or 0) <= 0:
            errors.append("Hacimli Primli modelde paket eşiği zorunlu.")
        if float(payload.package_rate_low or 0) <= 0 or float(payload.package_rate_high or 0) <= 0:
            errors.append("Hacimli Primli modelde eşik altı ve üstü primler zorunlu.")
    elif pricing_model == "hourly_only":
        if float(payload.hourly_rate or 0) <= 0:
            errors.append("Sadece Saatlik modelde saatlik ücret zorunlu.")
    elif pricing_model == "fixed_monthly":
        if float(payload.fixed_monthly_fee or 0) <= 0:
            errors.append("Sabit Aylık Ücret modelinde aylık ücret zorunlu.")

    return errors


def _payload_to_values(payload: RestaurantCreateRequest | RestaurantUpdateRequest) -> dict[str, object]:
    pricing_model = _normalize_pricing_model(payload.pricing_model)
    return {
        "brand": str(payload.brand or "").strip(),
        "branch": str(payload.branch or "").strip(),
        "pricing_model": pricing_model,
        "hourly_rate": float(payload.hourly_rate or 0),
        "package_rate": float(payload.package_rate or 0),
        "package_threshold": int(payload.package_threshold or 390),
        "package_rate_low": float(payload.package_rate_low or 0),
        "package_rate_high": float(payload.package_rate_high or 0),
        "fixed_monthly_fee": float(payload.fixed_monthly_fee or 0),
        "vat_rate": float(payload.vat_rate or 20),
        "target_headcount": int(payload.target_headcount or 0),
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "extra_headcount_request": int(payload.extra_headcount_request or 0),
        "extra_headcount_request_date": payload.extra_headcount_request_date,
        "reduce_headcount_request": int(payload.reduce_headcount_request or 0),
        "reduce_headcount_request_date": payload.reduce_headcount_request_date,
        "contact_name": str(payload.contact_name or "").strip(),
        "contact_phone": str(payload.contact_phone or "").strip(),
        "contact_email": str(payload.contact_email or "").strip(),
        "company_title": str(payload.company_title or "").strip(),
        "address": str(payload.address or "").strip(),
        "tax_office": str(payload.tax_office or "").strip(),
        "tax_number": str(payload.tax_number or "").strip(),
        "active": _status_to_active(payload.status),
        "notes": str(payload.notes or "").strip(),
    }


def build_restaurants_status() -> RestaurantsModuleStatus:
    return RestaurantsModuleStatus(
        module="restaurants",
        status="active",
        next_slice="restaurant-dashboard",
    )


def build_restaurants_dashboard(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> RestaurantsDashboardResponse:
    summary_values = fetch_restaurant_summary(conn)
    recent_rows = fetch_recent_restaurant_records(conn, limit=limit)
    return RestaurantsDashboardResponse(
        module="restaurants",
        status="active",
        summary=RestaurantSummary(**summary_values),
        recent_entries=[_build_management_entry(row) for row in recent_rows],
    )


def build_restaurants_form_options(
    *,
    pricing_model: str | None = None,
) -> RestaurantsFormOptionsResponse:
    selected_pricing_model = _normalize_pricing_model(pricing_model or "hourly_plus_package")
    return RestaurantsFormOptionsResponse(
        pricing_models=[
            RestaurantPricingModelOption(value=value, label=label)
            for value, label in PRICING_MODEL_LABELS.items()
        ],
        status_options=STATUS_OPTIONS,
        selected_pricing_model=selected_pricing_model,
    )


def build_restaurants_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    pricing_model: str | None = None,
    active: bool | None = None,
    search: str | None = None,
) -> RestaurantsManagementResponse:
    normalized_pricing_model = _normalize_pricing_model(pricing_model) if pricing_model else None
    rows = fetch_restaurant_management_records(
        conn,
        limit=limit,
        pricing_model=normalized_pricing_model,
        active=active,
        search=search,
    )
    return RestaurantsManagementResponse(
        total_entries=count_restaurant_management_records(
            conn,
            pricing_model=normalized_pricing_model,
            active=active,
            search=search,
        ),
        entries=[_build_management_entry(row) for row in rows],
    )


def build_restaurant_detail(
    conn: psycopg.Connection,
    *,
    restaurant_id: int,
) -> RestaurantDetailResponse:
    row = fetch_restaurant_record_by_id(conn, restaurant_id)
    if row is None:
        raise LookupError("Restoran kaydı bulunamadı.")
    return RestaurantDetailResponse(entry=_build_management_entry(row))


def create_restaurant_record(
    conn: psycopg.Connection,
    *,
    payload: RestaurantCreateRequest,
) -> RestaurantCreateResponse:
    errors = _validate_restaurant_payload(payload)
    if errors:
        raise ValueError(errors[0])
    restaurant_id = insert_restaurant_record(conn, _payload_to_values(payload))
    conn.commit()
    return RestaurantCreateResponse(
        restaurant_id=restaurant_id,
        message="Restoran kaydı oluşturuldu.",
    )


def update_restaurant_record_entry(
    conn: psycopg.Connection,
    *,
    restaurant_id: int,
    payload: RestaurantUpdateRequest,
) -> RestaurantUpdateResponse:
    existing_row = fetch_restaurant_record_by_id(conn, restaurant_id)
    if existing_row is None:
        raise LookupError("Restoran kaydı bulunamadı.")
    errors = _validate_restaurant_payload(payload)
    if errors:
        raise ValueError(errors[0])
    update_restaurant_record(conn, restaurant_id, _payload_to_values(payload))
    conn.commit()
    return RestaurantUpdateResponse(
        restaurant_id=restaurant_id,
        message="Restoran kartı güncellendi.",
    )


def toggle_restaurant_record_status(
    conn: psycopg.Connection,
    *,
    restaurant_id: int,
) -> RestaurantStatusUpdateResponse:
    existing_row = fetch_restaurant_record_by_id(conn, restaurant_id)
    if existing_row is None:
        raise LookupError("Restoran kaydı bulunamadı.")
    next_active = not bool(existing_row["active"])
    update_restaurant_status(conn, restaurant_id, active=next_active)
    conn.commit()
    return RestaurantStatusUpdateResponse(
        restaurant_id=restaurant_id,
        active=next_active,
        message="Restoran aktifleştirildi." if next_active else "Restoran pasife alındı.",
    )


def delete_restaurant_record_entry(
    conn: psycopg.Connection,
    *,
    restaurant_id: int,
) -> RestaurantDeleteResponse:
    existing_row = fetch_restaurant_record_by_id(conn, restaurant_id)
    if existing_row is None:
        raise LookupError("Restoran kaydı bulunamadı.")
    linked_people = count_restaurant_linked_personnel(conn, restaurant_id)
    linked_entries = count_restaurant_linked_daily_entries(conn, restaurant_id)
    linked_deductions = count_restaurant_linked_deductions(conn, restaurant_id)
    if linked_people or linked_entries or linked_deductions:
        raise ValueError("Bu restorana bağlı personel, puantaj veya kesinti kaydı var. Önce pasife alman daha doğru olur.")
    delete_restaurant_record(conn, restaurant_id)
    conn.commit()
    return RestaurantDeleteResponse(
        restaurant_id=restaurant_id,
        message="Restoran kaydı kalıcı olarak silindi.",
    )
