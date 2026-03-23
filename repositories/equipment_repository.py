from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, cache_db_read, fetch_df


@cache_db_read(ttl=30)
def fetch_equipment_issue_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT i.id, i.issue_date, p.full_name, i.item_name, i.quantity, i.unit_cost, i.unit_sale_price, i.vat_rate, i.auto_source_key,
               (i.quantity * i.unit_cost) AS total_cost,
               (i.quantity * i.unit_sale_price) AS total_sale,
               ((i.quantity * i.unit_sale_price) - (i.quantity * i.unit_cost)) AS gross_profit,
               i.installment_count, i.sale_type, i.notes
        FROM courier_equipment_issues i
        JOIN personnel p ON p.id = i.personnel_id
        ORDER BY i.issue_date DESC, i.id DESC
        """,
    )


@cache_db_read(ttl=30)
def fetch_equipment_installment_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT d.deduction_date, p.full_name, d.deduction_type, d.amount, d.notes, d.auto_source_key
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        WHERE d.equipment_issue_id IS NOT NULL
        ORDER BY d.deduction_date DESC, d.id DESC
        """,
    )


def insert_box_return_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO box_returns (personnel_id, return_date, quantity, condition_status, payout_amount, waived, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["personnel_id"],
            values["return_date"],
            values["quantity"],
            values["condition_status"],
            values["payout_amount"],
            values["waived"],
            values["notes"],
        ),
    )


@cache_db_read(ttl=30)
def fetch_box_return_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT b.return_date, p.full_name, b.quantity, b.condition_status, b.payout_amount, b.waived, b.notes
        FROM box_returns b
        JOIN personnel p ON p.id = b.personnel_id
        ORDER BY b.return_date DESC, b.id DESC
        """,
    )


@cache_db_read(ttl=30)
def fetch_equipment_sales_profit_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT item_name,
               SUM(quantity) AS sold_qty,
               SUM(quantity * unit_cost) AS total_cost,
               SUM(quantity * unit_sale_price) AS total_sale,
               SUM((quantity * unit_sale_price) - (quantity * unit_cost)) AS gross_profit
        FROM courier_equipment_issues
        WHERE sale_type = 'Satış'
        GROUP BY item_name
        ORDER BY total_sale DESC
        """,
    )


@cache_db_read(ttl=30)
def fetch_equipment_purchase_summary_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT item_name,
               SUM(quantity) AS purchased_qty,
               SUM(total_invoice_amount) AS purchased_total,
               CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount)/SUM(quantity) ELSE 0 END AS weighted_unit_cost
        FROM inventory_purchases
        GROUP BY item_name
        ORDER BY item_name
        """,
    )
