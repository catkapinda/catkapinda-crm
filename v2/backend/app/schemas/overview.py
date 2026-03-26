from datetime import date

from pydantic import BaseModel


class OverviewHeroSummary(BaseModel):
    active_restaurants: int
    active_personnel: int
    month_attendance_entries: int
    month_deduction_entries: int


class OverviewModuleCard(BaseModel):
    key: str
    title: str
    description: str
    href: str
    primary_label: str
    primary_value: str
    secondary_label: str
    secondary_value: str


class OverviewActivityItem(BaseModel):
    module_key: str
    module_label: str
    title: str
    subtitle: str
    meta: str
    entry_date: date | None = None
    href: str


class OverviewDashboardResponse(BaseModel):
    module: str
    status: str
    hero: OverviewHeroSummary
    modules: list[OverviewModuleCard]
    recent_activity: list[OverviewActivityItem]
