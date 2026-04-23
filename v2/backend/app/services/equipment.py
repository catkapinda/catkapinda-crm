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
from app.services.motor_rental import (
    MOTOR_PURCHASE_DEDUCTION_TYPE,
    MOTOR_RENTAL_DEDUCTION_TYPE,
    build_company_motor_purchase_plan,
    build_company_motor_rental_plan,
    is_motor_purchase_deduction_type,
    is_motor_rental_deduction_type,
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
    EquipmentIssueBulkDeleteRequest,
    EquipmentIssueBulkDeleteResponse,
    EquipmentIssueBulkUpdateRequest,
    EquipmentIssueBulkUpdateResponse,
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

VAT_RATE_DEFAULT = 0.0
EQUIPMENT_REDUCED_VAT_START_DATE = date(2026, 3, 1)
EQUIPMENT_VAT_RATE_AFTER_REDUCTION = 0.0
EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS = {"Kask", "Telefon Tutacağı", "Motor Kirası", "Motor Satın Alım"}
AUTO_MOTOR_RENTAL_DEDUCTION = 13000.0
AUTO_MOTOR_PURCHASE_TOTAL_PRICE = 135000.0
AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = 12
AUTO_EQUIPMENT_INSTALLMENT_COUNT = 2
MOTOR_PAYMENT_DEDUCTION_TYPES_SQL = (
    "('Motor Kirası', 'Motor Kirasi', 'Motor Satış Taksiti', 'Motor Satis Taksiti', "
    "'Motor Satın Alım', 'Motor Satin Alim')"
)
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


def _coerce_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value or date.today().isoformat()))


def _month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def _month_key_sql(column: str) -> str:
    return f"substr(COALESCE(CAST({column} AS TEXT), ''), 1, 7)"


def _fetch_motor_payment_personnel_rows(conn: psycopg.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT
            id,
            COALESCE(full_name, '-') AS personnel_label,
            COALESCE(status, '') AS status,
            start_date,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, 'Hayır') AS motor_rental,
            COALESCE(motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            motor_purchase_start_date,
            COALESCE(motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction
        FROM personnel
        WHERE COALESCE(status, '') = 'Aktif'
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_existing_motor_payment_amounts(conn: psycopg.Connection, month: str) -> dict[int, dict[str, float]]:
    rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(deduction_type, '') AS deduction_type,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') IN {MOTOR_PAYMENT_DEDUCTION_TYPES_SQL}
        GROUP BY personnel_id, COALESCE(deduction_type, '')
        """,
        (month,),
    ).fetchall()
    existing: dict[int, dict[str, float]] = {}
    for row in rows:
        person_id = int(row["personnel_id"])
        bucket = existing.setdefault(person_id, {"rental": 0.0, "purchase": 0.0})
        deduction_type = str(row["deduction_type"] or "")
        amount = float(row["total_amount"] or 0)
        if is_motor_rental_deduction_type(deduction_type):
            bucket["rental"] += amount
        elif is_motor_purchase_deduction_type(deduction_type):
            bucket["purchase"] += amount
    return existing


def _build_virtual_motor_payment_installments(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> list[EquipmentInstallmentEntry]:
    month = _month_key(reference_date)
    existing_amounts = _fetch_existing_motor_payment_amounts(conn, month)
    entries: list[EquipmentInstallmentEntry] = []
    for row in _fetch_motor_payment_personnel_rows(conn):
        person_id = int(row["id"])
        personnel_label = str(row.get("personnel_label") or "-")
        existing = existing_amounts.get(person_id, {})
        rental_plan = build_company_motor_rental_plan(
            row,
            month,
            existing_amount=existing.get("rental", 0.0),
        )
        if rental_plan is not None:
            entries.append(
                EquipmentInstallmentEntry(
                    deduction_date=rental_plan.deduction_date,
                    personnel_label=personnel_label,
                    deduction_type=MOTOR_RENTAL_DEDUCTION_TYPE,
                    amount=rental_plan.amount,
                    notes=rental_plan.notes,
                    auto_source_key=rental_plan.auto_source_key,
                )
            )
        purchase_plan = build_company_motor_purchase_plan(
            row,
            month,
            existing_amount=existing.get("purchase", 0.0),
        )
        if purchase_plan is not None:
            entries.append(
                EquipmentInstallmentEntry(
                    deduction_date=purchase_plan.deduction_date,
                    personnel_label=personnel_label,
                    deduction_type=MOTOR_PURCHASE_DEDUCTION_TYPE,
                    amount=purchase_plan.amount,
                    notes=purchase_plan.notes,
                    auto_source_key=purchase_plan.auto_source_key,
                )
            )
    return entries


def _sort_installment_entries(entries: list[EquipmentInstallmentEntry]) -> list[EquipmentInstallmentEntry]:
    return sorted(entries, key=lambda entry: (entry.deduction_date, entry.personnel_label), reverse=True)


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
        vat_rate=VAT_RATE_DEFAULT,
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


def _build_issue_label(row: dict[str, object]) -> str:
    issue_date = str(row.get("issue_date") or "-")
    personnel_label = str(row.get("personnel_label") or "-")
    item_name = str(row.get("item_name") or "-")
    issue_id = int(row.get("id") or 0)
    return f"{issue_date} | {personnel_label} | {item_name} | ID:{issue_id}"


def _normalize_issue_ids(issue_ids: list[int]) -> list[int]:
    normalized: list[int] = []
    seen: set[int] = set()
    for raw_value in issue_ids:
        issue_id = int(raw_value or 0)
        if issue_id <= 0 or issue_id in seen:
            continue
        seen.add(issue_id)
        normalized.append(issue_id)
    return normalized


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
    real_installments = [
        EquipmentInstallmentEntry(
            deduction_date=row["deduction_date"],
            personnel_label=str(row.get("personnel_label") or "-"),
            deduction_type=str(row.get("deduction_type") or ""),
            amount=float(row.get("amount") or 0),
            notes=str(row.get("notes") or ""),
            auto_source_key=str(row.get("auto_source_key") or ""),
        )
        for row in fetch_equipment_installments(conn, limit=limit)
    ]
    virtual_installments = _build_virtual_motor_payment_installments(conn, reference_date=reference_date)
    summary_values["installment_rows"] += len(virtual_installments)
    return EquipmentDashboardResponse(
        module="equipment",
        status="active",
        summary=EquipmentSummary(**summary_values),
        recent_issues=[_build_issue_entry(row) for row in fetch_recent_equipment_issues(conn, limit=limit)],
        recent_box_returns=[_build_box_return_entry(row) for row in fetch_recent_box_returns(conn, limit=limit)],
        installment_entries=_sort_installment_entries(real_installments + virtual_installments)[:limit],
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
        raise LookupError("Zimmet kaydı bulunamadı.")
    return EquipmentIssueDetailResponse(entry=_build_issue_entry(row))


def create_equipment_issue_entry(
    conn: psycopg.Connection,
    *,
    payload: EquipmentIssueCreateRequest,
) -> EquipmentIssueCreateResponse:
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmalı.")
    if payload.unit_cost < 0 or payload.unit_sale_price < 0:
        raise ValueError("Maliyet ve satış tutarı negatif olamaz.")

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
        message = f"Zimmet kaydı oluşturuldu. {installment_count} taksit planlandı."
    else:
        message = "Zimmet kaydı oluşturuldu."
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
        raise LookupError("Zimmet kaydı bulunamadı.")
    if str(existing.get("auto_source_key") or "").strip():
        raise ValueError("Otomatik oluşan zimmet kayıtları v2 ekranından güncellenemez.")
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmalı.")
    if payload.unit_cost < 0 or payload.unit_sale_price < 0:
        raise ValueError("Maliyet ve satış tutarı negatif olamaz.")

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
        message="Zimmet kaydı güncellendi.",
    )


def bulk_update_equipment_issue_entries(
    conn: psycopg.Connection,
    *,
    payload: EquipmentIssueBulkUpdateRequest,
) -> EquipmentIssueBulkUpdateResponse:
    issue_ids = _normalize_issue_ids(payload.issue_ids)
    if not issue_ids:
        raise ValueError("Önce en az bir zimmet kaydı seçmelisin.")
    if (
        payload.issue_date is None
        and payload.unit_cost is None
        and payload.unit_sale_price is None
        and payload.installment_count is None
        and payload.sale_type is None
        and not str(payload.note_append_text or "").strip()
    ):
        raise ValueError("Toplu güncelleme için en az bir alan seçmeli veya not eklemelisin.")
    if payload.unit_cost is not None and payload.unit_cost < 0:
        raise ValueError("Maliyet tutarı negatif olamaz.")
    if payload.unit_sale_price is not None and payload.unit_sale_price < 0:
        raise ValueError("Satış tutarı negatif olamaz.")
    if payload.installment_count is not None and payload.installment_count <= 0:
        raise ValueError("Taksit sayısı en az 1 olmalı.")

    existing_rows: list[dict[str, object]] = []
    blocked_labels: list[str] = []
    for issue_id in issue_ids:
        row = fetch_equipment_issue_by_id(conn, issue_id)
        if row is None:
            raise LookupError("Zimmet kaydı bulunamadı.")
        existing_rows.append(row)
        if str(row.get("auto_source_key") or "").strip():
            blocked_labels.append(_build_issue_label(row))
    if blocked_labels:
        raise ValueError(
            "Otomatik oluşan zimmet kayıtları toplu güncellenemez: "
            + ", ".join(blocked_labels)
            + "."
        )

    note_append_text = str(payload.note_append_text or "").strip()
    for row in existing_rows:
        issue_id = int(row["id"])
        issue_date = payload.issue_date or _coerce_date(row["issue_date"])
        item_name = _normalize_issue_item(str(row.get("item_name") or ISSUE_ITEMS[0]))
        sale_type = _normalize_sale_type(payload.sale_type or str(row.get("sale_type") or SALE_TYPE_OPTIONS[0]))
        installment_seed = (
            payload.installment_count
            if payload.installment_count is not None
            else int(row.get("installment_count") or 1)
        )
        installment_count = _normalize_installment_count(sale_type, installment_seed)
        quantity = int(row.get("quantity") or 0)
        unit_cost = float(payload.unit_cost if payload.unit_cost is not None else row.get("unit_cost") or 0)
        unit_sale_price = float(
            payload.unit_sale_price if payload.unit_sale_price is not None else row.get("unit_sale_price") or 0
        )
        notes = str(row.get("notes") or "").strip()
        if note_append_text:
            notes = f"{notes}\n{note_append_text}".strip() if notes else note_append_text
        vat_rate = VAT_RATE_DEFAULT

        update_equipment_issue_record(
            conn,
            issue_id,
            {
                "personnel_id": int(row.get("personnel_id") or 0),
                "issue_date": issue_date,
                "item_name": item_name,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "unit_sale_price": unit_sale_price,
                "vat_rate": vat_rate,
                "installment_count": installment_count,
                "sale_type": sale_type,
                "notes": notes,
            },
        )
        total_sale_amount = float(quantity) * unit_sale_price
        _rebuild_issue_installments(
            conn,
            issue_id=issue_id,
            personnel_id=int(row.get("personnel_id") or 0),
            issue_date=issue_date,
            item_name=item_name,
            total_sale_amount=total_sale_amount,
            installment_count=installment_count,
            sale_type=sale_type,
        )

    conn.commit()
    return EquipmentIssueBulkUpdateResponse(
        updated_count=len(existing_rows),
        message=f"{len(existing_rows)} zimmet kaydı güncellendi.",
    )


def delete_equipment_issue_entry(
    conn: psycopg.Connection,
    *,
    issue_id: int,
) -> EquipmentIssueDeleteResponse:
    existing = fetch_equipment_issue_by_id(conn, issue_id)
    if existing is None:
        raise LookupError("Zimmet kaydı bulunamadı.")
    if str(existing.get("auto_source_key") or "").strip():
        raise ValueError("Otomatik oluşan zimmet kayıtları v2 ekranından silinemez.")
    delete_equipment_issue_installments(conn, issue_id)
    delete_equipment_issue_record(conn, issue_id)
    conn.commit()
    return EquipmentIssueDeleteResponse(
        equipment_issue_id=issue_id,
        message="Zimmet kaydı ve bağlı taksitler silindi.",
    )


def bulk_delete_equipment_issue_entries(
    conn: psycopg.Connection,
    *,
    payload: EquipmentIssueBulkDeleteRequest,
) -> EquipmentIssueBulkDeleteResponse:
    issue_ids = _normalize_issue_ids(payload.issue_ids)
    if not issue_ids:
        raise ValueError("Önce en az bir zimmet kaydı seçmelisin.")

    existing_rows: list[dict[str, object]] = []
    blocked_labels: list[str] = []
    for issue_id in issue_ids:
        row = fetch_equipment_issue_by_id(conn, issue_id)
        if row is None:
            raise LookupError("Zimmet kaydı bulunamadı.")
        existing_rows.append(row)
        if str(row.get("auto_source_key") or "").strip():
            blocked_labels.append(_build_issue_label(row))
    if blocked_labels:
        raise ValueError(
            "Otomatik oluşan zimmet kayıtları toplu silinemez: "
            + ", ".join(blocked_labels)
            + "."
        )

    for row in existing_rows:
        issue_id = int(row["id"])
        delete_equipment_issue_installments(conn, issue_id)
        delete_equipment_issue_record(conn, issue_id)
    conn.commit()
    return EquipmentIssueBulkDeleteResponse(
        deleted_count=len(existing_rows),
        message=f"{len(existing_rows)} zimmet kaydı ve bağlı taksitler silindi.",
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
        raise LookupError("Box geri alım kaydı bulunamadı.")
    return BoxReturnDetailResponse(entry=_build_box_return_entry(row))


def create_box_return_entry(
    conn: psycopg.Connection,
    *,
    payload: BoxReturnCreateRequest,
) -> BoxReturnCreateResponse:
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmalı.")
    if payload.payout_amount < 0:
        raise ValueError("Geri ödeme tutarı negatif olamaz.")

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
        message="Box geri alım kaydı oluşturuldu.",
    )


def update_box_return_entry(
    conn: psycopg.Connection,
    *,
    box_return_id: int,
    payload: BoxReturnUpdateRequest,
) -> BoxReturnUpdateResponse:
    existing = fetch_box_return_by_id(conn, box_return_id)
    if existing is None:
        raise LookupError("Box geri alım kaydı bulunamadı.")
    if payload.quantity <= 0:
        raise ValueError("Adet en az 1 olmalı.")
    if payload.payout_amount < 0:
        raise ValueError("Geri ödeme tutarı negatif olamaz.")

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
        message="Box geri alım kaydı güncellendi.",
    )


def delete_box_return_entry(
    conn: psycopg.Connection,
    *,
    box_return_id: int,
) -> BoxReturnDeleteResponse:
    existing = fetch_box_return_by_id(conn, box_return_id)
    if existing is None:
        raise LookupError("Box geri alım kaydı bulunamadı.")
    delete_box_return_record(conn, box_return_id)
    conn.commit()
    return BoxReturnDeleteResponse(
        box_return_id=box_return_id,
        message="Box geri alım kaydı silindi.",
    )
