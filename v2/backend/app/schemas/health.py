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
    modules: list[PilotModuleEntry]
