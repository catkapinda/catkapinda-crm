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
