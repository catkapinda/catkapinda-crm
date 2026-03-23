from __future__ import annotations

from infrastructure.db_engine import CompatConnection, cache_db_read, fetch_df


@cache_db_read(ttl=60)
def fetch_reporting_entries(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT d.*, r.brand, r.branch, r.pricing_model, r.hourly_rate, r.package_rate,
               r.package_threshold, r.package_rate_low, r.package_rate_high,
               r.fixed_monthly_fee, r.vat_rate
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        """,
    )


@cache_db_read(ttl=60)
def fetch_reporting_restaurants(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM restaurants ORDER BY brand, branch")


@cache_db_read(ttl=60)
def fetch_reporting_personnel(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM personnel")


@cache_db_read(ttl=60)
def fetch_reporting_role_history(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM personnel_role_history ORDER BY personnel_id, effective_date, id")


@cache_db_read(ttl=60)
def fetch_reporting_all_deductions(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM deductions")


@cache_db_read(ttl=60)
def fetch_reporting_deductions_for_period(conn: CompatConnection, start_date: str, end_date: str):
    return fetch_df(conn, "SELECT * FROM deductions WHERE deduction_date BETWEEN ? AND ?", (start_date, end_date))
