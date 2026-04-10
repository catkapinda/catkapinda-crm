from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.schemas.payroll import (
    PayrollCostModelBreakdownEntry,
    PayrollDashboardResponse,
    PayrollEntry,
    PayrollModuleStatus,
    PayrollSummary,
    PayrollTopPersonnelEntry,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_repo_root_on_path() -> None:
    repo_root = str(_repo_root())
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _build_compat_connection(conn: psycopg.Connection):
    _ensure_repo_root_on_path()
    from infrastructure.db_engine import CompatConnection

    info = getattr(conn, "info", None)
    host = getattr(info, "host", "?") if info else "?"
    port = getattr(info, "port", 5432) if info else 5432
    dbname = getattr(info, "dbname", "postgres") if info else "postgres"
    user = getattr(info, "user", "?") if info else "?"
    cache_key = f"postgres:{host}:{port}/{dbname}:{user}"
    return CompatConnection(conn, "postgres", cache_key=cache_key)


def _safe_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return 0.0


_COST_MODEL_LABELS = {
    "standard_courier": "Standart Kurye",
    "fixed_monthly": "Sabit Aylık",
    "hourly_only": "Sadece Saatlik",
    "hourly_plus_package": "Saatlik + Paket",
}


def build_payroll_status() -> PayrollModuleStatus:
    return PayrollModuleStatus(
        module="payroll",
        status="active",
        next_slice="payroll-dashboard",
    )


def build_payroll_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None = None,
    role_filter: str | None = None,
    restaurant_filter: str | None = None,
    limit: int = 300,
) -> PayrollDashboardResponse:
    _ensure_repo_root_on_path()
    from engines.finance_engine import calculate_personnel_cost
    from rules.deduction_rules import filter_payroll_effective_deductions_df
    from rules.reporting_rules import month_bounds
    from services.reporting_service import load_monthly_payroll_source_payload

    compat_conn = _build_compat_connection(conn)
    payload = load_monthly_payroll_source_payload(compat_conn)

    if payload.entries.empty and payload.deductions.empty:
        return PayrollDashboardResponse(
            module="payroll",
            status="active",
            month_options=[],
            selected_month=None,
            role_options=[],
            restaurant_options=[],
            selected_role="Tümü",
            selected_restaurant="Tümü",
            summary=None,
            entries=[],
            cost_model_breakdown=[],
            top_personnel=[],
        )

    month_options = payload.month_options
    if not month_options:
        return PayrollDashboardResponse(
            module="payroll",
            status="active",
            month_options=[],
            selected_month=None,
            role_options=[],
            restaurant_options=[],
            selected_role="Tümü",
            selected_restaurant="Tümü",
            summary=None,
            entries=[],
            cost_model_breakdown=[],
            top_personnel=[],
        )

    resolved_month = selected_month if selected_month in month_options else month_options[0]
    selected_role = role_filter or "Tümü"
    selected_restaurant = restaurant_filter or "Tümü"

    entries = payload.entries.copy() if not payload.entries.empty else pd.DataFrame()
    deductions = payload.deductions.copy() if not payload.deductions.empty else pd.DataFrame()
    personnel_df = payload.personnel_df.copy() if not payload.personnel_df.empty else pd.DataFrame()
    role_history_df = payload.role_history_df.copy() if payload.role_history_df is not None and not payload.role_history_df.empty else pd.DataFrame()

    role_options = ["Tümü"]
    if not personnel_df.empty and "role" in personnel_df.columns:
        role_options.extend(sorted(personnel_df["role"].dropna().astype(str).unique().tolist()))
    role_options = list(dict.fromkeys(role_options))
    if selected_role not in role_options:
        selected_role = "Tümü"

    restaurant_options = ["Tümü"]
    if not entries.empty:
        entries["entry_date"] = pd.to_datetime(entries["entry_date"])
        restaurant_options.extend(
            sorted(
                (
                    entries["brand"].fillna("").astype(str)
                    + " - "
                    + entries["branch"].fillna("").astype(str)
                )
                .str.strip(" -")
                .replace("", pd.NA)
                .dropna()
                .unique()
                .tolist()
            )
        )
    restaurant_options = list(dict.fromkeys(restaurant_options))
    if selected_restaurant not in restaurant_options:
        selected_restaurant = "Tümü"

    start_date, end_date = month_bounds(resolved_month)
    month_entries = (
        entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy()
        if not entries.empty
        else pd.DataFrame()
    )
    month_deductions = (
        deductions[(deductions["deduction_date"] >= start_date) & (deductions["deduction_date"] <= end_date)].copy()
        if not deductions.empty
        else pd.DataFrame()
    )
    payroll_deductions = filter_payroll_effective_deductions_df(month_deductions, personnel_df)

    if selected_restaurant != "Tümü" and not month_entries.empty:
        month_entries = month_entries[
            (
                month_entries["brand"].fillna("").astype(str)
                + " - "
                + month_entries["branch"].fillna("").astype(str)
            )
            .str.strip(" -")
            == selected_restaurant
        ].copy()

    cost_df = calculate_personnel_cost(
        month_entries,
        personnel_df,
        payroll_deductions,
        role_history_df=role_history_df if not role_history_df.empty else None,
    )

    if not cost_df.empty and selected_role != "Tümü":
        cost_df = cost_df[cost_df["rol"].fillna("").astype(str).str.contains(selected_role, regex=False)].copy()

    if not month_entries.empty:
        by_person_branch = (
            month_entries.groupby("actual_personnel_id", dropna=False)
            .agg(restoran_sayisi=("restaurant_id", "nunique"))
            .reset_index()
            .rename(columns={"actual_personnel_id": "personnel_id"})
        )
        cost_df = cost_df.merge(by_person_branch, on="personnel_id", how="left")
        cost_df["restoran_sayisi"] = cost_df["restoran_sayisi"].fillna(0).astype(int)
    else:
        cost_df["restoran_sayisi"] = 0

    entries_payload = [
        PayrollEntry(
            personnel_id=int(row.get("personnel_id") or 0),
            personnel=str(row.get("personel") or "-"),
            role=str(row.get("rol") or "-"),
            status=str(row.get("durum") or "-"),
            total_hours=_safe_float(row.get("calisma_saati")),
            total_packages=_safe_float(row.get("paket")),
            gross_pay=_safe_float(row.get("brut_maliyet")),
            total_deductions=_safe_float(row.get("kesinti")),
            net_payment=_safe_float(row.get("net_maliyet")),
            restaurant_count=int(row.get("restoran_sayisi") or 0),
            cost_model=_COST_MODEL_LABELS.get(str(row.get("maliyet_modeli") or ""), str(row.get("maliyet_modeli") or "-")),
        )
        for _, row in cost_df.head(limit).iterrows()
    ] if not cost_df.empty else []

    cost_model_breakdown = []
    if not cost_df.empty:
        model_df = (
            cost_df.groupby("maliyet_modeli", dropna=False, as_index=False)
            .agg(
                personnel_count=("personnel_id", "nunique"),
                calisma_saati=("calisma_saati", "sum"),
                paket=("paket", "sum"),
                net_maliyet=("net_maliyet", "sum"),
            )
            .sort_values("net_maliyet", ascending=False)
        )
        cost_model_breakdown = [
            PayrollCostModelBreakdownEntry(
                cost_model=_COST_MODEL_LABELS.get(str(row.get("maliyet_modeli") or ""), str(row.get("maliyet_modeli") or "-")),
                personnel_count=int(row.get("personnel_count") or 0),
                total_hours=_safe_float(row.get("calisma_saati")),
                total_packages=_safe_float(row.get("paket")),
                net_payment=_safe_float(row.get("net_maliyet")),
            )
            for _, row in model_df.iterrows()
        ]

    top_personnel = [
        PayrollTopPersonnelEntry(
            personnel_id=int(row.get("personnel_id") or 0),
            personnel=str(row.get("personel") or "-"),
            role=str(row.get("rol") or "-"),
            total_hours=_safe_float(row.get("calisma_saati")),
            total_packages=_safe_float(row.get("paket")),
            total_deductions=_safe_float(row.get("kesinti")),
            net_payment=_safe_float(row.get("net_maliyet")),
            restaurant_count=int(row.get("restoran_sayisi") or 0),
            cost_model=_COST_MODEL_LABELS.get(str(row.get("maliyet_modeli") or ""), str(row.get("maliyet_modeli") or "-")),
        )
        for _, row in cost_df.sort_values("net_maliyet", ascending=False).head(8).iterrows()
    ] if not cost_df.empty and "net_maliyet" in cost_df.columns else []

    summary = None
    if not cost_df.empty:
        summary = PayrollSummary(
            selected_month=resolved_month,
            personnel_count=int(cost_df["personnel_id"].nunique()) if "personnel_id" in cost_df.columns else len(cost_df),
            total_hours=_safe_float(cost_df["calisma_saati"].sum()) if "calisma_saati" in cost_df.columns else 0.0,
            total_packages=_safe_float(cost_df["paket"].sum()) if "paket" in cost_df.columns else 0.0,
            gross_payroll=_safe_float(cost_df["brut_maliyet"].sum()) if "brut_maliyet" in cost_df.columns else 0.0,
            total_deductions=_safe_float(cost_df["kesinti"].sum()) if "kesinti" in cost_df.columns else 0.0,
            net_payment=_safe_float(cost_df["net_maliyet"].sum()) if "net_maliyet" in cost_df.columns else 0.0,
        )

    return PayrollDashboardResponse(
        module="payroll",
        status="active",
        month_options=month_options,
        selected_month=resolved_month,
        role_options=role_options,
        restaurant_options=restaurant_options,
        selected_role=selected_role,
        selected_restaurant=selected_restaurant,
        summary=summary,
        entries=entries_payload,
        cost_model_breakdown=cost_model_breakdown,
        top_personnel=top_personnel,
    )
