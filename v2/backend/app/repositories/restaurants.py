from __future__ import annotations

import psycopg

from app.core.database import is_sqlite_backend


def _active_is_true_sql(column: str = "r.active") -> str:
    return f"COALESCE(LOWER(CAST({column} AS TEXT)), 'true') IN ('1', 't', 'true')"


def _active_is_false_sql(column: str = "r.active") -> str:
    return f"NOT ({_active_is_true_sql(column)})"


def _optional_text_equality_sql(column: str) -> str:
    return f"(%s::text IS NULL OR COALESCE(CAST({column} AS TEXT), '') = %s::text)"


def _optional_boolean_filter_sql(column: str) -> str:
    return f"(%s::boolean IS NULL OR {_active_is_true_sql(column)} = %s::boolean)"


def _optional_text_search_guard_sql() -> str:
    return "%s::text IS NULL"


def _active_storage_value(value: bool) -> int:
    return 1 if bool(value) else 0


def _restaurant_select_sql() -> str:
    return f"""
        SELECT
            r.id,
            COALESCE(CAST(r.brand AS TEXT), '') AS brand,
            COALESCE(CAST(r.branch AS TEXT), '') AS branch,
            COALESCE(CAST(r.pricing_model AS TEXT), '') AS pricing_model,
            COALESCE(r.hourly_rate, 0) AS hourly_rate,
            COALESCE(r.package_rate, 0) AS package_rate,
            COALESCE(r.package_threshold, 390) AS package_threshold,
            COALESCE(r.package_rate_low, 0) AS package_rate_low,
            COALESCE(r.package_rate_high, 0) AS package_rate_high,
            COALESCE(r.fixed_monthly_fee, 0) AS fixed_monthly_fee,
            COALESCE(r.vat_rate, 20) AS vat_rate,
            COALESCE(r.target_headcount, 0) AS target_headcount,
            NULLIF(CAST(r.start_date AS TEXT), '') AS start_date,
            NULLIF(CAST(r.end_date AS TEXT), '') AS end_date,
            COALESCE(r.extra_headcount_request, 0) AS extra_headcount_request,
            NULLIF(CAST(r.extra_headcount_request_date AS TEXT), '') AS extra_headcount_request_date,
            COALESCE(r.reduce_headcount_request, 0) AS reduce_headcount_request,
            NULLIF(CAST(r.reduce_headcount_request_date AS TEXT), '') AS reduce_headcount_request_date,
            COALESCE(CAST(r.contact_name AS TEXT), '') AS contact_name,
            COALESCE(CAST(r.contact_phone AS TEXT), '') AS contact_phone,
            COALESCE(CAST(r.contact_email AS TEXT), '') AS contact_email,
            COALESCE(CAST(r.company_title AS TEXT), '') AS company_title,
            COALESCE(CAST(r.address AS TEXT), '') AS address,
            COALESCE(CAST(r.tax_office AS TEXT), '') AS tax_office,
            COALESCE(CAST(r.tax_number AS TEXT), '') AS tax_number,
            {_active_is_true_sql('r.active')} AS active,
            COALESCE(CAST(r.notes AS TEXT), '') AS notes
        FROM restaurants r
    """


def fetch_restaurant_summary(conn: psycopg.Connection) -> dict[str, int]:
    if is_sqlite_backend(conn):
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_restaurants,
                SUM(CASE WHEN COALESCE(active, 1) = 1 THEN 1 ELSE 0 END) AS active_restaurants,
                SUM(CASE WHEN COALESCE(active, 1) = 0 THEN 1 ELSE 0 END) AS passive_restaurants,
                SUM(CASE WHEN pricing_model = 'fixed_monthly' THEN 1 ELSE 0 END) AS fixed_monthly_restaurants
            FROM restaurants
            """
        ).fetchone()
    else:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_restaurants,
                COUNT(*) FILTER (WHERE {_active_is_true_sql('active')}) AS active_restaurants,
                COUNT(*) FILTER (WHERE {_active_is_false_sql('active')}) AS passive_restaurants,
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
        WHERE {_optional_text_equality_sql('r.pricing_model')}
          AND {_optional_boolean_filter_sql('r.active')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(CAST(r.brand AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.branch AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.contact_name AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.contact_phone AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.company_title AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.address AS TEXT), '') ILIKE %s
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
        f"""
        SELECT COUNT(*) AS total_count
        FROM restaurants r
        WHERE {_optional_text_equality_sql('r.pricing_model')}
          AND {_optional_boolean_filter_sql('r.active')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(CAST(r.brand AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.branch AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.contact_name AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.contact_phone AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.company_title AS TEXT), '') ILIKE %s
            OR COALESCE(CAST(r.address AS TEXT), '') ILIKE %s
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
            _active_storage_value(bool(values["active"])),
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
            _active_storage_value(bool(values["active"])),
            values["notes"],
            restaurant_id,
        ),
    )


def update_restaurant_status(conn: psycopg.Connection, restaurant_id: int, *, active: bool) -> None:
    conn.execute(
        "UPDATE restaurants SET active = %s WHERE id = %s",
        (_active_storage_value(active), restaurant_id),
    )


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
