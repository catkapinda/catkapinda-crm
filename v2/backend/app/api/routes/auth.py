from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
import psycopg

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.schemas.auth import (
    AuthCurrentUserResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthModesResponse,
)
from app.services.auth import (
    authenticate_user,
    build_auth_modes,
    build_login_response,
    revoke_authenticated_session,
    serialize_authenticated_user,
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
    return build_login_response(user)


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
    return AuthLogoutResponse(message="Oturum kapatildi.")
