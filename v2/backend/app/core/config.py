from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cat Kapinda CRM v2 API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    app_env: str = "development"
    database_url: str | None = None
    frontend_app_name: str = "Cat Kapinda CRM v2"
    auth_session_days: int = 30

    model_config = SettingsConfigDict(
        env_prefix="CK_V2_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
