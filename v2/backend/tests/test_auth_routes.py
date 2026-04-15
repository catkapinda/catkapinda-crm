from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import create_app


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


def test_request_password_reset_code_route_returns_validation_error(monkeypatch):
    def _raise_error(conn, phone):
        raise ValueError("Telefon numarası geçersiz.")

    monkeypatch.setattr("app.api.routes.auth.request_phone_password_reset_code", _raise_error)
    client = _build_app()

    response = client.post("/api/auth/request-password-reset-code", json={"phone": "abc"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Telefon numarası geçersiz."


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
