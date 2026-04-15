from __future__ import annotations

from datetime import datetime, timezone

import psycopg

from app.repositories.sales import (
    count_sales_management_records,
    delete_sales_record,
    fetch_recent_sales_records,
    fetch_sales_management_records,
    fetch_sales_record_by_id,
    fetch_sales_summary,
    insert_sales_record,
    update_sales_record,
)
from app.schemas.sales import (
    SalesCreateRequest,
    SalesCreateResponse,
    SalesDashboardResponse,
    SalesDeleteResponse,
    SalesDetailResponse,
    SalesEntry,
    SalesFormOptionsResponse,
    SalesManagementResponse,
    SalesModuleStatus,
    SalesPricingModelOption,
    SalesSummary,
    SalesUpdateRequest,
    SalesUpdateResponse,
)

PRICING_MODEL_LABELS = {
    "hourly_plus_package": "Hacimsiz Primli",
    "threshold_package": "Hacimli Primli",
    "hourly_only": "Sadece Saatlik",
    "fixed_monthly": "Sabit Aylik Ucret",
}
STATUS_OPTIONS = [
    "Yeni Talep",
    "İlk Görüşme Yapıldı",
    "Teklif Hazırlanıyor",
    "Teklif İletildi",
    "Toplantı Planlandı",
    "Tekrar Aranacak",
    "Olumsuz",
    "Sözleşme İmzalandı",
]
SOURCE_OPTIONS = ["Mail", "Telefon", "Referans", "Çat Kapı Ziyaret", "WhatsApp"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _display_pricing_model(value: str) -> str:
    return PRICING_MODEL_LABELS.get(value, value or "-")


def _normalize_pricing_model(value: str) -> str:
    normalized = str(value or "").strip()
    return normalized if normalized in PRICING_MODEL_LABELS else "hourly_plus_package"


def _format_compact_currency(value: float) -> str:
    amount = float(value or 0)
    if abs(amount - round(amount)) < 0.005:
        return f"{int(round(amount)):,} TL".replace(",", ".")
    return f"{amount:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def _build_pricing_hint(
    *,
    pricing_model: str,
    hourly_rate: float,
    package_rate: float,
    package_threshold: int,
    package_rate_low: float,
    package_rate_high: float,
    fixed_monthly_fee: float,
) -> str:
    if pricing_model == "threshold_package":
        threshold_value = package_threshold if int(package_threshold or 0) > 0 else 390
        return (
            f"{_format_compact_currency(hourly_rate)}/saat | "
            f"{threshold_value} alti {_format_compact_currency(package_rate_low)} | "
            f"ustu {_format_compact_currency(package_rate_high)}"
        )
    if pricing_model == "hourly_plus_package":
        return f"{_format_compact_currency(hourly_rate)}/saat + {_format_compact_currency(package_rate)}/paket"
    if pricing_model == "hourly_only":
        return f"{_format_compact_currency(hourly_rate)}/saat"
    if pricing_model == "fixed_monthly":
        return f"{_format_compact_currency(fixed_monthly_fee)}/ay"
    return ""


def _validate_payload(payload: SalesCreateRequest | SalesUpdateRequest) -> list[str]:
    errors: list[str] = []
    if not str(payload.restaurant_name or "").strip():
        errors.append("Restoran adi zorunlu.")
    if not str(payload.city or "").strip():
        errors.append("Il bilgisi zorunlu.")
    if not str(payload.district or "").strip():
        errors.append("Ilce bilgisi zorunlu.")
    if not str(payload.contact_name or "").strip():
        errors.append("Yetkili bilgisi zorunlu.")
    if not str(payload.contact_phone or "").strip():
        errors.append("Yetkili telefon bilgisi zorunlu.")
    if not str(payload.status or "").strip():
        errors.append("Durum seçimi zorunlu.")
    pricing_model = _normalize_pricing_model(payload.pricing_model)
    if pricing_model == "hourly_plus_package":
        if float(payload.hourly_rate or 0) <= 0:
            errors.append("Hacimsiz Primli modelde saatlik ücret zorunlu.")
        if float(payload.package_rate or 0) <= 0:
            errors.append("Hacimsiz Primli modelde paket ücreti zorunlu.")
    elif pricing_model == "threshold_package":
        if float(payload.hourly_rate or 0) <= 0:
            errors.append("Hacimli Primli modelde saatlik ücret zorunlu.")
        if int(payload.package_threshold or 0) <= 0:
            errors.append("Hacimli Primli modelde paket eşiği zorunlu.")
        if float(payload.package_rate_low or 0) <= 0:
            errors.append("Hacimli Primli modelde eşik altı ücret zorunlu.")
        if float(payload.package_rate_high or 0) <= 0:
            errors.append("Hacimli Primli modelde eşik üstü ücret zorunlu.")
    elif pricing_model == "hourly_only":
        if float(payload.hourly_rate or 0) <= 0:
            errors.append("Sadece Saatlik modelde saatlik ücret zorunlu.")
    elif pricing_model == "fixed_monthly":
        if float(payload.fixed_monthly_fee or 0) <= 0:
            errors.append("Sabit Aylık Ücret modelde aylık tutar zorunlu.")
    return errors


def _payload_to_values(payload: SalesCreateRequest | SalesUpdateRequest) -> dict[str, object]:
    pricing_model = _normalize_pricing_model(payload.pricing_model)
    pricing_model_hint = _build_pricing_hint(
        pricing_model=pricing_model,
        hourly_rate=float(payload.hourly_rate or 0),
        package_rate=float(payload.package_rate or 0),
        package_threshold=int(payload.package_threshold or 390),
        package_rate_low=float(payload.package_rate_low or 0),
        package_rate_high=float(payload.package_rate_high or 0),
        fixed_monthly_fee=float(payload.fixed_monthly_fee or 0),
    )
    proposed_quote = float(payload.proposed_quote or 0)
    if pricing_model == "fixed_monthly":
        proposed_quote = float(payload.fixed_monthly_fee or 0)
    return {
        "restaurant_name": str(payload.restaurant_name or "").strip(),
        "city": str(payload.city or "").strip(),
        "district": str(payload.district or "").strip(),
        "address": str(payload.address or "").strip(),
        "contact_name": str(payload.contact_name or "").strip(),
        "contact_phone": str(payload.contact_phone or "").strip(),
        "contact_email": str(payload.contact_email or "").strip(),
        "requested_courier_count": int(payload.requested_courier_count or 0),
        "lead_source": str(payload.lead_source or "").strip(),
        "proposed_quote": proposed_quote,
        "pricing_model": pricing_model,
        "hourly_rate": float(payload.hourly_rate or 0),
        "package_rate": float(payload.package_rate or 0),
        "package_threshold": int(payload.package_threshold or 390),
        "package_rate_low": float(payload.package_rate_low or 0),
        "package_rate_high": float(payload.package_rate_high or 0),
        "fixed_monthly_fee": float(payload.fixed_monthly_fee or 0),
        "pricing_model_hint": pricing_model_hint,
        "status": str(payload.status or "").strip(),
        "next_follow_up_date": payload.next_follow_up_date,
        "assigned_owner": str(payload.assigned_owner or "").strip(),
        "notes": str(payload.notes or "").strip(),
    }


def _build_entry(row: dict[str, object]) -> SalesEntry:
    return SalesEntry(
        id=int(row["id"]),
        restaurant_name=str(row.get("restaurant_name") or ""),
        city=str(row.get("city") or ""),
        district=str(row.get("district") or ""),
        address=str(row.get("address") or ""),
        contact_name=str(row.get("contact_name") or ""),
        contact_phone=str(row.get("contact_phone") or ""),
        contact_email=str(row.get("contact_email") or ""),
        requested_courier_count=int(row.get("requested_courier_count") or 0),
        lead_source=str(row.get("lead_source") or ""),
        proposed_quote=float(row.get("proposed_quote") or 0),
        pricing_model=str(row.get("pricing_model") or ""),
        pricing_model_label=_display_pricing_model(str(row.get("pricing_model") or "")),
        pricing_model_hint=str(row.get("pricing_model_hint") or ""),
        hourly_rate=float(row.get("hourly_rate") or 0),
        package_rate=float(row.get("package_rate") or 0),
        package_threshold=int(row.get("package_threshold") or 390),
        package_rate_low=float(row.get("package_rate_low") or 0),
        package_rate_high=float(row.get("package_rate_high") or 0),
        fixed_monthly_fee=float(row.get("fixed_monthly_fee") or 0),
        status=str(row.get("status") or ""),
        next_follow_up_date=row.get("next_follow_up_date"),
        assigned_owner=str(row.get("assigned_owner") or ""),
        notes=str(row.get("notes") or ""),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


def build_sales_status() -> SalesModuleStatus:
    return SalesModuleStatus(module="sales", status="active", next_slice="sales-ops")


def build_sales_dashboard(conn: psycopg.Connection, *, limit: int) -> SalesDashboardResponse:
    summary_values = fetch_sales_summary(conn)
    recent_rows = fetch_recent_sales_records(conn, limit=limit)
    return SalesDashboardResponse(
        module="sales",
        status="active",
        summary=SalesSummary(**summary_values),
        recent_entries=[_build_entry(row) for row in recent_rows],
    )


def build_sales_form_options(*, pricing_model: str | None = None) -> SalesFormOptionsResponse:
    selected_pricing_model = _normalize_pricing_model(pricing_model or "hourly_plus_package")
    return SalesFormOptionsResponse(
        pricing_models=[
            SalesPricingModelOption(value=value, label=label)
            for value, label in PRICING_MODEL_LABELS.items()
        ],
        source_options=SOURCE_OPTIONS,
        status_options=STATUS_OPTIONS,
        selected_pricing_model=selected_pricing_model,
    )


def build_sales_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    status: str | None = None,
    search: str | None = None,
) -> SalesManagementResponse:
    rows = fetch_sales_management_records(conn, limit=limit, status=status, search=search)
    return SalesManagementResponse(
        total_entries=count_sales_management_records(conn, status=status, search=search),
        entries=[_build_entry(row) for row in rows],
    )


def build_sales_detail(conn: psycopg.Connection, *, sales_id: int) -> SalesDetailResponse:
    row = fetch_sales_record_by_id(conn, sales_id)
    if row is None:
        raise LookupError("Satış kaydı bulunamadı.")
    return SalesDetailResponse(entry=_build_entry(row))


def create_sales_record(conn: psycopg.Connection, *, payload: SalesCreateRequest) -> SalesCreateResponse:
    errors = _validate_payload(payload)
    if errors:
        raise ValueError(errors[0])
    values = _payload_to_values(payload)
    now_iso = _utc_now_iso()
    values["created_at"] = now_iso
    values["updated_at"] = now_iso
    entry_id = insert_sales_record(conn, values)
    conn.commit()
    return SalesCreateResponse(message="Satış fırsatı oluşturuldu.", entry_id=entry_id)


def update_sales_record_entry(
    conn: psycopg.Connection,
    *,
    sales_id: int,
    payload: SalesUpdateRequest,
) -> SalesUpdateResponse:
    if fetch_sales_record_by_id(conn, sales_id) is None:
        raise LookupError("Satış kaydı bulunamadı.")
    errors = _validate_payload(payload)
    if errors:
        raise ValueError(errors[0])
    values = _payload_to_values(payload)
    values["updated_at"] = _utc_now_iso()
    update_sales_record(conn, sales_id, values)
    conn.commit()
    return SalesUpdateResponse(message="Satış fırsatı güncellendi.")


def delete_sales_record_entry(conn: psycopg.Connection, *, sales_id: int) -> SalesDeleteResponse:
    if fetch_sales_record_by_id(conn, sales_id) is None:
        raise LookupError("Satış kaydı bulunamadı.")
    delete_sales_record(conn, sales_id)
    conn.commit()
    return SalesDeleteResponse(message="Satış fırsatı silindi.")
