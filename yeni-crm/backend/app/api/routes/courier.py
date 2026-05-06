"""Kurye portal API route'ları — giriş, bordro, talepler, profil değişiklikleri.

Prefix: /api/courier
- POST /login — person_code + last4_tc → token
- POST /logout — token'ı iptal et
- GET /me — oturum açmış kuryenin bilgileri
- GET /my-bordro?period=YYYY-MM — kendi bordro detayı
- GET /my-bordro/pdf?period=YYYY-MM — bordro PDF indir
- GET /my-requests — talep geçmişi
- POST /my-requests — avans talep oluştur
- GET /my-profile-changes — kendi profil değişiklik talepleri
- POST /my-profile-changes — profil değişiklik talebi oluştur
"""
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel

from app.services.courier_auth import (
    create_session,
    get_personnel_for_courier,
    get_session,
    revoke_session,
    verify_credentials,
)
from app.services.otp import (
    request_otp_for_phone,
    verify_otp,
)
from app.services.courier_portal import (
    create_avans_request,
    get_my_bordro,
    get_my_bordro_periods,
    get_my_summary,
    list_my_requests,
)
from app.services.payroll_pdf import generate_payroll_pdf
from app.services.profile_changes import (
    CRITICAL_FIELDS,
    DIRECT_EDITABLE_FIELDS,
    direct_update,
    list_changes,
    list_my_direct_changes,
    submit_change,
    update_photo,
)
from app.services.signatures import (
    get_signature,
    save_signature,
)

router = APIRouter()


class LoginRequest(BaseModel):
    """Kurye giriş isteği (eski yöntem — person_code + TC son 4)."""

    person_code: str
    last4_tc: str


class OtpRequestPayload(BaseModel):
    """SMS OTP isteme — telefon numarası girişi."""

    phone: str


class OtpVerifyPayload(BaseModel):
    """SMS OTP doğrulama."""

    phone: str
    code: str


class AvansRequest(BaseModel):
    """Avans talep isteği."""

    amount: float
    reason: str | None = None


class ProfileChangeRequest(BaseModel):
    """Profil değişiklik talebi."""

    field: str
    new_value: str | None = None


class DirectUpdateRequest(BaseModel):
    """Doğrudan profil güncelleme (düşük riskli alan)."""

    field: str
    new_value: str | None = None


class PhotoUploadRequest(BaseModel):
    """Profil fotoğrafı yükleme (data URI)."""

    photo_data_url: str | None = None


class SignatureRequest(BaseModel):
    """Bordro/sözleşme imzası — canvas'tan gelen PNG data URI."""

    signature_data: str


# Bağımlılık: Authorization header'dan veya cookie'den token al
def get_current_personnel_id(
    authorization: str | None = Header(None, alias="Authorization"),
) -> int:
    """FastAPI dependency — request'ten token al ve personnel_id döner.

    Header: Authorization: Bearer <token>
    veya Cookie: kurye_session=<token>
    """
    token = None

    # Header'dan al
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        raise HTTPException(status_code=401, detail="Token gerekli")

    personnel_id = get_session(token)
    if personnel_id is None:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")

    return personnel_id


@router.post("/login")
async def login(req: LoginRequest) -> dict:
    """Kurye giriş — person_code + TC'nin son 4 hanesi.

    Başarılı olursa {token, expires_at, courier: {...}} döner.
    """
    personnel = verify_credentials(req.person_code, req.last4_tc)
    if not personnel:
        raise HTTPException(
            status_code=401,
            detail="Kimlik bilgileri hatalı veya kurye pasif durumda",
        )

    session = create_session(personnel["id"])

    return {
        "token": session["token"],
        "expires_at": session["expires_at"],
        "courier": {
            "id": personnel["id"],
            "person_code": personnel["person_code"],
            "full_name": personnel["full_name"],
            "role": personnel["role"],
        },
    }


@router.post("/login/request-otp")
async def request_login_otp(
    body: OtpRequestPayload, request: Request
) -> dict:
    """Telefon numarasına SMS OTP gönder (kurye giriş ilk adım)."""
    ip = request.client.host if request.client else None
    try:
        return request_otp_for_phone(body.phone, ip_address=ip)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/login/verify-otp")
async def verify_login_otp(body: OtpVerifyPayload) -> dict:
    """SMS OTP doğrula → session yarat → token döner."""
    try:
        personnel = verify_otp(body.phone, body.code)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    if not personnel:
        raise HTTPException(status_code=401, detail="Doğrulama başarısız")

    session = create_session(personnel["id"])
    return {
        "token": session["token"],
        "expires_at": session["expires_at"],
        "courier": {
            "id": personnel["id"],
            "person_code": personnel.get("person_code"),
            "full_name": personnel.get("full_name"),
            "role": personnel.get("role"),
        },
    }


@router.post("/logout")
async def logout(authorization: str | None = Header(None, alias="Authorization")) -> dict:
    """Kuryeyi çıkış yap — token'ı iptal et."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token gerekli")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Geçersiz Authorization header")

    token = parts[1]
    revoke_session(token)

    return {"ok": True}


@router.get("/me")
async def get_me(authorization: str | None = Header(None, alias="Authorization")) -> dict:
    """Oturum açmış kuryenin bilgileri."""
    personnel_id = get_current_personnel_id(authorization)
    courier = get_personnel_for_courier(personnel_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Kurye bulunamadı")
    return courier


@router.get("/my-bordro")
async def get_bordro(
    period: str = "2026-03",
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Kuryenin kendi bordrosunu döner."""
    personnel_id = get_current_personnel_id(authorization)
    try:
        return get_my_bordro(personnel_id, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-bordro-periods")
async def list_my_bordro_periods(
    authorization: str | None = Header(None, alias="Authorization"),
) -> list[dict]:
    """Kuryenin bordrosu olan ayların listesi (yeni → eski)."""
    personnel_id = get_current_personnel_id(authorization)
    return get_my_bordro_periods(personnel_id)


@router.get("/my-bordro/pdf")
async def get_bordro_pdf(
    period: str = "2026-03",
    authorization: str | None = Header(None, alias="Authorization"),
) -> Response:
    """Bordro PDF indir — varsa kuryenin dijital imzası gömülü gelir."""
    from app.services.payroll import get_personnel_payroll
    from app.services.personel import get_personnel

    personnel_id = get_current_personnel_id(authorization)
    try:
        payroll = get_personnel_payroll(personnel_id=personnel_id, period=period)
        if not payroll:
            raise HTTPException(status_code=404, detail="Bordro bulunamadı")
        personnel = get_personnel(personnel_id)
        signature = get_signature(personnel_id, period, include_data=True)
        pdf_bytes = generate_payroll_pdf(
            payroll, personnel, period, signature=signature,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=bordro-{period}.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-requests")
async def list_requests(authorization: str | None = Header(None, alias="Authorization")) -> list[dict]:
    """Kuryenin talep geçmişi."""
    personnel_id = get_current_personnel_id(authorization)
    return list_my_requests(personnel_id)


@router.post("/my-requests")
async def create_request(
    req: AvansRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Avans talep oluştur."""
    personnel_id = get_current_personnel_id(authorization)

    if not req.amount or req.amount <= 0:
        raise HTTPException(status_code=400, detail="Tutar sıfırdan büyük olmalı")

    try:
        result = create_avans_request(
            personnel_id=personnel_id,
            amount=req.amount,
            reason=req.reason or "",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-summary")
async def get_summary(
    period: str = "2026-03",
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Kuryenin dashboard özet bilgileri."""
    personnel_id = get_current_personnel_id(authorization)
    try:
        return get_my_summary(personnel_id, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-profile-changes")
async def list_profile_changes(authorization: str | None = Header(None, alias="Authorization")) -> list[dict]:
    """Kuryenin profil değişiklik talepleri."""
    personnel_id = get_current_personnel_id(authorization)
    return list_changes(personnel_id=personnel_id)


@router.post("/my-profile-changes")
async def create_profile_change(
    req: ProfileChangeRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Kritik alan için profil değişiklik talebi oluştur (admin onaylı)."""
    personnel_id = get_current_personnel_id(authorization)

    if not req.field:
        raise HTTPException(status_code=400, detail="Field gerekli")

    try:
        result = submit_change(personnel_id, req.field, req.new_value)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/my-profile/direct-update")
async def direct_update_profile(
    req: DirectUpdateRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Düşük riskli alan için doğrudan güncelle (acil durum kişisi, doğum tarihi vb.)"""
    personnel_id = get_current_personnel_id(authorization)
    if not req.field:
        raise HTTPException(status_code=400, detail="Field gerekli")
    try:
        return direct_update(personnel_id, req.field, req.new_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/my-profile/photo")
async def upload_profile_photo(
    req: PhotoUploadRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Profil fotoğrafı yükle/sil — data URI formatında."""
    personnel_id = get_current_personnel_id(authorization)
    try:
        return update_photo(personnel_id, req.photo_data_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-profile/direct-log")
async def list_my_direct_log(authorization: str | None = Header(None, alias="Authorization")) -> list[dict]:
    """Kendi doğrudan değişiklik logunu döner (son 30)."""
    personnel_id = get_current_personnel_id(authorization)
    return list_my_direct_changes(personnel_id)


@router.get("/my-profile/editable-fields")
async def get_editable_fields(authorization: str | None = Header(None, alias="Authorization")) -> dict:
    """Hangi alanların direkt vs onay-gerekli olduğunu döner."""
    get_current_personnel_id(authorization)  # auth check
    return {
        "critical": sorted(CRITICAL_FIELDS),
        "direct": sorted(DIRECT_EDITABLE_FIELDS),
    }


# ─────────────────────────────────────────────────────────────────
# E-imza endpointleri
# ─────────────────────────────────────────────────────────────────


@router.post("/my-bordro/{period}/sign")
async def sign_my_bordro(
    period: str,
    body: SignatureRequest,
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Bordroyu dijital olarak imzala (canvas PNG data URI gönderilir)."""
    personnel_id = get_current_personnel_id(authorization)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        return save_signature(
            personnel_id=personnel_id,
            period=period,
            signature_data=body.signature_data,
            ip_address=ip,
            user_agent=ua,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-bordro/{period}/signature")
async def get_my_bordro_signature(
    period: str,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Verilen ay için imza durumunu döner (data dahil değil — sadece meta)."""
    personnel_id = get_current_personnel_id(authorization)
    sig = get_signature(personnel_id, period, include_data=False)
    if not sig:
        return {"is_signed": False, "period": period}
    return sig
