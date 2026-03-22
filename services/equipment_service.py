from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repositories.equipment_repository import (
    fetch_box_return_management_df,
    fetch_equipment_installment_df,
    fetch_equipment_issue_management_df,
    fetch_equipment_purchase_summary_df,
    fetch_equipment_sales_profit_df,
    insert_box_return_record,
)
from repositories.personnel_repository import fetch_person_options_map


@dataclass
class EquipmentWorkspacePayload:
    person_opts: dict[str, int]
    issues: Any
    installment_df: Any
    returns_df: Any
    sales_profit: Any
    stock_purchase: Any


def load_equipment_workspace_payload(conn) -> EquipmentWorkspacePayload:
    return EquipmentWorkspacePayload(
        person_opts=fetch_person_options_map(conn, active_only=False),
        issues=fetch_equipment_issue_management_df(conn),
        installment_df=fetch_equipment_installment_df(conn),
        returns_df=fetch_box_return_management_df(conn),
        sales_profit=fetch_equipment_sales_profit_df(conn),
        stock_purchase=fetch_equipment_purchase_summary_df(conn),
    )


def create_equipment_issue_and_commit(
    conn,
    *,
    issue_values: dict[str, Any],
    insert_equipment_issue_and_get_id_fn: Callable[..., int],
    post_equipment_installments_fn: Callable[..., None],
    fmt_try_fn: Callable[[Any], str],
) -> str:
    try:
        issue_id = insert_equipment_issue_and_get_id_fn(
            conn,
            issue_values["personnel_id"],
            issue_values["issue_date"].isoformat(),
            issue_values["item_name"],
            issue_values["quantity"],
            issue_values["unit_cost"],
            issue_values["unit_sale_price"],
            issue_values["installment_count"],
            issue_values["sale_type"],
            issue_values["notes"],
            vat_rate=issue_values["vat_rate"],
        )
        post_equipment_installments_fn(
            conn,
            issue_id,
            issue_values["personnel_id"],
            issue_values["issue_date"],
            issue_values["item_name"],
            issue_values["total_sale_amount"],
            issue_values["installment_count"],
            issue_values["sale_type"],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    if issue_values["generates_installments"]:
        return (
            f"Zimmet kaydedildi. Toplam satış: {fmt_try_fn(issue_values['total_sale_amount'])} | "
            f"{issue_values['installment_count']} taksit oluşturuldu."
        )
    return f"Zimmet kaydedildi. Toplam işlem tutarı: {fmt_try_fn(issue_values['total_sale_amount'])}"


def bulk_update_equipment_issues_and_commit(
    conn,
    *,
    issue_ids: list[int],
    bulk_update_equipment_issue_records_fn: Callable[..., int],
    update_values: dict[str, Any],
) -> str:
    try:
        updated_count = bulk_update_equipment_issue_records_fn(
            conn,
            issue_ids,
            issue_date_value=update_values["issue_date_value"],
            unit_cost_value=update_values["unit_cost_value"],
            unit_sale_price_value=update_values["unit_sale_price_value"],
            vat_rate_value=update_values["vat_rate_value"],
            installment_count_value=update_values["installment_count_value"],
            sale_type_value=update_values["sale_type_value"],
            note_append_text=update_values["note_append_text"],
        )
    except Exception:
        conn.rollback()
        raise
    return f"{updated_count} zimmet kaydı toplu olarak güncellendi."


def delete_equipment_issues_and_commit(
    conn,
    *,
    issue_ids: list[int],
    delete_equipment_issue_records_fn: Callable[[Any, list[int]], int],
) -> str:
    try:
        deleted_count = delete_equipment_issue_records_fn(conn, issue_ids)
    except Exception:
        conn.rollback()
        raise
    return f"{deleted_count} zimmet kaydı ve bağlı taksitleri silindi."


def create_box_return_and_commit(conn, *, box_return_values: dict[str, Any]) -> str:
    try:
        insert_box_return_record(conn, box_return_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return "Box geri alım kaydı oluşturuldu."
