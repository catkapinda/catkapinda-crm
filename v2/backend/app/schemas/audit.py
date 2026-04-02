from datetime import datetime

from pydantic import BaseModel


class AuditModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class AuditSummary(BaseModel):
    total_entries: int
    last_7_days: int
    unique_actors: int
    unique_entities: int


class AuditEntry(BaseModel):
    id: int
    created_at: datetime
    actor_username: str
    actor_full_name: str
    actor_role: str
    entity_type: str
    entity_id: str
    action_type: str
    summary: str
    details_json: str


class AuditDashboardResponse(BaseModel):
    module: str
    status: str
    summary: AuditSummary
    recent_entries: list[AuditEntry]
    action_options: list[str]
    entity_options: list[str]
    actor_options: list[str]


class AuditManagementResponse(BaseModel):
    total_entries: int
    entries: list[AuditEntry]
    action_options: list[str]
    entity_options: list[str]
    actor_options: list[str]
