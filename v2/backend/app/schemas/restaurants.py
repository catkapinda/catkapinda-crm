from datetime import date

from pydantic import BaseModel


class RestaurantsModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class RestaurantSummary(BaseModel):
    total_restaurants: int
    active_restaurants: int
    passive_restaurants: int
    fixed_monthly_restaurants: int


class RestaurantManagementEntry(BaseModel):
    id: int
    brand: str
    branch: str
    pricing_model: str
    pricing_model_label: str
    hourly_rate: float
    package_rate: float
    package_threshold: int
    package_rate_low: float
    package_rate_high: float
    fixed_monthly_fee: float
    vat_rate: float
    target_headcount: int
    start_date: date | None
    end_date: date | None
    extra_headcount_request: int
    extra_headcount_request_date: date | None
    reduce_headcount_request: int
    reduce_headcount_request_date: date | None
    contact_name: str
    contact_phone: str
    contact_email: str
    company_title: str
    address: str
    tax_office: str
    tax_number: str
    active: bool
    notes: str


class RestaurantsDashboardResponse(BaseModel):
    module: str
    status: str
    summary: RestaurantSummary
    recent_entries: list[RestaurantManagementEntry]


class RestaurantPricingModelOption(BaseModel):
    value: str
    label: str


class RestaurantsFormOptionsResponse(BaseModel):
    pricing_models: list[RestaurantPricingModelOption]
    status_options: list[str]
    selected_pricing_model: str


class RestaurantCreateRequest(BaseModel):
    brand: str
    branch: str
    pricing_model: str
    hourly_rate: float = 0.0
    package_rate: float = 0.0
    package_threshold: int = 390
    package_rate_low: float = 0.0
    package_rate_high: float = 0.0
    fixed_monthly_fee: float = 0.0
    vat_rate: float = 20.0
    target_headcount: int = 0
    start_date: date | None = None
    end_date: date | None = None
    extra_headcount_request: int = 0
    extra_headcount_request_date: date | None = None
    reduce_headcount_request: int = 0
    reduce_headcount_request_date: date | None = None
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    company_title: str = ""
    address: str = ""
    tax_office: str = ""
    tax_number: str = ""
    status: str = "Aktif"
    notes: str = ""


class RestaurantCreateResponse(BaseModel):
    restaurant_id: int
    message: str


class RestaurantsManagementResponse(BaseModel):
    total_entries: int
    entries: list[RestaurantManagementEntry]


class RestaurantDetailResponse(BaseModel):
    entry: RestaurantManagementEntry


class RestaurantUpdateRequest(BaseModel):
    brand: str
    branch: str
    pricing_model: str
    hourly_rate: float = 0.0
    package_rate: float = 0.0
    package_threshold: int = 390
    package_rate_low: float = 0.0
    package_rate_high: float = 0.0
    fixed_monthly_fee: float = 0.0
    vat_rate: float = 20.0
    target_headcount: int = 0
    start_date: date | None = None
    end_date: date | None = None
    extra_headcount_request: int = 0
    extra_headcount_request_date: date | None = None
    reduce_headcount_request: int = 0
    reduce_headcount_request_date: date | None = None
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    company_title: str = ""
    address: str = ""
    tax_office: str = ""
    tax_number: str = ""
    status: str = "Aktif"
    notes: str = ""


class RestaurantUpdateResponse(BaseModel):
    restaurant_id: int
    message: str


class RestaurantStatusUpdateResponse(BaseModel):
    restaurant_id: int
    active: bool
    message: str


class RestaurantDeleteResponse(BaseModel):
    restaurant_id: int
    message: str
