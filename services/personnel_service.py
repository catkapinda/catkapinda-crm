from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Callable, MutableMapping

from repositories.personnel_repository import (
    fetch_active_restaurant_options,
    fetch_person_code_values,
    fetch_personnel_by_code,
    fetch_personnel_by_id,
    fetch_personnel_management_df,
    insert_personnel_record,
    update_personnel_record,
    update_personnel_status,
)
from services.audit_service import record_audit_event
from services.permission_service import require_action_access


@dataclass
class PersonnelWorkspacePayload:
    df: Any
    rest_opts: dict[str, int]
    rest_opts_with_blank: dict[str, int | None]
    passive_count: int
    recently_created_id: int


@dataclass
class PersonnelEditSelectionPayload:
    person_labels: dict[str, int]
    selected_id: int
    row: Any
    row_role_value: str
    row_status_value: str
    row_accounting_value: str
    row_new_company_value: str
    row_vehicle_value: str
    row_motor_purchase_value: str
    row_motor_usage_mode: str
    start_date_value: date | None
    assigned_value: str
    edit_form_signature: tuple[Any, ...]


@dataclass
class PersonnelCreateResult:
    created_person_id: int
    auto_code: str
    success_text: str


@dataclass
class PersonnelUpdateResult:
    updated_person: Any
    success_text: str


@dataclass
class PersonnelToggleResult:
    updated_person: Any
    success_text: str


@dataclass
class PersonnelDeleteResult:
    success_text: str


def role_code_prefix(role: str) -> str:
    mapping = {
        "Kurye": "K",
        "Bölge Müdürü": "BM",
        "Saha Denetmen Şefi": "SDS",
        "Restoran Takım Şefi": "RTS",
        "Joker": "J",
        "Şef": "TŞ",
    }
    return mapping.get(role or "Kurye", "K")


def build_next_person_code(conn, role: str, exclude_id: int | None = None) -> str:
    prefix = role_code_prefix(role)
    max_num = 0
    for code in fetch_person_code_values(conn, prefix, exclude_id=exclude_id):
        match = re.search(rf"^CK-{re.escape(prefix)}(\d+)$", code)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"CK-{prefix}{max_num + 1:02d}"


def build_personnel_code_display_values(
    conn,
    *,
    current_person_code: Any,
    original_role: str,
    effective_role: str,
    exclude_id: int | None = None,
) -> tuple[str, str]:
    suggested_code = build_next_person_code(conn, effective_role, exclude_id=exclude_id)
    if original_role == effective_role and str(current_person_code or "").strip():
        return suggested_code, str(current_person_code or "")

    new_prefix = role_code_prefix(effective_role)
    existing_num = ""
    match = re.search(rf"^CK-{re.escape(new_prefix)}(\d+)$", str(current_person_code or ""))
    if match:
        existing_num = match.group(1)
    suffix = existing_num or suggested_code.split(new_prefix, 1)[1]
    return suggested_code, f"CK-{new_prefix}{suffix}"


def build_new_person_form_defaults(
    *,
    default_role: str,
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
) -> dict[str, Any]:
    return {
        "new_person_full_name": "",
        "new_person_role": default_role,
        "new_person_phone": "",
        "new_person_assigned_label": "-",
        "new_person_tc_no": "",
        "new_person_iban": "",
        "new_person_address": "",
        "new_person_emergency_contact_name": "",
        "new_person_emergency_contact_phone": "",
        "new_person_accounting_type": "Kendi Muhasebecisi",
        "new_person_new_company_setup": "Hayır",
        "new_person_start_date": date.today(),
        "new_person_vehicle_type": "Çat Kapında",
        "new_person_motor_usage_mode": "Çat Kapında Motor Kirası",
        "new_person_motor_rental_monthly_amount": auto_motor_rental_deduction,
        "new_person_motor_purchase": "Hayır",
        "new_person_motor_purchase_start_date": date.today(),
        "new_person_motor_purchase_commitment_months": 12,
        "new_person_motor_purchase_sale_price": auto_motor_purchase_monthly_deduction,
        "new_person_accounting_revenue": 0.0,
        "new_person_accountant_cost": 0.0,
        "new_person_company_setup_revenue": 0.0,
        "new_person_company_setup_cost": 0.0,
        "new_person_monthly_fixed_cost": 0.0,
        "new_person_current_plate": "",
        "new_person_notes": "",
        "new_person_onboarding_items": [],
    }


def prepare_new_person_form_state(
    session_state: MutableMapping[str, Any],
    *,
    defaults: dict[str, Any],
    clear_new_person_onboarding_state_fn: Callable[[], None],
) -> None:
    if session_state.pop("personnel_form_reset_pending", False):
        clear_new_person_onboarding_state_fn()
        for key, value in defaults.items():
            session_state[key] = value
    for key, value in defaults.items():
        if key not in session_state:
            session_state[key] = value
    if session_state.get("new_person_accounting_type") not in ["Çat Kapında Muhasebe", "Kendi Muhasebecisi"]:
        session_state["new_person_accounting_type"] = "Kendi Muhasebecisi"


def build_personnel_edit_selection_payload(
    df,
    *,
    selected_label: str,
    personnel_role_options: list[str],
    motor_usage_mode_options: list[str],
    rest_opts: dict[str, Any],
    parse_date_value_fn: Callable[[Any], date | None],
    resolve_vehicle_type_value_fn: Callable[[str, str], str],
    resolve_motor_usage_mode_fn: Callable[[str, str, str], str],
) -> PersonnelEditSelectionPayload:
    person_labels = {
        f"{row['full_name']} | {row['role']} | Kod: {row['person_code'] or '-'} | ID: {row['id']}": int(row["id"])
        for _, row in df.iterrows()
    }
    selected_id = person_labels[selected_label]
    row = df.loc[df["id"] == selected_id].iloc[0]
    row_role_value = str(row["role"] or "Kurye")
    row_status_value = str(row["status"] or "Aktif")
    row_accounting_value = str(row["accounting_type"] or "Kendi Muhasebecisi")
    row_new_company_value = str(row["new_company_setup"] or "Hayır")
    row_vehicle_value = resolve_vehicle_type_value_fn(row["vehicle_type"] or "", row["motor_rental"] or "Hayır")
    row_motor_purchase_raw = row.get("motor_purchase", "Hayır")
    row_motor_purchase_value = str(row_motor_purchase_raw or "Hayır")
    if row_motor_purchase_value.strip().lower() in {"", "nan", "none"}:
        row_motor_purchase_value = "Hayır"
    row_motor_usage_mode = resolve_motor_usage_mode_fn(row_vehicle_value, row_motor_purchase_value, row["motor_rental"] or "Hayır")
    start_date_value = parse_date_value_fn(row["start_date"])
    assigned_raw = row.get("restoran", "-")
    assigned_value = assigned_raw if isinstance(assigned_raw, str) and assigned_raw in rest_opts else "-"
    edit_form_signature = (
        selected_id,
        row_role_value,
        row_status_value,
        row_accounting_value,
        row_new_company_value,
        row_motor_usage_mode,
    )
    return PersonnelEditSelectionPayload(
        person_labels=person_labels,
        selected_id=selected_id,
        row=row,
        row_role_value=row_role_value if row_role_value in personnel_role_options else "Kurye",
        row_status_value=row_status_value if row_status_value in ["Aktif", "Pasif"] else "Aktif",
        row_accounting_value=row_accounting_value if row_accounting_value in ["Çat Kapında Muhasebe", "Kendi Muhasebecisi"] else "Kendi Muhasebecisi",
        row_new_company_value=row_new_company_value if row_new_company_value in ["Hayır", "Evet"] else "Hayır",
        row_vehicle_value=row_vehicle_value,
        row_motor_purchase_value=row_motor_purchase_value,
        row_motor_usage_mode=row_motor_usage_mode if row_motor_usage_mode in motor_usage_mode_options else "Kendi Motoru",
        start_date_value=start_date_value,
        assigned_value=assigned_value,
        edit_form_signature=edit_form_signature,
    )


def load_personnel_workspace_payload(
    conn,
    *,
    recently_created_payload: Any,
    ensure_dataframe_columns_fn: Callable[[Any, dict[str, Any]], Any],
    safe_int_fn: Callable[[Any, int], int],
    get_row_value_fn: Callable[[Any, str, Any], Any],
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
    auto_motor_purchase_installment_count: int,
) -> PersonnelWorkspacePayload:
    df = fetch_personnel_management_df(conn)
    df = ensure_dataframe_columns_fn(
        df,
        {
            "emergency_contact_name": "",
            "emergency_contact_phone": "",
            "motor_rental_monthly_amount": auto_motor_rental_deduction,
            "motor_purchase": "Hayır",
            "motor_purchase_start_date": "",
            "motor_purchase_commitment_months": None,
            "motor_purchase_sale_price": 0.0,
            "motor_purchase_monthly_amount": auto_motor_purchase_monthly_deduction,
            "motor_purchase_installment_count": auto_motor_purchase_installment_count,
        },
    )
    rest_opts = fetch_active_restaurant_options(conn)
    rest_opts_with_blank = {"-": None, **rest_opts}
    passive_count = int((df["status"] == "Pasif").sum()) if not df.empty else 0
    recently_created_id = safe_int_fn(get_row_value_fn(recently_created_payload, "personnel_id"), 0) if recently_created_payload else 0
    return PersonnelWorkspacePayload(
        df=df,
        rest_opts=rest_opts,
        rest_opts_with_blank=rest_opts_with_blank,
        passive_count=passive_count,
        recently_created_id=recently_created_id,
    )


def create_person_with_onboarding(
    conn,
    *,
    role: str,
    person_values: dict[str, Any],
    onboarding_issue_payloads: list[dict[str, Any]],
    safe_int_fn: Callable[[Any, int], int],
    safe_float_fn: Callable[[Any, float], float],
    insert_equipment_issue_and_get_id_fn: Callable[..., int],
    post_equipment_installments_fn: Callable[..., None],
    sync_person_current_role_snapshot_fn: Callable[[Any, Any], None],
    sync_person_business_rules_fn: Callable[[Any, Any], None],
    actor_role: str = "admin",
) -> PersonnelCreateResult:
    require_action_access(actor_role, "personnel.create")
    auto_code = build_next_person_code(conn, role)
    values = {**person_values, "person_code": auto_code, "status": "Aktif"}
    created_person_id = 0
    try:
        insert_personnel_record(conn, values)
        created_person = fetch_personnel_by_code(conn, auto_code)
        if not created_person:
            raise RuntimeError("Personel kaydı oluşturuldu ancak kayıt tekrar okunamadı.")
        created_person_id = safe_int_fn(created_person["id"], 0)
        for payload in onboarding_issue_payloads:
            issue_date_value = payload["issue_date"]
            quantity_value = safe_int_fn(payload["quantity"], 1)
            sale_price_value = safe_float_fn(payload["unit_sale_price"], 0.0)
            installment_count_value = safe_int_fn(payload["installment_count"], 1)
            vat_rate_value = safe_float_fn(payload["vat_rate"], 10.0)
            issue_id = insert_equipment_issue_and_get_id_fn(
                conn,
                created_person_id,
                issue_date_value.isoformat(),
                str(payload["item_name"] or ""),
                quantity_value,
                safe_float_fn(payload["unit_cost"], 0.0),
                sale_price_value,
                installment_count_value,
                "Satış",
                str(payload.get("notes", "") or ""),
                vat_rate=vat_rate_value,
            )
            post_equipment_installments_fn(
                conn,
                issue_id,
                created_person_id,
                issue_date_value,
                str(payload["item_name"] or ""),
                float(quantity_value) * float(sale_price_value),
                installment_count_value,
                "Satış",
            )
        sync_person_current_role_snapshot_fn(conn, created_person)
        sync_person_business_rules_fn(conn, created_person)
        equipment_summary = (
            f" | {len(onboarding_issue_payloads)} onboarding ekipmanı kaydedildi"
            if onboarding_issue_payloads
            else ""
        )
        success_text = f"{values['full_name']} başarıyla eklendi. Kod: {auto_code}{equipment_summary}"
        record_audit_event(
            conn,
            entity_type="personnel",
            entity_id=created_person_id,
            action_type="create",
            summary=success_text,
            details={
                "full_name": values.get("full_name"),
                "role": values.get("role"),
                "assigned_restaurant_id": values.get("assigned_restaurant_id"),
                "onboarding_item_count": len(onboarding_issue_payloads),
            },
            commit=False,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return PersonnelCreateResult(
        created_person_id=created_person_id,
        auto_code=auto_code,
        success_text=success_text,
    )


def update_person_and_sync(
    conn,
    *,
    person_id: int,
    original_row: Any,
    person_values: dict[str, Any],
    role_changed: bool,
    transition_enabled: bool,
    transition_previous_role: str,
    transition_effective_date: date | None,
    is_fixed_cost_model_fn: Callable[[str], bool],
    safe_float_fn: Callable[[Any, float], float],
    safe_int_fn: Callable[[Any, int], int],
    normalize_cost_model_value_fn: Callable[[str, str], str],
    record_person_role_transition_fn: Callable[..., None],
    sync_person_current_role_snapshot_fn: Callable[[Any, Any], None],
    motor_mode_changed: bool,
    current_vehicle: str,
    current_motor_purchase: str,
    edit_vehicle_transition_date: date,
    auto_motor_rental_deduction: float,
    auto_motor_purchase_monthly_deduction: float,
    record_person_vehicle_transition_fn: Callable[..., None],
    sync_person_current_vehicle_snapshot_fn: Callable[[Any, Any], None],
    sync_person_business_rules_fn: Callable[[Any, Any], None],
    actor_role: str = "admin",
) -> PersonnelUpdateResult:
    require_action_access(actor_role, "personnel.update")
    try:
        update_personnel_record(conn, person_id, person_values)
        updated_person = fetch_personnel_by_id(conn, person_id)
        if role_changed and transition_enabled:
            previous_fixed_cost = 0.0
            previous_cost_model = normalize_cost_model_value_fn("", transition_previous_role)
            if is_fixed_cost_model_fn(previous_cost_model) and transition_previous_role == str(original_row["role"] or ""):
                previous_fixed_cost = safe_float_fn(original_row["monthly_fixed_cost"], 0.0)
            record_person_role_transition_fn(
                conn,
                original_row.to_dict(),
                updated_person,
                transition_previous_role,
                transition_effective_date,
                previous_monthly_fixed_cost=previous_fixed_cost,
            )
        else:
            sync_person_current_role_snapshot_fn(conn, updated_person)
        if motor_mode_changed:
            record_person_vehicle_transition_fn(
                conn,
                original_row.to_dict(),
                updated_person,
                current_vehicle,
                edit_vehicle_transition_date,
                previous_motor_rental=str(original_row["motor_rental"] or "Hayır"),
                previous_motor_rental_monthly_amount=safe_float_fn(original_row.get("motor_rental_monthly_amount", auto_motor_rental_deduction), auto_motor_rental_deduction),
                previous_motor_purchase=current_motor_purchase,
                previous_motor_purchase_commitment_months=safe_int_fn(original_row.get("motor_purchase_commitment_months", 0), 0),
                previous_motor_purchase_sale_price=safe_float_fn(original_row.get("motor_purchase_sale_price", 0.0), 0.0),
                previous_motor_purchase_monthly_amount=safe_float_fn(original_row.get("motor_purchase_monthly_amount", auto_motor_purchase_monthly_deduction), auto_motor_purchase_monthly_deduction),
            )
        else:
            sync_person_current_vehicle_snapshot_fn(conn, updated_person)
        sync_person_business_rules_fn(conn, updated_person, create_onboarding=False)
        success_text = "Personel kartı başarıyla güncellendi."
        record_audit_event(
            conn,
            entity_type="personnel",
            entity_id=person_id,
            action_type="update",
            summary=success_text,
            details={
                "full_name": person_values.get("full_name"),
                "role": person_values.get("role"),
                "status": person_values.get("status"),
                "role_changed": role_changed,
                "motor_mode_changed": motor_mode_changed,
            },
            commit=False,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return PersonnelUpdateResult(updated_person=updated_person, success_text=success_text)


def toggle_person_status_and_sync(
    conn,
    *,
    person_id: int,
    current_status: str,
    sync_person_business_rules_fn: Callable[[Any, Any], None],
    actor_role: str = "admin",
) -> PersonnelToggleResult:
    require_action_access(actor_role, "personnel.status_change")
    new_status = "Pasif" if current_status == "Aktif" else "Aktif"
    exit_date = date.today().isoformat() if new_status == "Pasif" else None
    try:
        update_personnel_status(conn, person_id, new_status, exit_date)
        updated_person = fetch_personnel_by_id(conn, person_id)
        sync_person_business_rules_fn(conn, updated_person, create_onboarding=False)
        success_text = "Personel başarıyla pasife alındı." if new_status == "Pasif" else "Personel başarıyla aktifleştirildi."
        record_audit_event(
            conn,
            entity_type="personnel",
            entity_id=person_id,
            action_type="status_change",
            summary=success_text,
            details={"new_status": new_status, "exit_date": exit_date},
            commit=False,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return PersonnelToggleResult(
        updated_person=updated_person,
        success_text=success_text,
    )


def delete_person_with_dependencies(
    conn,
    *,
    person_id: int,
    get_personnel_dependency_counts_fn: Callable[[Any, int], dict[str, int]],
    delete_personnel_and_dependencies_fn: Callable[[Any, int], None],
    actor_role: str = "admin",
) -> PersonnelDeleteResult:
    require_action_access(actor_role, "personnel.delete")
    dependency_counts = get_personnel_dependency_counts_fn(conn, person_id)
    delete_personnel_and_dependencies_fn(conn, person_id)
    detail_parts = [
        f"{label}: {count}"
        for label, count in [
            ("Puantaj", dependency_counts.get("puantaj", 0)),
            ("Kesinti", dependency_counts.get("kesinti", 0)),
            ("Rol geçmişi", dependency_counts.get("rol_gecmisi", 0)),
            ("Araç geçmişi", dependency_counts.get("arac_gecmisi", 0)),
            ("Plaka geçmişi", dependency_counts.get("plaka", 0)),
            ("Zimmet", dependency_counts.get("zimmet", 0)),
            ("Box iade", dependency_counts.get("box_iade", 0)),
        ]
        if count
    ]
    if detail_parts:
        success_text = "Personel ve bağlı kayıtlar kalıcı olarak silindi. " + " | ".join(detail_parts)
        record_audit_event(
            conn,
            entity_type="personnel",
            entity_id=person_id,
            action_type="delete",
            summary=success_text,
            details=dependency_counts,
        )
        return PersonnelDeleteResult(success_text=success_text)
    success_text = "Personel kaydı kalıcı olarak silindi."
    record_audit_event(
        conn,
        entity_type="personnel",
        entity_id=person_id,
        action_type="delete",
        summary=success_text,
        details=dependency_counts,
    )
    return PersonnelDeleteResult(success_text=success_text)
