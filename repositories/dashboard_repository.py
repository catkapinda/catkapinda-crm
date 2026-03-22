from __future__ import annotations

from infrastructure.db_engine import CompatConnection, fetch_df


def fetch_dashboard_entries(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT d.*, r.brand, r.branch, r.target_headcount, r.pricing_model, r.hourly_rate, r.package_rate,
               r.package_threshold, r.package_rate_low, r.package_rate_high, r.fixed_monthly_fee, r.vat_rate
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        """,
    )


def fetch_dashboard_active_restaurants(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM restaurants WHERE active = 1 ORDER BY brand, branch")


def fetch_dashboard_personnel(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM personnel")


def fetch_dashboard_role_history(conn: CompatConnection):
    return fetch_df(conn, "SELECT * FROM personnel_role_history ORDER BY personnel_id, effective_date, id")


def fetch_dashboard_deductions_for_period(conn: CompatConnection, month_start: str, month_end: str):
    return fetch_df(conn, "SELECT * FROM deductions WHERE deduction_date BETWEEN ? AND ?", (month_start, month_end))
