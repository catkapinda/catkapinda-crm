from pydantic import BaseModel

from app.schemas.reports import ReportDistributionEntry, ReportProfitEntry, ReportsSummary


class InvoiceDashboardEntry(BaseModel):
    restaurant_id: int | None
    restaurant: str
    pricing_model: str
    total_hours: float
    total_packages: float
    net_invoice: float
    gross_invoice: float


class InvoiceCollectionEntry(BaseModel):
    restaurant_id: int
    restaurant: str
    pricing_model: str
    total_hours: float
    total_packages: float
    net_invoice: float
    gross_invoice: float
    direct_personnel_cost: float
    gross_profit: float
    status: str
    due_date: str | None
    collected_amount: float
    remaining_amount: float
    payment_date: str | None
    last_contact_date: str | None
    responsible_name: str
    note: str


class InvoiceCollectionSummary(BaseModel):
    total_collected_amount: float
    total_open_amount: float
    overdue_amount: float
    tracked_restaurant_count: int
    collected_restaurant_count: int
    overdue_restaurant_count: int
    due_defined_restaurant_count: int


class InvoicesDashboardResponse(BaseModel):
    module: str
    status: str
    month_options: list[str]
    selected_month: str | None
    summary: ReportsSummary | None
    invoice_entries: list[InvoiceDashboardEntry]
    profit_entries: list[ReportProfitEntry]
    distribution_entries: list[ReportDistributionEntry]
    collection_entries: list[InvoiceCollectionEntry]
    collection_summary: InvoiceCollectionSummary
    collection_status_options: list[str]


class InvoiceCollectionUpsertRequest(BaseModel):
    restaurant_id: int
    collection_month: str
    status: str
    due_date: str | None = None
    collected_amount: float = 0.0
    payment_date: str | None = None
    last_contact_date: str | None = None
    responsible_name: str = ""
    note: str = ""


class InvoiceCollectionRecord(BaseModel):
    id: int
    restaurant_id: int
    collection_month: str
    status: str
    due_date: str | None
    collected_amount: float
    payment_date: str | None
    last_contact_date: str | None
    responsible_name: str
    note: str


class InvoiceCollectionUpsertResponse(BaseModel):
    message: str
    record: InvoiceCollectionRecord
