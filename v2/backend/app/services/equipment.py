from __future__ import annotations

import calendar
from datetime import date

import psycopg

from app.repositories.equipment import (
    count_box_return_management_records,
    count_equipment_issue_management_records,
    delete_box_return_record,
    delete_equipment_issue_installments,
    delete_equipment_issue_record,
    fetch_box_return_by_id,
    fetch_box_return_management_records,
    fetch_equipment_cost_defaults,
    fetch_equipment_installments,
    fetch_equipment_issue_by_id,
    fetch_equipment_issue_management_records,
    fetch_equipment_personnel_options,
    fetch_equipment_purchase_summary,
    fetch_equipment_sales_profit,
    fetch_equipment_summary,
    fetch_recent_box_returns,
    fetch_recent_equipment_issues,
    insert_box_return_record,
    insert_equipment_issue_record,
    update_box_return_record,
    update_equipment_issue_record,
)
from app.schemas.equipment import (
    BoxReturnCreateRequest,
    BoxReturnCreateResponse,
    BoxReturnDeleteResponse,
    BoxReturnDetailResponse,
    BoxReturnManagementEntry,
    BoxReturnUpdateRequest,
    BoxReturnUpdateResponse,
    BoxReturnsManagementResponse,
    EquipmentDashboardResponse,
    EquipmentFormOptionsResponse,
    EquipmentInstallmentEntry,
    EquipmentIssueCreateRequest,
    EquipmentIssueCreateResponse,
    EquipmentIssueDeleteResponse,
    EquipmentIssueDetailResponse,
    EquipmentIssueManagementEntry,
    EquipmentIssueUpdateRequest,
    EquipmentIssueUpdateResponse,
    EquipmentIssuesManagementResponse,
    EquipmentItemDefault,
    EquipmentModuleStatus,
    EquipmentPersonnelOption,
    EquipmentPurchaseSummaryEntry,
    EquipmentSalesProfitEntry,
    EquipmentSummary,
)

VAT_RATE_DEFAULT = 20.0
EQUIPMENT_REDUCED_VAT_START_DATE = date(2026, 3, 1)
EQUIPMENT_VAT_RATE_AFTER_REDUCTION = 10.0
EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS = {"Kask", "Telefon Tutacağı", "Motor Kirası", "Motor Satın Alım"}
AUTO_MOTOR_RENTAL_DEDUCTION = 13000.0
AUTO_MOTOR_PURCHASE_TOTAL_PRICE = 135000.0
AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = 12
AUTO_EQUIPMENT_INSTALLMENT_COUNT = 2
ISSUE_ITEMS = [
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
    "Motor Kirası",
    "Motor Satın Alım",
]
SALE_TYPE_OPTIONS = ["Satış", "Depozit / Teslim"]
RETURN_CONDITION_OPTIONS = ["Temiz", "Hasarlı", "Parasını istemedi"]
INSTALLMENT_COUNT_OPTIONS = [1, 2, 3, 6, 12]
SALE_PRICE_DEFAULTS = {
    "Box": 3200.0,
    "Punch": 2000.0,
    "Korumalı Mont": 4750.0,
    "Motor Kirası": AUTO_MOTOR_RENTAL_DEDUCTION,
    "Motor Satın Alım": AUTO_MOTOR_PURCHASE_TOTAL_PRICE,
}


def _normalize_issue_item(value: str) -> str:
    item_name = str(value or "").strip()
    return item_name if item_name in ISSUE_ITEMS else ISSUE_ITEMS[0]


def _normalize_sale_type(value: str) -> str:
    sale_type = str(value or "").strip()
    return sale_type if sale_type in SALE_TYPE_OPTIONS else SALE_TYPE_OPTIONS[0]


def _normalize_return_condition(value: str) -> str:
    condition = str(value or "").strip()
    return condition if condition in RETURN_CONDITION_OPTIONS else RETURN_CONDITION_OPTIONS[0]


def _get_equipment_vat_rate(item_name: str, issue_date: date) -> float:
    if item_name in EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS:
        return VAT_RATE_DEFAULT
    if issue_date >= EQUIPMENT_REDUCED_VAT_START_DATE:
        return EQUIPMENT_VAT_RATE_AFTER_REDUCTION
    return VAT_RATE_DEFAULT


def _get_default_sale_price(item_name: str) -> float:
    return float(SALE_PRICE_DEFAULTS.get(item_name, 0.0))


def _get_default_installment_count(item_name: str) -> int:
    if item_name == "Motor Satın Alım":
        return AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT
    if item_name == "Motor Kirası":
        return 1
    return AUTO_EQUIPMENT_INSTALLMENT_COUNT


def _normalize_installment_count(sale_type: str, installment_count: int) -> int:
    if sale_type != "Satış":
        return 1
    return max(int(installment_count or 1), 1)


def _generates_installments(sale_type: str, total_sale_amount: float, installment_count: int) -> bool:
    return sale_type == "Satış" and float(total_sale_amount or 0) > 0 and _normalize_installment_count(sale_type, installment_count) > 0


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _rebuild_issue_installments(
    conn: psycopg.Connection,
    *,
    issue_id: int,
    personnel_id: int,
    issue_date: date,
    item_name: str,
    total_sale_amount: float,
    installment_count: int,
    sale_type: str,
) -> None:
    delete_equipment_issue_installments(conn, issue_id)
    resolved_installment_count = _normalize_installment_count(sale_type, installment_count)
    if not _generates_installments(sale_type, total_sale_amount, resolved_installment_count):
        return
    installment_amount = round(float(total_sale_amount) / resolved_installment_count, 2)
    for index in range(resolved_installment_count):
        due_date = _add_months(issue_date, index).isoformat()
        conn.execute(
            """
            INSERT INTO deductions (
                personnel_id,
                deduction_date,
                deduction_type,
                amount,
                notes,
                equipment_issue_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                personnel_id,
                due_date,
                "Zimmet Taksiti",
                installment_amount,
                f"{item_name} {index + 1}/{resolved_installment_count}",
                issue_id,
            ),
        )


def _build_issue_entry(row: dict[str, object]) -> EquipmentIssueManagementEntry:
    auto_source_key = str(row.get("auto_source_key") or "")
    return EquipmentIssueManagementEntry(
        id=int(row["id"]),
        personnel_id=int(row.get("personnel_id") or 0),
        personnel_label=str(row.get("personnel_label") or "-"),
        issue_date=row["issue_date"],
        item_name=str(row.get("item_name") or ""),
        quantity=int(row.get("quantity") or 0),
        unit_cost=float(row.get("unit_cost") or 0),
        unit_sale_price=float(row.get("unit_sale_price") or 0),
        vat_rate=float(row.get("vat_rate") or VAT_RATE_DEFAULT),
        total_cost=float(row.get("total_cost") or 0),
        total_sale=float(row.get("total_sale") or 0),
        gross_profit=float(row.get("gross_profit") or 0),
        installment_count=int(row.get("installment_count") or 0),
        sale_type=str(row.get("sale_type") or ""),
        notes=str(row.get("notes") or ""),
        auto_source_key=auto_source_key,
        is_auto_record=bool(auto_source_key.strip()),
    )


def _build_box_return_entry(row: dict[str, object]) -> BoxReturnManagementEntry:
    return BoxReturnManagementEntry(
        id=int(row["id"]),
        personnel_id=int(row.get("personnel_id") or 0),
        personnel_label=str(row.get("personnel_label") or "-"),
        return_date=row["return_date"],
        quantity=int(row.get("quantity") or 0),
        condition_status=str(row.get("condition_status") or ""),
        payout_amount=float(row.get("payout_amount") or 0),
        waived=bool(row.get("waived") or 0),
        notes=str(row.get("notes") or ""),
    )


def build_equipment_status() -> EquipmentModuleStatus:
    return EquipmentModuleStatus(
        module="equipment",
        status="active",
        next_slice="equipment-management",
    )


def build_equipment_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
    limit: int,
) -> EquipmentDashboardResponse:
    summary_values = fetch_equipment_summary(conn, reference_date=reference_date)
    return EquipmentDashboardResponse(
        module="equipment",
        status="active",
        summary=EquipmentSummary(**summary_values),
        recent_issues=[_build_issue_entry(row) for row in fetch_recent_equipment_issues(conn, limit=limit)],
        recent_box_returns=[_build_box_return_entry(row) for row in fetch_recent_box_returns(conn, limit=limit)],
        installment_entries=[
            EquipmentInstallmentEntry(
                deduction_date=row["deduction_date"],
                personnel_label=str(row.get("personnel_label") or "-"),
                deduction_type=str(row.get("deduction_type") or ""),
                amount=float(row.get("amount") or 0),
                notes=str(row.get("notes") or ""),
                auto_source_key=str(row.get("auto_source_key") or ""),
            )
            for row in fetch_equipment_installments(conn, limit=limit)
        ],
        sales_profit=[
            EquipmentSalesProfitEntry(
                item_name=str(row.get("item_name") or ""),
                sold_qty=int(row.get("sold_qty") or 0),
                total_cost=float(row.get("total_cost") or 0),
                total_sale=float(row.get("total_sale") or 0),
                gross_profit=float(row.get("gross_profit") or 0),
            )
            for row in fetch_equipment_sales_profit(conn, limit=min(limit, 8))
        ],
        purchase_summary=[
            EquipmentPurchaseSummaryEntry(
                item_name=str(row.get("item_name") or ""),
                purchased_qty=int(row.get("purchased_qty") or 0),
                purchased_total=float(row.get("purchased_total") or 0),
                weighted_unit_cost=float(row.get("weighted_unit_cost") or 0),
            )
            for row in fetch_equipment_purchase_summary(conn, limit=min(limit, 8))
        ],
    )


def build_equipment_form_options(conn: psycopg.Connection) -> EquipmentFormOptionsResponse:
    personnel_rows = fetch_equipment_personnel_options(conn)
    purchase_defaults = {
        str(row.get("item_name") or ""): float(row.get("weighted_unit_cost") or 0)
        for row in fetch_equipment_cost_defaults(conn)
    }
    item_defaults = {
        item_name: EquipmentItemDefault(
            default_unit_cost=float(purchase_defaults.get(item_name, 0.0)),
            default_sale_price=_get_default_sale_price(item_name),
            default_installment_count=_get_default_installment_count(item_name),
            default_vat_rate=_get_equipment_vat_rate(item_name, date.today()),
        )
        for item_name in ISSUE_ITEMS
    }
    selected_personnel_id = int(personnel_rows[0]["id"]) if personnel_rows else None
    return EquipmentFormOptionsResponse(
        personnel=[
            EquipmentPersonnelOption(
                id=int(row["id"]),
                label=" | ".join(
                    [
                        str(row.get("full_name") or "-").strip(),
                        str(row.get("role") or "-").strip() or "-",
                        str(row.get("restaurant_label") or "-").strip() or "-",
                        str(row.get("status") or "-").strip() or "-",
                    ]
                ),
            )
            for row in personnel_rows
        ],
        issue_items=ISSUE_ITEMS,
        sale_type_options=SALE_TYPE_OPTIONS,
        return_condition_options=RETURN_CONDITION_OPTIONS,
        installment_count_options=INSTALLMENT_COUNT_OPTIONS,
        item_defaults=item_defaults,
        selected_personnel_id=selected_personnel_id,
        selected_item=ISSUE_ITEMS[0],
    )


def build_equipment_issue_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    personnel_id: int | None = None,
    item_name: str | None = None,
    search: str | None = None,
) -> EquipmentIssuesManagementResponse:
    normalized_item = _normalize_issue_item(item_name) if item_name else None
    return EquipmentIssuesManagementResponse(
        total_entries=count_equipment_issue_management_records(
            conn,
            personnel_id=personnel_id,
            item_name=normalized_item,
            search=search,
        ),
        entries=[
            _build_issue_entry(row)
            for row in fetch_equipment_issue_management_records(
                conn,
                limit=limit,
                personnel_id=personnel_id,
                item_name=normalized_item,
                search=search,
            )
        ],
    )


def build_equipment_issue_detail(
    conn: psycopg.Connection,
    *,
    issue_id: int,
) -> EquipmentIssueDetailResponse:
    row = fetch_equipment_issue_by_id(conn, issue_id)
    if row is None:
        raise LookupError("Zimmet kaydi bulunamadi.")
    return EquipmentIssueDetailResponse(entry=_build_issue_entry(row))


def create_equipment_issue_entry(
    conn: psycopg.Connection,
    *,
    payload: EquipmentIssueCreateRequest,
) -> EquipmentIssueCreateResponse:
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmali.")
    if payload.unit_cost < 0 or payload.unit_sale_price < 0:
        raise ValueError("Maliyet ve satis tutari negatif olamaz.")

    item_name = _normalize_issue_item(payload.item_name)
    sale_type = _normalize_sale_type(payload.sale_type)
    installment_count = _normalize_installment_count(sale_type, payload.installment_count)
    vat_rate = _get_equipment_vat_rate(item_name, payload.issue_date)
    issue_id = insert_equipment_issue_record(
        conn,
        {
            "personnel_id": payload.personnel_id,
            "issue_date": payload.issue_date,
            "item_name": item_name,
            "quantity": int(payload.quantity),
            "unit_cost": float(payload.unit_cost),
            "unit_sale_price": float(payload.unit_sale_price),
            "vat_rate": vat_rate,
            "installment_count": installment_count,
            "sale_type": sale_type,
            "notes": str(payload.notes or "").strip(),
        },
    )
    total_sale_amount = float(payload.quantity) * float(payload.unit_sale_price)
    _rebuild_issue_installments(
        conn,
        issue_id=issue_id,
        personnel_id=payload.personnel_id,
        issue_date=payload.issue_date,
        item_name=item_name,
        total_sale_amount=total_sale_amount,
        installment_count=installment_count,
        sale_type=sale_type,
    )
    conn.commit()
    if _generates_installments(sale_type, total_sale_amount, installment_count):
        message = f"Zimmet kaydi olusturuldu. {installment_count} taksit planlandi."
    else:
        message = "Zimmet kaydi olusturuldu."
    return EquipmentIssueCreateResponse(
        equipment_issue_id=issue_id,
        message=message,
    )


def update_equipment_issue_entry(
    conn: psycopg.Connection,
    *,
    issue_id: int,
    payload: EquipmentIssueUpdateRequest,
) -> EquipmentIssueUpdateResponse:
    existing = fetch_equipment_issue_by_id(conn, issue_id)
    if existing is None:
        raise LookupError("Zimmet kaydi bulunamadi.")
    if str(existing.get("auto_source_key") or "").strip():
        raise ValueError("Otomatik olusan zimmet kayitlari v2 ekranindan guncellenemez.")
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmali.")
    if payload.unit_cost < 0 or payload.unit_sale_price < 0:
        raise ValueError("Maliyet ve satis tutari negatif olamaz.")

    item_name = _normalize_issue_item(payload.item_name)
    sale_type = _normalize_sale_type(payload.sale_type)
    installment_count = _normalize_installment_count(sale_type, payload.installment_count)
    vat_rate = _get_equipment_vat_rate(item_name, payload.issue_date)
    update_equipment_issue_record(
        conn,
        issue_id,
        {
            "personnel_id": payload.personnel_id,
            "issue_date": payload.issue_date,
            "item_name": item_name,
            "quantity": int(payload.quantity),
            "unit_cost": float(payload.unit_cost),
            "unit_sale_price": float(payload.unit_sale_price),
            "vat_rate": vat_rate,
            "installment_count": installment_count,
            "sale_type": sale_type,
            "notes": str(payload.notes or "").strip(),
        },
    )
    total_sale_amount = float(payload.quantity) * float(payload.unit_sale_price)
    _rebuild_issue_installments(
        conn,
        issue_id=issue_id,
        personnel_id=payload.personnel_id,
        issue_date=payload.issue_date,
        item_name=item_name,
        total_sale_amount=total_sale_amount,
        installment_count=installment_count,
        sale_type=sale_type,
    )
    conn.commit()
    return EquipmentIssueUpdateResponse(
        equipment_issue_id=issue_id,
        message="Zimmet kaydi guncellendi.",
    )


def delete_equipment_issue_entry(
    conn: psycopg.Connection,
    *,
    issue_id: int,
) -> EquipmentIssueDeleteResponse:
    existing = fetch_equipment_issue_by_id(conn, issue_id)
    if existing is None:
        raise LookupError("Zimmet kaydi bulunamadi.")
    if str(existing.get("auto_source_key") or "").strip():
        raise ValueError("Otomatik olusan zimmet kayitlari v2 ekranindan silinemez.")
    delete_equipment_issue_installments(conn, issue_id)
    delete_equipment_issue_record(conn, issue_id)
    conn.commit()
    return EquipmentIssueDeleteResponse(
        equipment_issue_id=issue_id,
        message="Zimmet kaydi ve bagli taksitler silindi.",
    )


def build_box_return_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    personnel_id: int | None = None,
    search: str | None = None,
) -> BoxReturnsManagementResponse:
    return BoxReturnsManagementResponse(
        total_entries=count_box_return_management_records(
            conn,
            personnel_id=personnel_id,
            search=search,
        ),
        entries=[
            _build_box_return_entry(row)
            for row in fetch_box_return_management_records(
                conn,
                limit=limit,
                personnel_id=personnel_id,
                search=search,
            )
        ],
    )


def build_box_return_detail(
    conn: psycopg.Connection,
    *,
    box_return_id: int,
) -> BoxReturnDetailResponse:
    row = fetch_box_return_by_id(conn, box_return_id)
    if row is None:
        raise LookupError("Box geri alim kaydi bulunamadi.")
    return BoxReturnDetailResponse(entry=_build_box_return_entry(row))


def create_box_return_entry(
    conn: psycopg.Connection,
    *,
    payload: BoxReturnCreateRequest,
) -> BoxReturnCreateResponse:
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmali.")
    if payload.payout_amount < 0:
        raise ValueError("Geri odeme tutari negatif olamaz.")

    condition_status = _normalize_return_condition(payload.condition_status)
    waived = 1 if condition_status == "Parasını istemedi" else 0
    box_return_id = insert_box_return_record(
        conn,
        {
            "personnel_id": payload.personnel_id,
            "return_date": payload.return_date,
            "quantity": int(payload.quantity),
            "condition_status": condition_status,
            "payout_amount": float(payload.payout_amount),
            "waived": waived,
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return BoxReturnCreateResponse(
        box_return_id=box_return_id,
        message="Box geri alim kaydi olusturuldu.",
    )


def update_box_return_entry(
    conn: psycopg.Connection,
    *,
    box_return_id: int,
    payload: BoxReturnUpdateRequest,
) -> BoxReturnUpdateResponse:
    existing = fetch_box_return_by_id(conn, box_return_id)
    if existing is None:
        raise LookupError("Box geri alim kaydi bulunamadi.")
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmali.")
    if payload.payout_amount < 0:
        raise ValueError("Geri odeme tutari negatif olamaz.")

    condition_status = _normalize_return_condition(payload.condition_status)
    waived = 1 if condition_status == "Parasını istemedi" else 0
    update_box_return_record(
        conn,
        box_return_id,
        {
            "personnel_id": payload.personnel_id,
            "return_date": payload.return_date,
            "quantity": int(payload.quantity),
            "condition_status": condition_status,
            "payout_amount": float(payload.payout_amount),
            "waived": waived,
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return BoxReturnUpdateResponse(
        box_return_id=box_return_id,
        message="Box geri alim kaydi guncellendi.",
    )


def delete_box_return_entry(
    conn: psycopg.Connection,
    *,
    box_return_id: int,
) -> BoxReturnDeleteResponse:
    existing = fetch_box_return_by_id(conn, box_return_id)
    if existing is None:
        raise LookupError("Box geri alim kaydi bulunamadi.")
    delete_box_return_record(conn, box_return_id)
    conn.commit()
    return BoxReturnDeleteResponse(
        box_return_id=box_return_id,
        message="Box geri alim kaydi silindi.",
    )
