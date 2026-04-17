from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.main import create_app
from app.services.auth import AuthRateLimitError


class FakeConnection:
    def rollback(self) -> None:
        return None


def _build_app() -> TestClient:
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: FakeConnection()
    return TestClient(app)


def test_auth_modes_reflect_sms_state(monkeypatch):
    monkeypatch.setattr("app.services.auth.sms_delivery_enabled", lambda: True)
    client = _build_app()

    response = client.get("/api/auth/modes")

    assert response.status_code == 200
    assert response.json() == {
        "email_login": True,
        "phone_login": True,
        "sms_login": True,
    }


def test_auth_modes_disable_sms_when_provider_missing(monkeypatch):
    monkeypatch.setattr("app.services.auth.sms_delivery_enabled", lambda: False)
    client = _build_app()

    response = client.get("/api/auth/modes")

    assert response.status_code == 200
    assert response.json()["sms_login"] is False


def test_request_password_reset_code_route_returns_message(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.request_phone_password_reset_code",
        lambda conn, phone: {
            "message": "Kod gönderildi.",
            "masked_phone": "05******12",
        },
    )
    client = _build_app()

    response = client.post("/api/auth/request-password-reset-code", json={"phone": "05551234512"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "Kod gönderildi.",
        "masked_phone": "05******12",
    }


def test_login_route_records_audit_event(monkeypatch):
    audit_calls = []
    monkeypatch.setattr(
        "app.api.routes.auth.authenticate_user",
        lambda conn, identity, password: AuthenticatedUser(
            id=7,
            identity="mert.kurtulus@catkapinda.com",
            email="mert.kurtulus@catkapinda.com",
            phone="",
            full_name="Mert Kurtuluş",
            role="admin",
            role_display="Yönetim Kurulu / Yönetici",
            must_change_password=False,
            allowed_actions=[],
            expires_at="2099-01-01T00:00:00",
            token="token-123",
        ),
    )
    monkeypatch.setattr(
        "app.api.routes.auth.safe_record_audit_event",
        lambda conn, **kwargs: audit_calls.append(kwargs) or True,
    )
    client = _build_app()

    response = client.post(
        "/api/auth/login",
        json={"identity": "mert.kurtulus@catkapinda.com", "password": "123456"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["identity"] == "mert.kurtulus@catkapinda.com"
    assert "ck_v2_auth_token=" in response.headers["set-cookie"]
    assert "ck_v2_auth_present=1" in response.headers["set-cookie"]
    assert audit_calls[0]["entity_type"] == "oturum"
    assert audit_calls[0]["action_type"] == "giriş"


def test_logout_route_clears_auth_cookies(monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.revoke_authenticated_session", lambda conn, token: None)
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: FakeConnection()
    app.dependency_overrides["unused"] = lambda: None

    from app.api.deps.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=7,
        identity="mert.kurtulus@catkapinda.com",
        email="mert.kurtulus@catkapinda.com",
        phone="",
        full_name="Mert Kurtuluş",
        role="admin",
        role_display="Yönetim Kurulu / Yönetici",
        must_change_password=False,
        allowed_actions=[],
        expires_at="2099-01-01T00:00:00",
        token="token-123",
    )
    client = TestClient(app)

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert "ck_v2_auth_token=" in set_cookie
    assert "ck_v2_auth_present=" in set_cookie


def test_request_password_reset_code_route_returns_validation_error(monkeypatch):
    def _raise_error(conn, phone):
        raise ValueError("Telefon numarası geçersiz.")

    monkeypatch.setattr("app.api.routes.auth.request_phone_password_reset_code", _raise_error)
    client = _build_app()

    response = client.post("/api/auth/request-password-reset-code", json={"phone": "abc"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Telefon numarası geçersiz."


def test_login_route_returns_429_when_identity_is_temporarily_blocked(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.authenticate_user",
        lambda conn, identity, password: (_ for _ in ()).throw(
            AuthRateLimitError("Çok fazla hatalı giriş denemesi. Lütfen 15 dakika sonra tekrar dene.")
        ),
    )
    client = _build_app()

    response = client.post(
        "/api/auth/login",
        json={"identity": "mert.kurtulus@catkapinda.com", "password": "yanlış"},
    )

    assert response.status_code == 429
    assert "Çok fazla hatalı giriş denemesi." in response.json()["detail"]


def test_reset_password_with_code_route_returns_message(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.reset_password_with_phone_code",
        lambda conn, phone, login_code, new_password: {
            "message": "Şifre sıfırlandı. Yeni şifrenle giriş yapabilirsin."
        },
    )
    client = _build_app()

    response = client.post(
        "/api/auth/reset-password-with-code",
        json={
            "phone": "05551234512",
            "code": "123456",
            "new_password": "YeniSifre123",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Şifre sıfırlandı. Yeni şifrenle giriş yapabilirsin."


def test_reset_password_with_code_route_returns_validation_error(monkeypatch):
    def _raise_error(conn, phone, login_code, new_password):
        raise ValueError("Kod geçersiz veya süresi dolmuş.")

    monkeypatch.setattr("app.api.routes.auth.reset_password_with_phone_code", _raise_error)
    client = _build_app()

    response = client.post(
        "/api/auth/reset-password-with-code",
        json={
            "phone": "05551234512",
            "code": "000000",
            "new_password": "YeniSifre123",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Kod geçersiz veya süresi dolmuş."
