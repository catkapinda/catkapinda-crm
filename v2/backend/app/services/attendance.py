from __future__ import annotations

from datetime import date

import psycopg

from app.repositories.attendance import (
    count_attendance_management_entries,
    delete_attendance_entry,
    delete_attendance_entries,
    fetch_attendance_entry_by_id,
    fetch_attendance_entry_ids,
    fetch_attendance_management_entry_ids,
    fetch_attendance_management_entries,
    fetch_attendance_people,
    fetch_attendance_restaurants,
    fetch_attendance_summary,
    fetch_recent_attendance_entries,
    insert_attendance_entry,
    update_attendance_entry,
)
from app.schemas.attendance import (
    AttendanceCreateRequest,
    AttendanceCreateResponse,
    AttendanceBulkDeleteRequest,
    AttendanceBulkDeleteResponse,
    AttendanceDashboardResponse,
    AttendanceDeleteResponse,
    AttendanceEntryDetailResponse,
    AttendanceEntrySummary,
    AttendanceFilteredDeleteRequest,
    AttendanceFilteredDeleteResponse,
    AttendanceFormOptionsResponse,
    AttendanceManagementEntry,
    AttendanceManagementResponse,
    AttendanceModuleStatus,
    AttendancePersonOption,
    AttendanceRestaurantOption,
    AttendanceSummary,
    AttendanceUpdateRequest,
    AttendanceUpdateResponse,
)

ATTENDANCE_ENTRY_MODE_OPTIONS = [
    "Restoran Kuryesi",
    "Joker",
    "Destek",
    "Haftalık İzin",
]
ABSENCE_REASON_OPTIONS = ["İzin", "Raporlu", "İhbarsız Çıkış", "Gelmedi", "Diğer"]
ENTRY_MODE_ALIASES = {
    "Haftalik Buyume": "Haftalik Izin",
    "Haftalık Büyüme": "Haftalik Izin",
}
NON_WORKING_STATUSES = {"İzin", "Gelmedi", "Raporlu", "İhbarsız Çıkış"}


def _normalize_entry_mode(value: str) -> str:
    normalized = str(value or "").strip()
    return ENTRY_MODE_ALIASES.get(normalized, normalized or "Restoran Kuryesi")


def _normalize_bulk_entry_ids(entry_ids: list[int]) -> list[int]:
    normalized_ids: list[int] = []
    seen_ids: set[int] = set()
    for raw_entry_id in entry_ids:
        try:
            entry_id = int(raw_entry_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Toplu silme icin gecerli puantaj kayitlari secilmelidir.") from exc
        if entry_id <= 0:
            raise ValueError("Toplu silme icin gecerli puantaj kayitlari secilmelidir.")
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        normalized_ids.append(entry_id)
    if not normalized_ids:
        raise ValueError("Toplu silme icin en az bir puantaj kaydi secilmelidir.")
    return normalized_ids


def _resolve_filtered_delete_window(
    payload: AttendanceFilteredDeleteRequest,
) -> tuple[date, date, str]:
    if payload.date_from is None or payload.date_to is None:
        raise ValueError("Filtrelenmis toplu silme icin baslangic ve bitis tarihi secilmelidir.")
    if payload.date_from > payload.date_to:
        raise ValueError("Filtrelenmis toplu silmede baslangic tarihi bitis tarihinden buyuk olamaz.")
    normalized_search = str(payload.search or "").strip()
    return payload.date_from, payload.date_to, normalized_search


def _resolve_attendance_values(
    *,
    entry_mode: str,
    primary_person_id: int | None,
    replacement_person_id: int | None,
    absence_reason: str,
    worked_hours: float,
    package_count: float,
    monthly_invoice_amount: float,
    notes: str,
) -> dict[str, object]:
    normalized_mode = _normalize_entry_mode(entry_mode)
    notes_text = str(notes or "").strip()
    reason_text = str(absence_reason or "").strip()
    invoice_amount = float(monthly_invoice_amount or 0.0)

    if normalized_mode == "Restoran Kuryesi":
        if not primary_person_id:
            raise ValueError("Restoran kuryesi akışında çalışan personeli seçmelisin.")
        return {
            "planned_personnel_id": primary_person_id,
            "actual_personnel_id": primary_person_id,
            "status": "Normal",
            "worked_hours": float(worked_hours or 0),
            "package_count": float(package_count or 0),
            "monthly_invoice_amount": invoice_amount,
            "absence_reason": "",
            "coverage_type": "",
            "notes": notes_text,
        }

    if normalized_mode in {"Joker", "Destek"}:
        if not primary_person_id:
            raise ValueError("Yerine girişte normalde girecek personeli seçmelisin.")
        if not replacement_person_id:
            raise ValueError("Yerine girişte yerine giren personeli seçmelisin.")
        if primary_person_id == replacement_person_id:
            raise ValueError("Yerine girişte iki personel farklı olmalı.")
        if not reason_text:
            raise ValueError("Yerine girişte neden girmedi bilgisini seçmelisin.")
        return {
            "planned_personnel_id": primary_person_id,
            "actual_personnel_id": replacement_person_id,
            "status": "Normal",
            "worked_hours": float(worked_hours or 0),
            "package_count": float(package_count or 0),
            "monthly_invoice_amount": invoice_amount,
            "absence_reason": reason_text,
            "coverage_type": normalized_mode,
            "notes": notes_text,
        }

    if normalized_mode == "Haftalık İzin":
        if not primary_person_id:
            raise ValueError("Haftalık izinde çalışan personeli seçmelisin.")
        if not reason_text:
            raise ValueError("Haftalık izinde neden girmedi bilgisini seçmelisin.")
        return {
            "planned_personnel_id": primary_person_id,
            "actual_personnel_id": None,
            "status": reason_text if reason_text in NON_WORKING_STATUSES else "Gelmedi",
            "worked_hours": 0.0,
            "package_count": 0.0,
            "monthly_invoice_amount": invoice_amount,
            "absence_reason": reason_text,
            "coverage_type": "",
            "notes": notes_text,
        }

    raise ValueError("Gecersiz attendance akisi.")


def _build_management_entry(row: dict[str, object]) -> AttendanceManagementEntry:
    return AttendanceManagementEntry(
        id=int(row["id"]),
        entry_date=row["entry_date"],
        restaurant_id=int(row["restaurant_id"]),
        restaurant=str(row["restaurant"] or ""),
        entry_mode=_normalize_entry_mode(str(row["entry_mode"] or "")),
        primary_person_id=int(row["primary_person_id"]) if row["primary_person_id"] else None,
        primary_person_label=str(row["primary_person_label"] or "-"),
        replacement_person_id=int(row["replacement_person_id"]) if row["replacement_person_id"] else None,
        replacement_person_label=str(row["replacement_person_label"] or "-"),
        absence_reason=str(row["absence_reason"] or ""),
        coverage_type=str(row["coverage_type"] or ""),
        worked_hours=float(row["worked_hours"] or 0),
        package_count=float(row["package_count"] or 0),
        monthly_invoice_amount=float(row["monthly_invoice_amount"] or 0),
        notes=str(row["notes"] or ""),
    )


def build_attendance_status() -> AttendanceModuleStatus:
    return AttendanceModuleStatus(
        module="attendance",
        status="active",
        next_slice="daily-entry-dashboard",
    )


def build_attendance_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
    limit: int,
) -> AttendanceDashboardResponse:
    summary_values = fetch_attendance_summary(conn, reference_date=reference_date)
    recent_entry_rows = fetch_recent_attendance_entries(conn, limit=limit)
    return AttendanceDashboardResponse(
        module="attendance",
        status="active",
        summary=AttendanceSummary(
            total_entries=summary_values["total_count"],
            today_entries=summary_values["today_count"],
            month_entries=summary_values["month_count"],
            active_restaurants=summary_values["active_restaurants"],
        ),
        recent_entries=[
            AttendanceEntrySummary(
                id=int(row["id"]),
                entry_date=row["entry_date"],
                restaurant=str(row["restaurant"] or ""),
                employee_name=str(row["employee_name"] or "-"),
                entry_mode=_normalize_entry_mode(str(row["entry_mode"] or "")),
                absence_reason=str(row["absence_reason"] or ""),
                coverage_type=str(row["coverage_type"] or ""),
                worked_hours=float(row["worked_hours"] or 0),
                package_count=float(row["package_count"] or 0),
                monthly_invoice_amount=float(row["monthly_invoice_amount"] or 0),
                notes=str(row["notes"] or ""),
            )
            for row in recent_entry_rows
        ],
    )


def build_attendance_form_options(
    conn: psycopg.Connection,
    *,
    restaurant_id: int | None,
) -> AttendanceFormOptionsResponse:
    restaurants = fetch_attendance_restaurants(conn)
    selected_restaurant = None
    if restaurant_id is not None:
        selected_restaurant = next((row for row in restaurants if int(row["id"]) == restaurant_id), None)
    if selected_restaurant is None and restaurants:
        selected_restaurant = restaurants[0]
    selected_restaurant_id = int(selected_restaurant["id"]) if selected_restaurant else None
    selected_pricing_model = str(selected_restaurant["pricing_model"]) if selected_restaurant else None
    selected_fixed_monthly_fee = (
        float(selected_restaurant["fixed_monthly_fee"] or 0) if selected_restaurant else 0.0
    )
    people_rows = (
        fetch_attendance_people(conn, restaurant_id=selected_restaurant_id, include_all_active=False)
        if selected_restaurant_id is not None
        else []
    )
    return AttendanceFormOptionsResponse(
        restaurants=[
            AttendanceRestaurantOption(
                id=int(row["id"]),
                label=f"{str(row['brand']).strip()} - {str(row['branch']).strip()}",
                pricing_model=str(row["pricing_model"] or ""),
                fixed_monthly_fee=float(row["fixed_monthly_fee"] or 0),
            )
            for row in restaurants
        ],
        people=[
            AttendancePersonOption(
                id=int(row["id"]),
                label=f"{str(row['full_name']).strip()} ({str(row['role']).strip()})",
                role=str(row["role"] or ""),
            )
            for row in people_rows
        ],
        entry_modes=ATTENDANCE_ENTRY_MODE_OPTIONS,
        absence_reasons=ABSENCE_REASON_OPTIONS,
        selected_restaurant_id=selected_restaurant_id,
        selected_pricing_model=selected_pricing_model,
        selected_fixed_monthly_fee=selected_fixed_monthly_fee,
    )


def create_attendance_entry(
    conn: psycopg.Connection,
    *,
    payload: AttendanceCreateRequest,
) -> AttendanceCreateResponse:
    values = _resolve_attendance_values(
        entry_mode=payload.entry_mode,
        primary_person_id=payload.primary_person_id,
        replacement_person_id=payload.replacement_person_id,
        absence_reason=payload.absence_reason,
        worked_hours=payload.worked_hours,
        package_count=payload.package_count,
        monthly_invoice_amount=payload.monthly_invoice_amount,
        notes=payload.notes,
    )
    values["entry_date"] = payload.entry_date
    values["restaurant_id"] = payload.restaurant_id

    entry_id = insert_attendance_entry(conn, values)
    conn.commit()
    return AttendanceCreateResponse(
        entry_id=entry_id,
        message="Günlük puantaj kaydı oluşturuldu.",
    )


def build_attendance_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    restaurant_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AttendanceManagementResponse:
    rows = fetch_attendance_management_entries(
        conn,
        limit=limit,
        restaurant_id=restaurant_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    total_entries = count_attendance_management_entries(
        conn,
        restaurant_id=restaurant_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return AttendanceManagementResponse(
        total_entries=total_entries,
        entries=[_build_management_entry(row) for row in rows],
    )


def build_attendance_entry_detail(
    conn: psycopg.Connection,
    *,
    entry_id: int,
) -> AttendanceEntryDetailResponse:
    row = fetch_attendance_entry_by_id(conn, entry_id)
    if row is None:
        raise LookupError("Attendance kaydı bulunamadı.")
    return AttendanceEntryDetailResponse(entry=_build_management_entry(row))


def update_attendance_entry_record(
    conn: psycopg.Connection,
    *,
    entry_id: int,
    payload: AttendanceUpdateRequest,
) -> AttendanceUpdateResponse:
    existing_entry = fetch_attendance_entry_by_id(conn, entry_id)
    if existing_entry is None:
        raise LookupError("Attendance kaydı bulunamadı.")

    values = _resolve_attendance_values(
        entry_mode=payload.entry_mode,
        primary_person_id=payload.primary_person_id,
        replacement_person_id=payload.replacement_person_id,
        absence_reason=payload.absence_reason,
        worked_hours=payload.worked_hours,
        package_count=payload.package_count,
        monthly_invoice_amount=payload.monthly_invoice_amount,
        notes=payload.notes,
    )
    values["entry_date"] = payload.entry_date
    values["restaurant_id"] = payload.restaurant_id

    update_attendance_entry(conn, entry_id, values)
    conn.commit()
    return AttendanceUpdateResponse(
        entry_id=entry_id,
        message="Attendance kaydı güncellendi.",
    )


def delete_attendance_entry_record(
    conn: psycopg.Connection,
    *,
    entry_id: int,
) -> AttendanceDeleteResponse:
    existing_entry = fetch_attendance_entry_by_id(conn, entry_id)
    if existing_entry is None:
        raise LookupError("Attendance kaydı bulunamadı.")

    delete_attendance_entry(conn, entry_id)
    conn.commit()
    return AttendanceDeleteResponse(
        entry_id=entry_id,
        message="Attendance kaydı silindi.",
    )


def bulk_delete_attendance_entries(
    conn: psycopg.Connection,
    *,
    payload: AttendanceBulkDeleteRequest,
) -> AttendanceBulkDeleteResponse:
    entry_ids = _normalize_bulk_entry_ids(payload.entry_ids)
    existing_ids = fetch_attendance_entry_ids(conn, entry_ids=entry_ids)
    existing_id_set = set(existing_ids)
    missing_ids = [entry_id for entry_id in entry_ids if entry_id not in existing_id_set]
    if missing_ids:
        missing_labels = ", ".join(str(entry_id) for entry_id in missing_ids)
        raise LookupError(f"Secilen puantaj kayitlari bulunamadi: {missing_labels}.")

    deleted_ids = sorted(delete_attendance_entries(conn, entry_ids))
    if len(deleted_ids) != len(entry_ids):
        raise LookupError("Secilen puantaj kayitlarinin bir kismi silinemedi.")

    conn.commit()
    deleted_count = len(deleted_ids)
    return AttendanceBulkDeleteResponse(
        entry_ids=deleted_ids,
        deleted_count=deleted_count,
        message=f"{deleted_count} puantaj kaydi silindi.",
    )


def delete_attendance_entries_by_filter(
    conn: psycopg.Connection,
    *,
    payload: AttendanceFilteredDeleteRequest,
) -> AttendanceFilteredDeleteResponse:
    date_from, date_to, normalized_search = _resolve_filtered_delete_window(payload)
    entry_ids = fetch_attendance_management_entry_ids(
        conn,
        restaurant_id=payload.restaurant_id,
        search=normalized_search,
        date_from=date_from,
        date_to=date_to,
    )
    if not entry_ids:
        raise LookupError("Secilen filtrede silinecek puantaj kaydi bulunamadi.")

    deleted_ids = delete_attendance_entries(conn, entry_ids)
    deleted_count = len(deleted_ids)
    if deleted_count != len(entry_ids):
        raise LookupError("Filtrelenen puantaj kayitlarinin bir kismi silinemedi.")

    conn.commit()
    return AttendanceFilteredDeleteResponse(
        deleted_count=deleted_count,
        date_from=date_from,
        date_to=date_to,
        restaurant_id=payload.restaurant_id,
        search=normalized_search,
        message=f"Filtredeki {deleted_count} puantaj kaydi silindi.",
    )
