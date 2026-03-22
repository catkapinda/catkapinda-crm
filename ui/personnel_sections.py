from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd
import streamlit as st


def render_personnel_list_workspace(
    df: pd.DataFrame,
    *,
    recently_created_id: int,
    personnel_role_options: list[str],
    apply_text_search_fn: Callable[[pd.DataFrame, list[str], str], pd.DataFrame],
    build_personnel_preview_options_fn: Callable[[pd.DataFrame], dict[str, int]],
    build_personnel_list_rows_fn: Callable[[pd.DataFrame], list[dict[str, Any]]],
    build_personnel_preview_snapshot_items_fn: Callable[..., list[tuple[str, Any]]],
    format_motor_rental_summary_fn: Callable[[Any], str],
    format_motor_purchase_summary_fn: Callable[[Any], str],
    render_tab_header_fn: Callable[[str, str], None],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
) -> None:
    render_tab_header_fn("Personel Listesi", "Rol, durum ve restoran filtreleri ile kayıtları daralt; sağ panelden seçili kişiyi hızlıca incele.")
    f1, f2, f3, f4 = st.columns([2.1, 1, 1, 1.2])
    search_query = f1.text_input("Ara", placeholder="Ad, kod, telefon veya plaka ara", key="person_search")
    role_filter = f2.selectbox("Rol", ["Tümü", *personnel_role_options], key="person_role_filter")
    status_filter = f3.selectbox("Durum", ["Tümü", "Aktif", "Pasif"], key="person_status_filter")
    restaurant_options = ["Tümü"] + sorted(df["restoran"].dropna().astype(str).unique().tolist()) if not df.empty else ["Tümü"]
    restaurant_filter = f4.selectbox("Ana Restoran", restaurant_options, key="person_rest_filter")

    filtered_df = df.copy()
    if role_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["role"] == role_filter].copy()
    if status_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["status"] == status_filter].copy()
    if restaurant_filter != "Tümü":
        filtered_df = filtered_df[filtered_df["restoran"] == restaurant_filter].copy()
    filtered_df = apply_text_search_fn(
        filtered_df,
        ["person_code", "full_name", "phone", "emergency_contact_name", "emergency_contact_phone", "address", "current_plate", "restoran"],
        search_query,
    )

    if df.empty:
        st.info("Henüz personel kaydı yok.")
        return

    preview_source = filtered_df if not filtered_df.empty else df
    preview_labels = build_personnel_preview_options_fn(preview_source)
    if recently_created_id > 0:
        for label, person_id in preview_labels.items():
            if person_id == recently_created_id:
                st.session_state["person_preview_select"] = label
                break

    left, right = st.columns([2.35, 1])
    with left:
        personnel_rows = build_personnel_list_rows_fn(filtered_df)
        render_dashboard_data_grid_fn(
            "Personel Kartları",
            "Personel kayıtlarını rol, restoran ve operasyon durumu ile birlikte daha temiz satırlarda takip et.",
            ["Personel", "Rol", "Ana Restoran", "Motor", "Durum"],
            personnel_rows,
            "Filtreye uyan personel kaydı görünmüyor.",
            badge_columns={"Durum"},
            muted_columns={"Ana Restoran"},
        )
        st.caption(f"{len(filtered_df)} personel gösteriliyor.")
    with right:
        preview_label = st.selectbox("Kart Önizleme", list(preview_labels.keys()), key="person_preview_select")
        preview_id = preview_labels[preview_label]
        preview_row = df.loc[df["id"] == preview_id].iloc[0]
        render_record_snapshot_fn(
            "Seçili Personel",
            build_personnel_preview_snapshot_items_fn(
                preview_row,
                motor_rental_summary_fn=format_motor_rental_summary_fn,
                motor_purchase_summary_fn=format_motor_purchase_summary_fn,
            ),
        )
        st.info("Kartı düzenlemek, pasife almak veya görev bilgilerini değiştirmek için “Personel Düzenle” sekmesini kullan.")


def render_personnel_add_workspace(
    conn: Any,
    df: pd.DataFrame,
    *,
    can_create_personnel: bool,
    recently_created_id: int,
    workspace_key: str,
    rest_opts_with_blank: dict[str, Any],
    personnel_role_options: list[str],
    motor_usage_mode_options: list[str],
    motor_purchase_commitment_options: list[int],
    equipment_items: list[str],
    cost_model_labels: dict[str, str],
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
    auto_motor_purchase_installment_count: int,
    render_tab_header_fn: Callable[[str, str], None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    build_personnel_recent_snapshot_items_fn: Callable[..., list[tuple[str, Any]]],
    format_motor_rental_summary_fn: Callable[[Any], str],
    format_motor_purchase_summary_fn: Callable[[Any], str],
    render_field_label_fn: Callable[[str, bool], None],
    role_requires_primary_restaurant_fn: Callable[[str], bool],
    resolve_cost_role_option_fn: Callable[[str, str], str],
    is_fixed_cost_model_fn: Callable[[str], bool],
    get_role_fixed_cost_label_fn: Callable[..., str],
    next_person_code_fn: Callable[..., str],
    build_new_person_form_defaults_fn: Callable[..., dict[str, Any]],
    prepare_new_person_form_state_fn: Callable[..., None],
    create_person_with_onboarding_fn: Callable[..., Any],
    clear_new_person_onboarding_state_fn: Callable[[], None],
    initialize_onboarding_equipment_state_fn: Callable[[Any, str, date | None], None],
    onboarding_equipment_state_key_fn: Callable[[str, str], str],
    collect_onboarding_equipment_payloads_fn: Callable[[Any, list[str]], list[dict[str, Any]]],
    validate_onboarding_equipment_payloads_fn: Callable[[list[dict[str, Any]]], list[str]],
    build_motor_usage_payload_fn: Callable[..., dict[str, Any]],
    render_motor_deduction_snapshot_from_payload_fn: Callable[[dict[str, Any]], None],
    render_motor_purchase_proration_caption_fn: Callable[[], None],
    get_equipment_cost_snapshot_fn: Callable[[Any, str], tuple[Any, ...]],
    validate_personnel_form_fn: Callable[..., list[str]],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    fmt_number_fn: Callable[[Any], str],
    fmt_try_fn: Callable[[Any], str],
    normalize_cost_model_value_fn: Callable[[str, str], str],
    insert_equipment_issue_and_get_id_fn: Callable[..., int],
    post_equipment_installments_fn: Callable[..., None],
    sync_person_current_role_snapshot_fn: Callable[[Any, Any], None],
    sync_person_business_rules_fn: Callable[[Any, Any], None],
    set_flash_message_fn: Callable[[str, str], None],
) -> None:
    render_tab_header_fn("Yeni Personel Kartı", "Kimlik, muhasebe, motor ve işe giriş ekipmanlarını aynı onboarding akışında tamamlayarak yeni kart oluştur.")
    if recently_created_id > 0 and not df.empty:
        recent_match = df[df["id"] == recently_created_id]
        if not recent_match.empty:
            recent_row = recent_match.iloc[0]
            render_record_snapshot_fn(
                "Az Önce Oluşturulan Personel",
                build_personnel_recent_snapshot_items_fn(
                    recent_row,
                    motor_rental_summary_fn=format_motor_rental_summary_fn,
                    motor_purchase_summary_fn=format_motor_purchase_summary_fn,
                ),
            )

    new_person_defaults = build_new_person_form_defaults_fn(
        default_role=personnel_role_options[0],
        auto_motor_rental_deduction=auto_motor_rental_deduction,
        auto_motor_purchase_monthly_deduction=auto_motor_purchase_monthly_deduction,
    )
    prepare_new_person_form_state_fn(
        st.session_state,
        defaults=new_person_defaults,
        clear_new_person_onboarding_state_fn=clear_new_person_onboarding_state_fn,
    )

    st.markdown("##### Kimlik ve Görev")
    selected_cost_model = resolve_cost_role_option_fn("", st.session_state.get("new_person_role", personnel_role_options[0]))
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_field_label_fn("Ad Soyad", required=True)
        full_name = st.text_input("Ad Soyad", key="new_person_full_name", label_visibility="collapsed")
    with c2:
        render_field_label_fn("Rol")
        role = st.selectbox("Rol", personnel_role_options, key="new_person_role", label_visibility="collapsed")
    selected_cost_model = resolve_cost_role_option_fn("", role)
    with c3:
        render_field_label_fn("Maliyet Modeli")
        cost_model = st.selectbox(
            "Maliyet Modeli",
            [selected_cost_model],
            index=0,
            disabled=True,
            format_func=lambda x: cost_model_labels.get(x, x),
            label_visibility="collapsed",
        )
    code_preview = next_person_code_fn(conn, role)
    with c4:
        render_field_label_fn("Otomatik Personel Kodu")
        st.text_input("Otomatik Personel Kodu", value=code_preview, disabled=True, label_visibility="collapsed")

    c5, c6, c7 = st.columns(3)
    with c5:
        render_field_label_fn("Telefon", required=True)
        phone = st.text_input("Telefon", key="new_person_phone", label_visibility="collapsed")
    with c6:
        render_field_label_fn("Ana Restoran", required=role_requires_primary_restaurant_fn(role))
        assigned_label = st.selectbox(
            "Ana Restoran",
            list(rest_opts_with_blank.keys()),
            key="new_person_assigned_label",
            disabled=not role_requires_primary_restaurant_fn(role),
            label_visibility="collapsed",
        )
    with c7:
        render_field_label_fn("İşe Giriş Tarihi", required=True)
        start_date = st.date_input("İşe Giriş Tarihi", key="new_person_start_date", label_visibility="collapsed")

    c8, c9, c10 = st.columns(3)
    with c8:
        render_field_label_fn("TC Kimlik No", required=True)
        tc_no = st.text_input("TC Kimlik No", key="new_person_tc_no", label_visibility="collapsed")
    with c9:
        render_field_label_fn("IBAN", required=True)
        iban = st.text_input("IBAN", key="new_person_iban", label_visibility="collapsed")
    with c10:
        render_field_label_fn("Acil Durum İletişim Telefonu")
        emergency_contact_phone = st.text_input("Acil Durum İletişim Telefonu", key="new_person_emergency_contact_phone", label_visibility="collapsed")

    c11, c12 = st.columns(2)
    with c11:
        render_field_label_fn("Acil Durum İletişim Adı Soyadı")
        emergency_contact_name = st.text_input("Acil Durum İletişim Adı Soyadı", key="new_person_emergency_contact_name", label_visibility="collapsed")
    with c12:
        render_field_label_fn("Adres")
        address = st.text_area("Adres", placeholder="Açık Adres", key="new_person_address", label_visibility="collapsed")

    st.markdown("##### Muhasebe ve Şirket")
    c10, c11 = st.columns(2)
    with c10:
        render_field_label_fn("Muhasebe")
        accounting_type = st.selectbox("Muhasebe", ["Çat Kapında Muhasebe", "Kendi Muhasebecisi"], key="new_person_accounting_type", label_visibility="collapsed")
    with c11:
        render_field_label_fn("Yeni Şirket Açılışı")
        new_company_setup = st.selectbox("Yeni Şirket Açılışı", ["Hayır", "Evet"], key="new_person_new_company_setup", label_visibility="collapsed")

    c13, c14, c15 = st.columns(3)
    with c13:
        render_field_label_fn("Muhasebeden Aldığımız Ücret")
        accounting_revenue = st.number_input("Muhasebeden Aldığımız Ücret", min_value=0.0, step=100.0, key="new_person_accounting_revenue", label_visibility="collapsed")
    with c14:
        render_field_label_fn("Muhasebeciye Ödediğimiz")
        accountant_cost = st.number_input("Muhasebeciye Ödediğimiz", min_value=0.0, step=100.0, key="new_person_accountant_cost", label_visibility="collapsed")
    if is_fixed_cost_model_fn(cost_model):
        fixed_cost_label = get_role_fixed_cost_label_fn(role)
        with c15:
            render_field_label_fn(fixed_cost_label, required=True)
            monthly_fixed_cost = st.number_input(fixed_cost_label, min_value=0.0, step=100.0, key="new_person_monthly_fixed_cost", label_visibility="collapsed")
    else:
        c15.markdown("")
        monthly_fixed_cost = 0.0
    if role == "Joker":
        st.caption("Joker rolünde personel artık paket primi almaz; aylık sabit maaşı gün bazlı prorate edilerek hakedişe yansır.")

    c16, c17 = st.columns(2)
    with c16:
        render_field_label_fn("Şirket Açılışından Aldığımız Ücret")
        company_setup_revenue = st.number_input("Şirket Açılışından Aldığımız Ücret", min_value=0.0, step=100.0, key="new_person_company_setup_revenue", label_visibility="collapsed")
    with c17:
        render_field_label_fn("Şirket Açılış Maliyeti")
        company_setup_cost = st.number_input("Şirket Açılış Maliyeti", min_value=0.0, step=100.0, key="new_person_company_setup_cost", label_visibility="collapsed")

    st.markdown("##### Araç ve Operasyon")
    c18, c19, c20 = st.columns(3)
    with c18:
        render_field_label_fn("Motor Kullanım Modeli")
        motor_usage_mode = st.selectbox(
            "Motor Kullanım Modeli",
            motor_usage_mode_options,
            key="new_person_motor_usage_mode",
            label_visibility="collapsed",
        )
    with c19:
        render_field_label_fn("Güncel Plaka", required=True)
        current_plate = st.text_input("Güncel Plaka", key="new_person_current_plate", label_visibility="collapsed")
    sale_mode_enabled = motor_usage_mode == "Çat Kapında Motor Satışı"
    if motor_usage_mode == "Çat Kapında Motor Kirası":
        with c20:
            render_field_label_fn("Aylık Motor Kira Tutarı", required=True)
            motor_rental_monthly_amount = st.number_input(
                "Aylık Motor Kira Tutarı",
                min_value=0.0,
                step=100.0,
                key="new_person_motor_rental_monthly_amount",
                label_visibility="collapsed",
            )
        st.caption("Bu personel Çat Kapında motorunu kiralıyorsa aylık kira tutarı buradan yönetilir.")
    else:
        with c20:
            render_field_label_fn("Aylık Motor Kira Tutarı")
            st.number_input(
                "Aylık Motor Kira Tutarı",
                min_value=0.0,
                step=100.0,
                value=0.0,
                disabled=True,
                key="new_person_motor_rental_monthly_amount_disabled",
                label_visibility="collapsed",
            )
        motor_rental_monthly_amount = 0.0

    c21, c22, c23 = st.columns(3)
    with c21:
        render_field_label_fn("Motor Satın Alım Tarihi", required=sale_mode_enabled)
        motor_purchase_start_date = st.date_input(
            "Motor Satın Alım Tarihi",
            key="new_person_motor_purchase_start_date",
            disabled=not sale_mode_enabled,
            label_visibility="collapsed",
        )
    if sale_mode_enabled:
        render_motor_purchase_proration_caption_fn()
    with c22:
        render_field_label_fn("Taahhüt Süresi (Ay)", required=sale_mode_enabled)
        motor_purchase_commitment_months = st.selectbox(
            "Taahhüt Süresi (Ay)",
            motor_purchase_commitment_options,
            key="new_person_motor_purchase_commitment_months",
            disabled=not sale_mode_enabled,
            label_visibility="collapsed",
        )
    with c23:
        render_field_label_fn("Aylık Motor Satış Taksiti", required=sale_mode_enabled)
        motor_purchase_sale_price = st.number_input(
            "Aylık Motor Satış Taksiti",
            min_value=0.0,
            step=100.0,
            key="new_person_motor_purchase_sale_price",
            disabled=not sale_mode_enabled,
            label_visibility="collapsed",
        )
    if sale_mode_enabled:
        st.info("Motor satış modeli seçildi. Bu personelde ayrıca motor kirası uygulanmaz.")
    motor_usage_payload = build_motor_usage_payload_fn(
        motor_usage_mode=motor_usage_mode,
        motor_rental_monthly_amount=safe_float_fn(motor_rental_monthly_amount, 0.0),
        motor_purchase_start_date_value=motor_purchase_start_date if isinstance(motor_purchase_start_date, date) else None,
        motor_purchase_commitment_months=safe_int_fn(motor_purchase_commitment_months, 0),
        motor_purchase_sale_price=safe_float_fn(motor_purchase_sale_price, 0.0),
    )
    vehicle_type = str(motor_usage_payload["vehicle_type"] or "")
    motor_purchase = str(motor_usage_payload["motor_purchase"] or "Hayır")
    render_motor_deduction_snapshot_from_payload_fn(motor_usage_payload)

    st.markdown("##### İşe Giriş Ekipmanları")
    onboarding_items = st.multiselect(
        "İşe girişte verilen ekipmanlar",
        equipment_items,
        key="new_person_onboarding_items",
        help="İşe girişte satılan veya personele teslim edilen ekipmanları burada kaydet. Sonradan eklenen hareketleri seçili personelin düzenleme kartından yönetebilirsin.",
    )
    onboarding_issue_payloads: list[dict[str, Any]] = []
    if onboarding_items:
        st.caption("Satın alma kayıtlarındaki ortalama maliyet arka planda kullanılır. Burada yalnızca kuryeye satış fiyatını, KDV'yi ve taksit bilgisini girmen yeterli.")
        for item_name in onboarding_items:
            initialize_onboarding_equipment_state_fn(conn, item_name, start_date if isinstance(start_date, date) else None)
            issue_date_key = onboarding_equipment_state_key_fn(item_name, "issue_date")
            quantity_key = onboarding_equipment_state_key_fn(item_name, "quantity")
            sale_price_key = onboarding_equipment_state_key_fn(item_name, "sale_price")
            vat_rate_key = onboarding_equipment_state_key_fn(item_name, "vat_rate")
            installment_key = onboarding_equipment_state_key_fn(item_name, "installment_count")
            notes_key = onboarding_equipment_state_key_fn(item_name, "notes")
            cost_snapshot = get_equipment_cost_snapshot_fn(conn, item_name)
            average_cost = safe_float_fn(cost_snapshot[3], 0.0)
            st.markdown(f"###### {item_name}")
            item_c1, item_c2, item_c3 = st.columns(3)
            with item_c1:
                render_field_label_fn("Teslim Tarihi", required=True)
                st.date_input("Teslim Tarihi", key=issue_date_key, label_visibility="collapsed")
            with item_c2:
                render_field_label_fn("Adet", required=True)
                st.number_input("Adet", min_value=1, step=1, key=quantity_key, label_visibility="collapsed")
            with item_c3:
                render_field_label_fn("Kuryeye Satış Fiyatı | KDV dahil")
                st.number_input("Kuryeye Satış Fiyatı | KDV dahil", min_value=0.0, step=50.0, key=sale_price_key, label_visibility="collapsed")
            item_c4, item_c5, item_c6 = st.columns(3)
            with item_c4:
                render_field_label_fn("KDV")
                st.selectbox(
                    "KDV",
                    [10.0, 20.0],
                    key=vat_rate_key,
                    format_func=lambda x: f"%{fmt_number_fn(x)}",
                    label_visibility="collapsed",
                )
            with item_c5:
                render_field_label_fn("Taksit Sayısı")
                st.selectbox("Taksit Sayısı", [1, 2, 3, 6, 12], key=installment_key, label_visibility="collapsed")
            with item_c6:
                render_field_label_fn("Not")
                st.text_input("Not", key=notes_key, label_visibility="collapsed")
            if average_cost > 0:
                st.caption(f"Ortalama birim maliyet: {fmt_try_fn(average_cost)}")
        onboarding_issue_payloads = collect_onboarding_equipment_payloads_fn(conn, onboarding_items)

    notes = st.text_area("Notlar", placeholder="Personel hakkında operasyonel notlar", key="new_person_notes")

    if not can_create_personnel:
        st.caption("Personel olusturma yetkin olmadigi icin kaydetme butonu pasif.")
    create_clicked = st.button(
        "Personel Kartını Oluştur",
        use_container_width=True,
        key="new_person_create",
        disabled=not can_create_personnel,
    )
    if not create_clicked:
        if create_success_message := str(st.session_state.get("personnel_create_success_message", "") or "").strip():
            st.success(f"Personel kartı oluşturuldu. {create_success_message}")
        return

    st.session_state.pop("personnel_create_success_message", None)
    st.session_state.pop("personnel_recently_created", None)
    assigned_id = rest_opts_with_blank.get(assigned_label) if role_requires_primary_restaurant_fn(role) else None
    validation_errors = validate_personnel_form_fn(
        full_name=full_name,
        phone=phone,
        tc_no=tc_no,
        iban=iban,
        address=address,
        current_plate=current_plate,
        role=role,
        assigned_restaurant_id=assigned_id,
        start_date_value=start_date if isinstance(start_date, date) else None,
        vehicle_type=vehicle_type,
        motor_rental_monthly_amount=safe_float_fn(motor_rental_monthly_amount, 0.0),
        cost_model=cost_model,
        monthly_fixed_cost=monthly_fixed_cost,
        motor_purchase=motor_purchase,
        motor_purchase_start_date_value=motor_purchase_start_date if isinstance(motor_purchase_start_date, date) else None,
        motor_purchase_commitment_months=safe_int_fn(motor_purchase_commitment_months, 0),
        motor_purchase_sale_price=safe_float_fn(motor_purchase_sale_price, 0.0),
    )
    validation_errors.extend(validate_onboarding_equipment_payloads_fn(onboarding_issue_payloads))
    if validation_errors:
        for error_text in validation_errors:
            st.error(error_text)
        return

    try:
        create_result = create_person_with_onboarding_fn(
            conn,
            role=role,
            person_values={
                "full_name": full_name,
                "role": role,
                "phone": phone,
                "address": address,
                "tc_no": tc_no,
                "iban": iban,
                "emergency_contact_name": emergency_contact_name,
                "emergency_contact_phone": emergency_contact_phone,
                "accounting_type": accounting_type,
                "new_company_setup": new_company_setup,
                "accounting_revenue": accounting_revenue,
                "accountant_cost": accountant_cost,
                "company_setup_revenue": company_setup_revenue,
                "company_setup_cost": company_setup_cost,
                "assigned_restaurant_id": assigned_id,
                "vehicle_type": motor_usage_payload["vehicle_type"],
                "motor_rental": motor_usage_payload["motor_rental"],
                "motor_purchase": motor_usage_payload["motor_purchase"],
                "motor_purchase_start_date": motor_usage_payload["motor_purchase_start_date_str"],
                "motor_purchase_commitment_months": motor_usage_payload["motor_purchase_commitment_months"],
                "motor_rental_monthly_amount": motor_usage_payload["motor_rental_monthly_amount"],
                "motor_purchase_sale_price": motor_usage_payload["motor_purchase_sale_price"],
                "motor_purchase_monthly_amount": motor_usage_payload["motor_purchase_monthly_amount"],
                "motor_purchase_installment_count": motor_usage_payload["motor_purchase_installment_count"],
                "current_plate": current_plate,
                "start_date": start_date.isoformat() if isinstance(start_date, date) else None,
                "cost_model": normalize_cost_model_value_fn(cost_model, role),
                "monthly_fixed_cost": monthly_fixed_cost,
                "notes": notes,
            },
            onboarding_issue_payloads=onboarding_issue_payloads,
            safe_int_fn=safe_int_fn,
            safe_float_fn=safe_float_fn,
            insert_equipment_issue_and_get_id_fn=insert_equipment_issue_and_get_id_fn,
            post_equipment_installments_fn=post_equipment_installments_fn,
            sync_person_current_role_snapshot_fn=sync_person_current_role_snapshot_fn,
            sync_person_business_rules_fn=sync_person_business_rules_fn,
        )
    except Exception as exc:
        st.error(f"Personel kartı oluşturulamadı: {exc}")
        return

    success_text = create_result.success_text
    st.session_state[workspace_key] = "add"
    st.session_state["person_search"] = ""
    st.session_state["person_role_filter"] = "Tümü"
    st.session_state["person_status_filter"] = "Tümü"
    st.session_state["person_rest_filter"] = "Tümü"
    st.session_state["personnel_recently_created"] = {"personnel_id": create_result.created_person_id}
    st.session_state["personnel_create_success_message"] = success_text
    st.session_state["personnel_form_reset_pending"] = True
    set_flash_message_fn("success", success_text)
    st.rerun()


def render_personnel_edit_workspace(
    conn: Any,
    df: pd.DataFrame,
    *,
    can_update_personnel: bool,
    can_toggle_personnel_status: bool,
    can_delete_personnel: bool,
    can_create_equipment: bool,
    can_update_equipment: bool,
    can_delete_equipment: bool,
    can_box_return: bool,
    rest_opts: dict[str, Any],
    rest_opts_with_blank: dict[str, Any],
    personnel_role_options: list[str],
    motor_usage_mode_options: list[str],
    motor_purchase_commitment_options: list[int],
    issue_items: list[str],
    cost_model_labels: dict[str, str],
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
    render_tab_header_fn: Callable[[str, str], None],
    fetch_df_fn: Callable[[Any, str, tuple], pd.DataFrame],
    parse_date_value_fn: Callable[[Any], date | None],
    resolve_vehicle_type_value_fn: Callable[[str, str], str],
    resolve_motor_usage_mode_fn: Callable[[str, str, str], str],
    build_personnel_edit_selection_payload_fn: Callable[..., Any],
    initialize_edit_person_transition_state_fn: Callable[[int, str, float, date | None], None],
    role_requires_primary_restaurant_fn: Callable[[str], bool],
    format_motor_rental_summary_fn: Callable[[Any], str],
    format_motor_purchase_summary_fn: Callable[[Any], str],
    resolve_cost_role_option_fn: Callable[[str, str], str],
    format_display_df_fn: Callable[..., pd.DataFrame],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    render_field_label_fn: Callable[[str, bool], None],
    resolve_effective_role_from_transition_fn: Callable[[str, bool, str], tuple[str, bool]],
    is_fixed_cost_model_fn: Callable[[str], bool],
    get_role_fixed_cost_label_fn: Callable[..., str],
    build_personnel_code_display_values_fn: Callable[..., tuple[str, str]],
    update_person_and_sync_fn: Callable[..., Any],
    toggle_person_status_and_sync_fn: Callable[..., Any],
    delete_person_with_dependencies_fn: Callable[..., Any],
    build_motor_usage_payload_fn: Callable[..., dict[str, Any]],
    render_vehicle_transition_caption_fn: Callable[[], None],
    render_motor_purchase_proration_caption_fn: Callable[[], None],
    render_motor_deduction_snapshot_from_payload_fn: Callable[[dict[str, Any]], None],
    safe_float_fn: Callable[[Any, float], float],
    safe_int_fn: Callable[[Any, int], int],
    validate_personnel_form_fn: Callable[..., list[str]],
    validate_role_transition_inputs_fn: Callable[..., list[str]],
    normalize_cost_model_value_fn: Callable[[str, str], str],
    record_person_role_transition_fn: Callable[..., None],
    sync_person_current_role_snapshot_fn: Callable[[Any, Any], None],
    record_person_vehicle_transition_fn: Callable[..., None],
    sync_person_current_vehicle_snapshot_fn: Callable[[Any, Any], None],
    sync_person_business_rules_fn: Callable[[Any, Any], None],
    set_flash_message_fn: Callable[[str, str], None],
    get_personnel_dependency_counts_fn: Callable[[Any, int], dict[str, int]],
    delete_personnel_and_dependencies_fn: Callable[[Any, int], None],
    get_equipment_cost_snapshot_fn: Callable[[Any, str], tuple[Any, ...]],
    get_default_equipment_unit_cost_fn: Callable[[Any, str], float],
    get_default_equipment_sale_price_fn: Callable[[str], float],
    get_default_issue_installment_count_fn: Callable[[str], int],
    latest_average_cost_fn: Callable[[Any, str], float],
    get_equipment_vat_rate_fn: Callable[[str, Any], float],
    fmt_number_fn: Callable[[Any], str],
    fmt_try_fn: Callable[[Any], str],
    normalize_equipment_issue_installment_count_fn: Callable[[str, int], int],
    equipment_issue_generates_installments_fn: Callable[[str, float, int], bool],
    insert_equipment_issue_and_get_id_fn: Callable[..., int],
    post_equipment_installments_fn: Callable[..., None],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    update_equipment_issue_record_fn: Callable[..., bool],
    delete_equipment_issue_records_fn: Callable[[Any, list[int]], int],
) -> None:
    if df.empty:
        st.info("Güncellenecek personel kaydı bulunmuyor.")
        return

    render_tab_header_fn("Personel Düzenleme", "Solda düzenleme formu, sağda mevcut kart özeti bulunur. Rol değiştiğinde sistem uygun kod önerisini gösterir.")
    person_labels = {
        f"{row['full_name']} | {row['role']} | Kod: {row['person_code'] or '-'} | ID: {row['id']}": int(row["id"])
        for _, row in df.iterrows()
    }
    selected_label = st.selectbox("Düzenlenecek Personel", list(person_labels.keys()), key="edit_person_select")
    edit_selection = build_personnel_edit_selection_payload_fn(
        df,
        selected_label=selected_label,
        personnel_role_options=personnel_role_options,
        motor_usage_mode_options=motor_usage_mode_options,
        rest_opts=rest_opts,
        parse_date_value_fn=parse_date_value_fn,
        resolve_vehicle_type_value_fn=resolve_vehicle_type_value_fn,
        resolve_motor_usage_mode_fn=resolve_motor_usage_mode_fn,
    )
    person_labels = edit_selection.person_labels
    selected_id = edit_selection.selected_id
    row = edit_selection.row
    row_role_value = edit_selection.row_role_value
    row_status_value = edit_selection.row_status_value
    row_accounting_value = edit_selection.row_accounting_value
    row_new_company_value = edit_selection.row_new_company_value
    row_vehicle_value = edit_selection.row_vehicle_value
    row_motor_purchase_value = edit_selection.row_motor_purchase_value
    row_motor_usage_mode = edit_selection.row_motor_usage_mode
    start_val = edit_selection.start_date_value
    assigned_value = edit_selection.assigned_value
    edit_form_signature = edit_selection.edit_form_signature
    if st.session_state.get("_edit_person_form_signature") != edit_form_signature:
        st.session_state[f"edit_person_role_{selected_id}"] = row_role_value
        st.session_state[f"edit_person_status_{selected_id}"] = row_status_value
        st.session_state[f"edit_person_accounting_{selected_id}"] = (
            row_accounting_value
        )
        st.session_state[f"edit_person_new_company_{selected_id}"] = (
            row_new_company_value
        )
        st.session_state[f"edit_person_motor_usage_mode_{selected_id}"] = (
            row_motor_usage_mode
        )
        initialize_edit_person_transition_state_fn(
            selected_id,
            row_role_value,
            float(row.get("monthly_fixed_cost") or 0.0),
            start_val,
        )
        st.session_state["_edit_person_form_signature"] = edit_form_signature

    role_history_rows = fetch_df_fn(
        conn,
        """
        SELECT role, cost_model, monthly_fixed_cost, effective_date, notes
        FROM personnel_role_history
        WHERE personnel_id = ?
        ORDER BY effective_date DESC, id DESC
        """,
        (selected_id,),
    )
    status_options = ["Aktif", "Pasif"]
    role_options = personnel_role_options

    left, right = st.columns([2.2, 1])
    with right:
        render_personnel_edit_sidebar(
            row,
            role_history_rows,
            role_requires_primary_restaurant_fn=role_requires_primary_restaurant_fn,
            format_motor_rental_summary_fn=format_motor_rental_summary_fn,
            format_motor_purchase_summary_fn=format_motor_purchase_summary_fn,
            resolve_cost_role_option_fn=resolve_cost_role_option_fn,
            format_display_df_fn=format_display_df_fn,
            render_record_snapshot_fn=render_record_snapshot_fn,
            cost_model_labels=cost_model_labels,
        )
    with left:
        transition_enabled = st.checkbox(
            "Rol değişikliği kaydı ekle",
            key=f"edit_person_transition_enabled_{selected_id}",
        )
        transition_previous_role = row_role_value
        transition_new_role = row_role_value
        transition_effective_date = None
        transition_monthly_cost = float(row.get("monthly_fixed_cost") or 0.0)
        if transition_enabled:
            st.markdown("##### Rol Değişikliği")
            st.caption("Örnek: 15'ine kadar kurye, 16'sından itibaren joker ise başlangıç tarihine 16'sını gir.")
            role_change_cols = st.columns(4)
            with role_change_cols[0]:
                render_field_label_fn("Geçiş Öncesi Rol", required=True)
                transition_previous_role = st.selectbox(
                    "Geçiş Öncesi Rol",
                    role_options,
                    key=f"edit_person_previous_role_{selected_id}",
                    label_visibility="collapsed",
                )
            with role_change_cols[1]:
                render_field_label_fn("Yeni Rol", required=True)
                transition_new_role = st.selectbox(
                    "Yeni Rol",
                    role_options,
                    key=f"edit_person_transition_new_role_{selected_id}",
                    label_visibility="collapsed",
                )
            with role_change_cols[2]:
                render_field_label_fn("Rol Başlangıç Tarihi", required=True)
                transition_effective_date = st.date_input(
                    "Rol Başlangıç Tarihi",
                    key=f"edit_person_transition_date_{selected_id}",
                    label_visibility="collapsed",
                )
            transition_cost_model = resolve_cost_role_option_fn("", transition_new_role)
            with role_change_cols[3]:
                if is_fixed_cost_model_fn(transition_cost_model):
                    transition_cost_label = get_role_fixed_cost_label_fn(transition_new_role, transition=True)
                    render_field_label_fn(transition_cost_label, required=True)
                    transition_monthly_cost = st.number_input(
                        transition_cost_label,
                        min_value=0.0,
                        step=100.0,
                        key=f"edit_person_transition_monthly_cost_{selected_id}",
                        label_visibility="collapsed",
                    )
                else:
                    render_field_label_fn("Yeni Rol Maliyet Modeli")
                    st.text_input(
                        "Yeni Rol Maliyet Modeli",
                        value=cost_model_labels.get(transition_cost_model, transition_cost_model),
                        disabled=True,
                        key=f"edit_person_transition_cost_model_display_{selected_id}",
                        label_visibility="collapsed",
                    )
            if transition_new_role == "Joker":
                st.caption("Joker rolüne geçildiğinde bu personel artık paket primi almaz; yalnızca sabit maaşı gün bazlı prorate edilir.")

        effective_role, role_changed = resolve_effective_role_from_transition_fn(
            row_role_value,
            transition_enabled,
            transition_new_role,
        )

        with st.container():
            st.markdown("##### Kimlik ve Görev")
            c1, c2, c3 = st.columns(3)
            with c1:
                render_field_label_fn("Rol")
                st.text_input(
                    "Rol",
                    value=effective_role,
                    disabled=True,
                    key=f"edit_person_role_display_{selected_id}",
                    label_visibility="collapsed",
                )
            suggested_code, code_default = build_personnel_code_display_values_fn(
                conn,
                current_person_code=row["person_code"],
                original_role=row_role_value,
                effective_role=effective_role,
                exclude_id=selected_id,
            )
            with c2:
                render_field_label_fn("Personel Kodu")
                edit_code = st.text_input("Personel Kodu", value=code_default or suggested_code, label_visibility="collapsed")
            with c3:
                render_field_label_fn("Önerilen Kod")
                st.caption(suggested_code)

            c4, c5, c6 = st.columns(3)
            with c4:
                render_field_label_fn("Ad Soyad", required=True)
                edit_name = st.text_input("Ad Soyad", value=row["full_name"] or "", label_visibility="collapsed")
            with c5:
                render_field_label_fn("Durum")
                edit_status = st.selectbox(
                    "Durum",
                    status_options,
                    key=f"edit_person_status_{selected_id}",
                    label_visibility="collapsed",
                )
            with c6:
                render_field_label_fn("Telefon", required=True)
                edit_phone = st.text_input("Telefon", value=row["phone"] or "", label_visibility="collapsed")

            c7, c8, c9 = st.columns(3)
            with c7:
                render_field_label_fn("TC Kimlik No", required=True)
                edit_tc = st.text_input("TC Kimlik No", value=row["tc_no"] or "", label_visibility="collapsed")
            with c8:
                render_field_label_fn("IBAN", required=True)
                edit_iban = st.text_input("IBAN", value=row["iban"] or "", label_visibility="collapsed")
            with c9:
                render_field_label_fn("İşe Giriş Tarihi", required=True)
                edit_start_date = st.date_input("İşe Giriş Tarihi", value=start_val, label_visibility="collapsed")

            render_field_label_fn("Adres")
            edit_address = st.text_area("Adres", value=row["address"] or "", label_visibility="collapsed")

            st.markdown("##### Acil Durum İletişimi")
            c9a, c9b = st.columns(2)
            with c9a:
                render_field_label_fn("Acil Durum İletişim Adı Soyadı")
                edit_emergency_contact_name = st.text_input(
                    "Acil Durum İletişim Adı Soyadı",
                    value=row["emergency_contact_name"] or "",
                    label_visibility="collapsed",
                )
            with c9b:
                render_field_label_fn("Acil Durum İletişim Telefonu")
                edit_emergency_contact_phone = st.text_input(
                    "Acil Durum İletişim Telefonu",
                    value=row["emergency_contact_phone"] or "",
                    label_visibility="collapsed",
                )

            st.markdown("##### Muhasebe ve Şirket")
            c10, c11, c12 = st.columns(3)
            accounting_options = ["Çat Kapında Muhasebe", "Kendi Muhasebecisi"]
            with c10:
                render_field_label_fn("Muhasebe")
                edit_accounting = st.selectbox(
                    "Muhasebe",
                    accounting_options,
                    key=f"edit_person_accounting_{selected_id}",
                    label_visibility="collapsed",
                )
            new_company_options = ["Hayır", "Evet"]
            with c11:
                render_field_label_fn("Yeni Şirket Açılışı")
                edit_new_company = st.selectbox(
                    "Yeni Şirket Açılışı",
                    new_company_options,
                    key=f"edit_person_new_company_{selected_id}",
                    label_visibility="collapsed",
                )
            edit_cost_model = resolve_cost_role_option_fn("", effective_role)
            with c12:
                render_field_label_fn("Maliyet Modeli")
                st.selectbox(
                    "Maliyet Modeli",
                    [edit_cost_model],
                    index=0,
                    disabled=True,
                    format_func=lambda x: cost_model_labels.get(x, x),
                    key=f"edit_person_cost_model_display_{selected_id}",
                    label_visibility="collapsed",
                )
            c13, c14, c15 = st.columns(3)
            with c13:
                render_field_label_fn("Muhasebeden Aldığımız Ücret")
                edit_accounting_revenue = st.number_input("Muhasebeden Aldığımız Ücret", min_value=0.0, value=float(row["accounting_revenue"] or 0.0), step=100.0, label_visibility="collapsed")
            with c14:
                render_field_label_fn("Muhasebeciye Ödediğimiz")
                edit_accountant_cost = st.number_input("Muhasebeciye Ödediğimiz", min_value=0.0, value=float(row["accountant_cost"] or 0.0), step=100.0, label_visibility="collapsed")
            if is_fixed_cost_model_fn(edit_cost_model) and not transition_enabled:
                edit_fixed_cost_label = get_role_fixed_cost_label_fn(effective_role)
                with c15:
                    render_field_label_fn(edit_fixed_cost_label, required=True)
                    edit_monthly_cost = st.number_input(edit_fixed_cost_label, min_value=0.0, value=float(row["monthly_fixed_cost"] or 0.0), step=100.0, label_visibility="collapsed")
            else:
                c15.markdown("")
                edit_monthly_cost = float(row["monthly_fixed_cost"] or 0.0)

            c16, c17 = st.columns(2)
            with c16:
                render_field_label_fn("Şirket Açılışından Aldığımız Ücret")
                edit_company_setup_revenue = st.number_input("Şirket Açılışından Aldığımız Ücret", min_value=0.0, value=float(row["company_setup_revenue"] or 0.0), step=100.0, label_visibility="collapsed")
            with c17:
                render_field_label_fn("Şirket Açılış Maliyeti")
                edit_company_setup_cost = st.number_input("Şirket Açılış Maliyeti", min_value=0.0, value=float(row["company_setup_cost"] or 0.0), step=100.0, label_visibility="collapsed")

            st.markdown("##### Araç ve Operasyon")
            current_vehicle = resolve_vehicle_type_value_fn(row["vehicle_type"] or "", row["motor_rental"] or "Hayır")
            current_motor_usage_mode = resolve_motor_usage_mode_fn(current_vehicle, row["motor_purchase"] or "Hayır", row["motor_rental"] or "Hayır")
            edit_restaurant = "-"
            if role_requires_primary_restaurant_fn(effective_role):
                c18, c19, c20 = st.columns(3)
                with c18:
                    render_field_label_fn("Ana Restoran", required=True)
                    edit_restaurant_default = assigned_value if assigned_value in rest_opts_with_blank else "-"
                    edit_restaurant = st.selectbox(
                        "Ana Restoran",
                        list(rest_opts_with_blank.keys()),
                        index=list(rest_opts_with_blank.keys()).index(edit_restaurant_default),
                        key=f"edit_person_restaurant_{selected_id}_{effective_role}",
                        label_visibility="collapsed",
                    )
                with c19:
                    render_field_label_fn("Motor Kullanım Modeli")
                    edit_motor_usage_mode = st.selectbox(
                        "Motor Kullanım Modeli",
                        motor_usage_mode_options,
                        key=f"edit_person_motor_usage_mode_{selected_id}",
                        label_visibility="collapsed",
                    )
                with c20:
                    render_field_label_fn("Güncel Plaka", required=True)
                    edit_plate = st.text_input("Güncel Plaka", value=row["current_plate"] or "", label_visibility="collapsed")
            else:
                c18, c19 = st.columns(2)
                with c18:
                    render_field_label_fn("Motor Kullanım Modeli")
                    edit_motor_usage_mode = st.selectbox(
                        "Motor Kullanım Modeli",
                        motor_usage_mode_options,
                        key=f"edit_person_motor_usage_mode_{selected_id}",
                        label_visibility="collapsed",
                    )
                with c19:
                    render_field_label_fn("Güncel Plaka", required=True)
                    edit_plate = st.text_input("Güncel Plaka", value=row["current_plate"] or "", label_visibility="collapsed")
            current_motor_rental_monthly_amount = safe_float_fn(row.get("motor_rental_monthly_amount", auto_motor_rental_deduction), auto_motor_rental_deduction)
            if edit_motor_usage_mode == "Çat Kapında Motor Kirası":
                render_field_label_fn("Aylık Motor Kira Tutarı", required=True)
                edit_motor_rental_monthly_amount = st.number_input(
                    "Aylık Motor Kira Tutarı",
                    min_value=0.0,
                    value=max(current_motor_rental_monthly_amount, 0.0),
                    step=100.0,
                    key=f"edit_person_motor_rental_monthly_amount_{selected_id}",
                    label_visibility="collapsed",
                )
                st.caption("Bu personel Çat Kapında motorunu kiralıyorsa aylık kira tutarı buradan yönetilir.")
            else:
                edit_motor_rental_monthly_amount = 0.0
            motor_mode_changed = edit_motor_usage_mode != current_motor_usage_mode
            c20a, c20b = st.columns(2)
            with c20a:
                render_field_label_fn("Motor Düzeni Başlangıç Tarihi", required=motor_mode_changed)
                edit_vehicle_transition_date = st.date_input(
                    "Motor Düzeni Başlangıç Tarihi",
                    value=start_val or date.today(),
                    key=f"edit_person_vehicle_transition_date_{selected_id}",
                    label_visibility="collapsed",
                )
            with c20b:
                render_vehicle_transition_caption_fn()
            c21, c22, c23 = st.columns(3)
            with c21:
                render_field_label_fn("Motor Satın Alım Tarihi", required=edit_motor_usage_mode == "Çat Kapında Motor Satışı")
                default_motor_purchase_date = parse_date_value_fn(row["motor_purchase_start_date"]) or date.today()
                edit_motor_purchase_start_date = st.date_input(
                    "Motor Satın Alım Tarihi",
                    value=default_motor_purchase_date,
                    key=f"edit_person_motor_purchase_start_date_{selected_id}",
                    disabled=edit_motor_usage_mode != "Çat Kapında Motor Satışı",
                    label_visibility="collapsed",
                )
            if edit_motor_usage_mode == "Çat Kapında Motor Satışı":
                render_motor_purchase_proration_caption_fn()
            current_commitment_months = safe_int_fn(row["motor_purchase_commitment_months"], 12)
            if current_commitment_months not in motor_purchase_commitment_options:
                current_commitment_months = 12
            with c22:
                render_field_label_fn("Taahhüt Süresi (Ay)", required=edit_motor_usage_mode == "Çat Kapında Motor Satışı")
                edit_motor_purchase_commitment_months = st.selectbox(
                    "Taahhüt Süresi (Ay)",
                    motor_purchase_commitment_options,
                    index=motor_purchase_commitment_options.index(current_commitment_months),
                    key=f"edit_person_motor_purchase_commitment_months_{selected_id}",
                    disabled=edit_motor_usage_mode != "Çat Kapında Motor Satışı",
                    label_visibility="collapsed",
                )
            current_motor_purchase_sale_price = safe_float_fn(
                row["motor_purchase_monthly_amount"],
                safe_float_fn(row["motor_purchase_sale_price"], 0.0),
            )
            with c23:
                render_field_label_fn("Aylık Motor Satış Taksiti", required=edit_motor_usage_mode == "Çat Kapında Motor Satışı")
                edit_motor_purchase_sale_price = st.number_input(
                    "Aylık Motor Satış Taksiti",
                    min_value=0.0,
                    value=max(current_motor_purchase_sale_price, 0.0),
                    step=100.0,
                    key=f"edit_person_motor_purchase_sale_price_{selected_id}",
                    disabled=edit_motor_usage_mode != "Çat Kapında Motor Satışı",
                    label_visibility="collapsed",
                )
            edit_motor_usage_payload = build_motor_usage_payload_fn(
                motor_usage_mode=edit_motor_usage_mode,
                motor_rental_monthly_amount=safe_float_fn(edit_motor_rental_monthly_amount, 0.0),
                motor_purchase_start_date_value=edit_motor_purchase_start_date if isinstance(edit_motor_purchase_start_date, date) else None,
                motor_purchase_commitment_months=safe_int_fn(edit_motor_purchase_commitment_months, 0),
                motor_purchase_sale_price=safe_float_fn(edit_motor_purchase_sale_price, 0.0),
            )
            edit_vehicle = str(edit_motor_usage_payload["vehicle_type"] or "")
            edit_motor_purchase = str(edit_motor_usage_payload["motor_purchase"] or "Hayır")
            current_motor_purchase = str(row["motor_purchase"] or "Hayır") if pd.notna(row["motor_purchase"]) else "Hayır"
            if edit_motor_usage_mode == "Çat Kapında Motor Satışı":
                st.info("Motor satış modeli seçildi. Bu personelde ayrıca motor kirası uygulanmaz.")
            render_motor_deduction_snapshot_from_payload_fn(edit_motor_usage_payload)
            edit_notes = st.text_area("Notlar", value=row["notes"] or "")

            c24, c25, c26 = st.columns(3)
            if not can_update_personnel or not can_toggle_personnel_status or not can_delete_personnel:
                st.caption("Yetkine gore bazi personel aksiyonlari pasif.")
            update_clicked = c24.button(
                "Personeli Güncelle",
                use_container_width=True,
                key=f"edit_person_update_{selected_id}",
                disabled=not can_update_personnel,
            )
            toggle_clicked = c25.button(
                "Aktif/Pasif Durumunu Değiştir",
                use_container_width=True,
                key=f"edit_person_toggle_{selected_id}",
                disabled=not can_toggle_personnel_status,
            )
            delete_clicked = c26.button(
                "Kalıcı Sil",
                use_container_width=True,
                key=f"edit_person_delete_{selected_id}",
                disabled=not can_delete_personnel,
            )

            if update_clicked:
                assigned_id = rest_opts_with_blank.get(edit_restaurant) if role_requires_primary_restaurant_fn(effective_role) else None
                effective_monthly_cost = (
                    safe_float_fn(transition_monthly_cost, 0.0)
                    if role_changed and transition_enabled and is_fixed_cost_model_fn(edit_cost_model)
                    else safe_float_fn(edit_monthly_cost, 0.0)
                )
                validation_errors = validate_personnel_form_fn(
                    full_name=edit_name,
                    phone=edit_phone,
                    tc_no=edit_tc,
                    iban=edit_iban,
                    address=edit_address,
                    current_plate=edit_plate,
                    role=effective_role,
                    assigned_restaurant_id=assigned_id,
                    start_date_value=edit_start_date if isinstance(edit_start_date, date) else None,
                    vehicle_type=edit_vehicle,
                    motor_rental_monthly_amount=safe_float_fn(edit_motor_usage_payload["motor_rental_monthly_amount"], 0.0),
                    cost_model=edit_cost_model,
                    monthly_fixed_cost=effective_monthly_cost,
                    motor_purchase=edit_motor_purchase,
                    motor_purchase_start_date_value=edit_motor_purchase_start_date if isinstance(edit_motor_purchase_start_date, date) else None,
                    motor_purchase_commitment_months=safe_int_fn(edit_motor_purchase_commitment_months, 0),
                    motor_purchase_sale_price=safe_float_fn(edit_motor_purchase_sale_price, 0.0),
                )
                validation_errors.extend(
                    validate_role_transition_inputs_fn(
                        role_changed=role_changed,
                        transition_enabled=transition_enabled,
                        transition_previous_role=transition_previous_role,
                        effective_role=effective_role,
                        transition_effective_date=transition_effective_date if isinstance(transition_effective_date, date) else None,
                        start_date_value=edit_start_date if isinstance(edit_start_date, date) else None,
                    )
                )
                if motor_mode_changed and isinstance(edit_start_date, date) and edit_vehicle_transition_date < edit_start_date:
                    validation_errors.append("Motor düzeni başlangıç tarihi işe giriş tarihinden önce olamaz.")
                if validation_errors:
                    for error_text in validation_errors:
                        st.error(error_text)
                else:
                    try:
                        update_result = update_person_and_sync_fn(
                            conn,
                            person_id=selected_id,
                            original_row=row,
                            person_values={
                                "person_code": edit_code,
                                "full_name": edit_name,
                                "role": effective_role,
                                "status": edit_status,
                                "phone": edit_phone,
                                "address": edit_address,
                                "tc_no": edit_tc,
                                "iban": edit_iban,
                                "emergency_contact_name": edit_emergency_contact_name,
                                "emergency_contact_phone": edit_emergency_contact_phone,
                                "accounting_type": edit_accounting,
                                "new_company_setup": edit_new_company,
                                "accounting_revenue": edit_accounting_revenue,
                                "accountant_cost": edit_accountant_cost,
                                "company_setup_revenue": edit_company_setup_revenue,
                                "company_setup_cost": edit_company_setup_cost,
                                "assigned_restaurant_id": assigned_id,
                                "vehicle_type": edit_motor_usage_payload["vehicle_type"],
                                "motor_rental": edit_motor_usage_payload["motor_rental"],
                                "motor_purchase": edit_motor_usage_payload["motor_purchase"],
                                "motor_purchase_start_date": edit_motor_usage_payload["motor_purchase_start_date_str"],
                                "motor_purchase_commitment_months": edit_motor_usage_payload["motor_purchase_commitment_months"],
                                "motor_rental_monthly_amount": edit_motor_usage_payload["motor_rental_monthly_amount"],
                                "motor_purchase_sale_price": edit_motor_usage_payload["motor_purchase_sale_price"],
                                "motor_purchase_monthly_amount": edit_motor_usage_payload["motor_purchase_monthly_amount"],
                                "motor_purchase_installment_count": edit_motor_usage_payload["motor_purchase_installment_count"],
                                "current_plate": edit_plate,
                                "start_date": edit_start_date.isoformat() if isinstance(edit_start_date, date) else None,
                                "cost_model": normalize_cost_model_value_fn(edit_cost_model, effective_role),
                                "monthly_fixed_cost": effective_monthly_cost,
                                "notes": edit_notes,
                            },
                            role_changed=role_changed,
                            transition_enabled=transition_enabled,
                            transition_previous_role=transition_previous_role,
                            transition_effective_date=transition_effective_date if isinstance(transition_effective_date, date) else None,
                            is_fixed_cost_model_fn=is_fixed_cost_model_fn,
                            safe_float_fn=safe_float_fn,
                            safe_int_fn=safe_int_fn,
                            normalize_cost_model_value_fn=normalize_cost_model_value_fn,
                            record_person_role_transition_fn=record_person_role_transition_fn,
                            sync_person_current_role_snapshot_fn=sync_person_current_role_snapshot_fn,
                            motor_mode_changed=motor_mode_changed,
                            current_vehicle=current_vehicle,
                            current_motor_purchase=current_motor_purchase,
                            edit_vehicle_transition_date=edit_vehicle_transition_date,
                            auto_motor_rental_deduction=auto_motor_rental_deduction,
                            auto_motor_purchase_monthly_deduction=auto_motor_purchase_monthly_deduction,
                            record_person_vehicle_transition_fn=record_person_vehicle_transition_fn,
                            sync_person_current_vehicle_snapshot_fn=sync_person_current_vehicle_snapshot_fn,
                            sync_person_business_rules_fn=sync_person_business_rules_fn,
                        )
                    except Exception as exc:
                        st.error(f"Personel kartı güncellenemedi: {exc}")
                    else:
                        set_flash_message_fn("success", update_result.success_text)
                        st.rerun()

            if toggle_clicked:
                try:
                    toggle_result = toggle_person_status_and_sync_fn(
                        conn,
                        person_id=selected_id,
                        current_status=str(row["status"] or "Aktif"),
                        sync_person_business_rules_fn=sync_person_business_rules_fn,
                    )
                except Exception as exc:
                    st.error(f"Personel durumu güncellenemedi: {exc}")
                else:
                    set_flash_message_fn("success", toggle_result.success_text)
                    st.rerun()

            if delete_clicked:
                try:
                    delete_result = delete_person_with_dependencies_fn(
                        conn,
                        person_id=selected_id,
                        get_personnel_dependency_counts_fn=get_personnel_dependency_counts_fn,
                        delete_personnel_and_dependencies_fn=delete_personnel_and_dependencies_fn,
                    )
                except Exception as exc:
                    st.error(f"Personel silinemedi: {exc}")
                else:
                    set_flash_message_fn("success", delete_result.success_text)
                    st.rerun()

            render_personnel_equipment_section(
                conn,
                selected_id,
                can_create_equipment=can_create_equipment,
                can_update_equipment=can_update_equipment,
                can_delete_equipment=can_delete_equipment,
                issue_items=issue_items,
                get_equipment_cost_snapshot_fn=get_equipment_cost_snapshot_fn,
                get_default_equipment_unit_cost_fn=get_default_equipment_unit_cost_fn,
                get_default_equipment_sale_price_fn=get_default_equipment_sale_price_fn,
                get_default_issue_installment_count_fn=get_default_issue_installment_count_fn,
                latest_average_cost_fn=latest_average_cost_fn,
                get_equipment_vat_rate_fn=get_equipment_vat_rate_fn,
                safe_int_fn=safe_int_fn,
                safe_float_fn=safe_float_fn,
                fmt_number_fn=fmt_number_fn,
                fmt_try_fn=fmt_try_fn,
                normalize_equipment_issue_installment_count_fn=normalize_equipment_issue_installment_count_fn,
                equipment_issue_generates_installments_fn=equipment_issue_generates_installments_fn,
                insert_equipment_issue_and_get_id_fn=insert_equipment_issue_and_get_id_fn,
                post_equipment_installments_fn=post_equipment_installments_fn,
                set_flash_message_fn=set_flash_message_fn,
                fetch_df_fn=fetch_df_fn,
                format_display_df_fn=format_display_df_fn,
                build_grid_rows_fn=build_grid_rows_fn,
                render_dashboard_data_grid_fn=render_dashboard_data_grid_fn,
                update_equipment_issue_record_fn=update_equipment_issue_record_fn,
                delete_equipment_issue_records_fn=delete_equipment_issue_records_fn,
                parse_date_value_fn=parse_date_value_fn,
            )

            render_personnel_box_return_section(
                conn,
                selected_id,
                can_box_return=can_box_return,
                fetch_df_fn=fetch_df_fn,
                safe_int_fn=safe_int_fn,
                format_display_df_fn=format_display_df_fn,
                build_grid_rows_fn=build_grid_rows_fn,
                render_dashboard_data_grid_fn=render_dashboard_data_grid_fn,
                set_flash_message_fn=set_flash_message_fn,
            )


def render_personnel_plate_workspace(
    conn: Any,
    *,
    can_update_personnel: bool,
    get_person_options_fn: Callable[[Any, bool], dict[str, int]],
    fetch_df_fn: Callable[[Any, str, tuple], pd.DataFrame],
    safe_int_fn: Callable[[Any, int], int],
    format_display_df_fn: Callable[..., pd.DataFrame],
    render_tab_header_fn: Callable[[str, str], None],
) -> None:
    render_tab_header_fn("Plaka ve Motor Geçmişi", "Aktif plaka değişimlerini kayıt altına al, geçmiş zimmet hareketlerini alttaki tabloda takip et.")
    person_opts = get_person_options_fn(conn, active_only=False)
    if not person_opts:
        st.info("Önce personel eklenmeli.")
        return

    with st.form("plate_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        person_label = c1.selectbox("Personel", list(person_opts.keys()))
        plate = c2.text_input("Yeni Plaka")
        reason = c3.selectbox("Sebep", ["Yeni zimmet", "Kaza", "Bakım", "Geçici değişim", "Diğer"])
        c4, c5 = st.columns(2)
        start_dt = c4.date_input("Başlangıç", value=date.today())
        end_dt = c5.date_input("Bitiş", value=None)
        if not can_update_personnel:
            st.caption("Personel guncelleme yetkin olmadigi icin plaka ekleme pasif.")
        submitted = st.form_submit_button(
            "Plaka Geçmişine Ekle",
            use_container_width=True,
            disabled=not can_update_personnel,
        )
        if submitted and plate:
            pid = person_opts[person_label]
            conn.execute("UPDATE plate_history SET active=0, end_date=? WHERE personnel_id=? AND active=1", (start_dt.isoformat(), pid))
            conn.execute(
                "INSERT INTO plate_history (personnel_id, plate, start_date, end_date, reason, active) VALUES (?, ?, ?, ?, ?, 1)",
                (pid, plate, start_dt.isoformat(), end_dt.isoformat() if isinstance(end_dt, date) else None, reason),
            )
            conn.execute("UPDATE personnel SET current_plate=? WHERE id=?", (plate, pid))
            conn.commit()
            st.success("Plaka geçmişi güncellendi.")
            st.rerun()

    plate_history_df = fetch_df_fn(
        conn,
        """
        SELECT ph.start_date, ph.end_date, p.full_name, ph.plate, ph.reason, ph.active
        FROM plate_history ph
        JOIN personnel p ON p.id = ph.personnel_id
        ORDER BY ph.start_date DESC, ph.id DESC
        """,
        (),
    )
    if plate_history_df.empty:
        return

    plate_history_df["durum_text"] = plate_history_df["active"].apply(lambda x: "Aktif" if safe_int_fn(x, 0) == 1 else "Kapandı")
    plate_display = format_display_df_fn(
        plate_history_df,
        rename_map={
            "start_date": "Başlangıç",
            "end_date": "Bitiş",
            "full_name": "Personel",
            "plate": "Plaka",
            "reason": "Sebep",
            "durum_text": "Durum",
        },
    )
    cols = ["Başlangıç", "Bitiş", "Personel", "Plaka", "Sebep", "Durum"]
    st.dataframe(plate_display[cols], use_container_width=True, hide_index=True)


def render_personnel_edit_sidebar(
    row: Any,
    role_history_rows: pd.DataFrame,
    *,
    role_requires_primary_restaurant_fn: Callable[[str], bool],
    format_motor_rental_summary_fn: Callable[[Any], str],
    format_motor_purchase_summary_fn: Callable[[Any], str],
    resolve_cost_role_option_fn: Callable[[str, str], str],
    format_display_df_fn: Callable[..., pd.DataFrame],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    cost_model_labels: dict[str, str],
) -> None:
    current_snapshot_items = [
        ("Kod", row["person_code"] or "-"),
        ("Durum", row["status"] or "-"),
    ]
    if role_requires_primary_restaurant_fn(str(row["role"] or "")):
        current_snapshot_items.append(("Restoran", row["restoran"] or "-"))
    current_snapshot_items.extend(
        [
            ("Motor", row["vehicle_type"] or "-"),
            ("Motor Kirası", format_motor_rental_summary_fn(row)),
            ("Çat Kapında Motor Satışı", format_motor_purchase_summary_fn(row)),
            ("Rol", resolve_cost_role_option_fn(str(row["cost_model"] or ""), str(row["role"] or "Kurye"))),
            ("Acil Durum Kişisi", row["emergency_contact_name"] or "-"),
        ]
    )
    render_record_snapshot_fn("Mevcut Kart", current_snapshot_items)
    if role_history_rows.empty:
        return

    st.markdown("##### Rol Geçmişi")
    role_history_display = format_display_df_fn(
        role_history_rows,
        currency_cols=["monthly_fixed_cost"],
        rename_map={
            "role": "Rol",
            "cost_model": "Maliyet Modeli",
            "monthly_fixed_cost": "Aylık Sabit Maliyet",
            "effective_date": "Başlangıç Tarihi",
            "notes": "Not",
        },
        value_maps={"cost_model": cost_model_labels},
    )
    st.dataframe(role_history_display, use_container_width=True, hide_index=True)


def render_personnel_box_return_section(
    conn: Any,
    selected_id: int,
    *,
    can_box_return: bool,
    fetch_df_fn: Callable[[Any, str, tuple], pd.DataFrame],
    safe_int_fn: Callable[[Any, int], int],
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    set_flash_message_fn: Callable[[str, str], None],
) -> None:
    st.markdown("##### Box Geri Alım")
    with st.form(f"edit_person_box_return_form_{selected_id}", clear_on_submit=True):
        r1, r2, r3 = st.columns(3)
        return_date = r1.date_input("Box Geri Alım Tarihi", value=date.today())
        condition_status = r2.selectbox("Box Durumu", ["Temiz", "Hasarlı", "Parasını istemedi"])
        return_quantity = r3.number_input("Box Adedi", min_value=1, value=1, step=1)
        r4, r5 = st.columns(2)
        payout_amount = r4.number_input("Ödenen Tutar", min_value=0.0, value=0.0, step=100.0)
        return_notes = r5.text_input("İade Notu")
        if not can_box_return:
            st.caption("Box geri alim kaydetme yetkin olmadigi icin buton pasif.")
        save_box_return_clicked = st.form_submit_button(
            "Box Geri Alımını Kaydet",
            use_container_width=True,
            disabled=not can_box_return,
        )
        if save_box_return_clicked:
            waived = 1 if condition_status == "Parasını istemedi" else 0
            conn.execute(
                """
                INSERT INTO box_returns (personnel_id, return_date, quantity, condition_status, payout_amount, waived, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (selected_id, return_date.isoformat(), int(return_quantity), condition_status, payout_amount, waived, return_notes),
            )
            conn.commit()
            set_flash_message_fn("success", "Box geri alımı personel kartından kaydedildi.")
            st.rerun()

    person_box_returns_df = fetch_df_fn(
        conn,
        """
        SELECT return_date, quantity, condition_status, payout_amount, waived, notes
        FROM box_returns
        WHERE personnel_id = ?
        ORDER BY return_date DESC, id DESC
        """,
        (selected_id,),
    )
    if person_box_returns_df.empty:
        return

    person_box_returns_df["waived_text"] = person_box_returns_df["waived"].apply(lambda x: "Evet" if safe_int_fn(x, 0) == 1 else "Hayır")
    box_return_display = format_display_df_fn(
        person_box_returns_df,
        currency_cols=["payout_amount"],
        number_cols=["quantity"],
        rename_map={
            "return_date": "Tarih",
            "quantity": "Adet",
            "condition_status": "Durum",
            "payout_amount": "Ödenen Tutar",
            "waived_text": "Parasını İstemedi",
            "notes": "Not",
        },
    )
    box_return_columns = ["Tarih", "Adet", "Durum", "Ödenen Tutar", "Parasını İstemedi", "Not"]
    render_dashboard_data_grid_fn(
        "Seçili Personelin Box İade Geçmişi",
        "Bu kart yalnızca seçili personelin box geri alım hareketlerini gösterir.",
        box_return_columns,
        build_grid_rows_fn(box_return_display[box_return_columns], box_return_columns),
        "Bu personele ait box geri alım kaydı yok.",
        muted_columns={"Not"},
    )


def render_personnel_equipment_section(
    conn: Any,
    selected_id: int,
    *,
    can_create_equipment: bool,
    can_update_equipment: bool,
    can_delete_equipment: bool,
    issue_items: list[str],
    get_equipment_cost_snapshot_fn: Callable[[Any, str], tuple[Any, Any, Any, float]],
    get_default_equipment_unit_cost_fn: Callable[[Any, str], float],
    get_default_equipment_sale_price_fn: Callable[[str], float],
    get_default_issue_installment_count_fn: Callable[[str], int],
    latest_average_cost_fn: Callable[[Any, str], float],
    get_equipment_vat_rate_fn: Callable[[str, Any], float],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    fmt_number_fn: Callable[[Any], str],
    fmt_try_fn: Callable[[Any], str],
    normalize_equipment_issue_installment_count_fn: Callable[[str, int], int],
    equipment_issue_generates_installments_fn: Callable[[str, float, int], bool],
    insert_equipment_issue_and_get_id_fn: Callable[..., int],
    post_equipment_installments_fn: Callable[..., None],
    set_flash_message_fn: Callable[[str, str], None],
    fetch_df_fn: Callable[[Any, str, tuple], pd.DataFrame],
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    update_equipment_issue_record_fn: Callable[..., bool],
    delete_equipment_issue_records_fn: Callable[[Any, list[int]], int],
    parse_date_value_fn: Callable[[Any], date | None],
) -> None:
    st.markdown("##### Ekipman ve İade")
    st.caption("Seçili personele ait ekipman satışlarını burada düzenleyebilir, box geri alımını aynı karttan kaydedebilirsin.")

    new_issue_prefix = f"edit_person_new_issue_{selected_id}"
    new_issue_item_key = f"{new_issue_prefix}_item"
    new_issue_last_item_key = f"{new_issue_prefix}_last_item"
    new_issue_qty_key = f"{new_issue_prefix}_quantity"
    new_issue_date_key = f"{new_issue_prefix}_date"
    new_issue_cost_key = f"{new_issue_prefix}_cost"
    new_issue_cost_snapshot_key = f"{new_issue_prefix}_cost_snapshot"
    new_issue_sale_key = f"{new_issue_prefix}_sale"
    new_issue_sale_type_key = f"{new_issue_prefix}_sale_type"
    new_issue_installment_key = f"{new_issue_prefix}_installment"
    new_issue_notes_key = f"{new_issue_prefix}_notes"

    if st.session_state.get(new_issue_item_key) not in issue_items:
        st.session_state[new_issue_item_key] = issue_items[0]
    if st.session_state.get(new_issue_last_item_key) not in issue_items:
        st.session_state[new_issue_last_item_key] = st.session_state.get(new_issue_item_key, issue_items[0])
    current_new_issue_item = st.session_state.get(new_issue_item_key, issue_items[0])
    current_new_issue_snapshot = get_equipment_cost_snapshot_fn(conn, current_new_issue_item)
    current_new_issue_average_cost = current_new_issue_snapshot[3]
    if new_issue_date_key not in st.session_state or not isinstance(st.session_state.get(new_issue_date_key), date):
        st.session_state[new_issue_date_key] = date.today()
    if new_issue_qty_key not in st.session_state:
        st.session_state[new_issue_qty_key] = 1
    if new_issue_cost_key not in st.session_state:
        st.session_state[new_issue_cost_key] = float(get_default_equipment_unit_cost_fn(conn, current_new_issue_item))
        st.session_state[new_issue_cost_snapshot_key] = current_new_issue_snapshot
    if new_issue_sale_key not in st.session_state:
        default_sale = get_default_equipment_sale_price_fn(current_new_issue_item) or st.session_state[new_issue_cost_key]
        st.session_state[new_issue_sale_key] = float(default_sale)
    if new_issue_sale_type_key not in st.session_state:
        st.session_state[new_issue_sale_type_key] = "Satış"
    if new_issue_installment_key not in st.session_state:
        st.session_state[new_issue_installment_key] = int(get_default_issue_installment_count_fn(current_new_issue_item))
    if new_issue_notes_key not in st.session_state:
        st.session_state[new_issue_notes_key] = ""
    if tuple(st.session_state.get(new_issue_cost_snapshot_key) or ()) != tuple(current_new_issue_snapshot):
        st.session_state[new_issue_cost_key] = float(current_new_issue_average_cost)
        st.session_state[new_issue_cost_snapshot_key] = current_new_issue_snapshot

    st.markdown("###### Yeni ekipman hareketi ekle")
    add1, add2, add3 = st.columns(3)
    new_issue_date = add1.date_input("Teslim / satış tarihi", key=new_issue_date_key)
    new_issue_item = add2.selectbox("Ürün", issue_items, key=new_issue_item_key)
    if st.session_state.get(new_issue_last_item_key) != new_issue_item:
        refreshed_snapshot = get_equipment_cost_snapshot_fn(conn, new_issue_item)
        refreshed_cost = refreshed_snapshot[3]
        if refreshed_cost <= 0:
            refreshed_cost = latest_average_cost_fn(conn, new_issue_item)
        refreshed_sale = get_default_equipment_sale_price_fn(new_issue_item) or refreshed_cost
        st.session_state[new_issue_cost_key] = float(refreshed_cost)
        st.session_state[new_issue_sale_key] = float(refreshed_sale)
        st.session_state[new_issue_cost_snapshot_key] = refreshed_snapshot
        st.session_state[new_issue_installment_key] = int(get_default_issue_installment_count_fn(new_issue_item))
        st.session_state[new_issue_last_item_key] = new_issue_item
    active_new_issue_snapshot = get_equipment_cost_snapshot_fn(conn, new_issue_item)
    active_new_issue_average_cost = active_new_issue_snapshot[3]
    new_issue_qty = add3.number_input("Adet", min_value=1, step=1, key=new_issue_qty_key)
    new_issue_vat_rate = get_equipment_vat_rate_fn(new_issue_item, new_issue_date)
    add4, add5, add6 = st.columns(3)
    new_issue_cost = add4.number_input("Birim maliyet", min_value=0.0, step=50.0, key=new_issue_cost_key)
    new_issue_sale = add5.number_input("Kuryeye satış fiyatı | KDV dahil", min_value=0.0, step=50.0, key=new_issue_sale_key)
    new_issue_sale_type = add6.selectbox("İşlem tipi", ["Satış", "Depozit / Teslim"], key=new_issue_sale_type_key)
    add7, add8, add9 = st.columns(3)
    installment_options = [1, 2, 3, 6, 12]
    new_issue_installment_value = safe_int_fn(
        st.session_state.get(new_issue_installment_key),
        get_default_issue_installment_count_fn(new_issue_item),
    )
    if new_issue_installment_value not in installment_options:
        new_issue_installment_value = get_default_issue_installment_count_fn(new_issue_item)
        st.session_state[new_issue_installment_key] = new_issue_installment_value
    if new_issue_sale_type == "Satış":
        add7.selectbox("Taksit sayısı", installment_options, key=new_issue_installment_key)
        new_issue_installment = safe_int_fn(st.session_state.get(new_issue_installment_key), new_issue_installment_value)
    else:
        add7.selectbox("Taksit sayısı", [1], index=0, disabled=True, key=f"{new_issue_prefix}_installment_disabled")
        new_issue_installment = 1
    add8.markdown(
        f"<div class='ck-inline-note'>Varsayılan KDV: %{fmt_number_fn(new_issue_vat_rate)}</div>",
        unsafe_allow_html=True,
    )
    if active_new_issue_average_cost > 0:
        add9.markdown(
            f"<div class='ck-inline-note'>Ağırlıklı maliyet referansı: {fmt_try_fn(active_new_issue_average_cost)}</div>",
            unsafe_allow_html=True,
        )
    new_issue_notes = st.text_input("Not", key=new_issue_notes_key)
    effective_new_issue_installment = normalize_equipment_issue_installment_count_fn(new_issue_sale_type, new_issue_installment)
    new_issue_total_sale = float(new_issue_qty) * float(new_issue_sale)
    generates_new_issue_installments = equipment_issue_generates_installments_fn(
        new_issue_sale_type,
        new_issue_total_sale,
        effective_new_issue_installment,
    )
    if new_issue_sale_type != "Satış":
        st.caption("Depozit / Teslim seçildiğinde bağlı zimmet taksiti oluşturulmaz.")
    add_issue_label = "Ekipman Hareketini Kaydet ve Taksit Oluştur" if generates_new_issue_installments else "Ekipman Hareketini Kaydet"
    if not can_create_equipment:
        st.caption("Ekipman hareketi olusturma yetkin olmadigi icin kaydetme butonu pasif.")
    if st.button(
        add_issue_label,
        key=f"{new_issue_prefix}_submit",
        use_container_width=True,
        disabled=not can_create_equipment,
    ):
        new_issue_id = insert_equipment_issue_and_get_id_fn(
            conn,
            selected_id,
            new_issue_date.isoformat(),
            new_issue_item,
            int(new_issue_qty),
            new_issue_cost,
            new_issue_sale,
            int(effective_new_issue_installment),
            new_issue_sale_type,
            new_issue_notes,
            vat_rate=new_issue_vat_rate,
        )
        post_equipment_installments_fn(
            conn,
            new_issue_id,
            selected_id,
            new_issue_date,
            new_issue_item,
            new_issue_total_sale,
            int(effective_new_issue_installment),
            new_issue_sale_type,
        )
        st.session_state[new_issue_qty_key] = 1
        st.session_state[new_issue_notes_key] = ""
        if generates_new_issue_installments:
            set_flash_message_fn(
                "success",
                f"Ekipman hareketi kaydedildi. Toplam satış: {fmt_try_fn(new_issue_total_sale)} | {effective_new_issue_installment} taksit oluşturuldu.",
            )
        else:
            set_flash_message_fn("success", f"Ekipman hareketi kaydedildi. Toplam işlem tutarı: {fmt_try_fn(new_issue_total_sale)}")
        st.rerun()

    person_issue_df = fetch_df_fn(
        conn,
        """
        SELECT id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, installment_count, sale_type, notes
        FROM courier_equipment_issues
        WHERE personnel_id = ?
        ORDER BY issue_date DESC, id DESC
        """,
        (selected_id,),
    )
    if person_issue_df.empty:
        st.info("Bu personele ait ekipman kaydı henüz yok. İşe girişte verilen ekipmanları personel kartından, sonraki hareketleri bu düzenleme alanından ekleyebilirsin.")
        return

    person_issue_display = format_display_df_fn(
        person_issue_df,
        currency_cols=["unit_cost", "unit_sale_price"],
        number_cols=["quantity", "installment_count"],
        percent_cols=["vat_rate"],
        rename_map={
            "issue_date": "Tarih",
            "item_name": "Ürün",
            "quantity": "Adet",
            "unit_cost": "Birim Maliyet",
            "unit_sale_price": "Birim Satış",
            "vat_rate": "KDV",
            "installment_count": "Taksit",
            "sale_type": "İşlem Tipi",
            "notes": "Not",
        },
    )
    person_issue_columns = ["Tarih", "Ürün", "Adet", "Birim Satış", "Taksit", "İşlem Tipi"]
    render_dashboard_data_grid_fn(
        "Seçili Personelin Ekipman Hareketleri",
        "Bu kartta yalnızca seçili personele ait ekipman kayıtları görünür.",
        person_issue_columns,
        build_grid_rows_fn(person_issue_display[person_issue_columns], person_issue_columns),
        "Bu personele ait ekipman kaydı yok.",
        muted_columns={"İşlem Tipi"},
    )

    person_issue_options = {
        f"{issue_row['issue_date']} | {issue_row['item_name']} | {safe_int_fn(issue_row['quantity'], 0)} adet | ID:{safe_int_fn(issue_row['id'], 0)}": int(issue_row["id"])
        for _, issue_row in person_issue_df.iterrows()
    }
    selected_issue_label = st.selectbox(
        "Düzenlenecek ekipman kaydı",
        list(person_issue_options.keys()),
        key=f"edit_person_issue_select_{selected_id}",
    )
    selected_issue_id = person_issue_options[selected_issue_label]
    selected_issue_row = person_issue_df.loc[person_issue_df["id"] == selected_issue_id].iloc[0]
    issue_date_value = parse_date_value_fn(selected_issue_row["issue_date"]) or date.today()
    current_issue_item = str(selected_issue_row["item_name"] or "")
    current_issue_item_options = issue_items
    current_issue_item_index = current_issue_item_options.index(current_issue_item) if current_issue_item in current_issue_item_options else 0
    issue_sale_type_value = str(selected_issue_row["sale_type"] or "Satış")
    issue_installment_options = [1, 2, 3, 6, 12]
    issue_installment_value = safe_int_fn(selected_issue_row["installment_count"], 1)
    if issue_installment_value not in issue_installment_options:
        issue_installment_value = 1

    d1, d2, d3 = st.columns(3)
    edit_issue_date = d1.date_input("Ekipman Tarihi", value=issue_date_value)
    edit_issue_item = d2.selectbox("Ekipman Ürünü", current_issue_item_options, index=current_issue_item_index)
    edit_issue_quantity = d3.number_input("Ekipman Adedi", min_value=1, value=max(safe_int_fn(selected_issue_row["quantity"], 1), 1), step=1)
    d4, d5, d6 = st.columns(3)
    edit_issue_cost = d4.number_input("Ekipman Birim Maliyeti", min_value=0.0, value=max(safe_float_fn(selected_issue_row["unit_cost"]), 0.0), step=50.0)
    edit_issue_sale = d5.number_input("Ekipman Birim Satışı", min_value=0.0, value=max(safe_float_fn(selected_issue_row["unit_sale_price"]), 0.0), step=50.0)
    edit_issue_vat = d6.selectbox("Ekipman KDV", [10.0, 20.0], index=0 if safe_float_fn(selected_issue_row["vat_rate"], 10.0) < 20 else 1, format_func=lambda x: f"%{fmt_number_fn(x)}")
    d7, d8, d9 = st.columns(3)
    edit_issue_sale_type = d7.selectbox("Ekipman İşlem Tipi", ["Satış", "Depozit / Teslim"], index=0 if issue_sale_type_value == "Satış" else 1)
    if edit_issue_sale_type == "Satış":
        edit_issue_installment = d8.selectbox("Ekipman Taksit Sayısı", issue_installment_options, index=issue_installment_options.index(issue_installment_value))
    else:
        d8.selectbox("Ekipman Taksit Sayısı", [1], index=0, disabled=True)
        edit_issue_installment = 1
    edit_issue_notes = d9.text_input("Ekipman Notu", value=str(selected_issue_row["notes"] or ""))
    e1, e2 = st.columns(2)
    if not can_update_equipment or not can_delete_equipment:
        st.caption("Yetkine gore bazi ekipman aksiyonlari pasif.")
    issue_update_clicked = e1.button(
        "Ekipman Kaydını Güncelle",
        use_container_width=True,
        key=f"edit_person_issue_update_{selected_issue_id}",
        disabled=not can_update_equipment,
    )
    issue_delete_clicked = e2.button(
        "Ekipman Kaydını Sil",
        use_container_width=True,
        key=f"edit_person_issue_delete_{selected_issue_id}",
        disabled=not can_delete_equipment,
    )
    if issue_update_clicked:
        updated = update_equipment_issue_record_fn(
            conn,
            selected_issue_id,
            issue_date_value=edit_issue_date,
            item_name=edit_issue_item,
            quantity=edit_issue_quantity,
            unit_cost=edit_issue_cost,
            unit_sale_price=edit_issue_sale,
            vat_rate=edit_issue_vat,
            installment_count=edit_issue_installment,
            sale_type=edit_issue_sale_type,
            notes=edit_issue_notes,
        )
        if updated:
            set_flash_message_fn("success", "Ekipman kaydı güncellendi.")
            st.rerun()
        st.error("Ekipman kaydı güncellenemedi.")
    if issue_delete_clicked:
        deleted_count = delete_equipment_issue_records_fn(conn, [selected_issue_id])
        if deleted_count > 0:
            set_flash_message_fn("success", "Ekipman kaydı ve bağlı taksitleri silindi.")
            st.rerun()
        st.error("Ekipman kaydı silinemedi.")
