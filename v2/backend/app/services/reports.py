from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.core.database import is_sqlite_backend
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
    if is_sqlite_backend(conn):
        return _build_local_reports_dashboard(conn, selected_month=selected_month, limit=limit)

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


def _build_local_reports_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    limit: int,
) -> ReportsDashboardResponse:
    month_rows = conn.execute(
        """
        SELECT DISTINCT substr(COALESCE(entry_date, ''), 1, 7) AS month_key
        FROM daily_entries
        WHERE COALESCE(entry_date, '') <> ''
        ORDER BY month_key DESC
        """
    ).fetchall()
    month_options = [str(row["month_key"]) for row in month_rows if row["month_key"]]
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
    invoice_rows = conn.execute(
        """
        SELECT
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            COALESCE(r.pricing_model, '-') AS pricing_model,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COALESCE(SUM(d.monthly_invoice_amount), 0) AS gross_invoice,
            COALESCE(SUM(
                CASE
                    WHEN COALESCE(r.vat_rate, 0) > 0
                        THEN d.monthly_invoice_amount / (1 + (r.vat_rate / 100.0))
                    ELSE d.monthly_invoice_amount
                END
            ), 0) AS net_invoice
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        WHERE substr(COALESCE(d.entry_date, ''), 1, 7) = %s
        GROUP BY restaurant, pricing_model
        ORDER BY gross_invoice DESC, restaurant
        """,
        (resolved_month,),
    ).fetchall()
    invoice_entries = [
        ReportInvoiceEntry(
            restaurant=str(row["restaurant"] or "-"),
            pricing_model=str(row["pricing_model"] or "-"),
            total_hours=_safe_float(row["total_hours"]),
            total_packages=_safe_float(row["total_packages"]),
            net_invoice=_safe_float(row["net_invoice"]),
            gross_invoice=_safe_float(row["gross_invoice"]),
        )
        for row in invoice_rows[:limit]
    ]

    attendance_rows = conn.execute(
        """
        SELECT
            COALESCE(actual_personnel_id, planned_personnel_id) AS personnel_id,
            COALESCE(SUM(worked_hours), 0) AS total_hours,
            COALESCE(SUM(package_count), 0) AS total_packages
        FROM daily_entries
        WHERE substr(COALESCE(entry_date, ''), 1, 7) = %s
          AND COALESCE(actual_personnel_id, planned_personnel_id) IS NOT NULL
        GROUP BY COALESCE(actual_personnel_id, planned_personnel_id)
        """,
        (resolved_month,),
    ).fetchall()
    deductions_rows = conn.execute(
        """
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_deductions
        FROM deductions
        WHERE substr(COALESCE(deduction_date, ''), 1, 7) = %s
          AND personnel_id IS NOT NULL
        GROUP BY personnel_id
        """,
        (resolved_month,),
    ).fetchall()
    personnel_rows = conn.execute(
        """
        SELECT
            id,
            COALESCE(full_name, '-') AS full_name,
            COALESCE(role, '-') AS role,
            COALESCE(monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(cost_model, '-') AS cost_model
        FROM personnel
        """
    ).fetchall()

    attendance_by_person = {
        int(row["personnel_id"]): {
            "total_hours": _safe_float(row["total_hours"]),
            "total_packages": _safe_float(row["total_packages"]),
        }
        for row in attendance_rows
        if row["personnel_id"] is not None
    }
    deductions_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_deductions"])
        for row in deductions_rows
        if row["personnel_id"] is not None
    }

    cost_entries: list[ReportCostEntry] = []
    for row in personnel_rows:
        person_id = int(row["id"])
        attendance = attendance_by_person.get(person_id, {})
        total_hours = _safe_float(attendance.get("total_hours"))
        total_packages = _safe_float(attendance.get("total_packages"))
        total_deductions = _safe_float(deductions_by_person.get(person_id))
        monthly_fixed_cost = _safe_float(row["monthly_fixed_cost"])
        net_cost = max(monthly_fixed_cost - total_deductions, 0.0)
        if total_hours <= 0 and total_packages <= 0 and monthly_fixed_cost <= 0 and total_deductions <= 0:
            continue
        cost_entries.append(
            ReportCostEntry(
                personnel=str(row["full_name"] or "-"),
                role=str(row["role"] or "-"),
                total_hours=total_hours,
                total_packages=total_packages,
                total_deductions=total_deductions,
                net_cost=net_cost,
                cost_model=str(row["cost_model"] or "-"),
            )
        )

    cost_entries.sort(key=lambda item: item.net_cost, reverse=True)
    cost_entries = cost_entries[:limit]

    model_totals: dict[str, dict[str, float | int]] = {}
    for row in invoice_entries:
        bucket = model_totals.setdefault(
            row.pricing_model,
            {
                "restaurant_count": 0,
                "total_hours": 0.0,
                "total_packages": 0.0,
                "gross_invoice": 0.0,
            },
        )
        bucket["restaurant_count"] = int(bucket["restaurant_count"]) + 1
        bucket["total_hours"] = float(bucket["total_hours"]) + row.total_hours
        bucket["total_packages"] = float(bucket["total_packages"]) + row.total_packages
        bucket["gross_invoice"] = float(bucket["gross_invoice"]) + row.gross_invoice

    model_breakdown = [
        ReportModelBreakdownEntry(
            pricing_model=pricing_model,
            restaurant_count=int(values["restaurant_count"]),
            total_hours=float(values["total_hours"]),
            total_packages=float(values["total_packages"]),
            gross_invoice=float(values["gross_invoice"]),
        )
        for pricing_model, values in sorted(
            model_totals.items(),
            key=lambda item: float(item[1]["gross_invoice"]),
            reverse=True,
        )
    ]

    total_revenue = sum(row.gross_invoice for row in invoice_entries)
    total_personnel_cost = sum(row.net_cost for row in cost_entries)
    side_income_net = sum(row.total_deductions for row in cost_entries)
    summary = ReportsSummary(
        selected_month=resolved_month,
        restaurant_count=len(invoice_entries),
        courier_count=len(cost_entries),
        total_hours=sum(row.total_hours for row in invoice_entries),
        total_packages=sum(row.total_packages for row in invoice_entries),
        total_revenue=total_revenue,
        total_personnel_cost=total_personnel_cost,
        gross_profit=total_revenue - total_personnel_cost,
        side_income_net=side_income_net,
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
        top_restaurants=[
            ReportTopRestaurantEntry(
                restaurant=row.restaurant,
                pricing_model=row.pricing_model,
                total_hours=row.total_hours,
                total_packages=row.total_packages,
                gross_invoice=row.gross_invoice,
            )
            for row in invoice_entries[:6]
        ],
        top_couriers=[
            ReportTopCourierEntry(
                personnel=row.personnel,
                role=row.role,
                total_hours=row.total_hours,
                total_deductions=row.total_deductions,
                net_cost=row.net_cost,
                cost_model=row.cost_model,
            )
            for row in cost_entries[:6]
        ],
    )
