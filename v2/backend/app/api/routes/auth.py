from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
import psycopg

from app.api.deps.auth import get_current_user
from app.core.audit import response_to_dict, safe_record_audit_event
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.auth import (
    AuthChangePasswordRequest,
    AuthChangePasswordResponse,
    AuthCurrentUserResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthModesResponse,
    AuthPasswordResetCodeRequest,
    AuthPasswordResetRequest,
    AuthPasswordResetResponse,
    AuthPhoneCodeRequest,
    AuthPhoneCodeRequestResponse,
    AuthPhoneCodeVerifyRequest,
)
from app.services.auth import (
    authenticate_user,
    build_auth_modes,
    build_login_response,
    change_authenticated_user_password,
    request_phone_login_code,
    request_phone_password_reset_code,
    reset_password_with_phone_code,
    revoke_authenticated_session,
    serialize_authenticated_user,
    verify_phone_login_code_and_login,
)

router = APIRouter()


@router.get("/modes", response_model=AuthModesResponse)
def get_auth_modes() -> AuthModesResponse:
    return build_auth_modes()


@router.post("/login", response_model=AuthLoginResponse)
def login_route(
    payload: AuthLoginRequest,
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthLoginResponse:
    try:
        user = authenticate_user(
            conn,
            identity=payload.identity,
            password=payload.password,
        )
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    response = build_login_response(user)
    response_data = response_to_dict(response)
    safe_record_audit_event(
        conn,
        user=user,
        entity_type="oturum",
        action_type="giriş",
        summary="Kullanıcı giriş yaptı.",
        entity_id=user.id,
        details={"identity": user.identity, "token_type": response_data.get("token_type")},
    )
    return response


@router.post("/request-phone-code", response_model=AuthPhoneCodeRequestResponse)
def request_phone_code_route(
    payload: AuthPhoneCodeRequest,
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthPhoneCodeRequestResponse:
    try:
        return request_phone_login_code(conn, phone=payload.phone)
    except RuntimeError as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/request-password-reset-code", response_model=AuthPhoneCodeRequestResponse)
def request_password_reset_code_route(
    payload: AuthPasswordResetCodeRequest,
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthPhoneCodeRequestResponse:
    try:
        return request_phone_password_reset_code(conn, phone=payload.phone)
    except RuntimeError as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/verify-phone-code", response_model=AuthLoginResponse)
def verify_phone_code_route(
    payload: AuthPhoneCodeVerifyRequest,
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthLoginResponse:
    try:
        user = verify_phone_login_code_and_login(
            conn,
            phone=payload.phone,
            login_code=payload.code,
        )
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return build_login_response(user)


@router.post("/reset-password-with-code", response_model=AuthPasswordResetResponse)
def reset_password_with_code_route(
    payload: AuthPasswordResetRequest,
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthPasswordResetResponse:
    try:
        return reset_password_with_phone_code(
            conn,
            phone=payload.phone,
            login_code=payload.code,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/me", response_model=AuthCurrentUserResponse)
def get_current_user_route(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthCurrentUserResponse:
    return serialize_authenticated_user(user)


@router.post("/logout", response_model=AuthLogoutResponse)
def logout_route(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthLogoutResponse:
    revoke_authenticated_session(conn, token=user.token)
    response = AuthLogoutResponse(message="Oturum kapatıldı.")
    safe_record_audit_event(
        conn,
        user=user,
        entity_type="oturum",
        action_type="çıkış",
        summary=response.message,
        entity_id=user.id,
        details={"identity": user.identity},
    )
    return response


@router.post("/change-password", response_model=AuthChangePasswordResponse)
def change_password_route(
    payload: AuthChangePasswordRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> AuthChangePasswordResponse:
    try:
        refreshed_user = change_authenticated_user_password(
            conn,
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except LookupError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = AuthChangePasswordResponse(
        message="Şifre güncellendi.",
        user=serialize_authenticated_user(refreshed_user),
    )
    response_data = response_to_dict(response)
    safe_record_audit_event(
        conn,
        user=refreshed_user,
        entity_type="hesap",
        action_type="şifre değiştir",
        summary=str(response_data.get("message") or ""),
        entity_id=refreshed_user.id,
        details={"identity": refreshed_user.identity},
    )
    return response
