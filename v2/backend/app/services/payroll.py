from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.core.database import is_sqlite_backend
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
    if is_sqlite_backend(conn):
        return _build_local_payroll_dashboard(
            conn,
            selected_month=selected_month,
            role_filter=role_filter,
            restaurant_filter=restaurant_filter,
            limit=limit,
        )

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


def _build_local_payroll_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    role_filter: str | None,
    restaurant_filter: str | None,
    limit: int,
) -> PayrollDashboardResponse:
    month_rows = conn.execute(
        """
        SELECT month_key
        FROM (
            SELECT DISTINCT substr(COALESCE(entry_date, ''), 1, 7) AS month_key
            FROM daily_entries
            WHERE COALESCE(entry_date, '') <> ''
            UNION
            SELECT DISTINCT substr(COALESCE(deduction_date, ''), 1, 7) AS month_key
            FROM deductions
            WHERE COALESCE(deduction_date, '') <> ''
        )
        WHERE month_key <> ''
        ORDER BY month_key DESC
        """
    ).fetchall()
    month_options = [str(row["month_key"]) for row in month_rows if row["month_key"]]
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

    role_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(role, '-') AS role
        FROM personnel
        WHERE COALESCE(role, '') <> ''
        ORDER BY role
        """
    ).fetchall()
    role_options = ["Tümü", *[str(row["role"]) for row in role_rows if row["role"]]]
    role_options = list(dict.fromkeys(role_options))
    if selected_role not in role_options:
        selected_role = "Tümü"

    restaurant_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        WHERE substr(COALESCE(d.entry_date, ''), 1, 7) = %s
        ORDER BY restaurant_label
        """,
        (resolved_month,),
    ).fetchall()
    restaurant_options = ["Tümü", *[str(row["restaurant_label"]) for row in restaurant_rows if row["restaurant_label"]]]
    restaurant_options = list(dict.fromkeys(restaurant_options))
    if selected_restaurant not in restaurant_options:
        selected_restaurant = "Tümü"

    attendance_query = """
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COUNT(DISTINCT d.restaurant_id) AS restaurant_count
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE substr(COALESCE(d.entry_date, ''), 1, 7) = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
    """
    attendance_params: list[object] = [resolved_month]
    if selected_restaurant != "Tümü":
        attendance_query += """
          AND COALESCE(r.brand || ' - ' || r.branch, '-') = %s
        """
        attendance_params.append(selected_restaurant)
    attendance_query += """
        GROUP BY COALESCE(d.actual_personnel_id, d.planned_personnel_id)
    """
    attendance_rows = conn.execute(attendance_query, tuple(attendance_params)).fetchall()

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
            COALESCE(status, '-') AS status,
            COALESCE(cost_model, '-') AS cost_model,
            COALESCE(monthly_fixed_cost, 0) AS monthly_fixed_cost
        FROM personnel
        """
    ).fetchall()

    attendance_by_person = {
        int(row["personnel_id"]): {
            "total_hours": _safe_float(row["total_hours"]),
            "total_packages": _safe_float(row["total_packages"]),
            "restaurant_count": int(row["restaurant_count"] or 0),
        }
        for row in attendance_rows
        if row["personnel_id"] is not None
    }
    deductions_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_deductions"])
        for row in deductions_rows
        if row["personnel_id"] is not None
    }

    personnel_index = {int(row["id"]): row for row in personnel_rows if row["id"] is not None}
    relevant_personnel_ids = sorted(set(attendance_by_person) | set(deductions_by_person))

    entries_payload: list[PayrollEntry] = []
    for person_id in relevant_personnel_ids:
        person = personnel_index.get(person_id)
        if person is None:
            continue
        role = str(person["role"] or "-")
        if selected_role != "Tümü" and role != selected_role:
            continue

        attendance = attendance_by_person.get(person_id, {})
        total_hours = _safe_float(attendance.get("total_hours"))
        total_packages = _safe_float(attendance.get("total_packages"))
        restaurant_count = int(attendance.get("restaurant_count") or 0)
        gross_pay = _safe_float(person["monthly_fixed_cost"])
        total_deductions = _safe_float(deductions_by_person.get(person_id))
        net_payment = max(gross_pay - total_deductions, 0.0)
        cost_model_key = str(person["cost_model"] or "-")

        entries_payload.append(
            PayrollEntry(
                personnel_id=person_id,
                personnel=str(person["full_name"] or "-"),
                role=role,
                status=str(person["status"] or "-"),
                total_hours=total_hours,
                total_packages=total_packages,
                gross_pay=gross_pay,
                total_deductions=total_deductions,
                net_payment=net_payment,
                restaurant_count=restaurant_count,
                cost_model=_COST_MODEL_LABELS.get(cost_model_key, cost_model_key),
            )
        )

    entries_payload.sort(key=lambda row: (-row.net_payment, row.personnel))
    entries_payload = entries_payload[:limit]

    cost_model_breakdown: list[PayrollCostModelBreakdownEntry] = []
    if entries_payload:
        grouped_entries: dict[str, dict[str, float | int]] = {}
        for entry in entries_payload:
            bucket = grouped_entries.setdefault(
                entry.cost_model,
                {
                    "personnel_count": 0,
                    "total_hours": 0.0,
                    "total_packages": 0.0,
                    "net_payment": 0.0,
                },
            )
            bucket["personnel_count"] = int(bucket["personnel_count"]) + 1
            bucket["total_hours"] = float(bucket["total_hours"]) + entry.total_hours
            bucket["total_packages"] = float(bucket["total_packages"]) + entry.total_packages
            bucket["net_payment"] = float(bucket["net_payment"]) + entry.net_payment

        cost_model_breakdown = [
            PayrollCostModelBreakdownEntry(
                cost_model=cost_model,
                personnel_count=int(values["personnel_count"]),
                total_hours=float(values["total_hours"]),
                total_packages=float(values["total_packages"]),
                net_payment=float(values["net_payment"]),
            )
            for cost_model, values in sorted(
                grouped_entries.items(),
                key=lambda item: float(item[1]["net_payment"]),
                reverse=True,
            )
        ]

    top_personnel = [
        PayrollTopPersonnelEntry(
            personnel_id=entry.personnel_id,
            personnel=entry.personnel,
            role=entry.role,
            total_hours=entry.total_hours,
            total_packages=entry.total_packages,
            total_deductions=entry.total_deductions,
            net_payment=entry.net_payment,
            restaurant_count=entry.restaurant_count,
            cost_model=entry.cost_model,
        )
        for entry in entries_payload[:8]
    ]

    summary = None
    if entries_payload:
        summary = PayrollSummary(
            selected_month=resolved_month,
            personnel_count=len(entries_payload),
            total_hours=_safe_float(sum(entry.total_hours for entry in entries_payload)),
            total_packages=_safe_float(sum(entry.total_packages for entry in entries_payload)),
            gross_payroll=_safe_float(sum(entry.gross_pay for entry in entries_payload)),
            total_deductions=_safe_float(sum(entry.total_deductions for entry in entries_payload)),
            net_payment=_safe_float(sum(entry.net_payment for entry in entries_payload)),
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
