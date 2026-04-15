from fastapi.testclient import TestClient

from app.core.bootstrap import mark_runtime_bootstrap_state, reset_runtime_bootstrap_state
from app.core.config import settings
from app.core.database import get_db
from app.main import create_app


class HealthyConnection:
    def execute(self, query: str, params: tuple[str, ...] | None = None):
        if query == "SELECT 1":
            return 1

        normalized = " ".join(query.split())
        if normalized.startswith("SELECT COUNT(*) AS count FROM auth_users WHERE role = %s AND is_active = 1"):
            assert params is not None
            role = params[0]
            if role == "admin":
                return CountCursor(3)
            if role == "mobile_ops":
                return CountCursor(2)
            return CountCursor(0)

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


class CountCursor:
    def __init__(self, count: int):
        self.count = count

    def fetchone(self):
        return {"count": self.count}


def test_health_route_returns_service_metadata():
    reset_runtime_bootstrap_state()
    settings.release_sha = "abcdef1234567890"
    settings.render_service_name = "crmcatkapinda-v2-api"
    client = TestClient(create_app(enable_bootstrap=False))

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "crmcatkapinda-v2-api"
    assert "version" in payload
    assert "environment" in payload
    assert payload["commit_sha"] == "abcdef1234567890"
    assert payload["release_label"] == "abcdef1"


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
    monkeypatch.setattr(settings, "api_public_url", "https://pilot-api.example.com")
    monkeypatch.setattr(settings, "release_sha", "abcdef1234567890")
    monkeypatch.setattr(settings, "render_service_name", "crmcatkapinda-v2-api")
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
    assert payload["core_ready"] is True
    assert payload["commit_sha"] == "abcdef1234567890"
    assert payload["release_label"] == "abcdef1"
    assert payload["auth"]["email_login"] is True
    assert payload["auth"]["phone_login"] is True
    assert payload["auth"]["sms_login"] is True
    assert payload["auth"]["sms_allowlist_count"] == 1
    assert payload["auth"]["admin_user_count"] == 3
    assert payload["auth"]["mobile_ops_user_count"] == 2
    assert payload["auth"]["default_password_configured"] is False
    assert payload["cutover"]["phase"] == "not_ready"
    assert payload["cutover"]["ready"] is False
    assert payload["decision"]["tone"] == "warning"
    assert payload["decision"]["primary_href"] == "#deploy-readiness"
    assert payload["cutover"]["modules_ready_count"] == len(payload["modules"])
    assert any("Varsayilan v2 sifresi" in item for item in payload["cutover"]["blocking_items"])
    assert any(entry["service"] == "backend" for entry in payload["config"])
    assert len(payload["pilot_accounts"]) == 3
    assert payload["pilot_accounts"][0]["email"] == "ebru@catkapinda.com"
    assert payload["pilot_flow"][0]["href"] == "/login"
    assert any(step["href"] == "/attendance" for step in payload["pilot_flow"])
    assert len(payload["pilot_scenarios"]) == 5
    assert payload["pilot_scenarios"][0]["href"] == "/"
    assert any(step["href"] == "/attendance" for step in payload["pilot_scenarios"])
    assert any("hakedis" in step["success_hint"].lower() or "finans" in step["success_hint"].lower() for step in payload["pilot_scenarios"])
    assert payload["deploy_steps"][0]["title"].startswith("1. Render'da blueprint")
    assert payload["deploy_steps"][1]["service_name"] == "crmcatkapinda-v2-api"
    assert payload["deploy_steps"][5]["service_name"] == "crmcatkapinda"
    assert payload["rollout_steps"][0]["service_name"] == "crmcatkapinda-v2-api"
    assert payload["rollout_steps"][3]["service_name"] == "crmcatkapinda"
    assert "CK_V2_PILOT_URL" in payload["rollout_steps"][3]["env_keys"]
    assert payload["pilot_links"][0]["href"] == "https://pilot.example.com/login"
    assert any(link["href"] == "https://pilot.example.com/api/pilot-status" for link in payload["pilot_links"])
    assert payload["smoke_commands"][0]["command"] == "python v2/scripts/pilot_smoke.py --base-url https://pilot.example.com"
    assert "--identity ebru@catkapinda.com" in payload["smoke_commands"][1]["command"]
    assert "--json --output pilot-report.json" in payload["smoke_commands"][2]["command"]
    assert "--markdown --output pilot-report.md" in payload["smoke_commands"][3]["command"]
    assert "--legacy-cutover-mode banner" in payload["smoke_commands"][4]["command"]
    assert "--legacy-cutover-mode redirect" in payload["smoke_commands"][5]["command"]
    assert "--preset pilot" in payload["smoke_commands"][6]["command"]
    assert "--preset cutover" in payload["smoke_commands"][7]["command"]
    helper_map = {entry["label"]: entry for entry in payload["helper_commands"]}
    assert helper_map["Render Env Bundle"]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com"
    )
    assert helper_map["Render Env Bundle"]["category"] == "env"
    assert helper_map["Render Env Bundle JSON"]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com --json"
    )
    assert helper_map["Streamlit Banner Env"]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com "
        "--service streamlit --cutover-mode banner"
    )
    assert helper_map["Streamlit Redirect Env"]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com "
        "--service streamlit --cutover-mode redirect"
    )
    assert helper_map["Guarded Banner Env"]["command"] == (
        "python v2/scripts/pilot_cutover_guard.py "
        "--base-url https://pilot.example.com --mode banner"
    )
    assert helper_map["Guarded Banner Env"]["category"] == "env"
    assert helper_map["Guarded Redirect Env"]["command"] == (
        "python v2/scripts/pilot_cutover_guard.py "
        "--base-url https://pilot.example.com --mode redirect"
    )
    assert helper_map["Guarded Redirect Env"]["category"] == "env"
    assert helper_map["API Env"]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com --service api"
    )
    assert helper_map["Frontend Env"]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com --service frontend"
    )
    assert helper_map["Pilot Launch Packet"]["command"] == (
        "python v2/scripts/pilot_launch_packet.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com --output pilot-launch.md"
    )
    assert helper_map["Pilot Launch Packet"]["category"] == "packet"
    assert helper_map["Pilot Cutover Packet"]["command"] == (
        "python v2/scripts/pilot_launch_packet.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com "
        "--cutover-mode redirect --output pilot-cutover.md"
    )
    assert helper_map["Pilot Cutover Packet"]["category"] == "packet"
    assert helper_map["Live Pilot Status Report"]["command"] == (
        "python v2/scripts/pilot_status_report.py "
        "--base-url https://pilot.example.com --output pilot-status-live.md"
    )
    assert helper_map["Live Pilot Status Report"]["category"] == "packet"
    assert helper_map["Live Pilot Status JSON"]["command"] == (
        "python v2/scripts/pilot_status_report.py "
        "--base-url https://pilot.example.com --json --output pilot-status-live.json"
    )
    assert helper_map["Live Pilot Status JSON"]["category"] == "packet"
    assert helper_map["Pilot Preflight Bundle"]["command"] == (
        "python v2/scripts/pilot_preflight.py "
        "--base-url https://pilot.example.com --output-dir pilot-preflight --fresh-output"
    )
    assert helper_map["Pilot Preflight Bundle"]["category"] == "packet"
    assert helper_map["Pilot Preflight + Smoke"]["command"] == (
        "python v2/scripts/pilot_preflight.py "
        "--base-url https://pilot.example.com --output-dir pilot-preflight "
        "--fresh-output --include-smoke --preset pilot --strict-smoke"
    )
    assert helper_map["Pilot Preflight + Smoke"]["category"] == "packet"
    assert helper_map["Pilot Day Zero Kit"]["command"] == (
        "python v2/scripts/pilot_day_zero.py "
        "--base-url https://pilot.example.com --api-url https://pilot-api.example.com --output-dir pilot-day-zero "
        "--fresh-output --strict"
    )
    assert helper_map["Pilot Day Zero Kit"]["category"] == "packet"
    assert helper_map["Pilot Day Zero + Smoke"]["command"] == (
        "python v2/scripts/pilot_day_zero.py "
        "--base-url https://pilot.example.com --api-url https://pilot-api.example.com --output-dir pilot-day-zero "
        "--fresh-output --include-smoke --smoke-preset pilot --strict --strict-smoke"
    )
    assert helper_map["Pilot Day Zero + Smoke"]["category"] == "packet"
    assert helper_map["Pilot Day Zero Verify"]["command"] == (
        "python v2/scripts/pilot_day_zero_verify.py --output-dir pilot-day-zero"
    )
    assert helper_map["Pilot Day Zero Verify"]["category"] == "quick-check"
    assert helper_map["Pilot Gate Check"]["command"] == (
        "python v2/scripts/pilot_gate.py "
        "--base-url https://pilot.example.com --mode pilot"
    )
    assert helper_map["Pilot Gate Check"]["category"] == "quick-check"
    assert helper_map["Cutover Gate Check"]["command"] == (
        "python v2/scripts/pilot_gate.py "
        "--base-url https://pilot.example.com --mode cutover"
    )
    assert helper_map["Frontend Health Curl"]["command"] == "curl -fsSL https://pilot.example.com/api/health"
    assert helper_map["Frontend Ready Curl"]["command"] == "curl -fsSL https://pilot.example.com/api/ready"
    assert helper_map["Backend Health Curl"]["command"] == "curl -fsSL https://pilot-api.example.com/api/health"
    assert helper_map["Backend Pilot Curl"]["command"] == "curl -fsSL https://pilot-api.example.com/api/health/pilot"
    assert payload["command_pack"][0]["title"] == "1. Env bloklarini hazirla"
    assert payload["command_pack"][0]["command"] == (
        "python v2/scripts/render_env_bundle.py "
        "--frontend-url https://pilot.example.com --api-url https://pilot-api.example.com"
    )
    assert payload["command_pack"][1]["command"] == "curl -fsSL https://pilot.example.com/api/health"
    assert payload["command_pack"][2]["command"] == "curl -fsSL https://pilot-api.example.com/api/health/pilot"
    assert payload["command_pack"][3]["command"] == (
        "python v2/scripts/pilot_smoke.py --base-url https://pilot.example.com --preset pilot"
    )
    assert payload["command_pack"][4]["command"] == (
        "python v2/scripts/pilot_gate.py --base-url https://pilot.example.com --mode pilot"
    )
    assert "--identity ebru@catkapinda.com --password <sifre>" in payload["command_pack"][5]["command"]
    assert payload["command_pack"][6]["command"] == (
        "python v2/scripts/pilot_day_zero.py "
        "--base-url https://pilot.example.com --api-url https://pilot-api.example.com --output-dir pilot-day-zero "
        "--fresh-output --strict"
    )
    assert payload["command_pack"][7]["command"] == (
        "python v2/scripts/pilot_cutover_guard.py --base-url https://pilot.example.com --mode banner"
    )
    assert payload["command_pack"][8]["command"] == "python v2/scripts/pilot_day_zero_verify.py --output-dir pilot-day-zero"
    assert payload["services"][0]["name"] == "crmcatkapinda-v2"
    assert payload["services"][0]["service_type"] == "frontend"
    assert payload["services"][0]["public_url"] == "https://pilot.example.com"
    assert payload["services"][1]["name"] == "crmcatkapinda-v2-api"
    assert payload["services"][1]["service_type"] == "backend"
    assert payload["services"][1]["public_url"] == "https://pilot-api.example.com"
    assert "config" in payload
    assert "missing_env_vars" in payload
    assert "required_missing_env_vars" in payload
    assert "optional_missing_env_vars" in payload
    assert "next_actions" in payload
    assert isinstance(payload["config"], list)
    assert isinstance(payload["missing_env_vars"], list)
    assert isinstance(payload["required_missing_env_vars"], list)
    assert isinstance(payload["optional_missing_env_vars"], list)
    assert isinstance(payload["next_actions"], list)
    assert isinstance(payload["pilot_links"], list)
    assert isinstance(payload["smoke_commands"], list)
    assert isinstance(payload["helper_commands"], list)
    assert isinstance(payload["command_pack"], list)
    assert isinstance(payload["services"], list)
    assert isinstance(payload["env_snippets"], list)
    snippet_map = {entry["service_name"]: entry for entry in payload["env_snippets"]}
    assert "CK_V2_APP_ENV=production" in snippet_map["crmcatkapinda-v2-api"]["body"]
    assert "CK_V2_RENDER_SERVICE_NAME=crmcatkapinda-v2-api" in snippet_map["crmcatkapinda-v2-api"]["body"]
    assert "CK_V2_API_PUBLIC_URL=https://pilot-api.example.com" in snippet_map["crmcatkapinda-v2-api"]["body"]
    assert "CK_V2_FRONTEND_SERVICE_NAME=crmcatkapinda-v2" in snippet_map["crmcatkapinda-v2"]["body"]
    assert "NEXT_PUBLIC_V2_API_BASE_URL=/v2-api" in snippet_map["crmcatkapinda-v2"]["body"]
    assert "CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000" in snippet_map["local-v2-frontend"]["body"]
    assert "CK_V2_PILOT_URL=https://pilot.example.com" in snippet_map["crmcatkapinda"]["body"]
    assert "CK_V2_CUTOVER_MODE=banner" in snippet_map["crmcatkapinda"]["body"]
    modules = {entry["module"]: entry for entry in payload["modules"]}
    assert modules["overview"]["href"] == "/"
    assert modules["audit"]["href"] == "/audit"
    assert modules["audit"]["status"] == "active"
    assert modules["attendance"]["status"] == "active"
    assert "detail" in modules["attendance"]
    assert "missing_tables" in modules["attendance"]
    assert modules["reports"]["href"] == "/reports"


def test_pilot_readiness_treats_sms_as_optional_when_core_envs_exist(monkeypatch):
    reset_runtime_bootstrap_state()
    mark_runtime_bootstrap_state(ok=True, detail="Auth runtime bootstrap basarili.")
    monkeypatch.setattr("app.services.auth.sms_delivery_enabled", lambda: False)
    monkeypatch.setattr(settings, "database_url", "postgresql://pilot")
    monkeypatch.setattr(settings, "frontend_base_url", "https://pilot.example.com")
    monkeypatch.setattr(settings, "public_app_url", "")
    monkeypatch.setattr(settings, "api_public_url", "")
    monkeypatch.setattr(settings, "release_sha", None)
    monkeypatch.setattr(settings, "render_service_name", "crmcatkapinda-v2-api")
    monkeypatch.setattr(settings, "auth_ebru_phone", "")
    monkeypatch.setattr(settings, "auth_mert_phone", "")
    monkeypatch.setattr(settings, "auth_muhammed_phone", "")
    monkeypatch.setattr(settings, "default_auth_password", "gizli123")

    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_db] = lambda: HealthyConnection()
    client = TestClient(app)

    response = client.get("/api/health/pilot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["core_ready"] is True
    assert payload["commit_sha"] is None
    assert payload["release_label"] == "crmcatkapinda-v2-api"
    assert payload["required_missing_env_vars"] == []
    assert "AUTH_EBRU_PHONE" in payload["optional_missing_env_vars"]
    assert "SMS_PROVIDER" in payload["optional_missing_env_vars"]
    assert payload["auth"]["default_password_configured"] is True
    assert payload["cutover"]["phase"] == "ready_for_pilot"
    assert payload["cutover"]["ready"] is True
    assert payload["decision"]["tone"] == "info"
    assert payload["decision"]["primary_href"] == "/login"
    assert any("Opsiyonel env ayarlari" in item for item in payload["cutover"]["remaining_items"])
    assert payload["rollout_steps"][0]["status"] == "ready"


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


def test_local_setup_route_returns_doctor_snapshot(monkeypatch):
    reset_runtime_bootstrap_state()
    monkeypatch.setattr(
        "app.api.routes.health.build_local_doctor_report",
        lambda v2_root, runtime_env, **kwargs: {
            "ready": False,
            "backend_env_path": f"{v2_root}/backend/.env",
            "frontend_env_path": f"{v2_root}/frontend/.env.local",
            "backend_env_exists": False,
            "frontend_env_exists": True,
            "database_url_present": False,
            "database_url_source": None,
            "runtime_database_url_present": False,
            "runtime_database_url_source": None,
            "backend_env_database_url_present": False,
            "backend_env_database_url_source": None,
            "backend_restart_required": False,
            "backend_restart_reason": None,
            "default_auth_password_present": False,
            "default_auth_password_source": None,
            "default_auth_password_is_default": False,
            "frontend_proxy_target_present": True,
            "frontend_proxy_target": "http://127.0.0.1:8000",
            "frontend_proxy_source": "file:CK_V2_INTERNAL_API_BASE_URL",
            "current_app_seed_detected": False,
            "current_app_seed_sources": [],
            "current_app_seed_placeholders": ["workspace_secrets_template:DATABASE_URL"],
            "current_app_available_sources": [
                {
                    "label": "workspace_secrets_template",
                    "path": f"{v2_root.parent}/secrets.template.toml",
                    "kind": "streamlit_secrets",
                    "exists": True,
                }
            ],
            "missing_phone_keys": ["AUTH_EBRU_PHONE"],
            "blocking_items": ["Backend veritabani URL'i eksik."],
            "warnings": ["Varsayilan sifre acik degil."],
            "next_actions": ["python v2/scripts/local_v2_doctor.py"],
        },
    )
    client = TestClient(create_app(enable_bootstrap=False))

    response = client.get("/api/health/local-setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert payload["frontend_proxy_target"] == "http://127.0.0.1:8000"
    assert payload["current_app_seed_placeholders"] == ["workspace_secrets_template:DATABASE_URL"]
    assert payload["current_app_available_sources"][0]["exists"] is True
    assert payload["next_actions"] == ["python v2/scripts/local_v2_doctor.py"]
