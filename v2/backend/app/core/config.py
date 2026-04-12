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
    frontend_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_FRONTEND_BASE_URL", "FRONTEND_BASE_URL"),
    )
    public_app_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_PUBLIC_APP_URL", "PUBLIC_APP_URL"),
    )
    api_public_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_API_PUBLIC_URL", "API_PUBLIC_URL"),
    )
    auth_ebru_phone: str = Field(default="", validation_alias=AliasChoices("AUTH_EBRU_PHONE"))
    auth_mert_phone: str = Field(default="", validation_alias=AliasChoices("AUTH_MERT_PHONE"))
    auth_muhammed_phone: str = Field(default="", validation_alias=AliasChoices("AUTH_MUHAMMED_PHONE"))
    default_auth_password: str = Field(
        default="123456",
        validation_alias=AliasChoices("CK_V2_DEFAULT_AUTH_PASSWORD", "DEFAULT_AUTH_PASSWORD"),
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
            self.resolved_frontend_base_url.rstrip("/"),
            self.resolved_public_app_url.rstrip("/"),
        }
        return [origin for origin in allowed if origin]

    @property
    def resolved_frontend_base_url(self) -> str:
        return str(self.frontend_base_url or self.public_app_url or "http://127.0.0.1:3000").strip()

    @property
    def resolved_public_app_url(self) -> str:
        return str(self.public_app_url or self.frontend_base_url or "http://127.0.0.1:3000").strip()

    @property
    def resolved_api_public_url(self) -> str:
        return str(self.api_public_url or "http://127.0.0.1:8000").strip()

    @property
    def sms_phone_allowlist(self) -> list[str]:
        def normalize(value: str) -> str:
            digits = "".join(ch for ch in str(value or "") if ch.isdigit())
            if digits.startswith("90") and len(digits) == 12:
                digits = digits[2:]
            if digits.startswith("0") and len(digits) == 11:
                digits = digits[1:]
            return digits if len(digits) == 10 else ""

        phones = {
            normalize(self.auth_ebru_phone),
            normalize(self.auth_mert_phone),
            normalize(self.auth_muhammed_phone),
        }
        return sorted(phone for phone in phones if phone)

    @property
    def default_auth_users(self) -> list[dict[str, str]]:
        return [
            {
                "email": "ebru@catkapinda.com",
                "full_name": "Ebru Aslan",
                "role": "admin",
                "role_display": "Yönetim Kurulu / Yönetici",
                "phone": self.auth_ebru_phone,
            },
            {
                "email": "mert.kurtulus@catkapinda.com",
                "full_name": "Mert Kurtuluş",
                "role": "admin",
                "role_display": "Yönetim Kurulu / Yönetici",
                "phone": self.auth_mert_phone,
            },
            {
                "email": "muhammed.terim@catkapinda.com",
                "full_name": "Muhammed Terim",
                "role": "admin",
                "role_display": "Yönetim Kurulu / Yönetici",
                "phone": self.auth_muhammed_phone,
            },
        ]

    @property
    def legacy_auth_identities(self) -> set[str]:
        return {"catkapinda", "chef"}


settings = Settings()
