"""Uygulama ayarları — environment'tan okur."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Veritabanı
    database_url: str = "postgresql://localhost/postgres"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # SMS
    sms_provider: str = "netgsm"
    sms_api_url: str = "https://api.netgsm.com.tr"
    sms_netgsm_username: str = ""
    sms_netgsm_password: str = ""
    sms_sender: str = "CATKAPINDA"
    # Test/staging allowlist — virgülle ayrılmış telefon listesi
    # (örn. "05551234567,05559876543"). Boşsa allowlist devre dışı,
    # tüm numaralara gönderim açık (production için bu bekleniyor).
    sms_test_phones: str = ""
    # Redirect mode (test): set edildiyse, **tüm** SMS'lerin hedef
    # numarası bu numaraya yönlendirilir (allowlist by-pass). Kuryelerin
    # gerçek numaralarına dokunulmaz, sadece NetGSM'e giden istekteki
    # `no` alanı override edilir. Production'da boş bırakılır.
    sms_test_redirect_phone: str = ""

    # App
    app_env: str = "development"
    app_name: str = "Catkapinda CRM"
    log_level: str = "INFO"

    # Anthropic / AI Insights
    # ANTHROPIC_API_KEY — Console'dan alınan key. Boşsa AI Insights
    # devre dışı, frontend deterministik fallback'i kullanır.
    anthropic_api_key: str = ""
    ai_insights_model: str = "claude-sonnet-4-5"
    # Cache TTL — saniye (default 48 saat). Yaşı bu değerin üzerindeyse
    # bir sonraki istekte arka planda yeniler ('lazy refresh').
    ai_insights_ttl_seconds: int = 60 * 60 * 48

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sms_test_phones_set(self) -> set[str]:
        """Allowlist'teki numaraları normalize edilmiş (10 hane '5XX...') set olarak döndürür."""
        out: set[str] = set()
        for raw in (self.sms_test_phones or "").split(","):
            raw = raw.strip()
            if not raw:
                continue
            # Inline normalize (sms.py'a circular import olmasın diye)
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits.startswith("90") and len(digits) == 12:
                digits = digits[2:]
            if digits.startswith("0") and len(digits) == 11:
                digits = digits[1:]
            if len(digits) == 10 and digits.startswith("5"):
                out.add(digits)
        return out

    @property
    def sms_allowlist_enabled(self) -> bool:
        """Allowlist boş değilse aktif (staging davranışı)."""
        return len(self.sms_test_phones_set) > 0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
