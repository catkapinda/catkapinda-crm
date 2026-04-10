from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.main import create_app


def _fake_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=1,
        identity="admin@catkapinda.com",
        email="admin@catkapinda.com",
        phone="",
        full_name="Admin Kullanici",
        role="admin",
        role_display="Admin",
        must_change_password=False,
        allowed_actions=["payroll.view"],
        expires_at="2099-01-01T00:00:00",
        token="token",
    )


def test_payroll_dashboard_route_returns_breakdown_fields(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.payroll.build_payroll_dashboard",
        lambda *args, **kwargs: {
            "module": "payroll",
            "status": "active",
            "month_options": ["2026-03"],
            "selected_month": "2026-03",
            "role_options": ["Tümü", "Kurye"],
            "restaurant_options": ["Tümü", "Burger@ - Kavacık"],
            "selected_role": "Tümü",
            "selected_restaurant": "Tümü",
            "summary": {
                "selected_month": "2026-03",
                "personnel_count": 2,
                "total_hours": 300.0,
                "total_packages": 420.0,
                "gross_payroll": 85000.0,
                "total_deductions": 12000.0,
                "net_payment": 73000.0,
            },
            "entries": [],
            "cost_model_breakdown": [
                {
                    "cost_model": "Saatlik + Paket",
                    "personnel_count": 2,
                    "total_hours": 300.0,
                    "total_packages": 420.0,
                    "net_payment": 73000.0,
                }
            ],
            "top_personnel": [
                {
                    "personnel_id": 11,
                    "personnel": "Beytullah Belen",
                    "role": "Kurye",
                    "total_hours": 218.0,
                    "total_packages": 263.0,
                    "total_deductions": 0.0,
                    "net_payment": 59760.0,
                    "restaurant_count": 1,
                    "cost_model": "Saatlik + Paket",
                }
            ],
        },
    )

    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_user] = _fake_user
    client = TestClient(app)

    response = client.get("/api/payroll/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["cost_model_breakdown"][0]["cost_model"] == "Saatlik + Paket"
    assert payload["top_personnel"][0]["personnel"] == "Beytullah Belen"
