"""Box / ekipman geri alım servisi.

Kuryeden teslim alınan ekipman (varsayılan 'Box') kayıtlarını yönetir.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from psycopg.rows import dict_row

from app.core.database import get_connection


# Kondisyon seçenekleri — UI dropdown'unda kullanılır
CONDITION_OPTIONS: list[str] = [
    "Sağlam",
    "Hafif Hasarlı",
    "Ağır Hasarlı",
    "Kullanılamaz",
    "Eksik",
]

# Ekipman türü seçenekleri (default Box, ihtiyaç olursa genişletilir)
ITEM_OPTIONS: list[str] = [
    "Box",
    "Çanta",
    "Korumalı Mont",
    "Yağmurluk",
    "Kask",
    "Telefon Tutacağı",
]


def list_box_returns(
    *,
    personnel_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    condition: str | None = None,
    search: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """Filtrelere göre box_returns listesi (en yeni önce)."""
    sql = """
        SELECT
            b.id, b.personnel_id, b.item_name,
            b.return_date::text AS return_date,
            b.quantity, b.condition_status,
            COALESCE(b.payout_amount, 0)::float AS payout_amount,
            b.waived, b.notes,
            b.created_at, b.updated_at,
            COALESCE(p.full_name, '—') AS personnel_name,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(r.brand, '') AS rest_brand,
            COALESCE(r.branch, '') AS rest_branch
        FROM box_returns b
        LEFT JOIN personnel p ON p.id = b.personnel_id
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE 1=1
    """
    params: list[Any] = []
    if personnel_id is not None:
        sql += " AND b.personnel_id = %s"
        params.append(personnel_id)
    if date_from:
        sql += " AND b.return_date >= %s"
        params.append(date_from)
    if date_to:
        sql += " AND b.return_date <= %s"
        params.append(date_to)
    if condition:
        sql += " AND b.condition_status = %s"
        params.append(condition)
    if search and search.strip():
        sql += """ AND (
            COALESCE(p.full_name, '') ILIKE %s OR
            COALESCE(b.item_name, '') ILIKE %s OR
            COALESCE(b.notes, '') ILIKE %s
        )"""
        like = f"%{search.strip()}%"
        params.extend([like, like, like])
    sql += " ORDER BY b.return_date DESC, b.id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def get_box_return(box_return_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT b.*, COALESCE(p.full_name, '—') AS personnel_name
                FROM box_returns b
                LEFT JOIN personnel p ON p.id = b.personnel_id
                WHERE b.id = %s
                """,
                (box_return_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def stats_summary(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """KPI özet — toplam adet, toplam ödenen, tek kayıt sayısı, kurye sayısı."""
    sql = """
        SELECT
            COUNT(*)                  AS records_count,
            COALESCE(SUM(quantity),0) AS total_quantity,
            COALESCE(SUM(payout_amount),0)::float AS total_payout,
            COUNT(DISTINCT personnel_id) AS unique_personnel,
            COUNT(*) FILTER (WHERE waived = true) AS waived_count
        FROM box_returns
        WHERE 1=1
    """
    params: list[Any] = []
    if date_from:
        sql += " AND return_date >= %s"
        params.append(date_from)
    if date_to:
        sql += " AND return_date <= %s"
        params.append(date_to)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else {}


def _validate(payload: dict) -> dict:
    """Girdi doğrulama + normalize."""
    out: dict[str, Any] = {}

    pid = payload.get("personnel_id")
    if not pid:
        raise ValueError("Kurye seçilmeli.")
    out["personnel_id"] = int(pid)

    rd = (payload.get("return_date") or "").strip()
    if not rd:
        raise ValueError("Geri alım tarihi gerekli.")
    try:
        date.fromisoformat(rd)
    except ValueError as e:
        raise ValueError("Tarih formatı YYYY-AA-GG olmalı.") from e
    out["return_date"] = rd

    item = (payload.get("item_name") or "Box").strip() or "Box"
    out["item_name"] = item

    qty = int(payload.get("quantity") or 1)
    if qty < 1:
        raise ValueError("Adet en az 1 olmalı.")
    out["quantity"] = qty

    cond = (payload.get("condition_status") or "").strip()
    if not cond:
        raise ValueError("Kondisyon seçilmeli.")
    out["condition_status"] = cond

    payout = float(payload.get("payout_amount") or 0)
    if payout < 0:
        raise ValueError("Ödeme tutarı negatif olamaz.")
    out["payout_amount"] = payout

    out["waived"] = bool(payload.get("waived", False))
    out["notes"] = (payload.get("notes") or "").strip()

    return out


def create_box_return(payload: dict) -> dict:
    values = _validate(payload)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO box_returns
                    (personnel_id, item_name, return_date, quantity,
                     condition_status, payout_amount, waived, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    values["personnel_id"], values["item_name"],
                    values["return_date"], values["quantity"],
                    values["condition_status"], values["payout_amount"],
                    values["waived"], values["notes"],
                ),
            )
            new_id = cur.fetchone()["id"]
            conn.commit()
    return get_box_return(new_id) or {"id": new_id}


def update_box_return(box_return_id: int, payload: dict) -> dict:
    values = _validate(payload)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE box_returns SET
                    personnel_id = %s,
                    item_name = %s,
                    return_date = %s,
                    quantity = %s,
                    condition_status = %s,
                    payout_amount = %s,
                    waived = %s,
                    notes = %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    values["personnel_id"], values["item_name"],
                    values["return_date"], values["quantity"],
                    values["condition_status"], values["payout_amount"],
                    values["waived"], values["notes"],
                    box_return_id,
                ),
            )
            if cur.rowcount == 0:
                raise LookupError("Kayıt bulunamadı.")
            conn.commit()
    return get_box_return(box_return_id) or {"id": box_return_id}


def delete_box_return(box_return_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM box_returns WHERE id = %s", (box_return_id,))
            if cur.rowcount == 0:
                raise LookupError("Kayıt bulunamadı.")
            conn.commit()
