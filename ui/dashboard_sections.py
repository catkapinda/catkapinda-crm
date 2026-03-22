from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st


def render_dashboard_summary_cards(
    *,
    missing_attendance_count: int,
    under_target_count: int,
    joker_usage_count: int,
    missing_personnel_count: int,
    missing_restaurant_count: int,
    month_revenue: float,
    month_operation_gap: float,
    shared_overhead_total: float,
    profit_df: pd.DataFrame,
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    fmt_try_fn: Callable[[Any], str],
) -> None:
    c_top_1, c_top_2 = st.columns([1.2, 1])
    with c_top_1:
        render_record_snapshot_fn(
            "Kritik Uyarılar",
            [
                ("Bugün puantaj bekleyen şube", missing_attendance_count),
                ("Hedef kadro altında kalan şube", under_target_count),
                ("Bugün joker kullanılan şube", joker_usage_count),
                ("Eksik personel kartı", missing_personnel_count),
                ("Eksik restoran kartı", missing_restaurant_count),
            ],
        )
    with c_top_2:
        render_record_snapshot_fn(
            "Bu Ay Yönetim Özeti",
            [
                ("Restoran faturası", fmt_try_fn(month_revenue)),
                ("Operasyon farkı", fmt_try_fn(month_operation_gap)),
                ("Ortak Operasyon Payı", fmt_try_fn(shared_overhead_total)),
                ("Kârlı restoran", len(profit_df[profit_df["brut_fark"] >= 0]) if not profit_df.empty else 0),
                ("Riskli restoran", len(profit_df[profit_df["brut_fark"] < 0]) if not profit_df.empty else 0),
            ],
        )


def render_dashboard_focus_sections(
    *,
    priority_alerts: list[dict[str, str]],
    brand_summary_df: pd.DataFrame,
    render_alert_stack_fn: Callable[[str, list[dict[str, str]]], None],
    render_dashboard_data_grid_fn: Callable[..., None],
    fmt_number_fn: Callable[[Any], str],
    fmt_try_fn: Callable[[Any], str],
) -> None:
    focus_col, brand_col = st.columns([1.05, 1.15], gap="large")
    with focus_col:
        render_alert_stack_fn("Bugün Acil Aksiyon", priority_alerts)
    with brand_col:
        with st.container(border=True):
            if brand_summary_df.empty:
                render_dashboard_data_grid_fn(
                    "Marka Bazlı Özet",
                    "Markaların bu ayki operasyon ve gelir fotoğrafını daha okunur kart satırlarında gör.",
                    ["Marka", "Şube", "Hacim", "Fatura", "Operasyon Farkı", "Durum"],
                    [],
                    "Marka bazlı özet için bu ay puantaj verisi oluşmadı.",
                    badge_columns={"Durum"},
                )
            else:
                brand_rows = [
                    {
                        "Marka": row["brand"],
                        "Şube": fmt_number_fn(row["restoran_sayisi"]),
                        "Hacim": f"{fmt_number_fn(row['paket'])} Paket | {fmt_number_fn(row['saat'])} Saat",
                        "Fatura": fmt_try_fn(row["toplam_fatura"]),
                        "Operasyon Farkı": fmt_try_fn(row["operasyon_farki"]),
                        "Durum": row["durum"],
                    }
                    for _, row in brand_summary_df.head(8).iterrows()
                ]
                render_dashboard_data_grid_fn(
                    "Marka Bazlı Özet",
                    "Markaların bu ayki operasyon ve gelir fotoğrafını daha okunur kart satırlarında gör.",
                    ["Marka", "Şube", "Hacim", "Fatura", "Operasyon Farkı", "Durum"],
                    brand_rows,
                    "Marka bazlı özet için bu ay puantaj verisi oluşmadı.",
                    badge_columns={"Durum"},
                )


def render_dashboard_activity_sections(
    *,
    entries_empty: bool,
    daily_trend: pd.DataFrame,
    month_perf: pd.DataFrame,
    render_dashboard_section_header_fn: Callable[[str, str], None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    fmt_number_fn: Callable[[Any], str],
) -> None:
    if entries_empty:
        st.info("Henüz günlük puantaj kaydı yok. İlk kayıtlar geldikçe dashboard operasyon akışını burada gösterecek.")

    c1, c2 = st.columns([1.45, 1], gap="large")
    with c1:
        with st.container(border=True):
            render_dashboard_section_header_fn("Son 14 Gün Paket Akışı", "Paket ritmindeki artış ve düşüşleri son iki haftada izle.")
            if daily_trend.empty:
                st.info("Grafik için son 14 günde puantaj verisi oluşmadı.")
            else:
                try:
                    import altair as alt

                    area = alt.Chart(daily_trend).mark_area(color="#9FD4FF", opacity=0.38).encode(
                        x=alt.X("gun:T", axis=alt.Axis(title=None, format="%d %b", labelColor="#6B7A90", tickColor="#DCE6F5")),
                        y=alt.Y("paket:Q", axis=alt.Axis(title=None, gridColor="#E6EEF9", labelColor="#6B7A90")),
                        tooltip=[alt.Tooltip("gun:T", title="Tarih"), alt.Tooltip("paket:Q", title="Paket", format=",.0f")],
                    )
                    line = alt.Chart(daily_trend).mark_line(color="#0C4BCB", strokeWidth=3, point=alt.OverlayMarkDef(color="#0C4BCB", filled=True, size=64)).encode(
                        x="gun:T",
                        y="paket:Q",
                        tooltip=[alt.Tooltip("gun:T", title="Tarih"), alt.Tooltip("paket:Q", title="Paket", format=",.0f"), alt.Tooltip("saat:Q", title="Saat", format=",.1f")],
                    )
                    chart = (area + line).properties(height=300).configure_view(strokeWidth=0)
                    st.altair_chart(chart, use_container_width=True)
                except Exception:
                    fallback = daily_trend[["gun_label", "paket"]].set_index("gun_label")
                    st.line_chart(fallback)
                st.caption("Grafik son 14 günlük toplam paket hareketini gösterir.")

    with c2:
        top_rows = [
            (row["restoran"], f"{fmt_number_fn(row['paket'])} Paket | {fmt_number_fn(row['saat'])} Saat")
            for _, row in month_perf.head(6).iterrows()
        ]
        render_record_snapshot_fn("Bu Ay En Yoğun Şubeler", top_rows or [("-", "Henüz veri yok")])


def render_dashboard_action_sections(
    *,
    missing_attendance_df: pd.DataFrame,
    under_target_df: pd.DataFrame,
    joker_usage_df: pd.DataFrame,
    safe_int_fn: Callable[[Any, int], int],
    fmt_number_fn: Callable[[Any], str],
    render_alert_stack_fn: Callable[[str, list[dict[str, str]], bool], None],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_dashboard_section_header_fn: Callable[[str, str], None],
) -> None:
    alerts_col, actions_col = st.columns([1.25, 1], gap="large")
    with alerts_col:
        with st.container(border=True):
            action_alerts = []
            for _, row in missing_attendance_df.head(5).iterrows():
                action_alerts.append(
                    {
                        "tone": "critical",
                        "badge": "Bugün",
                        "title": f"{row['brand']} - {row['branch']}",
                        "detail": "Bugün puantaj bekleniyor. Günlük kayıt henüz girilmedi.",
                    }
                )
            for _, row in under_target_df.head(5).iterrows():
                action_alerts.append(
                    {
                        "tone": "warning" if safe_int_fn(row["acik_kadro"], 0) < 2 else "critical",
                        "badge": "Kadro",
                        "title": f"{row['brand']} - {row['branch']}",
                        "detail": f"Hedef kadronun altında. Açık kadro: {safe_int_fn(row['acik_kadro'])}",
                    }
                )
            render_alert_stack_fn("Aksiyon Gerektiren Şubeler", action_alerts, border=False)

            if not joker_usage_df.empty:
                st.markdown("<div class='ck-dashboard-spacer-sm'></div>", unsafe_allow_html=True)
                joker_rows = [
                    {
                        "Şube": row["restoran"],
                        "Joker": fmt_number_fn(row["joker_sayisi"]),
                        "Paket": fmt_number_fn(row["paket"]),
                    }
                    for _, row in joker_usage_df.head(6).iterrows()
                ]
                render_dashboard_data_grid_fn(
                    "Bugün Joker Kullanılan Şubeler",
                    "Joker desteği alan şubeleri ve gün içi yükünü öne çıkar.",
                    ["Şube", "Joker", "Paket"],
                    joker_rows,
                    "Bugün joker kullanılan şube görünmüyor.",
                )

    with actions_col:
        with st.container(border=True):
            render_dashboard_section_header_fn("Hızlı Komuta Alanı", "Sık kullanılan ekranlara tek dokunuşla geç.")
            quick_actions = [
                ("Bugünkü Puantajı Aç", "Puantaj", "Günlük saha kaydına geç.", None),
                ("Yeni Personel Kartı", "Personel Yönetimi", "Yeni kurye veya yönetici ekle.", "add"),
                ("Yeni Şube Kartı", "Restoran Yönetimi", "Restoran anlaşma kartını aç.", None),
                ("Kesinti Kaydı Gir", "Kesinti Yönetimi", "Ay sonu kesintisini işle.", None),
                ("Personel Düzenlemeyi Aç", "Personel Yönetimi", "Sonradan verilen ekipman, iade ve düzeltmeleri personel kartından yönet.", "edit"),
                ("Aylık Raporu Aç", "Raporlar ve Karlılık", "Bu ayın kârlılık ekranına geç.", None),
            ]
            for index, (button_label, target_menu, subtitle, target_workspace) in enumerate(quick_actions):
                if st.button(button_label, key=f"dashboard_quick_action_{index}", use_container_width=True):
                    if target_workspace:
                        st.session_state["personnel_workspace_mode"] = target_workspace
                    st.session_state["ck_sidebar_target_menu"] = target_menu
                    st.rerun()
                st.caption(subtitle)


def render_dashboard_finance_and_hygiene_sections(
    *,
    month_revenue: float,
    month_operation_gap: float,
    shared_overhead_total: float,
    top_profit_items: list[tuple[str, str]],
    risk_items: list[tuple[str, str]],
    missing_personnel_df: pd.DataFrame,
    missing_restaurant_df: pd.DataFrame,
    render_dashboard_section_header_fn: Callable[[str, str], None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    render_dashboard_data_grid_fn: Callable[..., None],
    fmt_try_fn: Callable[[Any], str],
) -> None:
    finance_col, hygiene_col = st.columns([1.15, 0.85], gap="large")
    with finance_col:
        with st.container(border=True):
            render_dashboard_section_header_fn("Bu Ay Karlılık Özeti", "Gelir, operasyon farkı ve ortak destek maliyetini birlikte değerlendir.")
            metric_cols = st.columns(3)
            metric_cols[0].metric("Restoran Faturası", fmt_try_fn(month_revenue))
            metric_cols[1].metric("Operasyon Farkı", fmt_try_fn(month_operation_gap))
            metric_cols[2].metric("Ortak Operasyon Payı", fmt_try_fn(shared_overhead_total))
            c_profit, c_risk = st.columns(2)
            with c_profit:
                render_record_snapshot_fn("En Kârlı 5 Restoran", top_profit_items)
            with c_risk:
                render_record_snapshot_fn("En Riskli 5 Restoran", risk_items)

    with hygiene_col:
        with st.container(border=True):
            render_dashboard_section_header_fn("Kart ve Zimmet Kontrolü", "Eksik alanlı personel ve restoran kartlarını düzenli tut.")
            render_record_snapshot_fn(
                "Veri Hijyeni",
                [
                    ("Eksik personel kartı", len(missing_personnel_df)),
                    ("Eksik restoran kartı", len(missing_restaurant_df)),
                ],
            )

            if not missing_personnel_df.empty:
                personnel_rows = [
                    {
                        "Personel": row["personel"],
                        "Rol": row["rol"],
                        "Eksik Alanlar": row["eksik_alanlar"],
                    }
                    for _, row in missing_personnel_df.head(6).iterrows()
                ]
                render_dashboard_data_grid_fn(
                    "Eksik Personel Kartları",
                    "Tamamlanması gereken aktif personel alanlarını hızlıca gör.",
                    ["Personel", "Rol", "Eksik Alanlar"],
                    personnel_rows,
                    "Eksik personel kartı görünmüyor.",
                    muted_columns={"Eksik Alanlar"},
                )
            elif not missing_restaurant_df.empty:
                restaurant_rows = [
                    {
                        "Restoran / Şube": row["restoran"],
                        "Eksik Alanlar": row["eksik_alanlar"],
                    }
                    for _, row in missing_restaurant_df.head(6).iterrows()
                ]
                render_dashboard_data_grid_fn(
                    "Eksik Restoran Kartları",
                    "İletişim ve vergi alanı eksik kalan şubeleri düzenle.",
                    ["Restoran / Şube", "Eksik Alanlar"],
                    restaurant_rows,
                    "Eksik restoran kartı görünmüyor.",
                    muted_columns={"Eksik Alanlar"},
                )
            else:
                st.success("Aktif kartlar tarafında öne çıkan kritik eksik görünmüyor.")
