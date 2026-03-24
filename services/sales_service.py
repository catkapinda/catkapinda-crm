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
    pricing_model_value: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _format_compact_currency(value: Any) -> str:
    try:
        amount = float(value or 0.0)
    except Exception:
        amount = 0.0
    if abs(amount - round(amount)) < 0.005:
        return f"{int(round(amount)):,}₺".replace(",", ".")
    return f"{amount:,.2f}₺".replace(",", "X").replace(".", ",").replace("X", ".")


def infer_sales_pricing_model(pricing_model: Any, pricing_model_hint: Any = None) -> str:
    model_text = str(pricing_model or "").strip()
    if model_text in {"hourly_plus_package", "threshold_package", "fixed_monthly", "hourly_only"}:
        return model_text

    hint_text = str(pricing_model_hint or "").strip().lower()
    if not hint_text:
        return "hourly_plus_package"
    if "390" in hint_text or "altı" in hint_text or "üstü" in hint_text:
        return "threshold_package"
    if "aylık" in hint_text or "/ay" in hint_text:
        return "fixed_monthly"
    if "paket" in hint_text:
        return "hourly_plus_package"
    if "saat" in hint_text:
        return "hourly_only"
    return "hourly_plus_package"


def build_sales_pricing_summary(
    *,
    pricing_model: str,
    hourly_rate: float,
    package_rate: float,
    package_threshold: int,
    package_rate_low: float,
    package_rate_high: float,
    fixed_monthly_fee: float,
) -> str:
    if pricing_model == "threshold_package":
        threshold_value = package_threshold if int(package_threshold or 0) > 0 else 390
        return (
            f"{_format_compact_currency(hourly_rate)}/saat | "
            f"{threshold_value} altı {_format_compact_currency(package_rate_low)} | "
            f"üstü {_format_compact_currency(package_rate_high)}"
        )
    if pricing_model == "hourly_plus_package":
        return f"{_format_compact_currency(hourly_rate)}/saat + {_format_compact_currency(package_rate)}/paket"
    if pricing_model == "hourly_only":
        return f"{_format_compact_currency(hourly_rate)}/saat"
    if pricing_model == "fixed_monthly":
        return f"{_format_compact_currency(fixed_monthly_fee)}/ay"
    return ""


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
            "pricing_model": "",
            "hourly_rate": 0.0,
            "package_rate": 0.0,
            "package_threshold": 390,
            "package_rate_low": 0.0,
            "package_rate_high": 0.0,
            "fixed_monthly_fee": 0.0,
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
    pricing_model: str,
    hourly_rate: float,
    package_rate: float,
    package_threshold: int,
    package_rate_low: float,
    package_rate_high: float,
    fixed_monthly_fee: float,
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
    if pricing_model == "hourly_plus_package":
        if float(hourly_rate or 0) <= 0:
            errors.append("Hacimsiz primli teklifte saatlik ücret zorunlu.")
        if float(package_rate or 0) <= 0:
            errors.append("Hacimsiz primli teklifte paket primi zorunlu.")
    elif pricing_model == "threshold_package":
        if float(hourly_rate or 0) <= 0:
            errors.append("Hacimli primli teklifte saatlik ücret zorunlu.")
        if int(package_threshold or 0) <= 0:
            errors.append("Hacimli primli teklifte paket eşiği zorunlu.")
        if float(package_rate_low or 0) <= 0:
            errors.append("Hacimli primli teklifte eşik altı prim zorunlu.")
        if float(package_rate_high or 0) <= 0:
            errors.append("Hacimli primli teklifte eşik üstü prim zorunlu.")
    elif pricing_model == "hourly_only":
        if float(hourly_rate or 0) <= 0:
            errors.append("Sadece saatlik teklifte saatlik ücret zorunlu.")
    elif pricing_model == "fixed_monthly":
        if float(fixed_monthly_fee or 0) <= 0:
            errors.append("Sabit aylık ücretli teklifte aylık tutar zorunlu.")
    else:
        errors.append("Geçerli bir teklif modeli seçmelisin.")
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
    current_pricing_model = infer_sales_pricing_model(row.get("pricing_model"), row.get("pricing_model_hint"))
    status_index = status_options.index(current_status) if current_status in status_options else 0
    source_index = source_options.index(current_source) if current_source in source_options else 0
    return SalesSelectionPayload(
        row=row,
        status_index=status_index,
        source_index=source_index,
        pricing_model_value=current_pricing_model,
    )


def create_sales_lead_and_commit(conn, *, sales_values: dict[str, Any], actor_role: str = "admin") -> str:
    require_action_access(actor_role, "sales.create")
    payload = dict(sales_values)
    pricing_model = infer_sales_pricing_model(payload.get("pricing_model"), payload.get("pricing_model_hint"))
    payload["pricing_model"] = pricing_model
    payload["pricing_model_hint"] = build_sales_pricing_summary(
        pricing_model=pricing_model,
        hourly_rate=float(payload.get("hourly_rate") or 0.0),
        package_rate=float(payload.get("package_rate") or 0.0),
        package_threshold=int(payload.get("package_threshold") or 0),
        package_rate_low=float(payload.get("package_rate_low") or 0.0),
        package_rate_high=float(payload.get("package_rate_high") or 0.0),
        fixed_monthly_fee=float(payload.get("fixed_monthly_fee") or 0.0),
    )
    if pricing_model == "fixed_monthly":
        payload["proposed_quote"] = float(payload.get("fixed_monthly_fee") or 0.0)
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
            "pricing_model": payload.get("pricing_model"),
        },
    )
    return success_text


def update_sales_lead_and_commit(conn, *, lead_id: int, sales_values: dict[str, Any], actor_role: str = "admin") -> str:
    require_action_access(actor_role, "sales.update")
    payload = dict(sales_values)
    pricing_model = infer_sales_pricing_model(payload.get("pricing_model"), payload.get("pricing_model_hint"))
    payload["pricing_model"] = pricing_model
    payload["pricing_model_hint"] = build_sales_pricing_summary(
        pricing_model=pricing_model,
        hourly_rate=float(payload.get("hourly_rate") or 0.0),
        package_rate=float(payload.get("package_rate") or 0.0),
        package_threshold=int(payload.get("package_threshold") or 0),
        package_rate_low=float(payload.get("package_rate_low") or 0.0),
        package_rate_high=float(payload.get("package_rate_high") or 0.0),
        fixed_monthly_fee=float(payload.get("fixed_monthly_fee") or 0.0),
    )
    if pricing_model == "fixed_monthly":
        payload["proposed_quote"] = float(payload.get("fixed_monthly_fee") or 0.0)
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
            "pricing_model": payload.get("pricing_model"),
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
