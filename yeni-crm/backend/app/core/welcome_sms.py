"""Welcome SMS — BM rolündeki kullanıcılara rastgele parola + SMS gönderir.

Akış (idempotent, sadece bir kez):
1. role='bm' AND phone IS NOT NULL AND welcome_sms_sent_at IS NULL
2. Her kullanıcı için 8 karakterlik rastgele parola üret
3. bcrypt hash → password_hash güncelle
4. NetGSM ile SMS gönder
5. welcome_sms_sent_at = now() (tekrar göndermez)

Startup hook olarak çağrılır (run_welcome_sms_for_pending_bm).
"""
from __future__ import annotations

import logging
import secrets
import string

from psycopg.rows import dict_row

from app.core.auth import hash_password
from app.core.database import get_connection
from app.core.sms import send_sms_allowlist_aware


log = logging.getLogger(__name__)


def _generate_password(length: int = 8) -> str:
    """8 karakterli okunabilir parola — sadece harf+rakam, ambiguous yok."""
    alphabet = (
        # Karışan karakterler hariç (0/O/o/1/I/l)
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnpqrstuvwxyz"
        "23456789"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def run_welcome_sms_for_pending_bm() -> None:
    """Pending BM kullanıcıları için karşılama SMS'i gönder.

    Render her startup'ta çağırır. Hatalar log'lanır, app açılmaya devam eder.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, full_name, phone
                    FROM users
                    WHERE role = 'bm'
                      AND status = 'active'
                      AND phone IS NOT NULL
                      AND welcome_sms_sent_at IS NULL
                    """
                )
                pending = cur.fetchall()

        if not pending:
            log.info("welcome_sms: bekleyen BM kullanıcı yok")
            return

        for user in pending:
            uid = int(user["id"])
            full_name = user.get("full_name") or "BM"
            phone = user.get("phone")
            if not phone:
                continue

            # Yeni parola üret + hash + DB güncelle
            new_password = _generate_password(8)
            new_hash = hash_password(new_password)

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET password_hash = %s,
                            welcome_sms_sent_at = now()
                        WHERE id = %s
                          AND welcome_sms_sent_at IS NULL
                        """,
                        (new_hash, uid),
                    )
                    rows_updated = cur.rowcount
                    conn.commit()

            if rows_updated == 0:
                # Yarış durumu — başka bir process zaten gönderdi
                continue

            # SMS gönder (allowlist/redirect aware)
            first_name = full_name.split()[0]
            message = (
                f"Merhaba {first_name}, Cat Kapinda CRM giris bilgileriniz:\n"
                f"Telefon: {phone}\n"
                f"Parola: {new_password}\n"
                f"Ilk giristen sonra Profil > Sifre Degistir ile yeni "
                f"parola belirleyin."
            )
            try:
                result = send_sms_allowlist_aware(phone, message)
                log.info(
                    "welcome_sms gönderildi: user_id=%s phone=%s***%s status=%s",
                    uid, phone[:3], phone[-2:], result.get("status"),
                )
            except Exception as e:  # noqa: BLE001
                # SMS başarısız → flag'i geri al ki tekrar denesin
                log.warning(
                    "welcome_sms başarısız user_id=%s: %s — flag geri alınıyor",
                    uid, e,
                )
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE users SET welcome_sms_sent_at = NULL "
                            "WHERE id = %s",
                            (uid,),
                        )
                        conn.commit()
    except Exception as e:  # noqa: BLE001
        log.exception("welcome_sms hook genel hata: %s", e)
