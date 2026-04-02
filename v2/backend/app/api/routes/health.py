from typing import Annotated

from fastapi import APIRouter, Depends
import psycopg

from app.core.bootstrap import get_runtime_bootstrap_state
from app.core.config import settings
from app.core.database import get_db
from app.core.sms import describe_sms_config
from app.schemas.health import (
    HealthCheckEntry,
    HealthResponse,
    PilotAuthStatus,
    PilotConfigEntry,
    PilotModuleEntry,
    PilotReadinessResponse,
    ReadinessResponse,
)
from app.services.attendance import build_attendance_status
from app.services.auth import build_auth_modes
from app.services.deductions import build_deductions_status
from app.services.equipment import build_equipment_status
from app.services.payroll import build_payroll_status
from app.services.personnel import build_personnel_status
from app.services.purchases import build_purchases_status
from app.services.reports import build_reports_status
from app.services.restaurants import build_restaurants_status
from app.services.sales import build_sales_status

router = APIRouter()

MODULE_TABLES: dict[str, tuple[str, ...]] = {
    "overview": ("restaurants", "personnel", "daily_entries"),
    "attendance": ("daily_entries", "restaurants", "personnel"),
    "personnel": (
        "personnel",
        "restaurants",
        "personnel_role_history",
        "personnel_vehicle_history",
        "plate_history",
    ),
    "deductions": ("deductions", "personnel"),
    "equipment": ("courier_equipment_issues", "box_returns", "inventory_purchases", "deductions", "personnel"),
    "payroll": ("personnel", "daily_entries", "deductions", "restaurants"),
    "purchases": ("inventory_purchases",),
    "sales": ("sales_leads",),
    "restaurants": ("restaurants", "personnel", "daily_entries", "deductions"),
    "reports": ("daily_entries", "personnel", "restaurants", "deductions"),
}


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="crmcatkapinda-v2-api",
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness(
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> ReadinessResponse:
    return _build_readiness_response(conn)


@router.get("/health/pilot", response_model=PilotReadinessResponse)
def pilot_readiness(
    conn: Annotated[psycopg.Connection, Depends(get_db)],
) -> PilotReadinessResponse:
    readiness_response = _build_readiness_response(conn)
    auth_modes = build_auth_modes()
    config_entries, missing_env_vars, next_actions = _build_pilot_config_summary()
    module_table_status = _build_module_table_status(conn)

    modules = [
        PilotModuleEntry(
            module="overview",
            label="Genel Bakış",
            status=module_table_status["overview"]["status"],
            next_slice="overview-dashboard",
            href="/",
            detail=module_table_status["overview"]["detail"],
            missing_tables=module_table_status["overview"]["missing_tables"],
        ),
        PilotModuleEntry(
            label="Puantaj",
            href="/attendance",
            detail=module_table_status["attendance"]["detail"],
            missing_tables=module_table_status["attendance"]["missing_tables"],
            **{**build_attendance_status().model_dump(), "status": module_table_status["attendance"]["status"]},
        ),
        PilotModuleEntry(
            label="Personel",
            href="/personnel",
            detail=module_table_status["personnel"]["detail"],
            missing_tables=module_table_status["personnel"]["missing_tables"],
            **{**build_personnel_status().model_dump(), "status": module_table_status["personnel"]["status"]},
        ),
        PilotModuleEntry(
            label="Kesintiler",
            href="/deductions",
            detail=module_table_status["deductions"]["detail"],
            missing_tables=module_table_status["deductions"]["missing_tables"],
            **{**build_deductions_status().model_dump(), "status": module_table_status["deductions"]["status"]},
        ),
        PilotModuleEntry(
            label="Ekipman",
            href="/equipment",
            detail=module_table_status["equipment"]["detail"],
            missing_tables=module_table_status["equipment"]["missing_tables"],
            **{**build_equipment_status().model_dump(), "status": module_table_status["equipment"]["status"]},
        ),
        PilotModuleEntry(
            label="Aylık Hakediş",
            href="/payroll",
            detail=module_table_status["payroll"]["detail"],
            missing_tables=module_table_status["payroll"]["missing_tables"],
            **{**build_payroll_status().model_dump(), "status": module_table_status["payroll"]["status"]},
        ),
        PilotModuleEntry(
            label="Satın Alma",
            href="/purchases",
            detail=module_table_status["purchases"]["detail"],
            missing_tables=module_table_status["purchases"]["missing_tables"],
            **{**build_purchases_status().model_dump(), "status": module_table_status["purchases"]["status"]},
        ),
        PilotModuleEntry(
            label="Satış",
            href="/sales",
            detail=module_table_status["sales"]["detail"],
            missing_tables=module_table_status["sales"]["missing_tables"],
            **{**build_sales_status().model_dump(), "status": module_table_status["sales"]["status"]},
        ),
        PilotModuleEntry(
            label="Restoranlar",
            href="/restaurants",
            detail=module_table_status["restaurants"]["detail"],
            missing_tables=module_table_status["restaurants"]["missing_tables"],
            **{**build_restaurants_status().model_dump(), "status": module_table_status["restaurants"]["status"]},
        ),
        PilotModuleEntry(
            label="Raporlar",
            href="/reports",
            detail=module_table_status["reports"]["detail"],
            missing_tables=module_table_status["reports"]["missing_tables"],
            **{**build_reports_status().model_dump(), "status": module_table_status["reports"]["status"]},
        ),
    ]

    overall_ok = readiness_response.status == "ok" and all(entry.status == "active" for entry in modules)
    return PilotReadinessResponse(
        status="ok" if overall_ok else "degraded",
        service=readiness_response.service,
        version=readiness_response.version,
        environment=readiness_response.environment,
        checks=readiness_response.checks,
        auth=PilotAuthStatus(
            email_login=auth_modes.email_login,
            phone_login=auth_modes.phone_login,
            sms_login=auth_modes.sms_login,
            sms_allowlist_count=len(settings.sms_phone_allowlist),
        ),
        config=config_entries,
        missing_env_vars=missing_env_vars,
        next_actions=next_actions,
        modules=modules,
    )


def _build_readiness_response(conn: psycopg.Connection) -> ReadinessResponse:
    checks: list[HealthCheckEntry] = []
    bootstrap_state = get_runtime_bootstrap_state()

    checks.append(
        HealthCheckEntry(
            name="database_url",
            ok=bool(settings.database_url),
            detail="DATABASE_URL tanimli" if settings.database_url else "DATABASE_URL eksik",
        )
    )

    checks.append(
        HealthCheckEntry(
            name="runtime_bootstrap",
            ok=bootstrap_state["ok"] is not False,
            detail=str(bootstrap_state["detail"] or ""),
        )
    )

    checks.append(
        HealthCheckEntry(
            name="frontend_base_url",
            ok=bool(settings.frontend_base_url),
            detail=settings.frontend_base_url or "Frontend URL eksik",
        )
    )

    checks.append(
        HealthCheckEntry(
            name="public_app_url",
            ok=bool(settings.public_app_url),
            detail=settings.public_app_url or "Public app URL eksik",
        )
    )

    sms_configured = bool(settings.sms_phone_allowlist) and bool(settings.frontend_base_url)
    checks.append(
        HealthCheckEntry(
            name="sms_allowlist",
            ok=bool(settings.sms_phone_allowlist),
            detail=f"{len(settings.sms_phone_allowlist)} izinli telefon",
        )
    )
    checks.append(
        HealthCheckEntry(
            name="sms_flow",
            ok=sms_configured,
            detail="SMS giriş temel ayarları hazır" if sms_configured else "SMS giriş için allowlist eksik olabilir",
        )
    )

    db_ok = False
    db_detail = None
    try:
        conn.execute("SELECT 1")
        db_ok = True
        db_detail = "Veritabanı erişimi başarılı"
    except Exception as exc:  # pragma: no cover - defensive for runtime-only failures
        db_detail = str(exc)

    checks.append(
        HealthCheckEntry(
            name="database_reachable",
            ok=db_ok,
            detail=db_detail,
        )
    )

    overall = "ok" if all(check.ok for check in checks) else "degraded"
    return ReadinessResponse(
        status=overall,
        service="crmcatkapinda-v2-api",
        version=settings.app_version,
        environment=settings.app_env,
        checks=checks,
    )


def _build_pilot_config_summary() -> tuple[list[PilotConfigEntry], list[str], list[str]]:
    sms_setup = describe_sms_config()
    config_entries: list[PilotConfigEntry] = [
        PilotConfigEntry(
            name="database",
            ok=bool(settings.database_url),
            detail="Veritabanı URL tanımlı" if settings.database_url else "CK_V2_DATABASE_URL veya DATABASE_URL eksik",
            missing_envs=[] if settings.database_url else ["CK_V2_DATABASE_URL"],
        ),
        PilotConfigEntry(
            name="frontend_base_url",
            ok=bool(settings.frontend_base_url),
            detail=settings.frontend_base_url or "CK_V2_FRONTEND_BASE_URL eksik",
            missing_envs=[] if settings.frontend_base_url else ["CK_V2_FRONTEND_BASE_URL"],
        ),
        PilotConfigEntry(
            name="public_app_url",
            ok=bool(settings.public_app_url),
            detail=settings.public_app_url or "CK_V2_PUBLIC_APP_URL eksik",
            missing_envs=[] if settings.public_app_url else ["CK_V2_PUBLIC_APP_URL"],
        ),
        PilotConfigEntry(
            name="sms_allowlist",
            ok=bool(settings.sms_phone_allowlist),
            detail=f"{len(settings.sms_phone_allowlist)} izinli telefon",
            missing_envs=(
                []
                if settings.sms_phone_allowlist
                else ["AUTH_EBRU_PHONE", "AUTH_MERT_PHONE", "AUTH_MUHAMMED_PHONE"]
            ),
        ),
        PilotConfigEntry(
            name="sms_provider",
            ok=bool(sms_setup["configured"]),
            detail=(
                f"{sms_setup['provider']} hazır"
                if sms_setup["configured"]
                else (sms_setup["provider"] or "SMS sağlayıcısı ayarsız")
            ),
            missing_envs=list(sms_setup["missing_envs"]),
        ),
    ]

    missing_env_vars: list[str] = []
    for entry in config_entries:
        for env_name in entry.missing_envs:
            if env_name not in missing_env_vars:
                missing_env_vars.append(env_name)

    next_actions: list[str] = []
    if any(name in missing_env_vars for name in {"CK_V2_DATABASE_URL"}):
        next_actions.append("Backend servisine veritabanı URL'sini gir.")
    if any(name in missing_env_vars for name in {"CK_V2_FRONTEND_BASE_URL", "CK_V2_PUBLIC_APP_URL"}):
        next_actions.append("Backend frontend/public URL ayarlarını pilot domain ile eşleştir.")
    if any(name in missing_env_vars for name in {"AUTH_EBRU_PHONE", "AUTH_MERT_PHONE", "AUTH_MUHAMMED_PHONE"}):
        next_actions.append("SMS giriş için yönetici telefon allowlist değerlerini gir.")
    if sms_setup["missing_envs"]:
        next_actions.append("NetGSM/SMS environment değişkenlerini tamamla.")
    if not next_actions:
        next_actions.append("Pilot açılışı için zorunlu environment ayarları tamam.")

    return config_entries, missing_env_vars, next_actions


def _build_module_table_status(conn: psycopg.Connection) -> dict[str, dict[str, object]]:
    status_map: dict[str, dict[str, object]] = {}
    for module, tables in MODULE_TABLES.items():
        missing_tables: list[str] = []
        for table_name in tables:
            row = conn.execute("SELECT to_regclass(%s) AS table_name", (f"public.{table_name}",)).fetchone()
            if not row or not row.get("table_name"):
                missing_tables.append(table_name)

        status_map[module] = {
            "status": "active" if not missing_tables else "degraded",
            "detail": (
                f"{len(tables) - len(missing_tables)}/{len(tables)} temel tablo hazır"
                if not missing_tables
                else f"Eksik tablolar: {', '.join(missing_tables)}"
            ),
            "missing_tables": missing_tables,
        }
    return status_map
