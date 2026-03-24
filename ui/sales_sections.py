from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd
import streamlit as st


def _resolve_sales_offer_text(row: Any, *, fmt_try_fn: Callable[[Any], str]) -> str:
    pricing_summary = str(row.get("pricing_model_hint") or "").strip()
    if pricing_summary:
        return pricing_summary
    proposed_quote = row.get("proposed_quote")
    if proposed_quote in [None, ""]:
        return "-"
    return fmt_try_fn(proposed_quote)


def _build_sales_snapshot_items(
    row: Any,
    *,
    fmt_try_fn: Callable[[Any], str],
    safe_int_fn: Callable[[Any, int], int],
) -> list[tuple[str, Any]]:
    location = " / ".join(part for part in [str(row.get("city") or "").strip(), str(row.get("district") or "").strip()] if part)
    return [
        ("Restoran", row.get("restaurant_name") or "-"),
        ("Konum", location or "-"),
        ("Durum", row.get("status") or "-"),
        ("Talep", f"{safe_int_fn(row.get('requested_courier_count'), 0)} kurye"),
        ("Yetkili", row.get("contact_name") or "-"),
        ("Telefon", row.get("contact_phone") or "-"),
        ("Kaynak", row.get("lead_source") or "-"),
        ("Teklif", _resolve_sales_offer_text(row, fmt_try_fn=fmt_try_fn)),
    ]


def _build_sales_rows(filtered_df: pd.DataFrame, *, safe_int_fn: Callable[[Any, int], int], fmt_try_fn: Callable[[Any], str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if filtered_df is None or filtered_df.empty:
        return rows
    for _, row in filtered_df.iterrows():
        location = " / ".join(part for part in [str(row.get("city") or "").strip(), str(row.get("district") or "").strip()] if part)
        rows.append(
            {
                "Restoran": row.get("restaurant_name") or "-",
                "Konum": location or "-",
                "Yetkili": row.get("contact_name") or "-",
                "Talep": f"{safe_int_fn(row.get('requested_courier_count'), 0)} kurye",
                "Kaynak": row.get("lead_source") or "-",
                "Teklif": _resolve_sales_offer_text(row, fmt_try_fn=fmt_try_fn),
                "Durum": row.get("status") or "-",
                "Takip": row.get("next_follow_up_date") or "-",
            }
        )
    return rows


def _render_sales_pricing_fields(
    *,
    pricing_model: str,
    render_field_label_fn: Callable[[str, bool], None],
    safe_float_fn: Callable[[Any, float], float] | None = None,
    safe_int_fn: Callable[[Any, int], int] | None = None,
    row: Any | None = None,
) -> tuple[float, float, int, float, float, float]:
    hourly_rate = 0.0
    package_rate = 0.0
    package_threshold = 390
    package_rate_low = 0.0
    package_rate_high = 0.0
    fixed_fee = 0.0

    if pricing_model == "hourly_plus_package":
        p1, p2 = st.columns(2)
        with p1:
            render_field_label_fn("Saatlik Ücret", required=True)
            hourly_rate = st.number_input(
                "Saatlik Ücret",
                min_value=0.0,
                value=safe_float_fn(row.get("hourly_rate"), 0.0) if row is not None and safe_float_fn else 0.0,
                step=1.0,
                label_visibility="collapsed",
            )
        with p2:
            render_field_label_fn("Paket Primi", required=True)
            package_rate = st.number_input(
                "Paket Primi",
                min_value=0.0,
                value=safe_float_fn(row.get("package_rate"), 0.0) if row is not None and safe_float_fn else 0.0,
                step=0.25,
                label_visibility="collapsed",
            )
    elif pricing_model == "threshold_package":
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            render_field_label_fn("Saatlik Ücret", required=True)
            hourly_rate = st.number_input(
                "Saatlik Ücret",
                min_value=0.0,
                value=safe_float_fn(row.get("hourly_rate"), 0.0) if row is not None and safe_float_fn else 0.0,
                step=1.0,
                label_visibility="collapsed",
            )
        with p2:
            render_field_label_fn("Paket Eşiği", required=True)
            package_threshold = st.number_input(
                "Paket Eşiği",
                min_value=0,
                value=safe_int_fn(row.get("package_threshold"), 390) if row is not None and safe_int_fn else 390,
                step=1,
                label_visibility="collapsed",
            )
        with p3:
            render_field_label_fn("390 Altı Prim", required=True)
            package_rate_low = st.number_input(
                "390 Altı Prim",
                min_value=0.0,
                value=safe_float_fn(row.get("package_rate_low"), 0.0) if row is not None and safe_float_fn else 0.0,
                step=0.25,
                label_visibility="collapsed",
            )
        with p4:
            render_field_label_fn("390 Üstü Prim", required=True)
            package_rate_high = st.number_input(
                "390 Üstü Prim",
                min_value=0.0,
                value=safe_float_fn(row.get("package_rate_high"), 0.0) if row is not None and safe_float_fn else 0.0,
                step=0.25,
                label_visibility="collapsed",
            )
    elif pricing_model == "hourly_only":
        render_field_label_fn("Saatlik Ücret", required=True)
        hourly_rate = st.number_input(
            "Saatlik Ücret",
            min_value=0.0,
            value=safe_float_fn(row.get("hourly_rate"), 0.0) if row is not None and safe_float_fn else 0.0,
            step=1.0,
            label_visibility="collapsed",
        )
    elif pricing_model == "fixed_monthly":
        render_field_label_fn("Sabit Aylık Ücret", required=True)
        fixed_fee = st.number_input(
            "Sabit Aylık Ücret",
            min_value=0.0,
            value=safe_float_fn(row.get("fixed_monthly_fee"), 0.0) if row is not None and safe_float_fn else 0.0,
            step=100.0,
            label_visibility="collapsed",
        )

    return hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_fee


def render_sales_list_workspace(
    df: pd.DataFrame,
    *,
    status_options: list[str],
    source_options: list[str],
    safe_int_fn: Callable[[Any, int], int],
    fmt_try_fn: Callable[[Any], str],
    apply_text_search_fn: Callable[[pd.DataFrame, list[str], str], pd.DataFrame],
    render_tab_header_fn: Callable[[str, str], None],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    set_flash_message_fn: Callable[[str, str], None],
    delete_sales_lead_and_commit_fn: Callable[..., str],
    can_delete_sales: bool,
) -> None:
    render_tab_header_fn("Gelen Fırsatlar", "Yeni restoran taleplerini kaynak, teklif ve takip durumu ile birlikte tek listede yönet.")
    f1, f2, f3 = st.columns([2.2, 1.2, 1.2])
    search_query = f1.text_input("Ara", placeholder="Restoran, yetkili, telefon veya ilçe ara", key="sales_search")
    status_filter = f2.selectbox("Durum", ["Tümü", *status_options], key="sales_status_filter")
    source_filter = f3.selectbox("Talep Yeri", ["Tümü", *source_options], key="sales_source_filter")

    filtered_df = df.copy()
    if status_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["status"] == status_filter].copy()
    if source_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["lead_source"] == source_filter].copy()
    filtered_df = apply_text_search_fn(
        filtered_df,
        ["restaurant_name", "city", "district", "contact_name", "contact_phone", "contact_email", "address", "assigned_owner"],
        search_query,
    )

    if df.empty:
        st.info("Henüz satış fırsatı yok.")
        return

    options = {f"{row['restaurant_name']} | {row['city']} / {row['district']} | ID:{row['id']}": int(row["id"]) for _, row in df.iterrows()}
    left, right = st.columns([2.35, 1])
    with left:
        render_dashboard_data_grid_fn(
            "Satış Fırsatları",
            "Talep, teklif ve takip tarihlerini temiz satırlarda izle.",
            ["Restoran", "Konum", "Yetkili", "Talep", "Kaynak", "Teklif", "Durum", "Takip"],
            _build_sales_rows(filtered_df, safe_int_fn=safe_int_fn, fmt_try_fn=fmt_try_fn),
            "Filtreye uyan satış fırsatı görünmüyor.",
            badge_columns={"Durum"},
            muted_columns={"Konum", "Kaynak", "Takip"},
        )
        st.caption(f"{len(filtered_df)} satış fırsatı gösteriliyor.")
    with right:
        selected_label = st.selectbox("İşlem Yapılacak Fırsat", list(options.keys()), key="sales_action_select")
        selected_id = options[selected_label]
        selected_row = df.loc[df["id"] == selected_id].iloc[0]
        render_record_snapshot_fn(
            "Seçili Fırsat",
            _build_sales_snapshot_items(selected_row, fmt_try_fn=fmt_try_fn, safe_int_fn=safe_int_fn),
        )
        if st.button("Fırsatı Sil", use_container_width=True, key="sales_delete_btn", disabled=not can_delete_sales):
            try:
                success_message = delete_sales_lead_and_commit_fn(lead_id=selected_id)
            except Exception as exc:
                st.error(f"Satış fırsatı silinemedi: {exc}")
            else:
                set_flash_message_fn("success", success_message)
                st.rerun()
        if not can_delete_sales:
            st.caption("Silme yetkine sahip değilsin.")


def render_sales_add_workspace(
    *,
    can_create_sales: bool,
    status_options: list[str],
    source_options: list[str],
    pricing_model_labels: dict[str, str],
    render_tab_header_fn: Callable[[str, str], None],
    render_field_label_fn: Callable[[str, bool], None],
    validate_sales_lead_values_fn: Callable[..., list[str]],
    create_sales_lead_and_commit_fn: Callable[..., str],
    set_flash_message_fn: Callable[[str, str], None],
) -> None:
    render_tab_header_fn("Yeni Fırsat Ekle", "Talep kanalını, yetkili bilgilerini ve önerilen teklifi aynı kartta kaydet.")
    c1, c2 = st.columns(2)
    with c1:
        render_field_label_fn("Restoran Adı", required=True)
        restaurant_name = st.text_input("Restoran Adı", label_visibility="collapsed")
    with c2:
        render_field_label_fn("Talep Yeri", required=True)
        lead_source = st.selectbox("Talep Yeri", source_options, label_visibility="collapsed")

    c3, c4, c5 = st.columns(3)
    with c3:
        render_field_label_fn("İl", required=True)
        city = st.text_input("İl", label_visibility="collapsed")
    with c4:
        render_field_label_fn("İlçe", required=True)
        district = st.text_input("İlçe", label_visibility="collapsed")
    with c5:
        render_field_label_fn("Talep Edilen Kurye Sayısı")
        requested_courier_count = st.number_input("Talep Edilen Kurye Sayısı", min_value=0, value=0, step=1, label_visibility="collapsed")

    render_field_label_fn("Adres")
    address = st.text_area("Adres", label_visibility="collapsed")

    c6, c7, c8 = st.columns(3)
    with c6:
        render_field_label_fn("Yetkili", required=True)
        contact_name = st.text_input("Yetkili", label_visibility="collapsed")
    with c7:
        render_field_label_fn("Yetkili Telefon", required=True)
        contact_phone = st.text_input("Yetkili Telefon", label_visibility="collapsed")
    with c8:
        render_field_label_fn("Mail")
        contact_email = st.text_input("Mail", label_visibility="collapsed")

    c9, c10, c11 = st.columns(3)
    with c9:
        render_field_label_fn("Teklif Modeli")
        pricing_model = st.selectbox(
            "Teklif Modeli",
            list(pricing_model_labels.keys()),
            format_func=lambda value: pricing_model_labels.get(value, value),
            label_visibility="collapsed",
        )
    with c10:
        render_field_label_fn("Durum", required=True)
        status = st.selectbox("Durum", status_options, label_visibility="collapsed")
    with c11:
        render_field_label_fn("Takip Tarihi")
        next_follow_up_date = st.date_input("Takip Tarihi", value=None, label_visibility="collapsed")

    hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee = _render_sales_pricing_fields(
        pricing_model=pricing_model,
        render_field_label_fn=render_field_label_fn,
    )

    c13, c14 = st.columns(2)
    with c13:
        render_field_label_fn("İlgilenen Kişi")
        assigned_owner = st.text_input("İlgilenen Kişi", label_visibility="collapsed")
    with c14:
        render_field_label_fn("Notlar")
        notes = st.text_area("Notlar", label_visibility="collapsed")

    if not can_create_sales:
        st.caption("Satış fırsatı oluşturma yetkin yok.")
    if not st.button("Satış Fırsatını Oluştur", use_container_width=True, key="sales_create_btn", disabled=not can_create_sales):
        return

    validation_errors = validate_sales_lead_values_fn(
        restaurant_name=restaurant_name,
        city=city,
        district=district,
        contact_name=contact_name,
        contact_phone=contact_phone,
        status=status,
        pricing_model=pricing_model,
        hourly_rate=hourly_rate,
        package_rate=package_rate,
        package_threshold=package_threshold,
        package_rate_low=package_rate_low,
        package_rate_high=package_rate_high,
        fixed_monthly_fee=fixed_monthly_fee,
    )
    if validation_errors:
        for error_text in validation_errors:
            st.error(error_text)
        return

    try:
        success_message = create_sales_lead_and_commit_fn(
            sales_values={
                "restaurant_name": restaurant_name,
                "city": city,
                "district": district,
                "address": address,
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
                "requested_courier_count": requested_courier_count,
                "lead_source": lead_source,
                "proposed_quote": 0.0,
                "pricing_model": pricing_model,
                "hourly_rate": hourly_rate,
                "package_rate": package_rate,
                "package_threshold": package_threshold,
                "package_rate_low": package_rate_low,
                "package_rate_high": package_rate_high,
                "fixed_monthly_fee": fixed_monthly_fee,
                "pricing_model_hint": "",
                "status": status,
                "next_follow_up_date": next_follow_up_date.isoformat() if isinstance(next_follow_up_date, date) else "",
                "assigned_owner": assigned_owner,
                "notes": notes,
            }
        )
    except Exception as exc:
        st.error(f"Satış fırsatı kaydedilemedi: {exc}")
    else:
        set_flash_message_fn("success", success_message)
        st.rerun()


def render_sales_edit_workspace(
    df: pd.DataFrame,
    *,
    can_update_sales: bool,
    status_options: list[str],
    source_options: list[str],
    pricing_model_labels: dict[str, str],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    fmt_try_fn: Callable[[Any], str],
    parse_date_value_fn: Callable[[Any], date | None],
    render_tab_header_fn: Callable[[str, str], None],
    render_field_label_fn: Callable[[str, bool], None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    build_sales_selection_payload_fn: Callable[..., Any],
    validate_sales_lead_values_fn: Callable[..., list[str]],
    update_sales_lead_and_commit_fn: Callable[..., str],
    set_flash_message_fn: Callable[[str, str], None],
) -> None:
    render_tab_header_fn("Fırsatı Güncelle", "Teklif, durum ve takip bilgisini seçili satış fırsatı üzerinden güncelle.")
    if df.empty:
        st.info("Güncellenecek satış fırsatı yok.")
        return

    option_map = {f"{row['restaurant_name']} | {row['city']} / {row['district']} | ID:{row['id']}": int(row["id"]) for _, row in df.iterrows()}
    selected_label = st.selectbox("Güncellenecek Fırsat", list(option_map.keys()), key="sales_edit_select")
    selected_id = option_map[selected_label]
    selection_payload = build_sales_selection_payload_fn(df, selected_id=selected_id, status_options=status_options, source_options=source_options)
    row = selection_payload.row
    render_record_snapshot_fn(
        "Mevcut Fırsat",
        _build_sales_snapshot_items(row, fmt_try_fn=fmt_try_fn, safe_int_fn=safe_int_fn),
    )

    c1, c2 = st.columns(2)
    with c1:
        render_field_label_fn("Restoran Adı", required=True)
        restaurant_name = st.text_input("Restoran Adı", value=row.get("restaurant_name") or "", label_visibility="collapsed")
    with c2:
        render_field_label_fn("Talep Yeri", required=True)
        lead_source = st.selectbox("Talep Yeri", source_options, index=selection_payload.source_index, label_visibility="collapsed")

    c3, c4, c5 = st.columns(3)
    with c3:
        render_field_label_fn("İl", required=True)
        city = st.text_input("İl", value=row.get("city") or "", label_visibility="collapsed")
    with c4:
        render_field_label_fn("İlçe", required=True)
        district = st.text_input("İlçe", value=row.get("district") or "", label_visibility="collapsed")
    with c5:
        render_field_label_fn("Talep Edilen Kurye Sayısı")
        requested_courier_count = st.number_input(
            "Talep Edilen Kurye Sayısı",
            min_value=0,
            value=max(safe_int_fn(row.get("requested_courier_count"), 0), 0),
            step=1,
            label_visibility="collapsed",
        )

    render_field_label_fn("Adres")
    address = st.text_area("Adres", value=row.get("address") or "", label_visibility="collapsed")

    c6, c7, c8 = st.columns(3)
    with c6:
        render_field_label_fn("Yetkili", required=True)
        contact_name = st.text_input("Yetkili", value=row.get("contact_name") or "", label_visibility="collapsed")
    with c7:
        render_field_label_fn("Yetkili Telefon", required=True)
        contact_phone = st.text_input("Yetkili Telefon", value=row.get("contact_phone") or "", label_visibility="collapsed")
    with c8:
        render_field_label_fn("Mail")
        contact_email = st.text_input("Mail", value=row.get("contact_email") or "", label_visibility="collapsed")

    c9, c10, c11, c12 = st.columns(4)
    with c9:
        render_field_label_fn("Teklif Modeli")
        pricing_model = st.selectbox(
            "Teklif Modeli",
            list(pricing_model_labels.keys()),
            index=list(pricing_model_labels.keys()).index(selection_payload.pricing_model_value)
            if selection_payload.pricing_model_value in pricing_model_labels
            else 0,
            format_func=lambda value: pricing_model_labels.get(value, value),
            label_visibility="collapsed",
        )
    with c10:
        render_field_label_fn("Durum", required=True)
        status = st.selectbox("Durum", status_options, index=selection_payload.status_index, label_visibility="collapsed")
    with c11:
        render_field_label_fn("Takip Tarihi")
        next_follow_up_date = st.date_input(
            "Takip Tarihi",
            value=parse_date_value_fn(row.get("next_follow_up_date")),
            label_visibility="collapsed",
        )

    hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee = _render_sales_pricing_fields(
        pricing_model=pricing_model,
        render_field_label_fn=render_field_label_fn,
        safe_float_fn=safe_float_fn,
        safe_int_fn=safe_int_fn,
        row=row,
    )

    c13, c14 = st.columns(2)
    with c13:
        render_field_label_fn("İlgilenen Kişi")
        assigned_owner = st.text_input("İlgilenen Kişi", value=row.get("assigned_owner") or "", label_visibility="collapsed")
    with c14:
        render_field_label_fn("Notlar")
        notes = st.text_area("Notlar", value=row.get("notes") or "", label_visibility="collapsed")

    if not can_update_sales:
        st.caption("Satış fırsatı güncelleme yetkin yok.")
    if not st.button("Fırsatı Güncelle", use_container_width=True, key="sales_update_btn", disabled=not can_update_sales):
        return

    validation_errors = validate_sales_lead_values_fn(
        restaurant_name=restaurant_name,
        city=city,
        district=district,
        contact_name=contact_name,
        contact_phone=contact_phone,
        status=status,
        pricing_model=pricing_model,
        hourly_rate=hourly_rate,
        package_rate=package_rate,
        package_threshold=package_threshold,
        package_rate_low=package_rate_low,
        package_rate_high=package_rate_high,
        fixed_monthly_fee=fixed_monthly_fee,
    )
    if validation_errors:
        for error_text in validation_errors:
            st.error(error_text)
        return

    try:
        success_message = update_sales_lead_and_commit_fn(
            lead_id=selected_id,
            sales_values={
                "restaurant_name": restaurant_name,
                "city": city,
                "district": district,
                "address": address,
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
                "requested_courier_count": requested_courier_count,
                "lead_source": lead_source,
                "proposed_quote": 0.0,
                "pricing_model": pricing_model,
                "hourly_rate": hourly_rate,
                "package_rate": package_rate,
                "package_threshold": package_threshold,
                "package_rate_low": package_rate_low,
                "package_rate_high": package_rate_high,
                "fixed_monthly_fee": fixed_monthly_fee,
                "pricing_model_hint": "",
                "status": status,
                "next_follow_up_date": next_follow_up_date.isoformat() if isinstance(next_follow_up_date, date) else "",
                "assigned_owner": assigned_owner,
                "notes": notes,
            },
        )
    except Exception as exc:
        st.error(f"Satış fırsatı güncellenemedi: {exc}")
    else:
        set_flash_message_fn("success", success_message)
        st.rerun()
