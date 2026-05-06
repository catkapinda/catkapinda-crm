"""Bordro hazır SMS bildirimleri.

Akış: bir restoran×ay puantajı admin tarafından onaylandığında
(`puantaj_approvals.decide(..., status='approved')`), o ayda söz konusu
restoranda çalışmış olan tüm kuryelere "bordron hazır, imzala" SMS'i
gönderilir. `payroll_sms_log` tablosundaki `UNIQUE(personnel_id, period)`
kısıtı sayesinde aynı kurye+ay için sadece **ilk** restoran onayında SMS
gider; sonraki onaylar de-duplikasyon ile atlanır.

Staging davranışı: `SMS_TEST_PHONES` env'i tanımlıysa sadece allowlist'teki
numaralara gerçek SMS gider, diğerleri `not_in_allowlist` durumuyla log'a
yazılır.
"""
from __future__ import annotations

import logging

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app.core.database import get_connection
from app.core.sms import is_sms_configured, send_sms_allowlist_aware

log = logging.getLogger(__name__)


# Türkçe ay isimleri — NetGSM TR encoding güvenliği için ASCII normalize
TR_MONTHS_ASCII = [
    "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
    "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
]


def _format_period_ascii(period: str) -> str:
    """``"2026-03"`` → ``"Mart 2026"`` (ASCII)."""
    try:
        y, m = period.split("-")
        idx = int(m) - 1
        if 0 <= idx < 12:
            return f"{TR_MONTHS_ASCII[idx]} {y}"
    except Exception:
        pass
    return period


def _build_message(period: str) -> str:
    """SMS metni — kısa, ASCII-safe, link içerir."""
    ay_yil = _format_period_ascii(period)
    return (
        f"Cat Kapinda: {ay_yil} bordron hazir.\n"
        f"Imzalamak icin: kurye.crmcatkapinda.com"
    )


def _list_couriers_for_restaurant_period(
    restaurant_id: int,
    period: str,
) -> list[dict]:
    """O restoranda o ay puantaj girişi olan kuryeleri (DISTINCT) çeker.

    `daily_entries.actual_personnel_id` üzerinden gruplama. Sadece aktif
    personel + telefonu mevcut olanlar değil — telefonsuz olanlar da gelir,
    onlar log'da `no_phone` olarak işaretlenir (ileride telefon eklenince
    el ile yeniden tetiklenebilsin diye).
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT p.id, p.full_name, p.phone
                FROM daily_entries de
                JOIN personnel p ON p.id = de.actual_personnel_id
                WHERE de.restaurant_id = %s
                  AND LEFT(de.entry_date::text, 7) = %s
                  AND de.actual_personnel_id IS NOT NULL
                  AND COALESCE(de.worked_hours, 0) > 0
                """,
                (restaurant_id, period),
            )
            return list(cur.fetchall())


def _record_log(
    personnel_id: int,
    period: str,
    status: str,
    phone_used: str | None,
    error: str | None,
    triggered_by_approval_id: int | None,
) -> bool:
    """SMS log'una kayıt at. UNIQUE(personnel_id, period) ihlali ``False`` döner
    (zaten gönderilmiş, dedup tetiklendi)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO payroll_sms_log
                      (personnel_id, period, status, phone_used, error,
                       triggered_by_approval_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (personnel_id, period, status, phone_used, error,
                     triggered_by_approval_id),
                )
                conn.commit()
        return True
    except UniqueViolation:
        # Zaten kaydı var → dedup
        return False
    except Exception as exc:
        log.warning(
            "payroll_sms_log insert failed personnel=%s period=%s: %s",
            personnel_id, period, exc,
        )
        return False


def _already_sent(personnel_id: int, period: str) -> bool:
    """Daha önce SMS gönderildiyse (`sent` veya `not_in_allowlist`) ``True``.

    `failed` ya da `no_phone` ise tekrar denenmesine izin vermek için ``False``
    döner (telefon eklenince/sorun düzelince retry edilebilsin)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM payroll_sms_log
                    WHERE personnel_id = %s AND period = %s
                      AND status IN ('sent', 'not_in_allowlist', 'dry_run')
                    LIMIT 1
                    """,
                    (personnel_id, period),
                )
                return cur.fetchone() is not None
    except Exception as exc:
        log.warning("_already_sent check failed: %s", exc)
        return False


def notify_couriers_for_approval(
    *,
    approval_id: int,
    restaurant_id: int,
    period: str,
) -> dict[str, int]:
    """Bir restoran×ay onaylandığında etkilenen kuryelere SMS gönderir.

    Aynı kurye+ay için tekrar gönderim yapılmaz (de-dup). Hatalar
    swallow edilir: tek bir kuryeye SMS gönderim hatası onay işlemini
    bozmaz, log'a `failed` olarak yazılır.

    Returns:
        Sayım sözlüğü: ``{sent, skipped_already_sent, no_phone,
        not_in_allowlist, failed, total}``
    """
    counts = {
        "sent": 0,
        "skipped_already_sent": 0,
        "no_phone": 0,
        "not_in_allowlist": 0,
        "failed": 0,
        "total": 0,
    }

    if not is_sms_configured():
        log.warning(
            "SMS env eksik — payroll bildirim atlandı approval=%s rest=%s period=%s",
            approval_id, restaurant_id, period,
        )
        return counts

    try:
        couriers = _list_couriers_for_restaurant_period(restaurant_id, period)
    except Exception as exc:
        log.error("courier list query failed: %s", exc)
        return counts

    counts["total"] = len(couriers)
    message = _build_message(period)

    for c in couriers:
        pid = int(c["id"])
        phone = (c.get("phone") or "").strip()
        full_name = c.get("full_name") or f"#{pid}"

        # 1) De-dup: zaten gönderilmiş mi?
        if _already_sent(pid, period):
            counts["skipped_already_sent"] += 1
            continue

        # 2) Telefon yok mu?
        if not phone:
            _record_log(
                pid, period, "no_phone", None, None, approval_id,
            )
            counts["no_phone"] += 1
            log.info("sms skip no_phone personnel=%s (%s)", pid, full_name)
            continue

        # 3) Allowlist-bilinçli gönderim
        try:
            result = send_sms_allowlist_aware(phone, message)
            status = result.get("status", "sent")
            phone_used = result.get("phone")
            inserted = _record_log(
                pid, period, status, phone_used, None, approval_id,
            )
            if not inserted:
                # Race: bu arada başka bir thread/onay log atmış
                counts["skipped_already_sent"] += 1
                continue
            if status == "sent":
                counts["sent"] += 1
                log.info("sms sent personnel=%s period=%s", pid, period)
            elif status == "not_in_allowlist":
                counts["not_in_allowlist"] += 1
        except ValueError as exc:
            # Geçersiz telefon formatı
            _record_log(
                pid, period, "failed", phone, f"invalid_phone: {exc}",
                approval_id,
            )
            counts["failed"] += 1
            log.warning(
                "sms invalid phone personnel=%s phone=%r: %s",
                pid, phone, exc,
            )
        except Exception as exc:
            _record_log(
                pid, period, "failed", phone, str(exc)[:300], approval_id,
            )
            counts["failed"] += 1
            log.warning(
                "sms failed personnel=%s period=%s: %s",
                pid, period, exc,
            )

    log.info(
        "payroll notify summary approval=%s rest=%s period=%s -> %s",
        approval_id, restaurant_id, period, counts,
    )
    return counts
