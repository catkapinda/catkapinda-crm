from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any, Callable

import pandas as pd


_SAFE_INT: Callable[[Any, int], int] | None = None
_SAFE_FLOAT: Callable[[Any, float], float] | None = None
_PARSE_DATE_VALUE: Callable[[Any], date | None] | None = None
_END_OF_MONTH: Callable[[date], date] | None = None
_NORMALIZE_COST_MODEL_VALUE: Callable[[str, str], str] | None = None
_PRICING_RULE_CLS: Any = None

_VAT_RATE_DEFAULT = 20.0
_COURIER_HOURLY_COST = 250.0
_COURIER_PACKAGE_COST_DEFAULT_LOW = 20.0
_COURIER_PACKAGE_COST_DEFAULT_HIGH = 25.0
_COURIER_PACKAGE_COST_QC = 25.0
_PACKAGE_THRESHOLD_DEFAULT = 390


def configure_reporting_rules(
    *,
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    parse_date_value_fn: Callable[[Any], date | None],
    end_of_month_fn: Callable[[date], date],
    normalize_cost_model_value_fn: Callable[[str, str], str],
    pricing_rule_cls: Any,
    vat_rate_default: float,
    courier_hourly_cost: float,
    courier_package_cost_default_low: float,
    courier_package_cost_default_high: float,
    courier_package_cost_qc: float,
    package_threshold_default: int,
) -> None:
    global _SAFE_INT
    global _SAFE_FLOAT
    global _PARSE_DATE_VALUE
    global _END_OF_MONTH
    global _NORMALIZE_COST_MODEL_VALUE
    global _PRICING_RULE_CLS
    global _VAT_RATE_DEFAULT
    global _COURIER_HOURLY_COST
    global _COURIER_PACKAGE_COST_DEFAULT_LOW
    global _COURIER_PACKAGE_COST_DEFAULT_HIGH
    global _COURIER_PACKAGE_COST_QC
    global _PACKAGE_THRESHOLD_DEFAULT

    _SAFE_INT = safe_int_fn
    _SAFE_FLOAT = safe_float_fn
    _PARSE_DATE_VALUE = parse_date_value_fn
    _END_OF_MONTH = end_of_month_fn
    _NORMALIZE_COST_MODEL_VALUE = normalize_cost_model_value_fn
    _PRICING_RULE_CLS = pricing_rule_cls
    _VAT_RATE_DEFAULT = float(vat_rate_default)
    _COURIER_HOURLY_COST = float(courier_hourly_cost)
    _COURIER_PACKAGE_COST_DEFAULT_LOW = float(courier_package_cost_default_low)
    _COURIER_PACKAGE_COST_DEFAULT_HIGH = float(courier_package_cost_default_high)
    _COURIER_PACKAGE_COST_QC = float(courier_package_cost_qc)
    _PACKAGE_THRESHOLD_DEFAULT = int(package_threshold_default)


def infer_reporting_period(month_df: pd.DataFrame, deductions_df: pd.DataFrame) -> tuple[date, date]:
    candidate_dates: list[date] = []
    if month_df is not None and not month_df.empty and "entry_date" in month_df.columns:
        parsed_entries = pd.to_datetime(month_df["entry_date"], errors="coerce").dropna()
        candidate_dates.extend(parsed_entries.dt.date.tolist())
    if deductions_df is not None and not deductions_df.empty and "deduction_date" in deductions_df.columns:
        parsed_deductions = pd.to_datetime(deductions_df["deduction_date"], errors="coerce").dropna()
        candidate_dates.extend(parsed_deductions.dt.date.tolist())
    if not candidate_dates:
        today_value = date.today()
        return today_value.replace(day=1), _END_OF_MONTH(today_value)
    first_date = min(candidate_dates)
    month_start_value = first_date.replace(day=1)
    return month_start_value, _END_OF_MONTH(month_start_value)


def get_operational_restaurant_names_for_period(
    restaurants_df: pd.DataFrame | None,
    period_start: date,
    period_end: date,
) -> list[str]:
    if restaurants_df is None or restaurants_df.empty:
        return []

    work = restaurants_df.copy()
    for column_name, default_value in {
        "brand": "",
        "branch": "",
        "active": 1,
        "start_date": None,
        "end_date": None,
    }.items():
        if column_name not in work.columns:
            work[column_name] = default_value

    operational_names: set[str] = set()
    for _, row in work.iterrows():
        brand = str(row.get("brand") or "").strip()
        branch = str(row.get("branch") or "").strip()
        if not brand or not branch:
            continue

        start_date_value = _PARSE_DATE_VALUE(row.get("start_date"))
        end_date_value = _PARSE_DATE_VALUE(row.get("end_date"))
        has_dates = start_date_value is not None or end_date_value is not None
        if has_dates:
            overlaps_period = (
                (start_date_value is None or start_date_value <= period_end)
                and (end_date_value is None or end_date_value >= period_start)
            )
            if not overlaps_period:
                continue
        elif _SAFE_INT(row.get("active"), 0) != 1:
            continue

        operational_names.add(f"{brand} - {branch}")

    return sorted(operational_names)


def build_person_role_segments(
    person_row: Any,
    role_history_df: pd.DataFrame,
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    person_id_value = person_row.get("id") if hasattr(person_row, "get") else person_row["id"]
    person_id = _SAFE_INT(person_id_value, 0)
    if person_id <= 0 or period_end < period_start:
        return []

    if role_history_df is None or role_history_df.empty or "personnel_id" not in role_history_df.columns:
        history_rows = pd.DataFrame()
    else:
        history_rows = role_history_df[role_history_df["personnel_id"] == person_id].copy()

    snapshots: list[dict[str, Any]] = []
    if not history_rows.empty:
        history_rows["effective_date_value"] = history_rows["effective_date"].apply(_PARSE_DATE_VALUE)
        history_rows = history_rows[history_rows["effective_date_value"].notna()].sort_values(["effective_date_value"])
        for _, row in history_rows.iterrows():
            effective_date_value = _PARSE_DATE_VALUE(row.get("effective_date_value"))
            if effective_date_value is None or effective_date_value > period_end:
                continue
            role_value = str(row.get("role", "Kurye") or "Kurye")
            snapshots.append(
                {
                    "effective_date": effective_date_value,
                    "role": role_value,
                    "cost_model": _NORMALIZE_COST_MODEL_VALUE(
                        str(row.get("cost_model", "standard_courier") or "standard_courier"),
                        role_value,
                    ),
                    "monthly_fixed_cost": _SAFE_FLOAT(row.get("monthly_fixed_cost"), 0.0),
                }
            )

    if not snapshots:
        role_raw_value = person_row.get("role", "Kurye") if hasattr(person_row, "get") else person_row["role"]
        cost_model_raw_value = person_row.get("cost_model", "standard_courier") if hasattr(person_row, "get") else person_row["cost_model"]
        start_date_raw_value = person_row.get("start_date") if hasattr(person_row, "get") else person_row["start_date"]
        monthly_fixed_cost_raw_value = person_row.get("monthly_fixed_cost") if hasattr(person_row, "get") else person_row["monthly_fixed_cost"]
        role_value = str(role_raw_value or "Kurye")
        snapshots.append(
            {
                "effective_date": _PARSE_DATE_VALUE(start_date_raw_value) or period_start,
                "role": role_value,
                "cost_model": _NORMALIZE_COST_MODEL_VALUE(
                    str(cost_model_raw_value or "standard_courier"),
                    role_value,
                ),
                "monthly_fixed_cost": _SAFE_FLOAT(monthly_fixed_cost_raw_value, 0.0),
            }
        )

    segments: list[dict[str, Any]] = []
    for index, snapshot in enumerate(snapshots):
        next_snapshot = snapshots[index + 1] if index + 1 < len(snapshots) else None
        segment_start = max(snapshot["effective_date"], period_start)
        segment_end = period_end if next_snapshot is None else min(period_end, next_snapshot["effective_date"] - timedelta(days=1))
        if segment_end < period_start or segment_start > period_end or segment_end < segment_start:
            continue
        segments.append(
            {
                "role": snapshot["role"],
                "cost_model": snapshot["cost_model"],
                "monthly_fixed_cost": snapshot["monthly_fixed_cost"],
                "start_date": segment_start,
                "end_date": segment_end,
            }
        )
    return segments


def describe_role_segments(segments: list[dict[str, Any]], fallback_role: str) -> str:
    ordered_roles: list[str] = []
    for segment in segments:
        role_name = str(segment.get("role") or "").strip()
        if role_name and role_name not in ordered_roles:
            ordered_roles.append(role_name)
    if not ordered_roles:
        return fallback_role
    if len(ordered_roles) == 1:
        return ordered_roles[0]
    return " -> ".join(ordered_roles)


def describe_cost_model_segments(segments: list[dict[str, Any]], fallback_cost_model: str) -> str:
    ordered_models: list[str] = []
    for segment in segments:
        model_name = str(segment.get("cost_model") or "").strip()
        if model_name and model_name not in ordered_models:
            ordered_models.append(model_name)
    if not ordered_models:
        return fallback_cost_model
    if len(ordered_models) == 1:
        return ordered_models[0]
    return "Geçişli"


def calculate_customer_invoice(group: pd.DataFrame, rule: Any) -> tuple[float, float, float, float]:
    total_hours = float(group["worked_hours"].fillna(0).sum())
    total_packages = float(group["package_count"].fillna(0).sum())

    if rule.pricing_model == "hourly_plus_package":
        subtotal = total_hours * rule.hourly_rate + total_packages * rule.package_rate
    elif rule.pricing_model == "threshold_package":
        package_threshold = float(rule.package_threshold or 0)
        package_rate = rule.package_rate_low if total_packages <= package_threshold else rule.package_rate_high
        subtotal = total_hours * rule.hourly_rate + total_packages * package_rate
    elif rule.pricing_model == "hourly_only":
        subtotal = total_hours * rule.hourly_rate
    elif rule.pricing_model == "fixed_monthly":
        subtotal = rule.fixed_monthly_fee
    else:
        subtotal = 0.0

    vat = subtotal * (rule.vat_rate / 100.0)
    grand_total = subtotal + vat
    return total_hours, total_packages, subtotal, grand_total


def calculate_standard_package_cost(total_packages: float, brand: str = "", pricing_model: str = "") -> float:
    package_total = float(total_packages or 0)
    if (brand or "").strip() == "Quick China":
        return package_total * _COURIER_PACKAGE_COST_QC
    if pricing_model == "threshold_package":
        package_rate = _COURIER_PACKAGE_COST_DEFAULT_LOW if package_total <= _PACKAGE_THRESHOLD_DEFAULT else _COURIER_PACKAGE_COST_DEFAULT_HIGH
        return package_total * package_rate
    return 0.0


def calculate_standard_courier_cost(
    total_hours: float,
    total_packages: float = 0.0,
    brand: str = "",
    pricing_model: str = "",
) -> float:
    cost = float(total_hours or 0) * _COURIER_HOURLY_COST
    cost += calculate_standard_package_cost(total_packages, brand=brand, pricing_model=pricing_model)
    return cost


def month_bounds(selected_month: str) -> tuple[str, str]:
    year, month = map(int, selected_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def build_invoice_summary_df(month_df: pd.DataFrame) -> pd.DataFrame:
    if month_df is None or month_df.empty:
        return pd.DataFrame()

    invoicing_rows = []
    for (restaurant_id, brand, branch), group in month_df.groupby(["restaurant_id", "brand", "branch"], dropna=False):
        if group.empty:
            continue
        first = group.iloc[0]
        rule = _PRICING_RULE_CLS(
            pricing_model=str(first.get("pricing_model", "") or ""),
            hourly_rate=_SAFE_FLOAT(first.get("hourly_rate"), 0.0),
            package_rate=_SAFE_FLOAT(first.get("package_rate"), 0.0),
            package_threshold=_SAFE_INT(first.get("package_threshold"), 0),
            package_rate_low=_SAFE_FLOAT(first.get("package_rate_low"), 0.0),
            package_rate_high=_SAFE_FLOAT(first.get("package_rate_high"), 0.0),
            fixed_monthly_fee=_SAFE_FLOAT(first.get("fixed_monthly_fee"), 0.0),
            vat_rate=_SAFE_FLOAT(first.get("vat_rate"), _VAT_RATE_DEFAULT),
        )
        hours, packages, subtotal, grand_total = calculate_customer_invoice(group, rule)
        invoicing_rows.append(
            {
                "restaurant_id": restaurant_id,
                "restoran": f"{brand} - {branch}",
                "model": rule.pricing_model,
                "saat": hours,
                "paket": packages,
                "kdv_haric": subtotal,
                "kdv_dahil": grand_total,
            }
        )

    if not invoicing_rows:
        return pd.DataFrame()
    return pd.DataFrame(invoicing_rows).sort_values(["kdv_dahil", "restoran"], ascending=[False, True]).reset_index(drop=True)


def build_restaurant_invoice_drilldown_map(
    month_df: pd.DataFrame,
    personnel_df: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    if month_df is None or month_df.empty:
        return {}

    work = month_df.copy()
    for column_name, default_value in {
        "brand": "",
        "branch": "",
        "worked_hours": 0.0,
        "package_count": 0.0,
        "actual_personnel_id": None,
    }.items():
        if column_name not in work.columns:
            work[column_name] = default_value

    work["restoran"] = work["brand"].fillna("").astype(str) + " - " + work["branch"].fillna("").astype(str)
    work["worked_hours"] = pd.to_numeric(work["worked_hours"], errors="coerce").fillna(0.0)
    work["package_count"] = pd.to_numeric(work["package_count"], errors="coerce").fillna(0.0)
    work["actual_personnel_id"] = pd.to_numeric(work["actual_personnel_id"], errors="coerce")

    if personnel_df is not None and not personnel_df.empty and "id" in personnel_df.columns:
        people_lookup = personnel_df[["id", "full_name", "role"]].copy()
        people_lookup["id"] = pd.to_numeric(people_lookup["id"], errors="coerce")
        people_lookup = people_lookup.rename(columns={"id": "actual_personnel_id", "full_name": "personel", "role": "rol"})
        work = work.merge(people_lookup, how="left", on="actual_personnel_id")
    else:
        work["personel"] = None
        work["rol"] = None

    work["personel"] = work["personel"].fillna("")
    work["rol"] = work["rol"].fillna("")
    work.loc[(work["personel"].astype(str).str.strip() == "") & work["actual_personnel_id"].notna(), "personel"] = (
        "Personel #" + work["actual_personnel_id"].fillna(0).astype(int).astype(str)
    )
    work.loc[work["personel"].astype(str).str.strip() == "", "personel"] = "Belirsiz Personel"
    work.loc[work["rol"].astype(str).str.strip() == "", "rol"] = "-"

    grouped = (
        work.groupby(["restoran", "personel", "rol"], dropna=False)
        .agg(calisma_saati=("worked_hours", "sum"), paket=("package_count", "sum"))
        .reset_index()
    )
    grouped = grouped[(grouped["calisma_saati"] > 0) | (grouped["paket"] > 0)].copy()
    if grouped.empty:
        return {}

    drilldown_map: dict[str, pd.DataFrame] = {}
    for restoran_name, restaurant_group in grouped.groupby("restoran", dropna=False):
        detail_df = restaurant_group[["personel", "rol", "calisma_saati", "paket"]].copy()
        detail_df = detail_df.sort_values(["paket", "calisma_saati", "personel"], ascending=[False, False, True]).reset_index(drop=True)
        drilldown_map[str(restoran_name or "")] = detail_df
    return drilldown_map
