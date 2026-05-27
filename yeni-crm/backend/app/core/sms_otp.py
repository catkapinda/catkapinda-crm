"""SMS OTP — telefon + 6-haneli kod ile parolasız giriş.

Akış:
1. POST /api/auth/sms-otp/request {phone}
   → 6-haneli kod üret, bcrypt hash, sms_otp_codes'a 5 dk geçerli kaydet
   → NetGSM ile kod SMS'i gönder
2. POST /api/auth/sms-otp/verify {phone, code}
   → en son geçerli (used_at IS NULL, expires_at > now()) kayıt bul
   → code_hash karşılaştır
   → eşleşirse used_at = now() set et, JWT token döndür

Güvenlik:
- Kod 6 hane (1.000.000 olasılık)
- bcrypt hash ile saklanır
- 5 dk geçerlilik (1 kez kullanılır)
- En fazla 5 yanlış deneme — sonra kayıt geçersiz sayılır
- Rate limit: aynı telefon için 60 sn içinde max 1 yeni kod
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from psycopg.rows import dict_row

from app.core.auth import _normalize_phone, get_user_by_phone
from app.core.database import get_connection
from app.core.sms import send_sms_allowlist_aware


log = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def _generate_code() -> str:
    """6-haneli numerik kod — kriptografik olarak güvenli."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def _verify_code(code: str, code_hash: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), code_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def request_otp(phone: str) -> dict:
    """Telefona OTP kodu gönder.

    Returns:
        {"sent": bool, "cooldown_seconds": int}
        Telefon sistemde kayıtlı değilse de True döner (user enumeration
        saldırısını engellemek için). SMS gönderilmez.
    """
    normalized = _normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        # Sessizce true döndür (privacy)
        return {"sent": True, "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS}

    # Kullanıcı sistemde var mı?
    user = get_user_by_phone(normalized)
    if not user or user.get("status") != "active":
        # Yine sessizce true (user enumeration koruması)
        return {"sent": True, "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS}

    # GÜVENLİK: yalnız BM rolüne SMS gönder. Admin kullanıcılar e-posta+parola
    # akışını kullanmalı; SMS OTP kötüye kullanılmasın.
    if user.get("role") != "bm":
        log.info(
            "otp request: kullanıcı BM değil, SMS gönderilmedi "
            "(id=%s, role=%s)",
            user.get("id"), user.get("role"),
        )
        # Privacy: sent=True göster ama gerçekte gönderme
        return {"sent": True, "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS}

    # Rate limit — son 60 saniye içinde başka bir kod gitti mi?
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT created_at FROM sms_otp_codes
                WHERE phone = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (normalized,),
            )
            last = cur.fetchone()
            if last:
                age = (
                    datetime.now(timezone.utc)
                    - last["created_at"].replace(tzinfo=timezone.utc)
                ).total_seconds()
                if age < OTP_RESEND_COOLDOWN_SECONDS:
                    remaining = int(OTP_RESEND_COOLDOWN_SECONDS - age)
                    return {"sent": False, "cooldown_seconds": remaining}

    # Yeni kod üret
    code = _generate_code()
    code_hash = _hash_code(code)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sms_otp_codes (phone, code_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (normalized, code_hash, expires_at),
            )
            conn.commit()

    # SMS gönder (NetGSM)
    first_name = (user.get("full_name") or "").split()[0] if user.get("full_name") else ""
    msg_prefix = f"Merhaba {first_name}, " if first_name else "Merhaba, "
    message = (
        f"{msg_prefix}Cat Kapinda CRM giris kodunuz: {code}\n"
        f"{OTP_EXPIRY_MINUTES} dakika gecerlidir. Kimseyle paylasmayin."
    )
    try:
        result = send_sms_allowlist_aware(normalized, message)
        log.info(
            "otp gönderildi: phone=%s***%s status=%s",
            normalized[:3], normalized[-2:], result.get("status"),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("otp SMS gönderilemedi phone=%s***%s: %s",
                    normalized[:3], normalized[-2:], e)
        # SMS başarısız olsa bile kayıt duruyor — yeniden gönderilebilir
        # Cooldown'a takılır ama kullanıcı 1 dk sonra tekrar deneyebilir

    return {"sent": True, "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS}


def verify_otp(phone: str, code: str) -> dict | None:
    """Kod doğrula.

    Returns:
        Eşleşirse: kullanıcı dict (id, email, phone, full_name, role)
        Aksi halde None
    """
    normalized = _normalize_phone(phone)
    code = (code or "").strip()
    if not normalized or not code or len(code) != 6:
        return None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # En son geçerli kayıt
            cur.execute(
                """
                SELECT id, code_hash, expires_at, attempts
                FROM sms_otp_codes
                WHERE phone = %s
                  AND used_at IS NULL
                  AND expires_at > now()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (normalized,),
            )
            row = cur.fetchone()
            if not row:
                return None

            # Çok deneme
            if int(row["attempts"]) >= OTP_MAX_ATTEMPTS:
                return None

            # Deneme sayacını artır
            cur.execute(
                "UPDATE sms_otp_codes SET attempts = attempts + 1 WHERE id = %s",
                (row["id"],),
            )

            if not _verify_code(code, row["code_hash"]):
                conn.commit()
                return None

            # Eşleşti — kodu tüket
            cur.execute(
                "UPDATE sms_otp_codes SET used_at = now() WHERE id = %s",
                (row["id"],),
            )
            conn.commit()

    # Kullanıcıyı dön
    user = get_user_by_phone(normalized)
    if not user or user.get("status") != "active":
        return None
    # GÜVENLİK: sadece BM rolü SMS OTP ile giriş yapabilir
    if user.get("role") != "bm":
        log.warning(
            "otp verify: BM olmayan kullanıcı SMS ile giriş denedi "
            "(id=%s, role=%s)",
            user.get("id"), user.get("role"),
        )
        return None
    return {
        "id": user["id"],
        "email": user.get("email"),
        "phone": user.get("phone"),
        "full_name": user["full_name"],
        "role": user["role"],
    }
