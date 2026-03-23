from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, cache_db_read, fetch_df


@cache_db_read(ttl=30)
def fetch_sales_leads_df(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM sales_leads ORDER BY updated_at DESC, id DESC")


def insert_sales_lead_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO sales_leads (
            restaurant_name,
            city,
            district,
            address,
            contact_name,
            contact_phone,
            contact_email,
            requested_courier_count,
            lead_source,
            proposed_quote,
            pricing_model_hint,
            status,
            next_follow_up_date,
            assigned_owner,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["restaurant_name"],
            values["city"],
            values["district"],
            values["address"],
            values["contact_name"],
            values["contact_phone"],
            values["contact_email"],
            values["requested_courier_count"],
            values["lead_source"],
            values["proposed_quote"],
            values["pricing_model_hint"],
            values["status"],
            values["next_follow_up_date"],
            values["assigned_owner"],
            values["notes"],
            values["created_at"],
            values["updated_at"],
        ),
    )


def update_sales_lead_record(conn: CompatConnection, lead_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE sales_leads
        SET restaurant_name = ?,
            city = ?,
            district = ?,
            address = ?,
            contact_name = ?,
            contact_phone = ?,
            contact_email = ?,
            requested_courier_count = ?,
            lead_source = ?,
            proposed_quote = ?,
            pricing_model_hint = ?,
            status = ?,
            next_follow_up_date = ?,
            assigned_owner = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            values["restaurant_name"],
            values["city"],
            values["district"],
            values["address"],
            values["contact_name"],
            values["contact_phone"],
            values["contact_email"],
            values["requested_courier_count"],
            values["lead_source"],
            values["proposed_quote"],
            values["pricing_model_hint"],
            values["status"],
            values["next_follow_up_date"],
            values["assigned_owner"],
            values["notes"],
            values["updated_at"],
            lead_id,
        ),
    )


def delete_sales_lead_record(conn: CompatConnection, lead_id: int) -> None:
    conn.execute("DELETE FROM sales_leads WHERE id = ?", (lead_id,))
