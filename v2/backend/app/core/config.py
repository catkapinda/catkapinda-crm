from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cat Kapinda CRM v2 API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    app_env: str = "development"
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_DATABASE_URL", "DATABASE_URL"),
    )
    frontend_app_name: str = "Cat Kapinda CRM v2"
    auth_session_days: int = 30
    frontend_base_url: str = Field(
        default="http://127.0.0.1:3000",
        validation_alias=AliasChoices("CK_V2_FRONTEND_BASE_URL", "FRONTEND_BASE_URL"),
    )
    public_app_url: str = Field(
        default="http://127.0.0.1:3000",
        validation_alias=AliasChoices("CK_V2_PUBLIC_APP_URL", "PUBLIC_APP_URL"),
    )

    model_config = SettingsConfigDict(
        env_prefix="CK_V2_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_allowed_origins(self) -> list[str]:
        allowed = {
            self.frontend_base_url.rstrip("/"),
            self.public_app_url.rstrip("/"),
        }
        return [origin for origin in allowed if origin]


settings = Settings()
