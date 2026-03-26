from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SalesModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class SalesSummary(BaseModel):
    total_entries: int
    open_follow_up: int
    proposal_stage: int
    won_count: int


class SalesEntry(BaseModel):
    id: int
    restaurant_name: str
    city: str
    district: str
    address: str
    contact_name: str
    contact_phone: str
    contact_email: str
    requested_courier_count: int
    lead_source: str
    proposed_quote: float
    pricing_model: str
    pricing_model_label: str
    pricing_model_hint: str
    hourly_rate: float
    package_rate: float
    package_threshold: int
    package_rate_low: float
    package_rate_high: float
    fixed_monthly_fee: float
    status: str
    next_follow_up_date: date | None
    assigned_owner: str
    notes: str
    created_at: str
    updated_at: str


class SalesDashboardResponse(BaseModel):
    module: str
    status: str
    summary: SalesSummary
    recent_entries: list[SalesEntry]


class SalesPricingModelOption(BaseModel):
    value: str
    label: str


class SalesFormOptionsResponse(BaseModel):
    pricing_models: list[SalesPricingModelOption]
    source_options: list[str]
    status_options: list[str]
    selected_pricing_model: str


class SalesManagementResponse(BaseModel):
    total_entries: int
    entries: list[SalesEntry]


class SalesDetailResponse(BaseModel):
    entry: SalesEntry


class SalesRecordBase(BaseModel):
    restaurant_name: str = Field(min_length=1)
    city: str = Field(min_length=1)
    district: str = Field(min_length=1)
    address: str = ""
    contact_name: str = Field(min_length=1)
    contact_phone: str = Field(min_length=1)
    contact_email: str = ""
    requested_courier_count: int = 0
    lead_source: str = ""
    proposed_quote: float = 0
    pricing_model: str = "hourly_plus_package"
    hourly_rate: float = 0
    package_rate: float = 0
    package_threshold: int = 390
    package_rate_low: float = 0
    package_rate_high: float = 0
    fixed_monthly_fee: float = 0
    status: str = ""
    next_follow_up_date: date | None = None
    assigned_owner: str = ""
    notes: str = ""


class SalesCreateRequest(SalesRecordBase):
    pass


class SalesUpdateRequest(SalesRecordBase):
    pass


class SalesCreateResponse(BaseModel):
    message: str
    entry_id: int


class SalesUpdateResponse(BaseModel):
    message: str


class SalesDeleteResponse(BaseModel):
    message: str
