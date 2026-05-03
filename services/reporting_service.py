from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from builders.analytics_builders import build_side_income_summary_df, split_equipment_profit_categories
from engines.finance_engine import build_branch_profitability, calculate_personnel_cost
from repositories.reporting_repository import (
    fetch_reporting_all_deductions,
    fetch_reporting_deductions_for_period,
    fetch_reporting_entries,
    fetch_reporting_personnel,
    fetch_reporting_restaurants,
    fetch_reporting_role_history,
)
from rules.deduction_rules import calculate_fuel_discount_summary, filter_payroll_effective_deductions_df
from rules.equipment_rules import build_equipment_profitability_frames
from rules.reporting_rules import (
    build_invoice_summary_df,
    build_restaurant_attendance_export_map,
    build_restaurant_invoice_drilldown_map,
    get_operational_restaurant_names_for_period,
    month_bounds,
)


@dataclass
class ReportsWorkspacePayload:
    month_df: pd.DataFrame
    restaurants_df: pd.DataFrame
    personnel_df: pd.DataFrame
    role_history_df: pd.DataFrame
    deductions_df: pd.DataFrame
    invoice_df: pd.DataFrame
    invoice_drilldown_map: dict[str, pd.DataFrame]
    invoice_attendance_export_map: dict[str, pd.DataFrame]
    cost_df: pd.DataFrame
    profit_df: pd.DataFrame
    person_distribution_df: pd.DataFrame
    shared_overhead_df: pd.DataFrame
    side_df: pd.DataFrame
    equipment_profit_df: pd.DataFrame
    equipment_purchase_df: pd.DataFrame
    revenue: float
    personnel_cost: float
    gross_profit: float
    side_income_net: float
    fuel_reflection_amount: float
    company_fuel_reflection_amount: float
    utts_fuel_discount_amount: float
    partner_card_discount_amount: float
    operational_restaurant_names: list[str]


@dataclass
class MonthlyPayrollSourcePayload:
    entries: pd.DataFrame
    deductions: pd.DataFrame
    personnel_df: pd.DataFrame
    role_history_df: pd.DataFrame
    month_options: list[str]


def load_reporting_entries_and_month_options(conn) -> tuple[pd.DataFrame, list[str]]:
    entries = fetch_reporting_entries(conn)
    if entries.empty:
        return entries, []
    entries = entries.copy()
    entries["entry_date"] = pd.to_datetime(entries["entry_date"])
    month_options = sorted(entries["entry_date"].dt.strftime("%Y-%m").unique(), reverse=True)
    return entries, month_options


def load_monthly_payroll_source_payload(conn) -> MonthlyPayrollSourcePayload:
    entries = fetch_reporting_entries(conn)
    deductions = fetch_reporting_all_deductions(conn)
    personnel_df = fetch_reporting_personnel(conn)
    role_history_df = fetch_reporting_role_history(conn)

    entries = entries.copy() if not entries.empty else pd.DataFrame()
    deductions = deductions.copy() if not deductions.empty else pd.DataFrame()

    date_series: list[str] = []
    if not entries.empty:
        entries["entry_date"] = pd.to_datetime(entries["entry_date"])
        date_series.extend(entries["entry_date"].dt.strftime("%Y-%m").dropna().tolist())
    if not deductions.empty:
        deductions["deduction_date"] = pd.to_datetime(deductions["deduction_date"])
        date_series.extend(deductions["deduction_date"].dt.strftime("%Y-%m").dropna().tolist())

    month_options = sorted(pd.Series(date_series).dropna().unique().tolist(), reverse=True) if date_series else []
    return MonthlyPayrollSourcePayload(
        entries=entries,
        deductions=deductions,
        personnel_df=personnel_df,
        role_history_df=role_history_df,
        month_options=month_options,
    )


def build_reports_workspace_payload(conn, entries: pd.DataFrame, selected_month: str) -> ReportsWorkspacePayload:
    start_date, end_date = month_bounds(selected_month)
    month_df = entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy()

    restaurants_df = fetch_reporting_restaurants(conn)
    personnel_df = fetch_reporting_personnel(conn)
    role_history_df = fetch_reporting_role_history(conn)
    deductions_df = fetch_reporting_deductions_for_period(conn, start_date, end_date)
    payroll_deductions_df = filter_payroll_effective_deductions_df(deductions_df)

    invoice_df = build_invoice_summary_df(month_df).sort_values("restoran").reset_index(drop=True)
    invoice_drilldown_map = build_restaurant_invoice_drilldown_map(month_df, personnel_df)
    invoice_attendance_export_map = build_restaurant_attendance_export_map(
        month_df,
        personnel_df,
        selected_month,
        invoice_drilldown_map=invoice_drilldown_map,
    )

    cost_df = calculate_personnel_cost(month_df, personnel_df, payroll_deductions_df, role_history_df=role_history_df)
    revenue = float(invoice_df["kdv_dahil"].sum()) if not invoice_df.empty else 0.0
    personnel_cost = float(cost_df["net_maliyet"].sum()) if not cost_df.empty else 0.0
    gross_profit = revenue - personnel_cost

    equipment_profit_df, equipment_purchase_df = build_equipment_profitability_frames(conn, start_date, end_date)
    motor_rental_profit_df, motor_sale_profit_df, equipment_only_profit_df = split_equipment_profit_categories(equipment_profit_df)

    accounting_ded = deductions_df[deductions_df["deduction_type"] == "Muhasebe Ücreti"].copy() if not deductions_df.empty else pd.DataFrame()
    setup_ded = deductions_df[deductions_df["deduction_type"] == "Şirket Açılış Ücreti"].copy() if not deductions_df.empty else pd.DataFrame()

    accounting_rev = float(accounting_ded["amount"].sum()) if not accounting_ded.empty else 0.0
    setup_rev = float(setup_ded["amount"].sum()) if not setup_ded.empty else 0.0
    accounting_person_ids = accounting_ded["personnel_id"].dropna().astype(int).unique().tolist() if not accounting_ded.empty else []
    setup_person_ids = setup_ded["personnel_id"].dropna().astype(int).unique().tolist() if not setup_ded.empty else []
    accountant_cost_total = float(personnel_df.loc[personnel_df["id"].isin(accounting_person_ids), "accountant_cost"].fillna(0).sum()) if accounting_person_ids and "accountant_cost" in personnel_df.columns else 0.0
    setup_cost = float(personnel_df.loc[personnel_df["id"].isin(setup_person_ids), "company_setup_cost"].fillna(0).sum()) if setup_person_ids and "company_setup_cost" in personnel_df.columns else 0.0

    motor_rental_rev = float(motor_rental_profit_df["total_sale"].sum()) if not motor_rental_profit_df.empty else 0.0
    motor_rental_cost = float(motor_rental_profit_df["total_cost"].sum()) if not motor_rental_profit_df.empty else 0.0
    motor_sale_rev = float(motor_sale_profit_df["total_sale"].sum()) if not motor_sale_profit_df.empty else 0.0
    motor_sale_cost = float(motor_sale_profit_df["total_cost"].sum()) if not motor_sale_profit_df.empty else 0.0
    equipment_rev = float(equipment_only_profit_df["total_sale"].sum()) if not equipment_only_profit_df.empty else 0.0
    equipment_cost = float(equipment_only_profit_df["total_cost"].sum()) if not equipment_only_profit_df.empty else 0.0
    fuel_discount_summary = calculate_fuel_discount_summary(deductions_df, personnel_df)
    fuel_reflection_amount = fuel_discount_summary["fuel_reflection_amount"]
    company_fuel_reflection_amount = fuel_discount_summary["company_fuel_reflection_amount"]
    utts_fuel_discount_amount = fuel_discount_summary["utts_fuel_discount_amount"]
    partner_card_discount_amount = fuel_discount_summary["partner_card_discount_amount"]

    side_income_net = (accounting_rev - accountant_cost_total) + (setup_rev - setup_cost) + (equipment_rev - equipment_cost)
    side_income_net += (motor_rental_rev - motor_rental_cost) + (motor_sale_rev - motor_sale_cost)
    side_income_net += utts_fuel_discount_amount + partner_card_discount_amount
    side_df = build_side_income_summary_df(
        accounting_rev=accounting_rev,
        accountant_cost_total=accountant_cost_total,
        setup_rev=setup_rev,
        setup_cost=setup_cost,
        motor_rental_rev=motor_rental_rev,
        motor_rental_cost=motor_rental_cost,
        motor_sale_rev=motor_sale_rev,
        motor_sale_cost=motor_sale_cost,
        equipment_rev=equipment_rev,
        equipment_cost=equipment_cost,
        utts_fuel_discount_amount=utts_fuel_discount_amount,
        partner_card_discount_amount=partner_card_discount_amount,
    )

    profit_df, person_distribution_df, shared_overhead_df = build_branch_profitability(
        month_df,
        personnel_df,
        payroll_deductions_df,
        invoice_df,
        role_history_df=role_history_df,
        restaurants_df=restaurants_df,
    )

    operational_restaurant_names = get_operational_restaurant_names_for_period(
        restaurants_df,
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
    )

    return ReportsWorkspacePayload(
        month_df=month_df,
        restaurants_df=restaurants_df,
        personnel_df=personnel_df,
        role_history_df=role_history_df,
        deductions_df=deductions_df,
        invoice_df=invoice_df,
        invoice_drilldown_map=invoice_drilldown_map,
        invoice_attendance_export_map=invoice_attendance_export_map,
        cost_df=cost_df,
        profit_df=profit_df,
        person_distribution_df=person_distribution_df,
        shared_overhead_df=shared_overhead_df,
        side_df=side_df,
        equipment_profit_df=equipment_profit_df,
        equipment_purchase_df=equipment_purchase_df,
        revenue=revenue,
        personnel_cost=personnel_cost,
        gross_profit=gross_profit,
        side_income_net=side_income_net,
        fuel_reflection_amount=fuel_reflection_amount,
        company_fuel_reflection_amount=company_fuel_reflection_amount,
        utts_fuel_discount_amount=utts_fuel_discount_amount,
        partner_card_discount_amount=partner_card_discount_amount,
        operational_restaurant_names=operational_restaurant_names,
    )
