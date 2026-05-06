"""Bordro/sözleşme dijital imza servisi.

Kurye bir döneme ait bordrosunu kabul ettiğinde canvas'tan PNG data URI'si
gönderir ve `payroll_signatures` tablosuna kaydedilir. Tek dönem-tek imza.
"""
from typing import Any

from app.core.database import get_connection


# Imza maksimum boyutu — ~300KB base64 (~225KB binary PNG)
SIGNATURE_MAX_LEN = 400_000


def _validate_signature_data(data: str) -> None:
    if not data or not data.startswith("data:image/"):
        raise ValueError("Geçersiz imza formatı (data URI bekleniyor)")
    if len(data) > SIGNATURE_MAX_LEN:
        raise ValueError("İmza çok büyük")


def save_signature(
    personnel_id: int,
    period: str,
    signature_data: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Bordro imzasını kaydeder. Aynı (personnel, period) için varsa üzerine yazar."""
    if not period or len(period) != 7:
        raise ValueError("period 'YYYY-MM' formatında olmalı")
    _validate_signature_data(signature_data)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payroll_signatures
                (personnel_id, period, signature_data, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (personnel_id, period) DO UPDATE
                SET signature_data = EXCLUDED.signature_data,
                    signed_at = now(),
                    ip_address = EXCLUDED.ip_address,
                    user_agent = EXCLUDED.user_agent
                RETURNING id, personnel_id, period, signed_at, ip_address
                """,
                (personnel_id, period, signature_data, ip_address, user_agent),
            )
            row = cur.fetchone()
            conn.commit()

    if not row:
        return {}

    return {
        "id": row[0],
        "personnel_id": row[1],
        "period": row[2],
        "signed_at": row[3].isoformat() if row[3] else None,
        "ip_address": row[4],
    }


def get_signature(
    personnel_id: int, period: str, include_data: bool = False
) -> dict[str, Any] | None:
    """Verilen kurye+dönem için imza varsa döner.

    include_data False ise data alanı dönmez (liste sayfası için lightweight).
    """
    cols = "id, personnel_id, period, signed_at, ip_address"
    if include_data:
        cols += ", signature_data"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {cols} FROM payroll_signatures
                WHERE personnel_id = %s AND period = %s
                LIMIT 1
                """,
                (personnel_id, period),
            )
            row = cur.fetchone()

    if not row:
        return None

    out: dict[str, Any] = {
        "id": row[0],
        "personnel_id": row[1],
        "period": row[2],
        "signed_at": row[3].isoformat() if row[3] else None,
        "ip_address": row[4],
        "is_signed": True,
    }
    if include_data:
        out["signature_data"] = row[5]
    return out


def list_signatures_for_period(period: str) -> list[dict[str, Any]]:
    """Belirli ay için imza atan tüm kuryeler + ödeme bilgisi — admin için."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id, s.personnel_id, p.full_name, p.person_code,
                    p.role, p.iban,
                    s.period, s.signed_at, s.ip_address,
                    s.paid_at, s.paid_by, s.paid_amount
                FROM payroll_signatures s
                LEFT JOIN personnel p ON p.id = s.personnel_id
                WHERE s.period = %s
                ORDER BY s.paid_at NULLS FIRST, s.signed_at DESC
                """,
                (period,),
            )
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "personnel_id": r[1],
            "personnel_name": r[2],
            "person_code": r[3],
            "role": r[4],
            "iban": r[5],
            "period": r[6],
            "signed_at": r[7].isoformat() if r[7] else None,
            "ip_address": r[8],
            "paid_at": r[9].isoformat() if r[9] else None,
            "paid_by": r[10],
            "paid_amount": float(r[11]) if r[11] is not None else None,
        }
        for r in rows
    ]


def mark_paid(
    personnel_id: int,
    period: str,
    paid_by: str | None = None,
    paid_amount: float | None = None,
) -> dict[str, Any] | None:
    """İmzalı bordroyu 'ödendi' olarak işaretle.

    Returns:
        Güncellenmiş satır (paid_at vs.) veya kayıt yoksa None.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE payroll_signatures
                SET paid_at = now(),
                    paid_by = %s,
                    paid_amount = %s
                WHERE personnel_id = %s AND period = %s
                RETURNING id, personnel_id, period, signed_at,
                          paid_at, paid_by, paid_amount
                """,
                (paid_by, paid_amount, personnel_id, period),
            )
            row = cur.fetchone()
            conn.commit()
    if not row:
        return None
    return {
        "id": row[0],
        "personnel_id": row[1],
        "period": row[2],
        "signed_at": row[3].isoformat() if row[3] else None,
        "paid_at": row[4].isoformat() if row[4] else None,
        "paid_by": row[5],
        "paid_amount": float(row[6]) if row[6] is not None else None,
    }


def unmark_paid(personnel_id: int, period: str) -> bool:
    """Ödendi işaretini geri al (yanlış işaretlendiyse)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE payroll_signatures
                SET paid_at = NULL, paid_by = NULL, paid_amount = NULL
                WHERE personnel_id = %s AND period = %s
                """,
                (personnel_id, period),
            )
            conn.commit()
            return cur.rowcount > 0


def delete_signature(personnel_id: int, period: str) -> bool:
    """Admin tarafından silme (ör. yeniden imzalanması istenirse)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM payroll_signatures
                WHERE personnel_id = %s AND period = %s
                """,
                (personnel_id, period),
            )
            conn.commit()
            return cur.rowcount > 0
