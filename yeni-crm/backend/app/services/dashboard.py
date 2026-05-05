"""Dashboard servis — özet metrikleri hesaplar."""
from datetime import date
from calendar import monthrange

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.payroll import list_personnel_payroll, calculate_tevkifat
from app.services.deductions import deductions_summary_by_type


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

            cur.execute("SELECT COUNT(*) FROM restaurants WHERE active = 1")
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
                "WHERE LEFT(deduction_date::text, 7) = %s",
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
                "WHERE LEFT(entry_date::text, 7) = %s",
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


def get_dashboard_analytics(period: str = "2026-03") -> dict:
    """Kapsamlı dashboard analytics — tüm KPI'ları gerçek veriden hesapla.

    Hesaplanan:
    - invoiced_kdv_haric: sum(bordro toplam_brut)
    - invoiced_kdv_dahil: × 1.20
    - tevkifat_total: sum(tevkifat)
    - total_courier_net: sum(kurye net ödenen)
    - total_management_salary: sum(yönetim sabit giderleri)
    - margin_pct: (invoiced_kdv_haric - total_costs) / invoiced_kdv_haric * 100
    - revenue_trend: son 6 ay
    - by_restaurant: aktif restoranlar ve aylık faturaları
    - personnel_performance: paket/saat bazında puanlama (0-5)
    - ai_insights: otomatik üretilen insight'lar
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Bordro verisi — toplam brüt + kurye net ödemeleri
            payroll = list_personnel_payroll(period)

            invoiced_kdv_haric = sum(float(p.get("brut", 0)) for p in payroll)
            invoiced_kdv_dahil = invoiced_kdv_haric * 1.20

            # Tevkifat hesabı (tüm bordrodan)
            tevkifat_calc = calculate_tevkifat(invoiced_kdv_dahil)
            tevkifat_total = float(tevkifat_calc.get("tevkifat_amount", 0))

            # Kuryelere ödenen net toplam
            total_courier_net = sum(float(p.get("net", 0)) for p in payroll
                                   if (p.get("role") or "").strip() in ["Kurye", "Joker"])

            # 2. Yönetim maaşları (BM, Kaptan, RTS sabit + Joker)
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(monthly_fixed_cost), 0) AS total_mgmt_salary
                FROM personnel
                WHERE status = 'Aktif'
                  AND role IN ('Bölge Müdürü', 'Kaptan', 'Restoran Takım Şefi', 'Joker')
                """
            )
            mgmt_row = cur.fetchone()
            total_management_salary = float(mgmt_row.get("total_mgmt_salary") or 0) if mgmt_row else 0

            # 3. Marj hesabı
            total_costs = total_courier_net + total_management_salary
            net_profit = invoiced_kdv_haric - total_costs
            margin_pct = (net_profit / invoiced_kdv_haric * 100) if invoiced_kdv_haric > 0 else 0

            # 4. Son 6 ay revenue trend
            revenue_trend = _get_revenue_trend(period, conn)

            # 5. Restoranlar bazında fatura
            by_restaurant = _get_restaurant_breakdown(period, conn)

            # 6. Kesinti dağılımı (zaten var)
            deduction_breakdown = deductions_summary_by_type(period)

            # 7. Personel performansı (paket/saat bazında)
            personnel_performance = _get_personnel_performance(period, conn)

            # 8. AI insights
            ai_insights = _generate_ai_insights(
                period, by_restaurant, personnel_performance,
                margin_pct, net_profit, invoiced_kdv_haric, conn
            )

    return {
        "period": period,
        "invoiced_kdv_haric": invoiced_kdv_haric,
        "invoiced_kdv_dahil": invoiced_kdv_dahil,
        "tevkifat_total": tevkifat_total,
        "total_courier_net": total_courier_net,
        "total_management_salary": total_management_salary,
        "total_costs": total_costs,
        "net_profit": net_profit,
        "margin_pct": margin_pct,
        "revenue_trend": revenue_trend,
        "by_restaurant": by_restaurant,
        "deduction_breakdown": deduction_breakdown,
        "personnel_performance": personnel_performance,
        "ai_insights": ai_insights,
    }


def _get_revenue_trend(current_period: str, conn) -> list[dict]:
    """Son 6 ay bordro verisi (including current)."""
    try:
        y, m = map(int, current_period.split("-"))
    except (ValueError, AttributeError):
        return []

    trend = []
    for offset in range(-5, 1):  # 5 ay öncesinden şimdiye
        if m + offset < 1:
            month = m + offset + 12
            year = y - 1
        elif m + offset > 12:
            month = m + offset - 12
            year = y + 1
        else:
            month = m + offset
            year = y

        period_str = f"{year:04d}-{month:02d}"
        payroll = list_personnel_payroll(period_str)
        invoiced = sum(float(p.get("brut", 0)) for p in payroll)
        net_paid = sum(float(p.get("net", 0)) for p in payroll)

        trend.append({
            "period": period_str,
            "invoiced": invoiced,
            "net_paid": net_paid,
        })

    return trend


def _get_restaurant_breakdown(period: str, conn) -> list[dict]:
    """Restoranlar bazında aylık fatura (invoiced + net paid)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id, r.brand, r.branch, r.pricing_model,
                COUNT(DISTINCT CASE WHEN de.actual_personnel_id IS NOT NULL
                                  THEN de.actual_personnel_id END) AS courier_count,
                COALESCE(SUM(
                    CASE
                        WHEN de.worked_hours > 0 THEN de.worked_hours * r.hourly_rate
                        ELSE 0
                    END
                ), 0) AS invoiced_partial
            FROM restaurants r
            LEFT JOIN daily_entries de ON de.restaurant_id = r.id
                                     AND LEFT(de.entry_date::text, 7) = %s
            WHERE r.active = 1
            GROUP BY r.id, r.brand, r.branch, r.pricing_model
            ORDER BY invoiced_partial DESC
            LIMIT 8
            """,
            (period,)
        )
        restaurants = cur.fetchall()

    result = []
    for r in restaurants:
        result.append({
            "id": int(r["id"]),
            "brand": r["brand"] or "—",
            "branch": r["branch"] or "—",
            "courier_count": int(r.get("courier_count") or 0),
            "invoiced": float(r.get("invoiced_partial") or 0),
            "net_paid": float(r.get("invoiced_partial") or 0) * 0.7,  # Approx
            "pricing_model": r["pricing_model"] or "?",
        })

    return result


def _get_personnel_performance(period: str, conn) -> list[dict]:
    """Personel performansı — paket/saat bazında 0-1 score (heatmap 0-5 için)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                p.id,
                COALESCE(SUM(de.package_count), 0) AS total_packages,
                COALESCE(SUM(de.worked_hours), 0) AS total_hours
            FROM personnel p
            LEFT JOIN daily_entries de ON de.actual_personnel_id = p.id
                                     AND LEFT(de.entry_date::text, 7) = %s
            WHERE p.status = 'Aktif'
            GROUP BY p.id
            """,
            (period,)
        )
        rows = cur.fetchall()

    result = []
    max_packages = max((int(r.get("total_packages") or 0) for r in rows), default=1)

    for r in rows:
        packages = int(r.get("total_packages") or 0)
        hours = float(r.get("total_hours") or 0)
        # Score 0-1: paketler max'a göre normalized
        score = (packages / max_packages) if max_packages > 0 else 0

        result.append({
            "personnel_id": int(r["id"]),
            "packages": packages,
            "hours": hours,
            "score_0_1": score,
        })

    return result


def _generate_ai_insights(
    period: str, by_restaurant: list[dict], personnel_perf: list[dict],
    margin_pct: float, net_profit: float, total_invoice: float, conn
) -> list[dict]:
    """Otomatik insight'lar — en önemlisinden başlayarak (max 3)."""
    insights = []

    # Insight 1: Kapasite altında restoran
    if by_restaurant:
        for rest in by_restaurant[:3]:
            if rest["courier_count"] < 5:  # Örnek: 5'in altında
                insights.append({
                    "severity": "alert",
                    "text": f"{rest['brand']}{' · ' + rest['branch'] if rest['branch'] else ''} "
                           f"kurye kapasitesi düşük ({rest['courier_count']} kişi) — işe alım acil.",
                    "metric": "capacity",
                })
                break

    # Insight 2: Threshold yaklaşan restoran
    if personnel_perf:
        high_performers = [p for p in personnel_perf if p["score_0_1"] > 0.8]
        if high_performers and by_restaurant:
            top_rest = by_restaurant[0]
            insights.append({
                "severity": "warning",
                "text": f"{top_rest['brand']}: {len(high_performers)} kurye yüksek performans — "
                       f"ek paket talebi olabilir.",
                "metric": "performance",
            })

    # Insight 3: Kar marjı trend
    if margin_pct < 20:
        insights.append({
            "severity": "alert",
            "text": f"Bu ay marj {margin_pct:.1f}% — hedef %25'in altında. Kesinti denetimi gerekli.",
            "metric": "margin",
        })
    elif margin_pct > 30:
        insights.append({
            "severity": "info",
            "text": f"Harika ay! Marj {margin_pct:.1f}% — sürdürülmesi için mevcut sözleşmeleri koruyun.",
            "metric": "margin",
        })

    return insights[:3]  # En çok 3 insight
