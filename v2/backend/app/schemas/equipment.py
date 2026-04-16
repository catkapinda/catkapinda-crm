from datetime import date

from pydantic import BaseModel


class EquipmentModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class EquipmentSummary(BaseModel):
    total_issues: int
    this_month_issues: int
    installment_rows: int
    total_box_returns: int
    total_box_payout: float
    distinct_items: int


class EquipmentIssueManagementEntry(BaseModel):
    id: int
    personnel_id: int
    personnel_label: str
    issue_date: date
    item_name: str
    quantity: int
    unit_cost: float
    unit_sale_price: float
    vat_rate: float
    total_cost: float
    total_sale: float
    gross_profit: float
    installment_count: int
    sale_type: str
    notes: str
    auto_source_key: str
    is_auto_record: bool


class EquipmentInstallmentEntry(BaseModel):
    deduction_date: date
    personnel_label: str
    deduction_type: str
    amount: float
    notes: str
    auto_source_key: str


class BoxReturnManagementEntry(BaseModel):
    id: int
    personnel_id: int
    personnel_label: str
    return_date: date
    quantity: int
    condition_status: str
    payout_amount: float
    waived: bool
    notes: str


class EquipmentSalesProfitEntry(BaseModel):
    item_name: str
    sold_qty: int
    total_cost: float
    total_sale: float
    gross_profit: float


class EquipmentPurchaseSummaryEntry(BaseModel):
    item_name: str
    purchased_qty: int
    purchased_total: float
    weighted_unit_cost: float


class EquipmentDashboardResponse(BaseModel):
    module: str
    status: str
    summary: EquipmentSummary
    recent_issues: list[EquipmentIssueManagementEntry]
    recent_box_returns: list[BoxReturnManagementEntry]
    installment_entries: list[EquipmentInstallmentEntry]
    sales_profit: list[EquipmentSalesProfitEntry]
    purchase_summary: list[EquipmentPurchaseSummaryEntry]


class EquipmentPersonnelOption(BaseModel):
    id: int
    label: str


class EquipmentItemDefault(BaseModel):
    default_unit_cost: float
    default_sale_price: float
    default_installment_count: int
    default_vat_rate: float


class EquipmentFormOptionsResponse(BaseModel):
    personnel: list[EquipmentPersonnelOption]
    issue_items: list[str]
    sale_type_options: list[str]
    return_condition_options: list[str]
    installment_count_options: list[int]
    item_defaults: dict[str, EquipmentItemDefault]
    selected_personnel_id: int | None
    selected_item: str


class EquipmentIssueCreateRequest(BaseModel):
    personnel_id: int
    issue_date: date
    item_name: str
    quantity: int
    unit_cost: float
    unit_sale_price: float
    installment_count: int
    sale_type: str
    notes: str = ""


class EquipmentIssueCreateResponse(BaseModel):
    equipment_issue_id: int
    message: str


class EquipmentIssueUpdateRequest(BaseModel):
    personnel_id: int
    issue_date: date
    item_name: str
    quantity: int
    unit_cost: float
    unit_sale_price: float
    installment_count: int
    sale_type: str
    notes: str = ""


class EquipmentIssueUpdateResponse(BaseModel):
    equipment_issue_id: int
    message: str


class EquipmentIssueBulkUpdateRequest(BaseModel):
    issue_ids: list[int]
    issue_date: date | None = None
    unit_cost: float | None = None
    unit_sale_price: float | None = None
    vat_rate: float | None = None
    installment_count: int | None = None
    sale_type: str | None = None
    note_append_text: str = ""


class EquipmentIssueBulkUpdateResponse(BaseModel):
    updated_count: int
    message: str


class EquipmentIssueDeleteResponse(BaseModel):
    equipment_issue_id: int
    message: str


class EquipmentIssueBulkDeleteRequest(BaseModel):
    issue_ids: list[int]


class EquipmentIssueBulkDeleteResponse(BaseModel):
    deleted_count: int
    message: str


class EquipmentIssuesManagementResponse(BaseModel):
    total_entries: int
    entries: list[EquipmentIssueManagementEntry]


class EquipmentIssueDetailResponse(BaseModel):
    entry: EquipmentIssueManagementEntry


class BoxReturnCreateRequest(BaseModel):
    personnel_id: int
    return_date: date
    quantity: int
    condition_status: str
    payout_amount: float
    notes: str = ""


class BoxReturnCreateResponse(BaseModel):
    box_return_id: int
    message: str


class BoxReturnUpdateRequest(BaseModel):
    personnel_id: int
    return_date: date
    quantity: int
    condition_status: str
    payout_amount: float
    notes: str = ""


class BoxReturnUpdateResponse(BaseModel):
    box_return_id: int
    message: str


class BoxReturnDeleteResponse(BaseModel):
    box_return_id: int
    message: str


class BoxReturnsManagementResponse(BaseModel):
    total_entries: int
    entries: list[BoxReturnManagementEntry]


class BoxReturnDetailResponse(BaseModel):
    entry: BoxReturnManagementEntry
