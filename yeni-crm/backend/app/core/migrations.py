"""Idempotent şema migration'ları.

Backend startup'ında çalışır. ALTER TABLE IF NOT EXISTS gibi güvenli
ifadelerle kolon ekler. Hâlihazırda var olan veri korunur.

Build trigger: 2026-05-04 03:45 — force redeploy after webpack syntax fix.
"""
import logging

from app.core.database import get_connection

log = logging.getLogger(__name__)


# Sadece eklemeli (additive) migration'lar — drop yok, rename yok.
# Her ifade kendi başına idempotent olmalıdır.
MIGRATIONS: list[tuple[str, str]] = [
    (
        "personnel.fixed_monthly_billing",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS fixed_monthly_billing numeric DEFAULT 0
        """,
    ),
    (
        "restaurants.standard_daily_hours",
        """
        ALTER TABLE restaurants
        ADD COLUMN IF NOT EXISTS standard_daily_hours integer DEFAULT 0
        """,
    ),
    (
        "personnel.standard_daily_hours",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS standard_daily_hours integer DEFAULT 11
        """,
    ),
    # ─── Talep modülleri (Avans / Motor değişikliği / Muhasebe değişimi) ───
    (
        "courier_requests.table",
        """
        CREATE TABLE IF NOT EXISTS courier_requests (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            request_type varchar(40) NOT NULL,
            amount numeric DEFAULT 0,
            reason text,
            status varchar(20) NOT NULL DEFAULT 'Beklemede',
            decision_notes text,
            requested_at timestamptz DEFAULT now(),
            decided_at timestamptz,
            decided_by varchar(120)
        )
        """,
    ),
    (
        "courier_requests.idx_personnel",
        """
        CREATE INDEX IF NOT EXISTS idx_requests_personnel
        ON courier_requests(personnel_id)
        """,
    ),
    (
        "courier_requests.idx_status",
        """
        CREATE INDEX IF NOT EXISTS idx_requests_status
        ON courier_requests(status)
        """,
    ),
    # ─── Talep detay alanları (motor & muhasebe değişikliği) ───
    (
        "courier_requests.vehicle_from",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS vehicle_from varchar(40)
        """,
    ),
    (
        "courier_requests.vehicle_to",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS vehicle_to varchar(40)
        """,
    ),
    (
        "courier_requests.vehicle_reason",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS vehicle_reason varchar(40)
        """,
    ),
    (
        "courier_requests.plate",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS plate varchar(20)
        """,
    ),
    (
        "courier_requests.accounting_from",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS accounting_from varchar(40)
        """,
    ),
    (
        "courier_requests.accounting_to",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS accounting_to varchar(40)
        """,
    ),
    # ─── Faturalar (restoran ödeme takip) ───
    (
        "restaurant_invoices.table",
        """
        CREATE TABLE IF NOT EXISTS restaurant_invoices (
            id SERIAL PRIMARY KEY,
            restaurant_id integer NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            period varchar(7) NOT NULL,
            invoice_no varchar(40),
            amount_excl_vat numeric DEFAULT 0,
            vat_amount numeric DEFAULT 0,
            amount_incl_vat numeric DEFAULT 0,
            status varchar(20) NOT NULL DEFAULT 'Beklemede',
            issued_at timestamptz DEFAULT now(),
            paid_at timestamptz,
            paid_amount numeric DEFAULT 0,
            notes text,
            UNIQUE(restaurant_id, period)
        )
        """,
    ),
    (
        "restaurant_invoices.idx_period",
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_period
        ON restaurant_invoices(period)
        """,
    ),
    (
        "restaurant_invoices.idx_status",
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_status
        ON restaurant_invoices(status)
        """,
    ),
]


def run_migrations() -> None:
    """Startup migration'larını çalıştır. Hatalar log'a yazılır, app açılmaya devam eder."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for name, sql in MIGRATIONS:
                    try:
                        cur.execute(sql)
                        log.info("migration ok: %s", name)
                    except Exception as e:
                        log.warning("migration failed %s: %s", name, e)
                conn.commit()
    except Exception as e:
        log.error("migrations connection failed: %s", e)
