"""FastAPI uygulamasının giriş noktası."""
import logging
import threading
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import close_pool, get_connection, get_pool
from app.core.migrations import run_migrations
from app.core.welcome_sms import run_welcome_sms_for_pending_bm

log = logging.getLogger(__name__)

# Supabase ücretsiz plan, DB ~7 gün hareketsiz kalınca projeyi DURAKLATIR
# (paused) → veritabanı kapanır → tüm DB çağrıları "couldn't get a connection"
# hatası verir (login, şifre sıfırlama, bordro...). Render'ın /api/health
# sağlık kontrolü DB'ye dokunmadığı için bunu önlemiyordu. Bu arka plan
# thread'i periyodik 'SELECT 1' atarak DB'yi aktif tutar → proje duraklamaz.
_DB_KEEPALIVE_INTERVAL_SEC = 6 * 60 * 60  # 6 saat


def _db_keepalive_loop() -> None:
    while True:
        time.sleep(_DB_KEEPALIVE_INTERVAL_SEC)
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            log.info("db keepalive ping ok")
        except Exception as e:  # noqa: BLE001
            log.warning("db keepalive ping failed: %s", e)


def _start_db_keepalive() -> None:
    t = threading.Thread(target=_db_keepalive_loop, name="db-keepalive", daemon=True)
    t.start()

# Application logging — config.LOG_LEVEL env'e göre seviyeyi ayarla.
# Default WARNING olduğunda `log.info(...)` mesajları (örn. payroll SMS
# özeti, NetGSM çağrısı sonucu) Render log akışında görünmez.
_settings_for_log = get_settings()
logging.basicConfig(
    level=getattr(
        logging,
        (_settings_for_log.log_level or "INFO").upper(),
        logging.INFO,
    ),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Uygulama yaşam döngüsü — başlangıçta DB pool kur, sonunda kapat."""
    # Başlangıç
    get_pool()  # Bağlantı havuzunu önceden başlat
    run_migrations()  # Eksik kolonları (idempotent) ekle
    run_welcome_sms_for_pending_bm()  # BM kullanıcılara karşılama SMS (idempotent)
    _start_db_keepalive()  # Supabase'i aktif tut → proje duraklamasın
    yield
    # Kapanış
    close_pool()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Çat Kapında CRM v3 — restoran kurye yönetim sistemi",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API route'ları
    app.include_router(api_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "version": "0.1.0", "docs": "/docs"}

    return app


app = create_app()
