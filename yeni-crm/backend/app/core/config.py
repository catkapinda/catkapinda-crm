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

    # App
    app_env: str = "development"
    app_name: str = "Catkapinda CRM"
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
