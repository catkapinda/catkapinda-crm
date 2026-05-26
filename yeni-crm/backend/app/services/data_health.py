"""Sistem Veri Sağlığı — sanity checks.

Bir period için sistem genelinde 10 kontrol koşar ve her birini
green/yellow/red status + sample + öneri ile döner. Anomaliyi
kullanıcı fark etmeden önce bizim haberimiz olsun diye tasarlandı.

Endpoint: GET /api/data-health?period=YYYY-MM
"""
from __future__ import annotations

from datetime import date
from typing import Any

from psycopg.rows import dict_row

from app.core.database import get_connection


Severity = str  # 'green' | 'yellow' | 'red'


def _check_pricing_history(period: str) -> dict[str, Any]:
    """Tüm restoranların restaurant_pricing_history satırı var mı?"""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT r.id, r.brand, r.branch
                FROM restaurants r
                WHERE NOT EXISTS (
                    SELECT 1 FROM restaurant_pricing_history ph
                    WHERE ph.restaurant_id = r.id
                )
                ORDER BY r.brand, r.branch
                LIMIT 5
                """,
            )
            samples = cur.fetchall()
            cur.execute(
                """
                SELECT COUNT(*) AS n FROM restaurants r
                WHERE NOT EXISTS (
                    SELECT 1 FROM restaurant_pricing_history ph
                    WHERE ph.restaurant_id = r.id
                )
                """,
            )
            n_missing = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) AS n FROM restaurants")
            total = int(cur.fetchone()["n"])

    status: Severity = "green" if n_missing == 0 else ("yellow" if n_missing < 3 else "red")
    return {
        "key": "pricing_history_coverage",
        "label": "Tarife geçmişi (pricing_history) — eksik satır var mı?",
        "status": status,
        "count": n_missing,
        "total": total,
        "samples": [
            {
                "id": int(s["id"]),
                "name": f"{s['brand']} / {s['branch']}" if s["branch"] else s["brand"],
                "detail": "history satırı YOK — fatura 0 olabilir",
            }
            for s in samples
        ],
        "suggestion": (
            "Migration tetiklenirse otomatik backfill yapar; manuel için: "
            "INSERT INTO restaurant_pricing_history (...) SELECT FROM restaurants ..."
            if n_missing > 0 else "—"
        ),
    }


def _check_restaurant_rates_set(_: str) -> dict[str, Any]:
    """Aktif restoranların hepsinde tarife alanlarından en az biri dolu mu?"""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, brand, branch
                FROM restaurants
                WHERE active = 1
                  AND COALESCE(hourly_rate, 0) = 0
                  AND COALESCE(package_rate, 0) = 0
                  AND COALESCE(package_rate_low, 0) = 0
                  AND COALESCE(package_rate_high, 0) = 0
                  AND COALESCE(fixed_monthly_fee, 0) = 0
                ORDER BY brand, branch
                LIMIT 5
                """,
            )
            samples = cur.fetchall()
            cur.execute(
                """
                SELECT COUNT(*) AS n FROM restaurants
                WHERE active = 1
                  AND COALESCE(hourly_rate, 0) = 0
                  AND COALESCE(package_rate, 0) = 0
                  AND COALESCE(package_rate_low, 0) = 0
                  AND COALESCE(package_rate_high, 0) = 0
                  AND COALESCE(fixed_monthly_fee, 0) = 0
                """,
            )
            n = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) AS n FROM restaurants WHERE active = 1")
            total = int(cur.fetchone()["n"])

    status: Severity = "green" if n == 0 else "red"
    return {
        "key": "restaurant_rates_set",
        "label": "Aktif restoranların tarife alanları dolu mu?",
        "status": status,
        "count": n,
        "total": total,
        "samples": [
            {
                "id": int(s["id"]),
                "name": f"{s['brand']} / {s['branch']}" if s["branch"] else s["brand"],
                "detail": "Hiçbir tarife alanı dolu değil → fatura 0",
            }
            for s in samples
        ],
        "suggestion": (
            "Restoran düzenle modalından tarife alanlarını gir."
            if n > 0 else "—"
        ),
    }


def _check_zero_billing_with_puantaj(period: str) -> dict[str, Any]:
    """Period'da puantaj olan ama otomatik fatura 0 çıkan restoranlar?"""
    # Anomali: daily_entries varken billing 0 → tarife eksik veya hesap yanlış
    from app.services.collections import _compute_auto_invoice_map
    auto_map = _compute_auto_invoice_map(period)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT
                    r.id, r.brand, r.branch,
                    COALESCE(SUM(d.worked_hours), 0)::float AS hours,
                    COALESCE(SUM(d.package_count), 0)::int AS pkts
                FROM restaurants r
                JOIN daily_entries d ON d.restaurant_id = r.id
                WHERE LEFT(d.entry_date::text, 7) = %s
                  AND COALESCE(d.worked_hours, 0) > 0
                GROUP BY r.id, r.brand, r.branch
                """,
                (period,),
            )
            with_entries = cur.fetchall()

    problem = []
    for r in with_entries:
        rid = int(r["id"])
        billing = float(auto_map.get(rid, {}).get("auto_invoice_excl_vat") or 0)
        if billing <= 0:
            problem.append({
                "id": rid,
                "name": f"{r['brand']} / {r['branch']}" if r["branch"] else r["brand"],
                "detail": f"{r['hours']:.0f} sa, {r['pkts']} paket — fatura 0",
            })

    n = len(problem)
    status: Severity = "green" if n == 0 else ("yellow" if n <= 2 else "red")
    return {
        "key": "zero_billing_with_puantaj",
        "label": f"{period}: Puantaj var ama fatura 0 çıkan restoranlar?",
        "status": status,
        "count": n,
        "total": len(with_entries),
        "samples": problem[:5],
        "suggestion": (
            "Restoranların tarife alanlarını ya da pricing_history satırını kontrol et."
            if n > 0 else "—"
        ),
    }


def _check_margin_anomaly(period: str) -> dict[str, Any]:
    """Marj < %0 (zarar) veya > %60 (anormal yüksek) olan restoranlar?"""
    from app.services.restaurant_reports import get_restaurant_reports
    reports = get_restaurant_reports(period)
    by_rest = reports.get("cost_per_package", {}).get("by_restaurant", [])

    problem = []
    for r in by_rest:
        margin_pct = float(r.get("margin_pct") or 0)
        if margin_pct < 0 or margin_pct > 60:
            problem.append({
                "id": int(r.get("restaurant_id") or 0),
                "name": f"{r['brand']} / {r['branch']}" if r.get("branch") else r["brand"],
                "detail": (
                    f"marj %{margin_pct:.1f} — "
                    + ("zarar yapıyor" if margin_pct < 0 else "anormal yüksek (tarife denetimi gerekli)")
                ),
            })

    n = len(problem)
    status: Severity = "green" if n == 0 else ("yellow" if n <= 2 else "red")
    return {
        "key": "margin_anomaly",
        "label": f"{period}: Marj sağlık aralığı (%0–%60)",
        "status": status,
        "count": n,
        "total": len(by_rest),
        "samples": problem[:5],
        "suggestion": (
            "Negatif marj: tarife yetersiz; +%60: KDV mantığı veya pricing_model hatası olabilir."
            if n > 0 else "—"
        ),
    }


def _check_cost_per_package_anomaly(period: str) -> dict[str, Any]:
    """Paket başı maliyet [10, 60] ₺ aralığı dışında olan restoranlar?"""
    from app.services.restaurant_reports import get_restaurant_reports
    reports = get_restaurant_reports(period)
    by_rest = reports.get("cost_per_package", {}).get("by_restaurant", [])

    problem = []
    for r in by_rest:
        cost = float(r.get("cost_per_package") or 0)
        pkts = int(r.get("packages") or 0)
        if pkts > 50 and (cost < 10 or cost > 60):
            problem.append({
                "id": int(r.get("restaurant_id") or 0),
                "name": f"{r['brand']} / {r['branch']}" if r.get("branch") else r["brand"],
                "detail": f"paket başı maliyet {cost:.2f} ₺ — {pkts} paket için",
            })

    n = len(problem)
    status: Severity = "green" if n == 0 else ("yellow" if n <= 2 else "red")
    return {
        "key": "cost_per_package_anomaly",
        "label": f"{period}: Paket başı maliyet sağlık aralığı (10–60 ₺)",
        "status": status,
        "count": n,
        "total": len(by_rest),
        "samples": problem[:5],
        "suggestion": (
            "Düşük: kurye maliyet attribution hatası olabilir. "
            "Yüksek: courier_hourly_rate fazla veya paket sayısı düşük."
            if n > 0 else "—"
        ),
    }


def _check_orphan_entries(period: str) -> dict[str, Any]:
    """restaurant_id veya actual_personnel_id NULL olan entry'ler?"""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM daily_entries
                WHERE LEFT(entry_date::text, 7) = %s
                  AND COALESCE(worked_hours, 0) > 0
                  AND (restaurant_id IS NULL OR actual_personnel_id IS NULL)
                """,
                (period,),
            )
            n = int(cur.fetchone()["n"])
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM daily_entries
                WHERE LEFT(entry_date::text, 7) = %s
                """,
                (period,),
            )
            total = int(cur.fetchone()["n"])

    status: Severity = "green" if n == 0 else ("yellow" if n < 10 else "red")
    return {
        "key": "orphan_entries",
        "label": f"{period}: Restoran/kurye eşleşmesi olmayan kayıtlar",
        "status": status,
        "count": n,
        "total": total,
        "samples": [],
        "suggestion": (
            "Puantaj girişlerini kontrol et; restoran/kurye atama eksik kayıtlar."
            if n > 0 else "—"
        ),
    }


def _check_zero_payroll_active_couriers(period: str) -> dict[str, Any]:
    """Aktif kurye ama brüt 0 (puantajda kayıt var olmasına rağmen)?"""
    from app.services.payroll import list_personnel_payroll
    payroll = list_personnel_payroll(period)
    rows = payroll if isinstance(payroll, list) else payroll.get("rows", [])

    problem = []
    for r in rows:
        toplam_brut = float(r.get("toplam_brut") or 0)
        ana_hours = float(r.get("ana_hours") or 0)
        ana_pkts = int(r.get("ana_packages") or 0)
        destek = float(r.get("destek_brut") or 0)
        worked = ana_hours > 0 or ana_pkts > 0 or destek > 0
        if worked and toplam_brut == 0 and (r.get("role") or "") in ("Kurye", "Joker"):
            problem.append({
                "id": int(r.get("id") or 0),
                "name": r.get("full_name"),
                "detail": f"{ana_hours} sa, {ana_pkts} paket çalışmış ama brüt 0",
            })

    n = len(problem)
    status: Severity = "green" if n == 0 else ("yellow" if n <= 2 else "red")
    return {
        "key": "zero_payroll_active",
        "label": f"{period}: Çalışmış ama brüt 0 olan kuryeler",
        "status": status,
        "count": n,
        "total": len(rows),
        "samples": problem[:5],
        "suggestion": (
            "Kuryelerin atanmış restoranı + tarife alanları kontrol edilmeli."
            if n > 0 else "—"
        ),
    }


def _check_active_restaurants_without_couriers(_: str) -> dict[str, Any]:
    """Aktif restoran ama atanmış kurye 0?"""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT r.id, r.brand, r.branch
                FROM restaurants r
                WHERE r.active = 1
                  AND NOT EXISTS (
                      SELECT 1 FROM personnel p
                      WHERE p.assigned_restaurant_id = r.id
                        AND p.role IN ('Kurye', 'Joker')
                        AND COALESCE(p.status, 'Aktif') = 'Aktif'
                  )
                ORDER BY r.brand, r.branch
                LIMIT 5
                """,
            )
            samples = cur.fetchall()
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM restaurants r
                WHERE r.active = 1
                  AND NOT EXISTS (
                      SELECT 1 FROM personnel p
                      WHERE p.assigned_restaurant_id = r.id
                        AND p.role IN ('Kurye', 'Joker')
                        AND COALESCE(p.status, 'Aktif') = 'Aktif'
                  )
                """,
            )
            n = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) AS n FROM restaurants WHERE active = 1")
            total = int(cur.fetchone()["n"])

    status: Severity = "green" if n == 0 else "yellow"
    return {
        "key": "active_rest_no_courier",
        "label": "Aktif restoran ama atanmış kurye yok",
        "status": status,
        "count": n,
        "total": total,
        "samples": [
            {
                "id": int(s["id"]),
                "name": f"{s['brand']} / {s['branch']}" if s["branch"] else s["brand"],
                "detail": "Operasyon joker/desteklerle dönüyor olabilir",
            }
            for s in samples
        ],
        "suggestion": (
            "Bu restoranlar joker/destekle dönüyor — atama planı gözden geçirilebilir."
            if n > 0 else "—"
        ),
    }


def _check_personnel_status_mismatch(_: str) -> dict[str, Any]:
    """Status='Aktif' ama exit_date geçmiş tarih olan personel?"""
    today = date.today().isoformat()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, full_name, person_code, exit_date::text AS exit_date
                FROM personnel
                WHERE COALESCE(status, 'Aktif') = 'Aktif'
                  AND exit_date IS NOT NULL
                  AND exit_date::date < %s::date
                ORDER BY exit_date
                LIMIT 5
                """,
                (today,),
            )
            samples = cur.fetchall()
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM personnel
                WHERE COALESCE(status, 'Aktif') = 'Aktif'
                  AND exit_date IS NOT NULL
                  AND exit_date::date < %s::date
                """,
                (today,),
            )
            n = int(cur.fetchone()["n"])

    status: Severity = "green" if n == 0 else "yellow"
    return {
        "key": "personnel_status_mismatch",
        "label": "Status Aktif ama exit_date geçmiş personel",
        "status": status,
        "count": n,
        "total": -1,
        "samples": [
            {
                "id": int(s["id"]),
                "name": s["full_name"],
                "detail": f"{s['person_code']} — çıkış {s['exit_date']}",
            }
            for s in samples
        ],
        "suggestion": (
            "Pasife alınmalı; bordro ve atama dışı bırakılması için status='Pasif' yap."
            if n > 0 else "—"
        ),
    }


def _check_courier_rate_overrides(_: str) -> dict[str, Any]:
    """Quick China + Doğu Otomotiv courier override'ları var mı?"""
    expected = [
        ("quick china", "hourly_plus_package", 250, 25),
        ("doğu otomotiv", None, 295, None),
        ("dogu otomotiv", None, 295, None),  # diakritiksiz
    ]
    problems = []
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            for needle, exp_pm, exp_hr, exp_pr in expected:
                cur.execute(
                    """
                    SELECT id, brand, branch,
                           courier_pricing_model,
                           COALESCE(courier_hourly_rate, 0)::float AS hr,
                           COALESCE(courier_package_rate, 0)::float AS pr
                    FROM restaurants
                    WHERE LOWER(brand) LIKE %s
                    """,
                    (f"%{needle}%",),
                )
                rows = cur.fetchall()
                for r in rows:
                    issue = []
                    if exp_pm and (r["courier_pricing_model"] or "") != exp_pm:
                        issue.append(f"model={r['courier_pricing_model']} (beklenen {exp_pm})")
                    if exp_hr and abs(float(r["hr"]) - exp_hr) > 0.01:
                        issue.append(f"saatlik={r['hr']} (beklenen {exp_hr})")
                    if exp_pr and abs(float(r["pr"]) - exp_pr) > 0.01:
                        issue.append(f"paket={r['pr']} (beklenen {exp_pr})")
                    if issue:
                        problems.append({
                            "id": int(r["id"]),
                            "name": f"{r['brand']} / {r['branch']}" if r["branch"] else r["brand"],
                            "detail": "; ".join(issue),
                        })

    # Dedup by id
    seen = set()
    deduped = []
    for p in problems:
        if p["id"] not in seen:
            seen.add(p["id"])
            deduped.append(p)
    n = len(deduped)
    status: Severity = "green" if n == 0 else "yellow"
    return {
        "key": "courier_rate_overrides",
        "label": "Quick China + Doğu Otomotiv kurye override'ları uygulandı mı?",
        "status": status,
        "count": n,
        "total": -1,
        "samples": deduped[:5],
        "suggestion": (
            "Migration'da override eklendi; manuel: UPDATE restaurants SET "
            "courier_hourly_rate=..., courier_pricing_model=... WHERE brand ILIKE ..."
            if n > 0 else "—"
        ),
    }


def run_data_health_check(period: str) -> dict[str, Any]:
    """10 sanity check çalıştır + green/yellow/red özet."""
    checks: list[dict[str, Any]] = [
        _check_pricing_history(period),
        _check_restaurant_rates_set(period),
        _check_zero_billing_with_puantaj(period),
        _check_margin_anomaly(period),
        _check_cost_per_package_anomaly(period),
        _check_orphan_entries(period),
        _check_zero_payroll_active_couriers(period),
        _check_active_restaurants_without_couriers(period),
        _check_personnel_status_mismatch(period),
        _check_courier_rate_overrides(period),
    ]

    counts = {"green": 0, "yellow": 0, "red": 0}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1

    # Overall: kırmızı varsa red, sarı varsa yellow, hiçbiri yoksa green
    if counts["red"] > 0:
        overall = "red"
    elif counts["yellow"] > 0:
        overall = "yellow"
    else:
        overall = "green"

    return {
        "period": period,
        "checks": checks,
        "summary": {
            **counts,
            "overall_status": overall,
            "total_checks": len(checks),
        },
    }
