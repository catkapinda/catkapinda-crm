from datetime import date

from pydantic import BaseModel


class PurchasesModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class PurchaseSummary(BaseModel):
    total_entries: int
    this_month_entries: int
    this_month_total_invoice: float
    distinct_suppliers: int


class PurchaseManagementEntry(BaseModel):
    id: int
    purchase_date: date
    item_name: str
    quantity: int
    total_invoice_amount: float
    unit_cost: float
    supplier: str
    invoice_no: str
    notes: str


class PurchasesDashboardResponse(BaseModel):
    module: str
    status: str
    summary: PurchaseSummary
    recent_entries: list[PurchaseManagementEntry]


class PurchasesFormOptionsResponse(BaseModel):
    item_options: list[str]
    selected_item: str


class PurchaseCreateRequest(BaseModel):
    purchase_date: date
    item_name: str
    quantity: int
    total_invoice_amount: float
    supplier: str = ""
    invoice_no: str = ""
    notes: str = ""


class PurchaseCreateResponse(BaseModel):
    purchase_id: int
    message: str


class PurchasesManagementResponse(BaseModel):
    total_entries: int
    entries: list[PurchaseManagementEntry]


class PurchaseDetailResponse(BaseModel):
    entry: PurchaseManagementEntry


class PurchaseUpdateRequest(BaseModel):
    purchase_date: date
    item_name: str
    quantity: int
    total_invoice_amount: float
    supplier: str = ""
    invoice_no: str = ""
    notes: str = ""


class PurchaseUpdateResponse(BaseModel):
    purchase_id: int
    message: str


class PurchaseDeleteResponse(BaseModel):
    purchase_id: int
    message: str
