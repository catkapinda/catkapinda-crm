from datetime import date

from pydantic import BaseModel


class PersonnelModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class PersonnelSummary(BaseModel):
    total_personnel: int
    active_personnel: int
    passive_personnel: int
    assigned_restaurants: int


class PersonnelManagementEntry(BaseModel):
    id: int
    person_code: str
    full_name: str
    role: str
    status: str
    phone: str
    restaurant_id: int | None
    restaurant_label: str
    vehicle_mode: str
    current_plate: str
    start_date: date | None
    monthly_fixed_cost: float
    notes: str


class PersonnelDashboardResponse(BaseModel):
    module: str
    status: str
    summary: PersonnelSummary
    recent_entries: list[PersonnelManagementEntry]


class PersonnelRestaurantOption(BaseModel):
    id: int
    label: str


class PersonnelFormOptionsResponse(BaseModel):
    restaurants: list[PersonnelRestaurantOption]
    role_options: list[str]
    status_options: list[str]
    vehicle_mode_options: list[str]
    selected_restaurant_id: int | None


class PersonnelCreateRequest(BaseModel):
    full_name: str
    role: str
    phone: str = ""
    assigned_restaurant_id: int | None = None
    status: str = "Aktif"
    start_date: date | None = None
    vehicle_mode: str = "Kendi Motoru"
    current_plate: str = ""
    monthly_fixed_cost: float = 0.0
    notes: str = ""


class PersonnelCreateResponse(BaseModel):
    person_id: int
    person_code: str
    message: str


class PersonnelManagementResponse(BaseModel):
    total_entries: int
    entries: list[PersonnelManagementEntry]


class PersonnelDetailResponse(BaseModel):
    entry: PersonnelManagementEntry


class PersonnelUpdateRequest(BaseModel):
    full_name: str
    role: str
    phone: str = ""
    assigned_restaurant_id: int | None = None
    status: str = "Aktif"
    start_date: date | None = None
    vehicle_mode: str = "Kendi Motoru"
    current_plate: str = ""
    monthly_fixed_cost: float = 0.0
    notes: str = ""


class PersonnelUpdateResponse(BaseModel):
    person_id: int
    person_code: str
    message: str
