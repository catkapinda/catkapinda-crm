from pydantic import BaseModel


class AuthModeResponse(BaseModel):
    email_login: bool
    phone_login: bool
    sms_login: bool
