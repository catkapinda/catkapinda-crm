from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from repositories.deductions_repository import (
    delete_deduction_record,
    delete_deduction_records,
    fetch_deduction_management_df,
    insert_deduction_record,
    update_deduction_record,
)
from services.audit_service import record_audit_event


@dataclass
class DeductionsWorkspacePayload:
    raw_df: Any
    manual_deductions_df: Any


@dataclass
class DeductionSelectionPayload:
    row: Any
    current_person: str
    person_index: int
    type_index: int
    current_date: Any
    is_auto_record: bool


def load_deductions_workspace_payload(conn) -> DeductionsWorkspacePayload:
    raw_df = fetch_deduction_management_df(conn)
    manual_deductions_df = raw_df[raw_df["auto_source_key"].fillna("").astype(str).str.strip() == ""].copy() if not raw_df.empty else raw_df
    return DeductionsWorkspacePayload(raw_df=raw_df, manual_deductions_df=manual_deductions_df)


def build_deduction_selection_payload(
    raw_df,
    *,
    selected_id: int,
    person_opts: dict[str, int],
    deduction_types: list[str],
    safe_float_fn: Callable[[Any, float], float],
    is_system_personnel_auto_deduction_key_fn: Callable[[Any], bool],
) -> DeductionSelectionPayload:
    row = raw_df.loc[raw_df["id"] == selected_id].iloc[0]
    reverse_person = {v: k for k, v in person_opts.items()}
    current_person = reverse_person.get(int(row["personnel_id"]), list(person_opts.keys())[0])
    person_index = list(person_opts.keys()).index(current_person) if current_person in person_opts else 0
    type_index = deduction_types.index(row["deduction_type"]) if row["deduction_type"] in deduction_types else len(deduction_types) - 1
    current_date = datetime.strptime(str(row["deduction_date"]), "%Y-%m-%d").date()
    is_auto_record = is_system_personnel_auto_deduction_key_fn(row.get("auto_source_key"))
    row["amount"] = safe_float_fn(row["amount"])
    return DeductionSelectionPayload(
        row=row,
        current_person=current_person,
        person_index=person_index,
        type_index=type_index,
        current_date=current_date,
        is_auto_record=is_auto_record,
    )


def create_deduction_and_commit(
    conn,
    *,
    deduction_values: dict[str, Any],
) -> str:
    try:
        insert_deduction_record(conn, deduction_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = f"Kesinti ay sonuna kaydedildi: {deduction_values['deduction_date']}"
    record_audit_event(
        conn,
        entity_type="deduction",
        action_type="create",
        summary=success_text,
        details=deduction_values,
    )
    return success_text


def update_deduction_and_commit(
    conn,
    *,
    deduction_id: int,
    deduction_values: dict[str, Any],
) -> str:
    try:
        update_deduction_record(conn, deduction_id, deduction_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = f"Kesinti ay sonuna güncellendi: {deduction_values['deduction_date']}"
    record_audit_event(
        conn,
        entity_type="deduction",
        entity_id=deduction_id,
        action_type="update",
        summary=success_text,
        details=deduction_values,
    )
    return success_text


def delete_deduction_and_commit(conn, *, deduction_id: int) -> str:
    try:
        delete_deduction_record(conn, deduction_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = "Kesinti silindi."
    record_audit_event(
        conn,
        entity_type="deduction",
        entity_id=deduction_id,
        action_type="delete",
        summary=success_text,
    )
    return success_text


def bulk_delete_deductions_and_commit(conn, *, deduction_ids: list[int]) -> str:
    try:
        deleted_count = delete_deduction_records(conn, deduction_ids)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = f"{deleted_count} manuel kesinti kaydı toplu olarak silindi."
    record_audit_event(
        conn,
        entity_type="deduction",
        action_type="bulk_delete",
        summary=success_text,
        details={"deduction_ids": deduction_ids, "deleted_count": deleted_count},
    )
    return success_text
