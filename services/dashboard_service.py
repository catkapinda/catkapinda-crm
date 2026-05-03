from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

import pandas as pd

from services.attendance_service import NON_WORKING_ATTENDANCE_STATUSES

from repositories.dashboard_repository import (
    fetch_dashboard_active_restaurants,
    fetch_dashboard_deductions_for_period,
    fetch_dashboard_entries,
    fetch_dashboard_personnel,
    fetch_dashboard_role_history,
)
from rules.reporting_rules import build_invoice_summary_df, month_bounds


@dataclass
class DashboardWorkspacePayload:
    active_restaurants_df: pd.DataFrame
    personnel_df: pd.DataFrame
    role_history_df: pd.DataFrame
    month_deductions: pd.DataFrame
    entries: pd.DataFrame
    active_restaurants: int
    active_people: int
    today_working_people: int
    month_packages: float
    invoice_df: pd.DataFrame
    profit_df: pd.DataFrame
    shared_overhead_df: pd.DataFrame
    month_revenue: float
    month_operation_gap: float
    missing_attendance_df: pd.DataFrame
    under_target_df: pd.DataFrame
    joker_usage_df: pd.DataFrame
    missing_personnel_df: pd.DataFrame
    missing_restaurant_df: pd.DataFrame
    critical_alert_count: int
    top_profit_items: list[dict[str, Any]]
    risk_items: list[dict[str, Any]]
    priority_alerts: list[dict[str, Any]]
    brand_summary_df: pd.DataFrame
    shared_overhead_total: float
    entries_empty: bool
    daily_trend: pd.DataFrame
    month_perf: pd.DataFrame


def build_dashboard_workspace_payload(
    conn,
    *,
    today_value: date,
    parse_date_value_fn: Callable[[Any], date | None],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    role_requires_primary_restaurant_fn: Callable[[str], bool],
    fmt_try_fn: Callable[[Any], str],
    build_branch_profitability_fn: Callable[..., tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    build_dashboard_profit_snapshots_fn: Callable[..., tuple[list[dict[str, Any]], list[dict[str, Any]]]],
    build_dashboard_priority_alerts_fn: Callable[..., list[dict[str, Any]]],
    build_dashboard_brand_summary_fn: Callable[..., pd.DataFrame],
) -> DashboardWorkspacePayload:
    selected_month = today_value.strftime("%Y-%m")
    month_start, month_end = month_bounds(selected_month)

    entries = fetch_dashboard_entries(conn)
    active_restaurants_df = fetch_dashboard_active_restaurants(conn)
    personnel_df = fetch_dashboard_personnel(conn)
    role_history_df = fetch_dashboard_role_history(conn)
    month_deductions = fetch_dashboard_deductions_for_period(conn, month_start, month_end)

    for optional_column, default_value in {
        "company_title": "",
        "address": "",
        "contact_name": "",
        "contact_phone": "",
        "contact_email": "",
        "tax_office": "",
        "tax_number": "",
        "target_headcount": 0,
    }.items():
        if optional_column not in active_restaurants_df.columns:
            active_restaurants_df[optional_column] = default_value

    active_restaurants = len(active_restaurants_df)
    active_people_df = personnel_df[personnel_df["status"].fillna("").astype(str) == "Aktif"].copy() if not personnel_df.empty else pd.DataFrame()
    active_people = len(active_people_df)

    if not entries.empty:
        entries = entries.copy()
        entries["entry_date_value"] = pd.to_datetime(entries["entry_date"], errors="coerce").dt.date
        entries = entries[entries["entry_date_value"].notna()].copy()
    else:
        entries = pd.DataFrame(
            columns=[
                "entry_date",
                "entry_date_value",
                "restaurant_id",
                "actual_personnel_id",
                "status",
                "worked_hours",
                "package_count",
                "brand",
                "branch",
                "target_headcount",
                "pricing_model",
                "hourly_rate",
                "package_rate",
                "package_threshold",
                "package_rate_low",
                "package_rate_high",
                "fixed_monthly_fee",
                "vat_rate",
            ]
        )

    entries_empty = entries.empty
    month_entries = (
        entries[(entries["entry_date_value"] >= parse_date_value_fn(month_start)) & (entries["entry_date_value"] <= parse_date_value_fn(month_end))].copy()
        if not entries.empty
        else pd.DataFrame(columns=entries.columns)
    )
    today_entries = entries[entries["entry_date_value"] == today_value].copy() if not entries.empty else pd.DataFrame(columns=entries.columns)
    working_today_entries = (
        today_entries[
            (~today_entries["status"].fillna("").isin(list(NON_WORKING_ATTENDANCE_STATUSES)))
            | (today_entries["worked_hours"].fillna(0) > 0)
            | (today_entries["package_count"].fillna(0) > 0)
        ].copy()
        if not today_entries.empty
        else pd.DataFrame(columns=today_entries.columns)
    )

    today_working_people = (
        int(working_today_entries["actual_personnel_id"].dropna().astype(int).nunique())
        if not working_today_entries.empty and "actual_personnel_id" in working_today_entries.columns
        else 0
    )
    month_packages = float(month_entries["package_count"].sum()) if not month_entries.empty else 0.0

    invoice_df = build_invoice_summary_df(month_entries)
    profit_df, _, shared_overhead_df = build_branch_profitability_fn(
        month_entries,
        personnel_df,
        month_deductions,
        invoice_df,
        role_history_df,
        restaurants_df=active_restaurants_df,
    )
    month_revenue = float(invoice_df["kdv_dahil"].sum()) if not invoice_df.empty else 0.0
    month_operation_gap = float(profit_df["brut_fark"].sum()) if not profit_df.empty else 0.0

    today_restaurant_ids = (
        today_entries["restaurant_id"].dropna().astype(int).unique().tolist()
        if not today_entries.empty and "restaurant_id" in today_entries.columns
        else []
    )
    missing_attendance_df = (
        active_restaurants_df[~active_restaurants_df["id"].astype(int).isin(today_restaurant_ids)][["brand", "branch"]].copy()
        if not active_restaurants_df.empty
        else pd.DataFrame(columns=["brand", "branch"])
    )

    if not working_today_entries.empty:
        today_headcount_df = (
            working_today_entries.groupby("restaurant_id", dropna=False)["actual_personnel_id"]
            .nunique()
            .reset_index(name="bugun_kadro")
        )
    else:
        today_headcount_df = pd.DataFrame(columns=["restaurant_id", "bugun_kadro"])

    restaurant_headcount_df = active_restaurants_df[["id", "brand", "branch", "target_headcount"]].copy()
    restaurant_headcount_df["target_headcount"] = restaurant_headcount_df["target_headcount"].apply(lambda value: safe_int_fn(value, 0))
    under_target_df = restaurant_headcount_df.merge(
        today_headcount_df,
        how="left",
        left_on="id",
        right_on="restaurant_id",
    ).fillna({"bugun_kadro": 0})
    under_target_df["bugun_kadro"] = under_target_df["bugun_kadro"].apply(lambda value: safe_int_fn(value, 0))
    under_target_df["acik_kadro"] = under_target_df["target_headcount"] - under_target_df["bugun_kadro"]
    under_target_df = under_target_df[(under_target_df["target_headcount"] > 0) & (under_target_df["acik_kadro"] > 0)].copy()
    under_target_df = under_target_df.sort_values(["acik_kadro", "brand", "branch"], ascending=[False, True, True])

    people_lookup = personnel_df[["id", "full_name", "role"]].rename(
        columns={"id": "actual_personnel_id", "full_name": "personel", "role": "personel_rolu"}
    ) if not personnel_df.empty else pd.DataFrame(columns=["actual_personnel_id", "personel", "personel_rolu"])
    joker_usage_df = pd.DataFrame(columns=["restoran", "joker_sayisi", "paket"])
    if not working_today_entries.empty:
        joker_entries = working_today_entries.merge(people_lookup, how="left", on="actual_personnel_id")
        joker_entries = joker_entries[
            (joker_entries["status"].fillna("").astype(str) == "Joker")
            | (joker_entries["personel_rolu"].fillna("").astype(str) == "Joker")
        ].copy()
        if not joker_entries.empty:
            joker_usage_df = (
                joker_entries.groupby(["brand", "branch"], dropna=False)
                .agg(joker_sayisi=("actual_personnel_id", "nunique"), paket=("package_count", "sum"))
                .reset_index()
            )
            joker_usage_df["restoran"] = joker_usage_df["brand"] + " - " + joker_usage_df["branch"]
            joker_usage_df = joker_usage_df[["restoran", "joker_sayisi", "paket"]].sort_values(["joker_sayisi", "paket"], ascending=[False, False])

    missing_personnel_rows = []
    if not active_people_df.empty:
        for _, row in active_people_df.iterrows():
            missing_fields = []
            if not str(row.get("phone") or "").strip():
                missing_fields.append("Telefon")
            if not str(row.get("tc_no") or "").strip():
                missing_fields.append("TC")
            if not str(row.get("iban") or "").strip():
                missing_fields.append("IBAN")
            if not str(row.get("current_plate") or "").strip():
                missing_fields.append("Plaka")
            if role_requires_primary_restaurant_fn(str(row.get("role") or "")) and not safe_int_fn(row.get("assigned_restaurant_id"), 0):
                missing_fields.append("Ana restoran")
            if missing_fields:
                missing_personnel_rows.append(
                    {
                        "personel": str(row.get("full_name") or "-"),
                        "rol": str(row.get("role") or "-"),
                        "eksik_alanlar": ", ".join(missing_fields),
                    }
                )
    missing_personnel_df = pd.DataFrame(missing_personnel_rows)

    missing_restaurant_rows = []
    if not active_restaurants_df.empty:
        for _, row in active_restaurants_df.iterrows():
            missing_fields = []
            for field_label, field_name in [
                ("Yetkili", "contact_name"),
                ("Telefon", "contact_phone"),
                ("E-posta", "contact_email"),
                ("Ünvan", "company_title"),
                ("Adres", "address"),
                ("Vergi Dairesi", "tax_office"),
                ("Vergi No", "tax_number"),
            ]:
                if not str(row.get(field_name) or "").strip():
                    missing_fields.append(field_label)
            if missing_fields:
                missing_restaurant_rows.append(
                    {
                        "restoran": f"{row['brand']} - {row['branch']}",
                        "eksik_alanlar": ", ".join(missing_fields),
                    }
                )
    missing_restaurant_df = pd.DataFrame(missing_restaurant_rows)

    critical_alert_count = (
        len(missing_attendance_df)
        + len(under_target_df)
        + len(missing_personnel_df)
        + len(missing_restaurant_df)
    )

    top_profit_items, risk_items = build_dashboard_profit_snapshots_fn(profit_df, fmt_try_fn=fmt_try_fn)
    priority_alerts = build_dashboard_priority_alerts_fn(
        missing_attendance_df,
        under_target_df,
        profit_df,
        safe_int_fn=safe_int_fn,
        fmt_try_fn=fmt_try_fn,
    )
    brand_summary_df = build_dashboard_brand_summary_fn(
        month_entries,
        invoice_df,
        profit_df,
        safe_float_fn=safe_float_fn,
    )

    shared_overhead_total = float(shared_overhead_df["aylik_net_maliyet"].sum()) if not shared_overhead_df.empty else 0.0

    daily_trend = (
        entries.groupby("entry_date_value", dropna=False).agg(
            paket=("package_count", "sum"),
            saat=("worked_hours", "sum"),
        ).reset_index().rename(columns={"entry_date_value": "gun"})
        if not entries.empty
        else pd.DataFrame(columns=["gun", "paket", "saat"])
    )
    daily_trend = daily_trend.sort_values("gun").tail(14)
    if not daily_trend.empty:
        daily_trend["gun_label"] = pd.to_datetime(daily_trend["gun"]).dt.strftime("%d %b")

    month_perf = (
        month_entries.groupby(["brand", "branch"], dropna=False).agg(paket=("package_count", "sum"), saat=("worked_hours", "sum")).reset_index()
        if not month_entries.empty
        else pd.DataFrame(columns=["brand", "branch", "paket", "saat"])
    )
    if not month_perf.empty:
        month_perf["restoran"] = month_perf["brand"] + " - " + month_perf["branch"]
        month_perf = month_perf[["restoran", "paket", "saat"]].sort_values(["paket", "saat"], ascending=[False, False])

    return DashboardWorkspacePayload(
        active_restaurants_df=active_restaurants_df,
        personnel_df=personnel_df,
        role_history_df=role_history_df,
        month_deductions=month_deductions,
        entries=entries,
        active_restaurants=active_restaurants,
        active_people=active_people,
        today_working_people=today_working_people,
        month_packages=month_packages,
        invoice_df=invoice_df,
        profit_df=profit_df,
        shared_overhead_df=shared_overhead_df,
        month_revenue=month_revenue,
        month_operation_gap=month_operation_gap,
        missing_attendance_df=missing_attendance_df,
        under_target_df=under_target_df,
        joker_usage_df=joker_usage_df,
        missing_personnel_df=missing_personnel_df,
        missing_restaurant_df=missing_restaurant_df,
        critical_alert_count=critical_alert_count,
        top_profit_items=top_profit_items,
        risk_items=risk_items,
        priority_alerts=priority_alerts,
        brand_summary_df=brand_summary_df,
        shared_overhead_total=shared_overhead_total,
        entries_empty=entries_empty,
        daily_trend=daily_trend,
        month_perf=month_perf,
    )
