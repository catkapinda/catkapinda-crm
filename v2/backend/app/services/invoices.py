from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

from app.repositories.invoices import (
    build_collection_update_values,
    build_collection_values,
    fetch_restaurant_collection_row,
    fetch_restaurant_collection_rows,
    fetch_restaurant_id_label_map,
    insert_restaurant_collection_row,
    restaurant_exists,
    update_restaurant_collection_row,
)
from app.schemas.invoices import (
    InvoiceCollectionEntry,
    InvoiceCollectionRecord,
    InvoiceCollectionSummary,
    InvoiceCollectionUpsertRequest,
    InvoiceCollectionUpsertResponse,
    InvoiceDashboardEntry,
    InvoicesDashboardResponse,
)
from app.schemas.reports import ReportInvoiceDrilldownEntry, ReportsSummary
from app.services.reports import _build_local_invoice_drilldown_entries, _month_key_sql, build_reports_dashboard

_DEFAULT_COLLECTION_STATUS = "Bekliyor"
_COLLECTION_STATUS_OPTIONS = (
    "Bekliyor",
    "Planlandı",
    "Kısmi Tahsilat",
    "Tahsil Edildi",
    "Gecikti",
)
_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalize_month(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not _MONTH_PATTERN.fullmatch(normalized):
        raise ValueError("Tahsilat ayi YYYY-AA formatinda olmali.")
    return normalized


def _normalize_status(value: str | None) -> str:
    normalized = str(value or "").strip() or _DEFAULT_COLLECTION_STATUS
    if normalized not in _COLLECTION_STATUS_OPTIONS:
        raise ValueError("Tahsilat durumu tanimli degil.")
    return normalized


def _parse_optional_date(value: str | None) -> date | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Tarih alanlari YYYY-AA-GG formatinda olmali.") from exc


def _serialize_optional_date(value: object) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    normalized = str(value).strip()
    return normalized or None


def _build_collection_summary(entries: list[InvoiceCollectionEntry]) -> InvoiceCollectionSummary:
    today = date.today()
    overdue_entries = [
        entry
        for entry in entries
        if entry.remaining_amount > 0
        and entry.due_date
        and entry.due_date < today.isoformat()
        and entry.status != "Tahsil Edildi"
    ]
    return InvoiceCollectionSummary(
        total_collected_amount=sum(entry.collected_amount for entry in entries),
        total_open_amount=sum(entry.remaining_amount for entry in entries),
        overdue_amount=sum(entry.remaining_amount for entry in overdue_entries),
        tracked_restaurant_count=len(entries),
        collected_restaurant_count=sum(1 for entry in entries if entry.status == "Tahsil Edildi"),
        overdue_restaurant_count=len(overdue_entries),
        due_defined_restaurant_count=sum(1 for entry in entries if entry.due_date),
    )


def _build_invoice_drilldown_fallback(
    conn: Any,
    *,
    selected_month: str | None,
) -> list[ReportInvoiceDrilldownEntry]:
    if not selected_month:
        return []

    try:
        rows = conn.execute(
            f"""
            SELECT
                d.id,
                d.entry_date,
                d.restaurant_id,
                COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
                COALESCE(r.pricing_model, '-') AS pricing_model,
                COALESCE(r.hourly_rate, 0) AS hourly_rate,
                COALESCE(r.package_rate, 0) AS package_rate,
                COALESCE(r.package_threshold, 0) AS package_threshold,
                COALESCE(r.package_rate_low, 0) AS package_rate_low,
                COALESCE(r.package_rate_high, 0) AS package_rate_high,
                COALESCE(r.fixed_monthly_fee, 0) AS fixed_monthly_fee,
                COALESCE(r.vat_rate, 20) AS vat_rate,
                COALESCE(d.worked_hours, 0) AS worked_hours,
                COALESCE(d.package_count, 0) AS package_count,
                COALESCE(d.monthly_invoice_amount, 0) AS monthly_invoice_amount,
                COALESCE(p.full_name, '-') AS personnel,
                COALESCE(p.role, '-') AS role
            FROM daily_entries d
            JOIN restaurants r ON r.id = d.restaurant_id
            LEFT JOIN personnel p ON p.id = COALESCE(d.actual_personnel_id, d.planned_personnel_id)
            WHERE {_month_key_sql('d.entry_date')} = %s
            ORDER BY restaurant, personnel, d.entry_date, d.id
            """,
            (selected_month,),
        ).fetchall()
    except Exception:
        return []

    return _build_local_invoice_drilldown_entries([dict(row) for row in rows])


def _merge_invoice_drilldown_entries(
    primary_entries: list[ReportInvoiceDrilldownEntry],
    fallback_entries: list[ReportInvoiceDrilldownEntry],
) -> list[ReportInvoiceDrilldownEntry]:
    merged = list(primary_entries)
    seen_keys = {
        (
            entry.restaurant,
            entry.personnel,
            entry.role,
            round(entry.total_hours, 2),
            round(entry.total_packages, 2),
        )
        for entry in merged
    }
    for entry in fallback_entries:
        key = (
            entry.restaurant,
            entry.personnel,
            entry.role,
            round(entry.total_hours, 2),
            round(entry.total_packages, 2),
        )
        if key in seen_keys:
            continue
        merged.append(entry)
        seen_keys.add(key)

    merged.sort(
        key=lambda entry: (
            entry.restaurant,
            -entry.total_packages,
            -entry.total_hours,
            entry.personnel,
        )
    )
    return merged


def build_invoices_dashboard(
    conn: Any,
    *,
    selected_month: str | None = None,
    limit: int = 200,
) -> InvoicesDashboardResponse:
    reports_payload = build_reports_dashboard(conn, selected_month=selected_month, limit=limit)
    if not reports_payload.month_options or reports_payload.selected_month is None:
        return InvoicesDashboardResponse(
            module="invoices",
            status="inactive",
            month_options=[],
            selected_month=None,
            summary=None,
            invoice_entries=[],
            profit_entries=[],
            distribution_entries=[],
            invoice_drilldown_entries=[],
            collection_entries=[],
            collection_summary=_build_collection_summary([]),
            collection_status_options=list(_COLLECTION_STATUS_OPTIONS),
        )

    restaurant_id_by_label = fetch_restaurant_id_label_map(conn)
    collection_rows = fetch_restaurant_collection_rows(
        conn,
        collection_month=reports_payload.selected_month,
    )
    collection_by_restaurant_id = {
        int(row["restaurant_id"]): row
        for row in collection_rows
        if row.get("restaurant_id") is not None
    }
    profit_by_restaurant = {
        row.restaurant: row
        for row in reports_payload.profit_entries
    }

    invoice_entries: list[InvoiceDashboardEntry] = []
    collection_entries: list[InvoiceCollectionEntry] = []
    for row in reports_payload.invoice_entries:
        restaurant_id = restaurant_id_by_label.get(row.restaurant)
        invoice_entries.append(
            InvoiceDashboardEntry(
                restaurant_id=restaurant_id,
                restaurant=row.restaurant,
                pricing_model=row.pricing_model,
                total_hours=row.total_hours,
                total_packages=row.total_packages,
                net_invoice=row.net_invoice,
                gross_invoice=row.gross_invoice,
            )
        )
        profit_row = profit_by_restaurant.get(row.restaurant)
        saved_collection = collection_by_restaurant_id.get(int(restaurant_id or 0))
        collected_amount = _safe_float(saved_collection.get("collected_amount")) if saved_collection else 0.0
        remaining_amount = max(row.gross_invoice - collected_amount, 0.0)
        collection_entries.append(
            InvoiceCollectionEntry(
                restaurant_id=int(restaurant_id or 0),
                restaurant=row.restaurant,
                pricing_model=row.pricing_model,
                total_hours=row.total_hours,
                total_packages=row.total_packages,
                net_invoice=row.net_invoice,
                gross_invoice=row.gross_invoice,
                direct_personnel_cost=profit_row.direct_personnel_cost if profit_row else 0.0,
                gross_profit=profit_row.gross_profit if profit_row else row.gross_invoice,
                status=str(saved_collection.get("status") or _DEFAULT_COLLECTION_STATUS)
                if saved_collection
                else _DEFAULT_COLLECTION_STATUS,
                due_date=_serialize_optional_date(saved_collection.get("due_date")) if saved_collection else None,
                collected_amount=collected_amount,
                remaining_amount=remaining_amount,
                payment_date=_serialize_optional_date(saved_collection.get("payment_date")) if saved_collection else None,
                last_contact_date=_serialize_optional_date(saved_collection.get("last_contact_date"))
                if saved_collection
                else None,
                responsible_name=str(saved_collection.get("responsible_name") or "") if saved_collection else "",
                note=str(saved_collection.get("note") or "") if saved_collection else "",
            )
        )

    invoice_drilldown_entries = _merge_invoice_drilldown_entries(
        reports_payload.invoice_drilldown_entries,
        _build_invoice_drilldown_fallback(conn, selected_month=reports_payload.selected_month),
    )

    return InvoicesDashboardResponse(
        module="invoices",
        status="active",
        month_options=reports_payload.month_options,
        selected_month=reports_payload.selected_month,
        summary=ReportsSummary(**reports_payload.summary.model_dump()) if reports_payload.summary else None,
        invoice_entries=invoice_entries,
        profit_entries=reports_payload.profit_entries,
        distribution_entries=reports_payload.distribution_entries,
        invoice_drilldown_entries=invoice_drilldown_entries,
        collection_entries=collection_entries,
        collection_summary=_build_collection_summary(collection_entries),
        collection_status_options=list(_COLLECTION_STATUS_OPTIONS),
    )


def upsert_invoice_collection(
    conn: Any,
    *,
    payload: InvoiceCollectionUpsertRequest,
) -> InvoiceCollectionUpsertResponse:
    restaurant_id = int(payload.restaurant_id)
    if restaurant_id <= 0 or not restaurant_exists(conn, restaurant_id):
        raise LookupError("Tahsilat kaydi icin restoran bulunamadi.")

    collection_month = _normalize_month(payload.collection_month)
    status = _normalize_status(payload.status)
    due_date = _parse_optional_date(payload.due_date)
    payment_date = _parse_optional_date(payload.payment_date)
    last_contact_date = _parse_optional_date(payload.last_contact_date)
    collected_amount = max(_safe_float(payload.collected_amount), 0.0)
    responsible_name = str(payload.responsible_name or "").strip()
    note = str(payload.note or "").strip()

    existing = fetch_restaurant_collection_row(
        conn,
        restaurant_id=restaurant_id,
        collection_month=collection_month,
    )
    if existing:
        update_values = build_collection_update_values(
            status=status,
            due_date=due_date,
            collected_amount=collected_amount,
            payment_date=payment_date,
            last_contact_date=last_contact_date,
            responsible_name=responsible_name,
            note=note,
        )
        update_restaurant_collection_row(conn, int(existing["id"]), update_values)
        collection_id = int(existing["id"])
        message = "Tahsilat kaydi guncellendi."
    else:
        insert_values = build_collection_values(
            restaurant_id=restaurant_id,
            collection_month=collection_month,
            status=status,
            due_date=due_date,
            collected_amount=collected_amount,
            payment_date=payment_date,
            last_contact_date=last_contact_date,
            responsible_name=responsible_name,
            note=note,
        )
        collection_id = insert_restaurant_collection_row(conn, insert_values)
        message = "Tahsilat kaydi olusturuldu."

    conn.commit()
    saved = fetch_restaurant_collection_row(
        conn,
        restaurant_id=restaurant_id,
        collection_month=collection_month,
    )
    if saved is None:
        raise LookupError("Tahsilat kaydi kaydedildi ancak tekrar okunamadi.")

    return InvoiceCollectionUpsertResponse(
        message=message,
        record=InvoiceCollectionRecord(
            id=collection_id,
            restaurant_id=restaurant_id,
            collection_month=collection_month,
            status=str(saved.get("status") or _DEFAULT_COLLECTION_STATUS),
            due_date=_serialize_optional_date(saved.get("due_date")),
            collected_amount=_safe_float(saved.get("collected_amount")),
            payment_date=_serialize_optional_date(saved.get("payment_date")),
            last_contact_date=_serialize_optional_date(saved.get("last_contact_date")),
            responsible_name=str(saved.get("responsible_name") or ""),
            note=str(saved.get("note") or ""),
        ),
    )
