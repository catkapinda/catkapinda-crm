from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg

from app.core.config import settings
from app.core.security import (
    AuthenticatedUser,
    build_session_token,
    build_session_window,
    extract_mobile_auth_personnel_id,
    generate_phone_login_code,
    hash_auth_password,
    is_mobile_auth_email,
    mask_auth_phone,
    normalize_auth_identity,
    normalize_auth_phone,
    resolve_allowed_actions,
    verify_auth_password,
)
from app.core.sms import send_phone_login_code_sms, sms_delivery_enabled
from app.repositories.auth import (
    cleanup_expired_auth_sessions,
    cleanup_expired_phone_codes,
    clear_login_attempt,
    consume_phone_code,
    delete_auth_session,
    delete_pending_phone_codes,
    fetch_login_attempt,
    fetch_active_phone_code,
    fetch_auth_session,
    fetch_auth_user_by_identity,
    fetch_personnel_role_status,
    increment_phone_code_attempt,
    insert_auth_session,
    insert_phone_code,
    upsert_login_attempt,
    update_auth_user_password,
)
from app.schemas.auth import (
    AuthCurrentUserResponse,
    AuthLoginResponse,
    AuthModesResponse,
    AuthPasswordResetResponse,
    AuthPhoneCodeRequestResponse,
)

PHONE_LOGIN_CODE_MINUTES = 10
PHONE_LOGIN_CODE_ATTEMPT_LIMIT = 5
SMS_PHONE_AUTH_PERSONNEL_ROLES = {"Bölge Müdürü"}
LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW_MINUTES = 15
LOGIN_BLOCK_MINUTES = 15


class AuthRateLimitError(ValueError):
    pass


def build_auth_modes() -> AuthModesResponse:
    return AuthModesResponse(
        email_login=True,
        phone_login=True,
        sms_login=sms_delivery_enabled(),
    )


def authenticate_user(
    conn: psycopg.Connection,
    *,
    identity: str,
    password: str,
) -> AuthenticatedUser:
    normalized_identity = normalize_auth_identity(identity)
    now = datetime.now(UTC)
    _ensure_login_not_blocked(conn, identity=normalized_identity, now=now)
    user_row = fetch_auth_user_by_identity(conn, identity=identity)
    if not user_row:
        _record_login_failure(conn, identity=normalized_identity, now=now)
        raise ValueError("Giriş bilgileri geçersiz.")
    if int(user_row.get("is_active") or 0) != 1:
        raise ValueError("Bu hesap aktif degil.")
    if not verify_auth_password(password, str(user_row.get("password_hash") or "")):
        _record_login_failure(conn, identity=normalized_identity, now=now)
        raise ValueError("Giriş bilgileri geçersiz.")

    if normalized_identity:
        clear_login_attempt(conn, identity=normalized_identity)
    token = create_auth_session(conn, username=resolve_session_identity(user_row))
    return build_authenticated_user(user_row=user_row, token=token)


def _parse_attempt_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _ensure_login_not_blocked(
    conn: psycopg.Connection,
    *,
    identity: str,
    now: datetime,
) -> None:
    if not identity:
        return
    row = fetch_login_attempt(conn, identity=identity)
    if not row:
        return

    last_failed_at = _parse_attempt_timestamp(row.get("last_failed_at"))
    blocked_until = _parse_attempt_timestamp(row.get("blocked_until"))
    window_start = now - timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)

    if last_failed_at is None or last_failed_at < window_start:
        clear_login_attempt(conn, identity=identity)
        return
    if blocked_until and blocked_until <= now:
        clear_login_attempt(conn, identity=identity)
        return
    if blocked_until and blocked_until > now:
        raise AuthRateLimitError(
            f"Çok fazla hatalı giriş denemesi. Lütfen {LOGIN_BLOCK_MINUTES} dakika sonra tekrar dene."
        )


def _record_login_failure(
    conn: psycopg.Connection,
    *,
    identity: str,
    now: datetime,
) -> None:
    if not identity:
        return

    row = fetch_login_attempt(conn, identity=identity)
    window_start = now - timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)
    current_failed_count = 0
    first_failed_at_text = now.isoformat(timespec="seconds")

    if row:
        last_failed_at = _parse_attempt_timestamp(row.get("last_failed_at"))
        if last_failed_at and last_failed_at >= window_start:
            current_failed_count = int(row.get("failed_count") or 0)
            first_failed_at_text = str(row.get("first_failed_at") or first_failed_at_text)

    failed_count = current_failed_count + 1
    blocked_until = (
        (now + timedelta(minutes=LOGIN_BLOCK_MINUTES)).isoformat(timespec="seconds")
        if failed_count >= LOGIN_FAILURE_LIMIT
        else None
    )
    upsert_login_attempt(
        conn,
        identity=identity,
        failed_count=failed_count,
        first_failed_at=first_failed_at_text,
        last_failed_at=now.isoformat(timespec="seconds"),
        blocked_until=blocked_until,
    )
    conn.commit()


def create_auth_session(conn: psycopg.Connection, *, username: str) -> str:
    cleanup_expired_auth_sessions(conn)
    token = build_session_token()
    created_at, expires_at = build_session_window()
    insert_auth_session(
        conn,
        token=token,
        username=username,
        created_at=created_at,
        expires_at=expires_at,
    )
    conn.commit()
    return token


def resolve_authenticated_user(
    conn: psycopg.Connection,
    *,
    token: str,
) -> AuthenticatedUser:
    cleanup_expired_auth_sessions(conn)
    session_row = fetch_auth_session(conn, token=token)
    if not session_row:
        raise LookupError("Oturum bulunamadı.")

    user_row = fetch_auth_user_by_identity(conn, identity=str(session_row.get("username") or ""))
    if not user_row or int(user_row.get("is_active") or 0) != 1:
        delete_auth_session(conn, token=token)
        conn.commit()
        raise LookupError("Oturum geçersiz.")

    return build_authenticated_user(
        user_row=user_row,
        token=token,
        expires_at=str(session_row.get("expires_at") or ""),
    )


def revoke_authenticated_session(conn: psycopg.Connection, *, token: str) -> None:
    delete_auth_session(conn, token=token)
    conn.commit()


def resolve_session_identity(user_row: dict) -> str:
    return normalize_auth_identity(str(user_row.get("email") or "")) or normalize_auth_identity(
        str(user_row.get("phone") or "")
    )


def clear_login_attempts_for_user(conn: psycopg.Connection, *, user_row: dict) -> None:
    identities = {
        normalize_auth_identity(str(user_row.get("email") or "")),
        normalize_auth_identity(str(user_row.get("phone") or "")),
    }
    for identity in identities:
        if identity:
            clear_login_attempt(conn, identity=identity)


def build_authenticated_user(
    *,
    user_row: dict,
    token: str,
    expires_at: str | None = None,
) -> AuthenticatedUser:
    allowed_actions = resolve_allowed_actions(str(user_row.get("role") or ""))
    identity = resolve_session_identity(user_row)
    return AuthenticatedUser(
        id=int(user_row.get("id") or 0),
        identity=identity,
        email=str(user_row.get("email") or ""),
        phone=str(user_row.get("phone") or ""),
        full_name=str(user_row.get("full_name") or ""),
        role=str(user_row.get("role") or ""),
        role_display=str(user_row.get("role_display") or str(user_row.get("role") or "")),
        must_change_password=bool(int(user_row.get("must_change_password") or 0)),
        allowed_actions=allowed_actions,
        expires_at=expires_at or build_session_window()[1],
        token=token,
    )


def can_issue_phone_code_for_user(
    conn: psycopg.Connection,
    *,
    user_row: dict,
) -> bool:
    normalized_phone = normalize_auth_phone(str(user_row.get("phone") or ""))
    if not normalized_phone or int(user_row.get("is_active") or 0) != 1:
        return False

    if normalized_phone in settings.sms_phone_allowlist:
        return True

    email_value = str(user_row.get("email") or "")
    if not is_mobile_auth_email(email_value):
        return False

    personnel_id = extract_mobile_auth_personnel_id(email_value)
    if personnel_id <= 0:
        return False

    personnel_row = fetch_personnel_role_status(conn, personnel_id=personnel_id)
    if not personnel_row:
        return False
    return (
        str(personnel_row.get("status") or "").strip() == "Aktif"
        and str(personnel_row.get("role") or "").strip() in SMS_PHONE_AUTH_PERSONNEL_ROLES
    )


def can_issue_password_reset_code_for_user(*, user_row: dict) -> bool:
    normalized_phone = normalize_auth_phone(str(user_row.get("phone") or ""))
    return bool(normalized_phone) and int(user_row.get("is_active") or 0) == 1


def _issue_phone_code(
    conn: psycopg.Connection,
    *,
    user_row: dict,
    phone: str,
    purpose: str,
    message: str,
) -> AuthPhoneCodeRequestResponse:
    cleanup_expired_phone_codes(conn)
    issued_code = generate_phone_login_code()
    now_text = datetime.now(UTC).isoformat(timespec="seconds")
    expires_at = (datetime.now(UTC) + timedelta(minutes=PHONE_LOGIN_CODE_MINUTES)).isoformat(
        timespec="seconds"
    )

    try:
        delete_pending_phone_codes(
            conn,
            auth_user_id=int(user_row.get("id") or 0),
            purpose=purpose,
        )
        insert_phone_code(
            conn,
            auth_user_id=int(user_row.get("id") or 0),
            phone=phone,
            code_hash=hash_auth_password(issued_code),
            purpose=purpose,
            created_at=now_text,
            expires_at=expires_at,
        )
        send_phone_login_code_sms(
            phone,
            str(user_row.get("full_name") or ""),
            issued_code,
            expires_in_minutes=PHONE_LOGIN_CODE_MINUTES,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return AuthPhoneCodeRequestResponse(
        message=message,
        masked_phone=mask_auth_phone(phone),
    )


def request_phone_login_code(
    conn: psycopg.Connection,
    *,
    phone: str,
) -> AuthPhoneCodeRequestResponse:
    if not sms_delivery_enabled():
        raise RuntimeError("SMS ile giriş şu an aktif değil.")

    normalized_phone = normalize_auth_phone(phone)
    if not normalized_phone:
        raise ValueError("Telefon numarası geçersiz.")

    generic_message = "Eger bu telefon numarasi icin SMS giris yetkisi varsa, kod gonderildi."
    user_row = fetch_auth_user_by_identity(conn, identity=normalized_phone)
    if not user_row or not can_issue_phone_code_for_user(conn, user_row=user_row):
        return AuthPhoneCodeRequestResponse(
            message=generic_message,
            masked_phone=mask_auth_phone(normalized_phone),
        )

    return _issue_phone_code(
        conn,
        user_row=user_row,
        phone=normalized_phone,
        purpose="login",
        message=generic_message,
    )


def request_phone_password_reset_code(
    conn: psycopg.Connection,
    *,
    phone: str,
) -> AuthPhoneCodeRequestResponse:
    if not sms_delivery_enabled():
        raise RuntimeError("SMS ile şifre sıfırlama şu an aktif değil.")

    normalized_phone = normalize_auth_phone(phone)
    if not normalized_phone:
        raise ValueError("Telefon numarası geçersiz.")

    generic_message = "Eğer bu telefon numarası için şifre sıfırlama yetkisi varsa, kod gönderildi."
    user_row = fetch_auth_user_by_identity(conn, identity=normalized_phone)
    if not user_row or not can_issue_password_reset_code_for_user(user_row=user_row):
        return AuthPhoneCodeRequestResponse(
            message=generic_message,
            masked_phone=mask_auth_phone(normalized_phone),
        )

    return _issue_phone_code(
        conn,
        user_row=user_row,
        phone=normalized_phone,
        purpose="password_reset",
        message=generic_message,
    )


def verify_phone_login_code_and_login(
    conn: psycopg.Connection,
    *,
    phone: str,
    login_code: str,
) -> AuthenticatedUser:
    normalized_phone = normalize_auth_phone(phone)
    normalized_code = str(login_code or "").strip()
    if not normalized_phone or not normalized_code:
        raise ValueError("Telefon numarası veya kod geçersiz.")

    cleanup_expired_phone_codes(conn)
    now_text = datetime.now(UTC).isoformat(timespec="seconds")
    row = fetch_active_phone_code(
        conn,
        phone=normalized_phone,
        purpose="login",
        now_text=now_text,
    )
    if not row:
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    attempt_count = int(row.get("code_attempt_count") or 0)
    if attempt_count >= PHONE_LOGIN_CODE_ATTEMPT_LIMIT:
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    if not verify_auth_password(normalized_code, str(row.get("code_hash") or "")):
        increment_phone_code_attempt(
            conn,
            code_row_id=int(row.get("code_row_id") or 0),
            attempt_count=attempt_count + 1,
            attempted_at=now_text,
        )
        conn.commit()
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    if int(row.get("is_active") or 0) != 1:
        raise ValueError("Bu hesap aktif değil.")

    consume_phone_code(
        conn,
        code_row_id=int(row.get("code_row_id") or 0),
        attempt_count=attempt_count + 1,
        consumed_at=now_text,
    )
    token = create_auth_session(conn, username=resolve_session_identity(row))
    return build_authenticated_user(user_row=row, token=token)


def reset_password_with_phone_code(
    conn: psycopg.Connection,
    *,
    phone: str,
    login_code: str,
    new_password: str,
) -> AuthPasswordResetResponse:
    normalized_phone = normalize_auth_phone(phone)
    normalized_code = str(login_code or "").strip()
    normalized_new_password = str(new_password or "")
    if not normalized_phone or not normalized_code:
        raise ValueError("Telefon numarası veya kod geçersiz.")
    if len(normalized_new_password) < 6:
        raise ValueError("Yeni şifre en az 6 karakter olmalı.")

    cleanup_expired_phone_codes(conn)
    now_text = datetime.now(UTC).isoformat(timespec="seconds")
    row = fetch_active_phone_code(
        conn,
        phone=normalized_phone,
        purpose="password_reset",
        now_text=now_text,
    )
    if not row:
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    attempt_count = int(row.get("code_attempt_count") or 0)
    if attempt_count >= PHONE_LOGIN_CODE_ATTEMPT_LIMIT:
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    if not verify_auth_password(normalized_code, str(row.get("code_hash") or "")):
        increment_phone_code_attempt(
            conn,
            code_row_id=int(row.get("code_row_id") or 0),
            attempt_count=attempt_count + 1,
            attempted_at=now_text,
        )
        conn.commit()
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    if int(row.get("is_active") or 0) != 1:
        raise ValueError("Bu hesap aktif değil.")

    if verify_auth_password(normalized_new_password, str(row.get("password_hash") or "")):
        raise ValueError("Yeni şifre mevcut şifreden farklı olmalı.")

    consume_phone_code(
        conn,
        code_row_id=int(row.get("code_row_id") or 0),
        attempt_count=attempt_count + 1,
        consumed_at=now_text,
    )
    update_auth_user_password(
        conn,
        user_id=int(row.get("id") or 0),
        password_hash=hash_auth_password(normalized_new_password),
    )
    clear_login_attempts_for_user(conn, user_row=row)
    conn.commit()
    return AuthPasswordResetResponse(message="Şifre sıfırlandı. Yeni şifrenle giriş yapabilirsin.")


def serialize_authenticated_user(user: AuthenticatedUser) -> AuthCurrentUserResponse:
    return AuthCurrentUserResponse(
        id=user.id,
        identity=user.identity,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        role_display=user.role_display,
        must_change_password=user.must_change_password,
        allowed_actions=user.allowed_actions,
        expires_at=user.expires_at,
    )


def build_login_response(user: AuthenticatedUser) -> AuthLoginResponse:
    return AuthLoginResponse(
        access_token=user.token,
        token_type="bearer",
        expires_at=user.expires_at,
        user=serialize_authenticated_user(user),
    )


def change_authenticated_user_password(
    conn: psycopg.Connection,
    *,
    user: AuthenticatedUser,
    current_password: str,
    new_password: str,
) -> AuthenticatedUser:
    normalized_current = str(current_password or "")
    normalized_new = str(new_password or "")
    if len(normalized_new) < 6:
        raise ValueError("Yeni şifre en az 6 karakter olmalı.")
    if normalized_current == normalized_new:
        raise ValueError("Yeni şifre mevcut şifreden farklı olmalı.")

    user_row = fetch_auth_user_by_identity(conn, identity=user.identity)
    if not user_row:
        raise LookupError("Kullanıcı bulunamadı.")
    stored_hash = str(user_row.get("password_hash") or "")
    if not verify_auth_password(normalized_current, stored_hash):
        raise ValueError("Mevcut şifre doğru değil.")

    update_auth_user_password(
        conn,
        user_id=int(user_row.get("id") or 0),
        password_hash=hash_auth_password(normalized_new),
    )
    conn.commit()

    refreshed = fetch_auth_user_by_identity(conn, identity=user.identity)
    if not refreshed:
        raise LookupError("Kullanici güncellenemedi.")
    return build_authenticated_user(
        user_row=refreshed,
        token=user.token,
        expires_at=user.expires_at,
    )
