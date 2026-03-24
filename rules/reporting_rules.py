from __future__ import annotations

import calendar
import re
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


def _format_compact_number(value: Any) -> str:
    numeric_value = _SAFE_FLOAT(value, 0.0)
    if abs(numeric_value - round(numeric_value)) < 0.005:
        return f"{int(round(numeric_value))}"
    text = f"{numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if text.endswith(",00"):
        text = text[:-3]
    elif text.endswith("0"):
        text = text[:-1]
    return text


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


def _calculate_threshold_package_subtotal(total_hours: float, total_packages: float, rule: Any) -> float:
    raw_threshold = _SAFE_INT(getattr(rule, "package_threshold", 0), 0)
    package_threshold = float(raw_threshold if raw_threshold > 0 else _PACKAGE_THRESHOLD_DEFAULT)
    package_rate = rule.package_rate_low if float(total_packages or 0) <= package_threshold else rule.package_rate_high
    return float(total_hours or 0) * rule.hourly_rate + float(total_packages or 0) * package_rate


def _resolve_fixed_monthly_fee_from_group(group: pd.DataFrame, fallback_fee: float) -> float:
    resolved_fallback = _SAFE_FLOAT(fallback_fee, 0.0)
    if group is None or group.empty or "monthly_invoice_amount" not in group.columns:
        return resolved_fallback

    work = group.copy()
    work["monthly_invoice_amount"] = pd.to_numeric(work["monthly_invoice_amount"], errors="coerce").fillna(0.0)
    work = work[work["monthly_invoice_amount"] > 0].copy()
    if work.empty:
        return resolved_fallback

    if "entry_date" in work.columns:
        work["entry_date_sort"] = pd.to_datetime(work["entry_date"], errors="coerce")
    else:
        work["entry_date_sort"] = pd.NaT
    if "id" in work.columns:
        work["id_sort"] = pd.to_numeric(work["id"], errors="coerce").fillna(0)
    else:
        work["id_sort"] = 0

    work = work.sort_values(["entry_date_sort", "id_sort"], ascending=[True, True])
    return _SAFE_FLOAT(work.iloc[-1].get("monthly_invoice_amount"), resolved_fallback)


def _build_invoice_actor_keys(group: pd.DataFrame) -> pd.Series:
    actor_keys = pd.Series([""] * len(group), index=group.index, dtype="object")

    if "actual_personnel_id" in group.columns:
        actual_ids = pd.to_numeric(group["actual_personnel_id"], errors="coerce").astype("Int64").astype("string").fillna("")
        actor_keys = actual_ids.astype(str)
        actor_keys = actor_keys.replace("<NA>", "")

    if "planned_personnel_id" in group.columns:
        planned_ids = pd.to_numeric(group["planned_personnel_id"], errors="coerce").astype("Int64").astype("string").fillna("")
        planned_keys = planned_ids.astype(str).replace("<NA>", "")
        actor_keys = actor_keys.mask(actor_keys.astype(str).str.strip() == "", planned_keys)

    if "personel" in group.columns:
        person_names = group["personel"].fillna("").astype(str).str.strip()
        actor_keys = actor_keys.mask(actor_keys.astype(str).str.strip() == "", person_names)

    return actor_keys.fillna("").astype(str)


def calculate_customer_invoice(group: pd.DataFrame, rule: Any) -> tuple[float, float, float, float]:
    total_hours = float(group["worked_hours"].fillna(0).sum())
    total_packages = float(group["package_count"].fillna(0).sum())

    if rule.pricing_model == "hourly_plus_package":
        subtotal = total_hours * rule.hourly_rate + total_packages * rule.package_rate
    elif rule.pricing_model == "threshold_package":
        actor_keys = _build_invoice_actor_keys(group)
        if actor_keys.astype(str).str.strip().eq("").all():
            subtotal = _calculate_threshold_package_subtotal(total_hours, total_packages, rule)
        else:
            threshold_work = group.copy()
            threshold_work["invoice_actor_key"] = actor_keys
            grouped = (
                threshold_work.groupby("invoice_actor_key", dropna=False)
                .agg(worked_hours=("worked_hours", "sum"), package_count=("package_count", "sum"))
                .reset_index()
            )
            grouped = grouped[(grouped["worked_hours"] > 0) | (grouped["package_count"] > 0)].copy()
            subtotal = float(
                grouped.apply(
                    lambda row: _calculate_threshold_package_subtotal(
                        _SAFE_FLOAT(row.get("worked_hours"), 0.0),
                        _SAFE_FLOAT(row.get("package_count"), 0.0),
                        rule,
                    ),
                    axis=1,
                ).sum()
            )
    elif rule.pricing_model == "hourly_only":
        subtotal = total_hours * rule.hourly_rate
    elif rule.pricing_model == "fixed_monthly":
        subtotal = _resolve_fixed_monthly_fee_from_group(group, rule.fixed_monthly_fee)
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
            package_threshold=_SAFE_INT(first.get("package_threshold"), _PACKAGE_THRESHOLD_DEFAULT),
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
        "planned_personnel_id": None,
        "absence_reason": "",
        "coverage_type": "",
        "pricing_model": "",
        "hourly_rate": 0.0,
        "package_rate": 0.0,
        "package_threshold": _PACKAGE_THRESHOLD_DEFAULT,
        "package_rate_low": 0.0,
        "package_rate_high": 0.0,
        "fixed_monthly_fee": 0.0,
        "monthly_invoice_amount": 0.0,
        "vat_rate": _VAT_RATE_DEFAULT,
    }.items():
        if column_name not in work.columns:
            work[column_name] = default_value

    work["restoran"] = work["brand"].fillna("").astype(str) + " - " + work["branch"].fillna("").astype(str)
    work["worked_hours"] = pd.to_numeric(work["worked_hours"], errors="coerce").fillna(0.0)
    work["package_count"] = pd.to_numeric(work["package_count"], errors="coerce").fillna(0.0)
    work["actual_personnel_id"] = pd.to_numeric(work["actual_personnel_id"], errors="coerce").astype("Int64")
    work["planned_personnel_id"] = pd.to_numeric(work["planned_personnel_id"], errors="coerce").astype("Int64")

    if personnel_df is not None and not personnel_df.empty and "id" in personnel_df.columns:
        people_lookup = personnel_df[["id", "full_name", "role"]].copy()
        people_lookup["id"] = pd.to_numeric(people_lookup["id"], errors="coerce").astype("Int64")
        actual_lookup = people_lookup.rename(columns={"id": "actual_personnel_id", "full_name": "actual_personel", "role": "actual_rol"})
        planned_lookup = people_lookup.rename(columns={"id": "planned_personnel_id", "full_name": "planned_personel", "role": "planned_rol"})
        work = work.merge(actual_lookup, how="left", on="actual_personnel_id")
        work = work.merge(planned_lookup, how="left", on="planned_personnel_id")
    else:
        work["actual_personel"] = None
        work["actual_rol"] = None
        work["planned_personel"] = None
        work["planned_rol"] = None

    work["courier_id"] = work["actual_personnel_id"].where(work["actual_personnel_id"].notna(), work["planned_personnel_id"])
    work["personel"] = work["actual_personel"].fillna("").astype(str)
    work.loc[work["personel"].str.strip() == "", "personel"] = work["planned_personel"].fillna("").astype(str)
    work["rol"] = work["actual_rol"].fillna("").astype(str)
    work.loc[work["rol"].str.strip() == "", "rol"] = work["planned_rol"].fillna("").astype(str)
    work.loc[(work["personel"].astype(str).str.strip() == "") & work["courier_id"].notna(), "personel"] = (
        "Personel #" + work["courier_id"].fillna(0).astype(int).astype(str)
    )
    work.loc[work["personel"].astype(str).str.strip() == "", "personel"] = "Belirsiz Personel"
    work.loc[work["rol"].astype(str).str.strip() == "", "rol"] = "-"

    drilldown_map: dict[str, pd.DataFrame] = {}
    for (restaurant_id, brand, branch), restaurant_entries in work.groupby(["restaurant_id", "brand", "branch"], dropna=False):
        if restaurant_entries.empty:
            continue
        first = restaurant_entries.iloc[0]
        rule = _PRICING_RULE_CLS(
            pricing_model=str(first.get("pricing_model", "") or ""),
            hourly_rate=_SAFE_FLOAT(first.get("hourly_rate"), 0.0),
            package_rate=_SAFE_FLOAT(first.get("package_rate"), 0.0),
            package_threshold=_SAFE_INT(first.get("package_threshold"), _PACKAGE_THRESHOLD_DEFAULT),
            package_rate_low=_SAFE_FLOAT(first.get("package_rate_low"), 0.0),
            package_rate_high=_SAFE_FLOAT(first.get("package_rate_high"), 0.0),
            fixed_monthly_fee=_SAFE_FLOAT(first.get("fixed_monthly_fee"), 0.0),
            vat_rate=_SAFE_FLOAT(first.get("vat_rate"), _VAT_RATE_DEFAULT),
        )
        resolved_fixed_monthly_fee = _resolve_fixed_monthly_fee_from_group(restaurant_entries, rule.fixed_monthly_fee)
        restaurant_total_hours, restaurant_total_packages, _, _ = calculate_customer_invoice(restaurant_entries, rule)

        grouped = (
            restaurant_entries.groupby(["personel", "rol"], dropna=False)
            .agg(calisma_saati=("worked_hours", "sum"), paket=("package_count", "sum"))
            .reset_index()
        )
        grouped = grouped[(grouped["calisma_saati"] > 0) | (grouped["paket"] > 0)].copy()
        if grouped.empty:
            continue

        courier_count = len(grouped)
        subtotal_values = []
        for _, courier_row in grouped.iterrows():
            courier_hours = _SAFE_FLOAT(courier_row.get("calisma_saati"), 0.0)
            courier_packages = _SAFE_FLOAT(courier_row.get("paket"), 0.0)
            if rule.pricing_model == "hourly_plus_package":
                courier_subtotal = courier_hours * rule.hourly_rate + courier_packages * rule.package_rate
            elif rule.pricing_model == "threshold_package":
                courier_subtotal = _calculate_threshold_package_subtotal(courier_hours, courier_packages, rule)
            elif rule.pricing_model == "hourly_only":
                courier_subtotal = courier_hours * rule.hourly_rate
            elif rule.pricing_model == "fixed_monthly":
                if restaurant_total_hours > 0:
                    courier_subtotal = resolved_fixed_monthly_fee * (courier_hours / restaurant_total_hours)
                elif restaurant_total_packages > 0:
                    courier_subtotal = resolved_fixed_monthly_fee * (courier_packages / restaurant_total_packages)
                else:
                    courier_subtotal = resolved_fixed_monthly_fee / max(courier_count, 1)
            else:
                courier_subtotal = 0.0
            subtotal_values.append(courier_subtotal)

        grouped["kdv_haric"] = subtotal_values
        grouped["kdv_dahil"] = grouped["kdv_haric"].apply(lambda value: float(value) * (1 + (rule.vat_rate / 100.0)))
        restoran_name = f"{brand} - {branch}"
        detail_df = grouped[["personel", "rol", "calisma_saati", "paket", "kdv_haric", "kdv_dahil"]].copy()
        detail_df = detail_df.sort_values(["paket", "calisma_saati", "personel"], ascending=[False, False, True]).reset_index(drop=True)
        drilldown_map[str(restoran_name or "")] = detail_df
    return drilldown_map


def build_restaurant_attendance_export_map(
    month_df: pd.DataFrame,
    personnel_df: pd.DataFrame | None,
    selected_month: str,
    invoice_drilldown_map: dict[str, pd.DataFrame] | None = None,
) -> dict[str, pd.DataFrame]:
    if month_df is None or month_df.empty:
        return {}

    year, month = map(int, selected_month.split("-"))
    total_days = calendar.monthrange(year, month)[1]
    day_columns = [f"{day:02d}" for day in range(1, total_days + 1)]

    work = month_df.copy()
    for column_name, default_value in {
        "brand": "",
        "branch": "",
        "entry_date": None,
        "status": "Normal",
        "worked_hours": 0.0,
        "package_count": 0.0,
        "planned_personnel_id": None,
        "actual_personnel_id": None,
        "absence_reason": "",
        "coverage_type": "",
    }.items():
        if column_name not in work.columns:
            work[column_name] = default_value

    work["restoran"] = work["brand"].fillna("").astype(str) + " - " + work["branch"].fillna("").astype(str)
    work["entry_date_value"] = pd.to_datetime(work["entry_date"], errors="coerce").dt.date
    work = work[work["entry_date_value"].notna()].copy()
    if work.empty:
        return {}
    work["day_key"] = pd.to_datetime(work["entry_date"], errors="coerce").dt.day.apply(lambda day: f"{int(day):02d}" if pd.notna(day) else "")
    work["worked_hours"] = pd.to_numeric(work["worked_hours"], errors="coerce").fillna(0.0)
    work["package_count"] = pd.to_numeric(work["package_count"], errors="coerce").fillna(0.0)
    work["planned_personnel_id"] = pd.to_numeric(work["planned_personnel_id"], errors="coerce").astype("Int64")
    work["actual_personnel_id"] = pd.to_numeric(work["actual_personnel_id"], errors="coerce").astype("Int64")

    if personnel_df is not None and not personnel_df.empty and "id" in personnel_df.columns:
        people_lookup = personnel_df[["id", "full_name", "role"]].copy()
        people_lookup["id"] = pd.to_numeric(people_lookup["id"], errors="coerce").astype("Int64")
        actual_lookup = people_lookup.rename(columns={"id": "actual_personnel_id", "full_name": "actual_personel", "role": "actual_rol"})
        planned_lookup = people_lookup.rename(columns={"id": "planned_personnel_id", "full_name": "planned_personel", "role": "planned_rol"})
        work = work.merge(actual_lookup, how="left", on="actual_personnel_id")
        work = work.merge(planned_lookup, how="left", on="planned_personnel_id")
    else:
        work["actual_personel"] = None
        work["actual_rol"] = None
        work["planned_personel"] = None
        work["planned_rol"] = None

    export_map: dict[str, pd.DataFrame] = {}
    invoice_drilldown_map = invoice_drilldown_map or {}

    for restaurant_name, restaurant_group in work.groupby("restoran", dropna=False):
        if restaurant_group.empty:
            continue
        row_store: dict[str, dict[str, Any]] = {}
        row_order: list[str] = []
        for _, entry_row in restaurant_group.iterrows():
            planned_name = str(entry_row.get("planned_personel") or "").strip()
            actual_name = str(entry_row.get("actual_personel") or "").strip()
            role_name = str(entry_row.get("planned_rol") or entry_row.get("actual_rol") or "-").strip() or "-"
            row_key = planned_name or actual_name or "Belirsiz Personel"
            if row_key not in row_store:
                row_store[row_key] = {"Kurye": row_key, "Rol": role_name, **{day_col: "" for day_col in day_columns}}
                row_order.append(row_key)

            day_key = str(entry_row.get("day_key") or "")
            if not day_key:
                continue
            status_text = str(entry_row.get("status") or "Normal").strip() or "Normal"
            absence_reason = str(entry_row.get("absence_reason") or "").strip()
            coverage_type = str(entry_row.get("coverage_type") or "").strip()
            hours = _SAFE_FLOAT(entry_row.get("worked_hours"), 0.0)
            packages = _SAFE_FLOAT(entry_row.get("package_count"), 0.0)
            detail_parts: list[str] = []
            if absence_reason:
                detail_parts.append(absence_reason)
            elif status_text and status_text != "Normal":
                detail_parts.append(status_text)
            if planned_name and actual_name and planned_name != actual_name:
                if coverage_type:
                    detail_parts.append(f"{coverage_type}: {actual_name}")
                else:
                    detail_parts.append(f"Yerine {actual_name}")
            elif coverage_type:
                detail_parts.append(coverage_type)
            stat_parts: list[str] = []
            if hours > 0:
                stat_parts.append(f"{_format_compact_number(hours)} saat")
            if packages > 0:
                stat_parts.append(f"{_format_compact_number(packages)} paket")
            if stat_parts:
                detail_parts.append(" | ".join(stat_parts))
            if not detail_parts:
                detail_parts.append("-")

            current_value = str(row_store[row_key].get(day_key, "") or "").strip()
            next_value = " / ".join(detail_parts)
            row_store[row_key][day_key] = f"{current_value} || {next_value}" if current_value else next_value

        summary_df = invoice_drilldown_map.get(str(restaurant_name or ""), pd.DataFrame())
        summary_map = {}
        if summary_df is not None and not summary_df.empty:
            for _, summary_row in summary_df.iterrows():
                summary_map[str(summary_row.get("personel") or "")] = summary_row

        export_rows = []
        for row_key in row_order:
            export_row = row_store[row_key]
            summary_row = summary_map.get(row_key)
            export_row["Toplam Saat"] = _SAFE_FLOAT(summary_row.get("calisma_saati"), 0.0) if summary_row is not None else 0.0
            export_row["Toplam Paket"] = _SAFE_FLOAT(summary_row.get("paket"), 0.0) if summary_row is not None else 0.0
            export_row["KDV Hariç"] = _SAFE_FLOAT(summary_row.get("kdv_haric"), 0.0) if summary_row is not None else 0.0
            export_row["KDV Dahil"] = _SAFE_FLOAT(summary_row.get("kdv_dahil"), 0.0) if summary_row is not None else 0.0
            export_rows.append(export_row)

        export_df = pd.DataFrame(export_rows)
        if export_df.empty:
            continue
        ordered_columns = ["Kurye", "Rol", "Toplam Saat", "Toplam Paket", "KDV Hariç", "KDV Dahil", *day_columns]
        export_df = export_df.reindex(columns=ordered_columns)
        export_map[str(restaurant_name or "")] = export_df

    return export_map


def build_restaurant_export_filename(restaurant_name: str, selected_month: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(restaurant_name or "").strip()).strip("_").lower()
    normalized = normalized or "restoran"
    return f"catkapinda_{normalized}_{selected_month}_puantaj.csv"
