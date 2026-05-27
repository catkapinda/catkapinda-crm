"""Restoran kurye talepleri — ek kurye / kurye azaltma talepleri CRUD.

Bu modül restoran bazlı kurye sayısı değişiklik taleplerini yönetir.
Personel-bazlı `courier_requests` tablosundan (avans, motor değişikliği)
farklı — bu tablo restoran tarafından yapılan kapasite taleplerini tutar.

Alan modeli:
- request_date   : Talebin yapıldığı tarih (kullanıcı manuel girer)
- change_type    : 'add' (ek kurye) | 'remove' (azaltma)
- count          : Kaç kurye (default 1)
- note           : Gerekçe / serbest not
- status         : 'open' (talep edildi) | 'fulfilled' (karşılandı) | 'cancelled'
- fulfilled_at   : Karşılanma tarihi (status=fulfilled olduğunda dolar)
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Optional

from psycopg.rows import dict_row

from app.core.database import get_connection


log = logging.getLogger(__name__)


VALID_CHANGE_TYPES = ("add", "remove")
VALID_STATUSES = ("open", "fulfilled", "cancelled")


def _serialize(row: dict) -> dict:
    """psycopg row → JSON-safe dict (date/datetime → ISO)."""
    out: dict[str, Any] = dict(row)
    for key in ("request_date", "fulfilled_at"):
        v = out.get(key)
        if isinstance(v, (date, datetime)):
            out[key] = v.isoformat()
    for key in ("created_at", "updated_at"):
        v = out.get(key)
        if isinstance(v, datetime):
            out[key] = v.isoformat()
    return out


def list_for_restaurant(restaurant_id: int) -> list[dict]:
    """Bir restorana ait tüm talepleri yeniden eskiye sırala."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, restaurant_id, request_date, change_type, count,
                       note, status, fulfilled_at, created_by,
                       created_at, updated_at
                FROM restaurant_courier_requests
                WHERE restaurant_id = %s
                ORDER BY request_date DESC, id DESC
                """,
                (restaurant_id,),
            )
            return [_serialize(r) for r in cur.fetchall()]


def create_request(
    restaurant_id: int,
    request_date: str | date,
    change_type: str,
    count: int = 1,
    note: Optional[str] = None,
    created_by: Optional[str] = None,
) -> dict:
    """Yeni talep oluştur."""
    if change_type not in VALID_CHANGE_TYPES:
        raise ValueError(
            f"Geçersiz change_type: {change_type}. Beklenen: {VALID_CHANGE_TYPES}"
        )
    if count < 1:
        raise ValueError("count en az 1 olmalı")

    # Tarihi normalize et
    if isinstance(request_date, str):
        try:
            request_date = date.fromisoformat(request_date)
        except ValueError as e:
            raise ValueError(f"Geçersiz tarih formatı (YYYY-MM-DD bekleniyor): {e}")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO restaurant_courier_requests
                    (restaurant_id, request_date, change_type, count,
                     note, status, created_by)
                VALUES (%s, %s, %s, %s, %s, 'open', %s)
                RETURNING *
                """,
                (
                    restaurant_id, request_date, change_type, count,
                    note, created_by,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return _serialize(row)


def update_request(
    request_id: int,
    *,
    request_date: Optional[str | date] = None,
    change_type: Optional[str] = None,
    count: Optional[int] = None,
    note: Optional[str] = None,
    status: Optional[str] = None,
    fulfilled_at: Optional[str | date] = None,
) -> Optional[dict]:
    """Talep güncelle — sadece verilen alanları."""
    updates: list[str] = []
    params: list[Any] = []

    if request_date is not None:
        if isinstance(request_date, str):
            request_date = date.fromisoformat(request_date)
        updates.append("request_date = %s")
        params.append(request_date)

    if change_type is not None:
        if change_type not in VALID_CHANGE_TYPES:
            raise ValueError(f"Geçersiz change_type: {change_type}")
        updates.append("change_type = %s")
        params.append(change_type)

    if count is not None:
        if count < 1:
            raise ValueError("count en az 1 olmalı")
        updates.append("count = %s")
        params.append(count)

    if note is not None:
        updates.append("note = %s")
        params.append(note)

    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Geçersiz status: {status}")
        updates.append("status = %s")
        params.append(status)
        # Karşılandı işaretlenmişse ve fulfilled_at gönderilmediyse bugün
        if status == "fulfilled" and fulfilled_at is None:
            updates.append("fulfilled_at = current_date")

    if fulfilled_at is not None:
        if isinstance(fulfilled_at, str):
            fulfilled_at = date.fromisoformat(fulfilled_at) if fulfilled_at else None
        updates.append("fulfilled_at = %s")
        params.append(fulfilled_at)

    if not updates:
        # Hiç değişiklik yoksa mevcut kaydı dön
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM restaurant_courier_requests WHERE id = %s",
                    (request_id,),
                )
                row = cur.fetchone()
                return _serialize(row) if row else None

    updates.append("updated_at = now()")
    params.append(request_id)
    sql = (
        "UPDATE restaurant_courier_requests SET "
        + ", ".join(updates)
        + " WHERE id = %s RETURNING *"
    )

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
            conn.commit()
            return _serialize(row) if row else None


def delete_request(request_id: int) -> bool:
    """Talebi kalıcı sil."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM restaurant_courier_requests WHERE id = %s",
                (request_id,),
            )
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted


def summary_for_restaurant(restaurant_id: int) -> dict:
    """Restoran için talep özeti — kart için."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'open') AS open_count,
                    COUNT(*) FILTER (
                        WHERE status = 'open' AND change_type = 'add'
                    ) AS open_add_count,
                    COUNT(*) FILTER (
                        WHERE status = 'open' AND change_type = 'remove'
                    ) AS open_remove_count,
                    COUNT(*) FILTER (WHERE status = 'fulfilled') AS fulfilled_count,
                    MAX(request_date) FILTER (WHERE status = 'open') AS latest_open
                FROM restaurant_courier_requests
                WHERE restaurant_id = %s
                """,
                (restaurant_id,),
            )
            row = cur.fetchone() or {}
            return {
                "open_count": int(row.get("open_count") or 0),
                "open_add_count": int(row.get("open_add_count") or 0),
                "open_remove_count": int(row.get("open_remove_count") or 0),
                "fulfilled_count": int(row.get("fulfilled_count") or 0),
                "latest_open": (
                    row.get("latest_open").isoformat()
                    if row.get("latest_open")
                    else None
                ),
            }
