from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable

import streamlit as st


_SAFE_INT: Callable[[Any, int], int] | None = None
_SAFE_FLOAT: Callable[[Any, float], float] | None = None
_FMT_TRY: Callable[[Any], str] | None = None
_RENDER_RECORD_SNAPSHOT: Callable[[str, list[tuple[str, Any]]], None] | None = None
_RESOLVE_MOTOR_USAGE_FIELDS: Callable[[str], tuple[str, str]] | None = None
_RESOLVE_MOTOR_RENTAL_VALUE: Callable[[str, str, str], str] | None = None
_ROLE_REQUIRES_PRIMARY_RESTAURANT: Callable[[str], bool] | None = None
_IS_FIXED_COST_MODEL: Callable[[str], bool] | None = None
_GET_EQUIPMENT_VAT_RATE: Callable[[str, date | str | None], float] | None = None
_GET_DEFAULT_EQUIPMENT_SALE_PRICE: Callable[[str], float] | None = None
_GET_DEFAULT_ISSUE_INSTALLMENT_COUNT: Callable[[str], int] | None = None
_GET_DEFAULT_EQUIPMENT_UNIT_COST: Callable[[Any, str], float] | None = None

_AUTO_MOTOR_RENTAL_DEDUCTION = 13000.0
_EQUIPMENT_ITEMS: list[str] = []


def configure_form_rules(
    *,
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    fmt_try_fn: Callable[[Any], str],
    render_record_snapshot_fn: Callable[[str, list[tuple[str, Any]]], None],
    resolve_motor_usage_fields_fn: Callable[[str], tuple[str, str]],
    resolve_motor_rental_value_fn: Callable[[str, str, str], str],
    role_requires_primary_restaurant_fn: Callable[[str], bool],
    is_fixed_cost_model_fn: Callable[[str], bool],
    get_equipment_vat_rate_fn: Callable[[str, date | str | None], float],
    get_default_equipment_sale_price_fn: Callable[[str], float],
    get_default_issue_installment_count_fn: Callable[[str], int],
    get_default_equipment_unit_cost_fn: Callable[[Any, str], float],
    auto_motor_rental_deduction: float,
    equipment_items: list[str],
) -> None:
    global _SAFE_INT
    global _SAFE_FLOAT
    global _FMT_TRY
    global _RENDER_RECORD_SNAPSHOT
    global _RESOLVE_MOTOR_USAGE_FIELDS
    global _RESOLVE_MOTOR_RENTAL_VALUE
    global _ROLE_REQUIRES_PRIMARY_RESTAURANT
    global _IS_FIXED_COST_MODEL
    global _GET_EQUIPMENT_VAT_RATE
    global _GET_DEFAULT_EQUIPMENT_SALE_PRICE
    global _GET_DEFAULT_ISSUE_INSTALLMENT_COUNT
    global _GET_DEFAULT_EQUIPMENT_UNIT_COST
    global _AUTO_MOTOR_RENTAL_DEDUCTION
    global _EQUIPMENT_ITEMS

    _SAFE_INT = safe_int_fn
    _SAFE_FLOAT = safe_float_fn
    _FMT_TRY = fmt_try_fn
    _RENDER_RECORD_SNAPSHOT = render_record_snapshot_fn
    _RESOLVE_MOTOR_USAGE_FIELDS = resolve_motor_usage_fields_fn
    _RESOLVE_MOTOR_RENTAL_VALUE = resolve_motor_rental_value_fn
    _ROLE_REQUIRES_PRIMARY_RESTAURANT = role_requires_primary_restaurant_fn
    _IS_FIXED_COST_MODEL = is_fixed_cost_model_fn
    _GET_EQUIPMENT_VAT_RATE = get_equipment_vat_rate_fn
    _GET_DEFAULT_EQUIPMENT_SALE_PRICE = get_default_equipment_sale_price_fn
    _GET_DEFAULT_ISSUE_INSTALLMENT_COUNT = get_default_issue_installment_count_fn
    _GET_DEFAULT_EQUIPMENT_UNIT_COST = get_default_equipment_unit_cost_fn
    _AUTO_MOTOR_RENTAL_DEDUCTION = float(auto_motor_rental_deduction)
    _EQUIPMENT_ITEMS = list(equipment_items)


def calculate_motor_purchase_monthly_reference(monthly_amount: float, commitment_months: int) -> float:
    resolved_months = max(int(commitment_months or 0), 0)
    if resolved_months <= 0:
        return 0.0
    return round(max(float(monthly_amount or 0), 0.0), 2)


def render_vehicle_transition_caption() -> None:
    st.caption(
        "Motor düzeni değiştiyse bu tarih, yeni kullanım modelinin geçerli olduğu ilk günü temsil eder. "
        "Kesintiler bu bilgiye göre manuel takip edilir."
    )


def render_motor_purchase_proration_caption() -> None:
    st.caption(
        "Bu tarih aylık motor satış taksidinin başladığı ilk gündür. Ayın 1'i değilse ilk ay tutarı, "
        "bu tarihten ay sonuna kadar prorate edilir."
    )


def render_motor_deduction_snapshot(
    *,
    vehicle_type: str,
    motor_purchase: str,
    motor_rental_monthly_amount: float = 13000.0,
    sale_price: float = 0.0,
    commitment_months: int = 0,
) -> None:
    items: list[tuple[str, Any]] = []
    if str(vehicle_type or "").strip() == "Çat Kapında" and str(motor_purchase or "Hayır").strip() != "Evet":
        items.append(("Motor Kirası", f"{_FMT_TRY(motor_rental_monthly_amount)} / ay"))
    if str(motor_purchase or "Hayır").strip() == "Evet":
        monthly_reference = calculate_motor_purchase_monthly_reference(_SAFE_FLOAT(sale_price, 0.0), _SAFE_INT(commitment_months, 0))
        if monthly_reference > 0:
            items.append(("Aylık Motor Satış Taksiti", f"{_FMT_TRY(monthly_reference)} / ay"))
        if _SAFE_INT(commitment_months, 0) > 0:
            items.append(("Taahhüt", f"{_SAFE_INT(commitment_months, 0)} ay"))
        items.append(("Motor Kirası", "Uygulanmaz"))
    if not items:
        return
    _RENDER_RECORD_SNAPSHOT("Motor Kesinti Referansı", items)
    st.caption(
        "Bu özet yalnızca referans amaçlıdır. Motor kira ve motor satış kesintilerini bu kurala göre "
        "manuel girebilirsin."
    )


def build_motor_usage_payload(
    *,
    motor_usage_mode: str,
    motor_rental_monthly_amount: float,
    motor_purchase_start_date_value: date | None,
    motor_purchase_commitment_months: int | None,
    motor_purchase_sale_price: float,
) -> dict[str, Any]:
    vehicle_type, motor_purchase = _RESOLVE_MOTOR_USAGE_FIELDS(motor_usage_mode)
    sale_mode_enabled = motor_purchase == "Evet"
    motor_rental = "Hayır" if sale_mode_enabled else _RESOLVE_MOTOR_RENTAL_VALUE(vehicle_type, "Hayır", motor_purchase)
    motor_rental_monthly_amount_value = (
        _SAFE_FLOAT(motor_rental_monthly_amount, 0.0)
        if motor_usage_mode == "Çat Kapında Motor Kirası"
        else 0.0
    )
    motor_purchase_start_date_str = (
        motor_purchase_start_date_value.isoformat()
        if sale_mode_enabled and isinstance(motor_purchase_start_date_value, date)
        else None
    )
    motor_purchase_commitment_value = _SAFE_INT(motor_purchase_commitment_months, 12) if sale_mode_enabled else None
    motor_purchase_sale_price_value = _SAFE_FLOAT(motor_purchase_sale_price, 0.0) if sale_mode_enabled else None
    motor_purchase_monthly_reference = (
        calculate_motor_purchase_monthly_reference(motor_purchase_sale_price_value, motor_purchase_commitment_value)
        if sale_mode_enabled
        else 0.0
    )
    motor_purchase_installment_count_value = motor_purchase_commitment_value if sale_mode_enabled else None
    return {
        "vehicle_type": vehicle_type,
        "motor_rental": motor_rental,
        "motor_purchase": motor_purchase,
        "motor_rental_monthly_amount": motor_rental_monthly_amount_value,
        "motor_purchase_start_date_str": motor_purchase_start_date_str,
        "motor_purchase_commitment_months": motor_purchase_commitment_value,
        "motor_purchase_sale_price": motor_purchase_sale_price_value,
        "motor_purchase_monthly_amount": motor_purchase_monthly_reference,
        "motor_purchase_installment_count": motor_purchase_installment_count_value,
    }


def motor_usage_payload_has_charge(payload: dict[str, Any]) -> bool:
    return (
        str(payload.get("motor_rental", "Hayır") or "Hayır") == "Evet"
        or str(payload.get("motor_purchase", "Hayır") or "Hayır") == "Evet"
    )


def render_motor_deduction_snapshot_from_payload(payload: dict[str, Any]) -> None:
    if not motor_usage_payload_has_charge(payload):
        return
    render_motor_deduction_snapshot(
        vehicle_type=str(payload.get("vehicle_type", "") or ""),
        motor_purchase=str(payload.get("motor_purchase", "Hayır") or "Hayır"),
        motor_rental_monthly_amount=_SAFE_FLOAT(payload.get("motor_rental_monthly_amount", 0.0), 0.0),
        sale_price=_SAFE_FLOAT(
            payload.get("motor_purchase_monthly_amount", payload.get("motor_purchase_sale_price", 0.0)),
            0.0,
        ),
        commitment_months=_SAFE_INT(payload.get("motor_purchase_commitment_months", 0), 0),
    )


def onboarding_equipment_state_key(item_name: str, field_name: str) -> str:
    normalized_item = re.sub(r"[^a-z0-9]+", "_", str(item_name or "").lower()).strip("_")
    normalized_field = re.sub(r"[^a-z0-9]+", "_", str(field_name or "").lower()).strip("_")
    return f"new_person_onboarding_{normalized_item}_{normalized_field}"


def clear_new_person_onboarding_state() -> None:
    st.session_state["new_person_onboarding_items"] = []
    for item_name in _EQUIPMENT_ITEMS:
        for field_name in ["issue_date", "quantity", "sale_price", "vat_rate", "installment_count", "notes"]:
            st.session_state.pop(onboarding_equipment_state_key(item_name, field_name), None)


def initialize_onboarding_equipment_state(conn: Any, item_name: str, default_issue_date: date | None) -> None:
    issue_date_key = onboarding_equipment_state_key(item_name, "issue_date")
    quantity_key = onboarding_equipment_state_key(item_name, "quantity")
    sale_price_key = onboarding_equipment_state_key(item_name, "sale_price")
    vat_rate_key = onboarding_equipment_state_key(item_name, "vat_rate")
    installment_key = onboarding_equipment_state_key(item_name, "installment_count")
    notes_key = onboarding_equipment_state_key(item_name, "notes")

    resolved_issue_date = default_issue_date if isinstance(default_issue_date, date) else date.today()
    default_vat_rate = _GET_EQUIPMENT_VAT_RATE(item_name, resolved_issue_date)
    default_sale_price = _GET_DEFAULT_EQUIPMENT_SALE_PRICE(item_name)
    default_installment_count = _GET_DEFAULT_ISSUE_INSTALLMENT_COUNT(item_name)

    if issue_date_key not in st.session_state or not isinstance(st.session_state.get(issue_date_key), date):
        st.session_state[issue_date_key] = resolved_issue_date
    if quantity_key not in st.session_state:
        st.session_state[quantity_key] = 1
    if sale_price_key not in st.session_state:
        st.session_state[sale_price_key] = float(default_sale_price)
    if vat_rate_key not in st.session_state or _SAFE_FLOAT(st.session_state.get(vat_rate_key), 0.0) not in {10.0, 20.0}:
        st.session_state[vat_rate_key] = float(default_vat_rate if default_vat_rate in {10.0, 20.0} else 10.0)
    if installment_key not in st.session_state:
        st.session_state[installment_key] = int(default_installment_count if default_installment_count in [1, 2, 3, 6, 12] else 2)
    if notes_key not in st.session_state:
        st.session_state[notes_key] = ""


def collect_onboarding_equipment_payloads(conn: Any, selected_items: list[str]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for item_name in selected_items:
        quantity_key = onboarding_equipment_state_key(item_name, "quantity")
        issue_date_key = onboarding_equipment_state_key(item_name, "issue_date")
        sale_price_key = onboarding_equipment_state_key(item_name, "sale_price")
        vat_rate_key = onboarding_equipment_state_key(item_name, "vat_rate")
        installment_key = onboarding_equipment_state_key(item_name, "installment_count")
        notes_key = onboarding_equipment_state_key(item_name, "notes")
        payloads.append(
            {
                "item_name": item_name,
                "issue_date": st.session_state.get(issue_date_key),
                "quantity": max(_SAFE_INT(st.session_state.get(quantity_key), 1), 1),
                "unit_sale_price": max(_SAFE_FLOAT(st.session_state.get(sale_price_key), 0.0), 0.0),
                "vat_rate": 20.0 if _SAFE_FLOAT(st.session_state.get(vat_rate_key), 10.0) >= 20.0 else 10.0,
                "installment_count": max(_SAFE_INT(st.session_state.get(installment_key), 1), 1),
                "unit_cost": max(_GET_DEFAULT_EQUIPMENT_UNIT_COST(conn, item_name), 0.0),
                "notes": str(st.session_state.get(notes_key, "") or "").strip(),
            }
        )
    return payloads


def validate_onboarding_equipment_payloads(payloads: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for payload in payloads:
        item_name = str(payload.get("item_name") or "").strip() or "Ürün"
        if not isinstance(payload.get("issue_date"), date):
            errors.append(f"{item_name} için teslim tarihi zorunlu.")
        if _SAFE_INT(payload.get("quantity"), 0) <= 0:
            errors.append(f"{item_name} için adet en az 1 olmalı.")
        if _SAFE_INT(payload.get("installment_count"), 0) <= 0:
            errors.append(f"{item_name} için taksit sayısı zorunlu.")
        if _SAFE_FLOAT(payload.get("vat_rate"), 0.0) not in {10.0, 20.0}:
            errors.append(f"{item_name} için KDV oranı %10 veya %20 olmalı.")
    return errors


def validate_restaurant_form(
    *,
    brand: str,
    branch: str,
    pricing_model: str,
    hourly_rate: float,
    package_rate: float,
    package_threshold: int,
    package_rate_low: float,
    package_rate_high: float,
    fixed_fee: float,
    headcount: int,
    start_date_value: date | None,
    end_date_value: date | None,
    extra_req: int,
    extra_req_date: date | None,
    reduce_req: int,
    reduce_req_date: date | None,
    contact_name: str,
    contact_phone: str,
    contact_email: str,
    company_title: str,
    address: str,
    tax_office: str,
    tax_number: str,
) -> list[str]:
    errors: list[str] = []
    if not (brand or "").strip():
        errors.append("Marka alanı zorunlu.")
    if not (branch or "").strip():
        errors.append("Şube alanı zorunlu.")
    if not (contact_name or "").strip():
        errors.append("Yetkili ad soyad alanı zorunlu.")
    if not (contact_phone or "").strip():
        errors.append("Yetkili telefon alanı zorunlu.")
    if not (contact_email or "").strip():
        errors.append("Yetkili e-posta alanı zorunlu.")
    if not (tax_office or "").strip():
        errors.append("Vergi dairesi alanı zorunlu.")
    if not (tax_number or "").strip():
        errors.append("Vergi numarası alanı zorunlu.")
    if headcount <= 0:
        errors.append("Hedef kadro 0'dan büyük olmalı.")
    if start_date_value is None:
        errors.append("Başlangıç tarihi zorunlu.")
    if start_date_value and end_date_value and end_date_value < start_date_value:
        errors.append("Bitiş tarihi başlangıç tarihinden önce olamaz.")
    if extra_req > 0 and extra_req_date is None:
        errors.append("Ek kurye talebi girildiğinde ek talep tarihi de seçilmeli.")
    if reduce_req > 0 and reduce_req_date is None:
        errors.append("Kurye azaltma talebi girildiğinde azaltma talep tarihi de seçilmeli.")

    if pricing_model == "hourly_plus_package":
        if hourly_rate <= 0:
            errors.append("Saatlik + Paket modelinde saatlik ücret zorunlu.")
        if package_rate <= 0:
            errors.append("Saatlik + Paket modelinde paket primi zorunlu.")
    elif pricing_model == "threshold_package":
        if hourly_rate <= 0:
            errors.append("Eşikli Paket modelinde saatlik ücret zorunlu.")
        if package_threshold <= 0:
            errors.append("Eşikli Paket modelinde paket eşiği zorunlu.")
        if package_rate_low <= 0 or package_rate_high <= 0:
            errors.append("Eşikli Paket modelinde eşik altı ve eşik üstü primler zorunlu.")
    elif pricing_model == "hourly_only":
        if hourly_rate <= 0:
            errors.append("Sadece Saatlik modelinde saatlik ücret zorunlu.")
    elif pricing_model == "fixed_monthly":
        if fixed_fee <= 0:
            errors.append("Sabit Aylık Ücret modelinde sabit aylık ücret zorunlu.")

    return errors


def validate_personnel_form(
    *,
    full_name: str,
    phone: str,
    tc_no: str,
    iban: str,
    address: str,
    current_plate: str,
    role: str,
    assigned_restaurant_id: int | None,
    start_date_value: date | None,
    vehicle_type: str,
    motor_rental_monthly_amount: float,
    cost_model: str,
    monthly_fixed_cost: float,
    motor_purchase: str = "Hayır",
    motor_purchase_start_date_value: date | None = None,
    motor_purchase_commitment_months: int | None = None,
    motor_purchase_sale_price: float = 0.0,
) -> list[str]:
    errors: list[str] = []
    if not (full_name or "").strip():
        errors.append("Ad Soyad alanı zorunlu.")
    if not (phone or "").strip():
        errors.append("Telefon alanı zorunlu.")
    if not (tc_no or "").strip():
        errors.append("TC Kimlik No alanı zorunlu.")
    if not (iban or "").strip():
        errors.append("IBAN alanı zorunlu.")
    if not (current_plate or "").strip():
        errors.append("Güncel plaka alanı zorunlu.")
    if start_date_value is None:
        errors.append("İşe giriş tarihi zorunlu.")
    if _ROLE_REQUIRES_PRIMARY_RESTAURANT(role) and not assigned_restaurant_id:
        errors.append("Bu rol için ana restoran seçilmesi zorunlu.")
    if str(vehicle_type or "").strip() == "Çat Kapında" and str(motor_purchase or "Hayır") != "Evet":
        if _SAFE_FLOAT(motor_rental_monthly_amount, 0.0) <= 0:
            errors.append("Çat Kapında motor kullanımında aylık motor kira tutarı zorunlu.")
    if str(motor_purchase or "Hayır") == "Evet":
        if motor_purchase_start_date_value is None:
            errors.append("Motor satın alım tarihi zorunlu.")
        if _SAFE_INT(motor_purchase_commitment_months, 0) <= 0:
            errors.append("Motor satış taahhüt süresi zorunlu.")
        if _SAFE_FLOAT(motor_purchase_sale_price, 0.0) <= 0:
            errors.append("Motor satış fiyatı zorunlu.")
    if _IS_FIXED_COST_MODEL(cost_model) and monthly_fixed_cost <= 0:
        errors.append("Sabit maliyetli rollerde aylık sabit maliyet zorunlu.")
    return errors
