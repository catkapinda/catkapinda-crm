from fastapi.testclient import TestClient

from app.main import create_app


def test_auth_modes_reflect_sms_state(monkeypatch):
    monkeypatch.setattr("app.services.auth.sms_delivery_enabled", lambda: True)
    client = TestClient(create_app(enable_bootstrap=False))

    response = client.get("/api/auth/modes")

    assert response.status_code == 200
    assert response.json() == {
        "email_login": True,
        "phone_login": True,
        "sms_login": True,
    }


def test_auth_modes_disable_sms_when_provider_missing(monkeypatch):
    monkeypatch.setattr("app.services.auth.sms_delivery_enabled", lambda: False)
    client = TestClient(create_app(enable_bootstrap=False))

    response = client.get("/api/auth/modes")

    assert response.status_code == 200
    assert response.json()["sms_login"] is False
