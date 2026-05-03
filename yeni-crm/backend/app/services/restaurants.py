"""Restoran servis."""
from psycopg.rows import dict_row

from app.core.database import get_connection


# Güncellenebilir kolonlar — beyaz liste (whitelist) güvenlik için
EDITABLE_COLUMNS: set[str] = {
    "brand",
    "branch",
    "billing_group",
    "pricing_model",
    "hourly_rate",
    "package_rate",
    "package_threshold",
    "package_rate_low",
    "package_rate_high",
    "fixed_monthly_fee",
    "vat_rate",
    "target_headcount",
    "contact_name",
    "contact_phone",
    "contact_email",
    "address",
    "company_title",
    "tax_number",
    "tax_office",
    "start_date",
    "end_date",
    "active",
    "notes",
}


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
        sql += " WHERE active = 1"
    elif active is False:
        sql += " WHERE active = 0"
    sql += " ORDER BY brand, branch"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)


def get_restaurant(restaurant_id: int) -> dict | None:
    """Tek restoran detayı."""
    sql = """
        SELECT id, brand, branch, billing_group, pricing_model,
               hourly_rate, package_rate, package_threshold,
               package_rate_low, package_rate_high, fixed_monthly_fee,
               vat_rate, target_headcount, contact_name, contact_phone,
               contact_email, address, company_title, tax_number, tax_office,
               start_date, end_date, active, notes
        FROM restaurants
        WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (restaurant_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def update_restaurant(restaurant_id: int, fields: dict) -> dict | None:
    """Restoran alanlarını güncelle. Sadece beyaz listedeki kolonlar geçerli."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe:
        # Hiç güncellenecek geçerli alan yok — mevcut kaydı dön
        return get_restaurant(restaurant_id)

    set_parts = [f"{col} = %s" for col in safe.keys()]
    sql = f"""
        UPDATE restaurants
        SET {', '.join(set_parts)}
        WHERE id = %s
        RETURNING id
    """
    params = list(safe.values()) + [restaurant_id]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            updated = cur.fetchone()
            conn.commit()
    if not updated:
        return None
    return get_restaurant(restaurant_id)
