from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import hash_auth_password
from app.services.auth import (
    AuthRateLimitError,
    authenticate_user,
    reset_password_with_phone_code,
    verify_phone_login_code_and_login,
)


class FakeConnection:
    def __init__(self):
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


def _build_user(password: str) -> dict[str, object]:
    return {
        "id": 7,
        "email": "mert.kurtulus@catkapinda.com",
        "phone": "",
        "full_name": "Mert Kurtuluş",
        "role": "admin",
        "role_display": "Yönetim Kurulu / Yönetici",
        "is_active": 1,
        "must_change_password": 0,
        "password_hash": hash_auth_password(password),
    }


def test_authenticate_user_blocks_after_repeated_failures(monkeypatch):
    conn = FakeConnection()
    user_row = _build_user("DogruSifre123")
    attempts: dict[str, dict[str, object]] = {}

    monkeypatch.setattr(
        "app.services.auth.fetch_auth_user_by_identity",
        lambda _conn, identity: user_row if identity == "mert.kurtulus@catkapinda.com" else None,
    )
    monkeypatch.setattr(
        "app.services.auth.fetch_login_attempt",
        lambda _conn, identity: attempts.get(identity),
    )
    monkeypatch.setattr(
        "app.services.auth.upsert_login_attempt",
        lambda _conn, identity, failed_count, first_failed_at, last_failed_at, blocked_until: attempts.__setitem__(
            identity,
            {
                "identity": identity,
                "failed_count": failed_count,
                "first_failed_at": first_failed_at,
                "last_failed_at": last_failed_at,
                "blocked_until": blocked_until,
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.auth.clear_login_attempt",
        lambda _conn, identity: attempts.pop(identity, None),
    )

    for _ in range(5):
        with pytest.raises(ValueError, match="Giriş bilgileri geçersiz."):
            authenticate_user(conn, identity="mert.kurtulus@catkapinda.com", password="YanlisSifre")

    assert attempts["mert.kurtulus@catkapinda.com"]["failed_count"] == 5
    assert attempts["mert.kurtulus@catkapinda.com"]["blocked_until"]
    assert conn.commit_count == 5

    with pytest.raises(AuthRateLimitError, match="Çok fazla hatalı giriş denemesi."):
        authenticate_user(conn, identity="mert.kurtulus@catkapinda.com", password="DogruSifre123")


def test_authenticate_user_clears_login_attempt_after_success(monkeypatch):
    conn = FakeConnection()
    user_row = _build_user("DogruSifre123")
    attempts = {
        "mert.kurtulus@catkapinda.com": {
            "identity": "mert.kurtulus@catkapinda.com",
            "failed_count": 2,
            "first_failed_at": (datetime.now(UTC) - timedelta(minutes=2)).isoformat(timespec="seconds"),
            "last_failed_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(timespec="seconds"),
            "blocked_until": None,
        }
    }

    monkeypatch.setattr(
        "app.services.auth.fetch_auth_user_by_identity",
        lambda _conn, identity: user_row if identity == "mert.kurtulus@catkapinda.com" else None,
    )
    monkeypatch.setattr(
        "app.services.auth.fetch_login_attempt",
        lambda _conn, identity: attempts.get(identity),
    )
    monkeypatch.setattr(
        "app.services.auth.clear_login_attempt",
        lambda _conn, identity: attempts.pop(identity, None),
    )
    monkeypatch.setattr("app.services.auth.cleanup_expired_auth_sessions", lambda _conn: None)
    monkeypatch.setattr("app.services.auth.insert_auth_session", lambda _conn, **kwargs: None)

    user = authenticate_user(
        conn,
        identity="mert.kurtulus@catkapinda.com",
        password="DogruSifre123",
    )

    assert user.identity == "mert.kurtulus@catkapinda.com"
    assert attempts == {}


def test_authenticate_user_accepts_naive_login_attempt_timestamps(monkeypatch):
    conn = FakeConnection()
    user_row = _build_user("DogruSifre123")
    attempts = {
        "mert.kurtulus@catkapinda.com": {
            "identity": "mert.kurtulus@catkapinda.com",
            "failed_count": 1,
            "first_failed_at": (datetime.now(UTC) - timedelta(minutes=2)).replace(tzinfo=None).isoformat(timespec="seconds"),
            "last_failed_at": (datetime.now(UTC) - timedelta(minutes=1)).replace(tzinfo=None).isoformat(timespec="seconds"),
            "blocked_until": None,
        }
    }

    monkeypatch.setattr(
        "app.services.auth.fetch_auth_user_by_identity",
        lambda _conn, identity: user_row if identity == "mert.kurtulus@catkapinda.com" else None,
    )
    monkeypatch.setattr(
        "app.services.auth.fetch_login_attempt",
        lambda _conn, identity: attempts.get(identity),
    )
    monkeypatch.setattr(
        "app.services.auth.clear_login_attempt",
        lambda _conn, identity: attempts.pop(identity, None),
    )
    monkeypatch.setattr("app.services.auth.cleanup_expired_auth_sessions", lambda _conn: None)
    monkeypatch.setattr("app.services.auth.insert_auth_session", lambda _conn, **kwargs: None)

    user = authenticate_user(
        conn,
        identity="mert.kurtulus@catkapinda.com",
        password="DogruSifre123",
    )

    assert user.identity == "mert.kurtulus@catkapinda.com"
    assert attempts == {}


def test_reset_password_with_phone_code_clears_login_attempts_for_email_and_phone(monkeypatch):
    conn = FakeConnection()
    user_row = _build_user("EskiSifre123")
    user_row["phone"] = "05551234567"
    consumed = {}
    updated = {}
    cleared: list[str] = []

    monkeypatch.setattr("app.services.auth.cleanup_expired_phone_codes", lambda _conn: None)
    monkeypatch.setattr(
        "app.services.auth.fetch_active_phone_code",
        lambda _conn, phone, purpose, now_text: {
            "code_row_id": 44,
            "code_attempt_count": 0,
            **user_row,
            "code_hash": hash_auth_password("123456"),
        },
    )
    monkeypatch.setattr(
        "app.services.auth.consume_phone_code",
        lambda _conn, code_row_id, attempt_count, consumed_at: consumed.update(
            {"code_row_id": code_row_id, "attempt_count": attempt_count}
        ),
    )
    monkeypatch.setattr(
        "app.services.auth.update_auth_user_password",
        lambda _conn, user_id, password_hash: updated.update({"user_id": user_id, "password_hash": password_hash}),
    )
    monkeypatch.setattr(
        "app.services.auth.clear_login_attempt",
        lambda _conn, identity: cleared.append(identity),
    )

    response = reset_password_with_phone_code(
        conn,
        phone="05551234567",
        login_code="123456",
        new_password="YeniSifre123!",
    )

    assert response.message == "Şifre sıfırlandı. Yeni şifrenle giriş yapabilirsin."
    assert consumed == {"code_row_id": 44, "attempt_count": 1}
    assert updated["user_id"] == 7
    assert "mert.kurtulus@catkapinda.com" in cleared
    assert "5551234567" in cleared
    assert conn.commit_count == 1


def test_sms_login_clears_mobile_ops_temporary_password_flag(monkeypatch):
    conn = FakeConnection()
    user_row = _build_user("GeciciSifre123")
    user_row.update(
        {
            "email": "mobile.personnel.97@auth.catkapinda.local",
            "phone": "5435553235",
            "full_name": "Yaşar Tunç Beratoğlu",
            "role": "mobile_ops",
            "role_display": "Mobil Operasyon",
            "must_change_password": 1,
        }
    )
    consumed = {}
    cleared: list[int] = []

    monkeypatch.setattr("app.services.auth.cleanup_expired_phone_codes", lambda _conn: None)
    monkeypatch.setattr(
        "app.services.auth.fetch_active_phone_code",
        lambda _conn, phone, purpose, now_text: {
            "code_row_id": 54,
            "code_attempt_count": 0,
            **user_row,
            "code_hash": hash_auth_password("654321"),
        },
    )
    monkeypatch.setattr(
        "app.services.auth.consume_phone_code",
        lambda _conn, code_row_id, attempt_count, consumed_at: consumed.update(
            {"code_row_id": code_row_id, "attempt_count": attempt_count}
        ),
    )
    monkeypatch.setattr(
        "app.services.auth.clear_auth_user_must_change_password",
        lambda _conn, user_id: cleared.append(user_id),
    )
    monkeypatch.setattr("app.services.auth.create_auth_session", lambda _conn, username: "token-654")

    user = verify_phone_login_code_and_login(
        conn,
        phone="0543 555 32 35",
        login_code="654321",
    )

    assert consumed == {"code_row_id": 54, "attempt_count": 1}
    assert cleared == [7]
    assert user.role == "mobile_ops"
    assert user.must_change_password is False
