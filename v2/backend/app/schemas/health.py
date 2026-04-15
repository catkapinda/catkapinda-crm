from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    commit_sha: str | None = None
    release_label: str | None = None


class HealthCheckEntry(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    commit_sha: str | None = None
    release_label: str | None = None
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


class PilotHelperCommand(BaseModel):
    label: str
    category: str = "env"
    command: str


class PilotCommandPackEntry(BaseModel):
    title: str
    detail: str
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


class LocalSetupSourceEntry(BaseModel):
    label: str
    path: str
    kind: str
    exists: bool


class LocalSetupResponse(BaseModel):
    ready: bool
    backend_env_path: str
    frontend_env_path: str
    backend_env_exists: bool
    frontend_env_exists: bool
    database_url_present: bool
    database_url_source: str | None = None
    default_auth_password_present: bool
    default_auth_password_source: str | None = None
    default_auth_password_is_default: bool
    frontend_proxy_target_present: bool
    frontend_proxy_target: str | None = None
    frontend_proxy_source: str | None = None
    frontend_env_needs_sync: bool = False
    detected_frontend_urls: list[str] = []
    suggested_frontend_url: str | None = None
    suggested_api_url: str | None = None
    suggested_bootstrap_command: str | None = None
    suggested_frontend_env_command: str | None = None
    suggested_scaffold_command: str | None = None
    suggested_env_write_command: str | None = None
    suggested_current_app_env_command: str | None = None
    suggested_backend_start_command: str | None = None
    current_app_seed_detected: bool
    current_app_seed_sources: list[str] = []
    current_app_seed_placeholders: list[str] = []
    current_app_available_sources: list[LocalSetupSourceEntry] = []
    missing_phone_keys: list[str] = []
    blocking_items: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []


class PilotReadinessResponse(BaseModel):
    status: str
    core_ready: bool
    service: str
    version: str
    environment: str
    commit_sha: str | None = None
    release_label: str | None = None
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
    helper_commands: list[PilotHelperCommand]
    command_pack: list[PilotCommandPackEntry]
    services: list[PilotServiceEntry]
    env_snippets: list[PilotEnvSnippetEntry]
