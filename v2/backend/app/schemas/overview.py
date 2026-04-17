from datetime import date

from pydantic import BaseModel


class OverviewHeroSummary(BaseModel):
    active_restaurants: int
    active_personnel: int
    month_attendance_entries: int
    month_deduction_entries: int


class OverviewFinanceHighlight(BaseModel):
    label: str
    value: str


class OverviewFinanceSummary(BaseModel):
    selected_month: str | None
    total_revenue: float
    gross_profit: float
    total_personnel_cost: float
    side_income_net: float
    top_restaurants: list[OverviewFinanceHighlight]
    risk_restaurants: list[OverviewFinanceHighlight]


class OverviewHygieneEntry(BaseModel):
    title: str
    subtitle: str


class OverviewHygieneSummary(BaseModel):
    missing_personnel_cards: int
    missing_restaurant_cards: int
    personnel_samples: list[OverviewHygieneEntry]
    restaurant_samples: list[OverviewHygieneEntry]


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
    finance: OverviewFinanceSummary
    hygiene: OverviewHygieneSummary
    modules: list[OverviewModuleCard]
    recent_activity: list[OverviewActivityItem]
