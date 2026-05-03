"""Sidebar sayaç (badge) servisi — yan menüdeki canlı rozetler."""
from app.core.database import get_connection


def get_sidebar_counts() -> dict:
    """Yan menüde gösterilecek canlı sayılar.

    Tüm sorgular tek bağlantı üzerinden tek seferde çalışır.
    """
    counts: dict[str, int] = {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Aktif personel
            cur.execute("SELECT COUNT(*) FROM personnel WHERE status = 'Aktif'")
            row = cur.fetchone()
            counts["personel"] = row[0] if row else 0

            # Aktif restoran
            cur.execute("SELECT COUNT(*) FROM restaurants WHERE active = 1")
            row = cur.fetchone()
            counts["restoranlar"] = row[0] if row else 0

            # Bekleyen puantaj onayları (tablo yoksa 0)
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM puantaj_approvals WHERE status = 'pending'"
                )
                row = cur.fetchone()
                counts["puantaj_onay"] = row[0] if row else 0
            except Exception:
                counts["puantaj_onay"] = 0

            # Bekleyen hakediş onayları
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM hakedis_approvals WHERE status = 'pending'"
                )
                row = cur.fetchone()
                counts["hakedis_onay"] = row[0] if row else 0
            except Exception:
                counts["hakedis_onay"] = 0

            # Bekleyen avans talepleri
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM advance_requests WHERE status = 'pending'"
                )
                row = cur.fetchone()
                counts["avans"] = row[0] if row else 0
            except Exception:
                counts["avans"] = 0

            # Açık talepler (lead/talep tablosu varsa)
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM sales_leads WHERE status IN ('open', 'in_progress')"
                )
                row = cur.fetchone()
                counts["talepler"] = row[0] if row else 0
            except Exception:
                counts["talepler"] = 0

    return counts
