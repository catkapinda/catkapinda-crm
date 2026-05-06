"""Puantaj Onay servisi.

İş akışı:
1) Operasyon ekibi (puantajı giren BM/Kaptan) bir restoranın aylık puantajını
   tamamlayınca 'Onaya Gönder' der → puantaj_approvals tablosuna 'pending' kayıt.
2) Admin /puantaj-onaylari sayfasında bekleyenleri görür.
3) Admin 'Onayla' der → status='approved'. Reddederse 'rejected' + decision_notes.
4) Onaylanan kayıtlar bordroya hazır kabul edilir.

Aynı (restaurant_id, period) için birden fazla kayıt olamaz (UNIQUE).
Yeniden gönderim yapılmak istenirse mevcut kayıt güncellenir.
"""
from typing import Any

from psycopg.rows import dict_row

from app.core.database import get_connection


def _row_summary(restaurant_id: int, period: str) -> dict:
    """Restoranın o ay için puantaj özet rakamlarını çıkar (snapshot)."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS entry_count,
                    COALESCE(SUM(worked_hours), 0) AS total_hours,
                    COALESCE(SUM(package_count), 0) AS total_packages
                FROM daily_entries
                WHERE restaurant_id = %s
                  AND LEFT(entry_date::text, 7) = %s
                """,
                (restaurant_id, period),
            )
            row = cur.fetchone() or {}
    return {
        "entry_count": int(row.get("entry_count") or 0),
        "total_hours": float(row.get("total_hours") or 0),
        "total_packages": int(row.get("total_packages") or 0),
    }


def submit_for_approval(
    restaurant_id: int,
    period: str,
    submitted_by: str | None = None,
) -> dict:
    """Restoranın aylık puantajını onaya gönder.

    Aynı period için pending varsa snapshot güncellenir.
    Approved varsa pending durumuna geri çekilmez (admin önce iptal etmeli).
    """
    if not period or len(period) != 7:
        raise ValueError("period 'YYYY-MM' formatında olmalı")

    summary = _row_summary(restaurant_id, period)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO puantaj_approvals
                (restaurant_id, period, status, submitted_by, submitted_at,
                 entry_count, total_hours, total_packages)
                VALUES (%s, %s, 'pending', %s, now(), %s, %s, %s)
                ON CONFLICT (restaurant_id, period) DO UPDATE
                SET
                  status = CASE
                      WHEN puantaj_approvals.status = 'approved' THEN 'approved'
                      ELSE 'pending'
                  END,
                  submitted_by = EXCLUDED.submitted_by,
                  submitted_at = now(),
                  entry_count = EXCLUDED.entry_count,
                  total_hours = EXCLUDED.total_hours,
                  total_packages = EXCLUDED.total_packages,
                  decided_by = NULL,
                  decided_at = NULL,
                  decision_notes = NULL
                RETURNING id, restaurant_id, period, status,
                          submitted_by, submitted_at,
                          entry_count, total_hours, total_packages
                """,
                (
                    restaurant_id, period, submitted_by,
                    summary["entry_count"],
                    summary["total_hours"],
                    summary["total_packages"],
                ),
            )
            row = cur.fetchone()
            conn.commit()

    return _serialize(row)


def list_approvals(
    status: str | None = None,
    period: str | None = None,
) -> list[dict]:
    """Onay listesi — restoran + status'e göre filtre.

    Default: pending olanlar, en yeni başta.
    """
    sql = """
        SELECT
            a.id, a.restaurant_id, a.period, a.status,
            a.submitted_by, a.submitted_at,
            a.decided_by, a.decided_at, a.decision_notes,
            a.entry_count, a.total_hours, a.total_packages,
            r.brand AS rest_brand, r.branch AS rest_branch,
            r.pricing_model
        FROM puantaj_approvals a
        LEFT JOIN restaurants r ON r.id = a.restaurant_id
        WHERE 1=1
    """
    params: list[Any] = []
    if status:
        sql += " AND a.status = %s"
        params.append(status)
    if period:
        sql += " AND a.period = %s"
        params.append(period)
    sql += " ORDER BY a.submitted_at DESC"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [_serialize(r) for r in rows]


def get_approval(approval_id: int) -> dict | None:
    """Tek onay kaydı detayı."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.*, r.brand AS rest_brand, r.branch AS rest_branch,
                    r.pricing_model
                FROM puantaj_approvals a
                LEFT JOIN restaurants r ON r.id = a.restaurant_id
                WHERE a.id = %s
                """,
                (approval_id,),
            )
            row = cur.fetchone()
    return _serialize(row) if row else None


def get_for_restaurant(restaurant_id: int, period: str) -> dict | None:
    """Bir restoranın belirli ay için onay durumunu döner (yoksa None)."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.*, r.brand AS rest_brand, r.branch AS rest_branch
                FROM puantaj_approvals a
                LEFT JOIN restaurants r ON r.id = a.restaurant_id
                WHERE a.restaurant_id = %s AND a.period = %s
                LIMIT 1
                """,
                (restaurant_id, period),
            )
            row = cur.fetchone()
    return _serialize(row) if row else None


def decide(
    approval_id: int,
    status: str,  # 'approved' | 'rejected'
    decided_by: str | None = None,
    decision_notes: str | None = None,
) -> dict | None:
    """Admin onayı/reddi."""
    if status not in ("approved", "rejected"):
        raise ValueError(f"Geçersiz status: {status}")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE puantaj_approvals
                SET
                  status = %s,
                  decided_by = %s,
                  decided_at = now(),
                  decision_notes = %s
                WHERE id = %s
                RETURNING id, restaurant_id, period, status,
                          submitted_by, submitted_at,
                          decided_by, decided_at, decision_notes,
                          entry_count, total_hours, total_packages
                """,
                (status, decided_by, decision_notes, approval_id),
            )
            row = cur.fetchone()
            conn.commit()

    return _serialize(row) if row else None


def get_summary_by_period(period: str) -> dict:
    """O ay için özet sayılar (sidebar / dashboard için).

    {pending, approved, rejected, total_restaurants_active}
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, COUNT(*) FROM puantaj_approvals
                WHERE period = %s GROUP BY status
                """,
                (period,),
            )
            counts = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute("SELECT COUNT(*) FROM restaurants WHERE active = 1")
            row = cur.fetchone()
            total_active = row[0] if row else 0

    return {
        "period": period,
        "pending": counts.get("pending", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "total_restaurants_active": total_active,
    }


def _serialize(row: dict | None) -> dict:
    if not row:
        return {}
    return {
        "id": row.get("id"),
        "restaurant_id": row.get("restaurant_id"),
        "rest_brand": row.get("rest_brand"),
        "rest_branch": row.get("rest_branch"),
        "pricing_model": row.get("pricing_model"),
        "period": row.get("period"),
        "status": row.get("status"),
        "submitted_by": row.get("submitted_by"),
        "submitted_at": (
            row["submitted_at"].isoformat() if row.get("submitted_at") else None
        ),
        "decided_by": row.get("decided_by"),
        "decided_at": (
            row["decided_at"].isoformat() if row.get("decided_at") else None
        ),
        "decision_notes": row.get("decision_notes"),
        "entry_count": int(row.get("entry_count") or 0),
        "total_hours": float(row.get("total_hours") or 0),
        "total_packages": int(row.get("total_packages") or 0),
    }
