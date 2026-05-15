"""Restoran raporları servisi — analizler ve KPI'lar.

Başlıklar:
1. Turn Over Analizi — kurye işe giriş/çıkış oranı (restoran bazlı)
2. Saat-Paket Verimi — kurye verimliliği (paket/saat sıralaması)
3. Paket Başı Maliyet — total fatura (KDV hariç) / paket
4. Aylık Paket Artışı — ay bazlı paket karşılaştırması (growth %)
"""
from datetime import date
from calendar import monthrange

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.payroll import list_personnel_payroll


def get_restaurant_reports(period: str = "2026-03") -> dict:
    """Tüm restoran analizleri tek endpoint'te.

    period: "YYYY-MM" (örn. "2026-03")

    Döndüren:
    - turnover: restoran bazlı işe giriş/çıkış analizi
    - courier_efficiency: kurye bazlı saat-paket verimi
    - cost_per_package: restoran ve kurye bazlı maliyet
    - package_growth: ay bazlı büyüme yüzdeleri
    """

    # Önceki ay hesapla
    try:
        y, m = map(int, period.split("-"))
    except (ValueError, AttributeError):
        y, m = date.today().year, date.today().month

    if m == 1:
        prev_m, prev_y = 12, y - 1
    else:
        prev_m, prev_y = m - 1, y

    previous_period = f"{prev_y:04d}-{prev_m:02d}"

    with get_connection() as conn:
        # 1. Turn Over Analizi
        turnover = _get_turnover_analysis(period, conn)

        # 2. Saat-Paket Verimi
        courier_efficiency = _get_courier_efficiency(period, conn)

        # 3. Paket Başı Maliyet
        cost_per_package = _get_cost_per_package(period, conn)

        # 4. Aylık Paket Artışı
        package_growth = _get_package_growth(period, previous_period, conn)

    return {
        "period": period,
        "previous_period": previous_period,
        "turnover": turnover,
        "courier_efficiency": courier_efficiency,
        "cost_per_package": cost_per_package,
        "package_growth": package_growth,
    }


def _get_turnover_analysis(period: str, conn) -> list[dict]:
    """Restoran bazlı işe giriş/çıkış analizi.

    Hedef: Her restoran için aktif kurye sayısı, bu ay işe girenler, çıkanlar.
    turnover_pct = exited_count / active_count (churn oranı)
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id AS restaurant_id,
                r.brand,
                r.branch,
                COUNT(DISTINCT CASE
                    WHEN p.status = 'Aktif'
                    THEN p.id
                END) AS active_count,
                COUNT(DISTINCT CASE
                    WHEN LEFT(COALESCE(p.start_date::text, ''), 7) = %s
                         AND p.assigned_restaurant_id = r.id
                    THEN p.id
                END) AS started_count,
                COUNT(DISTINCT CASE
                    WHEN LEFT(COALESCE(p.exit_date::text, ''), 7) = %s
                         AND p.assigned_restaurant_id = r.id
                    THEN p.id
                END) AS exited_count
            FROM restaurants r
            LEFT JOIN personnel p ON p.assigned_restaurant_id = r.id
            WHERE r.active = 1
            GROUP BY r.id, r.brand, r.branch
            ORDER BY r.brand, r.branch
            """,
            (period, period)
        )
        rows = cur.fetchall()

    result = []
    for r in rows:
        active = int(r.get("active_count") or 0)
        exited = int(r.get("exited_count") or 0)

        # Turnover %: çıkanların aktif sayıya oranı
        turnover_pct = (exited / active * 100) if active > 0 else 0.0

        result.append({
            "restaurant_id": int(r["restaurant_id"]),
            "brand": r["brand"] or "—",
            "branch": r["branch"] or "—",
            "started_count": int(r.get("started_count") or 0),
            "exited_count": exited,
            "active_count": active,
            "turnover_pct": round(turnover_pct, 2),
        })

    return result


def _get_courier_efficiency(period: str, conn) -> list[dict]:
    """Kurye bazlı paket/saat verimi.

    Ana atama (assigned_restaurant_id) ile saat ve paket hesapla.
    packages_per_hour = toplam_paket / toplam_saat
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                p.id AS personnel_id,
                p.full_name,
                p.person_code,
                r.brand AS rest_brand,
                r.branch AS rest_branch,
                COUNT(DISTINCT de.id) AS entry_count,
                COALESCE(SUM(de.worked_hours), 0) AS total_hours,
                COALESCE(SUM(de.package_count), 0) AS total_packages
            FROM personnel p
            LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
            LEFT JOIN daily_entries de ON de.actual_personnel_id = p.id
                                      AND LEFT(de.entry_date::text, 7) = %s
                                      AND de.restaurant_id = p.assigned_restaurant_id
            WHERE p.role IN ('Kurye', 'Joker')
              AND p.status = 'Aktif'
            GROUP BY p.id, p.full_name, p.person_code, r.brand, r.branch
            HAVING COALESCE(SUM(de.worked_hours), 0) > 0
            ORDER BY
                COALESCE(SUM(de.package_count), 0) / NULLIF(COALESCE(SUM(de.worked_hours), 0), 0) DESC
            """,
            (period,)
        )
        rows = cur.fetchall()

    result = []
    for r in rows:
        hours = float(r.get("total_hours") or 0)
        packages = int(r.get("total_packages") or 0)

        packages_per_hour = (packages / hours) if hours > 0 else 0.0

        result.append({
            "personnel_id": int(r["personnel_id"]),
            "full_name": r["full_name"] or "—",
            "person_code": r["person_code"] or "—",
            "rest_brand": r["rest_brand"] or "—",
            "rest_branch": r["rest_branch"] or "—",
            "packages": packages,
            "hours": round(hours, 2),
            "packages_per_hour": round(packages_per_hour, 2),
        })

    return result


def _get_cost_per_package(period: str, conn) -> dict:
    """Paket başı maliyet — restoran + kurye bazlı.

    cost_per_package = toplam_fatura_kdv_hariç / toplam_paket
    """
    # Bordrodan toplam brüt ve paket verisi
    # NOT: list_personnel_payroll DICT döner ({period, rows, summary});
    # rows içindeki her elemanda key adları 'toplam_brut' ve 'ana_packages'.
    payroll_data = list_personnel_payroll(period)
    payroll = payroll_data.get("rows", []) if isinstance(payroll_data, dict) else []

    total_brut = sum(float(p.get("toplam_brut", 0)) for p in payroll)
    total_packages_all = sum(int(p.get("ana_packages", 0)) for p in payroll)

    overall_cost = (total_brut / total_packages_all) if total_packages_all > 0 else 0.0

    # Restoran bazlı
    by_restaurant = _get_cost_per_package_by_restaurant(period, conn)

    # Kurye bazlı (top 20)
    by_courier = _get_cost_per_package_by_courier(period, conn)

    return {
        "overall": round(overall_cost, 2),
        "by_restaurant": by_restaurant,
        "by_courier": by_courier,
    }


def _get_cost_per_package_by_restaurant(period: str, conn) -> list[dict]:
    """Restoran bazlı paket başı maliyet."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id AS restaurant_id,
                r.brand,
                r.branch,
                COALESCE(SUM(de.package_count), 0) AS total_packages
            FROM restaurants r
            LEFT JOIN daily_entries de ON de.restaurant_id = r.id
                                      AND LEFT(de.entry_date::text, 7) = %s
            WHERE r.active = 1
            GROUP BY r.id, r.brand, r.branch
            HAVING COALESCE(SUM(de.package_count), 0) > 0
            ORDER BY total_packages DESC
            """,
            (period,)
        )
        rest_rows = cur.fetchall()

    # Kurye bordro verisi — kişi başı kaç paket
    payroll_data = list_personnel_payroll(period)
    payroll = payroll_data.get("rows", []) if isinstance(payroll_data, dict) else []
    payroll_by_id = {int(p.get("id", 0)): p for p in payroll}

    result = []
    for r in rest_rows:
        rest_id = int(r["restaurant_id"])
        total_packages = int(r.get("total_packages") or 0)

        # Bu restorana atanmış kuryeler için toplam brüt hesapla
        total_brut_for_rest = 0.0
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT p.id
                FROM personnel p
                WHERE p.assigned_restaurant_id = %s
                  AND p.role IN ('Kurye', 'Joker')
                  AND p.status = 'Aktif'
                """,
                (rest_id,)
            )
            courier_ids = [int(row["id"]) for row in cur.fetchall()]

        for cid in courier_ids:
            if cid in payroll_by_id:
                total_brut_for_rest += float(payroll_by_id[cid].get("toplam_brut", 0))

        cost_per_pkg = (total_brut_for_rest / total_packages) if total_packages > 0 else 0.0

        result.append({
            "restaurant_id": rest_id,
            "brand": r["brand"] or "—",
            "branch": r["branch"] or "—",
            "billing_excl_vat": round(total_brut_for_rest, 2),
            "packages": total_packages,
            "cost_per_package": round(cost_per_pkg, 2),
        })

    return result


def _get_cost_per_package_by_courier(period: str, conn) -> list[dict]:
    """Kurye bazlı paket başı maliyet (top 20 + bottom 5)."""
    payroll_data = list_personnel_payroll(period)
    payroll = payroll_data.get("rows", []) if isinstance(payroll_data, dict) else []

    result = []
    for p in payroll:
        pid = int(p.get("id", 0))
        packages = int(p.get("ana_packages", 0))
        brut = float(p.get("toplam_brut", 0))

        if packages > 0:
            cost_per_pkg = brut / packages

            # Bu kuryenin restoranını bul
            with get_connection() as conn_inner:
                with conn_inner.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        "SELECT assigned_restaurant_id FROM personnel WHERE id = %s",
                        (pid,)
                    )
                    row = cur.fetchone()
                    rest_id = row.get("assigned_restaurant_id") if row else None

            # Restoran bilgisi
            rest_brand = "—"
            if rest_id:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        "SELECT brand FROM restaurants WHERE id = %s",
                        (rest_id,)
                    )
                    r = cur.fetchone()
                    rest_brand = r.get("brand", "—") if r else "—"

            result.append({
                "personnel_id": pid,
                "full_name": p.get("full_name") or "—",
                "rest_brand": rest_brand,
                "billing": round(brut, 2),
                "packages": packages,
                "cost_per_package": round(cost_per_pkg, 2),
            })

    # Top 20 en pahalı + bottom 5 en ucuz
    result_sorted = sorted(result, key=lambda x: x["cost_per_package"], reverse=True)
    top = result_sorted[:20]
    bottom = sorted(result, key=lambda x: x["cost_per_package"])[:5]

    return top + bottom


def _get_package_growth(period: str, previous_period: str, conn) -> list[dict]:
    """Aylık paket artışı — restoran bazlı growth %."""

    # Cari ay paketleri
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id AS restaurant_id,
                r.brand,
                r.branch,
                COALESCE(SUM(de.package_count), 0) AS total_packages
            FROM restaurants r
            LEFT JOIN daily_entries de ON de.restaurant_id = r.id
                                      AND LEFT(de.entry_date::text, 7) = %s
            WHERE r.active = 1
            GROUP BY r.id, r.brand, r.branch
            """,
            (period,)
        )
        current_rows = cur.fetchall()

    current_by_rest = {int(r["restaurant_id"]): int(r.get("total_packages") or 0)
                       for r in current_rows}

    # Önceki ay paketleri
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id AS restaurant_id,
                COALESCE(SUM(de.package_count), 0) AS total_packages
            FROM restaurants r
            LEFT JOIN daily_entries de ON de.restaurant_id = r.id
                                      AND LEFT(de.entry_date::text, 7) = %s
            WHERE r.active = 1
            GROUP BY r.id
            """,
            (previous_period,)
        )
        previous_rows = cur.fetchall()

    previous_by_rest = {int(r["restaurant_id"]): int(r.get("total_packages") or 0)
                        for r in previous_rows}

    # Büyüme hesapla
    result = []
    for rest_id, current_pkg in current_by_rest.items():
        prev_pkg = previous_by_rest.get(rest_id, 0)

        # Büyüme % = (current - prev) / prev * 100
        growth_pct = ((current_pkg - prev_pkg) / prev_pkg * 100) if prev_pkg > 0 else (
            100.0 if current_pkg > 0 else 0.0
        )
        delta = current_pkg - prev_pkg

        # Brand/branch bilgisi
        for r in current_rows:
            if int(r["restaurant_id"]) == rest_id:
                result.append({
                    "restaurant_id": rest_id,
                    "brand": r["brand"] or "—",
                    "branch": r["branch"] or "—",
                    "current_packages": current_pkg,
                    "previous_packages": prev_pkg,
                    "growth_pct": round(growth_pct, 2),
                    "delta": delta,
                })
                break

    # En yüksek büyümeden başla
    result.sort(key=lambda x: x["growth_pct"], reverse=True)

    return result
