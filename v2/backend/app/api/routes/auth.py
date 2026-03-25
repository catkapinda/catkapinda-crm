from fastapi import APIRouter

from app.schemas.auth import AuthModeResponse

router = APIRouter()


@router.get("/modes", response_model=AuthModeResponse)
def get_auth_modes() -> AuthModeResponse:
    return AuthModeResponse(
        email_login=True,
        phone_login=True,
        sms_login=True,
    )
