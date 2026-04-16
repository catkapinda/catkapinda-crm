from datetime import date

from pydantic import BaseModel, Field


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


class AttendanceRestaurantOption(BaseModel):
    id: int
    label: str
    pricing_model: str
    fixed_monthly_fee: float


class AttendancePersonOption(BaseModel):
    id: int
    label: str
    role: str


class AttendanceFormOptionsResponse(BaseModel):
    restaurants: list[AttendanceRestaurantOption]
    people: list[AttendancePersonOption]
    entry_modes: list[str]
    absence_reasons: list[str]
    bulk_statuses: list[str]
    selected_restaurant_id: int | None
    selected_pricing_model: str | None
    selected_fixed_monthly_fee: float


class AttendanceCreateRequest(BaseModel):
    entry_date: date
    restaurant_id: int
    entry_mode: str
    primary_person_id: int | None = None
    replacement_person_id: int | None = None
    absence_reason: str = ""
    worked_hours: float = 0.0
    package_count: float = 0.0
    monthly_invoice_amount: float = 0.0
    notes: str = ""


class AttendanceCreateResponse(BaseModel):
    entry_id: int
    message: str


class AttendanceBulkCreateRowRequest(BaseModel):
    person_id: int | None = None
    worked_hours: float = 0.0
    package_count: float = 0.0
    entry_status: str = "Normal"
    notes: str = ""


class AttendanceBulkCreateRequest(BaseModel):
    entry_date: date
    restaurant_id: int
    include_all_active: bool = False
    rows: list[AttendanceBulkCreateRowRequest] = Field(default_factory=list)


class AttendanceBulkCreateResponse(BaseModel):
    entry_ids: list[int]
    created_count: int
    message: str


class AttendanceManagementEntry(BaseModel):
    id: int
    entry_date: date
    restaurant_id: int
    restaurant: str
    entry_mode: str
    primary_person_id: int | None
    primary_person_label: str
    replacement_person_id: int | None
    replacement_person_label: str
    absence_reason: str
    coverage_type: str
    worked_hours: float
    package_count: float
    monthly_invoice_amount: float
    notes: str


class AttendanceManagementResponse(BaseModel):
    total_entries: int
    entries: list[AttendanceManagementEntry]


class AttendanceEntryDetailResponse(BaseModel):
    entry: AttendanceManagementEntry


class AttendanceUpdateRequest(BaseModel):
    entry_date: date
    restaurant_id: int
    entry_mode: str
    primary_person_id: int | None = None
    replacement_person_id: int | None = None
    absence_reason: str = ""
    worked_hours: float = 0.0
    package_count: float = 0.0
    monthly_invoice_amount: float = 0.0
    notes: str = ""


class AttendanceUpdateResponse(BaseModel):
    entry_id: int
    message: str


class AttendanceDeleteResponse(BaseModel):
    entry_id: int
    message: str


class AttendanceBulkDeleteRequest(BaseModel):
    entry_ids: list[int] = Field(default_factory=list)


class AttendanceBulkDeleteResponse(BaseModel):
    entry_ids: list[int]
    deleted_count: int
    message: str


class AttendanceFilteredDeleteRequest(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    restaurant_id: int | None = None
    search: str | None = None


class AttendanceFilteredDeleteResponse(BaseModel):
    deleted_count: int
    date_from: date
    date_to: date
    restaurant_id: int | None
    search: str
    message: str
