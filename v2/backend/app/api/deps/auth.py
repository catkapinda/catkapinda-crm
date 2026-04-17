from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
import psycopg

from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.services.auth import resolve_authenticated_user

AUTH_SESSION_COOKIE_NAME = "ck_v2_auth_token"


def get_current_user(
    conn: Annotated[psycopg.Connection, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=AUTH_SESSION_COOKIE_NAME)] = None,
) -> AuthenticatedUser:
    token = extract_bearer_token(authorization) or str(session_cookie or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giris gerekli.",
        )
    try:
        return resolve_authenticated_user(conn, token=token)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum suresi dolmus veya gecersiz.",
        ) from exc


def require_action(action: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if action not in user.allowed_actions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu alani goruntuleme yetkin yok.",
            )
        return user

    return dependency


def extract_bearer_token(authorization: str | None) -> str:
    raw_value = str(authorization or "").strip()
    if not raw_value.lower().startswith("bearer "):
        return ""
    return raw_value[7:].strip()
