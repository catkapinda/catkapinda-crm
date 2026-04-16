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


class PersonnelPlateSummary(BaseModel):
    total_history_records: int
    active_plate_assignments: int
    active_catkapinda_vehicle_personnel: int
    active_missing_plate_personnel: int


class PersonnelRoleSummary(BaseModel):
    total_history_records: int
    active_personnel: int
    distinct_roles: int
    fixed_cost_cards: int


class PersonnelVehicleSummary(BaseModel):
    total_history_records: int
    active_catkapinda_vehicle_personnel: int
    rental_cards: int
    sale_cards: int


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


class PersonnelPlateCandidateEntry(BaseModel):
    id: int
    person_code: str
    full_name: str
    role: str
    status: str
    restaurant_label: str
    vehicle_mode: str
    current_plate: str
    plate_history_count: int


class PersonnelPlateHistoryEntry(BaseModel):
    id: int
    personnel_id: int
    person_code: str
    full_name: str
    role: str
    restaurant_label: str
    vehicle_mode: str
    current_plate: str
    plate: str
    start_date: date | None
    end_date: date | None
    reason: str
    active: bool


class PersonnelRoleCandidateEntry(BaseModel):
    id: int
    person_code: str
    full_name: str
    role: str
    status: str
    restaurant_label: str
    cost_model: str
    monthly_fixed_cost: float
    role_history_count: int


class PersonnelRoleHistoryEntry(BaseModel):
    id: int
    personnel_id: int
    person_code: str
    full_name: str
    status: str
    restaurant_label: str
    role: str
    cost_model: str
    monthly_fixed_cost: float
    effective_date: date | None
    notes: str


class PersonnelVehicleCandidateEntry(BaseModel):
    id: int
    person_code: str
    full_name: str
    role: str
    status: str
    restaurant_label: str
    vehicle_mode: str
    current_plate: str
    motor_rental_monthly_amount: float
    motor_purchase_start_date: date | None
    motor_purchase_commitment_months: int
    motor_purchase_sale_price: float
    motor_purchase_monthly_deduction: float
    vehicle_history_count: int


class PersonnelVehicleHistoryEntry(BaseModel):
    id: int
    personnel_id: int
    person_code: str
    full_name: str
    role: str
    status: str
    restaurant_label: str
    vehicle_mode: str
    current_plate: str
    motor_rental_monthly_amount: float
    motor_purchase_start_date: date | None
    motor_purchase_commitment_months: int
    motor_purchase_sale_price: float
    motor_purchase_monthly_deduction: float
    effective_date: date | None
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
    motor_rental_monthly_amount: float = 13000.0
    motor_purchase_start_date: date | None = None
    motor_purchase_commitment_months: int = 0
    motor_purchase_sale_price: float = 0.0
    motor_purchase_monthly_deduction: float = 0.0
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


class PersonnelPlateWorkspaceResponse(BaseModel):
    summary: PersonnelPlateSummary
    people: list[PersonnelPlateCandidateEntry]
    history: list[PersonnelPlateHistoryEntry]


class PersonnelRoleWorkspaceResponse(BaseModel):
    summary: PersonnelRoleSummary
    people: list[PersonnelRoleCandidateEntry]
    history: list[PersonnelRoleHistoryEntry]


class PersonnelVehicleWorkspaceResponse(BaseModel):
    summary: PersonnelVehicleSummary
    people: list[PersonnelVehicleCandidateEntry]
    history: list[PersonnelVehicleHistoryEntry]


class PersonnelUpdateRequest(BaseModel):
    full_name: str
    role: str
    phone: str = ""
    assigned_restaurant_id: int | None = None
    status: str = "Aktif"
    start_date: date | None = None
    vehicle_mode: str = "Kendi Motoru"
    motor_rental_monthly_amount: float = 13000.0
    motor_purchase_start_date: date | None = None
    motor_purchase_commitment_months: int = 0
    motor_purchase_sale_price: float = 0.0
    motor_purchase_monthly_deduction: float = 0.0
    current_plate: str = ""
    monthly_fixed_cost: float = 0.0
    notes: str = ""


class PersonnelPlateCreateRequest(BaseModel):
    personnel_id: int
    plate: str
    reason: str = "Yeni zimmet"
    start_date: date | None = None
    end_date: date | None = None


class PersonnelPlateCreateResponse(BaseModel):
    history_id: int
    personnel_id: int
    plate: str
    message: str


class PersonnelRoleCreateRequest(BaseModel):
    personnel_id: int
    role: str
    monthly_fixed_cost: float = 0.0
    effective_date: date | None = None
    notes: str = ""


class PersonnelRoleCreateResponse(BaseModel):
    history_id: int
    personnel_id: int
    role: str
    message: str


class PersonnelVehicleCreateRequest(BaseModel):
    personnel_id: int
    vehicle_mode: str
    motor_rental_monthly_amount: float = 13000.0
    motor_purchase_start_date: date | None = None
    motor_purchase_commitment_months: int = 0
    motor_purchase_sale_price: float = 0.0
    motor_purchase_monthly_deduction: float = 0.0
    effective_date: date | None = None
    notes: str = ""


class PersonnelVehicleCreateResponse(BaseModel):
    history_id: int
    personnel_id: int
    vehicle_mode: str
    message: str


class PersonnelUpdateResponse(BaseModel):
    person_id: int
    person_code: str
    message: str


class PersonnelStatusUpdateResponse(BaseModel):
    person_id: int
    status: str
    message: str


class PersonnelDeleteResponse(BaseModel):
    person_id: int
    message: str
