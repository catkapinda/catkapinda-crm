from __future__ import annotations

import psycopg


def _restaurant_select_sql() -> str:
    return """
        SELECT
            r.id,
            COALESCE(r.brand, '') AS brand,
            COALESCE(r.branch, '') AS branch,
            COALESCE(r.pricing_model, '') AS pricing_model,
            COALESCE(r.hourly_rate, 0) AS hourly_rate,
            COALESCE(r.package_rate, 0) AS package_rate,
            COALESCE(r.package_threshold, 390) AS package_threshold,
            COALESCE(r.package_rate_low, 0) AS package_rate_low,
            COALESCE(r.package_rate_high, 0) AS package_rate_high,
            COALESCE(r.fixed_monthly_fee, 0) AS fixed_monthly_fee,
            COALESCE(r.vat_rate, 20) AS vat_rate,
            COALESCE(r.target_headcount, 0) AS target_headcount,
            r.start_date,
            r.end_date,
            COALESCE(r.extra_headcount_request, 0) AS extra_headcount_request,
            r.extra_headcount_request_date,
            COALESCE(r.reduce_headcount_request, 0) AS reduce_headcount_request,
            r.reduce_headcount_request_date,
            COALESCE(r.contact_name, '') AS contact_name,
            COALESCE(r.contact_phone, '') AS contact_phone,
            COALESCE(r.contact_email, '') AS contact_email,
            COALESCE(r.company_title, '') AS company_title,
            COALESCE(r.address, '') AS address,
            COALESCE(r.tax_office, '') AS tax_office,
            COALESCE(r.tax_number, '') AS tax_number,
            COALESCE(r.active, TRUE) AS active,
            COALESCE(r.notes, '') AS notes
        FROM restaurants r
    """


def fetch_restaurant_summary(conn: psycopg.Connection) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_restaurants,
            COUNT(*) FILTER (WHERE COALESCE(active, TRUE) = TRUE) AS active_restaurants,
            COUNT(*) FILTER (WHERE COALESCE(active, TRUE) = FALSE) AS passive_restaurants,
            COUNT(*) FILTER (WHERE pricing_model = 'fixed_monthly') AS fixed_monthly_restaurants
        FROM restaurants
        """
    ).fetchone()
    if row is None:
        return {
            "total_restaurants": 0,
            "active_restaurants": 0,
            "passive_restaurants": 0,
            "fixed_monthly_restaurants": 0,
        }
    return {
        "total_restaurants": int(row["total_restaurants"] or 0),
        "active_restaurants": int(row["active_restaurants"] or 0),
        "passive_restaurants": int(row["passive_restaurants"] or 0),
        "fixed_monthly_restaurants": int(row["fixed_monthly_restaurants"] or 0),
    }


def fetch_recent_restaurant_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        f"""
        {_restaurant_select_sql()}
        ORDER BY r.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_restaurant_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    pricing_model: str | None = None,
    active: bool | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        f"""
        {_restaurant_select_sql()}
        WHERE (%s IS NULL OR r.pricing_model = %s)
          AND (%s IS NULL OR COALESCE(r.active, TRUE) = %s)
          AND (
            %s IS NULL
            OR COALESCE(r.brand, '') ILIKE %s
            OR COALESCE(r.branch, '') ILIKE %s
            OR COALESCE(r.contact_name, '') ILIKE %s
            OR COALESCE(r.contact_phone, '') ILIKE %s
            OR COALESCE(r.company_title, '') ILIKE %s
            OR COALESCE(r.address, '') ILIKE %s
          )
        ORDER BY r.brand, r.branch, r.id DESC
        LIMIT %s
        """,
        (
            pricing_model,
            pricing_model,
            active,
            active,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_restaurant_management_records(
    conn: psycopg.Connection,
    *,
    pricing_model: str | None = None,
    active: bool | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM restaurants r
        WHERE (%s IS NULL OR r.pricing_model = %s)
          AND (%s IS NULL OR COALESCE(r.active, TRUE) = %s)
          AND (
            %s IS NULL
            OR COALESCE(r.brand, '') ILIKE %s
            OR COALESCE(r.branch, '') ILIKE %s
            OR COALESCE(r.contact_name, '') ILIKE %s
            OR COALESCE(r.contact_phone, '') ILIKE %s
            OR COALESCE(r.company_title, '') ILIKE %s
            OR COALESCE(r.address, '') ILIKE %s
          )
        """,
        (
            pricing_model,
            pricing_model,
            active,
            active,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_restaurant_record_by_id(
    conn: psycopg.Connection,
    restaurant_id: int,
) -> dict | None:
    row = conn.execute(
        f"""
        {_restaurant_select_sql()}
        WHERE r.id = %s
        """,
        (restaurant_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_restaurant_record(conn: psycopg.Connection, values: dict) -> int:
    row = conn.execute(
        """
        INSERT INTO restaurants (
            brand,
            branch,
            billing_group,
            pricing_model,
            hourly_rate,
            package_rate,
            package_threshold,
            package_rate_low,
            package_rate_high,
            fixed_monthly_fee,
            vat_rate,
            target_headcount,
            start_date,
            end_date,
            extra_headcount_request,
            extra_headcount_request_date,
            reduce_headcount_request,
            reduce_headcount_request_date,
            contact_name,
            contact_phone,
            contact_email,
            company_title,
            address,
            tax_office,
            tax_number,
            active,
            notes
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            values["brand"],
            values["branch"],
            None,
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
            values["active"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def update_restaurant_record(
    conn: psycopg.Connection,
    restaurant_id: int,
    values: dict,
) -> None:
    conn.execute(
        """
        UPDATE restaurants
        SET
            brand = %s,
            branch = %s,
            pricing_model = %s,
            hourly_rate = %s,
            package_rate = %s,
            package_threshold = %s,
            package_rate_low = %s,
            package_rate_high = %s,
            fixed_monthly_fee = %s,
            vat_rate = %s,
            target_headcount = %s,
            start_date = %s,
            end_date = %s,
            extra_headcount_request = %s,
            extra_headcount_request_date = %s,
            reduce_headcount_request = %s,
            reduce_headcount_request_date = %s,
            contact_name = %s,
            contact_phone = %s,
            contact_email = %s,
            company_title = %s,
            address = %s,
            tax_office = %s,
            tax_number = %s,
            active = %s,
            notes = %s
        WHERE id = %s
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
            values["active"],
            values["notes"],
            restaurant_id,
        ),
    )


def update_restaurant_status(conn: psycopg.Connection, restaurant_id: int, *, active: bool) -> None:
    conn.execute("UPDATE restaurants SET active = %s WHERE id = %s", (active, restaurant_id))


def delete_restaurant_record(conn: psycopg.Connection, restaurant_id: int) -> None:
    conn.execute("DELETE FROM restaurants WHERE id = %s", (restaurant_id,))


def count_restaurant_linked_personnel(conn: psycopg.Connection, restaurant_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM personnel WHERE assigned_restaurant_id = %s",
        (restaurant_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_restaurant_linked_daily_entries(conn: psycopg.Connection, restaurant_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM daily_entries WHERE restaurant_id = %s",
        (restaurant_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_restaurant_linked_deductions(conn: psycopg.Connection, restaurant_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        WHERE p.assigned_restaurant_id = %s
        """,
        (restaurant_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0
