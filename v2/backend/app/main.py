from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.bootstrap import ensure_runtime_bootstrap
from app.core.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_bootstrap()
    yield


def create_app(*, enable_bootstrap: bool = True) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan if enable_bootstrap else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "status": "ok",
            "message": "API çalışıyor. Sağlık için /api/health, dokümantasyon için /docs bağlantısını aç.",
            "api_prefix": settings.api_prefix,
            "health": f"{settings.api_prefix}/health",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()
