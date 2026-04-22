from __future__ import annotations

from datetime import date

import psycopg

from app.repositories.deductions import (
    count_deduction_management_records,
    delete_deduction_records,
    delete_deduction_record,
    fetch_deduction_management_records,
    fetch_deduction_personnel_options,
    fetch_deduction_record_by_id,
    fetch_deduction_records_by_ids,
    fetch_deduction_summary,
    fetch_recent_deduction_records,
    insert_deduction_record,
    update_deduction_record,
)
from app.schemas.deductions import (
    DeductionBulkDeleteRequest,
    DeductionBulkDeleteResponse,
    DeductionCreateRequest,
    DeductionCreateResponse,
    DeductionDeleteResponse,
    DeductionDetailResponse,
    DeductionManagementEntry,
    DeductionPersonnelOption,
    DeductionsDashboardResponse,
    DeductionsFormOptionsResponse,
    DeductionsManagementResponse,
    DeductionsModuleStatus,
    DeductionSummary,
    DeductionUpdateRequest,
    DeductionUpdateResponse,
)

MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE = "Motor Servis Bakım"
MOTOR_DAMAGE_DEDUCTION_TYPE = "Motor Hasar"
HELMET_DEDUCTION_TYPE = "Kask"
PHONE_MOUNT_DEDUCTION_TYPE = "Telefon Tutacagi"
PROTECTIVE_JACKET_DEDUCTION_TYPE = "Korumali Mont"
RAINCOAT_DEDUCTION_TYPE = "Yagmurluk"
BOX_DEDUCTION_TYPE = "Box"
PUNCH_DEDUCTION_TYPE = "Punch"
TSHIRT_DEDUCTION_TYPE = "Tisort"
POLAR_DEDUCTION_TYPE = "Polar"
VEST_DEDUCTION_TYPE = "Yelek"
CHEST_BAG_DEDUCTION_TYPE = "Gogus Cantasi"
ADVANCE_DEDUCTION_TYPE = "Avans"
ADMINISTRATIVE_FINE_DEDUCTION_TYPE = "Idari ceza"
NON_INVOICED_AMOUNT_DEDUCTION_TYPE = "Fatura Edilmeyen Tutar"
FUEL_DEDUCTION_TYPE = "Yakit"
HGS_DEDUCTION_TYPE = "HGS"
PARTNER_CARD_DISCOUNT_DEDUCTION_TYPE = "Partner Kart Indirimi"

LEGACY_DEDUCTION_TYPE_MAP = {
    "Bakim": MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    "Bakım": MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    "Hasar": MOTOR_DAMAGE_DEDUCTION_TYPE,
    "Telefon Tutacağı": PHONE_MOUNT_DEDUCTION_TYPE,
    "Korumalı Mont": PROTECTIVE_JACKET_DEDUCTION_TYPE,
    "Yağmurluk": RAINCOAT_DEDUCTION_TYPE,
    "Tişört": TSHIRT_DEDUCTION_TYPE,
    "Göğüs Çantası": CHEST_BAG_DEDUCTION_TYPE,
    "Yakıt": FUEL_DEDUCTION_TYPE,
    "İdari ceza": ADMINISTRATIVE_FINE_DEDUCTION_TYPE,
}

DEDUCTION_TYPE_OPTIONS = [
    MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    FUEL_DEDUCTION_TYPE,
    HGS_DEDUCTION_TYPE,
    HELMET_DEDUCTION_TYPE,
    PHONE_MOUNT_DEDUCTION_TYPE,
    MOTOR_DAMAGE_DEDUCTION_TYPE,
    PROTECTIVE_JACKET_DEDUCTION_TYPE,
    RAINCOAT_DEDUCTION_TYPE,
    BOX_DEDUCTION_TYPE,
    PUNCH_DEDUCTION_TYPE,
    TSHIRT_DEDUCTION_TYPE,
    POLAR_DEDUCTION_TYPE,
    VEST_DEDUCTION_TYPE,
    CHEST_BAG_DEDUCTION_TYPE,
    ADMINISTRATIVE_FINE_DEDUCTION_TYPE,
    NON_INVOICED_AMOUNT_DEDUCTION_TYPE,
    ADVANCE_DEDUCTION_TYPE,
]
KNOWN_DEDUCTION_TYPES = [*DEDUCTION_TYPE_OPTIONS, PARTNER_CARD_DISCOUNT_DEDUCTION_TYPE]


def _normalize_bulk_deduction_ids(values: list[int]) -> list[int]:
    seen_ids: set[int] = set()
    normalized_ids: list[int] = []
    for raw_value in values:
        try:
            deduction_id = int(raw_value)
        except (TypeError, ValueError):
            continue
        if deduction_id <= 0 or deduction_id in seen_ids:
            continue
        seen_ids.add(deduction_id)
        normalized_ids.append(deduction_id)
    if not normalized_ids:
        raise ValueError("Önce en az bir manuel kesinti kaydı seçmelisin.")
    return normalized_ids


def _normalize_deduction_type(value: str) -> str:
    raw = str(value or "").strip()
    normalized = LEGACY_DEDUCTION_TYPE_MAP.get(raw, raw)
    return normalized if normalized in KNOWN_DEDUCTION_TYPES else MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE


def _get_deduction_type_caption(deduction_type: str) -> str:
    normalized_type = _normalize_deduction_type(deduction_type)
    if normalized_type == MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE:
        return "Cat Kapinda kiralik motorda sirket oder. Satilik ve kendi motorda kurye odemesi olarak kaydedilir."
    if normalized_type == MOTOR_DAMAGE_DEDUCTION_TYPE:
        return "Motor hasar bedeli tum motor tiplerinde kuryeye yansitilir."
    if normalized_type == HGS_DEDUCTION_TYPE:
        return "HGS tutarini toplam olarak gir. Sistem ekstra KDV eklemez."
    if normalized_type == FUEL_DEDUCTION_TYPE:
        return "Yakit tutari aynen kesinti olur; UTTS indirimi hesaplanmaz."
    if normalized_type == ADVANCE_DEDUCTION_TYPE:
        return "Avans, tahsilat takibi icin dusulur ama kurye fatura matrahini azaltmaz."
    if normalized_type == PARTNER_CARD_DISCOUNT_DEDUCTION_TYPE:
        return "Partner kart indirimi artik finansal hesaba katilmaz."
    return ""


def _build_management_entry(row: dict[str, object]) -> DeductionManagementEntry:
    normalized_type = _normalize_deduction_type(str(row.get("deduction_type") or ""))
    auto_source_key = str(row.get("auto_source_key") or "")
    return DeductionManagementEntry(
        id=int(row["id"]),
        personnel_id=int(row["personnel_id"]),
        personnel_label=str(row.get("personnel_label") or "-"),
        deduction_date=row["deduction_date"],
        deduction_type=normalized_type,
        type_caption=_get_deduction_type_caption(normalized_type),
        amount=float(row.get("amount") or 0),
        notes=str(row.get("notes") or ""),
        auto_source_key=auto_source_key,
        is_auto_record=bool(auto_source_key.strip()),
    )


def build_deductions_status() -> DeductionsModuleStatus:
    return DeductionsModuleStatus(
        module="deductions",
        status="active",
        next_slice="deductions-management",
    )


def build_deductions_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
    limit: int,
) -> DeductionsDashboardResponse:
    summary_values = fetch_deduction_summary(conn, reference_date=reference_date)
    recent_rows = fetch_recent_deduction_records(conn, limit=limit)
    return DeductionsDashboardResponse(
        module="deductions",
        status="active",
        summary=DeductionSummary(**summary_values),
        recent_entries=[_build_management_entry(row) for row in recent_rows],
    )


def build_deductions_form_options(
    conn: psycopg.Connection,
    *,
    personnel_id: int | None = None,
) -> DeductionsFormOptionsResponse:
    personnel_rows = fetch_deduction_personnel_options(conn)
    selected_personnel_id = personnel_id
    if selected_personnel_id is None and personnel_rows:
        selected_personnel_id = int(personnel_rows[0]["id"])
    return DeductionsFormOptionsResponse(
        personnel=[
            DeductionPersonnelOption(
                id=int(row["id"]),
                label=f"{str(row['full_name']).strip()} | {str(row['role']).strip()} | {str(row['restaurant_label']).strip()}",
            )
            for row in personnel_rows
        ],
        deduction_types=DEDUCTION_TYPE_OPTIONS,
        type_captions={item: _get_deduction_type_caption(item) for item in DEDUCTION_TYPE_OPTIONS},
        selected_personnel_id=selected_personnel_id,
    )


def build_deductions_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    personnel_id: int | None = None,
    deduction_type: str | None = None,
    search: str | None = None,
) -> DeductionsManagementResponse:
    normalized_type = _normalize_deduction_type(deduction_type) if deduction_type else None
    rows = fetch_deduction_management_records(
        conn,
        limit=limit,
        personnel_id=personnel_id,
        deduction_type=normalized_type,
        search=search,
    )
    return DeductionsManagementResponse(
        total_entries=count_deduction_management_records(
            conn,
            personnel_id=personnel_id,
            deduction_type=normalized_type,
            search=search,
        ),
        entries=[_build_management_entry(row) for row in rows],
    )


def build_deduction_detail(
    conn: psycopg.Connection,
    *,
    deduction_id: int,
) -> DeductionDetailResponse:
    row = fetch_deduction_record_by_id(conn, deduction_id)
    if row is None:
        raise LookupError("Kesinti kaydı bulunamadı.")
    return DeductionDetailResponse(entry=_build_management_entry(row))


def create_deduction_entry(
    conn: psycopg.Connection,
    *,
    payload: DeductionCreateRequest,
) -> DeductionCreateResponse:
    normalized_type = _normalize_deduction_type(payload.deduction_type)
    if payload.amount <= 0:
        raise ValueError("Tutar sıfırdan büyük olmalı.")

    deduction_id = insert_deduction_record(
        conn,
        {
            "personnel_id": payload.personnel_id,
            "deduction_date": payload.deduction_date,
            "deduction_type": normalized_type,
            "amount": float(payload.amount),
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return DeductionCreateResponse(
        deduction_id=deduction_id,
        message="Kesinti kaydı oluşturuldu.",
    )


def update_deduction_entry(
    conn: psycopg.Connection,
    *,
    deduction_id: int,
    payload: DeductionUpdateRequest,
) -> DeductionUpdateResponse:
    existing = fetch_deduction_record_by_id(conn, deduction_id)
    if existing is None:
        raise LookupError("Kesinti kaydı bulunamadı.")
    if str(existing.get("auto_source_key") or "").strip():
        raise ValueError("Otomatik oluşan kesinti kayıtları v2 ekranından düzenlenemez.")

    normalized_type = _normalize_deduction_type(payload.deduction_type)
    if payload.amount <= 0:
        raise ValueError("Tutar sıfırdan büyük olmalı.")

    update_deduction_record(
        conn,
        deduction_id,
        {
            "personnel_id": payload.personnel_id,
            "deduction_date": payload.deduction_date,
            "deduction_type": normalized_type,
            "amount": float(payload.amount),
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return DeductionUpdateResponse(
        deduction_id=deduction_id,
        message="Kesinti kaydı güncellendi.",
    )


def delete_deduction_entry(
    conn: psycopg.Connection,
    *,
    deduction_id: int,
) -> DeductionDeleteResponse:
    existing = fetch_deduction_record_by_id(conn, deduction_id)
    if existing is None:
        raise LookupError("Kesinti kaydı bulunamadı.")
    if str(existing.get("auto_source_key") or "").strip():
        raise ValueError("Otomatik oluşan kesinti kayıtları v2 ekranından silinemez.")
    delete_deduction_record(conn, deduction_id)
    conn.commit()
    return DeductionDeleteResponse(
        deduction_id=deduction_id,
        message="Kesinti kaydı silindi.",
    )


def bulk_delete_deduction_entries(
    conn: psycopg.Connection,
    *,
    payload: DeductionBulkDeleteRequest,
) -> DeductionBulkDeleteResponse:
    deduction_ids = _normalize_bulk_deduction_ids(payload.deduction_ids)
    existing_rows = fetch_deduction_records_by_ids(conn, deduction_ids)
    existing_rows_by_id = {int(row["id"]): row for row in existing_rows}
    missing_ids = [deduction_id for deduction_id in deduction_ids if deduction_id not in existing_rows_by_id]
    if missing_ids:
        missing_labels = ", ".join(str(deduction_id) for deduction_id in missing_ids)
        raise LookupError(f"Seçilen kesinti kayıtları bulunamadı: {missing_labels}.")

    auto_record_ids = [
        deduction_id
        for deduction_id in deduction_ids
        if str(existing_rows_by_id[deduction_id].get("auto_source_key") or "").strip()
    ]
    if auto_record_ids:
        blocked_labels = ", ".join(str(deduction_id) for deduction_id in auto_record_ids)
        raise ValueError(
            f"Otomatik oluşan kesinti kayıtları toplu silinemez: {blocked_labels}."
        )

    deleted_ids = sorted(delete_deduction_records(conn, deduction_ids))
    if len(deleted_ids) != len(deduction_ids):
        raise LookupError("Seçilen kesinti kayıtlarının bir kısmı silinemedi.")

    conn.commit()
    deleted_count = len(deleted_ids)
    return DeductionBulkDeleteResponse(
        deduction_ids=deleted_ids,
        deleted_count=deleted_count,
        message=f"{deleted_count} kesinti kaydı silindi.",
    )
