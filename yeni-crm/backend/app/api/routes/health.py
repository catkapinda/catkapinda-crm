"""Sağlık kontrolü — Render & yük dengeleyici için."""
from fastapi import APIRouter

from app.core.database import get_connection

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    """Basit sağlık kontrolü."""
    return {"status": "ok", "service": "catkapinda-crm-backend"}


@router.get("/db")
async def db_health() -> dict[str, str]:
    """Veritabanı bağlantı kontrolü."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}
