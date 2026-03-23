from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from repositories.attendance_repository import (
    delete_daily_entry,
    fetch_attendance_hero_stats,
    fetch_bulk_attendance_people_rows,
    fetch_daily_entry_by_id,
    fetch_daily_entry_management_df,
    insert_daily_entry,
    update_daily_entry,
)
from services.audit_service import record_audit_event
from services.permission_service import require_action_access

ATTENDANCE_ENTRY_MODE_OPTIONS = [
    "Restoran Kuryesi",
    "Joker",
    "Destek",
    "Haftalık İzin",
]
ABSENCE_REASON_OPTIONS = ["İzin", "Raporlu", "İhbarsız Çıkış", "Gelmedi", "Diğer"]
COVERAGE_TYPE_OPTIONS = ["Joker", "Destek"]
NON_WORKING_ATTENDANCE_STATUSES = {"İzin", "Gelmedi", "Raporlu", "İhbarsız Çıkış"}


@dataclass
class DailyEntryWorkspacePayload:
    df: Any
    entry_map: dict[str, int]


@dataclass
class DailyEntrySelectionPayload:
    selected_id: int
    selected_row: Any
    current_rest_label: str
    entry_mode: str
    planned_default: str
    actual_default: str
    absence_reason_default: str
    coverage_type_default: str


@dataclass
class BulkAttendanceContext:
    person_label_map: dict[str, int]
    name_to_label: dict[str, str]
    default_rows: list[dict[str, Any]]


@dataclass
class AttendanceHeroStats:
    total_count: int
    today_count: int
    month_count: int
    active_restaurants: int


def load_attendance_hero_stats(conn, today_value: date) -> AttendanceHeroStats:
    stats = fetch_attendance_hero_stats(
        conn,
        today_iso=today_value.isoformat(),
        month_start_iso=today_value.replace(day=1).isoformat(),
    )
    return AttendanceHeroStats(
        total_count=int(stats.get("total_count", 0) or 0),
        today_count=int(stats.get("today_count", 0) or 0),
        month_count=int(stats.get("month_count", 0) or 0),
        active_restaurants=int(stats.get("active_restaurants", 0) or 0),
    )


def load_daily_entry_workspace_payload(conn) -> DailyEntryWorkspacePayload:
    df = fetch_daily_entry_management_df(conn)
    entry_map = {
        f"{row['entry_date']} | {row['restoran']} | {row['calisan_personel']} | {row['package_count']} paket | ID:{row['id']}": int(row["id"])
        for _, row in df.iterrows()
    } if not df.empty else {}
    return DailyEntryWorkspacePayload(df=df, entry_map=entry_map)


def infer_daily_entry_mode(
    *,
    status: Any,
    planned_personnel_id: Any,
    actual_personnel_id: Any,
    coverage_type: Any = None,
) -> str:
    status_text = str(status or "").strip()
    coverage_text = str(coverage_type or "").strip()
    planned_id = int(planned_personnel_id or 0) if planned_personnel_id else 0
    actual_id = int(actual_personnel_id or 0) if actual_personnel_id else 0
    if planned_id > 0 and actual_id > 0 and planned_id != actual_id:
        if coverage_text in COVERAGE_TYPE_OPTIONS:
            return coverage_text
        if status_text == "Joker":
            return "Joker"
        return "Destek"
    if planned_id > 0 and actual_id <= 0:
        return "Haftalık İzin"
    return "Restoran Kuryesi"


def resolve_daily_entry_values(
    *,
    entry_mode: str,
    primary_person_id: int | None,
    planned_personnel_id: int | None,
    actual_personnel_id: int | None,
    absence_reason: str,
    coverage_type: str,
    worked_hours: float,
    package_count: float,
    notes: str,
) -> dict[str, Any]:
    notes_text = str(notes or "").strip()
    reason_text = str(absence_reason or "").strip()
    coverage_text = str(coverage_type or "").strip()
    resolved_planned_id = planned_personnel_id or primary_person_id

    if entry_mode == "Restoran Kuryesi":
        if not primary_person_id:
            raise ValueError("Restoran kuryesi akışında giren kuryeyi seçmelisin.")
        return {
            "planned_personnel_id": primary_person_id,
            "actual_personnel_id": primary_person_id,
            "status": "Normal",
            "worked_hours": float(worked_hours or 0),
            "package_count": float(package_count or 0),
            "absence_reason": "",
            "coverage_type": "",
            "notes": notes_text,
        }

    if entry_mode in {"Joker", "Destek"}:
        if not resolved_planned_id:
            raise ValueError("Yerine girişte çalışan personeli seçmelisin.")
        if not actual_personnel_id:
            raise ValueError("Yerine girişte giren kuryeyi seçmelisin.")
        if resolved_planned_id == actual_personnel_id:
            raise ValueError("Yerine girişte giren kurye, normalde girecek kişiden farklı olmalı.")
        if not reason_text:
            raise ValueError("Yerine girişte neden girmedi bilgisini seçmelisin.")
        return {
            "planned_personnel_id": resolved_planned_id,
            "actual_personnel_id": actual_personnel_id,
            "status": "Normal",
            "worked_hours": float(worked_hours or 0),
            "package_count": float(package_count or 0),
            "absence_reason": reason_text,
            "coverage_type": entry_mode,
            "notes": notes_text,
        }

    if entry_mode == "Haftalık İzin":
        if not resolved_planned_id:
            raise ValueError("Haftalık izinde çalışan personeli seçmelisin.")
        if not reason_text:
            raise ValueError("Haftalık izinde neden girmedi bilgisini seçmelisin.")
        status_text = reason_text if reason_text in NON_WORKING_ATTENDANCE_STATUSES else "Gelmedi"
        return {
            "planned_personnel_id": resolved_planned_id,
            "actual_personnel_id": None,
            "status": status_text,
            "worked_hours": 0.0,
            "package_count": 0.0,
            "absence_reason": reason_text,
            "coverage_type": "",
            "notes": notes_text,
        }

    raise ValueError("Geçersiz puantaj akışı.")


def build_daily_entry_selection_payload(
    conn,
    *,
    selected_id: int,
    rest_opts: dict[str, int],
    person_opts: dict[str, int],
) -> DailyEntrySelectionPayload:
    selected_row = fetch_daily_entry_by_id(conn, selected_id)
    current_rest_label = next((label for label, rid in rest_opts.items() if rid == selected_row["restaurant_id"]), list(rest_opts.keys())[0])
    entry_mode = infer_daily_entry_mode(
        status=selected_row["status"],
        planned_personnel_id=selected_row["planned_personnel_id"],
        actual_personnel_id=selected_row["actual_personnel_id"],
        coverage_type=selected_row["coverage_type"],
    )
    planned_default = "-"
    actual_default = "-"
    for label, pid in person_opts.items():
        if selected_row["planned_personnel_id"] == pid:
            planned_default = label
        if selected_row["actual_personnel_id"] == pid:
            actual_default = label
    absence_reason_default = str(selected_row["absence_reason"] or "").strip()
    if not absence_reason_default and str(selected_row["status"] or "").strip() in NON_WORKING_ATTENDANCE_STATUSES:
        absence_reason_default = str(selected_row["status"] or "").strip()
    coverage_type_default = str(selected_row["coverage_type"] or "").strip()
    if not coverage_type_default and planned_default != "-" and actual_default != "-" and planned_default != actual_default:
        if str(selected_row["status"] or "").strip() == "Joker" or "(Joker)" in actual_default:
            coverage_type_default = "Joker"
        else:
            coverage_type_default = "Destek"
    return DailyEntrySelectionPayload(
        selected_id=selected_id,
        selected_row=selected_row,
        current_rest_label=current_rest_label,
        entry_mode=entry_mode,
        planned_default=planned_default,
        actual_default=actual_default,
        absence_reason_default=absence_reason_default,
        coverage_type_default=coverage_type_default,
    )


def create_daily_entry_and_sync(
    conn,
    *,
    entry_values: dict[str, Any],
    affected_person_id: int | None,
    sync_personnel_business_rules_for_ids_fn: Callable[..., None],
    actor_role: str = "admin",
) -> str:
    require_action_access(actor_role, "attendance.create")
    try:
        insert_daily_entry(conn, entry_values)
        sync_personnel_business_rules_for_ids_fn(conn, [affected_person_id], create_onboarding=False, full_history=True)
        success_text = "Günlük kayıt eklendi."
        record_audit_event(
            conn,
            entity_type="attendance",
            action_type="create",
            summary=success_text,
            details={
                "entry_date": entry_values.get("entry_date"),
                "restaurant_id": entry_values.get("restaurant_id"),
                "planned_personnel_id": entry_values.get("planned_personnel_id"),
                "actual_personnel_id": entry_values.get("actual_personnel_id"),
                "status": entry_values.get("status"),
                "absence_reason": entry_values.get("absence_reason"),
                "coverage_type": entry_values.get("coverage_type"),
                "worked_hours": entry_values.get("worked_hours"),
                "package_count": entry_values.get("package_count"),
            },
            commit=False,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return success_text


def update_daily_entry_and_sync(
    conn,
    *,
    entry_id: int,
    entry_values: dict[str, Any],
    previous_actual_id: int,
    actual_id: int | None,
    sync_personnel_business_rules_for_ids_fn: Callable[..., None],
    actor_role: str = "admin",
) -> str:
    require_action_access(actor_role, "attendance.update")
    try:
        update_daily_entry(conn, entry_id, entry_values)
        sync_personnel_business_rules_for_ids_fn(conn, [previous_actual_id, actual_id], create_onboarding=False, full_history=True)
        success_text = "Günlük puantaj kaydı güncellendi."
        record_audit_event(
            conn,
            entity_type="attendance",
            entity_id=entry_id,
            action_type="update",
            summary=success_text,
            details={
                "entry_date": entry_values.get("entry_date"),
                "restaurant_id": entry_values.get("restaurant_id"),
                "planned_personnel_id": entry_values.get("planned_personnel_id"),
                "previous_actual_id": previous_actual_id,
                "actual_personnel_id": actual_id,
                "status": entry_values.get("status"),
                "absence_reason": entry_values.get("absence_reason"),
                "coverage_type": entry_values.get("coverage_type"),
            },
            commit=False,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return success_text


def delete_daily_entry_and_sync(
    conn,
    *,
    entry_id: int,
    deleted_actual_id: int,
    sync_personnel_business_rules_for_ids_fn: Callable[..., None],
    actor_role: str = "admin",
) -> str:
    require_action_access(actor_role, "attendance.delete")
    try:
        delete_daily_entry(conn, entry_id)
        sync_personnel_business_rules_for_ids_fn(conn, [deleted_actual_id], create_onboarding=False, full_history=True)
        success_text = "Günlük puantaj kaydı silindi."
        record_audit_event(
            conn,
            entity_type="attendance",
            entity_id=entry_id,
            action_type="delete",
            summary=success_text,
            details={"deleted_actual_id": deleted_actual_id},
            commit=False,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return success_text


def build_bulk_attendance_context(
    conn,
    *,
    restaurant_id: int,
    include_all_active: bool,
    session_rows: Any,
) -> BulkAttendanceContext:
    people_rows = fetch_bulk_attendance_people_rows(conn, restaurant_id, include_all_active)
    person_label_map = {f"{r['full_name']} ({r['role']})": r["id"] for r in people_rows}
    name_to_label = {str(r["full_name"]).strip().lower(): f"{r['full_name']} ({r['role']})" for r in people_rows}
    if session_rows:
        default_rows = session_rows
    else:
        default_rows = [
            {
                "Personel": label,
                "Saat": 0.0,
                "Paket": 0,
                "Durum": "Normal",
                "Not": "",
            }
            for label in person_label_map.keys()
        ]
    return BulkAttendanceContext(
        person_label_map=person_label_map,
        name_to_label=name_to_label,
        default_rows=default_rows,
    )


def build_bulk_rows_from_parsed(
    parsed_rows: list[dict[str, Any]],
    *,
    name_to_label: dict[str, str],
    normalize_entry_status_fn: Callable[[str], str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in parsed_rows:
        guess = name_to_label.get(str(row["person_label"]).strip().lower())
        rows.append(
            {
                "Personel": guess or row["person_label"],
                "Saat": float(row["worked_hours"] or 0),
                "Paket": int(row["package_count"] or 0),
                "Durum": normalize_entry_status_fn(str(row["entry_status"] or "Normal")),
                "Not": row.get("notes", ""),
            }
        )
    return rows


def save_bulk_entries_and_sync(
    conn,
    *,
    edited_df: Any,
    selected_date_iso: str,
    restaurant_id: int,
    person_label_map: dict[str, int],
    username: str,
    normalize_entry_status_fn: Callable[[str], str],
    sync_personnel_business_rules_for_ids_fn: Callable[..., None],
    actor_role: str = "admin",
) -> int:
    require_action_access(actor_role, "attendance.bulk_create")
    inserted = 0
    affected_person_ids: list[int] = []
    try:
        for _, row in edited_df.iterrows():
            person_label = str(row.get("Personel", "")).strip()
            if not person_label or person_label not in person_label_map:
                continue
            hours = float(row.get("Saat") or 0)
            packages = int(row.get("Paket") or 0)
            status = normalize_entry_status_fn(str(row.get("Durum") or "Normal").strip())
            notes = str(row.get("Not") or "").strip()
            if hours == 0 and packages == 0 and status == "Normal":
                continue
            person_id = person_label_map[person_label]
            note_parts = [part for part in [notes, "Kaynak: Toplu Puantaj", f"Kaydeden: {username}"] if part]
            insert_daily_entry(
                conn,
                {
                    "entry_date": selected_date_iso,
                    "restaurant_id": restaurant_id,
                    "planned_personnel_id": person_id,
                    "actual_personnel_id": person_id,
                    "status": status,
                    "worked_hours": hours,
                    "package_count": packages,
                    "absence_reason": "",
                    "coverage_type": "",
                    "notes": " | ".join(note_parts),
                },
            )
            inserted += 1
            affected_person_ids.append(person_id)
        sync_personnel_business_rules_for_ids_fn(conn, affected_person_ids, create_onboarding=False, full_history=True)
        if inserted:
            record_audit_event(
                conn,
                entity_type="attendance",
                entity_id=restaurant_id,
                action_type="bulk_create",
                summary=f"{inserted} toplu puantaj kaydı oluşturuldu.",
                details={
                    "entry_date": selected_date_iso,
                    "restaurant_id": restaurant_id,
                    "inserted_count": inserted,
                },
                commit=False,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted
