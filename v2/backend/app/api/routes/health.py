from typing import Annotated

from fastapi import APIRouter, Depends
import psycopg

from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import (
    HealthCheckEntry,
    HealthResponse,
    PilotAuthStatus,
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

    modules = [
        PilotModuleEntry(
            module="overview",
            label="Genel Bakış",
            status="active",
            next_slice="overview-dashboard",
            href="/",
        ),
        PilotModuleEntry(label="Puantaj", href="/attendance", **build_attendance_status().model_dump()),
        PilotModuleEntry(label="Personel", href="/personnel", **build_personnel_status().model_dump()),
        PilotModuleEntry(label="Kesintiler", href="/deductions", **build_deductions_status().model_dump()),
        PilotModuleEntry(label="Ekipman", href="/equipment", **build_equipment_status().model_dump()),
        PilotModuleEntry(label="Aylık Hakediş", href="/payroll", **build_payroll_status().model_dump()),
        PilotModuleEntry(label="Satın Alma", href="/purchases", **build_purchases_status().model_dump()),
        PilotModuleEntry(label="Satış", href="/sales", **build_sales_status().model_dump()),
        PilotModuleEntry(label="Restoranlar", href="/restaurants", **build_restaurants_status().model_dump()),
        PilotModuleEntry(label="Raporlar", href="/reports", **build_reports_status().model_dump()),
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
        modules=modules,
    )


def _build_readiness_response(conn: psycopg.Connection) -> ReadinessResponse:
    checks: list[HealthCheckEntry] = []

    checks.append(
        HealthCheckEntry(
            name="database_url",
            ok=bool(settings.database_url),
            detail="DATABASE_URL tanimli" if settings.database_url else "DATABASE_URL eksik",
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
