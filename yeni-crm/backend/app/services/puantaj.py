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
