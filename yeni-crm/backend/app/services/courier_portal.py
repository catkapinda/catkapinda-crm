"""Kurye portal servisleri — bordro, talepler.

Mevcut servisleri sarmallar (payroll, requests) ve kurye-spesifik
filtreleme yapar.
"""
from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.payroll import get_personnel_payroll
from app.services.requests import list_requests, create_request


def get_my_bordro(personnel_id: int, period: str) -> dict:
    """Kuryenin kendi bordrosunu döner (aylık net hakediş).

    period: 'YYYY-MM' formatında
    """
    return get_personnel_payroll(personnel_id, period)


def list_my_requests(personnel_id: int) -> list[dict]:
    """Kuryenin kendi talep geçmişini döner."""
    return list_requests(personnel_id=personnel_id)


def create_avans_request(personnel_id: int, amount: float, reason: str) -> dict:
    """Avans talep oluştur."""
    fields = {
        "personnel_id": personnel_id,
        "request_type": "Avans",
        "amount": amount,
        "reason": reason,
    }
    return create_request(fields)


def get_my_summary(personnel_id: int, period: str) -> dict:
    """Kuryenin dashboard özet bilgilerini döner.

    - Seçilen aya ait bordro (brüt, kesintiler, net)
    - Beklemede talep sayısı
    - En son 3 talep
    """
    bordro = get_personnel_payroll(personnel_id, period)
    all_requests = list_my_requests(personnel_id)

    # Beklemede talepler
    pending_requests = [r for r in all_requests if r.get("status") == "Beklemede"]
    approved_requests = [r for r in all_requests if r.get("status") == "Onaylandı"]
    rejected_requests = [r for r in all_requests if r.get("status") == "Reddedildi"]

    return {
        "period": period,
        "bordro": bordro,
        "request_stats": {
            "pending_count": len(pending_requests),
            "approved_count": len(approved_requests),
            "rejected_count": len(rejected_requests),
        },
        "recent_requests": all_requests[:5],
    }
