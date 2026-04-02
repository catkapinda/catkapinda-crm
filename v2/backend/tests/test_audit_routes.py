from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.main import create_app


def fake_admin_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=1,
        identity="admin@catkapinda.com",
        email="admin@catkapinda.com",
        phone="",
        full_name="Admin",
        role="admin",
        role_display="Admin",
        must_change_password=False,
        allowed_actions=["audit.view"],
        expires_at="2099-01-01T00:00:00",
        token="token",
    )


def test_audit_status_route_returns_metadata():
    client = TestClient(create_app(enable_bootstrap=False))

    response = client.get("/api/audit/status")

    assert response.status_code == 200
    assert response.json() == {
        "module": "audit",
        "status": "active",
        "next_slice": "audit-management",
    }


def test_audit_routes_return_dashboard_and_records(monkeypatch):
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_current_user] = fake_admin_user
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(
        "app.api.routes.audit.build_audit_dashboard",
        lambda conn, limit: {
            "module": "audit",
            "status": "active",
            "summary": {
                "total_entries": 12,
                "last_7_days": 4,
                "unique_actors": 2,
                "unique_entities": 3,
            },
            "recent_entries": [],
            "action_options": ["create"],
            "entity_options": ["personnel"],
            "actor_options": ["Ebru"],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.audit.build_audit_management",
        lambda conn, limit, action_type=None, entity_type=None, actor_name=None, search=None: {
            "total_entries": 12,
            "entries": [],
            "action_options": ["create"],
            "entity_options": ["personnel"],
            "actor_options": ["Ebru"],
        },
    )
    client = TestClient(app)

    dashboard_response = client.get("/api/audit/dashboard")
    records_response = client.get("/api/audit/records")

    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["summary"]["total_entries"] == 12
    assert records_response.status_code == 200
    assert records_response.json()["action_options"] == ["create"]
