from pydantic import BaseModel


class PayrollModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class PayrollSummary(BaseModel):
    selected_month: str
    personnel_count: int
    total_hours: float
    total_packages: float
    gross_payroll: float
    total_deductions: float
    net_payment: float


class PayrollEntry(BaseModel):
    personnel_id: int
    personnel: str
    role: str
    status: str
    total_hours: float
    total_packages: float
    gross_pay: float
    total_deductions: float
    net_payment: float
    restaurant_count: int
    cost_model: str


class PayrollCostModelBreakdownEntry(BaseModel):
    cost_model: str
    personnel_count: int
    total_hours: float
    total_packages: float
    net_payment: float


class PayrollTopPersonnelEntry(BaseModel):
    personnel_id: int
    personnel: str
    role: str
    total_hours: float
    total_packages: float
    total_deductions: float
    net_payment: float
    restaurant_count: int
    cost_model: str


class PayrollDashboardResponse(BaseModel):
    module: str
    status: str
    month_options: list[str]
    selected_month: str | None
    role_options: list[str]
    restaurant_options: list[str]
    selected_role: str
    selected_restaurant: str
    summary: PayrollSummary | None
    entries: list[PayrollEntry]
    cost_model_breakdown: list[PayrollCostModelBreakdownEntry]
    top_personnel: list[PayrollTopPersonnelEntry]
