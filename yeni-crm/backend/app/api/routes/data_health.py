"""Sistem Veri Sağlığı endpoint."""
import logging

from fastapi import APIRouter, HTTPException

from app.services.data_health import run_data_health_check

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("")
async def get_data_health(period: str = "2026-03") -> dict:
    """10 sanity check çalıştır — green/yellow/red liste döner.

    Kontroller:
    1. Tarife geçmişi (pricing_history) coverage
    2. Aktif restoranların tarife alanları dolu mu
    3. Period: puantaj var ama fatura 0 olan restoranlar
    4. Period: marj sağlık aralığı (%0–%60)
    5. Period: paket başı maliyet (10–60 ₺)
    6. Period: orphan entries (restoran/kurye eşleşmesiz)
    7. Period: çalışmış ama brüt 0 kuryeler
    8. Aktif restoran ama atanmış kurye yok
    9. Status Aktif ama exit_date geçmiş
    10. Quick China + Doğu Otomotiv courier override
    """
    try:
        return run_data_health_check(period)
    except Exception as e:
        log.exception("/api/data-health failed: %s", e)
        raise HTTPException(500, detail=f"data-health failed: {type(e).__name__}: {e}") from e
