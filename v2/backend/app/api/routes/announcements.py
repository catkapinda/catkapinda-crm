from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps.auth import require_action
from app.core.security import AuthenticatedUser
from app.schemas.announcements import AnnouncementsDashboardResponse, AnnouncementsModuleStatus
from app.services.announcements import build_announcements_dashboard, build_announcements_status

router = APIRouter()


@router.get("/status", response_model=AnnouncementsModuleStatus)
def get_announcements_status() -> AnnouncementsModuleStatus:
    return build_announcements_status()


@router.get("/dashboard", response_model=AnnouncementsDashboardResponse)
def get_announcements_dashboard(
    _user: Annotated[AuthenticatedUser, Depends(require_action("announcements.view"))],
) -> AnnouncementsDashboardResponse:
    return build_announcements_dashboard()
