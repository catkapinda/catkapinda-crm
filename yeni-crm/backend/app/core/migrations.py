"""Idempotent şema migration'ları.

Backend startup'ında çalışır. ALTER TABLE IF NOT EXISTS gibi güvenli
ifadelerle kolon ekler. Hâlihazırda var olan veri korunur.
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
