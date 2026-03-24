from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd

from rules.reporting_rules import (
    build_person_role_segments,
    calculate_standard_courier_cost,
    calculate_standard_package_cost,
    describe_cost_model_segments,
    describe_role_segments,
    get_operational_restaurant_names_for_period,
    infer_reporting_period,
)


_SAFE_INT: Callable[[Any, int], int] | None = None
_SAFE_FLOAT: Callable[[Any, float], float] | None = None
_IS_FIXED_COST_MODEL: Callable[[str], bool] | None = None
_CALCULATE_PRORATED_MONTHLY_COST: Callable[[float, date, date], float] | None = None
_SHARED_OVERHEAD_ROLES: set[str] = set()
_COURIER_HOURLY_COST = 250.0


def configure_finance_engine(
    *,
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    is_fixed_cost_model_fn: Callable[[str], bool],
    calculate_prorated_monthly_cost_fn: Callable[[float, date, date], float],
    shared_overhead_roles: set[str],
    courier_hourly_cost: float,
) -> None:
    global _SAFE_INT
    global _SAFE_FLOAT
    global _IS_FIXED_COST_MODEL
    global _CALCULATE_PRORATED_MONTHLY_COST
    global _SHARED_OVERHEAD_ROLES
    global _COURIER_HOURLY_COST

    _SAFE_INT = safe_int_fn
    _SAFE_FLOAT = safe_float_fn
    _IS_FIXED_COST_MODEL = is_fixed_cost_model_fn
    _CALCULATE_PRORATED_MONTHLY_COST = calculate_prorated_monthly_cost_fn
    _SHARED_OVERHEAD_ROLES = set(shared_overhead_roles)
    _COURIER_HOURLY_COST = float(courier_hourly_cost)


def calculate_personnel_cost(
    month_df: pd.DataFrame,
    personnel_df: pd.DataFrame,
    deductions_df: pd.DataFrame,
    role_history_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    results = []
    if personnel_df.empty:
        return pd.DataFrame()

    required_entry_columns = {
        "actual_personnel_id",
        "entry_date",
        "brand",
        "branch",
        "pricing_model",
        "worked_hours",
        "package_count",
    }
    if month_df is None or month_df.empty or not required_entry_columns.issubset(set(month_df.columns)):
        entry_rows = pd.DataFrame(
            columns=[
                "actual_personnel_id",
                "restaurant_id",
                "entry_date_value",
                "brand",
                "branch",
                "pricing_model",
                "worked_hours",
                "package_count",
            ]
        )
    else:
        entry_rows = month_df.copy()
        entry_rows["entry_date_value"] = pd.to_datetime(entry_rows["entry_date"], errors="coerce").dt.date
        entry_rows = entry_rows.dropna(subset=["entry_date_value"]).copy()
        if "restaurant_id" not in entry_rows.columns:
            entry_rows["restaurant_id"] = 0
        if "branch" not in entry_rows.columns:
            entry_rows["branch"] = ""

    if deductions_df is None or deductions_df.empty or not {"personnel_id", "amount"}.issubset(set(deductions_df.columns)):
        deduction_by_person = pd.DataFrame(columns=["personnel_id", "deduction_total"])
    else:
        deduction_by_person = deductions_df.groupby("personnel_id", dropna=False)["amount"].sum().reset_index(name="deduction_total")

    period_start, period_end = infer_reporting_period(month_df, deductions_df)

    for _, person in personnel_df.iterrows():
        person_id = person["id"]
        person_entries = entry_rows[entry_rows["actual_personnel_id"] == person_id].copy() if not entry_rows.empty else pd.DataFrame()
        worked_hours = float(person_entries["worked_hours"].sum()) if not person_entries.empty else 0.0
        packages = float(person_entries["package_count"].sum()) if not person_entries.empty else 0.0
        deductions = float(deduction_by_person.loc[deduction_by_person["personnel_id"] == person_id, "deduction_total"].sum()) if not deduction_by_person.empty else 0.0

        role_segments = build_person_role_segments(person, role_history_df, period_start, period_end)
        gross_cost = 0.0
        for segment in role_segments:
            segment_start = segment["start_date"]
            segment_end = segment["end_date"]
            segment_entries = (
                person_entries[
                    (person_entries["entry_date_value"] >= segment_start)
                    & (person_entries["entry_date_value"] <= segment_end)
                ].copy()
                if not person_entries.empty
                else pd.DataFrame()
            )
            if _IS_FIXED_COST_MODEL(str(segment["cost_model"] or "")):
                gross_cost += _CALCULATE_PRORATED_MONTHLY_COST(
                    _SAFE_FLOAT(segment["monthly_fixed_cost"], 0.0),
                    segment_start,
                    segment_end,
                )
                continue

            segment_hours = float(segment_entries["worked_hours"].sum()) if not segment_entries.empty else 0.0
            gross_cost += segment_hours * _COURIER_HOURLY_COST
            if not segment_entries.empty:
                package_groups = (
                    segment_entries.groupby(["restaurant_id", "brand", "branch", "pricing_model"], dropna=False)["package_count"]
                    .sum()
                    .reset_index()
                )
                for _, package_row in package_groups.iterrows():
                    gross_cost += calculate_standard_package_cost(
                        package_row["package_count"],
                        brand=package_row.get("brand", ""),
                        pricing_model=package_row.get("pricing_model", ""),
                    )

        net_cost = gross_cost - deductions
        role_label = describe_role_segments(role_segments, str(person["role"] or "Kurye"))
        model_label = describe_cost_model_segments(role_segments, str(person["cost_model"] or "standard_courier"))
        results.append(
            {
                "personnel_id": person_id,
                "personel": person["full_name"],
                "rol": role_label,
                "durum": person["status"],
                "calisma_saati": worked_hours,
                "paket": packages,
                "brut_maliyet": gross_cost,
                "kesinti": deductions,
                "net_maliyet": net_cost,
                "maliyet_modeli": model_label,
            }
        )
    return pd.DataFrame(results).sort_values(["rol", "personel"])


def build_branch_profitability(
    month_df: pd.DataFrame,
    personnel_df: pd.DataFrame,
    deductions_df: pd.DataFrame,
    invoice_df: pd.DataFrame,
    role_history_df: pd.DataFrame | None = None,
    restaurants_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if month_df.empty or invoice_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    entry_rows = month_df.copy()
    entry_rows["entry_date_value"] = pd.to_datetime(entry_rows["entry_date"], errors="coerce").dt.date
    entry_rows = entry_rows.dropna(subset=["entry_date_value"]).copy()
    restaurant_meta = month_df[["restaurant_id", "brand", "branch"]].drop_duplicates() if "restaurant_id" in month_df.columns else pd.DataFrame()
    period_start, period_end = infer_reporting_period(month_df, deductions_df)

    if deductions_df.empty:
        ded_by_person = pd.DataFrame(columns=["personnel_id", "toplam_kesinti"])
    else:
        ded_by_person = deductions_df.groupby("personnel_id", dropna=False)["amount"].sum().reset_index(name="toplam_kesinti")

    allocation_rows = []
    shared_overhead_rows = []
    invoiced_restaurants = sorted(invoice_df["restoran"].dropna().astype(str).unique().tolist())
    shared_overhead_restaurants = get_operational_restaurant_names_for_period(restaurants_df, period_start, period_end)
    if not shared_overhead_restaurants:
        shared_overhead_restaurants = invoiced_restaurants

    for _, person in personnel_df.iterrows():
        pid = _SAFE_INT(person["id"])
        if pid <= 0:
            continue
        person_entries = entry_rows[entry_rows["actual_personnel_id"] == pid].copy() if not entry_rows.empty else pd.DataFrame()
        total_ded = float(ded_by_person.loc[ded_by_person["personnel_id"] == pid, "toplam_kesinti"].sum()) if not ded_by_person.empty else 0.0
        role_segments = build_person_role_segments(person, role_history_df, period_start, period_end)

        fixed_segments = [segment for segment in role_segments if _IS_FIXED_COST_MODEL(str(segment.get("cost_model") or ""))]
        fixed_segment_gross_map: list[tuple[dict[str, Any], float]] = []
        total_fixed_gross = 0.0
        for segment in fixed_segments:
            segment_gross = _CALCULATE_PRORATED_MONTHLY_COST(
                _SAFE_FLOAT(segment.get("monthly_fixed_cost"), 0.0),
                segment["start_date"],
                segment["end_date"],
            )
            fixed_segment_gross_map.append((segment, segment_gross))
            total_fixed_gross += segment_gross

        for segment in role_segments:
            segment_start = segment["start_date"]
            segment_end = segment["end_date"]
            segment_entries = (
                person_entries[
                    (person_entries["entry_date_value"] >= segment_start)
                    & (person_entries["entry_date_value"] <= segment_end)
                ].copy()
                if not person_entries.empty
                else pd.DataFrame()
            )

            if not _IS_FIXED_COST_MODEL(str(segment.get("cost_model") or "")):
                if segment_entries.empty:
                    continue
                grouped_segment_entries = (
                    segment_entries.groupby(["brand", "branch", "pricing_model"], dropna=False)
                    .agg(saat=("worked_hours", "sum"), paket=("package_count", "sum"))
                    .reset_index()
                )
                for _, row in grouped_segment_entries.iterrows():
                    allocation_rows.append(
                        {
                            "restoran": f"{row['brand']} - {row['branch']}",
                            "personel": person.get("full_name") or "-",
                            "rol": segment["role"],
                            "saat": float(row["saat"] or 0),
                            "paket": float(row["paket"] or 0),
                            "maliyet": calculate_standard_courier_cost(
                                float(row["saat"] or 0),
                                total_packages=float(row["paket"] or 0),
                                brand=row["brand"],
                                pricing_model=row.get("pricing_model", ""),
                            ),
                            "kaynak": "Degisken maliyet",
                        }
                    )
                continue

            segment_gross = _CALCULATE_PRORATED_MONTHLY_COST(
                _SAFE_FLOAT(segment.get("monthly_fixed_cost"), 0.0),
                segment_start,
                segment_end,
            )
            segment_deduction_share = (total_ded * (segment_gross / total_fixed_gross)) if total_fixed_gross > 0 else 0.0
            segment_net = segment_gross - segment_deduction_share
            role_name = str(segment.get("role") or "")

            if role_name in _SHARED_OVERHEAD_ROLES and shared_overhead_restaurants:
                per_restaurant_share = segment_net / len(shared_overhead_restaurants)
                for restaurant_name in shared_overhead_restaurants:
                    allocation_rows.append(
                        {
                            "restoran": restaurant_name,
                            "personel": person["full_name"],
                            "rol": role_name,
                            "saat": 0.0,
                            "paket": 0.0,
                            "maliyet": per_restaurant_share,
                            "kaynak": "Paylasilan yonetim maliyeti",
                        }
                    )
                shared_overhead_rows.append(
                    {
                        "personel": person["full_name"],
                        "rol": role_name,
                        "donem": f"{segment_start.isoformat()} / {segment_end.isoformat()}",
                        "aylik_brut_maliyet": segment_gross,
                        "toplam_kesinti": segment_deduction_share,
                        "aylik_net_maliyet": segment_net,
                        "paylastirilan_restoran_sayisi": len(shared_overhead_restaurants),
                        "restoran_basina_pay": per_restaurant_share,
                    }
                )
                continue

            if not segment_entries.empty and float(segment_entries["worked_hours"].sum()) > 0:
                grouped_fixed_work = (
                    segment_entries.groupby(["brand", "branch"], dropna=False)
                    .agg(saat=("worked_hours", "sum"), paket=("package_count", "sum"))
                    .reset_index()
                )
                total_segment_hours = float(grouped_fixed_work["saat"].sum())
                for _, work_row in grouped_fixed_work.iterrows():
                    share = float(work_row["saat"] or 0) / total_segment_hours if total_segment_hours > 0 else 0.0
                    allocation_rows.append(
                        {
                            "restoran": f"{work_row['brand']} - {work_row['branch']}",
                            "personel": person["full_name"],
                            "rol": role_name,
                            "saat": float(work_row["saat"] or 0),
                            "paket": float(work_row["paket"] or 0),
                            "maliyet": segment_net * share,
                            "kaynak": "Sabit maliyet payi",
                        }
                    )
            else:
                rid = person.get("assigned_restaurant_id")
                row = restaurant_meta[restaurant_meta["restaurant_id"] == rid] if not restaurant_meta.empty else pd.DataFrame()
                if not row.empty:
                    brand = row.iloc[0]["brand"]
                    branch = row.iloc[0]["branch"]
                    allocation_rows.append(
                        {
                            "restoran": f"{brand} - {branch}",
                            "personel": person["full_name"],
                            "rol": role_name,
                            "saat": 0.0,
                            "paket": 0.0,
                            "maliyet": segment_net,
                            "kaynak": "Sabit maliyet tam atama",
                        }
                    )

    alloc_df = pd.DataFrame(allocation_rows)
    if alloc_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(shared_overhead_rows)

    direct_cost_df = (
        alloc_df[alloc_df["kaynak"] != "Paylasilan yonetim maliyeti"]
        .groupby("restoran", dropna=False)
        .agg(dogrudan_personel_maliyeti=("maliyet", "sum"))
        .reset_index()
    )
    shared_cost_df = (
        alloc_df[alloc_df["kaynak"] == "Paylasilan yonetim maliyeti"]
        .groupby("restoran", dropna=False)
        .agg(paylasilan_yonetim_maliyeti=("maliyet", "sum"))
        .reset_index()
    )

    profit_df = invoice_df.merge(direct_cost_df, how="left", on="restoran").merge(shared_cost_df, how="left", on="restoran")
    profit_df = profit_df.fillna({"dogrudan_personel_maliyeti": 0, "paylasilan_yonetim_maliyeti": 0})
    profit_df["toplam_personel_maliyeti"] = profit_df["dogrudan_personel_maliyeti"] + profit_df["paylasilan_yonetim_maliyeti"]
    profit_df["brut_fark"] = profit_df["kdv_dahil"] - profit_df["toplam_personel_maliyeti"]
    profit_df["kar_marji_%"] = profit_df.apply(lambda x: (x["brut_fark"] / x["kdv_dahil"] * 100) if x["kdv_dahil"] else 0, axis=1)
    profit_df = profit_df.sort_values("brut_fark", ascending=False)

    person_distribution = alloc_df.sort_values(["restoran", "rol", "personel"]).reset_index(drop=True)
    shared_overhead_df = pd.DataFrame(shared_overhead_rows).sort_values(["rol", "personel"]).reset_index(drop=True) if shared_overhead_rows else pd.DataFrame()
    return profit_df, person_distribution, shared_overhead_df
