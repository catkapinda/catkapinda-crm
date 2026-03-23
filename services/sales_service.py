from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from repositories.sales_repository import (
    delete_sales_lead_record,
    fetch_sales_leads_df,
    insert_sales_lead_record,
    update_sales_lead_record,
)
from services.audit_service import record_audit_event
from services.permission_service import require_action_access


@dataclass
class SalesWorkspacePayload:
    df: Any


@dataclass
class SalesSelectionPayload:
    row: Any
    status_index: int
    source_index: int


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_sales_hero_stats(df, *, safe_int_fn: Callable[[Any, int], int]) -> list[tuple[str, Any]]:
    if df is None or df.empty:
        return [
            ("Toplam Fırsat", "0"),
            ("Açık Takip", "0"),
            ("Teklif Aşaması", "0"),
            ("Kazanılan", "0"),
        ]
    total_count = len(df)
    open_follow_up = int(df["status"].fillna("").astype(str).isin(["Yeni Talep", "Teklif Hazırlanıyor", "Teklif İletildi", "Tekrar Aranacak", "Toplantı Planlandı"]).sum())
    proposal_stage = int(df["status"].fillna("").astype(str).isin(["Teklif Hazırlanıyor", "Teklif İletildi"]).sum())
    won_count = int(df["status"].fillna("").astype(str).eq("Sözleşme İmzalandı").sum())
    return [
        ("Toplam Fırsat", safe_int_fn(total_count, 0)),
        ("Açık Takip", safe_int_fn(open_follow_up, 0)),
        ("Teklif Aşaması", safe_int_fn(proposal_stage, 0)),
        ("Kazanılan", safe_int_fn(won_count, 0)),
    ]


def load_sales_workspace_payload(
    conn,
    *,
    ensure_dataframe_columns_fn: Callable[[Any, dict[str, Any]], Any],
) -> SalesWorkspacePayload:
    df = fetch_sales_leads_df(conn)
    df = ensure_dataframe_columns_fn(
        df,
        {
            "restaurant_name": "",
            "city": "",
            "district": "",
            "address": "",
            "contact_name": "",
            "contact_phone": "",
            "contact_email": "",
            "requested_courier_count": 0,
            "lead_source": "",
            "proposed_quote": "",
            "pricing_model_hint": "",
            "status": "",
            "next_follow_up_date": "",
            "assigned_owner": "",
            "notes": "",
            "created_at": "",
            "updated_at": "",
        },
    )
    return SalesWorkspacePayload(df=df)


def validate_sales_lead_values(
    *,
    restaurant_name: str,
    city: str,
    district: str,
    contact_name: str,
    contact_phone: str,
    status: str,
) -> list[str]:
    errors: list[str] = []
    if not str(restaurant_name or "").strip():
        errors.append("Restoran adı zorunlu.")
    if not str(city or "").strip():
        errors.append("İl bilgisi zorunlu.")
    if not str(district or "").strip():
        errors.append("İlçe bilgisi zorunlu.")
    if not str(contact_name or "").strip():
        errors.append("Yetkili adı zorunlu.")
    if not str(contact_phone or "").strip():
        errors.append("Yetkili telefon numarası zorunlu.")
    if not str(status or "").strip():
        errors.append("Durum seçimi zorunlu.")
    return errors


def build_sales_selection_payload(
    df,
    *,
    selected_id: int,
    status_options: list[str],
    source_options: list[str],
) -> SalesSelectionPayload:
    row = df.loc[df["id"] == selected_id].iloc[0]
    current_status = str(row.get("status") or status_options[0])
    current_source = str(row.get("lead_source") or source_options[0])
    status_index = status_options.index(current_status) if current_status in status_options else 0
    source_index = source_options.index(current_source) if current_source in source_options else 0
    return SalesSelectionPayload(row=row, status_index=status_index, source_index=source_index)


def create_sales_lead_and_commit(conn, *, sales_values: dict[str, Any], actor_role: str = "admin") -> str:
    require_action_access(actor_role, "sales.create")
    payload = dict(sales_values)
    payload["created_at"] = _utc_now_iso()
    payload["updated_at"] = payload["created_at"]
    try:
        insert_sales_lead_record(conn, payload)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = "Satış fırsatı başarıyla eklendi."
    record_audit_event(
        conn,
        entity_type="sales_lead",
        action_type="create",
        summary=success_text,
        details={
            "restaurant_name": payload.get("restaurant_name"),
            "status": payload.get("status"),
            "lead_source": payload.get("lead_source"),
        },
    )
    return success_text


def update_sales_lead_and_commit(conn, *, lead_id: int, sales_values: dict[str, Any], actor_role: str = "admin") -> str:
    require_action_access(actor_role, "sales.update")
    payload = dict(sales_values)
    payload["updated_at"] = _utc_now_iso()
    try:
        update_sales_lead_record(conn, lead_id, payload)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = "Satış fırsatı başarıyla güncellendi."
    record_audit_event(
        conn,
        entity_type="sales_lead",
        entity_id=lead_id,
        action_type="update",
        summary=success_text,
        details={
            "restaurant_name": payload.get("restaurant_name"),
            "status": payload.get("status"),
            "lead_source": payload.get("lead_source"),
        },
    )
    return success_text


def delete_sales_lead_and_commit(conn, *, lead_id: int, actor_role: str = "admin") -> str:
    require_action_access(actor_role, "sales.delete")
    try:
        delete_sales_lead_record(conn, lead_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    success_text = "Satış fırsatı silindi."
    record_audit_event(
        conn,
        entity_type="sales_lead",
        entity_id=lead_id,
        action_type="delete",
        summary=success_text,
    )
    return success_text
