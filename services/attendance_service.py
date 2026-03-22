from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repositories.attendance_repository import (
    delete_daily_entry,
    fetch_daily_entry_by_id,
    fetch_daily_entry_management_df,
    insert_daily_entry,
    update_daily_entry,
)


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
) -> str:
    try:
        insert_daily_entry(conn, entry_values)
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, [affected_person_id], create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
    return "Günlük kayıt eklendi."


def update_daily_entry_and_sync(
    conn,
    *,
    entry_id: int,
    entry_values: dict[str, Any],
    previous_actual_id: int,
    actual_id: int | None,
    sync_personnel_business_rules_for_ids_fn: Callable[..., None],
) -> str:
    try:
        update_daily_entry(conn, entry_id, entry_values)
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, [previous_actual_id, actual_id], create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
    return "Günlük puantaj kaydı güncellendi."


def delete_daily_entry_and_sync(
    conn,
    *,
    entry_id: int,
    deleted_actual_id: int,
    sync_personnel_business_rules_for_ids_fn: Callable[..., None],
) -> str:
    try:
        delete_daily_entry(conn, entry_id)
        conn.commit()
        sync_personnel_business_rules_for_ids_fn(conn, [deleted_actual_id], create_onboarding=False, full_history=True)
    except Exception:
        conn.rollback()
        raise
    return "Günlük puantaj kaydı silindi."
