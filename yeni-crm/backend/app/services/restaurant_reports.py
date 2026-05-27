"""Restoran raporları servisi — analizler ve KPI'lar.

Başlıklar:
1. Turn Over Analizi — kurye işe giriş/çıkış oranı (restoran bazlı)
2. Saat-Paket Verimi — kurye verimliliği (paket/saat sıralaması)
3. Paket Başı Maliyet — total fatura (KDV hariç) / paket
4. Aylık Paket Artışı — ay bazlı paket karşılaştırması (growth %)
"""
import time
from datetime import date
from calendar import monthrange

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.payroll import list_personnel_payroll


# Module-level basit TTL cache. get_restaurant_reports ağır (list_personnel_payroll
# iki kere çağrılır, N+1 query'ler var) — Render free tier'ın 30 saniyelik gateway
# timeout'unu aşabiliyor. Cache sayesinde aynı period için tekrar tekrar
# hesaplama yapılmaz.
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 300  # 5 dk


def _cache_get(key: str) -> dict | None:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, data = item
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return data


def _cache_set(key: str, value: dict) -> None:
    _CACHE[key] = (time.time(), value)


def invalidate_cache(period: str | None = None) -> None:
    """Cache'i temizle (test veya kasıtlı tazeleme için)."""
    if period is None:
        _CACHE.clear()
    else:
        _CACHE.pop(period, None)


def get_restaurant_reports(period: str = "2026-03", *, use_cache: bool = True) -> dict:
    """Tüm restoran analizleri tek endpoint'te.

    period: "YYYY-MM" (örn. "2026-03")
    use_cache: True ise 5 dk TTL cache kullan; False ise direkt hesapla.

    Döndüren:
    - turnover: restoran bazlı işe giriş/çıkış analizi
    - courier_efficiency: kurye bazlı saat-paket verimi
    - cost_per_package: restoran ve kurye bazlı maliyet
    - package_growth: ay bazlı büyüme yüzdeleri
    """
    if use_cache:
        cached = _cache_get(period)
        if cached is not None:
            return cached

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

    result = {
        "period": period,
        "previous_period": previous_period,
        "turnover": turnover,
        "courier_efficiency": courier_efficiency,
        "cost_per_package": cost_per_package,
        "package_growth": package_growth,
    }
    if use_cache:
        _cache_set(period, result)
    return result


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
    """Paket başı maliyet + fatura — restoran + kurye bazlı.

    overall (CK genel):
      • billing_per_package = SUM(restoran faturası) / SUM(paket)  → ortalama gelir
      • cost_per_package    = SUM(kurye brüt) / SUM(paket)         → ortalama maliyet
      • margin_pct          = (billing - cost) / billing × 100
    """
    payroll_data = list_personnel_payroll(period)
    payroll = payroll_data.get("rows", []) if isinstance(payroll_data, dict) else []

    total_brut = sum(float(p.get("toplam_brut", 0)) for p in payroll)
    total_packages_all = sum(int(p.get("ana_packages", 0)) for p in payroll)

    # Restoran bazlı (her satırda billing_excl_vat + cost_per_package + margin)
    by_restaurant = _get_cost_per_package_by_restaurant(period, conn, payroll=payroll)

    # CK toplam fatura (restoran agregesinden — KDV hariç matrah)
    total_billing = sum(float(x.get("billing_excl_vat") or 0) for x in by_restaurant)

    # total_brut KDV DAHİL — marj için KDV hariç matrahını kullan
    total_brut_excl_vat = total_brut / 1.20 if total_brut > 0 else 0.0

    overall_billing_per_pkg = (total_billing / total_packages_all) if total_packages_all > 0 else 0.0
    overall_cost = (total_brut_excl_vat / total_packages_all) if total_packages_all > 0 else 0.0
    margin = total_billing - total_brut_excl_vat
    margin_pct = (margin / total_billing * 100) if total_billing > 0 else 0.0

    # Kurye bazlı (top 20) — payroll'u paylaş
    by_courier = _get_cost_per_package_by_courier(period, conn, payroll=payroll)

    return {
        # 'overall' geriye uyumluluk için tek değer — CK paket başı maliyeti
        # (KDV hariç matrah üzerinden)
        "overall": round(overall_cost, 2),
        # CK toplam metrikleri (hepsi KDV HARİÇ apples-to-apples):
        "overall_billing_excl_vat": round(total_billing, 2),
        "overall_courier_cost": round(total_brut_excl_vat, 2),  # KDV hariç (marj için)
        "overall_courier_cost_incl_vat": round(total_brut, 2),  # KDV dahil (referans)
        "overall_packages": total_packages_all,
        "overall_billing_per_package": round(overall_billing_per_pkg, 2),
        "overall_cost_per_package": round(overall_cost, 2),
        "overall_margin": round(margin, 2),
        "overall_margin_pct": round(margin_pct, 1),
        "by_restaurant": by_restaurant,
        "by_courier": by_courier,
    }


def _get_cost_per_package_by_restaurant(period: str, conn, payroll: list[dict] | None = None) -> list[dict]:
    """Restoran bazlı paket başı maliyet + restoran faturası.

    Üç farklı kavram döner:
      • billing_excl_vat — Restorana KESILEN fatura (KDV hariç).
        pricing_model + puantajdan hesaplanır:
        saat × hourly_rate + paket × pkg_rate (Fasuli/QuickChina karma)
        veya fixed_monthly_fee (SC Petshop)
      • courier_cost — Kuryelere ÖDEDİĞİMİZ toplam brüt (CK'nın maliyeti)
      • cost_per_package — courier_cost ÷ paket (CK'nın paket başı maliyeti)
      • billing_per_package — billing_excl_vat ÷ paket (restoranın paket başı ödediği)

    Önceki sürüm billing_excl_vat olarak courier_cost'u dolduruyordu —
    bu yüzden Quick China gibi karma anlaşmalı restoranlar 'olağandışı
    düşük fatura' yorumu alıyordu (gerçek fatura çok daha yüksek).
    """
    # 1) Restoran havuzu (period-aware: aktif + puantajlı + faturalı)
    from app.services.collections import (
        _compute_auto_invoice_map,
        _get_period_restaurants,
    )

    period_rests = _get_period_restaurants(period)
    rest_by_id = {int(r["id"]): r for r in period_rests}

    # 2) Otomatik fatura hesabı (pricing_model'e göre)
    auto_map = _compute_auto_invoice_map(period)

    # 3) Paket toplamları
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id AS restaurant_id,
                r.brand,
                r.branch,
                COALESCE(SUM(de.package_count), 0)::int AS total_packages
            FROM restaurants r
            LEFT JOIN daily_entries de ON de.restaurant_id = r.id
                                      AND LEFT(de.entry_date::text, 7) = %s
            WHERE r.id = ANY(%s)
            GROUP BY r.id, r.brand, r.branch
            ORDER BY total_packages DESC
            """,
            (period, list(rest_by_id.keys()) or [0]),
        )
        rest_rows = cur.fetchall()

    # 4) Personel maliyet attribution — HYBRID:
    #    a) Paket/saat bazlı kuryeler (is_fixed_salary=False):
    #       ana_brut → assigned_rid (kendi tarife oranıyla zaten doğru)
    #       destek_lines.amount → her destek restoranına ayrı (yine kendi tarifesi)
    #    b) SABİT AYLIK personel (is_fixed_salary=True — BM/Kaptan/RTŞ):
    #       toplam_brut, çalıştığı saate orantılı dağıtılır.
    #       Örnek: BM 15k aylık, QC'de 100sa + A'da 30sa + B'de 20sa + C'de 10sa
    #         → QC: 15000×(100/160)=9.375  A:2.812  B:1.875  C:937 (sum=15k)
    #       Aksi halde BM'in tüm aylığı tek restorana yazılıp paket başı
    #       maliyeti yapay olarak şişirir.
    if payroll is None:
        payroll_data = list_personnel_payroll(period)
        payroll = payroll_data.get("rows", []) if isinstance(payroll_data, dict) else []

    courier_cost_by_rest: dict[int, float] = {}
    for pr in payroll:
        assigned_rid = pr.get("assigned_restaurant_id")

        if pr.get("is_fixed_salary"):
            # Sabit aylık — toplam_brut'u çalıştığı saate göre dağıt
            toplam = float(pr.get("toplam_brut") or 0)
            if toplam <= 0:
                continue
            ana_hours = float(pr.get("ana_hours") or 0)
            rest_hours: dict[int, float] = {}
            if assigned_rid:
                rest_hours[int(assigned_rid)] = ana_hours
            for line in (pr.get("destek_lines") or []):
                rid = line.get("restaurant_id")
                if rid:
                    rid_i = int(rid)
                    rest_hours[rid_i] = rest_hours.get(rid_i, 0.0) + float(
                        line.get("hours") or 0
                    )
            total_hours = sum(rest_hours.values())
            if total_hours > 0:
                for rid, h in rest_hours.items():
                    share = toplam * (h / total_hours)
                    courier_cost_by_rest[rid] = (
                        courier_cost_by_rest.get(rid, 0.0) + share
                    )
            elif assigned_rid:
                # Ay içinde hiç puantaj yoksa fallback: tüm aylığı assigned'a yaz
                courier_cost_by_rest[int(assigned_rid)] = (
                    courier_cost_by_rest.get(int(assigned_rid), 0.0) + toplam
                )
        else:
            # Paket/saat bazlı — ana_brut assigned'a, destek_lines kendi rate'inden
            if assigned_rid:
                rid = int(assigned_rid)
                ana = float(pr.get("ana_brut") or 0) + float(
                    pr.get("ekstra_mesai_brut") or 0
                )
                courier_cost_by_rest[rid] = courier_cost_by_rest.get(rid, 0.0) + ana
            for line in (pr.get("destek_lines") or []):
                dest_rid = line.get("restaurant_id")
                if dest_rid:
                    drid = int(dest_rid)
                    amount = float(line.get("amount") or 0)
                    courier_cost_by_rest[drid] = (
                        courier_cost_by_rest.get(drid, 0.0) + amount
                    )

    result = []
    for r in rest_rows:
        rest_id = int(r["restaurant_id"])
        total_packages = int(r.get("total_packages") or 0)

        # Restorana yansıyan fatura (pricing_model'den)
        auto = auto_map.get(rest_id, {})
        billing_excl = float(auto.get("auto_invoice_excl_vat") or 0)

        # Bu restorana yansıyan kurye maliyeti (KDV DAHİL — kurye fatura kesiyor)
        # Yukarıda hesaplanan courier_cost_by_rest dict'ini kullan
        courier_cost_incl_vat = courier_cost_by_rest.get(rest_id, 0.0)
        # KDV hariç matrahı (CK için gerçek gider — KDV indirilebilir)
        courier_cost_excl_vat = courier_cost_incl_vat / 1.20 if courier_cost_incl_vat > 0 else 0.0

        # Paket başı metrikler (apples-to-apples: ikisi de KDV HARİÇ)
        # NOT (2026-05-27): 'cost_per_package' artık BASIT formülle hesaplanır:
        #   fatura ÷ paket — restoran perspektifi (paket başına ödediği ücret).
        #   Eski formül (kurye-maliyet ÷ paket) marj analizi için ayrı
        #   courier_cost_per_package alanı olarak korundu.
        billing_per_pkg = (billing_excl / total_packages) if total_packages > 0 else 0.0
        cost_per_pkg = billing_per_pkg  # ana metrik: fatura/paket
        courier_cost_per_pkg = (
            (courier_cost_excl_vat / total_packages) if total_packages > 0 else 0.0
        )
        # Marj = CK geliri − CK maliyeti (her ikisi KDV hariç matrah)
        margin = billing_excl - courier_cost_excl_vat
        margin_pct = (margin / billing_excl * 100) if billing_excl > 0 else 0.0

        # Sıfır paketse listeden çıkar
        if total_packages == 0 and billing_excl == 0:
            continue

        result.append({
            "restaurant_id": rest_id,
            "brand": r["brand"] or "—",
            "branch": r["branch"] or "—",
            "packages": total_packages,
            # Restorana kesilen fatura (KDV hariç matrah)
            "billing_excl_vat": round(billing_excl, 2),
            "billing_per_package": round(billing_per_pkg, 2),
            # CK maliyeti (marj hesabı için — KDV apples-to-apples)
            "courier_cost": round(courier_cost_excl_vat, 2),
            "courier_cost_incl_vat": round(courier_cost_incl_vat, 2),
            "courier_cost_per_package": round(courier_cost_per_pkg, 2),
            # Ana metrik: paket başı maliyet = fatura/paket (restoran perspektifi)
            "cost_per_package": round(cost_per_pkg, 2),
            # Marj (KDV hariç matrahların farkı — gerçek CK kârı)
            "margin": round(margin, 2),
            "margin_pct": round(margin_pct, 1),
            "auto_basis": auto.get("auto_basis"),
        })

    return result


def _get_cost_per_package_by_courier(period: str, conn, payroll: list[dict] | None = None) -> list[dict]:
    """Kurye bazlı paket başı maliyet (top 20 + bottom 5)."""
    if payroll is None:
        payroll_data = list_personnel_payroll(period)
        payroll = payroll_data.get("rows", []) if isinstance(payroll_data, dict) else []

    # N+1 query'i ortadan kaldır: tek JOIN ile personnel→restaurant mapping
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT p.id AS personnel_id, r.brand AS rest_brand
            FROM personnel p
            LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
            """
        )
        rest_map: dict[int, str] = {
            int(row["personnel_id"]): (row.get("rest_brand") or "—")
            for row in cur.fetchall()
        }

    result = []
    for p in payroll:
        pid = int(p.get("id", 0))
        packages = int(p.get("ana_packages", 0))
        brut = float(p.get("toplam_brut", 0))

        if packages > 0:
            cost_per_pkg = brut / packages
            result.append({
                "personnel_id": pid,
                "full_name": p.get("full_name") or "—",
                "rest_brand": rest_map.get(pid, "—"),
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


# ──────────────────────────────────────────────────────────────────
# Personel Hareketi — restoran detay/PDF için şeffaflık paneli
# ──────────────────────────────────────────────────────────────────


def get_personnel_movements(restaurant_id: int, period: str) -> dict:
    """Bir restoran × ay için personel hareket özeti.

    Restoran yetkilisine 'açık kapı bırakmayan' bir görünüm:
      • Bu ay kaç kurye atamasından ayrıldı (exit_date bu ayda)
      • Kaç yeni kurye katıldı (start_date bu ayda, atanmış)
      • Atanmamış kuryeler dışında kim çalıştı (joker, komşu şube,
        bölge müdürü/kaptan/RTS destek) — kaç gün, kaç paket
      • Ay içinde kaç gün operasyon kayıt aldı (kesintisiz mi)

    Returns:
        {
          "restaurant_id": int,
          "period": str,
          "exits": [{id, full_name, person_code, role, exit_date}],
          "joins": [{id, full_name, person_code, role, start_date}],
          "support_workers": [{id, full_name, person_code, role, source,
                              working_days, total_hours, total_packages}],
          "active_courier_count": int,    # ay sonunda atanmış aktif kurye
          "operation_days": int,           # kayıt olan gün sayısı
          "month_days": int,
          "uninterrupted": bool,
          "summary": str                    # tek satırlık restoran-dostu özet
        }
    """
    yyyy, mm = period.split("-")
    yyyy_i, mm_i = int(yyyy), int(mm)
    month_days = monthrange(yyyy_i, mm_i)[1]

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1) Bu ay çıkanlar (exit_date bu ay içinde, restoranı bu)
            cur.execute(
                """
                SELECT id, full_name, person_code, role,
                       exit_date::text AS exit_date
                FROM personnel
                WHERE assigned_restaurant_id = %s
                  AND exit_date IS NOT NULL
                  AND LEFT(exit_date::text, 7) = %s
                ORDER BY exit_date
                """,
                (restaurant_id, period),
            )
            exits = [dict(r) for r in cur.fetchall()]

            # 2) Bu ay katılanlar (start_date bu ay içinde, restoranı bu)
            cur.execute(
                """
                SELECT id, full_name, person_code, role,
                       start_date::text AS start_date
                FROM personnel
                WHERE assigned_restaurant_id = %s
                  AND start_date IS NOT NULL
                  AND LEFT(start_date::text, 7) = %s
                ORDER BY start_date
                """,
                (restaurant_id, period),
            )
            joins = [dict(r) for r in cur.fetchall()]

            # 3) Destek olarak çalışanlar — bu restoranda çalıştı ama
            #    assigned_restaurant_id farklı (veya NULL = Joker).
            cur.execute(
                """
                SELECT
                    p.id, p.full_name, p.person_code, p.role,
                    p.assigned_restaurant_id,
                    r2.brand AS home_brand,
                    r2.branch AS home_branch,
                    COUNT(DISTINCT d.entry_date) AS working_days,
                    COALESCE(SUM(d.worked_hours), 0)::float AS total_hours,
                    COALESCE(SUM(d.package_count), 0)::int AS total_packages
                FROM daily_entries d
                JOIN personnel p ON p.id = d.actual_personnel_id
                LEFT JOIN restaurants r2 ON r2.id = p.assigned_restaurant_id
                WHERE d.restaurant_id = %s
                  AND LEFT(d.entry_date::text, 7) = %s
                  AND COALESCE(d.worked_hours, 0) > 0
                  AND (p.assigned_restaurant_id IS NULL
                       OR p.assigned_restaurant_id <> %s)
                GROUP BY p.id, p.full_name, p.person_code, p.role,
                         p.assigned_restaurant_id, r2.brand, r2.branch
                ORDER BY working_days DESC, total_packages DESC
                """,
                (restaurant_id, period, restaurant_id),
            )
            support_rows = cur.fetchall()
            support_workers = []
            for r in support_rows:
                role = r.get("role") or ""
                # Kaynak tipi
                if "joker" in role.lower():
                    source = "joker"
                elif role in ("Bölge Müdürü", "Kaptan", "Restoran Takım Şefi"):
                    source = "yönetim"
                elif r.get("assigned_restaurant_id"):
                    source = "komşu_şube"
                else:
                    source = "diğer"
                home_label = ""
                if r.get("home_brand"):
                    home_label = r["home_brand"]
                    if r.get("home_branch"):
                        home_label += f" / {r['home_branch']}"
                support_workers.append({
                    "id": int(r["id"]),
                    "full_name": r.get("full_name"),
                    "person_code": r.get("person_code"),
                    "role": role,
                    "source": source,
                    "home_assignment": home_label,
                    "working_days": int(r.get("working_days") or 0),
                    "total_hours": round(float(r.get("total_hours") or 0), 1),
                    "total_packages": int(r.get("total_packages") or 0),
                })

            # 4) Operasyon günü sayısı (kayıt olan gün)
            cur.execute(
                """
                SELECT COUNT(DISTINCT entry_date) AS d
                FROM daily_entries
                WHERE restaurant_id = %s
                  AND LEFT(entry_date::text, 7) = %s
                  AND COALESCE(worked_hours, 0) > 0
                """,
                (restaurant_id, period),
            )
            row = cur.fetchone() or {"d": 0}
            operation_days = int(row.get("d") or 0)

            # 5) Ay sonu itibarıyla atanmış aktif kurye sayısı
            #    (status='Aktif' VEYA exit_date bu ayın sonundan sonra)
            month_end = f"{period}-{month_days:02d}"
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM personnel
                WHERE assigned_restaurant_id = %s
                  AND role IN ('Kurye', 'Joker')
                  AND (
                      COALESCE(status, 'Aktif') = 'Aktif'
                      OR COALESCE(exit_date::date, '1900-01-01'::date) > %s::date
                  )
                """,
                (restaurant_id, month_end),
            )
            ac = cur.fetchone() or {"n": 0}
            active_courier_count = int(ac.get("n") or 0)

            # 6) Hedef kurye sayısı (restoran kartından)
            cur.execute(
                "SELECT target_headcount FROM restaurants WHERE id = %s",
                (restaurant_id,),
            )
            tr = cur.fetchone() or {}
            target_headcount = int(tr.get("target_headcount") or 0)

            # 7) Ay içinde GERÇEKTEN çalışan unique kurye sayısı
            #    (kendi atanan + jokerler + destek/komşu/yönetim — hepsi)
            cur.execute(
                """
                SELECT COUNT(DISTINCT d.actual_personnel_id) AS n
                FROM daily_entries d
                WHERE d.restaurant_id = %s
                  AND LEFT(d.entry_date::text, 7) = %s
                  AND COALESCE(d.worked_hours, 0) > 0
                  AND d.actual_personnel_id IS NOT NULL
                """,
                (restaurant_id, period),
            )
            uc = cur.fetchone() or {"n": 0}
            actual_unique_couriers = int(uc.get("n") or 0)

            # 8) Ay içinde tek günde kapsanmamış (worked_hours=0 olan) gün var mı?
            #    Tam-gün hizmet kanıtı — operasyon kesintisi olup olmadığı.
            #    'uninterrupted' zaten operation_days >= month_days ile aynı.

    uninterrupted = operation_days >= month_days
    headcount_gap = actual_unique_couriers - target_headcount  # +/- fark

    # Özet cümle — restoran yetkilisi için
    parts: list[str] = []
    if exits:
        parts.append(f"{len(exits)} atanmış kurye ayrıldı")
    if joins:
        parts.append(f"{len(joins)} yeni kurye katıldı")
    if support_workers:
        joker_n = sum(1 for w in support_workers if w["source"] == "joker")
        komsu_n = sum(1 for w in support_workers if w["source"] == "komşu_şube")
        yonetim_n = sum(1 for w in support_workers if w["source"] == "yönetim")
        bits: list[str] = []
        if joker_n:
            bits.append(f"{joker_n} joker")
        if komsu_n:
            bits.append(f"{komsu_n} komşu şube kuryesi")
        if yonetim_n:
            bits.append(f"{yonetim_n} bölge müdürü/RTS")
        total_support_days = sum(w["working_days"] for w in support_workers)
        if bits:
            parts.append(
                f"toplam {len(support_workers)} destek (" + " + ".join(bits)
                + f") {total_support_days} mesai günü çalıştı"
            )

    if uninterrupted:
        op_status = (
            f"ay boyunca operasyon {operation_days}/{month_days} gün kesintisiz açık kaldı"
        )
    else:
        gap = month_days - operation_days
        op_status = (
            f"ay içinde {operation_days}/{month_days} gün kayıt var, "
            f"{gap} gün kayıt yok"
        )

    # Hedef vs gerçekleşen kurye analizi
    if target_headcount > 0:
        if actual_unique_couriers > target_headcount:
            extra = actual_unique_couriers - target_headcount
            headcount_note = (
                f"hedef {target_headcount} kurye iken ay içinde "
                f"{actual_unique_couriers} farklı kişi hizmet verdi "
                f"(+{extra} ek/joker/destek)"
            )
        elif actual_unique_couriers < target_headcount:
            short = target_headcount - actual_unique_couriers
            headcount_note = (
                f"hedef {target_headcount} kurye iken ay içinde "
                f"{actual_unique_couriers} kişi çalıştı (−{short} eksik)"
            )
        else:
            headcount_note = (
                f"hedef {target_headcount} kurye sayısı korundu "
                f"({actual_unique_couriers} kişi hizmet verdi)"
            )
    else:
        headcount_note = ""

    summary_parts: list[str] = []
    if headcount_note:
        summary_parts.append(headcount_note)
    if parts:
        summary_parts.append("; ".join(parts))
    summary_parts.append(op_status)
    summary = ". ".join(p[0].upper() + p[1:] if p else p for p in summary_parts if p) + "."

    return {
        "restaurant_id": restaurant_id,
        "period": period,
        "exits": exits,
        "joins": joins,
        "support_workers": support_workers,
        "active_courier_count": active_courier_count,
        "operation_days": operation_days,
        "month_days": month_days,
        "uninterrupted": uninterrupted,
        # Hedef vs gerçek kurye analizi (yeni)
        "target_headcount": target_headcount,
        "actual_unique_couriers": actual_unique_couriers,
        "headcount_gap": headcount_gap,
        "headcount_note": headcount_note,
        "summary": summary,
    }
