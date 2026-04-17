from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from urllib.parse import urlparse


class Settings(BaseSettings):
    app_name: str = "Cat Kapinda CRM v2 API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    app_env: str = "development"
    release_sha: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_RELEASE_SHA", "RENDER_GIT_COMMIT", "COMMIT_SHA"),
    )
    render_service_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_RENDER_SERVICE_NAME", "RENDER_SERVICE_NAME", "SERVICE_NAME"),
    )
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_DATABASE_URL", "DATABASE_URL"),
    )
    local_sqlite_fallback_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("CK_V2_ENABLE_LOCAL_SQLITE_FALLBACK"),
    )
    local_sqlite_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CK_V2_LOCAL_SQLITE_PATH"),
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
    def resolved_local_sqlite_path(self) -> str:
        configured = str(self.local_sqlite_path or "").strip()
        if configured:
            return configured
        return str(Path(__file__).resolve().parents[2] / ".local" / "catkapinda_crm.db")

    @property
    def is_production(self) -> bool:
        return str(self.app_env or "").strip().lower() == "production"

    @property
    def trusted_hostnames(self) -> list[str]:
        configured_urls = {
            self.resolved_frontend_base_url,
            self.resolved_public_app_url,
            self.resolved_api_public_url,
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000",
            "http://testserver",
        }
        hostnames = set[str]()
        for raw_url in configured_urls:
            hostname = urlparse(str(raw_url or "").strip()).hostname or ""
            if hostname:
                hostnames.add(hostname)
        render_hostname = str(self.render_service_name or "").strip()
        if render_hostname:
            hostnames.add(render_hostname)
        return sorted(hostnames)

    @property
    def short_release_sha(self) -> str | None:
        if not self.release_sha:
            return None
        return str(self.release_sha).strip()[:7] or None

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
