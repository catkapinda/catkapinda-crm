from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repositories.personnel_repository import (
    fetch_active_restaurant_options,
    fetch_personnel_management_df,
)


@dataclass
class PersonnelWorkspacePayload:
    df: Any
    rest_opts: dict[str, int]
    rest_opts_with_blank: dict[str, int | None]
    passive_count: int
    recently_created_id: int


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
