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
    admin_user_count: int
    mobile_ops_user_count: int
    default_password_configured: bool


class PilotConfigEntry(BaseModel):
    name: str
    service: str = "backend"
    ok: bool
    required: bool = True
    detail: str | None = None
    missing_envs: list[str] = []


class PilotModuleEntry(BaseModel):
    module: str
    label: str
    status: str
    next_slice: str
    href: str
    detail: str | None = None
    missing_tables: list[str] = []


class PilotCutoverSummary(BaseModel):
    phase: str
    ready: bool
    summary: str
    core_checks_ready: bool
    auth_ready: bool
    modules_ready_count: int
    modules_total_count: int
    blocking_items: list[str]
    remaining_items: list[str]


class PilotDecisionSummary(BaseModel):
    title: str
    detail: str
    tone: str
    primary_label: str
    primary_href: str


class PilotAccountEntry(BaseModel):
    email: str
    full_name: str
    role: str
    has_phone: bool


class PilotFlowStep(BaseModel):
    title: str
    detail: str
    href: str


class PilotScenarioStep(BaseModel):
    title: str
    module: str
    detail: str
    success_hint: str
    href: str


class PilotDeployStep(BaseModel):
    title: str
    detail: str
    service_name: str | None = None


class PilotRolloutStep(BaseModel):
    title: str
    detail: str
    status: str
    service_name: str | None = None
    env_keys: list[str] = []


class PilotLinkEntry(BaseModel):
    label: str
    href: str


class PilotSmokeCommand(BaseModel):
    label: str
    command: str


class PilotServiceEnvEntry(BaseModel):
    key: str
    required: bool
    configured: bool
    detail: str | None = None


class PilotServiceEntry(BaseModel):
    name: str
    service_type: str
    public_url: str
    health_path: str
    env_vars: list[PilotServiceEnvEntry] = []


class PilotEnvSnippetEntry(BaseModel):
    service_name: str
    title: str
    body: str


class PilotReadinessResponse(BaseModel):
    status: str
    core_ready: bool
    service: str
    version: str
    environment: str
    checks: list[HealthCheckEntry]
    auth: PilotAuthStatus
    config: list[PilotConfigEntry]
    missing_env_vars: list[str]
    required_missing_env_vars: list[str]
    optional_missing_env_vars: list[str]
    next_actions: list[str]
    modules: list[PilotModuleEntry]
    cutover: PilotCutoverSummary
    decision: PilotDecisionSummary
    pilot_accounts: list[PilotAccountEntry]
    pilot_flow: list[PilotFlowStep]
    pilot_scenarios: list[PilotScenarioStep]
    deploy_steps: list[PilotDeployStep]
    rollout_steps: list[PilotRolloutStep]
    pilot_links: list[PilotLinkEntry]
    smoke_commands: list[PilotSmokeCommand]
    services: list[PilotServiceEntry]
    env_snippets: list[PilotEnvSnippetEntry]
