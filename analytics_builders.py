from __future__ import annotations

from typing import Any, Callable

import pandas as pd


def build_dashboard_profit_snapshots(
    profit_df: pd.DataFrame,
    *,
    fmt_try_fn: Callable[[Any], str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    if profit_df is None or profit_df.empty:
        return [("-", "Henüz veri yok")], [("-", "Henüz veri yok")]

    top_profit_items = [
        (row["restoran"], fmt_try_fn(row["brut_fark"]))
        for _, row in profit_df.head(5).iterrows()
    ]
    risk_items = [
        (row["restoran"], fmt_try_fn(row["brut_fark"]))
        for _, row in profit_df.sort_values("brut_fark", ascending=True).head(5).iterrows()
    ]
    return top_profit_items, risk_items


def build_dashboard_priority_alerts(
    missing_attendance_df: pd.DataFrame,
    under_target_df: pd.DataFrame,
    profit_df: pd.DataFrame,
    *,
    safe_int_fn: Callable[[Any, int], int],
    fmt_try_fn: Callable[[Any], str],
) -> list[dict[str, str]]:
    priority_alerts: list[dict[str, str]] = []

    for _, row in missing_attendance_df.head(3).iterrows():
        priority_alerts.append(
            {
                "tone": "critical",
                "badge": "Bugün",
                "title": f"{row['brand']} - {row['branch']}",
                "detail": "Günlük puantaj kaydı henüz açılmadı. Gün sonu kapanışını geciktirebilir.",
            }
        )

    for _, row in under_target_df.head(3).iterrows():
        open_headcount = safe_int_fn(row["acik_kadro"], 0)
        priority_alerts.append(
            {
                "tone": "critical" if open_headcount >= 2 else "warning",
                "badge": "Kadro",
                "title": f"{row['brand']} - {row['branch']}",
                "detail": f"Hedef kadroya göre {open_headcount} kişilik açık görünüyor.",
            }
        )

    if profit_df is not None and not profit_df.empty:
        negative_profit_df = profit_df[profit_df["brut_fark"] < 0].sort_values("brut_fark", ascending=True).head(3)
        for _, row in negative_profit_df.iterrows():
            priority_alerts.append(
                {
                    "tone": "warning",
                    "badge": "Finans",
                    "title": str(row["restoran"] or "-"),
                    "detail": f"Bu ay operasyon farkı {fmt_try_fn(row['brut_fark'])} seviyesinde.",
                }
            )

    return priority_alerts


def build_dashboard_brand_summary(
    month_entries: pd.DataFrame,
    invoice_df: pd.DataFrame,
    profit_df: pd.DataFrame,
    *,
    safe_float_fn: Callable[[Any, float], float],
) -> pd.DataFrame:
    if month_entries is None or month_entries.empty:
        return pd.DataFrame()

    restaurant_brand_df = month_entries[["brand", "branch"]].drop_duplicates().copy()
    restaurant_brand_df["restoran"] = restaurant_brand_df["brand"] + " - " + restaurant_brand_df["branch"]

    brand_ops_df = (
        month_entries.groupby("brand", dropna=False)
        .agg(
            restoran_sayisi=("restaurant_id", "nunique"),
            paket=("package_count", "sum"),
            saat=("worked_hours", "sum"),
        )
        .reset_index()
    )
    brand_revenue_df = (
        invoice_df.merge(restaurant_brand_df[["restoran", "brand"]], how="left", on="restoran")
        .groupby("brand", dropna=False)
        .agg(toplam_fatura=("kdv_dahil", "sum"))
        .reset_index()
    ) if invoice_df is not None and not invoice_df.empty else pd.DataFrame(columns=["brand", "toplam_fatura"])
    brand_profit_agg_df = (
        profit_df.merge(restaurant_brand_df[["restoran", "brand"]], how="left", on="restoran")
        .groupby("brand", dropna=False)
        .agg(
            operasyon_farki=("brut_fark", "sum"),
            ortalama_marj=("kar_marji_%", "mean"),
        )
        .reset_index()
    ) if profit_df is not None and not profit_df.empty else pd.DataFrame(columns=["brand", "operasyon_farki", "ortalama_marj"])

    brand_summary_df = (
        brand_ops_df.merge(brand_revenue_df, how="left", on="brand")
        .merge(brand_profit_agg_df, how="left", on="brand")
        .fillna({"toplam_fatura": 0, "operasyon_farki": 0, "ortalama_marj": 0})
    )
    brand_summary_df["durum"] = brand_summary_df.apply(
        lambda row: "Kritik"
        if safe_float_fn(row["operasyon_farki"], 0.0) < 0
        else ("İzleme" if safe_float_fn(row["ortalama_marj"], 0.0) < 8 else "Sağlam"),
        axis=1,
    )
    return brand_summary_df.sort_values(["operasyon_farki", "paket"], ascending=[False, False]).reset_index(drop=True)


def split_equipment_profit_categories(
    equipment_profit_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if equipment_profit_df is None or equipment_profit_df.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    motor_rental_profit_df = equipment_profit_df[equipment_profit_df["item_name"] == "Motor Kirası"].copy()
    motor_sale_profit_df = equipment_profit_df[equipment_profit_df["item_name"] == "Motor Satın Alım"].copy()
    equipment_only_profit_df = equipment_profit_df[
        ~equipment_profit_df["item_name"].isin(["Motor Kirası", "Motor Satın Alım"])
    ].copy()
    return motor_rental_profit_df, motor_sale_profit_df, equipment_only_profit_df


def build_side_income_summary_df(
    *,
    accounting_rev: float,
    accountant_cost_total: float,
    setup_rev: float,
    setup_cost: float,
    motor_rental_rev: float,
    motor_rental_cost: float,
    motor_sale_rev: float,
    motor_sale_cost: float,
    equipment_rev: float,
    equipment_cost: float,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"kalem": "Muhasebe Hizmeti", "gelir": accounting_rev, "maliyet": accountant_cost_total, "net_kar": accounting_rev - accountant_cost_total},
            {"kalem": "Şirket Açılışı", "gelir": setup_rev, "maliyet": setup_cost, "net_kar": setup_rev - setup_cost},
            {"kalem": "Motor Kirası", "gelir": motor_rental_rev, "maliyet": motor_rental_cost, "net_kar": motor_rental_rev - motor_rental_cost},
            {"kalem": "Motor Satışı", "gelir": motor_sale_rev, "maliyet": motor_sale_cost, "net_kar": motor_sale_rev - motor_sale_cost},
            {"kalem": "Ekipman Satışları", "gelir": equipment_rev, "maliyet": equipment_cost, "net_kar": equipment_rev - equipment_cost},
        ]
    )
