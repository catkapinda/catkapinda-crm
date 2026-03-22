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
