from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st


def render_restaurant_list_workspace(
    conn: Any,
    df: pd.DataFrame,
    *,
    can_toggle_restaurant_status: bool,
    can_delete_restaurant: bool,
    pricing_model_labels: dict[str, str],
    active_status_labels: dict[Any, str],
    safe_int_fn: Callable[[Any, int], int],
    fmt_number_fn: Callable[[Any], str],
    apply_text_search_fn: Callable[[pd.DataFrame, list[str], str], pd.DataFrame],
    build_restaurant_list_rows_fn: Callable[..., list[dict[str, Any]]],
    build_restaurant_snapshot_items_fn: Callable[..., list[tuple[str, Any]]],
    render_tab_header_fn: Callable[[str, str], None],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    set_flash_message_fn: Callable[[str, str], None],
    toggle_restaurant_status_and_commit_fn: Callable[..., str],
    delete_restaurant_with_guards_fn: Callable[..., str],
) -> None:
    render_tab_header_fn("Şube Listesi", "Marka, fiyat modeli ve durum filtresi ile kayıtları daralt; sağ panelden seçili şube üzerinde hızlı işlem yap.")
    f1, f2, f3, f4 = st.columns([2.2, 1, 1.2, 1])
    search_query = f1.text_input("Ara", placeholder="Marka, şube veya yetkili adı ara", key="restaurant_search")
    brand_options = ["Tümü"] + sorted(df["brand"].dropna().astype(str).unique().tolist()) if not df.empty else ["Tümü"]
    brand_filter = f2.selectbox("Marka", brand_options, key="restaurant_brand_filter")
    model_filter = f3.selectbox(
        "Fiyat Modeli",
        ["Tümü"] + list(pricing_model_labels.keys()),
        format_func=lambda x: "Tümü" if x == "Tümü" else pricing_model_labels.get(x, x),
        key="restaurant_model_filter",
    )
    status_filter = f4.selectbox("Durum", ["Tümü", "Aktif", "Pasif"], key="restaurant_status_filter")

    filtered_df = df.copy()
    if brand_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["brand"] == brand_filter].copy()
    if model_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["pricing_model"] == model_filter].copy()
    if status_filter != "Tümü":
        wanted = 1 if status_filter == "Aktif" else 0
        filtered_df = filtered_df[filtered_df["active"].apply(lambda x: safe_int_fn(x, 0)) == wanted].copy()
    filtered_df = apply_text_search_fn(filtered_df, ["brand", "branch", "contact_name", "contact_phone", "company_title", "address"], search_query)

    if df.empty:
        st.info("Henüz kayıtlı restoran yok.")
        return

    action_labels = {f"{row['brand']} - {row['branch']} (ID: {row['id']})": int(row["id"]) for _, row in df.iterrows()}
    left, right = st.columns([2.35, 1])
    with left:
        restaurant_rows = build_restaurant_list_rows_fn(
            filtered_df,
            pricing_model_labels=pricing_model_labels,
            active_status_labels=active_status_labels,
            fmt_number_fn=fmt_number_fn,
        )
        render_dashboard_data_grid_fn(
            "Şube Kartları",
            "Marka, fiyat modeli ve yönetim bilgisini daha okunur kart satırlarında izle.",
            ["Şube", "Fiyat Modeli", "Kadro", "Yetkili", "Durum"],
            restaurant_rows,
            "Filtreye uyan restoran kaydı görünmüyor.",
            badge_columns={"Durum"},
            muted_columns={"Fiyat Modeli"},
        )
        st.caption(f"{len(filtered_df)} kayıt gösteriliyor.")
    with right:
        selected_label = st.selectbox("İşlem Yapılacak Şube", list(action_labels.keys()), key="restaurant_action_select")
        selected_id = action_labels[selected_label]
        selected_row = df.loc[df["id"] == selected_id].iloc[0]
        render_record_snapshot_fn(
            "Seçili Şube",
            build_restaurant_snapshot_items_fn(
                selected_row,
                pricing_model_labels=pricing_model_labels,
                active_status_labels=active_status_labels,
                safe_int_fn=safe_int_fn,
            ),
        )
        st.markdown("##### Hızlı Aksiyonlar")
        b1, b2 = st.columns(2)
        current_active = safe_int_fn(selected_row["active"], 1)
        if b1.button(
            "Pasife Al" if current_active == 1 else "Aktifleştir",
            use_container_width=True,
            key="restaurant_toggle_btn",
            disabled=not can_toggle_restaurant_status,
        ):
            try:
                success_message = toggle_restaurant_status_and_commit_fn(conn, restaurant_id=selected_id, current_active=current_active)
            except Exception as exc:
                st.error(f"Restoran durumu güncellenemedi: {exc}")
            else:
                set_flash_message_fn("success", success_message)
                st.rerun()
        if b2.button(
            "Kalıcı Sil",
            use_container_width=True,
            key="restaurant_delete_btn",
            disabled=not can_delete_restaurant,
        ):
            try:
                success_message = delete_restaurant_with_guards_fn(conn, restaurant_id=selected_id)
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Restoran silinemedi: {exc}")
            else:
                set_flash_message_fn("success", success_message)
                st.rerun()
        if not can_toggle_restaurant_status or not can_delete_restaurant:
            st.caption("Yetkine gore bazi hizli aksiyonlar pasif.")
        st.caption("Kalıcı silme işlemi yalnızca test veya yanlış açılmış kayıtlar için kullanılmalı.")


def _render_pricing_fields(
    *,
    pricing_model: str,
    render_field_label_fn: Callable[[str, bool], None],
    safe_float_fn: Callable[[Any, float], float] | None = None,
    safe_int_fn: Callable[[Any, int], int] | None = None,
    row: Any | None = None,
) -> tuple[float, float, int, float, float, float]:
    hourly_rate = 0.0
    package_rate = 0.0
    package_threshold = 0
    package_rate_low = 0.0
    package_rate_high = 0.0
    fixed_fee = 0.0

    if pricing_model == "hourly_plus_package":
        c1, c2 = st.columns(2)
        with c1:
            render_field_label_fn("Saatlik Ücret", required=True)
            hourly_rate = st.number_input(
                "Saatlik Ücret",
                min_value=0.0,
                value=safe_float_fn(row["hourly_rate"]) if row is not None and safe_float_fn else 0.0,
                step=1.0,
                label_visibility="collapsed",
            )
        with c2:
            render_field_label_fn("Paket Primi", required=True)
            package_rate = st.number_input(
                "Paket Primi",
                min_value=0.0,
                value=safe_float_fn(row["package_rate"]) if row is not None and safe_float_fn else 0.0,
                step=1.0,
                label_visibility="collapsed",
            )
    elif pricing_model == "threshold_package":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_field_label_fn("Saatlik Ücret", required=True)
            hourly_rate = st.number_input(
                "Saatlik Ücret",
                min_value=0.0,
                value=safe_float_fn(row["hourly_rate"]) if row is not None and safe_float_fn else 0.0,
                step=1.0,
                label_visibility="collapsed",
            )
        with c2:
            render_field_label_fn("Paket Eşiği", required=True)
            package_threshold = st.number_input(
                "Paket Eşiği",
                min_value=0,
                value=safe_int_fn(row["package_threshold"], 390) if row is not None and safe_int_fn else 390,
                step=1,
                label_visibility="collapsed",
            )
        with c3:
            render_field_label_fn("Eşik Altı Prim", required=True)
            package_rate_low = st.number_input(
                "Eşik Altı Prim",
                min_value=0.0,
                value=safe_float_fn(row["package_rate_low"]) if row is not None and safe_float_fn else 0.0,
                step=0.25,
                label_visibility="collapsed",
            )
        with c4:
            render_field_label_fn("Eşik Üstü Prim", required=True)
            package_rate_high = st.number_input(
                "Eşik Üstü Prim",
                min_value=0.0,
                value=safe_float_fn(row["package_rate_high"]) if row is not None and safe_float_fn else 0.0,
                step=0.25,
                label_visibility="collapsed",
            )
    elif pricing_model == "hourly_only":
        render_field_label_fn("Saatlik Ücret", required=True)
        hourly_rate = st.number_input(
            "Saatlik Ücret",
            min_value=0.0,
            value=safe_float_fn(row["hourly_rate"]) if row is not None and safe_float_fn else 0.0,
            step=1.0,
            label_visibility="collapsed",
        )
    elif pricing_model == "fixed_monthly":
        render_field_label_fn("Sabit Aylık Ücret", required=True)
        fixed_fee = st.number_input(
            "Sabit Aylık Ücret",
            min_value=0.0,
            value=safe_float_fn(row["fixed_monthly_fee"]) if row is not None and safe_float_fn else 0.0,
            step=100.0,
            label_visibility="collapsed",
        )

    return hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_fee


def render_restaurant_add_workspace(
    conn: Any,
    *,
    can_create_restaurant: bool,
    pricing_model_labels: dict[str, str],
    render_tab_header_fn: Callable[[str, str], None],
    render_field_label_fn: Callable[[str, bool], None],
    validate_restaurant_form_fn: Callable[..., list[str]],
    set_flash_message_fn: Callable[[str, str], None],
    create_restaurant_and_commit_fn: Callable[..., str],
) -> None:
    render_tab_header_fn("Yeni Şube Kartı", "Temel bilgiler, fiyatlandırma, operasyon ve iletişim alanlarını daha düzenli bloklar halinde gir.")
    with st.container():
        st.markdown("##### Temel Bilgiler")
        c1, c2 = st.columns(2)
        with c1:
            render_field_label_fn("Marka", required=True)
            brand = st.text_input("Marka", label_visibility="collapsed")
        with c2:
            render_field_label_fn("Şube", required=True)
            branch = st.text_input("Şube", label_visibility="collapsed")

        st.markdown("##### Fiyatlandırma")
        c4, c5 = st.columns(2)
        with c4:
            render_field_label_fn("Fiyat Modeli", required=True)
            pricing_model = st.selectbox(
                "Fiyat Modeli",
                list(pricing_model_labels.keys()),
                format_func=lambda x: pricing_model_labels.get(x, x),
                label_visibility="collapsed",
            )
        with c5:
            render_field_label_fn("KDV %")
            vat_rate = st.number_input("KDV %", min_value=0.0, value=20.0, step=1.0, label_visibility="collapsed")

        hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_fee = _render_pricing_fields(
            pricing_model=pricing_model,
            render_field_label_fn=render_field_label_fn,
        )

        st.markdown("##### Operasyon ve Kadro")
        c12, c13, c14 = st.columns(3)
        with c12:
            render_field_label_fn("Hedef Kadro", required=True)
            headcount = st.number_input("Hedef Kadro", min_value=0, value=0, step=1, label_visibility="collapsed")
        with c13:
            render_field_label_fn("Başlangıç Tarihi", required=True)
            start_date_val = st.date_input("Başlangıç Tarihi", value=None, label_visibility="collapsed")
        with c14:
            render_field_label_fn("Bitiş Tarihi")
            end_date_val = st.date_input("Bitiş Tarihi", value=None, label_visibility="collapsed")

        c15, c16 = st.columns(2)
        extra_req = c15.number_input("Ek Kurye Talep Sayısı", min_value=0, value=0, step=1)
        extra_req_date = c16.date_input("Ek Kurye Talep Tarihi", value=None)

        c17, c18 = st.columns(2)
        reduce_req = c17.number_input("Kurye Azaltma Talep Sayısı", min_value=0, value=0, step=1)
        reduce_req_date = c18.date_input("Kurye Azaltma Talep Tarihi", value=None)

        st.markdown("##### İletişim ve Vergi")
        c19, c20, c21 = st.columns(3)
        with c19:
            render_field_label_fn("Yetkili Ad Soyad", required=True)
            contact_name = st.text_input("Yetkili Ad Soyad", label_visibility="collapsed")
        with c20:
            render_field_label_fn("Yetkili Telefon", required=True)
            contact_phone = st.text_input("Yetkili Telefon", label_visibility="collapsed")
        with c21:
            render_field_label_fn("Yetkili E-Posta", required=True)
            contact_email = st.text_input("Yetkili E-Posta", label_visibility="collapsed")

        c22, c23 = st.columns(2)
        with c22:
            render_field_label_fn("Ünvan")
            company_title = st.text_input("Ünvan", label_visibility="collapsed")
        with c23:
            render_field_label_fn("Adres")
            address = st.text_input("Adres", label_visibility="collapsed")

        c24, c25 = st.columns(2)
        with c24:
            render_field_label_fn("Vergi Dairesi", required=True)
            tax_office = st.text_input("Vergi Dairesi", label_visibility="collapsed")
        with c25:
            render_field_label_fn("Vergi Numarası", required=True)
            tax_number = st.text_input("Vergi Numarası", label_visibility="collapsed")

        notes = st.text_area("Notlar", placeholder="Şube içi önemli notlar, çalışma düzeni veya anlaşma detayı")
        if not can_create_restaurant:
            st.caption("Restoran olusturma yetkin olmadigi icin kaydetme butonu pasif.")
        submitted = st.button(
            "Şube Kartını Oluştur",
            use_container_width=True,
            key="restaurant_create_submit",
            disabled=not can_create_restaurant,
        )
        if not submitted:
            return

        validation_errors = validate_restaurant_form_fn(
            brand=brand,
            branch=branch,
            pricing_model=pricing_model,
            hourly_rate=hourly_rate,
            package_rate=package_rate,
            package_threshold=package_threshold,
            package_rate_low=package_rate_low,
            package_rate_high=package_rate_high,
            fixed_fee=fixed_fee,
            headcount=headcount,
            start_date_value=start_date_val if isinstance(start_date_val, date) else None,
            end_date_value=end_date_val if isinstance(end_date_val, date) else None,
            extra_req=extra_req,
            extra_req_date=extra_req_date if isinstance(extra_req_date, date) else None,
            reduce_req=reduce_req,
            reduce_req_date=reduce_req_date if isinstance(reduce_req_date, date) else None,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            company_title=company_title,
            address=address,
            tax_office=tax_office,
            tax_number=tax_number,
        )
        if validation_errors:
            for error_text in validation_errors:
                st.error(error_text)
            return

        try:
            success_message = create_restaurant_and_commit_fn(
                conn,
                restaurant_values={
                    "brand": brand,
                    "branch": branch,
                    "billing_group": None,
                    "pricing_model": pricing_model,
                    "hourly_rate": hourly_rate,
                    "package_rate": package_rate,
                    "package_threshold": package_threshold if pricing_model == "threshold_package" else None,
                    "package_rate_low": package_rate_low,
                    "package_rate_high": package_rate_high,
                    "fixed_monthly_fee": fixed_fee,
                    "vat_rate": vat_rate,
                    "target_headcount": headcount,
                    "start_date": start_date_val.isoformat() if isinstance(start_date_val, date) else None,
                    "end_date": end_date_val.isoformat() if isinstance(end_date_val, date) else None,
                    "extra_headcount_request": extra_req,
                    "extra_headcount_request_date": extra_req_date.isoformat() if isinstance(extra_req_date, date) else None,
                    "reduce_headcount_request": reduce_req,
                    "reduce_headcount_request_date": reduce_req_date.isoformat() if isinstance(reduce_req_date, date) else None,
                    "contact_name": contact_name,
                    "contact_phone": contact_phone,
                    "contact_email": contact_email,
                    "company_title": company_title,
                    "address": address,
                    "tax_office": tax_office,
                    "tax_number": tax_number,
                    "notes": notes,
                },
            )
        except Exception as exc:
            st.error(f"Restoran kartı oluşturulamadı: {exc}")
        else:
            set_flash_message_fn("success", success_message)
            st.rerun()


def render_restaurant_edit_workspace(
    conn: Any,
    df: pd.DataFrame,
    *,
    can_update_restaurant: bool,
    pricing_model_labels: dict[str, str],
    active_status_labels: dict[Any, str],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    validate_restaurant_form_fn: Callable[..., list[str]],
    render_tab_header_fn: Callable[[str, str], None],
    render_field_label_fn: Callable[[str, bool], None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    set_flash_message_fn: Callable[[str, str], None],
    update_restaurant_and_commit_fn: Callable[..., str],
) -> None:
    if df.empty:
        st.info("Güncellenecek restoran kaydı bulunmuyor.")
        return

    render_tab_header_fn("Şube Güncelleme", "Solda düzenleme formunu kullan, sağ tarafta mevcut şube kartının kısa özetini gör.")
    edit_labels = {f"{row['brand']} - {row['branch']} (ID: {row['id']})": int(row["id"]) for _, row in df.iterrows()}
    edit_selected_label = st.selectbox("Güncellenecek Şube", list(edit_labels.keys()), key="restaurant_edit_select")
    selected_id = edit_labels[edit_selected_label]
    selected_row = df.loc[df["id"] == selected_id].iloc[0]
    left, right = st.columns([2.2, 1])
    with right:
        render_record_snapshot_fn(
            "Mevcut Kart",
            [
                ("Durum", active_status_labels.get(selected_row["active"], selected_row["active"])),
                ("Başlangıç", selected_row["start_date"] or "-"),
                ("Ek Talep", safe_int_fn(selected_row["extra_headcount_request"])),
                ("Azaltma Talebi", safe_int_fn(selected_row["reduce_headcount_request"])),
            ],
        )
    with left:
        with st.container():
            st.markdown("##### Temel Bilgiler")
            c1, c2 = st.columns(2)
            with c1:
                render_field_label_fn("Marka", required=True)
                edit_brand = st.text_input("Marka", value=selected_row["brand"] or "", label_visibility="collapsed")
            with c2:
                render_field_label_fn("Şube", required=True)
                edit_branch = st.text_input("Şube", value=selected_row["branch"] or "", label_visibility="collapsed")

            st.markdown("##### Fiyatlandırma")
            pricing_options = list(pricing_model_labels.keys())
            current_pricing = selected_row["pricing_model"] if pd.notna(selected_row["pricing_model"]) and selected_row["pricing_model"] in pricing_options else pricing_options[0]
            c4, c5 = st.columns(2)
            with c4:
                render_field_label_fn("Fiyat Modeli", required=True)
                edit_pricing_model = st.selectbox(
                    "Fiyat Modeli",
                    pricing_options,
                    index=pricing_options.index(current_pricing),
                    format_func=lambda x: pricing_model_labels.get(x, x),
                    label_visibility="collapsed",
                )
            with c5:
                render_field_label_fn("KDV %")
                edit_vat_rate = st.number_input("KDV %", min_value=0.0, value=safe_float_fn(selected_row["vat_rate"], 20.0), step=1.0, label_visibility="collapsed")

            edit_hourly_rate, edit_package_rate, edit_package_threshold, edit_package_rate_low, edit_package_rate_high, edit_fixed_fee = _render_pricing_fields(
                pricing_model=edit_pricing_model,
                render_field_label_fn=render_field_label_fn,
                safe_float_fn=safe_float_fn,
                safe_int_fn=safe_int_fn,
                row=selected_row,
            )

            st.markdown("##### Operasyon ve Kadro")
            start_val = datetime.strptime(selected_row["start_date"], "%Y-%m-%d").date() if pd.notna(selected_row["start_date"]) and selected_row["start_date"] else None
            end_val = datetime.strptime(selected_row["end_date"], "%Y-%m-%d").date() if pd.notna(selected_row["end_date"]) and selected_row["end_date"] else None
            c12, c13, c14 = st.columns(3)
            with c12:
                render_field_label_fn("Hedef Kadro", required=True)
                edit_headcount = st.number_input("Hedef Kadro", min_value=0, value=safe_int_fn(selected_row["target_headcount"]), step=1, label_visibility="collapsed")
            with c13:
                render_field_label_fn("Başlangıç Tarihi", required=True)
                edit_start_date = st.date_input("Başlangıç Tarihi", value=start_val, label_visibility="collapsed")
            with c14:
                render_field_label_fn("Bitiş Tarihi")
                edit_end_date = st.date_input("Bitiş Tarihi", value=end_val, label_visibility="collapsed")

            extra_date_val = datetime.strptime(selected_row["extra_headcount_request_date"], "%Y-%m-%d").date() if pd.notna(selected_row["extra_headcount_request_date"]) and selected_row["extra_headcount_request_date"] else None
            reduce_date_val = datetime.strptime(selected_row["reduce_headcount_request_date"], "%Y-%m-%d").date() if pd.notna(selected_row["reduce_headcount_request_date"]) and selected_row["reduce_headcount_request_date"] else None
            c15, c16 = st.columns(2)
            edit_extra_req = c15.number_input("Ek Kurye Talep Sayısı", min_value=0, value=safe_int_fn(selected_row["extra_headcount_request"]), step=1)
            edit_extra_req_date = c16.date_input("Ek Kurye Talep Tarihi", value=extra_date_val)

            c17, c18 = st.columns(2)
            edit_reduce_req = c17.number_input("Kurye Azaltma Talep Sayısı", min_value=0, value=safe_int_fn(selected_row["reduce_headcount_request"]), step=1)
            edit_reduce_req_date = c18.date_input("Kurye Azaltma Talep Tarihi", value=reduce_date_val)

            st.markdown("##### İletişim ve Vergi")
            c19, c20, c21 = st.columns(3)
            with c19:
                render_field_label_fn("Yetkili Ad Soyad", required=True)
                edit_contact_name = st.text_input("Yetkili Ad Soyad", value=selected_row["contact_name"] or "", label_visibility="collapsed")
            with c20:
                render_field_label_fn("Yetkili Telefon", required=True)
                edit_contact_phone = st.text_input("Yetkili Telefon", value=selected_row["contact_phone"] or "", label_visibility="collapsed")
            with c21:
                render_field_label_fn("Yetkili E-Posta", required=True)
                edit_contact_email = st.text_input("Yetkili E-Posta", value=selected_row["contact_email"] or "", label_visibility="collapsed")

            c22, c23 = st.columns(2)
            with c22:
                render_field_label_fn("Ünvan")
                edit_company_title = st.text_input("Ünvan", value=selected_row["company_title"] or "", label_visibility="collapsed")
            with c23:
                render_field_label_fn("Adres")
                edit_address = st.text_input("Adres", value=selected_row["address"] or "", label_visibility="collapsed")

            c24, c25 = st.columns(2)
            with c24:
                render_field_label_fn("Vergi Dairesi", required=True)
                edit_tax_office = st.text_input("Vergi Dairesi", value=selected_row["tax_office"] or "", label_visibility="collapsed")
            with c25:
                render_field_label_fn("Vergi Numarası", required=True)
                edit_tax_number = st.text_input("Vergi Numarası", value=selected_row["tax_number"] or "", label_visibility="collapsed")

            edit_notes = st.text_area("Notlar", value=selected_row["notes"] or "")
            if not can_update_restaurant:
                st.caption("Restoran guncelleme yetkin olmadigi icin kaydetme butonu pasif.")
            submitted_edit = st.button(
                "Şube Kartını Güncelle",
                use_container_width=True,
                key="restaurant_edit_submit",
                disabled=not can_update_restaurant,
            )
            if not submitted_edit:
                return

            validation_errors = validate_restaurant_form_fn(
                brand=edit_brand,
                branch=edit_branch,
                pricing_model=edit_pricing_model,
                hourly_rate=edit_hourly_rate,
                package_rate=edit_package_rate,
                package_threshold=edit_package_threshold,
                package_rate_low=edit_package_rate_low,
                package_rate_high=edit_package_rate_high,
                fixed_fee=edit_fixed_fee,
                headcount=edit_headcount,
                start_date_value=edit_start_date if isinstance(edit_start_date, date) else None,
                end_date_value=edit_end_date if isinstance(edit_end_date, date) else None,
                extra_req=edit_extra_req,
                extra_req_date=edit_extra_req_date if isinstance(edit_extra_req_date, date) else None,
                reduce_req=edit_reduce_req,
                reduce_req_date=edit_reduce_req_date if isinstance(edit_reduce_req_date, date) else None,
                contact_name=edit_contact_name,
                contact_phone=edit_contact_phone,
                contact_email=edit_contact_email,
                company_title=edit_company_title,
                address=edit_address,
                tax_office=edit_tax_office,
                tax_number=edit_tax_number,
            )
            if validation_errors:
                for error_text in validation_errors:
                    st.error(error_text)
                return

            try:
                success_message = update_restaurant_and_commit_fn(
                    conn,
                    restaurant_id=selected_id,
                    restaurant_values={
                        "brand": edit_brand,
                        "branch": edit_branch,
                        "pricing_model": edit_pricing_model,
                        "hourly_rate": edit_hourly_rate,
                        "package_rate": edit_package_rate,
                        "package_threshold": edit_package_threshold if edit_pricing_model == "threshold_package" else None,
                        "package_rate_low": edit_package_rate_low,
                        "package_rate_high": edit_package_rate_high,
                        "fixed_monthly_fee": edit_fixed_fee,
                        "vat_rate": edit_vat_rate,
                        "target_headcount": edit_headcount,
                        "start_date": edit_start_date.isoformat() if isinstance(edit_start_date, date) else None,
                        "end_date": edit_end_date.isoformat() if isinstance(edit_end_date, date) else None,
                        "extra_headcount_request": edit_extra_req,
                        "extra_headcount_request_date": edit_extra_req_date.isoformat() if isinstance(edit_extra_req_date, date) else None,
                        "reduce_headcount_request": edit_reduce_req,
                        "reduce_headcount_request_date": edit_reduce_req_date.isoformat() if isinstance(edit_reduce_req_date, date) else None,
                        "contact_name": edit_contact_name,
                        "contact_phone": edit_contact_phone,
                        "contact_email": edit_contact_email,
                        "company_title": edit_company_title,
                        "address": edit_address,
                        "tax_office": edit_tax_office,
                        "tax_number": edit_tax_number,
                        "notes": edit_notes,
                    },
                )
            except Exception as exc:
                st.error(f"Restoran kartı güncellenemedi: {exc}")
            else:
                set_flash_message_fn("success", success_message)
                st.rerun()
