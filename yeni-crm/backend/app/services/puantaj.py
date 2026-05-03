"""Puantaj (daily_entries) servisi.

`entry_date` text tipindedir (YYYY-MM-DD). Bu yüzden ay filtresinde
`LEFT(entry_date::text, 7) = '2026-03'` cast'i kullanılır.
"""
from psycopg.rows import dict_row

from app.core.database import get_connection


def list_entries(
    period: str,
    restaurant_id: int | None = None,
    personnel_id: int | None = None,
    limit: int = 5000,
) -> list[dict]:
    """Bir ay için puantaj kayıtları (restoran + personel adı JOIN'lu)."""
    sql = """
        SELECT
            d.id,
            d.entry_date,
            d.restaurant_id,
            r.brand AS restaurant_brand,
            r.branch AS restaurant_branch,
            r.pricing_model,
            d.actual_personnel_id,
            d.planned_personnel_id,
            p.full_name AS personnel_name,
            p.person_code,
            p.role AS personnel_role,
            d.worked_hours,
            d.package_count,
            d.coverage_type,
            d.absence_reason,
            d.status,
            d.notes,
            d.monthly_invoice_amount
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel p ON p.id = d.actual_personnel_id
        WHERE LEFT(d.entry_date::text, 7) = %s
    """
    params: list = [period]

    if restaurant_id is not None:
        sql += " AND d.restaurant_id = %s"
        params.append(restaurant_id)
    if personnel_id is not None:
        sql += " AND d.actual_personnel_id = %s"
        params.append(personnel_id)

    sql += " ORDER BY d.entry_date DESC, r.brand, p.full_name LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)


def summary_by_restaurant(period: str) -> list[dict]:
    """Restoran bazında aylık özet — kart görünümü için."""
    sql = """
        SELECT
            r.id AS restaurant_id,
            r.brand,
            r.branch,
            r.pricing_model,
            r.target_headcount,
            COUNT(d.id) AS entries,
            COUNT(DISTINCT d.actual_personnel_id) AS unique_personnel,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COUNT(*) FILTER (
                WHERE d.absence_reason IS NOT NULL AND d.absence_reason <> ''
            ) AS absences
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE LEFT(d.entry_date::text, 7) = %s
        GROUP BY r.id, r.brand, r.branch, r.pricing_model, r.target_headcount
        ORDER BY r.brand NULLS LAST, r.branch NULLS LAST
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    # numerik tipleri normalize et (Decimal → float)
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "restaurant_id": r["restaurant_id"],
                "brand": r["brand"],
                "branch": r["branch"],
                "pricing_model": r["pricing_model"],
                "target_headcount": r["target_headcount"],
                "entries": int(r["entries"] or 0),
                "unique_personnel": int(r["unique_personnel"] or 0),
                "total_hours": float(r["total_hours"] or 0),
                "total_packages": int(r["total_packages"] or 0),
                "absences": int(r["absences"] or 0),
            }
        )
    return out


def daily_matrix(period: str) -> dict:
    """Personel × gün matrisi — puantaj grid sayfası için.

    Her personelin her günü için hücre verisi:
        type: normal | izin | gelmedi | raporlu | ihbarsiz | empty
        hours, packages, is_joker (destek)

    Sıralama: ana atanmış kuryeler restoran adına göre, sonra Joker/BM.
    """
    # 1. Aktif personel + atanmış restoran adı
    personnel_sql = """
        SELECT
            p.id, p.full_name, p.person_code, p.role,
            p.assigned_restaurant_id,
            r.brand AS rest_brand, r.branch AS rest_branch
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE COALESCE(p.status, 'Aktif') = 'Aktif'
        ORDER BY r.brand NULLS LAST, r.branch NULLS LAST,
                 p.role, p.person_code
    """

    # 2. O ayın tüm puantaj kayıtları
    entries_sql = """
        SELECT
            d.actual_personnel_id,
            d.entry_date,
            d.worked_hours,
            d.package_count,
            d.coverage_type,
            d.absence_reason,
            d.status,
            d.restaurant_id,
            p.assigned_restaurant_id
        FROM daily_entries d
        LEFT JOIN personnel p ON p.id = d.actual_personnel_id
        WHERE LEFT(d.entry_date::text, 7) = %s
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(personnel_sql)
            personnel = cur.fetchall()

            cur.execute(entries_sql, (period,))
            entries = cur.fetchall()

    # 3. Personel + gün → cell map
    by_pid_day: dict[tuple[int, int], dict] = {}
    for e in entries:
        pid = e["actual_personnel_id"]
        if pid is None:
            continue
        date_str = str(e["entry_date"])
        if not date_str or len(date_str) < 10:
            continue
        try:
            day = int(date_str[8:10])
        except ValueError:
            continue
        key = (pid, day)

        worked_hours = float(e.get("worked_hours") or 0)
        worked = worked_hours > 0
        coverage = (e.get("coverage_type") or "").strip()
        status = (e.get("status") or "").strip()
        absence = (e.get("absence_reason") or "").strip()

        # Hücre tipi
        if worked:
            cell_type = "normal"
        elif status == "İzin" or absence == "İzin":
            cell_type = "izin"
        elif "rapor" in absence.lower() or "rapor" in status.lower():
            cell_type = "raporlu"
        elif "ihbar" in absence.lower():
            cell_type = "ihbarsiz"
        elif absence:
            cell_type = "gelmedi"
        else:
            cell_type = "empty"

        # Destek mi (kendi atandığı restoran dışında çalışıyorsa)
        is_support = (
            coverage == "Destek"
            or (
                e["assigned_restaurant_id"] is not None
                and e["restaurant_id"] is not None
                and e["assigned_restaurant_id"] != e["restaurant_id"]
            )
        )

        # Mevcut kaydı koru — eğer zaten normal varsa onu üstüne yazma
        existing = by_pid_day.get(key)
        if existing and existing["type"] == "normal" and cell_type != "normal":
            continue

        by_pid_day[key] = {
            "type": cell_type,
            "hours": worked_hours,
            "packages": int(e.get("package_count") or 0),
            "is_support": is_support,
            "restaurant_id": e["restaurant_id"],
        }

    # 4. Her personel için 31 günlük dizi + toplam
    rows: list[dict] = []
    for p in personnel:
        cells = []
        total_hours = 0.0
        total_pkts = 0
        worked_days = 0
        joker_days = 0
        for day in range(1, 32):
            cell = by_pid_day.get((p["id"], day))
            if cell:
                cells.append(cell)
                if cell["type"] == "normal":
                    total_hours += cell["hours"]
                    total_pkts += cell["packages"]
                    worked_days += 1
                    if cell["is_support"]:
                        joker_days += 1
            else:
                cells.append({"type": "empty", "hours": 0, "packages": 0,
                              "is_support": False, "restaurant_id": None})
        rows.append({
            "id": p["id"],
            "full_name": p["full_name"],
            "person_code": p["person_code"],
            "role": p["role"],
            "rest_brand": p["rest_brand"],
            "rest_branch": p["rest_branch"],
            "cells": cells,
            "total_hours": round(total_hours, 1),
            "total_packages": total_pkts,
            "worked_days": worked_days,
            "joker_days": joker_days,
        })

    # 5. Aylık özet sayılar
    cell_counts: dict[str, int] = {}
    for cell in by_pid_day.values():
        cell_counts[cell["type"]] = cell_counts.get(cell["type"], 0) + 1

    return {
        "period": period,
        "rows": rows,
        "summary": {
            "total_hours": round(
                sum(r["total_hours"] for r in rows), 1),
            "total_packages": sum(r["total_packages"] for r in rows),
            "worked_days": sum(r["worked_days"] for r in rows),
            "joker_days": sum(r["joker_days"] for r in rows),
            "cell_counts": cell_counts,
            "personnel_count": len(rows),
        },
    }


def available_periods() -> list[str]:
    """Veride mevcut olan tüm aylar (YYYY-MM) — yeni → eski sıralı."""
    sql = """
        SELECT DISTINCT LEFT(entry_date::text, 7) AS period
        FROM daily_entries
        WHERE entry_date IS NOT NULL AND entry_date::text <> ''
        ORDER BY period DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [r[0] for r in rows if r[0]]
