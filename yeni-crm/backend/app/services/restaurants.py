"""Restoran servis."""
from datetime import date

from psycopg.rows import dict_row

from app.core.database import get_connection


# Tarife alanları — değişimi rate history'ye yazılır
PRICING_FIELDS: set[str] = {
    "pricing_model",
    "hourly_rate",
    "package_rate",
    "package_threshold",
    "package_rate_low",
    "package_rate_high",
    "fixed_monthly_fee",
    "vat_rate",
}


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
    "standard_daily_hours",
    "contact_name",
    "contact_phone",
    "contact_email",
    "address",
    "company_title",
    "tax_number",
    "tax_office",
    "agreement_date",  # sözleşme imza tarihi
    "start_date",      # operasyon (paket atımı) başlangıç tarihi
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
               vat_rate, target_headcount, standard_daily_hours,
               contact_name, contact_phone,
               agreement_date, start_date, end_date, active, notes
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
               vat_rate, target_headcount, standard_daily_hours,
               contact_name, contact_phone,
               contact_email, address, company_title, tax_number, tax_office,
               agreement_date, start_date, end_date, active, notes
        FROM restaurants
        WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (restaurant_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def create_restaurant(fields: dict) -> dict | None:
    """Yeni restoran ekle. Sadece beyaz listedeki kolonlar geçerli."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe.get("brand"):
        raise ValueError("Marka adı (brand) zorunludur")
    # Varsayılan: aktif
    if "active" not in safe:
        safe["active"] = 1

    cols = list(safe.keys())
    vals = list(safe.values())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"""
        INSERT INTO restaurants ({', '.join(cols)})
        VALUES ({placeholders})
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, vals)
            row = cur.fetchone()
            conn.commit()
    if not row:
        return None
    return get_restaurant(row[0])


def update_restaurant(restaurant_id: int, fields: dict) -> dict | None:
    """Restoran alanlarını güncelle. Sadece beyaz listedeki kolonlar geçerli.

    Tarife alanları (PRICING_FIELDS) değiştiyse:
    - Yeni bir restaurant_pricing_history satırı eklenir
      (effective_from = bugün; bugün için varsa upsert).
    - Geçmiş dönem hesapları eski tarifeyle, bugünden itibaren yeni
      tarifeyle hesaplanmaya devam eder.
    """
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe:
        return get_restaurant(restaurant_id)

    # Mevcut tarifeyi al (değişen var mı kontrolü için)
    current = get_restaurant(restaurant_id) or {}
    pricing_changed = any(
        k in safe and (safe.get(k) is not None and safe[k] != current.get(k))
        for k in PRICING_FIELDS
    )

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
            if updated and pricing_changed:
                # Yeni history satırını oluştur — bugünden itibaren etkili
                _insert_pricing_history(cur, restaurant_id)
            conn.commit()
    if not updated:
        return None
    return get_restaurant(restaurant_id)


def _insert_pricing_history(cur, restaurant_id: int) -> None:
    """Restoranın güncel tarifesini history tablosuna bugünden etkili kaydet.

    Aynı gün içinde birden fazla değişim olursa (effective_from çakışırsa)
    son değer üzerine yazılır.
    """
    today = date.today()
    cur.execute(
        """
        INSERT INTO restaurant_pricing_history (
            restaurant_id, effective_from,
            pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high,
            fixed_monthly_fee, vat_rate, note
        )
        SELECT
            id, %s,
            pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high,
            fixed_monthly_fee, vat_rate, 'Kullanıcı güncellemesi'
        FROM restaurants
        WHERE id = %s
        ON CONFLICT (restaurant_id, effective_from)
        DO UPDATE SET
            pricing_model     = EXCLUDED.pricing_model,
            hourly_rate       = EXCLUDED.hourly_rate,
            package_rate      = EXCLUDED.package_rate,
            package_threshold = EXCLUDED.package_threshold,
            package_rate_low  = EXCLUDED.package_rate_low,
            package_rate_high = EXCLUDED.package_rate_high,
            fixed_monthly_fee = EXCLUDED.fixed_monthly_fee,
            vat_rate          = EXCLUDED.vat_rate,
            created_at        = now(),
            note              = 'Kullanıcı güncellemesi (gün içi revize)'
        """,
        (today, restaurant_id),
    )


def get_pricing_history(restaurant_id: int) -> list[dict]:
    """Bir restoranın tarife değişim geçmişi (yeni → eski)."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id, effective_from, pricing_model,
                    hourly_rate, package_rate,
                    package_threshold, package_rate_low, package_rate_high,
                    fixed_monthly_fee, vat_rate,
                    created_at, note
                FROM restaurant_pricing_history
                WHERE restaurant_id = %s
                ORDER BY effective_from DESC, created_at DESC
                """,
                (restaurant_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def last_pricing_change(restaurant_id: int) -> dict | None:
    """En son tarife değişimi (UI rozeti için)."""
    history = get_pricing_history(restaurant_id)
    return history[0] if history else None
