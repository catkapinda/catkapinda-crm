from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.core.database import is_sqlite_backend
from app.schemas.reports import (
    ReportCostEntry,
    ReportDistributionEntry,
    ReportInvoiceEntry,
    ReportModelBreakdownEntry,
    ReportProfitEntry,
    ReportSharedOverheadEntry,
    ReportSideIncomeEntry,
    ReportSideIncomeSnapshot,
    ReportTopCourierEntry,
    ReportTopRestaurantEntry,
    ReportsCoverageSummary,
    ReportsDashboardResponse,
    ReportsModuleStatus,
    ReportsSummary,
)


_ALLOCATION_SOURCE_LABELS = {
    "Degisken maliyet": "Değişken maliyet",
    "Sabit maliyet payi": "Sabit maliyet payı",
    "Sabit maliyet tam atama": "Sabit maliyet tam atama",
    "Paylasilan yonetim maliyeti": "Ortak Operasyon Payı",
}

_SHARED_OVERHEAD_ROLES = {"Joker", "Bölge Müdürü"}
_LOCAL_FUEL_DEDUCTION_TYPES = {"Yakit", "Yakıt"}
_LOCAL_PARTNER_CARD_DEDUCTION_TYPES = {"Partner Kart Indirimi", "Partner Kart İndirimi"}
_PACKAGE_THRESHOLD_DEFAULT = 390
_VAT_RATE_DEFAULT = 20.0
_COURIER_HOURLY_COST = 250.0
_COURIER_HOURLY_COST_DOGU_OTOMOTIV = 295.0
_COURIER_PACKAGE_COST_DEFAULT_LOW = 20.0
_COURIER_PACKAGE_COST_DEFAULT_HIGH = 25.0
_COURIER_PACKAGE_COST_QC = 25.0


def _empty_reports_coverage() -> ReportsCoverageSummary:
    return ReportsCoverageSummary(
        covered_restaurant_count=0,
        operational_restaurant_count=0,
    )


def _empty_side_income_snapshot() -> ReportSideIncomeSnapshot:
    return ReportSideIncomeSnapshot(
        fuel_reflection_amount=0.0,
        company_fuel_reflection_amount=0.0,
        utts_fuel_discount_amount=0.0,
        partner_card_discount_amount=0.0,
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


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _month_key_sql(column: str) -> str:
    return f"SUBSTR(CAST({column} AS TEXT), 1, 7)"


def _active_sql(column: str = "active") -> str:
    return f"COALESCE(LOWER(CAST({column} AS TEXT)), '1') IN ('1', 'true', 't', 'yes', 'evet')"


def _normalized_brand_key(brand: object) -> str:
    return str(brand or "").strip().lower()


def _is_quick_china_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) == "quick china"


def _is_dogu_otomotiv_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) in {"doğu otomotiv", "dogu otomotiv"}


def _calculate_standard_package_cost(total_packages: float, *, brand: object = "") -> float:
    package_total = float(total_packages or 0)
    if _is_dogu_otomotiv_brand(brand):
        return 0.0
    if _is_quick_china_brand(brand):
        return package_total * _COURIER_PACKAGE_COST_QC
    package_rate = (
        _COURIER_PACKAGE_COST_DEFAULT_LOW
        if package_total <= _PACKAGE_THRESHOLD_DEFAULT
        else _COURIER_PACKAGE_COST_DEFAULT_HIGH
    )
    return package_total * package_rate


def _calculate_standard_courier_cost(total_hours: float, total_packages: float, *, brand: object = "") -> float:
    hourly_cost = _COURIER_HOURLY_COST_DOGU_OTOMOTIV if _is_dogu_otomotiv_brand(brand) else _COURIER_HOURLY_COST
    return float(total_hours or 0) * hourly_cost + _calculate_standard_package_cost(total_packages, brand=brand)


def _is_fixed_cost_model(cost_model: object) -> bool:
    model = str(cost_model or "").strip()
    return model == "fixed_monthly" or model.startswith("fixed_")


def _calculate_personnel_gross_cost(
    *,
    cost_model: object,
    monthly_fixed_cost: float,
    total_hours: float,
    total_packages: float,
    segments: list[dict[str, object]],
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    has_attendance = total_hours > 0 or total_packages > 0
    if _is_fixed_cost_model(cost_model) and fixed_cost > 0:
        return fixed_cost
    if not has_attendance:
        return fixed_cost
    return _safe_float(
        sum(
            _calculate_standard_courier_cost(
                _safe_float(segment.get("total_hours")),
                _safe_float(segment.get("total_packages")),
                brand=segment.get("brand"),
            )
            for segment in segments
        )
    )


def _resolve_allocation_source_label(value: object) -> str:
    raw_value = str(value or "-")
    return _ALLOCATION_SOURCE_LABELS.get(raw_value, raw_value)


def _invoice_actor_key(row: dict[str, object]) -> str:
    actual_personnel_id = row.get("actual_personnel_id")
    planned_personnel_id = row.get("planned_personnel_id")
    if actual_personnel_id is not None:
        return f"actual:{actual_personnel_id}"
    if planned_personnel_id is not None:
        return f"planned:{planned_personnel_id}"
    return f"entry:{row.get('id', '')}"


def _fixed_monthly_fee_for_rows(rows: list[dict[str, object]], fallback_fee: float) -> float:
    positive_amount_rows = [
        row
        for row in rows
        if _safe_float(row.get("monthly_invoice_amount")) > 0
    ]
    if not positive_amount_rows:
        return _safe_float(fallback_fee)

    positive_amount_rows.sort(
        key=lambda row: (
            str(row.get("entry_date") or ""),
            _safe_int(row.get("id")),
        )
    )
    return _safe_float(positive_amount_rows[-1].get("monthly_invoice_amount"))


def _calculate_restaurant_invoice(rows: list[dict[str, object]]) -> tuple[float, float, float, float]:
    if not rows:
        return 0.0, 0.0, 0.0, 0.0

    first = rows[0]
    pricing_model = str(first.get("pricing_model") or "").strip()
    hourly_rate = _safe_float(first.get("hourly_rate"))
    package_rate = _safe_float(first.get("package_rate"))
    package_threshold = _safe_int(first.get("package_threshold"), _PACKAGE_THRESHOLD_DEFAULT)
    if package_threshold <= 0:
        package_threshold = _PACKAGE_THRESHOLD_DEFAULT
    package_rate_low = _safe_float(first.get("package_rate_low"))
    package_rate_high = _safe_float(first.get("package_rate_high"))
    fixed_monthly_fee = _safe_float(first.get("fixed_monthly_fee"))
    raw_vat_rate = first.get("vat_rate")
    vat_rate = _VAT_RATE_DEFAULT if raw_vat_rate in {None, ""} else _safe_float(raw_vat_rate)
    total_hours = sum(_safe_float(row.get("worked_hours")) for row in rows)
    total_packages = sum(_safe_float(row.get("package_count")) for row in rows)

    if pricing_model == "hourly_plus_package":
        subtotal = total_hours * hourly_rate + total_packages * package_rate
    elif pricing_model == "threshold_package":
        actor_totals: dict[str, dict[str, float]] = {}
        for row in rows:
            actor_bucket = actor_totals.setdefault(_invoice_actor_key(row), {"hours": 0.0, "packages": 0.0})
            actor_bucket["hours"] += _safe_float(row.get("worked_hours"))
            actor_bucket["packages"] += _safe_float(row.get("package_count"))
        subtotal = 0.0
        for values in actor_totals.values():
            actor_packages = values["packages"]
            actor_package_rate = package_rate_low if actor_packages <= package_threshold else package_rate_high
            subtotal += values["hours"] * hourly_rate + actor_packages * actor_package_rate
    elif pricing_model == "hourly_only":
        subtotal = total_hours * hourly_rate
    elif pricing_model == "fixed_monthly":
        subtotal = _fixed_monthly_fee_for_rows(rows, fixed_monthly_fee)
    else:
        subtotal = sum(_safe_float(row.get("monthly_invoice_amount")) for row in rows)

    grand_total = subtotal * (1 + (vat_rate / 100.0))
    return total_hours, total_packages, subtotal, grand_total


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

    try:
        _ensure_repo_root_on_path()
        from services.reporting_service import build_reports_workspace_payload, load_reporting_entries_and_month_options
    except ModuleNotFoundError:
        return _build_local_reports_dashboard(conn, selected_month=selected_month, limit=limit)

    compat_conn = _build_compat_connection(conn)
    try:
        entries_df, month_options = load_reporting_entries_and_month_options(compat_conn)
    except Exception:
        return _build_local_reports_dashboard(conn, selected_month=selected_month, limit=limit)

    if not month_options:
        return ReportsDashboardResponse(
            module="reports",
            status="active",
            month_options=[],
            selected_month=None,
            summary=None,
            invoice_entries=[],
            cost_entries=[],
            profit_entries=[],
            model_breakdown=[],
            top_restaurants=[],
            top_couriers=[],
            coverage=_empty_reports_coverage(),
            shared_overhead_entries=[],
            distribution_entries=[],
            side_income_entries=[],
            side_income_snapshot=_empty_side_income_snapshot(),
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

    profit_entries = [
        ReportProfitEntry(
            restaurant=str(row.get("restoran") or "-"),
            pricing_model=str(row.get("model") or "-"),
            total_hours=_safe_float(row.get("saat")),
            total_packages=_safe_float(row.get("paket")),
            net_invoice=_safe_float(row.get("kdv_haric")),
            gross_invoice=_safe_float(row.get("kdv_dahil")),
            direct_personnel_cost=_safe_float(row.get("dogrudan_personel_maliyeti")),
            shared_overhead_cost=_safe_float(row.get("paylasilan_yonetim_maliyeti")),
            total_personnel_cost=_safe_float(row.get("toplam_personel_maliyeti")),
            gross_profit=_safe_float(row.get("brut_fark")),
            profit_margin_percent=_safe_float(row.get("kar_marji_%")),
        )
        for _, row in payload.profit_df.sort_values("brut_fark", ascending=False).head(limit).iterrows()
    ] if not payload.profit_df.empty else []

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

    shared_overhead_entries = [
        ReportSharedOverheadEntry(
            personnel=str(row.get("personel") or "-"),
            role=str(row.get("rol") or "-"),
            gross_cost=_safe_float(row.get("aylik_brut_maliyet")),
            total_deductions=_safe_float(row.get("toplam_kesinti")),
            net_cost=_safe_float(row.get("aylik_net_maliyet")),
            allocated_restaurant_count=int(row.get("paylastirilan_restoran_sayisi") or 0),
            share_per_restaurant=_safe_float(row.get("restoran_basina_pay")),
        )
        for _, row in payload.shared_overhead_df.iterrows()
    ] if not payload.shared_overhead_df.empty else []

    distribution_entries = [
        ReportDistributionEntry(
            restaurant=str(row.get("restoran") or "-"),
            personnel=str(row.get("personel") or "-"),
            role=str(row.get("rol") or "-"),
            total_hours=_safe_float(row.get("saat")),
            total_packages=_safe_float(row.get("paket")),
            allocated_cost=_safe_float(row.get("maliyet")),
            allocation_source=_resolve_allocation_source_label(row.get("kaynak")),
        )
        for _, row in payload.person_distribution_df.head(limit * 3).iterrows()
    ] if not payload.person_distribution_df.empty else []

    side_income_entries = [
        ReportSideIncomeEntry(
            item=str(row.get("kalem") or "-"),
            revenue=_safe_float(row.get("gelir")),
            cost=_safe_float(row.get("maliyet")),
            net_profit=_safe_float(row.get("net_kar")),
        )
        for _, row in payload.side_df.iterrows()
    ] if not payload.side_df.empty else []

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
        profit_entries=profit_entries,
        model_breakdown=model_breakdown,
        top_restaurants=top_restaurants,
        top_couriers=top_couriers,
        coverage=ReportsCoverageSummary(
            covered_restaurant_count=int(payload.invoice_df["restoran"].dropna().astype(str).nunique()) if not payload.invoice_df.empty and "restoran" in payload.invoice_df.columns else 0,
            operational_restaurant_count=len(payload.operational_restaurant_names or []),
        ),
        shared_overhead_entries=shared_overhead_entries,
        distribution_entries=distribution_entries,
        side_income_entries=side_income_entries,
        side_income_snapshot=ReportSideIncomeSnapshot(
            fuel_reflection_amount=_safe_float(payload.fuel_reflection_amount),
            company_fuel_reflection_amount=_safe_float(payload.company_fuel_reflection_amount),
            utts_fuel_discount_amount=_safe_float(payload.utts_fuel_discount_amount),
            partner_card_discount_amount=_safe_float(payload.partner_card_discount_amount),
        ),
    )


def _build_local_reports_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    limit: int,
) -> ReportsDashboardResponse:
    month_rows = conn.execute(
        f"""
        SELECT DISTINCT {_month_key_sql('entry_date')} AS month_key
        FROM daily_entries
        WHERE COALESCE(CAST(entry_date AS TEXT), '') <> ''
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
            profit_entries=[],
            model_breakdown=[],
            top_restaurants=[],
            top_couriers=[],
            coverage=_empty_reports_coverage(),
            shared_overhead_entries=[],
            distribution_entries=[],
            side_income_entries=[],
            side_income_snapshot=_empty_side_income_snapshot(),
        )

    resolved_month = selected_month if selected_month in month_options else month_options[0]
    attendance_invoice_rows = conn.execute(
        f"""
        SELECT
            d.id,
            d.entry_date,
            d.actual_personnel_id,
            d.planned_personnel_id,
            d.restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            COALESCE(r.brand, '') AS brand,
            COALESCE(r.branch, '') AS branch,
            COALESCE(r.pricing_model, '-') AS pricing_model,
            COALESCE(r.hourly_rate, 0) AS hourly_rate,
            COALESCE(r.package_rate, 0) AS package_rate,
            COALESCE(r.package_threshold, 0) AS package_threshold,
            COALESCE(r.package_rate_low, 0) AS package_rate_low,
            COALESCE(r.package_rate_high, 0) AS package_rate_high,
            COALESCE(r.fixed_monthly_fee, 0) AS fixed_monthly_fee,
            COALESCE(r.vat_rate, 20) AS vat_rate,
            COALESCE(d.worked_hours, 0) AS worked_hours,
            COALESCE(d.package_count, 0) AS package_count,
            COALESCE(d.monthly_invoice_amount, 0) AS monthly_invoice_amount
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
        ORDER BY restaurant, d.entry_date, d.id
        """,
        (resolved_month,),
    ).fetchall()

    invoice_groups: dict[tuple[object, str], list[dict[str, object]]] = {}
    for raw_row in attendance_invoice_rows:
        row = dict(raw_row)
        restaurant_label = str(row.get("restaurant") or "-")
        invoice_groups.setdefault((row.get("restaurant_id"), restaurant_label), []).append(row)

    all_invoice_entries = []
    for (_, restaurant_label), rows in invoice_groups.items():
        if not rows:
            continue
        total_hours, total_packages, net_invoice, gross_invoice = _calculate_restaurant_invoice(rows)
        all_invoice_entries.append(
            ReportInvoiceEntry(
                restaurant=restaurant_label,
                pricing_model=str(rows[0].get("pricing_model") or "-"),
                total_hours=total_hours,
                total_packages=total_packages,
                net_invoice=round(net_invoice, 2),
                gross_invoice=round(gross_invoice, 2),
            )
        )
    all_invoice_entries.sort(key=lambda row: (-row.gross_invoice, row.restaurant))
    invoice_entries = all_invoice_entries[:limit]

    attendance_rows = conn.execute(
        f"""
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            d.restaurant_id,
            COALESCE(r.brand, '') AS brand,
            COALESCE(r.pricing_model, '') AS pricing_model,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
        GROUP BY
            COALESCE(d.actual_personnel_id, d.planned_personnel_id),
            d.restaurant_id,
            COALESCE(r.brand, ''),
            COALESCE(r.pricing_model, '')
        """,
        (resolved_month,),
    ).fetchall()
    deductions_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_deductions
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
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

    attendance_by_person: dict[int, dict[str, object]] = {}
    for row in attendance_rows:
        if row["personnel_id"] is None:
            continue
        person_id = int(row["personnel_id"])
        bucket = attendance_by_person.setdefault(
            person_id,
            {
                "total_hours": 0.0,
                "total_packages": 0.0,
                "segments": [],
            },
        )
        total_hours = _safe_float(row["total_hours"])
        total_packages = _safe_float(row["total_packages"])
        bucket["total_hours"] = _safe_float(bucket.get("total_hours")) + total_hours
        bucket["total_packages"] = _safe_float(bucket.get("total_packages")) + total_packages
        segments = bucket["segments"]
        if isinstance(segments, list):
            segments.append(
                {
                    "brand": str(row["brand"] or ""),
                    "pricing_model": str(row["pricing_model"] or ""),
                    "total_hours": total_hours,
                    "total_packages": total_packages,
                }
            )
    deductions_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_deductions"])
        for row in deductions_rows
        if row["personnel_id"] is not None
    }

    all_cost_entries: list[ReportCostEntry] = []
    person_cost_lookup: dict[int, ReportCostEntry] = {}
    for row in personnel_rows:
        person_id = int(row["id"])
        attendance = attendance_by_person.get(person_id, {})
        total_hours = _safe_float(attendance.get("total_hours"))
        total_packages = _safe_float(attendance.get("total_packages"))
        total_deductions = _safe_float(deductions_by_person.get(person_id))
        monthly_fixed_cost = _safe_float(row["monthly_fixed_cost"])
        segments = attendance.get("segments")
        gross_cost = _calculate_personnel_gross_cost(
            cost_model=row["cost_model"],
            monthly_fixed_cost=monthly_fixed_cost,
            total_hours=total_hours,
            total_packages=total_packages,
            segments=segments if isinstance(segments, list) else [],
        )
        net_cost = max(gross_cost - total_deductions, 0.0)
        if total_hours <= 0 and total_packages <= 0 and gross_cost <= 0 and total_deductions <= 0:
            continue
        entry = ReportCostEntry(
            personnel=str(row["full_name"] or "-"),
            role=str(row["role"] or "-"),
            total_hours=total_hours,
            total_packages=total_packages,
            total_deductions=total_deductions,
            net_cost=net_cost,
            cost_model=str(row["cost_model"] or "-"),
        )
        all_cost_entries.append(entry)
        person_cost_lookup[person_id] = entry

    all_cost_entries.sort(key=lambda item: item.net_cost, reverse=True)
    cost_entries = all_cost_entries[:limit]

    model_totals: dict[str, dict[str, float | int]] = {}
    for row in all_invoice_entries:
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

    operational_restaurant_row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM restaurants
        WHERE {_active_sql()}
        """
    ).fetchone()
    operational_restaurant_count = int(operational_restaurant_row["total_count"] or 0) if operational_restaurant_row else 0

    shared_overhead_entries: list[ReportSharedOverheadEntry] = []
    for row in personnel_rows:
        person_id = int(row["id"])
        role_name = str(row["role"] or "-")
        if role_name not in _SHARED_OVERHEAD_ROLES:
            continue
        metrics = person_cost_lookup.get(person_id)
        if metrics is None or metrics.net_cost <= 0:
            continue
        share_per_restaurant = (
            metrics.net_cost / operational_restaurant_count
            if operational_restaurant_count > 0
            else 0.0
        )
        shared_overhead_entries.append(
            ReportSharedOverheadEntry(
                personnel=metrics.personnel,
                role=metrics.role,
                gross_cost=metrics.net_cost + metrics.total_deductions,
                total_deductions=metrics.total_deductions,
                net_cost=metrics.net_cost,
                allocated_restaurant_count=operational_restaurant_count,
                share_per_restaurant=share_per_restaurant,
            )
        )

    distribution_rows = conn.execute(
        f"""
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            COALESCE(p.full_name, '-') AS personnel,
            COALESCE(p.role, '-') AS role,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        JOIN personnel p ON p.id = COALESCE(d.actual_personnel_id, d.planned_personnel_id)
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
        GROUP BY
            COALESCE(d.actual_personnel_id, d.planned_personnel_id),
            restaurant,
            personnel,
            role
        ORDER BY total_hours DESC, total_packages DESC, restaurant, personnel
        """,
        (resolved_month,),
    ).fetchall()
    distribution_entries: list[ReportDistributionEntry] = []
    for row in distribution_rows[: limit * 3]:
        personnel_id = int(row["personnel_id"] or 0)
        metrics = person_cost_lookup.get(personnel_id)
        if metrics is None or metrics.role in _SHARED_OVERHEAD_ROLES:
            continue
        total_hours = _safe_float(row["total_hours"])
        total_packages = _safe_float(row["total_packages"])
        attendance_totals = attendance_by_person.get(personnel_id, {})
        person_total_hours = _safe_float(attendance_totals.get("total_hours"))
        person_total_packages = _safe_float(attendance_totals.get("total_packages"))
        if person_total_hours > 0:
            share_ratio = total_hours / person_total_hours
            allocation_source = "Değişken maliyet"
        elif person_total_packages > 0:
            share_ratio = total_packages / person_total_packages
            allocation_source = "Değişken maliyet"
        else:
            share_ratio = 1.0
            allocation_source = "Sabit maliyet payı"
        distribution_entries.append(
            ReportDistributionEntry(
                restaurant=str(row["restaurant"] or "-"),
                personnel=str(row["personnel"] or "-"),
                role=str(row["role"] or "-"),
                total_hours=total_hours,
                total_packages=total_packages,
                allocated_cost=metrics.net_cost * share_ratio,
                allocation_source=allocation_source,
            )
        )

    deduction_rows = conn.execute(
        f"""
        SELECT
            COALESCE(d.deduction_type, '') AS deduction_type,
            COALESCE(SUM(d.amount), 0) AS total_amount
        FROM deductions d
        WHERE {_month_key_sql('d.deduction_date')} = %s
        GROUP BY COALESCE(d.deduction_type, '')
        """,
        (resolved_month,),
    ).fetchall()
    deduction_totals = {
        str(row["deduction_type"] or ""): _safe_float(row["total_amount"])
        for row in deduction_rows
    }
    fuel_reflection_amount = sum(
        amount for deduction_type, amount in deduction_totals.items() if deduction_type in _LOCAL_FUEL_DEDUCTION_TYPES
    )
    partner_card_discount_amount = sum(
        amount
        for deduction_type, amount in deduction_totals.items()
        if deduction_type in _LOCAL_PARTNER_CARD_DEDUCTION_TYPES
    )
    company_fuel_row = conn.execute(
        f"""
        SELECT COALESCE(SUM(d.amount), 0) AS total_amount
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        WHERE {_month_key_sql('d.deduction_date')} = %s
          AND COALESCE(d.deduction_type, '') IN ('Yakit', 'Yakıt')
          AND (
            COALESCE(p.motor_rental, 'Hayır') = 'Evet'
            OR COALESCE(p.motor_purchase, 'Hayır') = 'Evet'
          )
        """,
        (resolved_month,),
    ).fetchone()
    company_fuel_reflection_amount = _safe_float(company_fuel_row["total_amount"]) if company_fuel_row else 0.0
    utts_fuel_discount_amount = round(company_fuel_reflection_amount * 0.07, 2)

    side_income_entries: list[ReportSideIncomeEntry] = [
        ReportSideIncomeEntry(
            item="UTTS Yakıt İndirimi",
            revenue=utts_fuel_discount_amount,
            cost=0.0,
            net_profit=utts_fuel_discount_amount,
        ),
        ReportSideIncomeEntry(
            item="Partner Kart İndirimi",
            revenue=partner_card_discount_amount,
            cost=0.0,
            net_profit=partner_card_discount_amount,
        ),
    ]
    side_income_net = sum(row.net_profit for row in side_income_entries)
    total_revenue = sum(row.gross_invoice for row in all_invoice_entries)
    total_personnel_cost = sum(row.net_cost for row in all_cost_entries)
    shared_overhead_per_restaurant = sum(entry.share_per_restaurant for entry in shared_overhead_entries)
    profit_entries: list[ReportProfitEntry] = []
    for row in all_invoice_entries:
        direct_personnel_cost = sum(
            entry.allocated_cost
            for entry in distribution_entries
            if entry.restaurant == row.restaurant
        )
        shared_overhead_cost = shared_overhead_per_restaurant if operational_restaurant_count > 0 else 0.0
        total_personnel_cost_for_restaurant = direct_personnel_cost + shared_overhead_cost
        gross_profit_for_restaurant = row.gross_invoice - total_personnel_cost_for_restaurant
        profit_margin_percent = (
            (gross_profit_for_restaurant / row.gross_invoice) * 100
            if row.gross_invoice > 0
            else 0.0
        )
        profit_entries.append(
            ReportProfitEntry(
                restaurant=row.restaurant,
                pricing_model=row.pricing_model,
                total_hours=row.total_hours,
                total_packages=row.total_packages,
                net_invoice=row.net_invoice,
                gross_invoice=row.gross_invoice,
                direct_personnel_cost=direct_personnel_cost,
                shared_overhead_cost=shared_overhead_cost,
                total_personnel_cost=total_personnel_cost_for_restaurant,
                gross_profit=gross_profit_for_restaurant,
                profit_margin_percent=profit_margin_percent,
            )
        )
    profit_entries.sort(key=lambda item: item.gross_profit, reverse=True)

    summary = ReportsSummary(
        selected_month=resolved_month,
        restaurant_count=len(all_invoice_entries),
        courier_count=len(all_cost_entries),
        total_hours=sum(row.total_hours for row in all_invoice_entries),
        total_packages=sum(row.total_packages for row in all_invoice_entries),
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
        profit_entries=profit_entries[:limit],
        model_breakdown=model_breakdown,
        top_restaurants=[
            ReportTopRestaurantEntry(
                restaurant=row.restaurant,
                pricing_model=row.pricing_model,
                total_hours=row.total_hours,
                total_packages=row.total_packages,
                gross_invoice=row.gross_invoice,
            )
            for row in all_invoice_entries[:6]
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
            for row in all_cost_entries[:6]
        ],
        coverage=ReportsCoverageSummary(
            covered_restaurant_count=len(all_invoice_entries),
            operational_restaurant_count=operational_restaurant_count,
        ),
        shared_overhead_entries=shared_overhead_entries,
        distribution_entries=distribution_entries,
        side_income_entries=side_income_entries,
        side_income_snapshot=ReportSideIncomeSnapshot(
            fuel_reflection_amount=fuel_reflection_amount,
            company_fuel_reflection_amount=company_fuel_reflection_amount,
            utts_fuel_discount_amount=utts_fuel_discount_amount,
            partner_card_discount_amount=partner_card_discount_amount,
        ),
    )
