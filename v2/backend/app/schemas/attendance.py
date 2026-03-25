from datetime import date

from pydantic import BaseModel


class AttendanceModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class AttendanceSummary(BaseModel):
    total_entries: int
    today_entries: int
    month_entries: int
    active_restaurants: int


class AttendanceEntrySummary(BaseModel):
    id: int
    entry_date: date
    restaurant: str
    employee_name: str
    entry_mode: str
    absence_reason: str
    coverage_type: str
    worked_hours: float
    package_count: float
    monthly_invoice_amount: float
    notes: str


class AttendanceDashboardResponse(BaseModel):
    module: str
    status: str
    summary: AttendanceSummary
    recent_entries: list[AttendanceEntrySummary]
