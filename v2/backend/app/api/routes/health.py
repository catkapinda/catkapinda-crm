from typing import Annotated

from fastapi import APIRouter, Depends
import psycopg

from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthCheckEntry, HealthResponse, ReadinessResponse

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
