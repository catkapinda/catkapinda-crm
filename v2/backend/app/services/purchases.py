from __future__ import annotations

from datetime import date

import psycopg

from app.repositories.purchases import (
    count_purchase_management_records,
    delete_purchase_record,
    fetch_purchase_management_records,
    fetch_purchase_record_by_id,
    fetch_purchase_summary,
    fetch_recent_purchase_records,
    insert_purchase_record,
    update_purchase_record,
)
from app.schemas.purchases import (
    PurchaseCreateRequest,
    PurchaseCreateResponse,
    PurchaseDeleteResponse,
    PurchaseDetailResponse,
    PurchaseManagementEntry,
    PurchaseSummary,
    PurchasesDashboardResponse,
    PurchasesFormOptionsResponse,
    PurchasesManagementResponse,
    PurchasesModuleStatus,
    PurchaseUpdateRequest,
    PurchaseUpdateResponse,
)

PURCHASE_ITEM_OPTIONS = [
    "Box",
    "Punch",
    "Polar",
    "Tişört",
    "Korumalı Mont",
    "Yelek",
    "Reflektörlü Yelek",
    "Yağmurluk",
    "Göğüs Çantası",
    "Kask",
    "Telefon Tutacağı",
    "Motor Bakım",
]


def _normalize_item_name(value: str) -> str:
    normalized = str(value or "").strip()
    return normalized if normalized in PURCHASE_ITEM_OPTIONS else PURCHASE_ITEM_OPTIONS[0]


def _build_purchase_entry(row: dict[str, object]) -> PurchaseManagementEntry:
    return PurchaseManagementEntry(
        id=int(row["id"]),
        purchase_date=row["purchase_date"],
        item_name=str(row.get("item_name") or ""),
        quantity=int(row.get("quantity") or 0),
        total_invoice_amount=float(row.get("total_invoice_amount") or 0),
        unit_cost=float(row.get("unit_cost") or 0),
        supplier=str(row.get("supplier") or ""),
        invoice_no=str(row.get("invoice_no") or ""),
        notes=str(row.get("notes") or ""),
    )


def build_purchases_status() -> PurchasesModuleStatus:
    return PurchasesModuleStatus(
        module="purchases",
        status="active",
        next_slice="purchases-management",
    )


def build_purchases_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
    limit: int,
) -> PurchasesDashboardResponse:
    summary_values = fetch_purchase_summary(conn, reference_date=reference_date)
    recent_rows = fetch_recent_purchase_records(conn, limit=limit)
    return PurchasesDashboardResponse(
        module="purchases",
        status="active",
        summary=PurchaseSummary(**summary_values),
        recent_entries=[_build_purchase_entry(row) for row in recent_rows],
    )


def build_purchases_form_options(
    *,
    item_name: str | None = None,
) -> PurchasesFormOptionsResponse:
    selected_item = _normalize_item_name(item_name or PURCHASE_ITEM_OPTIONS[0])
    return PurchasesFormOptionsResponse(
        item_options=PURCHASE_ITEM_OPTIONS,
        selected_item=selected_item,
    )


def build_purchases_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    item_name: str | None = None,
    search: str | None = None,
) -> PurchasesManagementResponse:
    normalized_item = _normalize_item_name(item_name) if item_name else None
    rows = fetch_purchase_management_records(
        conn,
        limit=limit,
        item_name=normalized_item,
        search=search,
    )
    return PurchasesManagementResponse(
        total_entries=count_purchase_management_records(
            conn,
            item_name=normalized_item,
            search=search,
        ),
        entries=[_build_purchase_entry(row) for row in rows],
    )


def build_purchase_detail(
    conn: psycopg.Connection,
    *,
    purchase_id: int,
) -> PurchaseDetailResponse:
    row = fetch_purchase_record_by_id(conn, purchase_id)
    if row is None:
        raise LookupError("Satın alma kaydı bulunamadı.")
    return PurchaseDetailResponse(entry=_build_purchase_entry(row))


def create_purchase_record(
    conn: psycopg.Connection,
    *,
    payload: PurchaseCreateRequest,
) -> PurchaseCreateResponse:
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmalı.")
    if payload.total_invoice_amount <= 0:
        raise ValueError("Toplam fatura tutarı sıfırdan büyük olmalı.")

    item_name = _normalize_item_name(payload.item_name)
    total_invoice_amount = float(payload.total_invoice_amount)
    quantity = int(payload.quantity)
    unit_cost = round(total_invoice_amount / quantity, 2)
    purchase_id = insert_purchase_record(
        conn,
        {
            "purchase_date": payload.purchase_date,
            "item_name": item_name,
            "quantity": quantity,
            "total_invoice_amount": total_invoice_amount,
            "unit_cost": unit_cost,
            "supplier": str(payload.supplier or "").strip(),
            "invoice_no": str(payload.invoice_no or "").strip(),
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return PurchaseCreateResponse(
        purchase_id=purchase_id,
        message=f"Satın alma kaydı oluşturuldu. Birim maliyet: {unit_cost:.2f}₺",
    )


def update_purchase_record_entry(
    conn: psycopg.Connection,
    *,
    purchase_id: int,
    payload: PurchaseUpdateRequest,
) -> PurchaseUpdateResponse:
    existing = fetch_purchase_record_by_id(conn, purchase_id)
    if existing is None:
        raise LookupError("Satın alma kaydı bulunamadı.")
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmalı.")
    if payload.total_invoice_amount <= 0:
        raise ValueError("Toplam fatura tutarı sıfırdan büyük olmalı.")

    item_name = _normalize_item_name(payload.item_name)
    total_invoice_amount = float(payload.total_invoice_amount)
    quantity = int(payload.quantity)
    unit_cost = round(total_invoice_amount / quantity, 2)
    update_purchase_record(
        conn,
        purchase_id,
        {
            "purchase_date": payload.purchase_date,
            "item_name": item_name,
            "quantity": quantity,
            "total_invoice_amount": total_invoice_amount,
            "unit_cost": unit_cost,
            "supplier": str(payload.supplier or "").strip(),
            "invoice_no": str(payload.invoice_no or "").strip(),
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return PurchaseUpdateResponse(
        purchase_id=purchase_id,
        message=f"Satın alma kaydı güncellendi. Yeni birim maliyet: {unit_cost:.2f}₺",
    )


def delete_purchase_record_entry(
    conn: psycopg.Connection,
    *,
    purchase_id: int,
) -> PurchaseDeleteResponse:
    existing = fetch_purchase_record_by_id(conn, purchase_id)
    if existing is None:
        raise LookupError("Satın alma kaydı bulunamadı.")
    delete_purchase_record(conn, purchase_id)
    conn.commit()
    return PurchaseDeleteResponse(
        purchase_id=purchase_id,
        message="Satın alma kaydı silindi.",
    )
