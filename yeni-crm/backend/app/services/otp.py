"""SMS OTP servisi — kurye giriş için.

Akış:
1. Kurye telefonunu girer → request_otp_for_phone(phone)
   - Personel'i phone üzerinden bulur (status='Aktif')
   - 6 haneli kod üretir, hash'leyip courier_otp_codes'a kaydeder (5 dk geçerli)
   - NetGSM ile SMS gönderir
   - Kuryenin telefonunu maskelenmiş olarak döner: "0555 *** ** 78"

2. Kurye SMS'teki kodu girer → verify_otp(phone, code)
   - En son geçerli OTP'yi bul, hash karşılaştır
   - Doğruysa session yarat, kodu verified_at ile işaretle
   - Yanlışsa attempts++; 5 deneme sonra OTP geçersiz

Güvenlik:
- Kod hash'lenerek saklanır (sha256)
- 5 dakika TTL
- Max 5 yanlış deneme
- Aynı dakika içinde request_otp tekrar çağrılırsa (rate limit), eski kod hâlâ geçerli; yeni kod gönderilmez
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Any

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.core.sms import is_sms_configured, normalize_phone, send_otp_sms

log = logging.getLogger(__name__)

OTP_TTL_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_MIN_RESEND_SECONDS = 60  # 60 saniye geçmeden yeniden gönderme yok


def _digits_only(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _hash_code(code: str) -> str:
    """6 haneli kodu sha256 ile hash'le. Salt sabit (basit kullanım için yeterli)."""
    return hashlib.sha256(f"catkapinda-otp-v1::{code}".encode("utf-8")).hexdigest()


def _generate_code() -> str:
    """6 haneli rastgele kod üret."""
    n = secrets.randbelow(1_000_000)
    return f"{n:06d}"


def _mask_phone(phone10: str) -> str:
    """5XXXXXXXXX → 0 5XX *** ** XX"""
    if len(phone10) != 10:
        return phone10
    return f"0 {phone10[0:3]} *** ** {phone10[8:10]}"


def _find_personnel_by_phone(phone10: str) -> dict | None:
    """Aktif kuryeleri telefon numarasıyla bul.

    personnel.phone alanı çeşitli formatlarda olabilir (boşluk, parantez vs).
    Bu yüzden DB'deki regexp_replace ile sadece rakamları al, sonundaki 10 haneye bak.
    """
    sql = """
        SELECT id, full_name, phone, status, role
        FROM personnel
        WHERE COALESCE(status, 'Aktif') = 'Aktif'
          AND right(regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10) = %s
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (phone10,))
            row = cur.fetchone()
    return dict(row) if row else None


def request_otp_for_phone(
    phone: str, ip_address: str | None = None,
) -> dict[str, Any]:
    """Telefon numarasına OTP gönder. Telefon sistemde kayıtlı olmalı.

    Returns:
        {
            'sent': bool,
            'masked_phone': '0 555 *** ** 78',
            'expires_in_seconds': 300,
            'cooldown_seconds': 0,  # >0 ise yeniden gönderme için bekleme
        }
    """
    if not is_sms_configured():
        raise RuntimeError("SMS sağlayıcısı yapılandırılmamış (NetGSM env eksik)")

    phone10 = normalize_phone(phone)
    personnel = _find_personnel_by_phone(phone10)
    if not personnel:
        # Bilgi sızıntısı önle: aynı mesaj
        raise ValueError("Bu numaraya kayıtlı aktif kurye bulunamadı")

    pid = personnel["id"]
    masked = _mask_phone(phone10)
    now = datetime.utcnow()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Son OTP'yi bul, cooldown kontrolü
            cur.execute(
                """
                SELECT id, created_at, expires_at, verified_at
                FROM courier_otp_codes
                WHERE personnel_id = %s
                  AND verified_at IS NULL
                  AND expires_at > now()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (pid,),
            )
            last = cur.fetchone()

            if last:
                age = (now - last["created_at"].replace(tzinfo=None)).total_seconds()
                if age < OTP_MIN_RESEND_SECONDS:
                    return {
                        "sent": False,
                        "masked_phone": masked,
                        "expires_in_seconds": int(
                            (last["expires_at"].replace(tzinfo=None) - now)
                            .total_seconds()
                        ),
                        "cooldown_seconds": int(OTP_MIN_RESEND_SECONDS - age),
                    }

            # Yeni kod üret
            code = _generate_code()
            code_hash = _hash_code(code)
            expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

            cur.execute(
                """
                INSERT INTO courier_otp_codes
                (personnel_id, code_hash, phone_used, expires_at, ip_address)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (pid, code_hash, phone10, expires_at, ip_address),
            )
            conn.commit()

    # SMS gönder (DB'ye yazdıktan sonra; başarısızlıkta kayıt kalır, sorun yok — TTL sonra siler)
    try:
        send_otp_sms(phone10, code, minutes=OTP_TTL_MINUTES)
    except Exception as e:
        log.error("OTP SMS gönderilemedi: %s", e)
        raise RuntimeError(
            "SMS gönderimi başarısız oldu. Birazdan tekrar deneyin."
        ) from e

    return {
        "sent": True,
        "masked_phone": masked,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "cooldown_seconds": 0,
    }


def verify_otp(phone: str, code: str) -> dict[str, Any] | None:
    """OTP doğrula. Doğruysa personnel dict döner (None ise hata).

    Hatalı durumda ValueError fırlatır.
    """
    phone10 = normalize_phone(phone)
    code_clean = _digits_only(code)
    if len(code_clean) != 6:
        raise ValueError("Kod 6 haneli olmalı")

    personnel = _find_personnel_by_phone(phone10)
    if not personnel:
        raise ValueError("Numara bulunamadı")

    pid = personnel["id"]

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, code_hash, attempts, expires_at, verified_at
                FROM courier_otp_codes
                WHERE personnel_id = %s
                  AND verified_at IS NULL
                  AND expires_at > now()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (pid,),
            )
            row = cur.fetchone()

            if not row:
                raise ValueError("Geçerli kod bulunamadı, lütfen yeniden gönderin")

            if row["attempts"] >= OTP_MAX_ATTEMPTS:
                raise ValueError("Çok fazla yanlış deneme — yeniden kod isteyin")

            otp_id = row["id"]
            expected_hash = row["code_hash"]
            given_hash = _hash_code(code_clean)

            if not secrets.compare_digest(expected_hash, given_hash):
                cur.execute(
                    "UPDATE courier_otp_codes SET attempts = attempts + 1 WHERE id = %s",
                    (otp_id,),
                )
                conn.commit()
                raise ValueError("Kod hatalı")

            # Doğru — kullanıldı işaretle
            cur.execute(
                "UPDATE courier_otp_codes SET verified_at = now() WHERE id = %s",
                (otp_id,),
            )
            conn.commit()

    return personnel


def cleanup_expired_otps() -> int:
    """Eski OTP kayıtlarını temizle. Cron için."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM courier_otp_codes
                WHERE expires_at < now() - interval '1 day'
                """
            )
            conn.commit()
            return cur.rowcount
