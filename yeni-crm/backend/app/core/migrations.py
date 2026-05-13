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
    # ─── Kurye oturum yönetimi (Sprint 1 MVP) ───
    (
        "courier_sessions.table",
        """
        CREATE TABLE IF NOT EXISTS courier_sessions (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            token varchar(64) NOT NULL UNIQUE,
            expires_at timestamptz NOT NULL,
            created_at timestamptz DEFAULT now()
        )
        """,
    ),
    (
        "courier_sessions.idx_token",
        """
        CREATE INDEX IF NOT EXISTS idx_courier_sessions_token
        ON courier_sessions(token)
        """,
    ),
    (
        "courier_sessions.idx_personnel",
        """
        CREATE INDEX IF NOT EXISTS idx_courier_sessions_personnel
        ON courier_sessions(personnel_id)
        """,
    ),
    (
        "courier_sessions.idx_expires_at",
        """
        CREATE INDEX IF NOT EXISTS idx_courier_sessions_expires
        ON courier_sessions(expires_at)
        """,
    ),
    # ─── Kurye profil değişiklik talepleri ───
    (
        "profile_change_requests.table",
        """
        CREATE TABLE IF NOT EXISTS profile_change_requests (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            field varchar(40) NOT NULL,
            old_value text,
            new_value text,
            status varchar(20) NOT NULL DEFAULT 'Beklemede',
            requested_at timestamptz DEFAULT now(),
            decided_at timestamptz,
            decided_by varchar(120),
            decision_notes text
        )
        """,
    ),
    (
        "profile_change_requests.idx_personnel",
        """
        CREATE INDEX IF NOT EXISTS idx_profile_changes_personnel
        ON profile_change_requests(personnel_id)
        """,
    ),
    (
        "profile_change_requests.idx_status",
        """
        CREATE INDEX IF NOT EXISTS idx_profile_changes_status
        ON profile_change_requests(status)
        """,
    ),
    # ─── Profile edit Sprint 2: avatar + direct edit log ───
    (
        "personnel.profile_photo_url",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS profile_photo_url text
        """,
    ),
    (
        "personnel.profile_photo_data",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS profile_photo_data text
        """,
    ),
    (
        "personnel.birth_date",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS birth_date date
        """,
    ),
    (
        "personnel.tshirt_size",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS tshirt_size varchar(10)
        """,
    ),
    (
        "courier_direct_changes.table",
        """
        CREATE TABLE IF NOT EXISTS courier_direct_changes (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            field varchar(60) NOT NULL,
            old_value text,
            new_value text,
            changed_at timestamptz DEFAULT now()
        )
        """,
    ),
    (
        "courier_direct_changes.idx_personnel",
        """
        CREATE INDEX IF NOT EXISTS idx_direct_changes_personnel
        ON courier_direct_changes(personnel_id, changed_at DESC)
        """,
    ),
    # ─── Sprint 2: E-imza (bordro/sözleşme dijital imza) ───
    (
        "payroll_signatures.table",
        """
        CREATE TABLE IF NOT EXISTS payroll_signatures (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            period varchar(7) NOT NULL,
            signature_data text NOT NULL,
            signed_at timestamptz DEFAULT now(),
            ip_address varchar(45),
            user_agent text,
            UNIQUE (personnel_id, period)
        )
        """,
    ),
    (
        "payroll_signatures.idx_personnel_period",
        """
        CREATE INDEX IF NOT EXISTS idx_signatures_personnel_period
        ON payroll_signatures(personnel_id, period)
        """,
    ),
    # ─── Puantaj Onayları (operasyon → admin onay akışı) ───
    (
        "puantaj_approvals.table",
        """
        CREATE TABLE IF NOT EXISTS puantaj_approvals (
            id SERIAL PRIMARY KEY,
            restaurant_id integer NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            period varchar(7) NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'pending',
            submitted_by varchar(120),
            submitted_at timestamptz DEFAULT now(),
            decided_by varchar(120),
            decided_at timestamptz,
            decision_notes text,
            entry_count integer DEFAULT 0,
            total_hours numeric DEFAULT 0,
            total_packages integer DEFAULT 0,
            UNIQUE (restaurant_id, period)
        )
        """,
    ),
    (
        "puantaj_approvals.idx_status",
        """
        CREATE INDEX IF NOT EXISTS idx_puantaj_approvals_status
        ON puantaj_approvals(status, period DESC)
        """,
    ),
    # ─── Sprint 2: SMS OTP login ───
    (
        "courier_otp_codes.table",
        """
        CREATE TABLE IF NOT EXISTS courier_otp_codes (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            code_hash varchar(120) NOT NULL,
            phone_used varchar(20) NOT NULL,
            attempts integer DEFAULT 0,
            created_at timestamptz DEFAULT now(),
            expires_at timestamptz NOT NULL,
            verified_at timestamptz,
            ip_address varchar(45)
        )
        """,
    ),
    (
        "courier_otp_codes.idx_personnel_active",
        """
        CREATE INDEX IF NOT EXISTS idx_otp_personnel_expires
        ON courier_otp_codes(personnel_id, expires_at DESC)
        """,
    ),
    # ─── Bordro hazır SMS bildirim log'u (puantaj onayı sonrası) ───
    # Bir restoran×ay onaylanınca o ayın puantajına dahil kuryelere
    # "bordrun hazır, imzala" SMS'i atılır. UNIQUE(personnel_id, period)
    # kısıtı sayesinde aynı kurye+ay için birden fazla restoran
    # onaylandığında tek SMS gider (de-dup).
    (
        "payroll_sms_log.table",
        """
        CREATE TABLE IF NOT EXISTS payroll_sms_log (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            period varchar(7) NOT NULL,
            sent_at timestamptz DEFAULT now(),
            status varchar(24) NOT NULL DEFAULT 'sent',
              -- sent | failed | no_phone | not_in_allowlist | dry_run
            phone_used varchar(20),
            error text,
            triggered_by_approval_id integer,
            UNIQUE (personnel_id, period)
        )
        """,
    ),
    (
        "payroll_sms_log.idx_period",
        """
        CREATE INDEX IF NOT EXISTS idx_payroll_sms_log_period
        ON payroll_sms_log(period DESC)
        """,
    ),
    # ─── Bordro ödeme takibi (Hakediş Onayları sayfası için) ───
    # Mevcut payroll_signatures tablosuna ödeme alanları eklenir:
    # - paid_at: ödeme yapıldığında doldurulur
    # - paid_by: hangi admin/yönetici işaretledi
    # - paid_amount: net ödenen tutar (snapshot)
    # ALTER TABLE idempotent: kolon yoksa ekle, varsa atla.
    (
        "payroll_signatures.add_paid_at",
        """
        ALTER TABLE payroll_signatures
        ADD COLUMN IF NOT EXISTS paid_at timestamptz
        """,
    ),
    (
        "payroll_signatures.add_paid_by",
        """
        ALTER TABLE payroll_signatures
        ADD COLUMN IF NOT EXISTS paid_by varchar(120)
        """,
    ),
    (
        "payroll_signatures.add_paid_amount",
        """
        ALTER TABLE payroll_signatures
        ADD COLUMN IF NOT EXISTS paid_amount numeric
        """,
    ),
    (
        "payroll_signatures.idx_paid_at",
        """
        CREATE INDEX IF NOT EXISTS idx_signatures_paid_at
        ON payroll_signatures(paid_at)
        WHERE paid_at IS NULL
        """,
    ),
    # ─── AI Insights cache ───
    # Akıllı İçgörü hero kartı için Claude API'den dönen JSON payload
    # burada cache'lenir. TTL: 48 saat (uygulama tarafında kontrol).
    # period: '2026-04' gibi — her dönem ayrı satır
    # generated_at: cache yaşı için
    # payload: JSONB (headline, narrative, cards: [...])
    (
        "ai_insights_cache.table",
        """
        CREATE TABLE IF NOT EXISTS ai_insights_cache (
            id SERIAL PRIMARY KEY,
            scope varchar(40) NOT NULL DEFAULT 'personel',
            period varchar(7) NOT NULL,
            generated_at timestamptz NOT NULL DEFAULT now(),
            payload jsonb NOT NULL,
            model varchar(80),
            input_tokens integer,
            output_tokens integer,
            UNIQUE (scope, period)
        )
        """,
    ),
    (
        "ai_insights_cache.idx_generated_at",
        """
        CREATE INDEX IF NOT EXISTS idx_ai_insights_generated_at
        ON ai_insights_cache(scope, period, generated_at DESC)
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
