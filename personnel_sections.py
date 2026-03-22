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

    new_person_defaults = {
        "new_person_full_name": "",
        "new_person_role": personnel_role_options[0],
        "new_person_phone": "",
        "new_person_assigned_label": "-",
        "new_person_tc_no": "",
        "new_person_iban": "",
        "new_person_address": "",
        "new_person_emergency_contact_name": "",
        "new_person_emergency_contact_phone": "",
        "new_person_accounting_type": "Kendi Muhasebecisi",
        "new_person_new_company_setup": "Hayır",
        "new_person_start_date": date.today(),
        "new_person_vehicle_type": "Çat Kapında",
        "new_person_motor_usage_mode": "Çat Kapında Motor Kirası",
        "new_person_motor_rental_monthly_amount": auto_motor_rental_deduction,
        "new_person_motor_purchase": "Hayır",
        "new_person_motor_purchase_start_date": date.today(),
        "new_person_motor_purchase_commitment_months": 12,
        "new_person_motor_purchase_sale_price": auto_motor_purchase_monthly_deduction,
        "new_person_accounting_revenue": 0.0,
        "new_person_accountant_cost": 0.0,
        "new_person_company_setup_revenue": 0.0,
        "new_person_company_setup_cost": 0.0,
        "new_person_monthly_fixed_cost": 0.0,
        "new_person_current_plate": "",
        "new_person_notes": "",
        "new_person_onboarding_items": [],
    }
    if st.session_state.pop("personnel_form_reset_pending", False):
        clear_new_person_onboarding_state_fn()
        for key, value in new_person_defaults.items():
            st.session_state[key] = value
    for key, value in new_person_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.get("new_person_accounting_type") not in ["Çat Kapında Muhasebe", "Kendi Muhasebecisi"]:
        st.session_state["new_person_accounting_type"] = "Kendi Muhasebecisi"

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

    create_clicked = st.button("Personel Kartını Oluştur", use_container_width=True, key="new_person_create")
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
        start_date_str = start_date.isoformat() if isinstance(start_date, date) else None
        auto_code = next_person_code_fn(conn, role)
        conn.execute(
            """
            INSERT INTO personnel (
                person_code, full_name, role, status, phone, address, tc_no, iban,
                emergency_contact_name, emergency_contact_phone,
                accounting_type, new_company_setup, accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost,
                assigned_restaurant_id, vehicle_type, motor_rental, motor_purchase, motor_purchase_start_date, motor_purchase_commitment_months,
                motor_rental_monthly_amount, motor_purchase_sale_price, motor_purchase_monthly_amount, motor_purchase_installment_count, current_plate, start_date,
                cost_model, monthly_fixed_cost, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auto_code,
                full_name,
                role,
                "Aktif",
                phone,
                address,
                tc_no,
                iban,
                emergency_contact_name,
                emergency_contact_phone,
                accounting_type,
                new_company_setup,
                accounting_revenue,
                accountant_cost,
                company_setup_revenue,
                company_setup_cost,
                assigned_id,
                motor_usage_payload["vehicle_type"],
                motor_usage_payload["motor_rental"],
                motor_usage_payload["motor_purchase"],
                motor_usage_payload["motor_purchase_start_date_str"],
                motor_usage_payload["motor_purchase_commitment_months"],
                motor_usage_payload["motor_rental_monthly_amount"],
                motor_usage_payload["motor_purchase_sale_price"],
                motor_usage_payload["motor_purchase_monthly_amount"],
                motor_usage_payload["motor_purchase_installment_count"],
                current_plate,
                start_date_str,
                normalize_cost_model_value_fn(cost_model, role),
                monthly_fixed_cost,
                notes,
            ),
        )
        conn.commit()
        created_person = conn.execute("SELECT * FROM personnel WHERE person_code = ? ORDER BY id DESC", (auto_code,)).fetchone()
        if not created_person:
            raise RuntimeError("Personel kaydı oluşturuldu ancak kayıt tekrar okunamadı.")
        created_person_id = safe_int_fn(created_person["id"], 0)
        for payload in onboarding_issue_payloads:
            issue_date_value = payload["issue_date"]
            quantity_value = safe_int_fn(payload["quantity"], 1)
            sale_price_value = safe_float_fn(payload["unit_sale_price"], 0.0)
            installment_count_value = safe_int_fn(payload["installment_count"], 1)
            vat_rate_value = safe_float_fn(payload["vat_rate"], 10.0)
            issue_id = insert_equipment_issue_and_get_id_fn(
                conn,
                created_person_id,
                issue_date_value.isoformat(),
                str(payload["item_name"] or ""),
                quantity_value,
                safe_float_fn(payload["unit_cost"], 0.0),
                sale_price_value,
                installment_count_value,
                "Satış",
                str(payload.get("notes", "") or ""),
                vat_rate=vat_rate_value,
            )
            post_equipment_installments_fn(
                conn,
                issue_id,
                created_person_id,
                issue_date_value,
                str(payload["item_name"] or ""),
                float(quantity_value) * float(sale_price_value),
                installment_count_value,
                "Satış",
            )
        sync_person_current_role_snapshot_fn(conn, created_person)
        conn.commit()
        sync_person_business_rules_fn(conn, created_person)
    except Exception as exc:
        conn.rollback()
        st.error(f"Personel kartı oluşturulamadı: {exc}")
        return

    equipment_summary = (
        f" | {len(onboarding_issue_payloads)} onboarding ekipmanı kaydedildi"
        if onboarding_issue_payloads
        else ""
    )
    success_text = f"{full_name} başarıyla eklendi. Kod: {auto_code}{equipment_summary}"
    st.session_state[workspace_key] = "add"
    st.session_state["person_search"] = ""
    st.session_state["person_role_filter"] = "Tümü"
    st.session_state["person_status_filter"] = "Tümü"
    st.session_state["person_rest_filter"] = "Tümü"
    st.session_state["personnel_recently_created"] = {"personnel_id": created_person_id}
    st.session_state["personnel_create_success_message"] = success_text
    st.session_state["personnel_form_reset_pending"] = True
    set_flash_message_fn("success", success_text)
    st.rerun()


def render_personnel_plate_workspace(
    conn: Any,
    *,
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
        submitted = st.form_submit_button("Plaka Geçmişine Ekle", use_container_width=True)
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
        save_box_return_clicked = st.form_submit_button("Box Geri Alımını Kaydet", use_container_width=True)
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
    if st.button(add_issue_label, key=f"{new_issue_prefix}_submit", use_container_width=True):
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
    issue_update_clicked = e1.button("Ekipman Kaydını Güncelle", use_container_width=True, key=f"edit_person_issue_update_{selected_issue_id}")
    issue_delete_clicked = e2.button("Ekipman Kaydını Sil", use_container_width=True, key=f"edit_person_issue_delete_{selected_issue_id}")
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
