"""Kurye profil değişiklik talepleri servisi."""
from datetime import datetime
from typing import Any

from app.core.database import get_connection

# Kritik alanlar — admin onayı GEREK (talep akışı)
CRITICAL_FIELDS = {"phone", "iban", "address"}

# Düşük riskli alanlar — kurye DOĞRUDAN değiştirebilir (sadece log atılır)
DIRECT_EDITABLE_FIELDS = {
    "emergency_contact_name",
    "emergency_contact_phone",
    "birth_date",
    "tshirt_size",
}

# Backwards-compat: tüm düzenlenebilir alanlar
EDITABLE_FIELDS = CRITICAL_FIELDS | DIRECT_EDITABLE_FIELDS


def submit_change(personnel_id: int, field: str, new_value: str | None) -> dict[str, Any]:
    """Kritik alan için onay-gerekli değişiklik talebi gönder.

    - field CRITICAL_FIELDS'de olmalı
    - new_value current value'dan farklı olmalı
    - Aynı (personnel_id, field) için bekleyen talep varsa iptal et
    """
    if field not in CRITICAL_FIELDS:
        raise ValueError(
            f"Alan onay gerektirmiyor (doğrudan güncellenebilir): {field}"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Personel bilgisini oku
            cur.execute(
                f'SELECT {field} FROM personnel WHERE id = %s',
                (personnel_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Kurye bulunamadı")

            old_value = row[0]
            if old_value == new_value:
                raise ValueError("değişiklik yok")

            # Aynı alan için bekleyen talebi iptal et
            cur.execute(
                """
                UPDATE profile_change_requests
                SET status = 'İptal Edildi'
                WHERE personnel_id = %s AND field = %s AND status = 'Beklemede'
                """,
                (personnel_id, field)
            )

            # Yeni talebi ekle
            cur.execute(
                """
                INSERT INTO profile_change_requests
                (personnel_id, field, old_value, new_value, status)
                VALUES (%s, %s, %s, %s, 'Beklemede')
                RETURNING id, personnel_id, field, old_value, new_value, status,
                          requested_at, decided_at, decided_by, decision_notes
                """,
                (personnel_id, field, old_value, new_value)
            )
            result = cur.fetchone()
            conn.commit()

    return _serialize(result) if result else {}


def list_changes(
    status: str | None = None,
    personnel_id: int | None = None,
) -> list[dict[str, Any]]:
    """Profil değişiklik taleplerini listele (admin için).

    Personnel adı ve person_code ile join yap.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT
                    pcr.id, pcr.personnel_id, p.full_name, p.person_code,
                    pcr.field, pcr.old_value, pcr.new_value, pcr.status,
                    pcr.requested_at, pcr.decided_at, pcr.decided_by, pcr.decision_notes
                FROM profile_change_requests pcr
                LEFT JOIN personnel p ON pcr.personnel_id = p.id
                WHERE 1=1
            """
            params: list[Any] = []

            if status:
                query += " AND pcr.status = %s"
                params.append(status)

            if personnel_id:
                query += " AND pcr.personnel_id = %s"
                params.append(personnel_id)

            query += " ORDER BY pcr.requested_at DESC"

            cur.execute(query, params)
            rows = cur.fetchall()

    return [_serialize_with_personnel(r) for r in rows]


def get_change(change_id: int) -> dict[str, Any] | None:
    """Profil değişiklik talebini getir."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    pcr.id, pcr.personnel_id, p.full_name, p.person_code,
                    pcr.field, pcr.old_value, pcr.new_value, pcr.status,
                    pcr.requested_at, pcr.decided_at, pcr.decided_by, pcr.decision_notes
                FROM profile_change_requests pcr
                LEFT JOIN personnel p ON pcr.personnel_id = p.id
                WHERE pcr.id = %s
                """,
                (change_id,)
            )
            row = cur.fetchone()

    return _serialize_with_personnel(row) if row else None


def decide_change(
    change_id: int,
    status: str,  # "Onaylandı" | "Reddedildi"
    decided_by: str | None = None,
    decision_notes: str | None = None,
) -> dict[str, Any] | None:
    """Profil değişiklik talebini onayla/reddet.

    "Onaylandı" ise personnel tablosuna yeni değeri yaz.
    """
    if status not in ("Onaylandı", "Reddedildi"):
        raise ValueError(f"Geçersiz status: {status}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Talebi getir
            cur.execute(
                """
                SELECT id, personnel_id, field, new_value
                FROM profile_change_requests
                WHERE id = %s
                """,
                (change_id,)
            )
            row = cur.fetchone()
            if not row:
                return None

            change_id_check, personnel_id, field, new_value = row

            # Eğer onaylandıysa personnel'a yaz
            if status == "Onaylandı":
                cur.execute(
                    f"UPDATE personnel SET {field} = %s WHERE id = %s",
                    (new_value, personnel_id)
                )

            # Talebi güncelle
            cur.execute(
                """
                UPDATE profile_change_requests
                SET status = %s, decided_at = now(), decided_by = %s, decision_notes = %s
                WHERE id = %s
                RETURNING id, personnel_id, field, old_value, new_value, status,
                          requested_at, decided_at, decided_by, decision_notes
                """,
                (status, decided_by, decision_notes, change_id)
            )
            result = cur.fetchone()
            conn.commit()

    return _serialize(result) if result else None


def delete_change(change_id: int) -> bool:
    """Profil değişiklik talebini sil."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM profile_change_requests WHERE id = %s",
                (change_id,)
            )
            conn.commit()
            return cur.rowcount > 0


def count_pending_changes() -> int:
    """Bekleyen profil değişiklik talebi sayısı."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM profile_change_requests WHERE status = 'Beklemede'"
            )
            row = cur.fetchone()
            return row[0] if row else 0


# ─────────────────────────────────────────────────────────────────────
# Sprint 2: doğrudan düzenleme (düşük riskli alanlar) + log
# ─────────────────────────────────────────────────────────────────────


def direct_update(
    personnel_id: int, field: str, new_value: str | None
) -> dict[str, Any]:
    """Kuryenin doğrudan değiştirebildiği düşük riskli alanlar için
    anında personnel tablosunu günceller, courier_direct_changes'e log atar.

    Sadece DIRECT_EDITABLE_FIELDS'deki alanlar için çalışır.
    Kritik alanlar (phone/iban/address) için submit_change'i kullan.
    """
    if field not in DIRECT_EDITABLE_FIELDS:
        raise ValueError(
            f"Doğrudan düzenlenemez (onay gerekir): {field}"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT {field} FROM personnel WHERE id = %s',
                (personnel_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Kurye bulunamadı")

            old_value = row[0]
            # Boş -> boş
            if (old_value or "") == (new_value or ""):
                return {
                    "personnel_id": personnel_id,
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                    "changed": False,
                }

            # Personnel tablosunu güncelle
            cur.execute(
                f"UPDATE personnel SET {field} = %s WHERE id = %s",
                (new_value, personnel_id),
            )

            # Log
            cur.execute(
                """
                INSERT INTO courier_direct_changes
                (personnel_id, field, old_value, new_value)
                VALUES (%s, %s, %s, %s)
                """,
                (personnel_id, field, str(old_value or ""), str(new_value or "")),
            )

            conn.commit()

    return {
        "personnel_id": personnel_id,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "changed": True,
    }


def update_photo(personnel_id: int, photo_data_url: str | None) -> dict[str, Any]:
    """Profil fotoğrafını günceller.

    photo_data_url: data URI formatında base64 PNG/JPEG
    (örn 'data:image/jpeg;base64,/9j/4AAQ...')
    None gönderilirse fotoğraf kaldırılır.
    """
    # Boyut limiti — max ~500KB base64 (≈ 370KB binary)
    if photo_data_url and len(photo_data_url) > 700_000:
        raise ValueError("Fotoğraf çok büyük (max ~500KB)")

    if photo_data_url and not photo_data_url.startswith("data:image/"):
        raise ValueError("Geçersiz fotoğraf formatı")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE personnel
                SET profile_photo_data = %s
                WHERE id = %s
                """,
                (photo_data_url, personnel_id),
            )
            cur.execute(
                """
                INSERT INTO courier_direct_changes
                (personnel_id, field, old_value, new_value)
                VALUES (%s, 'profile_photo', %s, %s)
                """,
                (
                    personnel_id,
                    "(eski fotoğraf)" if photo_data_url else "(silindi)",
                    "(yeni fotoğraf)" if photo_data_url else "(silindi)",
                ),
            )
            conn.commit()

    return {
        "personnel_id": personnel_id,
        "has_photo": photo_data_url is not None,
    }


def list_my_direct_changes(personnel_id: int, limit: int = 30) -> list[dict[str, Any]]:
    """Kuryenin kendi doğrudan değişiklik logu (kişisel akış)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, field, old_value, new_value, changed_at
                FROM courier_direct_changes
                WHERE personnel_id = %s
                ORDER BY changed_at DESC
                LIMIT %s
                """,
                (personnel_id, limit),
            )
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "field": r[1],
            "old_value": r[2],
            "new_value": r[3],
            "changed_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


def _serialize(row: tuple | None) -> dict[str, Any]:
    """Veritabanı satırını dict'e çevir.

    Sütun sırası: id, personnel_id, field, old_value, new_value, status,
                  requested_at, decided_at, decided_by, decision_notes
    """
    if not row:
        return {}

    return {
        "id": row[0],
        "personnel_id": row[1],
        "field": row[2],
        "old_value": row[3],
        "new_value": row[4],
        "status": row[5],
        "requested_at": row[6].isoformat() if row[6] else None,
        "decided_at": row[7].isoformat() if row[7] else None,
        "decided_by": row[8],
        "decision_notes": row[9],
    }


def _serialize_with_personnel(row: tuple | None) -> dict[str, Any]:
    """Veritabanı satırını dict'e çevir (personnel join'li).

    Sütun sırası: id, personnel_id, full_name, person_code, field, old_value, new_value,
                  status, requested_at, decided_at, decided_by, decision_notes
    """
    if not row:
        return {}

    return {
        "id": row[0],
        "personnel_id": row[1],
        "personnel_name": row[2],
        "person_code": row[3],
        "field": row[4],
        "old_value": row[5],
        "new_value": row[6],
        "status": row[7],
        "requested_at": row[8].isoformat() if row[8] else None,
        "decided_at": row[9].isoformat() if row[9] else None,
        "decided_by": row[10],
        "decision_notes": row[11],
    }
