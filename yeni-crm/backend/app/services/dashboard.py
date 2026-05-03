"""Dashboard servis — özet metrikleri hesaplar."""
from app.core.database import get_connection


def get_dashboard_summary(period: str = "current") -> dict:
    """Genel bakış özet metrikleri.

    Şu an placeholder — gerçek hesaplamalar:
    - Toplam fatura (KDV hariç/dahil)
    - Toplam kesinti
    - Aktif personel sayısı
    - Mart 2026 örnek veri
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Aktif personel sayısı
            cur.execute("SELECT COUNT(*) FROM personnel WHERE status = 'Aktif'")
            row = cur.fetchone()
            active_count = row[0] if row else 0

            # Aktif restoran sayısı
            cur.execute("SELECT COUNT(*) FROM restaurants WHERE active = true")
            row = cur.fetchone()
            restaurant_count = row[0] if row else 0

    return {
        "period": period,
        "active_personnel": active_count,
        "active_restaurants": restaurant_count,
        # Diğerleri faz 2'de hesaplanacak
        "total_invoice_no_vat": None,
        "total_invoice_with_vat": None,
        "total_deductions": None,
    }
