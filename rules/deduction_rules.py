from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd


MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE = "Motor Servis Bakım"
MOTOR_DAMAGE_DEDUCTION_TYPE = "Motor Hasar"
HELMET_DEDUCTION_TYPE = "Kask"
PHONE_MOUNT_DEDUCTION_TYPE = "Telefon Tutacağı"
PROTECTIVE_JACKET_DEDUCTION_TYPE = "Korumalı Mont"
RAINCOAT_DEDUCTION_TYPE = "Yağmurluk"
BOX_DEDUCTION_TYPE = "Box"
PUNCH_DEDUCTION_TYPE = "Punch"
TSHIRT_DEDUCTION_TYPE = "Tişört"
POLAR_DEDUCTION_TYPE = "Polar"
VEST_DEDUCTION_TYPE = "Yelek"
CHEST_BAG_DEDUCTION_TYPE = "Göğüs Çantası"
ADVANCE_DEDUCTION_TYPE = "Avans"
ADMINISTRATIVE_FINE_DEDUCTION_TYPE = "İdari ceza"
NON_INVOICED_AMOUNT_DEDUCTION_TYPE = "Fatura Edilmeyen Tutar"
FUEL_DEDUCTION_TYPE = "Yakıt"
HGS_DEDUCTION_TYPE = "HGS"
PARTNER_CARD_DISCOUNT_DEDUCTION_TYPE = "Partner Kart İndirimi"
REDUCED_DEDUCTION_VAT_START_DATE = date(2026, 3, 1)

LEGACY_DEDUCTION_TYPE_MAP = {
    "Bakım": MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    "Hasar": MOTOR_DAMAGE_DEDUCTION_TYPE,
}

DEDUCTION_TYPE_OPTIONS = [
    MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    FUEL_DEDUCTION_TYPE,
    HGS_DEDUCTION_TYPE,
    HELMET_DEDUCTION_TYPE,
    PHONE_MOUNT_DEDUCTION_TYPE,
    MOTOR_DAMAGE_DEDUCTION_TYPE,
    PROTECTIVE_JACKET_DEDUCTION_TYPE,
    RAINCOAT_DEDUCTION_TYPE,
    BOX_DEDUCTION_TYPE,
    PUNCH_DEDUCTION_TYPE,
    TSHIRT_DEDUCTION_TYPE,
    POLAR_DEDUCTION_TYPE,
    VEST_DEDUCTION_TYPE,
    CHEST_BAG_DEDUCTION_TYPE,
    ADMINISTRATIVE_FINE_DEDUCTION_TYPE,
    NON_INVOICED_AMOUNT_DEDUCTION_TYPE,
    ADVANCE_DEDUCTION_TYPE,
]

HGS_VAT_RATE = 0.20
COMPANY_FUEL_DISCOUNT_RATE = 0.0
COMPANY_VEHICLE_TYPE = "Çat Kapında"
TWENTY_PERCENT_VAT_INCLUDED_DEDUCTION_TYPES = {
    MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE,
    FUEL_DEDUCTION_TYPE,
    HGS_DEDUCTION_TYPE,
    MOTOR_DAMAGE_DEDUCTION_TYPE,
    HELMET_DEDUCTION_TYPE,
    PHONE_MOUNT_DEDUCTION_TYPE,
}
TEN_PERCENT_VAT_INCLUDED_DEDUCTION_TYPES = {
    PROTECTIVE_JACKET_DEDUCTION_TYPE,
    RAINCOAT_DEDUCTION_TYPE,
    BOX_DEDUCTION_TYPE,
    PUNCH_DEDUCTION_TYPE,
    TSHIRT_DEDUCTION_TYPE,
    POLAR_DEDUCTION_TYPE,
    VEST_DEDUCTION_TYPE,
    CHEST_BAG_DEDUCTION_TYPE,
}
NON_INVOICED_DEDUCTION_TYPES = {
    ADMINISTRATIVE_FINE_DEDUCTION_TYPE,
    ADVANCE_DEDUCTION_TYPE,
}
SIDE_INCOME_ONLY_DEDUCTION_TYPES: set[str] = set()
PAYROLL_EXCLUDED_DEDUCTION_TYPES = {PARTNER_CARD_DISCOUNT_DEDUCTION_TYPE} | NON_INVOICED_DEDUCTION_TYPES


def normalize_deduction_type(value: Any) -> str:
    normalized_value = str(value or "").strip()
    return LEGACY_DEDUCTION_TYPE_MAP.get(normalized_value, normalized_value)


def is_hgs_deduction_type(deduction_type: Any) -> bool:
    return normalize_deduction_type(deduction_type) == HGS_DEDUCTION_TYPE


def is_side_income_only_deduction_type(deduction_type: Any) -> bool:
    return normalize_deduction_type(deduction_type) in SIDE_INCOME_ONLY_DEDUCTION_TYPES


def is_non_invoiced_deduction_type(deduction_type: Any) -> bool:
    return normalize_deduction_type(deduction_type) in NON_INVOICED_DEDUCTION_TYPES


def _is_yes_value(value: Any) -> bool:
    return str(value or "").strip().lower() == "evet"


def _parse_deduction_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    normalized_value = str(value).strip()
    if not normalized_value:
        return None
    try:
        return datetime.fromisoformat(normalized_value).date()
    except ValueError:
        return None


def get_deduction_vat_rate(deduction_type: Any, deduction_date: Any = None) -> float:
    return 0.0


def get_deduction_type_caption(deduction_type: Any) -> str:
    normalized_type = normalize_deduction_type(deduction_type)
    if normalized_type == MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE:
        return "Motor servis bakımında Çat Kapında kiralık motorları şirket öder. Çat Kapında satılık motor ve kendi motorunda bakım kuryeden kesilir."
    if normalized_type == MOTOR_DAMAGE_DEDUCTION_TYPE:
        return "Motor hasar bedeli tüm motor tiplerinde kuryeye yansıtılır. Girdiğin tutar aynen kesinti olur."
    if normalized_type == HGS_DEDUCTION_TYPE:
        return "HGS tutarını ödediğin toplam olarak gir. Sistem hakedişe aynı tutarı yazar, ekstra KDV eklemez."
    if normalized_type == FUEL_DEDUCTION_TYPE:
        return "Yakıt tutarını kuryeye yansıtılacak toplam olarak gir. Sistem tutarı aynen kesinti yazar; UTTS indirimi hesaplamaz."
    if normalized_type == HELMET_DEDUCTION_TYPE:
        return "Kask bedelini kuryeye yansıtılacak toplam olarak gir. Tutar aynen kesilir."
    if normalized_type == PHONE_MOUNT_DEDUCTION_TYPE:
        return "Telefon tutacağı bedelini kuryeye yansıtılacak toplam olarak gir. Tutar aynen kesilir."
    if normalized_type in TEN_PERCENT_VAT_INCLUDED_DEDUCTION_TYPES:
        return "Bu kalemde girdiğin tutar aynen kesinti olur; ayrıca KDV oranı uygulanmaz."
    if normalized_type == PARTNER_CARD_DISCOUNT_DEDUCTION_TYPE:
        return "Partner kart indirimi artık finansal hesaba katılmaz."
    if normalized_type == ADVANCE_DEDUCTION_TYPE:
        return "Personele verilen avansı tahsilat takibi için kaydet. Ödeme düşer ama kurye fatura matrahı bu kalemden etkilenmez."
    if normalized_type == ADMINISTRATIVE_FINE_DEDUCTION_TYPE:
        return "İdari ceza ödeme tahsilatı için kaydedilir. Bu kalem için ayrıca fatura KDV hesabı yapılmaz."
    if normalized_type == NON_INVOICED_AMOUNT_DEDUCTION_TYPE:
        return "Fatura edilmeyen tutarı kuryeden tahsilat takibi için kaydet."
    return ""


def filter_payroll_effective_deductions_df(
    deductions_df: pd.DataFrame | None,
    personnel_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if deductions_df is None:
        return pd.DataFrame()
    if deductions_df.empty or "deduction_type" not in deductions_df.columns:
        return deductions_df.copy()
    normalized_types = deductions_df["deduction_type"].apply(normalize_deduction_type)
    filtered_df = deductions_df[~normalized_types.isin(PAYROLL_EXCLUDED_DEDUCTION_TYPES)].copy()
    if filtered_df.empty:
        return filtered_df
    if (
        personnel_df is None
        or personnel_df.empty
        or "personnel_id" not in filtered_df.columns
        or not {"id", "vehicle_type", "motor_purchase"}.issubset(set(personnel_df.columns))
    ):
        return filtered_df

    personnel_work = personnel_df[["id", "vehicle_type", "motor_purchase"]].copy()
    personnel_work["id"] = pd.to_numeric(personnel_work["id"], errors="coerce")
    personnel_work = personnel_work.dropna(subset=["id"]).copy()
    if personnel_work.empty:
        return filtered_df

    rental_company_person_ids = (
        personnel_work[
            (personnel_work["vehicle_type"].fillna("").astype(str).str.strip() == COMPANY_VEHICLE_TYPE)
            & (~personnel_work["motor_purchase"].map(_is_yes_value))
        ]["id"]
        .astype(int)
        .tolist()
    )
    if not rental_company_person_ids:
        return filtered_df

    filtered_df["personnel_id"] = pd.to_numeric(filtered_df["personnel_id"], errors="coerce")
    filtered_df["_normalized_deduction_type"] = filtered_df["deduction_type"].apply(normalize_deduction_type)
    payroll_df = filtered_df[
        ~(
            filtered_df["_normalized_deduction_type"].eq(MOTOR_SERVICE_MAINTENANCE_DEDUCTION_TYPE)
            & filtered_df["personnel_id"].isin(rental_company_person_ids)
        )
    ].copy()
    return payroll_df.drop(columns=["_normalized_deduction_type"], errors="ignore")


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

    fuel_reflection_amount = float(fuel_deductions_df["amount"].fillna(0).sum()) if not fuel_deductions_df.empty else 0.0
    partner_card_discount_amount = 0.0

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
