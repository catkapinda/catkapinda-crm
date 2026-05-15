"""Restoran Raporları endpoint'leri."""
from fastapi import APIRouter, HTTPException

from app.services.ai_insights import get_or_generate as get_or_generate_ai
from app.services.restaurant_reports import get_restaurant_reports

router = APIRouter()


@router.get("")
async def get_reports(period: str = "2026-03") -> dict:
    """Tüm restoran raporlarını getir (turnover, efficiency, cost, growth).

    Query params:
    - period: "YYYY-MM" (default: "2026-03")

    Returns:
    {
        "period": "2026-03",
        "previous_period": "2026-02",
        "turnover": [...],
        "courier_efficiency": [...],
        "cost_per_package": {...},
        "package_growth": [...]
    }
    """
    return get_restaurant_reports(period)


@router.get("/ai-insights")
async def get_ai_insights(period: str = "2026-03", force: bool = False) -> dict:
    """Restoran raporları için Claude AI özet — 4 kart + headline + actions.

    Cache: 48 saat TTL (ai_insights_cache scope='restoran').
    force=true: cache by-pass, taze Claude çağrısı.

    Hata durumunda 503; frontend deterministik fallback gösterir.
    """
    try:
        return get_or_generate_ai(period=period, force=force, scope="restoran")
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_unavailable",
                "message": str(e),
            },
        ) from e
