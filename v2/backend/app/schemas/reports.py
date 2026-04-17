from pydantic import BaseModel


class ReportsModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class ReportsSummary(BaseModel):
    selected_month: str
    restaurant_count: int
    courier_count: int
    total_hours: float
    total_packages: float
    total_revenue: float
    total_personnel_cost: float
    gross_profit: float
    side_income_net: float


class ReportInvoiceEntry(BaseModel):
    restaurant: str
    pricing_model: str
    total_hours: float
    total_packages: float
    net_invoice: float
    gross_invoice: float


class ReportCostEntry(BaseModel):
    personnel: str
    role: str
    total_hours: float
    total_packages: float
    total_deductions: float
    net_cost: float
    cost_model: str


class ReportModelBreakdownEntry(BaseModel):
    pricing_model: str
    restaurant_count: int
    total_hours: float
    total_packages: float
    gross_invoice: float


class ReportTopRestaurantEntry(BaseModel):
    restaurant: str
    pricing_model: str
    total_hours: float
    total_packages: float
    gross_invoice: float


class ReportTopCourierEntry(BaseModel):
    personnel: str
    role: str
    total_hours: float
    total_deductions: float
    net_cost: float
    cost_model: str


class ReportsCoverageSummary(BaseModel):
    covered_restaurant_count: int
    operational_restaurant_count: int


class ReportSharedOverheadEntry(BaseModel):
    personnel: str
    role: str
    gross_cost: float
    total_deductions: float
    net_cost: float
    allocated_restaurant_count: int
    share_per_restaurant: float


class ReportDistributionEntry(BaseModel):
    restaurant: str
    personnel: str
    role: str
    total_hours: float
    total_packages: float
    allocated_cost: float
    allocation_source: str


class ReportSideIncomeEntry(BaseModel):
    item: str
    revenue: float
    cost: float
    net_profit: float


class ReportSideIncomeSnapshot(BaseModel):
    fuel_reflection_amount: float
    company_fuel_reflection_amount: float
    utts_fuel_discount_amount: float
    partner_card_discount_amount: float


class ReportsDashboardResponse(BaseModel):
    module: str
    status: str
    month_options: list[str]
    selected_month: str | None
    summary: ReportsSummary | None
    invoice_entries: list[ReportInvoiceEntry]
    cost_entries: list[ReportCostEntry]
    model_breakdown: list[ReportModelBreakdownEntry]
    top_restaurants: list[ReportTopRestaurantEntry]
    top_couriers: list[ReportTopCourierEntry]
    coverage: ReportsCoverageSummary
    shared_overhead_entries: list[ReportSharedOverheadEntry]
    distribution_entries: list[ReportDistributionEntry]
    side_income_entries: list[ReportSideIncomeEntry]
    side_income_snapshot: ReportSideIncomeSnapshot
