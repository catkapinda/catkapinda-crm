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

    Frontend ``BordroData`` tipi yeni şemayı kullanıyor
    (``total_brut/total_deductions/total_net``). Buradaki normalize
    eski raw payroll alanlarını (``toplam_brut/kesinti_total/sabit_total/
    tevkifat/net``) yeni şemaya çevirir; ham veri ``detail`` altında
    saklı kalır (PDF / detaylı görünüm hâlâ erişebilir).

    period: 'YYYY-MM' formatında
    """
    raw = get_personnel_payroll(personnel_id, period)
    if not raw:
        return {
            "personnel_id": personnel_id,
            "period": period,
            "total_brut": 0.0,
            "total_deductions": 0.0,
            "total_net": 0.0,
            "detail": None,
        }

    total_brut = float(raw.get("toplam_brut") or 0)
    total_deductions = float(
        (raw.get("kesinti_total") or 0)
        + (raw.get("sabit_total") or 0)
        + (raw.get("tevkifat") or 0)
    )
    total_net = float(raw.get("net") or 0)

    # Geriye dönük uyum: full_name vs. UI bordrolarım listesinde de var
    return {
        "personnel_id": personnel_id,
        "period": period,
        "full_name": raw.get("full_name"),
        "total_brut": total_brut,
        "total_deductions": total_deductions,
        "total_net": total_net,
        "detail": raw,
    }


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


def get_my_bordro_periods(personnel_id: int) -> list[dict]:
    """Kuryenin bordrosu olan ayların listesi — yeni tarih başta.

    Return:
        [{period: '2026-03', total_net: 89234.50, is_signed: bool}, ...]
    """
    from app.core.database import get_connection
    from psycopg.rows import dict_row

    sql = """
        SELECT DISTINCT LEFT(entry_date::text, 7) AS period
        FROM daily_entries
        WHERE actual_personnel_id = %s
          AND entry_date IS NOT NULL
          AND COALESCE(worked_hours, 0) > 0
        ORDER BY period DESC
        LIMIT 24
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (personnel_id,))
            periods = [r["period"] for r in cur.fetchall()]

            # Her period için imza durumu
            cur.execute(
                """
                SELECT period FROM payroll_signatures
                WHERE personnel_id = %s
                """,
                (personnel_id,),
            )
            signed = {r["period"] for r in cur.fetchall()}

    out: list[dict] = []
    for p in periods:
        try:
            bordro = get_personnel_payroll(personnel_id, p)
        except Exception:
            bordro = None
        out.append({
            "period": p,
            "total_net": float((bordro or {}).get("net") or 0),
            "total_brut": float((bordro or {}).get("toplam_brut") or 0),
            "ana_days": int((bordro or {}).get("ana_days") or 0),
            "is_signed": p in signed,
        })
    return out


def get_my_summary(personnel_id: int, period: str) -> dict:
    """Kuryenin dashboard özet bilgilerini döner.

    - Seçilen aya ait bordro (brüt, kesintiler, net) — yoksa sıfırlar
    - Beklemede talep sayısı
    - En son 3 talep
    """
    bordro_raw = get_personnel_payroll(personnel_id, period)
    # Frontend `bordro.total_brut` gibi alanlar bekliyor; dashboard'un kabul ettiği
    # düz şema. Bordro yoksa (yeni ay, henüz puantaj yok) sıfır döndür.
    if bordro_raw:
        bordro = {
            "total_brut": float(bordro_raw.get("toplam_brut") or 0),
            "total_deductions": float(
                (bordro_raw.get("kesinti_total") or 0)
                + (bordro_raw.get("sabit_total") or 0)
                + (bordro_raw.get("tevkifat") or 0)
            ),
            "total_net": float(bordro_raw.get("net") or 0),
        }
    else:
        bordro = {
            "total_brut": 0.0,
            "total_deductions": 0.0,
            "total_net": 0.0,
        }

    all_requests = list_my_requests(personnel_id)

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
