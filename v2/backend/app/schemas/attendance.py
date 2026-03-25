from pydantic import BaseModel


class AttendanceModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str
