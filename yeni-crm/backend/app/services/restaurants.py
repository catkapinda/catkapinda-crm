"""Restoran servis."""
from psycopg.rows import dict_row

from app.core.database import get_connection


def list_restaurants(active: bool | None = True) -> list[dict]:
    """Restoran listesi getir."""
    sql = """
        SELECT id, brand, branch, billing_group, pricing_model,
               hourly_rate, package_rate, package_threshold,
               package_rate_low, package_rate_high, fixed_monthly_fee,
               vat_rate, target_headcount, contact_name, contact_phone,
               start_date, end_date, active, notes
        FROM restaurants
    """
    params: list = []
    if active is True:
        sql += " WHERE active = true"
    elif active is False:
        sql += " WHERE active = false"
    sql += " ORDER BY brand, branch"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)
