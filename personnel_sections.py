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
