from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repositories.attendance_repository import (
    delete_daily_entry,
    fetch_bulk_attendance_people_rows,
    fetch_daily_entry_by_id,
    fetch_daily_entry_management_df,
    insert_daily_entry,
    update_daily_entry,
)
from services.audit_service import record_audit_event
from services.permission_service import require_action_access


@dataclass
class DailyEntryWorkspacePayload:
    df: Any
    entry_map: dict[str, int]


@dataclass
class DailyEntrySelectionPayload:
    selected_id: int
    selected_row: Any
    current_rest_label: str
    planned_default: str
    actual_default: str


@dataclass
class BulkAttendanceContext:
    person_label_map: dict[str, int]
    name_to_label: dict[str, str]
    default_rows: list[dict[str, Any]]


def load_daily_entry_workspace_payload(conn) -> DailyEntryWorkspacePayload:
    df = fetch_daily_entry_management_df(conn)
    entry_map = {
        f"{row['entry_date']} | {row['restoran']} | {row['calisan']} | {row['package_count']} paket | ID:{row['id']}": int(row["id"])
        for _, row in df.iterrows()
    } if not df.empty else {}
    return DailyEntryWorkspacePayload(df=df, entry_map=entry_map)


def build_daily_entry_selection_payload(
    conn,
    *,
    selected_id: int,
    rest_opts: dict[str, int],
    person_opts: dict[str, int],
) -> DailyEntrySelectionPayload:
    selected_row = fetch_daily_entry_by_id(conn, selected_id)
    current_rest_label = next((label for label, rid in rest_opts.items() if rid == selected_row["restaurant_id"]), list(rest_opts.keys())[0])
    planned_default = "-"
    actual_default = "-"
    for label, pid in person_opts.items():
        if selected_row["planned_personnel_id"] == pid:
            planned_default = label
        if selected_row["actual_personnel_id"] == pid:
            actual_default = label
    return DailyEntrySelectionPayload(
        selected_id=selected_id,
        selected_row=selected_row,
        current_rest_label=current_rest_label,
        planned_default=planned_default,
        actual_default=actual_default,
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
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, [affected_person_id], create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
    success_text = "Günlük kayıt eklendi."
    record_audit_event(
        conn,
        entity_type="attendance",
        action_type="create",
        summary=success_text,
        details={
            "entry_date": entry_values.get("entry_date"),
            "restaurant_id": entry_values.get("restaurant_id"),
            "actual_personnel_id": entry_values.get("actual_personnel_id"),
            "status": entry_values.get("status"),
            "worked_hours": entry_values.get("worked_hours"),
            "package_count": entry_values.get("package_count"),
        },
    )
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
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, [previous_actual_id, actual_id], create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
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
            "previous_actual_id": previous_actual_id,
            "actual_personnel_id": actual_id,
            "status": entry_values.get("status"),
        },
    )
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
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, [deleted_actual_id], create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
    success_text = "Günlük puantaj kaydı silindi."
    record_audit_event(
        conn,
        entity_type="attendance",
        entity_id=entry_id,
        action_type="delete",
        summary=success_text,
        details={"deleted_actual_id": deleted_actual_id},
    )
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
                    "notes": " | ".join(note_parts),
                },
            )
            inserted += 1
            affected_person_ids.append(person_id)
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, affected_person_ids, create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
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
        )
    return inserted
