from pydantic import BaseModel


class AuthModesResponse(BaseModel):
    email_login: bool
    phone_login: bool
    sms_login: bool


class AuthLoginRequest(BaseModel):
    identity: str
    password: str


class AuthCurrentUserResponse(BaseModel):
    id: int
    identity: str
    email: str
    phone: str
    full_name: str
    role: str
    role_display: str
    must_change_password: bool
    allowed_actions: list[str]
    expires_at: str


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: str
    user: AuthCurrentUserResponse


class AuthLogoutResponse(BaseModel):
    message: str
