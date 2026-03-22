from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, fetch_df


def fetch_restaurant_management_df(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM restaurants ORDER BY brand, branch")


def insert_restaurant_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO restaurants (
            brand, branch, billing_group, pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee,
            vat_rate, target_headcount, start_date, end_date,
            extra_headcount_request, extra_headcount_request_date,
            reduce_headcount_request, reduce_headcount_request_date,
            contact_name, contact_phone, contact_email, company_title, address, tax_office, tax_number,
            active, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            values["brand"],
            values["branch"],
            values["billing_group"],
            values["pricing_model"],
            values["hourly_rate"],
            values["package_rate"],
            values["package_threshold"],
            values["package_rate_low"],
            values["package_rate_high"],
            values["fixed_monthly_fee"],
            values["vat_rate"],
            values["target_headcount"],
            values["start_date"],
            values["end_date"],
            values["extra_headcount_request"],
            values["extra_headcount_request_date"],
            values["reduce_headcount_request"],
            values["reduce_headcount_request_date"],
            values["contact_name"],
            values["contact_phone"],
            values["contact_email"],
            values["company_title"],
            values["address"],
            values["tax_office"],
            values["tax_number"],
            values["notes"],
        ),
    )


def update_restaurant_record(conn: CompatConnection, restaurant_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE restaurants
        SET brand=?, branch=?, pricing_model=?, hourly_rate=?, package_rate=?,
            package_threshold=?, package_rate_low=?, package_rate_high=?, fixed_monthly_fee=?,
            vat_rate=?, target_headcount=?, start_date=?, end_date=?,
            extra_headcount_request=?, extra_headcount_request_date=?,
            reduce_headcount_request=?, reduce_headcount_request_date=?,
            contact_name=?, contact_phone=?, contact_email=?, company_title=?, address=?, tax_office=?, tax_number=?, notes=?
        WHERE id=?
        """,
        (
            values["brand"],
            values["branch"],
            values["pricing_model"],
            values["hourly_rate"],
            values["package_rate"],
            values["package_threshold"],
            values["package_rate_low"],
            values["package_rate_high"],
            values["fixed_monthly_fee"],
            values["vat_rate"],
            values["target_headcount"],
            values["start_date"],
            values["end_date"],
            values["extra_headcount_request"],
            values["extra_headcount_request_date"],
            values["reduce_headcount_request"],
            values["reduce_headcount_request_date"],
            values["contact_name"],
            values["contact_phone"],
            values["contact_email"],
            values["company_title"],
            values["address"],
            values["tax_office"],
            values["tax_number"],
            values["notes"],
            restaurant_id,
        ),
    )


def update_restaurant_status(conn: CompatConnection, restaurant_id: int, active_value: int) -> None:
    conn.execute("UPDATE restaurants SET active = ? WHERE id = ?", (active_value, restaurant_id))


def delete_restaurant_record(conn: CompatConnection, restaurant_id: int) -> None:
    conn.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_id,))


def count_restaurant_linked_personnel(conn: CompatConnection, restaurant_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM personnel WHERE assigned_restaurant_id = ?", (restaurant_id,)).fetchone()
    return int(row[0] if row else 0)


def count_restaurant_linked_daily_entries(conn: CompatConnection, restaurant_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM daily_entries WHERE restaurant_id = ?", (restaurant_id,)).fetchone()
    return int(row[0] if row else 0)


def count_restaurant_linked_deductions(conn: CompatConnection, restaurant_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        WHERE p.assigned_restaurant_id = ?
        """,
        (restaurant_id,),
    ).fetchone()
    return int(row[0] if row else 0)
