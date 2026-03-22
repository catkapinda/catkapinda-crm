from __future__ import annotations

from datetime import date

import streamlit as st


_AUTO_ACCOUNTING_DEDUCTION = 0.0
_AUTO_ACCOUNTANT_COST = 0.0
_AUTO_COMPANY_SETUP_REVENUE = 0.0
_AUTO_COMPANY_SETUP_COST = 0.0
_FIXED_COST_MODEL_BY_ROLE: dict[str, str] = {}
_PERSONNEL_ROLE_OPTIONS: list[str] = []


def configure_personnel_rules(
    *,
    auto_accounting_deduction: float,
    auto_accountant_cost: float,
    auto_company_setup_revenue: float,
    auto_company_setup_cost: float,
    fixed_cost_model_by_role: dict[str, str],
    personnel_role_options: list[str],
) -> None:
    global _AUTO_ACCOUNTING_DEDUCTION
    global _AUTO_ACCOUNTANT_COST
    global _AUTO_COMPANY_SETUP_REVENUE
    global _AUTO_COMPANY_SETUP_COST
    global _FIXED_COST_MODEL_BY_ROLE
    global _PERSONNEL_ROLE_OPTIONS

    _AUTO_ACCOUNTING_DEDUCTION = float(auto_accounting_deduction)
    _AUTO_ACCOUNTANT_COST = float(auto_accountant_cost)
    _AUTO_COMPANY_SETUP_REVENUE = float(auto_company_setup_revenue)
    _AUTO_COMPANY_SETUP_COST = float(auto_company_setup_cost)
    _FIXED_COST_MODEL_BY_ROLE = dict(fixed_cost_model_by_role)
    _PERSONNEL_ROLE_OPTIONS = list(personnel_role_options)


def resolve_motor_rental_value(vehicle_type: str, motor_rental: str, motor_purchase: str = "Hayır") -> str:
    if str(motor_purchase or "Hayır").strip() == "Evet":
        return "Hayır"
    normalized_vehicle_type = (vehicle_type or "").strip()
    if normalized_vehicle_type == "Kendi":
        normalized_vehicle_type = "Kendi Motoru"
    if normalized_vehicle_type == "Çat Kapında":
        return "Evet"
    if normalized_vehicle_type == "Kendi Motoru":
        return "Hayır"
    return "Evet" if (motor_rental or "Hayır") == "Evet" else "Hayır"


def resolve_vehicle_type_value(vehicle_type: str, motor_rental: str = "Hayır") -> str:
    normalized_vehicle_type = (vehicle_type or "").strip()
    if normalized_vehicle_type == "Kendi":
        normalized_vehicle_type = "Kendi Motoru"
    if normalized_vehicle_type in ["Çat Kapında", "Kendi Motoru"]:
        return normalized_vehicle_type
    return "Çat Kapında" if (motor_rental or "Hayır") == "Evet" else "Kendi Motoru"


def resolve_motor_usage_mode(vehicle_type: str, motor_purchase: str, motor_rental: str = "Hayır") -> str:
    normalized_vehicle_type = resolve_vehicle_type_value(vehicle_type, motor_rental)
    if str(motor_purchase or "Hayır").strip() == "Evet":
        return "Çat Kapında Motor Satışı"
    if normalized_vehicle_type == "Çat Kapında":
        return "Çat Kapında Motor Kirası"
    return "Kendi Motoru"


def resolve_motor_usage_fields(motor_usage_mode: str) -> tuple[str, str]:
    normalized_mode = str(motor_usage_mode or "").strip()
    if normalized_mode == "Çat Kapında Motor Satışı":
        return "Çat Kapında", "Evet"
    if normalized_mode == "Çat Kapında Motor Kirası":
        return "Çat Kapında", "Hayır"
    return "Kendi Motoru", "Hayır"


def role_requires_primary_restaurant(role: str) -> bool:
    return str(role or "").strip() in {"Kurye", "Restoran Takım Şefi"}


def resolve_accounting_defaults(accounting_type: str) -> tuple[float, float]:
    if (accounting_type or "").strip() == "Çat Kapında Muhasebe":
        return _AUTO_ACCOUNTING_DEDUCTION, _AUTO_ACCOUNTANT_COST
    return 0.0, 0.0


def resolve_company_setup_defaults(new_company_setup: str) -> tuple[float, float]:
    if (new_company_setup or "").strip() == "Evet":
        return _AUTO_COMPANY_SETUP_REVENUE, _AUTO_COMPANY_SETUP_COST
    return 0.0, 0.0


def resolve_fixed_cost_model(role: str) -> str:
    normalized_role = (role or "").strip()
    if normalized_role == "Kurye":
        return "standard_courier"
    return _FIXED_COST_MODEL_BY_ROLE.get(normalized_role, "standard_courier")


def get_role_fixed_cost_label(role: str, transition: bool = False) -> str:
    normalized_role = str(role or "").strip()
    if normalized_role not in _FIXED_COST_MODEL_BY_ROLE:
        return "Aylık Sabit Maliyet"
    suffix = "Sabit Maaşı" if transition else "Aylık Sabit Maliyeti"
    return f"{normalized_role} {suffix}"


def resolve_cost_role_option(cost_model: str, role: str) -> str:
    normalized = (cost_model or "").strip()
    reverse_labels = {value: key for key, value in _FIXED_COST_MODEL_BY_ROLE.items()}
    if normalized in reverse_labels:
        return reverse_labels[normalized]
    if normalized in _PERSONNEL_ROLE_OPTIONS:
        return normalized

    normalized_role = (role or "").strip()
    if normalized in ["", "standard_courier", "fixed_kurye"]:
        return normalized_role if normalized_role in _PERSONNEL_ROLE_OPTIONS else "Kurye"
    return normalized_role if normalized_role in _PERSONNEL_ROLE_OPTIONS else "Kurye"


def normalize_cost_model_value(cost_model: str, role: str) -> str:
    if (cost_model or "").strip() == "fixed_monthly":
        return resolve_fixed_cost_model(role)
    return resolve_fixed_cost_model(resolve_cost_role_option(cost_model, role))


def is_fixed_cost_model(cost_model: str) -> bool:
    return normalize_cost_model_value(cost_model, "Kurye") != "standard_courier"


def initialize_edit_person_transition_state(
    selected_id: int,
    row_role_value: str,
    monthly_fixed_cost: float,
    start_date_value: date | None,
) -> None:
    default_role = row_role_value if row_role_value in _PERSONNEL_ROLE_OPTIONS else "Kurye"
    st.session_state[f"edit_person_transition_enabled_{selected_id}"] = False
    st.session_state[f"edit_person_previous_role_{selected_id}"] = default_role
    st.session_state[f"edit_person_transition_new_role_{selected_id}"] = default_role
    st.session_state[f"edit_person_transition_monthly_cost_{selected_id}"] = float(monthly_fixed_cost or 0.0)
    st.session_state[f"edit_person_transition_date_{selected_id}"] = start_date_value if start_date_value else date.today()


def resolve_effective_role_from_transition(
    current_role: str,
    transition_enabled: bool,
    transition_new_role: str,
) -> tuple[str, bool]:
    effective_role = transition_new_role if transition_enabled else current_role
    return effective_role, effective_role != current_role


def validate_role_transition_inputs(
    *,
    role_changed: bool,
    transition_enabled: bool,
    transition_previous_role: str,
    effective_role: str,
    transition_effective_date: date | None,
    start_date_value: date | None,
) -> list[str]:
    errors: list[str] = []
    if role_changed and not transition_enabled:
        errors.append("Rol değişikliği yapıyorsan rol başlangıç tarihini de kaydetmelisin.")
        return errors
    if transition_enabled and not role_changed:
        errors.append("Rol değişikliği kaydı eklemek için yeni rol mevcut rolden farklı olmalı.")
        return errors
    if not (role_changed and transition_enabled):
        return errors
    if transition_previous_role == effective_role:
        errors.append("Rol geçiş kaydında önceki rol ile yeni rol farklı olmalı.")
    if not isinstance(transition_effective_date, date):
        errors.append("Rol başlangıç tarihi zorunlu.")
    elif isinstance(start_date_value, date) and transition_effective_date < start_date_value:
        errors.append("Rol başlangıç tarihi işe giriş tarihinden önce olamaz.")
    return errors
