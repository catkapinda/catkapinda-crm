"""Sidebar sayaç (badge) servisi — yan menüdeki canlı rozetler."""
from app.core.database import get_connection
from app.services.profile_changes import count_pending_changes


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

            # Bekleyen hakediş onayları — imzalanmış ama ödenmemiş bordrolar
            try:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM payroll_signatures
                    WHERE paid_at IS NULL
                    """
                )
                row = cur.fetchone()
                counts["hakedis_onay"] = row[0] if row else 0
            except Exception:
                counts["hakedis_onay"] = 0

            # Bekleyen kurye talepleri (avans / motor / muhasebe değişimi)
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM courier_requests WHERE status = 'Beklemede'"
                )
                row = cur.fetchone()
                counts["talepler"] = row[0] if row else 0
            except Exception:
                counts["talepler"] = 0

            # Geriye uyum: avans alias
            counts["avans"] = counts["talepler"]

            # Açık satış lead'leri (varsa)
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM sales_leads WHERE status IN ('open', 'in_progress')"
                )
                row = cur.fetchone()
                counts["satis_leads"] = row[0] if row else 0
            except Exception:
                counts["satis_leads"] = 0

            # Bekleyen profil değişiklik talebi
            try:
                counts["profil_onay"] = count_pending_changes()
            except Exception:
                counts["profil_onay"] = 0

    return counts
