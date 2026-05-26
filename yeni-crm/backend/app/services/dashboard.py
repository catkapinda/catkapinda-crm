"""Dashboard servis — özet metrikleri hesaplar."""
from datetime import date
from calendar import monthrange

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.payroll import calculate_tevkifat
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

    Top-level try/except — herhangi bir alt-hesap çöktüğünde safe defaults döner.
    """
    # Defaults (her şey patlarsa frontend boş kalmasın)
    result: dict = {
        "period": period,
        "invoiced_kdv_haric": 0.0,
        "invoiced_kdv_dahil": 0.0,
        "tevkifat_total": 0.0,
        "total_courier_net": 0.0,
        "total_management_salary": 0.0,
        "total_costs": 0.0,
        "net_profit": 0.0,
        "margin_pct": 0.0,
        "revenue_trend": [],
        "by_restaurant": [],
        "deduction_breakdown": [],
        "personnel_performance": [],
        "ai_insights": [],
    }

    try:
        # 1. Direkt SQL ile gelir & gider hesabı (list_personnel_payroll'a bağımlı değil)
        # Gelir = saatlik ödeme + paket ödemesi + sabit aylık (tüm tarife modelleri)
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # 1a. Saatlik + paket bazlı gelir (hourly_only, hourly_plus_package, threshold_package)
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(de.worked_hours * COALESCE(r.hourly_rate, 0)), 0)
                            AS hourly_revenue,
                        COALESCE(SUM(de.package_count * COALESCE(r.package_rate, 0)), 0)
                            AS package_revenue
                    FROM daily_entries de
                    LEFT JOIN restaurants r ON r.id = de.restaurant_id
                    WHERE LEFT(de.entry_date::text, 7) = %s
                      AND COALESCE(de.worked_hours, 0) > 0
                    """,
                    (period,),
                )
                rev_row = cur.fetchone() or {}
                hourly_revenue = float(rev_row.get("hourly_revenue") or 0)
                package_revenue = float(rev_row.get("package_revenue") or 0)

                # 1b. Sabit aylık gelir (fixed_monthly_billing kuryeler için)
                cur.execute(
                    """
                    SELECT COALESCE(SUM(p.fixed_monthly_billing), 0) AS fixed_billing
                    FROM personnel p
                    WHERE COALESCE(p.status, 'Aktif') = 'Aktif'
                      AND COALESCE(p.fixed_monthly_billing, 0) > 0
                      AND EXISTS (
                          SELECT 1 FROM daily_entries d
                          WHERE d.actual_personnel_id = p.id
                            AND LEFT(d.entry_date::text, 7) = %s
                      )
                    """,
                    (period,),
                )
                fixed_row = cur.fetchone() or {}
                fixed_billing = float(fixed_row.get("fixed_billing") or 0)

                # 1c. Yönetim maaşları
                cur.execute(
                    """
                    SELECT COALESCE(SUM(monthly_fixed_cost), 0) AS total_mgmt_salary
                    FROM personnel
                    WHERE status = 'Aktif'
                      AND role IN ('Bölge Müdürü', 'Kaptan', 'Restoran Takım Şefi', 'Joker')
                    """
                )
                mgmt_row = cur.fetchone() or {}
                total_management_salary = float(mgmt_row.get("total_mgmt_salary") or 0)

                # 1d. Kuryelere ödenen net (sabit maaş + monthly_fixed_cost'lu kuryeler)
                cur.execute(
                    """
                    SELECT COALESCE(SUM(monthly_fixed_cost), 0) AS courier_fixed
                    FROM personnel
                    WHERE status = 'Aktif'
                      AND role = 'Kurye'
                      AND COALESCE(monthly_fixed_cost, 0) > 0
                    """
                )
                cf_row = cur.fetchone() or {}
                courier_fixed_total = float(cf_row.get("courier_fixed") or 0)

                # 1e. Kesintiler (manuel zimmet/yakıt vb.)
                cur.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total_ded
                    FROM deductions
                    WHERE LEFT(deduction_date::text, 7) = %s
                    """,
                    (period,),
                )
                ded_row = cur.fetchone() or {}
                manual_deductions = float(ded_row.get("total_ded") or 0)

        # Toplam fatura (KDV hariç) = saatlik + paket + sabit aylık
        invoiced_kdv_haric = hourly_revenue + package_revenue + fixed_billing
        invoiced_kdv_dahil = invoiced_kdv_haric * 1.20

        tevkifat_calc = calculate_tevkifat(invoiced_kdv_dahil)
        tevkifat_total = float(tevkifat_calc.get("tevkifat_amount", 0))

        # Kuryelere ödenen ≈ saatlik+paket geliri (kurye payı zaten brüt) + sabit kurye maaşı
        total_courier_net = (hourly_revenue + package_revenue + courier_fixed_total) - manual_deductions
        total_courier_net = max(0, total_courier_net)

        # 3. Marj hesabı
        total_costs = total_courier_net + total_management_salary
        net_profit = invoiced_kdv_haric - total_costs
        margin_pct = (net_profit / invoiced_kdv_haric * 100) if invoiced_kdv_haric > 0 else 0

        result.update({
            "invoiced_kdv_haric": invoiced_kdv_haric,
            "invoiced_kdv_dahil": invoiced_kdv_dahil,
            "tevkifat_total": tevkifat_total,
            "total_courier_net": total_courier_net,
            "total_management_salary": total_management_salary,
            "total_costs": total_costs,
            "net_profit": net_profit,
            "margin_pct": margin_pct,
        })

        # 4. Son 3 ay revenue trend (eskiden 6 aydı, connection pool yorgunluğu için kısaltıldı)
        try:
            result["revenue_trend"] = _get_revenue_trend_lite(period)
        except Exception:
            pass

        # 5. Restoranlar bazında fatura
        try:
            result["by_restaurant"] = _get_restaurant_breakdown(period)
        except Exception:
            pass

        # 6. Kesinti dağılımı
        try:
            result["deduction_breakdown"] = deductions_summary_by_type(period)
        except Exception:
            pass

        # 7. Personel performansı
        try:
            result["personnel_performance"] = _get_personnel_performance(period)
        except Exception:
            pass

        # 8. AI insights
        try:
            result["ai_insights"] = _generate_ai_insights(
                period, result["by_restaurant"], result["personnel_performance"],
                margin_pct, net_profit, invoiced_kdv_haric,
            )
        except Exception:
            pass

    except Exception as e:
        # Tüm üst-seviye hesap çöktüğünde bile boş response dönsün, 500 atma
        import logging
        logging.getLogger(__name__).exception("get_dashboard_analytics failed: %s", e)

    return result


def _get_revenue_trend_lite(current_period: str) -> list[dict]:
    """Son 3 ay revenue trend — direct SQL (list_personnel_payroll'u çağırmaz, hızlı).

    invoiced ≈ sum(worked_hours × hourly_rate)  (yaklaşık brüt)
    net_paid ≈ invoiced × 0.7                  (kuryelere ödenen oran ortalaması)
    """
    try:
        y, m = map(int, current_period.split("-"))
    except (ValueError, AttributeError):
        return []

    periods: list[str] = []
    for offset in range(-2, 1):
        mm = m + offset
        yy = y
        if mm < 1:
            mm += 12
            yy -= 1
        periods.append(f"{yy:04d}-{mm:02d}")

    out: list[dict] = []
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            for p in periods:
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(de.worked_hours * COALESCE(r.hourly_rate, 0)), 0)
                            + COALESCE(SUM(de.package_count * COALESCE(r.package_rate, 0)), 0)
                            AS invoiced
                    FROM daily_entries de
                    LEFT JOIN restaurants r ON r.id = de.restaurant_id
                    WHERE LEFT(de.entry_date::text, 7) = %s
                      AND COALESCE(de.worked_hours, 0) > 0
                    """,
                    (p,),
                )
                row = cur.fetchone()
                invoiced = float((row and row.get("invoiced")) or 0)
                out.append({
                    "period": p,
                    "invoiced": invoiced,
                    "net_paid": invoiced * 0.7,
                })
    return out


def _get_restaurant_breakdown(period: str) -> list[dict]:
    """Restoranlar bazında aylık fatura (invoiced + net paid)."""
    with get_connection() as conn:
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


def _get_personnel_performance(period: str) -> list[dict]:
    """Personel performansı — paket/saat bazında 0-1 score (heatmap 0-5 için)."""
    with get_connection() as conn:
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
    margin_pct: float, net_profit: float, total_invoice: float,
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

    # Insight 2: Yüksek tempolu kurye sayısı — operasyon sağlığı sinyali
    # (Önceki sürüm 'ek paket talebi olabilir' diyordu — Çat Kapında
    # restorana paket talep etmez, mantıksız bir yorumdu. Doğrusu:
    # yüksek performans = operasyon sağlıklı, primlendirme veya
    # restoranı stabil olarak işaretleme fırsatı.)
    if personnel_perf:
        high_performers = [p for p in personnel_perf if p["score_0_1"] > 0.8]
        if high_performers and by_restaurant:
            top_rest = by_restaurant[0]
            insights.append({
                "severity": "info",
                "text": (
                    f"{top_rest['brand']}: {len(high_performers)} kurye yüksek "
                    "tempo — operasyon sağlıklı, performans primi/teşekkür için "
                    "uygun ay."
                ),
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


def get_available_periods() -> list[str]:
    """Sistemde gerçek veri (puantaj veya fatura) olan ayların listesi.

    En yeniden eskiye doğru sıralı, max 24 ay döner.
    Boş ay (puantajı sıfır + faturası sıfır) döndürmez.
    """
    periods: set[str] = set()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Puantaj verisi olan aylar
                cur.execute(
                    """
                    SELECT DISTINCT LEFT(entry_date::text, 7) AS period
                    FROM daily_entries
                    WHERE entry_date IS NOT NULL
                      AND COALESCE(worked_hours, 0) > 0
                    """
                )
                for row in cur.fetchall():
                    if row[0]:
                        periods.add(row[0])

                # Fatura kesilen aylar (manuel ayda da gözüksün)
                cur.execute(
                    """
                    SELECT DISTINCT period
                    FROM restaurant_invoices
                    WHERE period IS NOT NULL
                    """
                )
                for row in cur.fetchall():
                    if row[0]:
                        periods.add(row[0])
    except Exception:
        pass

    return sorted(periods, reverse=True)[:24]
