from fastapi import APIRouter

from app.schemas.attendance import AttendanceModuleStatus

router = APIRouter()


@router.get("/status", response_model=AttendanceModuleStatus)
def get_attendance_status() -> AttendanceModuleStatus:
    return AttendanceModuleStatus(
        module="attendance",
        status="planned",
        next_slice="daily-entry-form",
    )
