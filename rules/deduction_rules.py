from __future__ import annotations

from typing import Any

import pandas as pd


DEDUCTION_TYPE_OPTIONS = [
    "Bakım",
    "Yakıt",
    "HGS",
    "İdari ceza",
    "Hasar",
    "Fatura Edilmeyen Tutar",
    "Avans",
    "Partner Kart İndirimi",
]

HGS_VAT_RATE = 0.20
COMPANY_FUEL_DISCOUNT_RATE = 0.07
COMPANY_VEHICLE_TYPE = "Çat Kapında"
SIDE_INCOME_ONLY_DEDUCTION_TYPES = {"Partner Kart İndirimi"}


def normalize_deduction_type(value: Any) -> str:
    return str(value or "").strip()


def is_hgs_deduction_type(deduction_type: Any) -> bool:
    return normalize_deduction_type(deduction_type).lower() == "hgs"


def is_side_income_only_deduction_type(deduction_type: Any) -> bool:
    return normalize_deduction_type(deduction_type) in SIDE_INCOME_ONLY_DEDUCTION_TYPES


def get_deduction_type_caption(deduction_type: Any) -> str:
    normalized_type = normalize_deduction_type(deduction_type)
    if normalized_type == "HGS":
        return "HGS tutarını net gider olarak gir; sistem hakedişe %20 KDV dahil kesinti yazar."
    if normalized_type == "Yakıt":
        return "Yakıt tutarını kuryeye yansıtılacak %20 KDV dahil fatura toplamı olarak gir. Çat Kapında motorlarında %7 UTTS indirimi yan gelire otomatik eklenir."
    if normalized_type == "Partner Kart İndirimi":
        return "Kendi motoruyla çalışan kuryelerin ay sonu kart indirim gelirini manuel gir. Bu kalem hakedişten düşülmez, sadece yan gelirde görünür."
    if normalized_type == "Avans":
        return "Personele verilen avansı ay sonu hakedişinden düşmek için kaydet."
    return ""


def filter_payroll_effective_deductions_df(deductions_df: pd.DataFrame | None) -> pd.DataFrame:
    if deductions_df is None:
        return pd.DataFrame()
    if deductions_df.empty or "deduction_type" not in deductions_df.columns:
        return deductions_df.copy()
    return deductions_df[
        ~deductions_df["deduction_type"].fillna("").astype(str).isin(SIDE_INCOME_ONLY_DEDUCTION_TYPES)
    ].copy()


def calculate_fuel_discount_summary(
    deductions_df: pd.DataFrame | None,
    personnel_df: pd.DataFrame | None,
) -> dict[str, float]:
    if deductions_df is None or deductions_df.empty:
        return {
            "fuel_reflection_amount": 0.0,
            "company_fuel_reflection_amount": 0.0,
            "utts_fuel_discount_amount": 0.0,
            "partner_card_discount_amount": 0.0,
        }

    deductions_work = deductions_df.copy()
    deductions_work["deduction_type"] = deductions_work["deduction_type"].fillna("").astype(str)
    fuel_deductions_df = deductions_work[deductions_work["deduction_type"] == "Yakıt"].copy()
    partner_discount_df = deductions_work[deductions_work["deduction_type"] == "Partner Kart İndirimi"].copy()

    fuel_reflection_amount = float(fuel_deductions_df["amount"].fillna(0).sum()) if not fuel_deductions_df.empty else 0.0
    partner_card_discount_amount = float(partner_discount_df["amount"].fillna(0).sum()) if not partner_discount_df.empty else 0.0

    company_fuel_reflection_amount = 0.0
    if (
        not fuel_deductions_df.empty
        and personnel_df is not None
        and not personnel_df.empty
        and {"id", "vehicle_type"}.issubset(set(personnel_df.columns))
        and "personnel_id" in fuel_deductions_df.columns
    ):
        company_person_ids = (
            personnel_df[
                personnel_df["vehicle_type"].fillna("").astype(str).str.strip() == COMPANY_VEHICLE_TYPE
            ]["id"]
            .dropna()
            .astype(int)
            .tolist()
        )
        if company_person_ids:
            company_fuel_reflection_amount = float(
                fuel_deductions_df[fuel_deductions_df["personnel_id"].isin(company_person_ids)]["amount"].fillna(0).sum()
            )

    utts_fuel_discount_amount = round(company_fuel_reflection_amount * COMPANY_FUEL_DISCOUNT_RATE, 2)

    return {
        "fuel_reflection_amount": fuel_reflection_amount,
        "company_fuel_reflection_amount": company_fuel_reflection_amount,
        "utts_fuel_discount_amount": utts_fuel_discount_amount,
        "partner_card_discount_amount": partner_card_discount_amount,
    }
