from __future__ import annotations

from datetime import date
import re

import psycopg

from app.core.auth_sync import sync_mobile_auth_user_for_personnel
from app.repositories.personnel import (
    close_active_plate_history_records,
    count_personnel_linked_box_returns,
    count_personnel_linked_daily_entries,
    count_personnel_linked_deductions,
    count_personnel_linked_equipment_issues,
    count_personnel_linked_plate_history,
    count_personnel_linked_role_history,
    count_personnel_linked_vehicle_history,
    count_active_catkapinda_vehicle_personnel,
    count_active_personnel_missing_plate,
    count_active_plate_history_records,
    count_personnel_management_records,
    count_plate_history_records_for_personnel,
    count_total_plate_history_records,
    delete_personnel_and_dependencies,
    fetch_active_plate_history_record,
    fetch_person_code_values,
    fetch_personnel_plate_baseline_candidates,
    fetch_personnel_plate_candidates,
    fetch_recent_plate_history_records,
    fetch_personnel_management_records,
    fetch_personnel_record_by_id,
    fetch_personnel_restaurants,
    fetch_personnel_summary,
    fetch_recent_personnel_records,
    insert_plate_history_record,
    insert_personnel_record,
    update_personnel_current_plate,
    update_personnel_status,
    update_personnel_record,
)
from app.schemas.personnel import (
    PersonnelCreateRequest,
    PersonnelCreateResponse,
    PersonnelDeleteResponse,
    PersonnelDashboardResponse,
    PersonnelDetailResponse,
    PersonnelFormOptionsResponse,
    PersonnelPlateCandidateEntry,
    PersonnelPlateCreateRequest,
    PersonnelPlateCreateResponse,
    PersonnelPlateHistoryEntry,
    PersonnelPlateSummary,
    PersonnelPlateWorkspaceResponse,
    PersonnelManagementEntry,
    PersonnelManagementResponse,
    PersonnelModuleStatus,
    PersonnelRestaurantOption,
    PersonnelStatusUpdateResponse,
    PersonnelSummary,
    PersonnelUpdateRequest,
    PersonnelUpdateResponse,
)

PERSONNEL_ROLE_OPTIONS = [
    "Kurye",
    "Bolge Muduru",
    "Saha Denetmen Sefi",
    "Restoran Takim Sefi",
    "Joker",
]
PERSONNEL_STATUS_OPTIONS = ["Aktif", "Pasif"]
VEHICLE_MODE_OPTIONS = [
    "Kendi Motoru",
    "Cat Kapinda Motor Kirasi",
    "Cat Kapinda Motor Satisi",
]
FIXED_COST_MODEL_BY_ROLE = {
    "Kurye": "fixed_kurye",
    "Bolge Muduru": "fixed_bolge_muduru",
    "Saha Denetmen Sefi": "fixed_saha_denetmen_sefi",
    "Restoran Takim Sefi": "fixed_restoran_takim_sefi",
    "Joker": "fixed_joker",
}
ROLE_CODE_PREFIX = {
    "Kurye": "K",
    "Bolge Muduru": "BM",
    "Saha Denetmen Sefi": "SDS",
    "Restoran Takim Sefi": "RTS",
    "Joker": "J",
}
ROLE_ALIAS_MAP = {
    "Bölge Müdürü": "Bolge Muduru",
    "Saha Denetmen Şefi": "Saha Denetmen Sefi",
    "Restoran Takım Şefi": "Restoran Takim Sefi",
}
REVERSE_ROLE_ALIAS_MAP = {value: key for key, value in ROLE_ALIAS_MAP.items()}
VEHICLE_MODE_ALIAS_MAP = {
    "Çat Kapında Motor Kirası": "Cat Kapinda Motor Kirasi",
    "Çat Kapında Motor Satışı": "Cat Kapinda Motor Satisi",
}
REVERSE_VEHICLE_MODE_ALIAS_MAP = {value: key for key, value in VEHICLE_MODE_ALIAS_MAP.items()}


def _normalize_role(value: str) -> str:
    raw = str(value or "").strip()
    normalized = ROLE_ALIAS_MAP.get(raw, raw)
    return normalized if normalized in PERSONNEL_ROLE_OPTIONS else "Kurye"


def _display_role(value: str) -> str:
    return REVERSE_ROLE_ALIAS_MAP.get(value, value)


def _normalize_vehicle_mode(value: str) -> str:
    raw = str(value or "").strip()
    normalized = VEHICLE_MODE_ALIAS_MAP.get(raw, raw)
    return normalized if normalized in VEHICLE_MODE_OPTIONS else "Kendi Motoru"


def _display_vehicle_mode(value: str) -> str:
    return REVERSE_VEHICLE_MODE_ALIAS_MAP.get(value, value)


def _resolve_vehicle_fields(vehicle_mode: str) -> dict[str, str]:
    normalized_mode = _normalize_vehicle_mode(vehicle_mode)
    if normalized_mode == "Cat Kapinda Motor Kirasi":
        return {
            "vehicle_type": "Çat Kapında",
            "motor_rental": "Evet",
            "motor_purchase": "Hayır",
        }
    if normalized_mode == "Cat Kapinda Motor Satisi":
        return {
            "vehicle_type": "Çat Kapında",
            "motor_rental": "Hayır",
            "motor_purchase": "Evet",
        }
    return {
        "vehicle_type": "Kendi Motoru",
        "motor_rental": "Hayır",
        "motor_purchase": "Hayır",
    }


def _derive_vehicle_mode(row: dict[str, object]) -> str:
    vehicle_type = str(row.get("vehicle_type") or "").strip()
    motor_rental = str(row.get("motor_rental") or "Hayır").strip()
    motor_purchase = str(row.get("motor_purchase") or "Hayır").strip()
    if vehicle_type == "Çat Kapında" and motor_purchase == "Evet":
        return "Cat Kapinda Motor Satisi"
    if vehicle_type == "Çat Kapında" and motor_rental == "Evet":
        return "Cat Kapinda Motor Kirasi"
    return "Kendi Motoru"


def _role_code_prefix(role: str) -> str:
    return ROLE_CODE_PREFIX.get(_normalize_role(role), "K")


def _build_next_person_code(
    conn: psycopg.Connection,
    *,
    role: str,
    exclude_id: int | None = None,
) -> str:
    prefix = _role_code_prefix(role)
    max_number = 0
    for code in fetch_person_code_values(conn, prefix, exclude_id=exclude_id):
        match = re.search(rf"^CK-{re.escape(prefix)}(\d+)$", str(code or ""))
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"CK-{prefix}{max_number + 1:02d}"


def _resolve_cost_model_for_role(role: str) -> str:
    return FIXED_COST_MODEL_BY_ROLE.get(_normalize_role(role), "fixed_kurye")


def _build_management_entry(
    row: dict[str, object],
    *,
    include_vehicle_fields: bool = True,
) -> PersonnelManagementEntry:
    vehicle_mode = _display_vehicle_mode(_derive_vehicle_mode(row)) if include_vehicle_fields else ""
    current_plate = str(row["current_plate"] or "") if include_vehicle_fields else ""
    return PersonnelManagementEntry(
        id=int(row["id"]),
        person_code=str(row["person_code"] or ""),
        full_name=str(row["full_name"] or ""),
        role=_display_role(str(row["role"] or "")),
        status=str(row["status"] or ""),
        phone=str(row["phone"] or ""),
        restaurant_id=int(row["restaurant_id"]) if row["restaurant_id"] else None,
        restaurant_label=str(row["restaurant_label"] or "-"),
        vehicle_mode=vehicle_mode,
        current_plate=current_plate,
        start_date=row["start_date"],
        monthly_fixed_cost=float(row["monthly_fixed_cost"] or 0),
        notes=str(row["notes"] or ""),
    )


def _build_personnel_delete_message(dependency_counts: dict[str, int]) -> str:
    detail_parts = [
        f"{label}: {count}"
        for label, count in [
            ("Puantaj", dependency_counts.get("puantaj", 0)),
            ("Kesinti", dependency_counts.get("kesinti", 0)),
            ("Rol geçmişi", dependency_counts.get("rol_gecmisi", 0)),
            ("Araç geçmişi", dependency_counts.get("arac_gecmisi", 0)),
            ("Plaka geçmişi", dependency_counts.get("plaka", 0)),
            ("Zimmet", dependency_counts.get("zimmet", 0)),
            ("Box iade", dependency_counts.get("box_iade", 0)),
        ]
        if count
    ]
    if detail_parts:
        return "Personel ve bağlı kayıtlar kalıcı olarak silindi. " + " | ".join(detail_parts)
    return "Personel kaydı kalıcı olarak silindi."


def _sync_personnel_plate_history_baselines(conn: psycopg.Connection) -> None:
    changed = False
    for row in fetch_personnel_plate_baseline_candidates(conn):
        current_plate = str(row.get("current_plate") or "").strip()
        if not current_plate:
            continue
        if int(row.get("plate_history_count") or 0) > 0:
            continue
        start_date = row.get("start_date")
        insert_plate_history_record(
            conn,
            personnel_id=int(row["id"]),
            plate=current_plate,
            start_date=(
                start_date.isoformat()
                if isinstance(start_date, date)
                else str(start_date or date.today().isoformat())
            ),
            end_date=None,
            reason="Sistem: Başlangıç plakası",
            active=True,
        )
        changed = True
    if changed:
        conn.commit()


def _sync_plate_history_after_personnel_write(
    conn: psycopg.Connection,
    *,
    person_id: int,
    previous_plate: str,
    current_plate: str,
    effective_date: date | None,
    reason: str,
) -> None:
    normalized_previous_plate = str(previous_plate or "").strip()
    normalized_current_plate = str(current_plate or "").strip()
    effective_date_text = (effective_date or date.today()).isoformat()

    if normalized_current_plate == normalized_previous_plate:
        if normalized_current_plate and count_plate_history_records_for_personnel(conn, person_id) == 0:
            insert_plate_history_record(
                conn,
                personnel_id=person_id,
                plate=normalized_current_plate,
                start_date=effective_date_text,
                end_date=None,
                reason=reason,
                active=True,
            )
        return

    if normalized_previous_plate:
        close_active_plate_history_records(conn, person_id, end_date=effective_date_text)

    if normalized_current_plate:
        active_row = fetch_active_plate_history_record(conn, person_id)
        if active_row:
            active_plate = str(active_row.get("plate") or "").strip()
            if active_plate == normalized_current_plate:
                return
            close_active_plate_history_records(conn, person_id, end_date=effective_date_text)
        insert_plate_history_record(
            conn,
            personnel_id=person_id,
            plate=normalized_current_plate,
            start_date=effective_date_text,
            end_date=None,
            reason=reason,
            active=True,
        )


def build_personnel_status() -> PersonnelModuleStatus:
    return PersonnelModuleStatus(
        module="personnel",
        status="active",
        next_slice="personnel-dashboard",
    )


def build_personnel_dashboard(
    conn: psycopg.Connection,
    *,
    limit: int,
    include_vehicle_fields: bool = True,
) -> PersonnelDashboardResponse:
    summary_values = fetch_personnel_summary(conn)
    recent_rows = fetch_recent_personnel_records(conn, limit=limit)
    return PersonnelDashboardResponse(
        module="personnel",
        status="active",
        summary=PersonnelSummary(**summary_values),
        recent_entries=[
            _build_management_entry(row, include_vehicle_fields=include_vehicle_fields)
            for row in recent_rows
        ],
    )


def build_personnel_form_options(
    conn: psycopg.Connection,
    *,
    restaurant_id: int | None = None,
) -> PersonnelFormOptionsResponse:
    restaurants = fetch_personnel_restaurants(conn)
    default_restaurant_id = restaurant_id
    if default_restaurant_id is None and restaurants:
        default_restaurant_id = int(restaurants[0]["id"])
    return PersonnelFormOptionsResponse(
        restaurants=[
            PersonnelRestaurantOption(
                id=int(row["id"]),
                label=f"{str(row['brand']).strip()} - {str(row['branch']).strip()}",
            )
            for row in restaurants
        ],
        role_options=[_display_role(role) for role in PERSONNEL_ROLE_OPTIONS],
        status_options=PERSONNEL_STATUS_OPTIONS,
        vehicle_mode_options=[_display_vehicle_mode(mode) for mode in VEHICLE_MODE_OPTIONS],
        selected_restaurant_id=default_restaurant_id,
    )


def build_personnel_management(
    conn: psycopg.Connection,
    *,
    limit: int,
    restaurant_id: int | None = None,
    role: str | None = None,
    search: str | None = None,
    include_vehicle_fields: bool = True,
) -> PersonnelManagementResponse:
    normalized_role = _normalize_role(role) if role else None
    rows = fetch_personnel_management_records(
        conn,
        limit=limit,
        restaurant_id=restaurant_id,
        role=normalized_role,
        search=search,
    )
    return PersonnelManagementResponse(
        total_entries=count_personnel_management_records(
            conn,
            restaurant_id=restaurant_id,
            role=normalized_role,
            search=search,
        ),
        entries=[
            _build_management_entry(row, include_vehicle_fields=include_vehicle_fields)
            for row in rows
        ],
    )


def build_personnel_plate_workspace(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> PersonnelPlateWorkspaceResponse:
    _sync_personnel_plate_history_baselines(conn)
    people = fetch_personnel_plate_candidates(conn, limit=limit)
    history_rows = fetch_recent_plate_history_records(conn, limit=limit)
    return PersonnelPlateWorkspaceResponse(
        summary=PersonnelPlateSummary(
            total_history_records=count_total_plate_history_records(conn),
            active_plate_assignments=count_active_plate_history_records(conn),
            active_catkapinda_vehicle_personnel=count_active_catkapinda_vehicle_personnel(conn),
            active_missing_plate_personnel=count_active_personnel_missing_plate(conn),
        ),
        people=[
            PersonnelPlateCandidateEntry(
                id=int(row["id"]),
                person_code=str(row["person_code"] or ""),
                full_name=str(row["full_name"] or ""),
                role=_display_role(str(row["role"] or "")),
                status=str(row["status"] or ""),
                restaurant_label=str(row["restaurant_label"] or "-"),
                vehicle_mode=_display_vehicle_mode(_derive_vehicle_mode(row)),
                current_plate=str(row["current_plate"] or ""),
                plate_history_count=int(row["plate_history_count"] or 0),
            )
            for row in people
        ],
        history=[
            PersonnelPlateHistoryEntry(
                id=int(row["id"]),
                personnel_id=int(row["personnel_id"]),
                person_code=str(row["person_code"] or ""),
                full_name=str(row["full_name"] or ""),
                role=_display_role(str(row["role"] or "")),
                restaurant_label=str(row["restaurant_label"] or "-"),
                vehicle_mode=_display_vehicle_mode(_derive_vehicle_mode(row)),
                current_plate=str(row["current_plate"] or ""),
                plate=str(row["plate"] or ""),
                start_date=row["start_date"],
                end_date=row["end_date"],
                reason=str(row["reason"] or ""),
                active=bool(row["active"]),
            )
            for row in history_rows
        ],
    )


def create_personnel_plate_history_entry(
    conn: psycopg.Connection,
    *,
    payload: PersonnelPlateCreateRequest,
) -> PersonnelPlateCreateResponse:
    row = fetch_personnel_record_by_id(conn, payload.personnel_id)
    if row is None:
        raise LookupError("Personel kaydı bulunamadı.")

    plate = str(payload.plate or "").strip()
    if not plate:
        raise ValueError("Yeni plaka zorunlu.")

    start_date = payload.start_date or date.today()
    if payload.end_date and payload.end_date < start_date:
        raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")

    close_active_plate_history_records(conn, payload.personnel_id, end_date=start_date.isoformat())
    history_id = insert_plate_history_record(
        conn,
        personnel_id=payload.personnel_id,
        plate=plate,
        start_date=start_date.isoformat(),
        end_date=payload.end_date.isoformat() if payload.end_date else None,
        reason=str(payload.reason or "").strip() or "Yeni zimmet",
        active=True,
    )
    update_personnel_current_plate(conn, payload.personnel_id, plate)
    conn.commit()
    return PersonnelPlateCreateResponse(
        history_id=history_id,
        personnel_id=payload.personnel_id,
        plate=plate,
        message="Plaka geçmişi güncellendi.",
    )


def build_personnel_detail(
    conn: psycopg.Connection,
    *,
    person_id: int,
    include_vehicle_fields: bool = True,
) -> PersonnelDetailResponse:
    row = fetch_personnel_record_by_id(conn, person_id)
    if row is None:
        raise LookupError("Personel kaydı bulunamadı.")
    return PersonnelDetailResponse(
        entry=_build_management_entry(row, include_vehicle_fields=include_vehicle_fields)
    )


def create_personnel_record(
    conn: psycopg.Connection,
    *,
    payload: PersonnelCreateRequest,
    allow_vehicle_fields: bool = True,
) -> PersonnelCreateResponse:
    full_name = str(payload.full_name or "").strip()
    if not full_name:
        raise ValueError("Ad soyad zorunlu.")

    normalized_role = _normalize_role(payload.role)
    normalized_vehicle_mode = (
        _normalize_vehicle_mode(payload.vehicle_mode) if allow_vehicle_fields else "Kendi Motoru"
    )
    normalized_status = payload.status if payload.status in PERSONNEL_STATUS_OPTIONS else "Aktif"
    person_code = _build_next_person_code(conn, role=normalized_role)
    vehicle_fields = _resolve_vehicle_fields(normalized_vehicle_mode)
    person_id = insert_personnel_record(
        conn,
        {
            "person_code": person_code,
            "full_name": full_name,
            "role": _display_role(normalized_role),
            "status": normalized_status,
            "phone": str(payload.phone or "").strip(),
            "accounting_type": "Kendi Muhasebecisi",
            "new_company_setup": "Hayır",
            "assigned_restaurant_id": payload.assigned_restaurant_id,
            "vehicle_type": vehicle_fields["vehicle_type"],
            "motor_rental": vehicle_fields["motor_rental"],
            "motor_purchase": vehicle_fields["motor_purchase"],
            "current_plate": str(payload.current_plate or "").strip() if allow_vehicle_fields else "",
            "start_date": payload.start_date,
            "exit_date": date.today().isoformat() if normalized_status == "Pasif" else None,
            "cost_model": _resolve_cost_model_for_role(normalized_role),
            "monthly_fixed_cost": float(payload.monthly_fixed_cost or 0),
            "notes": str(payload.notes or "").strip(),
        },
    )
    _sync_plate_history_after_personnel_write(
        conn,
        person_id=person_id,
        previous_plate="",
        current_plate=str(payload.current_plate or "").strip() if allow_vehicle_fields else "",
        effective_date=payload.start_date,
        reason="Sistem: Başlangıç plakası",
    )
    sync_mobile_auth_user_for_personnel(conn, personnel_id=person_id)
    conn.commit()
    return PersonnelCreateResponse(
        person_id=person_id,
        person_code=person_code,
        message="Personel kaydı oluşturuldu.",
    )


def update_personnel_record_entry(
    conn: psycopg.Connection,
    *,
    person_id: int,
    payload: PersonnelUpdateRequest,
    allow_vehicle_fields: bool = True,
) -> PersonnelUpdateResponse:
    existing_row = fetch_personnel_record_by_id(conn, person_id)
    if existing_row is None:
        raise LookupError("Personel kaydı bulunamadı.")

    full_name = str(payload.full_name or "").strip()
    if not full_name:
        raise ValueError("Ad soyad zorunlu.")

    normalized_role = _normalize_role(payload.role)
    normalized_status = payload.status if payload.status in PERSONNEL_STATUS_OPTIONS else "Aktif"
    next_person_code = _build_next_person_code(conn, role=normalized_role, exclude_id=person_id)
    current_code = str(existing_row.get("person_code") or "").strip()
    person_code = current_code or next_person_code
    if _role_code_prefix(existing_row.get("role") or "") != _role_code_prefix(normalized_role):
        person_code = next_person_code

    if allow_vehicle_fields:
        normalized_vehicle_mode = _normalize_vehicle_mode(payload.vehicle_mode)
        vehicle_fields = _resolve_vehicle_fields(normalized_vehicle_mode)
        current_plate = str(payload.current_plate or "").strip()
        previous_plate = str(existing_row.get("current_plate") or "").strip()
    else:
        vehicle_fields = {
            "vehicle_type": str(existing_row.get("vehicle_type") or ""),
            "motor_rental": str(existing_row.get("motor_rental") or "Hayır"),
            "motor_purchase": str(existing_row.get("motor_purchase") or "Hayır"),
        }
        current_plate = str(existing_row.get("current_plate") or "")
        previous_plate = current_plate
    update_personnel_record(
        conn,
        person_id,
        {
            "person_code": person_code,
            "full_name": full_name,
            "role": _display_role(normalized_role),
            "status": normalized_status,
            "phone": str(payload.phone or "").strip(),
            "assigned_restaurant_id": payload.assigned_restaurant_id,
            "vehicle_type": vehicle_fields["vehicle_type"],
            "motor_rental": vehicle_fields["motor_rental"],
            "motor_purchase": vehicle_fields["motor_purchase"],
            "current_plate": current_plate,
            "start_date": payload.start_date,
            "exit_date": date.today().isoformat() if normalized_status == "Pasif" else None,
            "cost_model": _resolve_cost_model_for_role(normalized_role),
            "monthly_fixed_cost": float(payload.monthly_fixed_cost or 0),
            "notes": str(payload.notes or "").strip(),
        },
    )
    if allow_vehicle_fields:
        _sync_plate_history_after_personnel_write(
            conn,
            person_id=person_id,
            previous_plate=previous_plate,
            current_plate=current_plate,
            effective_date=date.today(),
            reason="Sistem: Personel kartından plaka değişimi",
        )
    sync_mobile_auth_user_for_personnel(conn, personnel_id=person_id)
    conn.commit()
    return PersonnelUpdateResponse(
        person_id=person_id,
        person_code=person_code,
        message="Personel kaydı güncellendi.",
    )


def toggle_personnel_record_status(
    conn: psycopg.Connection,
    *,
    person_id: int,
) -> PersonnelStatusUpdateResponse:
    existing_row = fetch_personnel_record_by_id(conn, person_id)
    if existing_row is None:
        raise LookupError("Personel kaydı bulunamadı.")
    next_status = "Pasif" if str(existing_row.get("status") or "") == "Aktif" else "Aktif"
    update_personnel_status(
        conn,
        person_id,
        status=next_status,
        exit_date=date.today().isoformat() if next_status == "Pasif" else None,
    )
    sync_mobile_auth_user_for_personnel(conn, personnel_id=person_id)
    conn.commit()
    return PersonnelStatusUpdateResponse(
        person_id=person_id,
        status=next_status,
        message="Personel pasife alındı." if next_status == "Pasif" else "Personel aktifleştirildi.",
    )


def delete_personnel_record_entry(
    conn: psycopg.Connection,
    *,
    person_id: int,
) -> PersonnelDeleteResponse:
    existing_row = fetch_personnel_record_by_id(conn, person_id)
    if existing_row is None:
        raise LookupError("Personel kaydı bulunamadı.")

    dependency_counts = {
        "puantaj": count_personnel_linked_daily_entries(conn, person_id),
        "kesinti": count_personnel_linked_deductions(conn, person_id),
        "rol_gecmisi": count_personnel_linked_role_history(conn, person_id),
        "arac_gecmisi": count_personnel_linked_vehicle_history(conn, person_id),
        "plaka": count_personnel_linked_plate_history(conn, person_id),
        "zimmet": count_personnel_linked_equipment_issues(conn, person_id),
        "box_iade": count_personnel_linked_box_returns(conn, person_id),
    }
    sync_mobile_auth_user_for_personnel(
        conn,
        personnel_id=person_id,
        fallback_row={**existing_row, "status": "Pasif"},
    )
    delete_personnel_and_dependencies(conn, person_id)
    conn.commit()
    return PersonnelDeleteResponse(
        person_id=person_id,
        message=_build_personnel_delete_message(dependency_counts),
    )
