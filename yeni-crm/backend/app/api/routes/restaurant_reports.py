"""Restoran Raporları endpoint'leri."""
import logging

from fastapi import APIRouter, HTTPException, Response

from app.services.ai_insights import (
    generate_restaurant_commentary,
    get_or_generate as get_or_generate_ai,
)
from app.services.restaurant_report_pdf import generate_restaurant_report_pdf
from app.services.restaurant_reports import get_restaurant_reports
from app.services.restaurants import get_restaurant

log = logging.getLogger(__name__)

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


@router.get("/{restaurant_id}/pdf")
async def get_restaurant_report_pdf(
    restaurant_id: int,
    period: str = "2026-03",
    skip_ai: bool = False,
) -> Response:
    """Tek restoran için premium performans raporu (PDF).

    Query params:
    - period: "YYYY-MM"
    - skip_ai: true → AI yorumu üretme (hızlı preview için).
               Varsayılan false: Claude'dan derin yorum çek.

    Response: application/pdf
    """
    restaurant = get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(404, detail="Restoran bulunamadı.")

    reports = get_restaurant_reports(period)

    commentary = None
    if not skip_ai:
        try:
            commentary = generate_restaurant_commentary(
                restaurant, period, reports=reports,
            )
        except Exception as e:
            # AI başarısız olsa bile PDF üretmeye devam et
            log.warning("restaurant pdf: commentary üretilemedi: %s", e)
            commentary = None

    try:
        pdf_bytes = generate_restaurant_report_pdf(
            restaurant=restaurant,
            period=period,
            reports=reports,
            commentary=commentary,
        )
    except Exception as e:
        log.exception("restaurant pdf üretilemedi: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_generation_failed",
                "message": str(e),
            },
        ) from e

    # Filename: ASCII-safe ve tireli (HTTP header Latin-1 olmalı)
    raw_brand = (restaurant.get("brand") or "rapor")
    safe_brand = "".join(
        c if c.isalnum() else "_" for c in raw_brand.encode("ascii", "ignore").decode("ascii")
    ) or "rapor"
    filename = f"performans_{safe_brand}_{period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
