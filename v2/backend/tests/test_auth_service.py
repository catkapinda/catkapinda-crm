from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import hash_auth_password
from app.services.auth import AuthRateLimitError, authenticate_user


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
