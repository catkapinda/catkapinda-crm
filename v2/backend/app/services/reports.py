from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.schemas.reports import (
    ReportCostEntry,
    ReportInvoiceEntry,
    ReportModelBreakdownEntry,
    ReportTopCourierEntry,
    ReportTopRestaurantEntry,
    ReportsDashboardResponse,
    ReportsModuleStatus,
    ReportsSummary,
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


def build_reports_status() -> ReportsModuleStatus:
    return ReportsModuleStatus(
        module="reports",
        status="active",
        next_slice="reports-dashboard",
    )


def build_reports_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None = None,
    limit: int = 24,
) -> ReportsDashboardResponse:
    _ensure_repo_root_on_path()
    from services.reporting_service import build_reports_workspace_payload, load_reporting_entries_and_month_options

    compat_conn = _build_compat_connection(conn)
    entries_df, month_options = load_reporting_entries_and_month_options(compat_conn)

    if not month_options:
        return ReportsDashboardResponse(
            module="reports",
            status="active",
            month_options=[],
            selected_month=None,
            summary=None,
            invoice_entries=[],
            cost_entries=[],
            model_breakdown=[],
            top_restaurants=[],
            top_couriers=[],
        )

    resolved_month = selected_month if selected_month in month_options else month_options[0]
    payload = build_reports_workspace_payload(compat_conn, entries_df, resolved_month)

    invoice_entries = [
        ReportInvoiceEntry(
            restaurant=str(row.get("restoran") or "-"),
            pricing_model=str(row.get("model") or "-"),
            total_hours=_safe_float(row.get("saat")),
            total_packages=_safe_float(row.get("paket")),
            net_invoice=_safe_float(row.get("kdv_haric")),
            gross_invoice=_safe_float(row.get("kdv_dahil")),
        )
        for _, row in payload.invoice_df.head(limit).iterrows()
    ] if not payload.invoice_df.empty else []

    cost_entries = [
        ReportCostEntry(
            personnel=str(row.get("personel") or "-"),
            role=str(row.get("rol") or "-"),
            total_hours=_safe_float(row.get("calisma_saati")),
            total_packages=_safe_float(row.get("paket")),
            total_deductions=_safe_float(row.get("kesinti")),
            net_cost=_safe_float(row.get("net_maliyet")),
            cost_model=str(row.get("maliyet_modeli") or "-"),
        )
        for _, row in payload.cost_df.head(limit).iterrows()
    ] if not payload.cost_df.empty else []

    model_breakdown = []
    if not payload.invoice_df.empty:
        model_df = (
            payload.invoice_df.groupby("model", dropna=False, as_index=False)
            .agg(
                restoran=("restoran", "nunique"),
                saat=("saat", "sum"),
                paket=("paket", "sum"),
                kdv_dahil=("kdv_dahil", "sum"),
            )
            .sort_values("kdv_dahil", ascending=False)
        )
        model_breakdown = [
            ReportModelBreakdownEntry(
                pricing_model=str(row.get("model") or "-"),
                restaurant_count=int(row.get("restoran") or 0),
                total_hours=_safe_float(row.get("saat")),
                total_packages=_safe_float(row.get("paket")),
                gross_invoice=_safe_float(row.get("kdv_dahil")),
            )
            for _, row in model_df.iterrows()
        ]

    top_restaurants = [
        ReportTopRestaurantEntry(
            restaurant=str(row.get("restoran") or "-"),
            pricing_model=str(row.get("model") or "-"),
            total_hours=_safe_float(row.get("saat")),
            total_packages=_safe_float(row.get("paket")),
            gross_invoice=_safe_float(row.get("kdv_dahil")),
        )
        for _, row in payload.invoice_df.sort_values("kdv_dahil", ascending=False).head(6).iterrows()
    ] if not payload.invoice_df.empty and "kdv_dahil" in payload.invoice_df.columns else []

    top_couriers = [
        ReportTopCourierEntry(
            personnel=str(row.get("personel") or "-"),
            role=str(row.get("rol") or "-"),
            total_hours=_safe_float(row.get("calisma_saati")),
            total_deductions=_safe_float(row.get("kesinti")),
            net_cost=_safe_float(row.get("net_maliyet")),
            cost_model=str(row.get("maliyet_modeli") or "-"),
        )
        for _, row in payload.cost_df.sort_values("net_maliyet", ascending=False).head(6).iterrows()
    ] if not payload.cost_df.empty and "net_maliyet" in payload.cost_df.columns else []

    summary = ReportsSummary(
        selected_month=resolved_month,
        restaurant_count=int(payload.invoice_df["restoran"].dropna().astype(str).nunique()) if not payload.invoice_df.empty and "restoran" in payload.invoice_df.columns else 0,
        courier_count=int(payload.cost_df["personel"].dropna().astype(str).nunique()) if not payload.cost_df.empty and "personel" in payload.cost_df.columns else 0,
        total_hours=_safe_float(payload.invoice_df["saat"].sum()) if not payload.invoice_df.empty and "saat" in payload.invoice_df.columns else 0.0,
        total_packages=_safe_float(payload.invoice_df["paket"].sum()) if not payload.invoice_df.empty and "paket" in payload.invoice_df.columns else 0.0,
        total_revenue=_safe_float(payload.revenue),
        total_personnel_cost=_safe_float(payload.personnel_cost),
        gross_profit=_safe_float(payload.gross_profit),
        side_income_net=_safe_float(payload.side_income_net),
    )

    return ReportsDashboardResponse(
        module="reports",
        status="active",
        month_options=month_options,
        selected_month=resolved_month,
        summary=summary,
        invoice_entries=invoice_entries,
        cost_entries=cost_entries,
        model_breakdown=model_breakdown,
        top_restaurants=top_restaurants,
        top_couriers=top_couriers,
    )
