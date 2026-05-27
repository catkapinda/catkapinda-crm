"""Authentication endpoints — login, me, forgot/reset password, change."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import (
    change_password,
    create_access_token,
    get_current_user,
    get_user_by_email,
    get_user_by_identifier,
    set_reset_token,
    update_last_login,
    use_reset_token,
    verify_password,
)
from app.core.sms_otp import request_otp, verify_otp
from app.core.config import get_settings
from app.core.email import Attachment, send_email

router = APIRouter()
log = logging.getLogger(__name__)


# ─── Pydantic models ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    # Hem e-posta hem telefon kabul eder. '@' varsa email, yoksa phone.
    identifier: str = Field(min_length=4)
    password: str = Field(min_length=4)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class OtpRequestRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class OtpVerifyRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    code: str = Field(min_length=6, max_length=6)


# ─── Endpoints ──────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> dict:
    """E-posta veya telefon + parola → JWT token + user info."""
    user = get_user_by_identifier(payload.identifier)
    if not user or user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bilgileriniz hatalı",
        )
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bilgileriniz hatalı",
        )

    update_last_login(user["id"])
    # Token subject e-posta yoksa phone
    subject_email = user.get("email") or f"phone:{user.get('phone')}"
    token = create_access_token(user["id"], subject_email)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user.get("email"),
            "phone": user.get("phone"),
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    """Mevcut oturum sahibinin bilgileri."""
    return {
        "id": user["id"],
        "email": user.get("email"),
        "phone": user.get("phone"),
        "full_name": user["full_name"],
        "role": user["role"],
        "last_login_at": (
            user["last_login_at"].isoformat() if user.get("last_login_at") else None
        ),
    }


@router.post("/forgot-password", status_code=204)
async def forgot_password(payload: ForgotPasswordRequest) -> None:
    """Şifremi unuttum — kayıtlı e-postaya reset linki yollar.

    Güvenlik: Tüm hatalar yutulur, daima 204 döner (privacy + güvenlik).
    Asıl hata Render log'una yazılır (log.exception).
    """
    try:
        user = get_user_by_email(payload.email)
        if not user or user.get("status") != "active":
            log.info("forgot_password: kullanıcı yok veya pasif (%s)", payload.email)
            return None
        if not user.get("email"):
            log.info("forgot_password: kullanıcı email'i yok (id=%s)", user.get("id"))
            return None

        token = set_reset_token(user["id"])
        settings = get_settings()
        base_url = (
            getattr(settings, "frontend_url", None)
            or "https://crmcatkapinda-v3.onrender.com"
        )
        reset_url = f"{base_url}/sifre-sifirla?token={token}"

        subject = "Çat Kapında CRM — Parola sıfırlama"
        full_name = user.get("full_name") or ""
        text_body = (
            f"Merhaba {full_name},\n\n"
            "Parolanızı sıfırlamak için aşağıdaki linke tıklayın "
            "(24 saat geçerli):\n\n"
            f"{reset_url}\n\n"
            "Bu isteği siz yapmadıysanız bu e-postayı yok sayın.\n\n"
            "Çat Kapında CRM"
        )
        html_body = (
            f"<p>Merhaba {full_name},</p>"
            "<p>Parolanızı sıfırlamak için aşağıdaki butona tıklayın "
            "(24 saat geçerli):</p>"
            f'<p><a href="{reset_url}" style="display:inline-block;padding:12px '
            '24px;background:#0F52BA;color:white;text-decoration:none;'
            'border-radius:8px;font-weight:600">Parolayı Sıfırla</a></p>'
            '<p style="color:#666;font-size:12px">Veya bu linki tarayıcıya '
            f"yapıştırın: <br>{reset_url}</p>"
            '<p style="color:#999;font-size:11px">Bu isteği siz yapmadıysanız '
            "bu e-postayı yok sayın.</p>"
        )

        try:
            send_email(
                to=user["email"],
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                attachments=[],
            )
            log.info("forgot_password e-posta gönderildi: %s", user["email"])
        except Exception as e:  # noqa: BLE001
            log.exception("forgot_password e-posta gönderilemedi: %s", e)
    except Exception as e:  # noqa: BLE001
        # Genel handler — DB, token vs. herhangi bir hata 204'ü değil 500'ü engeller
        log.exception("forgot_password genel hata: %s", e)
    return None


@router.post("/reset-password", status_code=204)
async def reset_password(payload: ResetPasswordRequest) -> None:
    """Reset token + yeni parola → parolayı günceller, token'ı tüketir."""
    ok = use_reset_token(payload.token, payload.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz veya süresi dolmuş token",
        )


@router.post("/change-password", status_code=204)
async def change_password_route(
    payload: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
) -> None:
    """Oturum açık kullanıcı parolasını değiştirir (mevcut parola gerekir)."""
    # Mevcut parolayı doğrula
    full = get_user_by_email(user["email"]) if user.get("email") else None
    if not full or not verify_password(payload.current_password, full["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut parola hatalı",
        )
    change_password(user["id"], payload.new_password)


# ─── SMS OTP — parolasız giriş (BM kullanıcıları için) ─────────────


@router.post("/sms-otp/request")
async def sms_otp_request(payload: OtpRequestRequest) -> dict:
    """Telefona 6-haneli kod gönder.

    Privacy: telefon sistemde olmasa bile sent=True döner (user
    enumeration koruması). Sadece SMS gönderilmez.
    """
    result = request_otp(payload.phone)
    return result


@router.post("/sms-otp/verify", response_model=LoginResponse)
async def sms_otp_verify(payload: OtpVerifyRequest) -> dict:
    """Telefon + kod → JWT token + user info."""
    user = verify_otp(payload.phone, payload.code)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kod hatalı veya süresi dolmuş",
        )
    update_last_login(user["id"])
    subject = user.get("email") or f"phone:{user.get('phone')}"
    token = create_access_token(user["id"], subject)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }
