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

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.services.courier_auth import (
    create_session,
    get_personnel_for_courier,
    get_session,
    revoke_session,
    verify_credentials,
)
from app.services.courier_portal import (
    create_avans_request,
    get_my_bordro,
    get_my_summary,
    list_my_requests,
)
from app.services.payroll_pdf import generate_payroll_pdf
from app.services.profile_changes import (
    list_changes,
    submit_change,
)

router = APIRouter()


class LoginRequest(BaseModel):
    """Kurye giriş isteği."""

    person_code: str
    last4_tc: str


class AvansRequest(BaseModel):
    """Avans talep isteği."""

    amount: float
    reason: str | None = None


class ProfileChangeRequest(BaseModel):
    """Profil değişiklik talebi."""

    field: str
    new_value: str | None = None


# Bağımlılık: Authorization header'dan veya cookie'den token al
def get_current_personnel_id(
    authorization: str | None = None,
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


@router.post("/logout")
async def logout(authorization: str | None = None) -> dict:
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
async def get_me(authorization: str | None = None) -> dict:
    """Oturum açmış kuryenin bilgileri."""
    personnel_id = get_current_personnel_id(authorization)
    courier = get_personnel_for_courier(personnel_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Kurye bulunamadı")
    return courier


@router.get("/my-bordro")
async def get_bordro(
    period: str = "2026-03",
    authorization: str | None = None,
) -> dict:
    """Kuryenin kendi bordrosunu döner."""
    personnel_id = get_current_personnel_id(authorization)
    try:
        return get_my_bordro(personnel_id, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-bordro/pdf")
async def get_bordro_pdf(
    period: str = "2026-03",
    authorization: str | None = None,
) -> Response:
    """Bordro PDF indir."""
    personnel_id = get_current_personnel_id(authorization)
    try:
        pdf_bytes = generate_payroll_pdf(personnel_id, period)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=bordro-{period}.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-requests")
async def list_requests(authorization: str | None = None) -> list[dict]:
    """Kuryenin talep geçmişi."""
    personnel_id = get_current_personnel_id(authorization)
    return list_my_requests(personnel_id)


@router.post("/my-requests")
async def create_request(
    req: AvansRequest,
    authorization: str | None = None,
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
    authorization: str | None = None,
) -> dict:
    """Kuryenin dashboard özet bilgileri."""
    personnel_id = get_current_personnel_id(authorization)
    try:
        return get_my_summary(personnel_id, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/my-profile-changes")
async def list_profile_changes(authorization: str | None = None) -> list[dict]:
    """Kuryenin profil değişiklik talepleri."""
    personnel_id = get_current_personnel_id(authorization)
    return list_changes(personnel_id=personnel_id)


@router.post("/my-profile-changes")
async def create_profile_change(
    req: ProfileChangeRequest,
    authorization: str | None = None,
) -> dict:
    """Profil değişiklik talebi oluştur."""
    personnel_id = get_current_personnel_id(authorization)

    if not req.field:
        raise HTTPException(status_code=400, detail="Field gerekli")

    try:
        result = submit_change(personnel_id, req.field, req.new_value)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
