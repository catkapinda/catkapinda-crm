"""Dashboard servis — özet metrikleri hesaplar."""
from datetime import date

from app.core.database import get_connection


def get_dashboard_summary(period: str = "current") -> dict:
    """Genel bakış özet metrikleri.

    period: "2026-03" (specific month), "current" (this month), "previous"
    """
    if period == "current":
        today = date.today()
        period_str = today.strftime("%Y-%m")
    elif period == "previous":
        today = date.today()
        m, y = today.month, today.year
        if m == 1:
            m, y = 12, y - 1
        else:
            m -= 1
        period_str = f"{y:04d}-{m:02d}"
    else:
        period_str = period

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM personnel WHERE status = 'Aktif'")
            row = cur.fetchone()
            active_count = row[0] if row else 0

            cur.execute("SELECT COUNT(*) FROM restaurants WHERE active = true")
            row = cur.fetchone()
            restaurant_count = row[0] if row else 0

            cur.execute("SELECT COUNT(*) FROM personnel WHERE role = 'Kurye' AND status = 'Aktif'")
            row = cur.fetchone()
            kurye_count = row[0] if row else 0

            cur.execute("SELECT COUNT(*) FROM personnel WHERE role = 'Joker' AND status = 'Aktif'")
            row = cur.fetchone()
            joker_count = row[0] if row else 0

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM deductions "
                "WHERE TO_CHAR(deduction_date, 'YYYY-MM') = %s",
                (period_str,),
            )
            row = cur.fetchone()
            total_deductions = float(row[0]) if row else 0

            cur.execute(
                "SELECT "
                "COUNT(*) AS total_entries, "
                "COALESCE(SUM(worked_hours), 0) AS total_hours, "
                "COALESCE(SUM(package_count), 0) AS total_packages "
                "FROM daily_entries "
                "WHERE TO_CHAR(entry_date, 'YYYY-MM') = %s",
                (period_str,),
            )
            row = cur.fetchone()
            entries = int(row[0]) if row else 0
            total_hours = float(row[1]) if row else 0
            total_packages = int(row[2]) if row else 0

    return {
        "period": period_str,
        "active_personnel": active_count,
        "active_restaurants": restaurant_count,
        "kurye_count": kurye_count,
        "joker_count": joker_count,
        "total_deductions": total_deductions,
        "puantaj_entries": entries,
        "total_hours": total_hours,
        "total_packages": total_packages,
    }
