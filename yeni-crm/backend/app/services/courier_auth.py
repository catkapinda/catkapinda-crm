"""Kurye kimlik doğrulama ve oturum yönetimi.

Basit oturum sistemi (Sprint 1):
- Giriş: person_code + TC'nin son 4 hanesi
- Oturum: 32 karakterlik rastgele token, 30 gün geçerlilik
- Veritabanı: courier_sessions tablosunda saklanır
"""
import secrets
from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row

from app.core.database import get_connection


def verify_credentials(person_code: str, last4_tc: str) -> dict | None:
    """Kimlik bilgilerini doğrula: person_code + TC'nin son 4 hanesi.

    Başarılı olursa personnel kaydını döner.
    """
    if not person_code or not last4_tc or len(last4_tc) != 4:
        return None

    sql = """
        SELECT
            id,
            person_code,
            full_name,
            role,
            tc_no,
            status
        FROM personnel
        WHERE UPPER(person_code) = UPPER(%s)
        AND status = 'Aktif'
        LIMIT 1
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (person_code,))
            row = cur.fetchone()

    if not row:
        return None

    # TC kontrolü: son 4 hane eşleşmelidir
    tc_no = str(row.get("tc_no") or "")
    if not tc_no or len(tc_no) < 4:
        return None

    if tc_no[-4:] != last4_tc:
        return None

    return {
        "id": row["id"],
        "person_code": row["person_code"],
        "full_name": row["full_name"],
        "role": row["role"],
    }


def create_session(personnel_id: int) -> dict:
    """Yeni oturum oluştur ve token döner.

    Geri döner: {token, expires_at}
    Token 32 karakter, 30 gün geçerlilik.
    """
    token = secrets.token_hex(16)  # 32 karakterlik hex string
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    sql = """
        INSERT INTO courier_sessions (personnel_id, token, expires_at, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING token, expires_at
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (personnel_id, token, expires_at, now))
            row = cur.fetchone()
        conn.commit()

    return {
        "token": row["token"],
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
    }


def get_session(token: str) -> int | None:
    """Token'dan personnel_id'yi döner.

    Token geçersiz veya süresi dolmuşsa None döner.
    """
    if not token or len(token) != 32:
        return None

    sql = """
        SELECT personnel_id, expires_at
        FROM courier_sessions
        WHERE token = %s
        LIMIT 1
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (token,))
            row = cur.fetchone()

    if not row:
        return None

    # Süresi dolmuş mu kontrolü
    expires_at = row.get("expires_at")
    if expires_at:
        expires_at_dt = (
            expires_at if isinstance(expires_at, datetime)
            else datetime.fromisoformat(str(expires_at))
        )
        # Naive datetime'ı UTC olarak varsay
        if expires_at_dt.tzinfo is None:
            expires_at_dt = expires_at_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at_dt:
            return None

    return row["personnel_id"]


def revoke_session(token: str) -> None:
    """Oturumu iptal et."""
    sql = "DELETE FROM courier_sessions WHERE token = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (token,))
        conn.commit()


def get_personnel_for_courier(personnel_id: int) -> dict | None:
    """Kurye bilgilerini döner — Profilim sayfasında düzenlenebilir alanlar dahil."""
    sql = """
        SELECT
            id,
            person_code,
            full_name,
            role,
            status,
            phone,
            current_plate,
            iban,
            address,
            emergency_contact_name,
            emergency_contact_phone,
            vehicle_type,
            accounting_type,
            assigned_restaurant_id
        FROM personnel
        WHERE id = %s
        LIMIT 1
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (personnel_id,))
            row = cur.fetchone()

    return dict(row) if row else None
