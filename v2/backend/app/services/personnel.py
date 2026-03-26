from __future__ import annotations

import re

import psycopg

from app.repositories.personnel import (
    count_personnel_management_records,
    fetch_person_code_values,
    fetch_personnel_management_records,
    fetch_personnel_record_by_id,
    fetch_personnel_restaurants,
    fetch_personnel_summary,
    fetch_recent_personnel_records,
    insert_personnel_record,
    update_personnel_record,
)
from app.schemas.personnel import (
    PersonnelCreateRequest,
    PersonnelCreateResponse,
    PersonnelDashboardResponse,
    PersonnelDetailResponse,
    PersonnelFormOptionsResponse,
    PersonnelManagementEntry,
    PersonnelManagementResponse,
    PersonnelModuleStatus,
    PersonnelRestaurantOption,
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


def _build_management_entry(row: dict[str, object]) -> PersonnelManagementEntry:
    return PersonnelManagementEntry(
        id=int(row["id"]),
        person_code=str(row["person_code"] or ""),
        full_name=str(row["full_name"] or ""),
        role=_display_role(str(row["role"] or "")),
        status=str(row["status"] or ""),
        phone=str(row["phone"] or ""),
        restaurant_id=int(row["restaurant_id"]) if row["restaurant_id"] else None,
        restaurant_label=str(row["restaurant_label"] or "-"),
        vehicle_mode=_display_vehicle_mode(_derive_vehicle_mode(row)),
        current_plate=str(row["current_plate"] or ""),
        start_date=row["start_date"],
        monthly_fixed_cost=float(row["monthly_fixed_cost"] or 0),
        notes=str(row["notes"] or ""),
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
) -> PersonnelDashboardResponse:
    summary_values = fetch_personnel_summary(conn)
    recent_rows = fetch_recent_personnel_records(conn, limit=limit)
    return PersonnelDashboardResponse(
        module="personnel",
        status="active",
        summary=PersonnelSummary(**summary_values),
        recent_entries=[_build_management_entry(row) for row in recent_rows],
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
        entries=[_build_management_entry(row) for row in rows],
    )


def build_personnel_detail(
    conn: psycopg.Connection,
    *,
    person_id: int,
) -> PersonnelDetailResponse:
    row = fetch_personnel_record_by_id(conn, person_id)
    if row is None:
        raise LookupError("Personel kaydi bulunamadi.")
    return PersonnelDetailResponse(entry=_build_management_entry(row))


def create_personnel_record(
    conn: psycopg.Connection,
    *,
    payload: PersonnelCreateRequest,
) -> PersonnelCreateResponse:
    full_name = str(payload.full_name or "").strip()
    if not full_name:
        raise ValueError("Ad soyad zorunlu.")

    normalized_role = _normalize_role(payload.role)
    normalized_vehicle_mode = _normalize_vehicle_mode(payload.vehicle_mode)
    person_code = _build_next_person_code(conn, role=normalized_role)
    vehicle_fields = _resolve_vehicle_fields(normalized_vehicle_mode)
    person_id = insert_personnel_record(
        conn,
        {
            "person_code": person_code,
            "full_name": full_name,
            "role": _display_role(normalized_role),
            "status": payload.status if payload.status in PERSONNEL_STATUS_OPTIONS else "Aktif",
            "phone": str(payload.phone or "").strip(),
            "accounting_type": "Kendi Muhasebecisi",
            "new_company_setup": "Hayır",
            "assigned_restaurant_id": payload.assigned_restaurant_id,
            "vehicle_type": vehicle_fields["vehicle_type"],
            "motor_rental": vehicle_fields["motor_rental"],
            "motor_purchase": vehicle_fields["motor_purchase"],
            "current_plate": str(payload.current_plate or "").strip(),
            "start_date": payload.start_date,
            "cost_model": _resolve_cost_model_for_role(normalized_role),
            "monthly_fixed_cost": float(payload.monthly_fixed_cost or 0),
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return PersonnelCreateResponse(
        person_id=person_id,
        person_code=person_code,
        message="Personel kaydi olusturuldu.",
    )


def update_personnel_record_entry(
    conn: psycopg.Connection,
    *,
    person_id: int,
    payload: PersonnelUpdateRequest,
) -> PersonnelUpdateResponse:
    existing_row = fetch_personnel_record_by_id(conn, person_id)
    if existing_row is None:
        raise LookupError("Personel kaydi bulunamadi.")

    full_name = str(payload.full_name or "").strip()
    if not full_name:
        raise ValueError("Ad soyad zorunlu.")

    normalized_role = _normalize_role(payload.role)
    normalized_vehicle_mode = _normalize_vehicle_mode(payload.vehicle_mode)
    next_person_code = _build_next_person_code(conn, role=normalized_role, exclude_id=person_id)
    current_code = str(existing_row.get("person_code") or "").strip()
    person_code = current_code or next_person_code
    if _role_code_prefix(existing_row.get("role") or "") != _role_code_prefix(normalized_role):
        person_code = next_person_code

    vehicle_fields = _resolve_vehicle_fields(normalized_vehicle_mode)
    update_personnel_record(
        conn,
        person_id,
        {
            "person_code": person_code,
            "full_name": full_name,
            "role": _display_role(normalized_role),
            "status": payload.status if payload.status in PERSONNEL_STATUS_OPTIONS else "Aktif",
            "phone": str(payload.phone or "").strip(),
            "assigned_restaurant_id": payload.assigned_restaurant_id,
            "vehicle_type": vehicle_fields["vehicle_type"],
            "motor_rental": vehicle_fields["motor_rental"],
            "motor_purchase": vehicle_fields["motor_purchase"],
            "current_plate": str(payload.current_plate or "").strip(),
            "start_date": payload.start_date,
            "cost_model": _resolve_cost_model_for_role(normalized_role),
            "monthly_fixed_cost": float(payload.monthly_fixed_cost or 0),
            "notes": str(payload.notes or "").strip(),
        },
    )
    conn.commit()
    return PersonnelUpdateResponse(
        person_id=person_id,
        person_code=person_code,
        message="Personel kaydi guncellendi.",
    )
