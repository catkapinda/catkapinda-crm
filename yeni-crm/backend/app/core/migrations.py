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
    # ─── Box / ekipman geri alım (V2'den taşındı) ───
    # Bir kuryeden, bir tarihte teslim alınan ekipman (varsayılan 'Box')
    # kaydı. Quantity, kondisyon, kuryeye ödenen payout_amount ve waived
    # bayrağı tutulur.
    (
        "box_returns.table",
        """
        CREATE TABLE IF NOT EXISTS box_returns (
            id SERIAL PRIMARY KEY,
            personnel_id integer NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            item_name varchar(80) NOT NULL DEFAULT 'Box',
            return_date date NOT NULL,
            quantity integer NOT NULL DEFAULT 1,
            condition_status varchar(40) NOT NULL,
            payout_amount numeric NOT NULL DEFAULT 0,
            waived boolean NOT NULL DEFAULT false,
            notes text NOT NULL DEFAULT '',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """,
    ),
    (
        "box_returns.idx_personnel",
        """
        CREATE INDEX IF NOT EXISTS idx_box_returns_personnel
        ON box_returns(personnel_id)
        """,
    ),
    (
        "box_returns.idx_return_date",
        """
        CREATE INDEX IF NOT EXISTS idx_box_returns_date
        ON box_returns(return_date DESC)
        """,
    ),
    # V2'den miras kalan tablo eski şemaya sahipse eksik kolonları ekle
    (
        "box_returns.created_at",
        """
        ALTER TABLE box_returns
        ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now()
        """,
    ),
    (
        "box_returns.updated_at",
        """
        ALTER TABLE box_returns
        ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now()
        """,
    ),
    # ─── Tahsilat takibi (restaurant_invoices'a ek alanlar) ───
    # V2'deki restaurant_collections'ın eksik kalan alanlarını V3'ün
    # mevcut restaurant_invoices tablosuna ekliyoruz: due_date,
    # last_contact_date, responsible_name. Böylece /tahsilatlar sayfası
    # tek tablodan beslenir.
    (
        "restaurant_invoices.due_date",
        """
        ALTER TABLE restaurant_invoices
        ADD COLUMN IF NOT EXISTS due_date date
        """,
    ),
    (
        "restaurant_invoices.last_contact_date",
        """
        ALTER TABLE restaurant_invoices
        ADD COLUMN IF NOT EXISTS last_contact_date date
        """,
    ),
    (
        "restaurant_invoices.responsible_name",
        """
        ALTER TABLE restaurant_invoices
        ADD COLUMN IF NOT EXISTS responsible_name varchar(120) DEFAULT ''
        """,
    ),
    (
        "restaurant_invoices.idx_due_date",
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_due_date
        ON restaurant_invoices(due_date)
        WHERE due_date IS NOT NULL
        """,
    ),
    # ─── Restoran tablosuna KURYE TARAFI tarife kolonları ───
    # Çat Kapında'nın kuryeye ÖDEDİĞİ tarifeler (restorandan ALINAN
    # tarifeden farklı). Örnek (sistem default — Fasuli/SushiCo/Quick China):
    #   Restoran: saatlik 273 ₺, eşik 390, low 34, high 47 (KDV hariç)
    #   Kurye:    saatlik 250 ₺, eşik 390, low 20, high 25 (KDV dahil)
    # Quick China istisna: kurye saatlik 250 + paket 25 (sabit, eşik yok)
    (
        "restaurants.courier_pricing_model",
        """
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS courier_pricing_model VARCHAR(40)
        """,
    ),
    (
        "restaurants.courier_hourly_rate",
        """
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS courier_hourly_rate NUMERIC(10,2)
        """,
    ),
    (
        "restaurants.courier_package_rate",
        """
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS courier_package_rate NUMERIC(10,2)
        """,
    ),
    (
        "restaurants.courier_package_threshold",
        """
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS courier_package_threshold INTEGER
        """,
    ),
    (
        "restaurants.courier_package_rate_low",
        """
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS courier_package_rate_low NUMERIC(10,2)
        """,
    ),
    (
        "restaurants.courier_package_rate_high",
        """
        ALTER TABLE restaurants
            ADD COLUMN IF NOT EXISTS courier_package_rate_high NUMERIC(10,2)
        """,
    ),
    # Quick China kuryesi: sabit paket başı 25 ₺ (eşik yok)
    (
        "restaurants.quick_china_courier_override_20260527",
        """
        UPDATE restaurants
        SET courier_pricing_model = 'hourly_plus_package',
            courier_hourly_rate = 250,
            courier_package_rate = 25
        WHERE brand ILIKE '%quick china%'
          AND courier_pricing_model IS NULL
        """,
    ),
    # Doğu Otomotiv kuryesi: saatlik 295 ₺ KDV dahil (diğer alanlar
    # default — threshold 390, low 20, high 25). Yalnız saatlik override.
    (
        "restaurants.dogu_otomotiv_courier_override_20260527",
        """
        UPDATE restaurants
        SET courier_hourly_rate = 295
        WHERE brand ILIKE '%doğu%'
          AND courier_hourly_rate IS NULL
        """,
    ),
    # 2026-05-27 fix: 'Dogu' (ö'süz) yazımını da yakala — ayrıca otomotiv
    # şartı eklenerek başka 'doğu' geçen marka varsa karışmasın.
    # Idempotent: zaten 295 olanı tekrar set etmez.
    (
        "restaurants.dogu_otomotiv_courier_v2_20260527",
        """
        UPDATE restaurants
        SET courier_hourly_rate = 295
        WHERE (brand ILIKE '%doğu%' OR brand ILIKE '%dogu%')
          AND brand ILIKE '%otomotiv%'
          AND (courier_hourly_rate IS NULL OR courier_hourly_rate <> 295)
        """,
    ),
    # ─── Restoran tarife geçmişi (rate history) ───
    # Her tarife değişimi tarihli olarak burada saklanır. Hesaplamalar
    # entry_date'e göre geçerli tarifeyi (effective_from <= entry_date,
    # en yakın) kullanır. Geçmişe dönük rakamlar değişmez.
    (
        "restaurant_pricing_history.table",
        """
        CREATE TABLE IF NOT EXISTS restaurant_pricing_history (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            effective_from DATE NOT NULL,
            pricing_model VARCHAR(40),
            hourly_rate NUMERIC(10,2),
            package_rate NUMERIC(10,2),
            package_threshold INTEGER,
            package_rate_low NUMERIC(10,2),
            package_rate_high NUMERIC(10,2),
            fixed_monthly_fee NUMERIC(12,2),
            vat_rate NUMERIC(5,2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            note TEXT,
            UNIQUE (restaurant_id, effective_from)
        )
        """,
    ),
    (
        "restaurant_pricing_history.idx_lookup",
        """
        CREATE INDEX IF NOT EXISTS idx_pricing_history_lookup
        ON restaurant_pricing_history(restaurant_id, effective_from DESC)
        """,
    ),
    # Backfill: mevcut restoran tarifeleri için ilk satırı oluştur.
    # effective_from = '2026-03-01' (V3 başlangıç dönemi). Eğer restoran
    # zaten history'de varsa atlanır (ON CONFLICT).
    (
        "restaurant_pricing_history.backfill",
        """
        INSERT INTO restaurant_pricing_history (
            restaurant_id, effective_from,
            pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high,
            fixed_monthly_fee, vat_rate, note
        )
        SELECT
            id, '2026-03-01'::date,
            pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high,
            fixed_monthly_fee, vat_rate, 'Backfill — V3 başlangıç'
        FROM restaurants
        WHERE active = 1
        ON CONFLICT (restaurant_id, effective_from) DO NOTHING
        """,
    ),
    # ─── Authentication: users tablosu ───
    (
        "users.table",
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(200) NOT NULL UNIQUE,
            full_name VARCHAR(200),
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(40) NOT NULL DEFAULT 'admin',
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_login_at TIMESTAMPTZ,
            reset_token VARCHAR(100),
            reset_token_expires_at TIMESTAMPTZ
        )
        """,
    ),
    (
        "users.idx_email",
        """
        CREATE INDEX IF NOT EXISTS idx_users_email
        ON users (LOWER(email))
        """,
    ),
    # İlk admin kullanıcı — bcrypt hash of 'admin123'
    # Sadece yoksa ekler. İlk girişten sonra Profil > Şifre Değiştir
    # ile yeni parola belirleyin!
    (
        "users.seed_admin",
        """
        INSERT INTO users (email, full_name, password_hash, role, status)
        VALUES (
            'admin@catkapinda.com',
            'CRM Yönetici',
            '$2b$12$DuHs09ZdXZRVjn0ybXf/iu1qcceDomApAZdCsZFiOYEbOWgILyxay',
            'admin',
            'active'
        )
        ON CONFLICT (email) DO NOTHING
        """,
    ),
    # 2026-05-27: Üç ek admin kullanıcı — hep bcrypt('admin123')
    # İlk girişten sonra Profil > Şifre Değiştir ile yeni parola.
    (
        "users.seed_ebru_20260527",
        """
        INSERT INTO users (email, full_name, password_hash, role, status)
        VALUES (
            'ebru@catkapinda.com',
            'Ebru Aslan',
            '$2b$12$DuHs09ZdXZRVjn0ybXf/iu1qcceDomApAZdCsZFiOYEbOWgILyxay',
            'admin',
            'active'
        )
        ON CONFLICT (email) DO NOTHING
        """,
    ),
    (
        "users.seed_muhammed_20260527",
        """
        INSERT INTO users (email, full_name, password_hash, role, status)
        VALUES (
            'muhammed.terim@catkapinda.com',
            'Muhammed Terim',
            '$2b$12$DuHs09ZdXZRVjn0ybXf/iu1qcceDomApAZdCsZFiOYEbOWgILyxay',
            'admin',
            'active'
        )
        ON CONFLICT (email) DO NOTHING
        """,
    ),
    (
        "users.seed_mert_20260527",
        """
        INSERT INTO users (email, full_name, password_hash, role, status)
        VALUES (
            'mert.kurtulus@catkapinda.com',
            'Mert Kurtuluş',
            '$2b$12$DuHs09ZdXZRVjn0ybXf/iu1qcceDomApAZdCsZFiOYEbOWgILyxay',
            'admin',
            'active'
        )
        ON CONFLICT (email) DO NOTHING
        """,
    ),
    # ─── 2026-05-27: BM rolü — telefon ile giriş ───
    # users tablosuna phone kolonu (UNIQUE, nullable — admin'ler için
    # zorunlu değil, sadece BM giriş yöntemi için)
    (
        "users.add_phone_20260527",
        """
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE
        """,
    ),
    (
        "users.idx_phone_20260527",
        """
        CREATE INDEX IF NOT EXISTS idx_users_phone
        ON users (phone) WHERE phone IS NOT NULL
        """,
    ),
    # email alanını nullable yap — BM kullanıcıları phone ile gireceği
    # için email zorunlu değil
    (
        "users.email_nullable_20260527",
        """
        ALTER TABLE users
            ALTER COLUMN email DROP NOT NULL
        """,
    ),
    # Cihan & Tunç'u personnel tablosundan phone alarak bm role'ünde
    # seed et. Parola admin123 (ilk girişten sonra değiştirsinler).
    # Personnel'de yoksa hiçbir satır eklenmez (sessizce).
    (
        "users.seed_cihan_20260527",
        """
        INSERT INTO users (email, phone, full_name, password_hash, role, status)
        SELECT
            NULL,
            REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g'),
            p.full_name,
            '$2b$12$DuHs09ZdXZRVjn0ybXf/iu1qcceDomApAZdCsZFiOYEbOWgILyxay',
            'bm',
            'active'
        FROM personnel p
        WHERE LOWER(p.full_name) LIKE '%cihan%'
          AND p.phone IS NOT NULL
          AND LENGTH(REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g')) >= 10
        LIMIT 1
        ON CONFLICT DO NOTHING
        """,
    ),
    (
        "users.seed_tunc_20260527",
        """
        INSERT INTO users (email, phone, full_name, password_hash, role, status)
        SELECT
            NULL,
            REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g'),
            p.full_name,
            '$2b$12$DuHs09ZdXZRVjn0ybXf/iu1qcceDomApAZdCsZFiOYEbOWgILyxay',
            'bm',
            'active'
        FROM personnel p
        WHERE (LOWER(p.full_name) LIKE '%tunç%' OR LOWER(p.full_name) LIKE '%tunc%')
          AND p.phone IS NOT NULL
          AND LENGTH(REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g')) >= 10
        LIMIT 1
        ON CONFLICT DO NOTHING
        """,
    ),
    # Welcome SMS gönderildi mi takibi — idempotent kontrol
    (
        "users.add_welcome_sms_flag_20260527",
        """
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS welcome_sms_sent_at TIMESTAMPTZ
        """,
    ),
    # SMS OTP — tek kullanımlık kod ile giriş (parolasız)
    # Cihan/Tunç gibi BM kullanıcıları için telefonla doğrudan giriş.
    (
        "sms_otp_codes.table",
        """
        CREATE TABLE IF NOT EXISTS sms_otp_codes (
            id SERIAL PRIMARY KEY,
            phone VARCHAR(20) NOT NULL,
            code_hash VARCHAR(255) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
    ),
    (
        "sms_otp_codes.idx_phone",
        """
        CREATE INDEX IF NOT EXISTS idx_sms_otp_phone_created
        ON sms_otp_codes (phone, created_at DESC)
        """,
    ),
    # ─── Puantaj: "yerine kim girdi" bağlantısı ────────────────────
    # daily_entries kaydı bir kuryenin gelmediği gün için 'Gelmedi/Raporlu/
    # İhbarsız' status'unda tutulur. covers_personnel_id, o günkü
    # operasyonu KAPSAYAN (yerine giren) kuryeyi gösterir.
    (
        "daily_entries.covers_personnel_id",
        """
        ALTER TABLE daily_entries
        ADD COLUMN IF NOT EXISTS covers_personnel_id integer
        REFERENCES personnel(id) ON DELETE SET NULL
        """,
    ),
    (
        "daily_entries.idx_covers",
        """
        CREATE INDEX IF NOT EXISTS idx_daily_entries_covers
        ON daily_entries(covers_personnel_id)
        WHERE covers_personnel_id IS NOT NULL
        """,
    ),
    # ─── Motor kira başlangıç tarihi (bordro orantılı hesap) ───────
    (
        "personnel.motor_rental_effective_date",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS motor_rental_effective_date date
        """,
    ),
    # ─── Motor bitiş/iade tarihi (bırakma / kendi motoruna geçiş) ──
    # Motor kira ve satış gün bazlı orantılı kesilir. Kurye motoru
    # bıraktıysa ya da kendi motoruna geçtiyse, o güne kadar kesilir.
    # (İş çıkışı zaten exit_date'ten okunur; bu alan motorun bittiği
    # günü ayrıca tutar.)
    (
        "personnel.motor_end_date",
        """
        ALTER TABLE personnel
        ADD COLUMN IF NOT EXISTS motor_end_date date
        """,
    ),
    # ─── Talep geçerlilik tarihi (motor/muhasebe değişikliği yürürlük) ──
    # Talep onaylanınca personel kaydına yazılır: motor → vehicle_to'ya
    # göre motor_end_date / motor_rental_effective_date /
    # motor_purchase_start_date; muhasebe → accounting_effective_date.
    (
        "courier_requests.effective_date",
        """
        ALTER TABLE courier_requests
        ADD COLUMN IF NOT EXISTS effective_date date
        """,
    ),
    # ─── users.phone normalize (SMS OTP eşleşme bug fix) ───────────
    # Seed sırasında REGEXP_REPLACE baştaki 0'ı koruyordu → DB'de
    # '05419073196' (11 hane). Login _normalize_phone ise 0'ı atıp
    # '5419073196' (10 hane) arıyor → EŞLEŞMEZ → SMS gönderilmiyordu.
    # Bu migration tüm users.phone değerlerini 10 haneye normalize eder.
    (
        "users.normalize_phone_20260601",
        """
        UPDATE users
        SET phone = CASE
            WHEN phone ~ '^90[0-9]{10}$' THEN SUBSTRING(phone FROM 3)
            WHEN phone ~ '^0[0-9]{10}$'  THEN SUBSTRING(phone FROM 2)
            ELSE phone
        END
        WHERE phone IS NOT NULL
          AND phone <> CASE
            WHEN phone ~ '^90[0-9]{10}$' THEN SUBSTRING(phone FROM 3)
            WHEN phone ~ '^0[0-9]{10}$'  THEN SUBSTRING(phone FROM 2)
            ELSE phone
          END
        """,
    ),
    # ─── Restoran sözleşme/operasyon tarihleri ─────────────────────
    # start_date = operasyon (paket atımı) başlangıç tarihi → ZATEN VAR
    # agreement_date = sözleşme imza/anlaşma tarihi (operasyondan önce)
    (
        "restaurants.agreement_date",
        """
        ALTER TABLE restaurants
        ADD COLUMN IF NOT EXISTS agreement_date date
        """,
    ),
    # ─── Restoran kurye talepleri (ek kurye / kurye azaltma) ───
    (
        "restaurant_courier_requests.table",
        """
        CREATE TABLE IF NOT EXISTS restaurant_courier_requests (
            id SERIAL PRIMARY KEY,
            restaurant_id integer NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            request_date date NOT NULL DEFAULT current_date,
            change_type varchar(10) NOT NULL,
            count integer NOT NULL DEFAULT 1,
            note text,
            status varchar(20) NOT NULL DEFAULT 'open',
            fulfilled_at date,
            created_by varchar(120),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """,
    ),
    (
        "restaurant_courier_requests.idx_rest",
        """
        CREATE INDEX IF NOT EXISTS idx_rcr_restaurant
        ON restaurant_courier_requests(restaurant_id, request_date DESC)
        """,
    ),
    (
        "restaurant_courier_requests.idx_status",
        """
        CREATE INDEX IF NOT EXISTS idx_rcr_status
        ON restaurant_courier_requests(status)
        """,
    ),
    # 2026-05-27: aktif olmayan veya sonradan eklenen restoranların
    # history satırını da tamamla (Celal Usta gibi). Bu migration
    # idempotent — zaten satırı olanları atlar.
    (
        "restaurant_pricing_history.backfill_v2_20260527",
        """
        INSERT INTO restaurant_pricing_history (
            restaurant_id, effective_from,
            pricing_model, hourly_rate, package_rate,
            package_threshold, package_rate_low, package_rate_high,
            fixed_monthly_fee, vat_rate, note
        )
        SELECT
            r.id, '2026-03-01'::date,
            r.pricing_model, r.hourly_rate, r.package_rate,
            r.package_threshold, r.package_rate_low, r.package_rate_high,
            r.fixed_monthly_fee, r.vat_rate,
            'Backfill v2 — eksik satır tamamla'
        FROM restaurants r
        WHERE NOT EXISTS (
            SELECT 1 FROM restaurant_pricing_history ph
            WHERE ph.restaurant_id = r.id
        )
        ON CONFLICT (restaurant_id, effective_from) DO NOTHING
        """,
    ),
]


def run_migrations() -> None:
    """Startup migration'larını çalıştır. Hatalar log'a yazılır, app açılmaya devam eder.

    ÖNEMLİ: Her migration AYRI transaction'da çalışır (başarılıysa commit,
    hatalıysa rollback). Aksi halde PostgreSQL'de tek bir migration patlayınca
    transaction 'aborted' duruma geçer; sonraki TÜM migration'lar düşer ve
    sondaki tek commit her şeyi geri alır → başarıyla eklenmiş kolonlar
    (ör. motor_end_date) bile kalıcı olmaz. Bu da bordro gibi yeni kolona
    bağımlı endpoint'lerde 500'e yol açar.
    """
    try:
        with get_connection() as conn:
            for name, sql in MIGRATIONS:
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                    conn.commit()  # her başarılı migration hemen kalıcı olsun
                    log.info("migration ok: %s", name)
                except Exception as e:
                    conn.rollback()  # transaction'ı temizle ki sonrakiler çalışsın
                    log.warning("migration failed %s: %s", name, e)
    except Exception as e:
        log.error("migrations connection failed: %s", e)
