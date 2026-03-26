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


class ReportsDashboardResponse(BaseModel):
    module: str
    status: str
    month_options: list[str]
    selected_month: str | None
    summary: ReportsSummary | None
    invoice_entries: list[ReportInvoiceEntry]
    cost_entries: list[ReportCostEntry]
