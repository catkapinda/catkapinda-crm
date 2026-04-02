from fastapi.testclient import TestClient

from app.core.bootstrap import mark_runtime_bootstrap_state, reset_runtime_bootstrap_state
from app.core.config import settings
from app.core.database import get_db
from app.main import create_app


class HealthyConnection:
    def execute(self, query: str, params: tuple[str, ...] | None = None):
        if query == "SELECT 1":
            return 1

        assert query == "SELECT to_regclass(%s) AS table_name"
        assert params is not None
        return HealthyCursor(params[0])


class BrokenConnection:
    def execute(self, query: str):
        raise RuntimeError("database offline")


class HealthyCursor:
    def __init__(self, table_name: str):
        self.table_name = table_name

    def fetchone(self):
        return {"table_name": self.table_name}


def test_health_route_returns_service_metadata():
    reset_runtime_bootstrap_state()
    client = TestClient(create_app(enable_bootstrap=False))

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "crmcatkapinda-v2-api"
    assert "version" in payload
    assert "environment" in payload


def test_readiness_route_reports_ok_with_healthy_db():
    reset_runtime_bootstrap_state()
    mark_runtime_bootstrap_state(ok=True, detail="Auth runtime bootstrap basarili.")
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: HealthyConnection()
    client = TestClient(app)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    checks = {entry["name"]: entry for entry in payload["checks"]}
    assert checks["database_reachable"]["ok"] is True
    assert checks["database_reachable"]["detail"] == "Veritabanı erişimi başarılı"


def test_readiness_route_reports_degraded_when_db_is_down():
    reset_runtime_bootstrap_state()
    mark_runtime_bootstrap_state(ok=True, detail="Auth runtime bootstrap basarili.")
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: BrokenConnection()
    client = TestClient(app)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    checks = {entry["name"]: entry for entry in payload["checks"]}
    assert checks["database_reachable"]["ok"] is False
    assert "database offline" in (checks["database_reachable"]["detail"] or "")


def test_pilot_readiness_route_returns_module_and_auth_summary(monkeypatch):
    reset_runtime_bootstrap_state()
    mark_runtime_bootstrap_state(ok=True, detail="Auth runtime bootstrap basarili.")
    monkeypatch.setattr("app.services.auth.sms_delivery_enabled", lambda: True)
    monkeypatch.setattr(settings, "database_url", "postgresql://pilot")
    monkeypatch.setattr(settings, "frontend_base_url", "https://pilot.example.com")
    monkeypatch.setattr(settings, "public_app_url", "https://pilot.example.com")
    monkeypatch.setattr(settings, "auth_ebru_phone", "05321234567")
    monkeypatch.setattr(settings, "auth_mert_phone", "")
    monkeypatch.setattr(settings, "auth_muhammed_phone", "")

    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: HealthyConnection()
    client = TestClient(app)

    response = client.get("/api/health/pilot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["auth"]["email_login"] is True
    assert payload["auth"]["phone_login"] is True
    assert payload["auth"]["sms_login"] is True
    assert payload["auth"]["sms_allowlist_count"] == 1
    assert "config" in payload
    assert "missing_env_vars" in payload
    assert "next_actions" in payload
    assert isinstance(payload["config"], list)
    assert isinstance(payload["missing_env_vars"], list)
    assert isinstance(payload["next_actions"], list)
    modules = {entry["module"]: entry for entry in payload["modules"]}
    assert modules["overview"]["href"] == "/"
    assert modules["attendance"]["status"] == "active"
    assert "detail" in modules["attendance"]
    assert "missing_tables" in modules["attendance"]
    assert modules["reports"]["href"] == "/reports"


def test_readiness_route_reports_degraded_when_runtime_bootstrap_failed():
    reset_runtime_bootstrap_state()
    mark_runtime_bootstrap_state(ok=False, detail="Runtime bootstrap basarisiz: test")
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: HealthyConnection()
    client = TestClient(app)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    payload = response.json()
    checks = {entry["name"]: entry for entry in payload["checks"]}
    assert checks["runtime_bootstrap"]["ok"] is False
    assert "basarisiz" in (checks["runtime_bootstrap"]["detail"] or "")
