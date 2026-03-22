from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, fetch_df


def fetch_purchases_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT id, purchase_date, item_name, quantity, total_invoice_amount, unit_cost, supplier, invoice_no, notes
        FROM inventory_purchases
        ORDER BY purchase_date DESC, id DESC
        """,
    )


def insert_purchase_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO inventory_purchases
        (purchase_date, item_name, quantity, total_invoice_amount, unit_cost, supplier, invoice_no, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["purchase_date"],
            values["item_name"],
            values["quantity"],
            values["total_invoice_amount"],
            values["unit_cost"],
            values["supplier"],
            values["invoice_no"],
            values["notes"],
        ),
    )


def update_purchase_record(conn: CompatConnection, purchase_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE inventory_purchases
        SET purchase_date = ?, item_name = ?, quantity = ?, total_invoice_amount = ?, unit_cost = ?, supplier = ?, invoice_no = ?, notes = ?
        WHERE id = ?
        """,
        (
            values["purchase_date"],
            values["item_name"],
            values["quantity"],
            values["total_invoice_amount"],
            values["unit_cost"],
            values["supplier"],
            values["invoice_no"],
            values["notes"],
            purchase_id,
        ),
    )


def delete_purchase_record(conn: CompatConnection, purchase_id: int) -> None:
    conn.execute("DELETE FROM inventory_purchases WHERE id = ?", (purchase_id,))
