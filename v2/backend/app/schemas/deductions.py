from datetime import date

from pydantic import BaseModel


class DeductionsModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class DeductionSummary(BaseModel):
    total_entries: int
    this_month_entries: int
    manual_entries: int
    auto_entries: int


class DeductionManagementEntry(BaseModel):
    id: int
    personnel_id: int
    personnel_label: str
    deduction_date: date
    deduction_type: str
    type_caption: str
    amount: float
    notes: str
    auto_source_key: str
    is_auto_record: bool


class DeductionsDashboardResponse(BaseModel):
    module: str
    status: str
    summary: DeductionSummary
    recent_entries: list[DeductionManagementEntry]


class DeductionPersonnelOption(BaseModel):
    id: int
    label: str


class DeductionsFormOptionsResponse(BaseModel):
    personnel: list[DeductionPersonnelOption]
    deduction_types: list[str]
    type_captions: dict[str, str]
    selected_personnel_id: int | None


class DeductionCreateRequest(BaseModel):
    personnel_id: int
    deduction_date: date
    deduction_type: str
    amount: float
    notes: str = ""


class DeductionCreateResponse(BaseModel):
    deduction_id: int
    message: str


class DeductionsManagementResponse(BaseModel):
    total_entries: int
    entries: list[DeductionManagementEntry]


class DeductionDetailResponse(BaseModel):
    entry: DeductionManagementEntry


class DeductionUpdateRequest(BaseModel):
    personnel_id: int
    deduction_date: date
    deduction_type: str
    amount: float
    notes: str = ""


class DeductionUpdateResponse(BaseModel):
    deduction_id: int
    message: str


class DeductionDeleteResponse(BaseModel):
    deduction_id: int
    message: str
