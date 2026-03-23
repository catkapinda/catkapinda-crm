from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st


def render_invoice_report_tab(
    invoice_df: pd.DataFrame,
    invoice_drilldown_map: dict[str, pd.DataFrame],
    invoice_attendance_export_map: dict[str, pd.DataFrame],
    selected_month: str,
    *,
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    pricing_model_labels: dict[str, str],
    fmt_number_fn: Callable[[Any], str],
    fmt_try_fn: Callable[[Any], str],
    build_restaurant_export_filename_fn: Callable[[str, str], str],
) -> None:
    open_restaurant = str(st.session_state.get("invoice_report_open_restaurant", "") or "")
    invoice_display_df = format_display_df_fn(
        invoice_df,
        currency_cols=["Restoran KDV Hariç", "Restoran KDV Dahil"],
        number_cols=["Toplam Saat", "Toplam Paket"],
        rename_map={
            "restoran": "Restoran / Şube",
            "model": "Fiyat Modeli",
            "saat": "Toplam Saat",
            "paket": "Toplam Paket",
            "kdv_haric": "Restoran KDV Hariç",
            "kdv_dahil": "Restoran KDV Dahil",
        },
        value_maps={"model": pricing_model_labels},
    )
    st.markdown(
        """
        <style>
        .invoice-report-shell {
            display: grid;
            gap: 14px;
        }
        .invoice-report-card {
            border: 1px solid rgba(207, 218, 238, 0.9);
            border-radius: 24px;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(247,250,255,0.98));
            box-shadow: 0 18px 34px rgba(15, 23, 42, 0.06);
            padding: 14px 16px 10px;
        }
        .invoice-model-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 7px 12px;
            border-radius: 999px;
            background: #EEF4FF;
            color: #0E4ACF;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.03em;
        }
        .invoice-metric-label {
            color: #62748E;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .invoice-metric-value {
            color: #12203A;
            font-size: 1.08rem;
            font-weight: 860;
            letter-spacing: -0.02em;
        }
        .invoice-metric-value.-strong {
            color: #0D4CCD;
            font-size: 1.2rem;
        }
        .invoice-detail-shell {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(222, 230, 244, 0.92);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if invoice_display_df is None or invoice_display_df.empty:
            st.info("Fatura görünümü için veri yok.")
        else:
            st.markdown("##### Restoran Faturası")
            st.caption("Restoran kartındaki şube adına tıklayarak hangi kurye kaç saat çalıştı, kaç paket attı detayını açıp kapatabilirsin.")
            st.markdown("<div class='invoice-report-shell'>", unsafe_allow_html=True)
            for row_index, row in invoice_display_df.iterrows():
                restaurant_name = str(row.get("Restoran / Şube", "-") or "-")
                model_name = str(row.get("Fiyat Modeli", "-") or "-")
                total_hours = str(row.get("Toplam Saat", "-") or "-")
                total_packages = str(row.get("Toplam Paket", "-") or "-")
                net_invoice = str(row.get("Restoran KDV Hariç", "-") or "-")
                gross_invoice = str(row.get("Restoran KDV Dahil", "-") or "-")
                is_open = open_restaurant == restaurant_name
                with st.container(border=True):
                    st.markdown("<div class='invoice-report-card'>", unsafe_allow_html=True)
                    head_col, metric1, metric2, metric3, metric4 = st.columns([3.2, 1, 1, 1.15, 1.25])
                    if head_col.button(
                        f"{'▾' if is_open else '▸'} {restaurant_name}",
                        key=f"invoice_toggle_{row_index}",
                        use_container_width=True,
                        type="primary" if is_open else "secondary",
                    ):
                        st.session_state["invoice_report_open_restaurant"] = "" if is_open else restaurant_name
                        st.rerun()
                    head_col.markdown(f"<div class='invoice-model-pill'>{model_name}</div>", unsafe_allow_html=True)
                    metric1.markdown("<div class='invoice-metric-label'>Toplam Saat</div>", unsafe_allow_html=True)
                    metric1.markdown(f"<div class='invoice-metric-value'>{total_hours}</div>", unsafe_allow_html=True)
                    metric2.markdown("<div class='invoice-metric-label'>Toplam Paket</div>", unsafe_allow_html=True)
                    metric2.markdown(f"<div class='invoice-metric-value'>{total_packages}</div>", unsafe_allow_html=True)
                    metric3.markdown("<div class='invoice-metric-label'>KDV Hariç</div>", unsafe_allow_html=True)
                    metric3.markdown(f"<div class='invoice-metric-value'>{net_invoice}</div>", unsafe_allow_html=True)
                    metric4.markdown("<div class='invoice-metric-label'>Restoran Faturası</div>", unsafe_allow_html=True)
                    metric4.markdown(f"<div class='invoice-metric-value -strong'>{gross_invoice}</div>", unsafe_allow_html=True)
                    if not is_open:
                        st.markdown("</div>", unsafe_allow_html=True)
                        continue
                    st.markdown("<div class='invoice-detail-shell'>", unsafe_allow_html=True)
                    detail_df = invoice_drilldown_map.get(restaurant_name, pd.DataFrame())
                    if detail_df.empty:
                        st.info("Bu restoran için kurye saat/paket kırılımı bulunamadı.")
                    else:
                        detail_display_df = format_display_df_fn(
                            detail_df,
                            currency_cols=["KDV Hariç", "KDV Dahil"],
                            number_cols=["Toplam Saat", "Toplam Paket"],
                            rename_map={
                                "personel": "Kurye",
                                "calisma_saati": "Toplam Saat",
                                "paket": "Toplam Paket",
                                "kdv_haric": "KDV Hariç",
                                "kdv_dahil": "KDV Dahil",
                            },
                        )
                        detail_columns = ["Kurye", "Toplam Saat", "Toplam Paket", "KDV Hariç", "KDV Dahil"]
                        render_dashboard_data_grid_fn(
                            f"{restaurant_name} Kurye Dağılımı",
                            "Bu şubede seçilen ay boyunca kurye bazında toplam saat, paket ve fatura katkısı.",
                            detail_columns,
                            build_grid_rows_fn(detail_display_df, detail_columns),
                            "Bu restoran için detay kırılımı yok.",
                        )
                    export_df = invoice_attendance_export_map.get(restaurant_name, pd.DataFrame())
                    if export_df is not None and not export_df.empty:
                        export_df = export_df.copy()
                        for number_column in ["Toplam Saat", "Toplam Paket"]:
                            if number_column in export_df.columns:
                                export_df[number_column] = export_df[number_column].apply(
                                    lambda value: fmt_number_fn(value) if pd.notna(value) else ""
                                )
                        for currency_column in ["KDV Hariç", "KDV Dahil"]:
                            if currency_column in export_df.columns:
                                export_df[currency_column] = export_df[currency_column].apply(fmt_try_fn)
                        st.download_button(
                            f"{restaurant_name} puantajını indir",
                            data=export_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name=build_restaurant_export_filename_fn(restaurant_name, selected_month),
                            mime="text/csv",
                            key=f"invoice_export_{row_index}",
                            use_container_width=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            "Fatura raporunu indir",
            data=invoice_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_fatura_{selected_month}.csv",
            mime="text/csv",
        )


def render_cost_report_tab(
    cost_df: pd.DataFrame,
    selected_month: str,
    *,
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    cost_model_labels: dict[str, str],
) -> None:
    cost_display_df = format_display_df_fn(
        cost_df,
        currency_cols=["Brüt Kurye Maliyeti", "Toplam Kesinti", "Net Kurye Maliyeti"],
        number_cols=["Toplam Saat", "Toplam Paket"],
        rename_map={
            "personel": "Personel",
            "rol": "Rol",
            "durum": "Durum",
            "calisma_saati": "Toplam Saat",
            "paket": "Toplam Paket",
            "brut_maliyet": "Brüt Kurye Maliyeti",
            "kesinti": "Toplam Kesinti",
            "net_maliyet": "Net Kurye Maliyeti",
            "maliyet_modeli": "Maliyet Modeli",
        },
        value_maps={"maliyet_modeli": cost_model_labels},
    )
    with st.container(border=True):
        cost_columns = ["Personel", "Rol", "Toplam Saat", "Toplam Paket", "Toplam Kesinti", "Net Kurye Maliyeti", "Maliyet Modeli"]
        render_dashboard_data_grid_fn(
            "Kurye Maliyeti",
            "Personel maliyetini, çalışma hacmi ve maliyet modeliyle birlikte daha güçlü bir listede gör.",
            cost_columns,
            build_grid_rows_fn(cost_display_df, cost_columns),
            "Kurye maliyet verisi bulunamadı.",
            muted_columns={"Maliyet Modeli"},
        )
        st.download_button(
            "Personel maliyet raporunu indir",
            data=cost_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_personel_maliyet_{selected_month}.csv",
            mime="text/csv",
        )


def render_profit_report_tab(
    profit_df: pd.DataFrame,
    selected_month: str,
    *,
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_executive_metrics_fn: Callable[..., None],
    fmt_try_fn: Callable[[Any], str],
    pricing_model_labels: dict[str, str],
) -> None:
    if profit_df.empty:
        st.info("Restoran kârlılığı için veri yok.")
        return

    render_executive_metrics_fn(
        [
            {
                "label": "En Yüksek Restoran Faturası",
                "value": fmt_try_fn(float(profit_df["kdv_dahil"].max())),
                "note": "KDV dahil en yüksek şube",
            },
            {
                "label": "En Yüksek Toplam Maliyet",
                "value": fmt_try_fn(float(profit_df["toplam_personel_maliyeti"].max())),
                "note": "Şube bazlı toplam yük",
                "tone": "warning",
            },
            {
                "label": "En Yüksek Brüt Fark",
                "value": fmt_try_fn(float(profit_df["brut_fark"].max())),
                "note": "En güçlü operasyon çıktısı",
                "tone": "positive",
            },
        ],
        title="Karlılık Nabzı",
        subtitle="Restoran kârlılık tablosundaki en güçlü öne çıkan üç sinyali izler.",
    )
    profit_display_df = format_display_df_fn(
        profit_df,
        currency_cols=["Restoran KDV Hariç", "Restoran KDV Dahil", "Doğrudan Personel Maliyeti", "Ortak Operasyon Payı", "Toplam Personel Maliyeti", "Brüt Fark"],
        percent_cols=["Kâr Marjı"],
        number_cols=["Toplam Saat", "Toplam Paket"],
        rename_map={
            "restoran": "Restoran / Şube",
            "saat": "Toplam Saat",
            "paket": "Toplam Paket",
            "kdv_haric": "Restoran KDV Hariç",
            "kdv_dahil": "Restoran KDV Dahil",
            "dogrudan_personel_maliyeti": "Doğrudan Personel Maliyeti",
            "paylasilan_yonetim_maliyeti": "Ortak Operasyon Payı",
            "toplam_personel_maliyeti": "Toplam Personel Maliyeti",
            "brut_fark": "Brüt Fark",
            "kar_marji_%": "Kâr Marjı",
            "model": "Fiyat Modeli",
        },
        value_maps={"model": pricing_model_labels},
    )
    with st.container(border=True):
        profit_columns = ["Restoran / Şube", "Restoran KDV Dahil", "Doğrudan Personel Maliyeti", "Ortak Operasyon Payı", "Brüt Fark", "Kâr Marjı"]
        render_dashboard_data_grid_fn(
            "Restoran Karlılığı",
            "Fatura ve maliyet tarafını aynı satırda görerek hangi şubenin gerçekten güçlü çalıştığını daha hızlı yorumla.",
            profit_columns,
            build_grid_rows_fn(profit_display_df, profit_columns),
            "Restoran kârlılığı için veri yok.",
            muted_columns={"Ortak Operasyon Payı"},
        )
        st.download_button(
            "Restoran kârlılık raporunu indir",
            data=profit_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_restoran_karlilik_{selected_month}.csv",
            mime="text/csv",
        )


def render_shared_overhead_report_tab(
    shared_overhead_df: pd.DataFrame,
    selected_month: str,
    *,
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_executive_metrics_fn: Callable[..., None],
    fmt_try_fn: Callable[[Any], str],
) -> None:
    if shared_overhead_df.empty:
        st.info("Bu ay ortak operasyon payı bulunmuyor.")
        return

    shared_total = float(shared_overhead_df["aylik_net_maliyet"].sum())
    allocated_count = int(shared_overhead_df["paylastirilan_restoran_sayisi"].max()) if not shared_overhead_df.empty else 0
    restaurant_share = (shared_total / allocated_count) if allocated_count > 0 else 0.0
    render_executive_metrics_fn(
        [
            {
                "label": "Toplam Ortak Operasyon Maliyeti",
                "value": fmt_try_fn(shared_total),
                "note": "Joker ve yönetim desteği toplamı",
            },
            {
                "label": "Paylaştırılan Restoran Sayısı",
                "value": allocated_count,
                "note": "Dönem içinde operasyonel kabul edilen şubeler",
            },
            {
                "label": "Restoran Başına Ortak Pay",
                "value": fmt_try_fn(restaurant_share),
                "note": "Şube başı ortak operasyon yükü",
                "tone": "warning",
            },
        ],
        title="Ortak Operasyon Özeti",
        subtitle="Joker ve Bölge Müdürü maliyetinin operasyonel restoran havuzuna nasıl dağıldığını özetler.",
    )
    shared_display_df = format_display_df_fn(
        shared_overhead_df,
        currency_cols=["Aylık Brüt Maliyet", "Toplam Kesinti", "Aylık Net Maliyet", "Restoran Başına Pay"],
        number_cols=["Paylaştırılan Restoran Sayısı"],
        rename_map={
            "personel": "Personel",
            "rol": "Rol",
            "aylik_brut_maliyet": "Aylık Brüt Maliyet",
            "toplam_kesinti": "Toplam Kesinti",
            "aylik_net_maliyet": "Aylık Net Maliyet",
            "paylastirilan_restoran_sayisi": "Paylaştırılan Restoran Sayısı",
            "restoran_basina_pay": "Restoran Başına Pay",
        },
    )
    with st.container(border=True):
        shared_columns = ["Personel", "Rol", "Aylık Net Maliyet", "Paylaştırılan Restoran Sayısı", "Restoran Başına Pay"]
        render_dashboard_data_grid_fn(
            "Ortak Operasyon Payı",
            "Paylaşılan yönetim yükünü kişi bazında ve restoran başına düşen etkiyle birlikte gör.",
            shared_columns,
            build_grid_rows_fn(shared_display_df, shared_columns),
            "Bu ay ortak operasyon payı bulunmuyor.",
        )
        st.download_button(
            "Ortak operasyon payını indir",
            data=shared_overhead_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_paylasilan_yonetim_{selected_month}.csv",
            mime="text/csv",
        )


def render_distribution_report_tab(
    person_distribution_df: pd.DataFrame,
    selected_month: str,
    *,
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    allocation_source_labels: dict[str, str],
) -> None:
    if person_distribution_df.empty:
        st.info("Personel-şube dağılımı için veri yok.")
        return

    distribution_display_df = format_display_df_fn(
        person_distribution_df,
        currency_cols=["Maliyet Payı"],
        number_cols=["Saat", "Paket"],
        rename_map={
            "restoran": "Restoran / Şube",
            "personel": "Personel",
            "rol": "Rol",
            "saat": "Saat",
            "paket": "Paket",
            "maliyet": "Maliyet Payı",
            "kaynak": "Maliyet Kaynağı",
        },
        value_maps={"kaynak": allocation_source_labels},
    )
    with st.container(border=True):
        distribution_columns = ["Restoran / Şube", "Personel", "Rol", "Saat", "Paket", "Maliyet Payı", "Maliyet Kaynağı"]
        render_dashboard_data_grid_fn(
            "Personel-Şube Dağılımı",
            "Personel maliyetinin şubelere nasıl dağıldığını daha seçilebilir bir yüzeyde incele.",
            distribution_columns,
            build_grid_rows_fn(distribution_display_df, distribution_columns),
            "Personel-şube dağılımı için veri yok.",
            muted_columns={"Maliyet Kaynağı"},
        )
        st.download_button(
            "Personel-şube dağılımını indir",
            data=person_distribution_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_personel_sube_dagilim_{selected_month}.csv",
            mime="text/csv",
        )


def render_side_income_report_tab(
    side_df: pd.DataFrame,
    equipment_profit_df: pd.DataFrame,
    equipment_purchase_df: pd.DataFrame,
    fuel_reflection_amount: float,
    *,
    format_display_df_fn: Callable[..., pd.DataFrame],
    build_grid_rows_fn: Callable[[pd.DataFrame, list[str]], list[dict[str, Any]]],
    render_dashboard_data_grid_fn: Callable[..., None],
    render_executive_metrics_fn: Callable[..., None],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    fmt_try_fn: Callable[[Any], str],
) -> None:
    render_executive_metrics_fn(
        [
            {
                "label": "Toplam Yan Gelir",
                "value": fmt_try_fn(float(side_df["gelir"].sum())),
                "note": "Yan gelir kalemleri toplamı",
            },
            {
                "label": "Toplam Yan Gelir Maliyeti",
                "value": fmt_try_fn(float(side_df["maliyet"].sum())),
                "note": "Eşlik eden toplam maliyet",
                "tone": "warning",
            },
            {
                "label": "Toplam Yan Gelir Neti",
                "value": fmt_try_fn(float(side_df["net_kar"].sum())),
                "note": "Net katkı görünümü",
                "tone": "positive" if float(side_df["net_kar"].sum()) >= 0 else "critical",
            },
        ],
        title="Yan Gelir Özeti",
        subtitle="Muhasebe, motor ve ekipman kaynaklı katkının üst görünümünü verir.",
    )
    side_display_df = format_display_df_fn(
        side_df,
        currency_cols=["Gelir", "Maliyet", "Net Kâr"],
        rename_map={"kalem": "Kalem", "gelir": "Gelir", "maliyet": "Maliyet", "net_kar": "Net Kâr"},
    )
    with st.container(border=True):
        side_columns = ["Kalem", "Gelir", "Maliyet", "Net Kâr"]
        render_dashboard_data_grid_fn(
            "Yan Gelir Analizi",
            "Yan gelir kalemlerini maliyet ve net katkı ile birlikte daha şık satırlarda gör.",
            side_columns,
            build_grid_rows_fn(side_display_df, side_columns),
            "Yan gelir analizi için veri yok.",
        )
    if fuel_reflection_amount > 0:
        render_record_snapshot_fn(
            "Yakıt Yansıtma Notu",
            [
                ("Toplam Yakıt Tahsilatı", fmt_try_fn(fuel_reflection_amount)),
                ("Durum", "Net yakıt marjı bu sürümde ayrı izlenmiyor"),
            ],
        )
    with st.expander("Ekipman ve Motor Detayı", expanded=False):
        st.caption("Detay görünümünde yalnızca `Satış` tipindeki ekipman ve motor hareketleri yer alır. `Depozit / Teslim` kayıtları bu kârlılık hesabına girmez.")
        if not equipment_profit_df.empty:
            equipment_sales_display = format_display_df_fn(
                equipment_profit_df,
                currency_cols=["total_cost", "total_sale", "gross_profit"],
                number_cols=["sold_qty"],
                rename_map={
                    "item_name": "Ürün",
                    "sold_qty": "Satılan Adet",
                    "total_cost": "Toplam Maliyet",
                    "total_sale": "Toplam Satış",
                    "gross_profit": "Brüt Kâr",
                },
            )
            equipment_sales_columns = ["Ürün", "Satılan Adet", "Toplam Maliyet", "Toplam Satış", "Brüt Kâr"]
            render_dashboard_data_grid_fn(
                "Ekipman ve Motor Satış Detayı",
                "Seçilen ay içinde satışa dönüşen ürünlerin detay katkısı.",
                equipment_sales_columns,
                build_grid_rows_fn(equipment_sales_display, equipment_sales_columns),
                "Bu ay satış tipinde ekipman veya motor hareketi görünmüyor.",
            )
        else:
            st.info("Seçilen ay için satış tipinde ekipman veya motor hareketi görünmüyor.")

        if not equipment_purchase_df.empty:
            purchase_display_df = format_display_df_fn(
                equipment_purchase_df,
                currency_cols=["purchased_total", "weighted_unit_cost"],
                number_cols=["purchased_qty"],
                rename_map={
                    "item_name": "Ürün",
                    "purchased_qty": "Alınan Adet",
                    "purchased_total": "Toplam Fatura",
                    "weighted_unit_cost": "Ağırlıklı Birim Maliyet",
                },
            )
            purchase_columns = ["Ürün", "Alınan Adet", "Toplam Fatura", "Ağırlıklı Birim Maliyet"]
            render_dashboard_data_grid_fn(
                "Satın Alma Maliyet Referansı",
                "Tüm satın alma geçmişine göre oluşan ağırlıklı maliyetleri yan gelir detayıyla birlikte değerlendir.",
                purchase_columns,
                build_grid_rows_fn(purchase_display_df, purchase_columns),
                "Henüz satın alma özeti yok.",
            )
        else:
            st.info("Satın alma maliyet referansı için ürün kaydı bulunmuyor.")
