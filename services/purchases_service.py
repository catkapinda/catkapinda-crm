from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from repositories.purchases_repository import (
    delete_purchase_record,
    fetch_purchases_management_df,
    insert_purchase_record,
    update_purchase_record,
)


@dataclass
class PurchasesWorkspacePayload:
    purchases: Any


@dataclass
class PurchaseSelectionPayload:
    row: Any
    current_date: Any
    item_index: int


def load_purchases_workspace_payload(conn) -> PurchasesWorkspacePayload:
    return PurchasesWorkspacePayload(purchases=fetch_purchases_management_df(conn))


def build_purchase_selection_payload(
    purchases,
    *,
    selected_id: int,
    item_options: list[str],
) -> PurchaseSelectionPayload:
    row = purchases.loc[purchases["id"] == selected_id].iloc[0]
    current_date = datetime.strptime(str(row["purchase_date"]), "%Y-%m-%d").date()
    current_item = str(row["item_name"] or "")
    item_index = item_options.index(current_item) if current_item in item_options else 0
    return PurchaseSelectionPayload(
        row=row,
        current_date=current_date,
        item_index=item_index,
    )


def create_purchase_and_commit(
    conn,
    *,
    purchase_values: dict[str, Any],
    fmt_try_fn: Callable[[Any], str],
) -> str:
    try:
        insert_purchase_record(conn, purchase_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return f"Satın alma kaydedildi. Birim maliyet: {fmt_try_fn(purchase_values['unit_cost'])}"


def update_purchase_and_commit(
    conn,
    *,
    purchase_id: int,
    purchase_values: dict[str, Any],
    fmt_try_fn: Callable[[Any], str],
) -> str:
    try:
        update_purchase_record(conn, purchase_id, purchase_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return f"Satın alma kaydı güncellendi. Yeni birim maliyet: {fmt_try_fn(purchase_values['unit_cost'])}"


def delete_purchase_and_commit(conn, *, purchase_id: int) -> str:
    try:
        delete_purchase_record(conn, purchase_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return "Satın alma kaydı silindi."
