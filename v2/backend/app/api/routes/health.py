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
    PilotAccountEntry,
    PilotAuthStatus,
    PilotConfigEntry,
    PilotCutoverSummary,
    PilotFlowStep,
    PilotLinkEntry,
    PilotModuleEntry,
    PilotReadinessResponse,
    PilotSmokeCommand,
    ReadinessResponse,
)
from app.services.attendance import build_attendance_status
from app.services.audit import build_audit_status
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
    "audit": ("audit_logs",),
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
    admin_user_count, mobile_ops_user_count = _build_auth_user_counts(conn)
    (
        config_entries,
        required_missing_env_vars,
        optional_missing_env_vars,
        next_actions,
    ) = _build_pilot_config_summary()
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
            label="Sistem Kayıtları",
            href="/audit",
            detail=module_table_status["audit"]["detail"],
            missing_tables=module_table_status["audit"]["missing_tables"],
            **{**build_audit_status().model_dump(), "status": module_table_status["audit"]["status"]},
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

    all_modules_active = all(entry.status == "active" for entry in modules)
    core_ready = readiness_response.status == "ok" and not required_missing_env_vars
    auth_ready = (
        auth_modes.email_login
        and admin_user_count > 0
        and settings.default_auth_password != "123456"
    )
    overall_ok = core_ready and all_modules_active
    cutover = _build_cutover_summary(
        core_ready=core_ready,
        auth_ready=auth_ready,
        phone_login_ready=auth_modes.phone_login,
        mobile_ops_user_count=mobile_ops_user_count,
        modules=modules,
        required_missing_env_vars=required_missing_env_vars,
        optional_missing_env_vars=optional_missing_env_vars,
        default_password_configured=settings.default_auth_password != "123456",
    )
    pilot_accounts = _build_pilot_accounts()
    pilot_flow = _build_pilot_flow()
    pilot_links = _build_pilot_links()
    smoke_commands = _build_smoke_commands()
    return PilotReadinessResponse(
        status="ok" if overall_ok else "degraded",
        core_ready=core_ready,
        service=readiness_response.service,
        version=readiness_response.version,
        environment=readiness_response.environment,
        checks=readiness_response.checks,
        auth=PilotAuthStatus(
            email_login=auth_modes.email_login,
            phone_login=auth_modes.phone_login,
            sms_login=auth_modes.sms_login,
            sms_allowlist_count=len(settings.sms_phone_allowlist),
            admin_user_count=admin_user_count,
            mobile_ops_user_count=mobile_ops_user_count,
            default_password_configured=settings.default_auth_password != "123456",
        ),
        config=config_entries,
        missing_env_vars=[*required_missing_env_vars, *optional_missing_env_vars],
        required_missing_env_vars=required_missing_env_vars,
        optional_missing_env_vars=optional_missing_env_vars,
        next_actions=next_actions,
        modules=modules,
        cutover=cutover,
        pilot_accounts=pilot_accounts,
        pilot_flow=pilot_flow,
        pilot_links=pilot_links,
        smoke_commands=smoke_commands,
    )


def _build_readiness_response(conn: psycopg.Connection) -> ReadinessResponse:
    checks: list[HealthCheckEntry] = []
    bootstrap_state = get_runtime_bootstrap_state()
    has_any_frontend_url = bool(settings.frontend_base_url or settings.public_app_url)

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
            ok=has_any_frontend_url,
            detail=settings.resolved_frontend_base_url if has_any_frontend_url else "Frontend URL eksik",
        )
    )

    checks.append(
        HealthCheckEntry(
            name="public_app_url",
            ok=has_any_frontend_url,
            detail=settings.resolved_public_app_url if has_any_frontend_url else "Public app URL eksik",
        )
    )

    sms_setup = describe_sms_config()
    sms_configured = bool(settings.sms_phone_allowlist) and bool(sms_setup["configured"])
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
            detail="SMS giriş temel ayarları hazır" if sms_configured else "SMS giriş pilot için opsiyonel durumda",
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

    optional_check_names = {"sms_allowlist", "sms_flow"}
    overall = "ok" if all(check.ok for check in checks if check.name not in optional_check_names) else "degraded"
    return ReadinessResponse(
        status=overall,
        service="crmcatkapinda-v2-api",
        version=settings.app_version,
        environment=settings.app_env,
        checks=checks,
    )


def _build_pilot_config_summary() -> tuple[list[PilotConfigEntry], list[str], list[str], list[str]]:
    sms_setup = describe_sms_config()
    has_any_frontend_url = bool(settings.frontend_base_url or settings.public_app_url)
    config_entries: list[PilotConfigEntry] = [
        PilotConfigEntry(
            name="database",
            service="backend",
            ok=bool(settings.database_url),
            required=True,
            detail="Veritabanı URL tanımlı" if settings.database_url else "CK_V2_DATABASE_URL veya DATABASE_URL eksik",
            missing_envs=[] if settings.database_url else ["CK_V2_DATABASE_URL"],
        ),
        PilotConfigEntry(
            name="frontend_base_url",
            service="backend",
            ok=has_any_frontend_url,
            required=True,
            detail=settings.resolved_frontend_base_url if has_any_frontend_url else "CK_V2_FRONTEND_BASE_URL veya CK_V2_PUBLIC_APP_URL eksik",
            missing_envs=[] if has_any_frontend_url else ["CK_V2_FRONTEND_BASE_URL", "CK_V2_PUBLIC_APP_URL"],
        ),
        PilotConfigEntry(
            name="public_app_url",
            service="backend",
            ok=has_any_frontend_url,
            required=False,
            detail=settings.resolved_public_app_url if has_any_frontend_url else "Public app URL pilot sonrasi da eklenebilir",
            missing_envs=[] if has_any_frontend_url else ["CK_V2_PUBLIC_APP_URL"],
        ),
        PilotConfigEntry(
            name="sms_allowlist",
            service="backend",
            required=False,
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
            service="backend",
            required=False,
            ok=bool(sms_setup["configured"]),
            detail=(
                f"{sms_setup['provider']} hazır"
                if sms_setup["configured"]
                else (sms_setup["provider"] or "SMS sağlayıcısı ayarsız")
            ),
            missing_envs=list(sms_setup["missing_envs"]),
        ),
        PilotConfigEntry(
            name="default_auth_password",
            service="backend",
            required=False,
            ok=settings.default_auth_password != "123456",
            detail=(
                "Varsayilan sifre degistirilmis"
                if settings.default_auth_password != "123456"
                else "Pilot oncesi varsayilan v2 sifresini degistirmen onerilir"
            ),
            missing_envs=[] if settings.default_auth_password != "123456" else ["CK_V2_DEFAULT_AUTH_PASSWORD"],
        ),
    ]

    required_missing_env_vars: list[str] = []
    optional_missing_env_vars: list[str] = []
    for entry in config_entries:
        for env_name in entry.missing_envs:
            target = required_missing_env_vars if entry.required else optional_missing_env_vars
            if env_name not in target:
                target.append(env_name)

    next_actions: list[str] = []
    if any(name in required_missing_env_vars for name in {"CK_V2_DATABASE_URL"}):
        next_actions.append("Backend servisine veritabanı URL'sini gir.")
    if any(name in required_missing_env_vars for name in {"CK_V2_FRONTEND_BASE_URL", "CK_V2_PUBLIC_APP_URL"}):
        next_actions.append("Backend tarafinda en az bir pilot uygulama URL'si tanimla.")
    if any(name in optional_missing_env_vars for name in {"AUTH_EBRU_PHONE", "AUTH_MERT_PHONE", "AUTH_MUHAMMED_PHONE"}):
        next_actions.append("SMS login acilacaksa yonetici telefon allowlist degerlerini gir.")
    if sms_setup["missing_envs"]:
        next_actions.append("SMS login istenecekse NetGSM/SMS environment degiskenlerini tamamla.")
    if settings.default_auth_password == "123456":
        next_actions.append("Pilot oncesi varsayilan v2 sifresini degistir.")
    if not next_actions:
        next_actions.append("Pilot acilisi icin zorunlu environment ayarlari tamam.")

    return config_entries, required_missing_env_vars, optional_missing_env_vars, next_actions


def _build_auth_user_counts(conn: psycopg.Connection) -> tuple[int, int]:
    try:
        admin_row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM auth_users
            WHERE role = %s
              AND is_active = 1
            """,
            ("admin",),
        ).fetchone()
        mobile_row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM auth_users
            WHERE role = %s
              AND is_active = 1
            """,
            ("mobile_ops",),
        ).fetchone()
        return (
            int((admin_row or {}).get("count") or 0),
            int((mobile_row or {}).get("count") or 0),
        )
    except Exception:  # pragma: no cover - defensive runtime fallback
        return (0, 0)


def _build_pilot_accounts() -> list[PilotAccountEntry]:
    accounts: list[PilotAccountEntry] = []
    for user in settings.default_auth_users:
        accounts.append(
            PilotAccountEntry(
                email=user["email"],
                full_name=user["full_name"],
                role=user["role_display"],
                has_phone=bool("".join(ch for ch in str(user.get("phone") or "") if ch.isdigit())),
            )
        )
    return accounts


def _build_pilot_flow() -> list[PilotFlowStep]:
    return [
        PilotFlowStep(
            title="1. Giriş ekranını doğrula",
            detail="Önce e-posta/şifre ile giriş yap. SMS env tamamlandıysa telefon kodu akışını da ayrıca dene.",
            href="/login",
        ),
        PilotFlowStep(
            title="2. Puantaj kaydı oluştur",
            detail="Günlük puantajdan bir kayıt ekle, ardından kayıt yönetiminden düzenleme ve silme akışını kontrol et.",
            href="/attendance",
        ),
        PilotFlowStep(
            title="3. Personel ve kesinti akışını kontrol et",
            detail="Personel kartı güncelle, ardından kesinti girişinin kaydedildiğini ve listede göründüğünü doğrula.",
            href="/personnel",
        ),
        PilotFlowStep(
            title="4. Finans yüzeylerini gözden geçir",
            detail="Aylık hakediş ve raporlar ekranında özet kartlar ile tabloların beklendiği gibi açıldığını doğrula.",
            href="/reports",
        ),
    ]


def _build_pilot_links() -> list[PilotLinkEntry]:
    base_url = settings.resolved_public_app_url.rstrip("/")
    return [
        PilotLinkEntry(label="Pilot Login", href=f"{base_url}/login"),
        PilotLinkEntry(label="Pilot Dashboard", href=f"{base_url}/"),
        PilotLinkEntry(label="Pilot Status", href=f"{base_url}/status"),
        PilotLinkEntry(label="Pilot Puantaj", href=f"{base_url}/attendance"),
    ]


def _build_smoke_commands() -> list[PilotSmokeCommand]:
    base_url = settings.resolved_public_app_url.rstrip("/")
    return [
        PilotSmokeCommand(
            label="Normal Smoke",
            command=f"python v2/scripts/pilot_smoke.py --base-url {base_url}",
        ),
        PilotSmokeCommand(
            label="Gercek Login Smoke",
            command=(
                f"python v2/scripts/pilot_smoke.py --base-url {base_url} "
                "--identity ebru@catkapinda.com --password <sifre>"
            ),
        ),
    ]


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


def _build_cutover_summary(
    *,
    core_ready: bool,
    auth_ready: bool,
    phone_login_ready: bool,
    mobile_ops_user_count: int,
    modules: list[PilotModuleEntry],
    required_missing_env_vars: list[str],
    optional_missing_env_vars: list[str],
    default_password_configured: bool,
) -> PilotCutoverSummary:
    modules_total_count = len(modules)
    modules_ready_count = sum(1 for module in modules if module.status == "active")
    all_modules_active = modules_ready_count == modules_total_count and modules_total_count > 0

    blocking_items: list[str] = []
    remaining_items: list[str] = []

    if not core_ready:
        if required_missing_env_vars:
            blocking_items.append("Zorunlu deploy environment ayarlari tamamlanmamis.")
        else:
            blocking_items.append("Backend veya veritabani readiness kontrolleri gecemiyor.")

    if not auth_ready:
        if not default_password_configured:
            blocking_items.append("Varsayilan v2 sifresi pilot oncesi degistirilmeli.")
        else:
            blocking_items.append("En az bir aktif admin hesabiyla giris akisi dogrulanmali.")

    if not all_modules_active:
        blocking_items.append(f"{modules_total_count - modules_ready_count} modul hala eksik veya degrade durumda.")

    if mobile_ops_user_count <= 0:
        remaining_items.append("Mobil operasyon kullanicilari senkronlanmali.")
    elif not phone_login_ready:
        remaining_items.append("Telefonla giris akisi mobil operasyon icin acilmali.")

    if optional_missing_env_vars:
        remaining_items.append("Opsiyonel env ayarlari tamamlanirsa SMS ve gecis akislari guclenir.")

    if blocking_items:
        phase = "not_ready"
        ready = False
        summary = "Streamlit'ten cikis icin once ana blokajlar kapanmali."
    elif remaining_items:
        phase = "ready_for_pilot"
        ready = True
        summary = "Pilot acilabilir; son opsiyonel maddeler kontrollu sekilde tamamlanabilir."
    else:
        phase = "ready_for_cutover"
        ready = True
        summary = "Yeni sistem pilot ve kontrollu cutover icin hazir gorunuyor."

    return PilotCutoverSummary(
        phase=phase,
        ready=ready,
        summary=summary,
        core_checks_ready=core_ready,
        auth_ready=auth_ready,
        modules_ready_count=modules_ready_count,
        modules_total_count=modules_total_count,
        blocking_items=blocking_items,
        remaining_items=remaining_items,
    )
