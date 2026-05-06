"""FastAPI uygulamasının giriş noktası."""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import close_pool, get_pool
from app.core.migrations import run_migrations

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
