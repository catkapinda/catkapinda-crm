from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class HealthCheckEntry(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    checks: list[HealthCheckEntry]


class PilotAuthStatus(BaseModel):
    email_login: bool
    phone_login: bool
    sms_login: bool
    sms_allowlist_count: int


class PilotConfigEntry(BaseModel):
    name: str
    ok: bool
    detail: str | None = None
    missing_envs: list[str] = []


class PilotModuleEntry(BaseModel):
    module: str
    label: str
    status: str
    next_slice: str
    href: str


class PilotReadinessResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    checks: list[HealthCheckEntry]
    auth: PilotAuthStatus
    config: list[PilotConfigEntry]
    missing_env_vars: list[str]
    next_actions: list[str]
    modules: list[PilotModuleEntry]
