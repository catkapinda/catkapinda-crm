"""NetGSM REST v2 SMS gönderim modülü.

Env değişkenleri (config.py'de):
- SMS_PROVIDER: "netgsm"
- SMS_API_URL: "https://api.netgsm.com.tr/sms/rest/v2/send"
- SMS_NETGSM_USERNAME: hesap kullanıcı adı
- SMS_NETGSM_PASSWORD: hesap şifresi
- SMS_SENDER: gönderici (mesaj başlığı, NetGSM'de kayıtlı)

Kullanım:
    from app.core.sms import send_otp_sms
    send_otp_sms(phone="05551234567", code="123456", minutes=5)
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any
from urllib import error, request

from app.core.config import get_settings

log = logging.getLogger(__name__)

# Default endpoint (v2'den bilinen sabit)
DEFAULT_NETGSM_URL = "https://api.netgsm.com.tr/sms/rest/v2/send"

# OTP mesaj şablonu — kullanıcı tarafında değiştirilebilir
DEFAULT_MESSAGE_TEMPLATE = (
    "Cat Kapinda CRM giris kodu: {code}\n"
    "Kod {minutes} dakika gecerlidir. Kimseyle paylasmayin."
)


def normalize_phone(phone: str) -> str:
    """Türkiye telefon numarasını NetGSM'in beklediği 10 haneli formata getir.

    "0 555 555 55 55" / "+90 555 555 55 55" / "905555555555" → "5555555555"
    Tek başına başında 0 olmayan 10 hane "5XX..." de kabul edilir.
    """
    s = re.sub(r"\D", "", phone or "")
    if s.startswith("90") and len(s) == 12:
        s = s[2:]
    if s.startswith("0") and len(s) == 11:
        s = s[1:]
    if len(s) != 10:
        raise ValueError("Geçersiz telefon numarası — 10 haneli '5XX' bekleniyor")
    if not s.startswith("5"):
        raise ValueError("Türkiye GSM numarası 5 ile başlamalı")
    return s


def is_sms_configured() -> bool:
    """SMS env'leri tamamsa True döner."""
    s = get_settings()
    return bool(s.sms_netgsm_username and s.sms_netgsm_password and s.sms_sender)


def send_sms(phone: str, message: str) -> dict[str, Any]:
    """NetGSM REST v2 endpoint'ine SMS gönderir.

    Hata durumunda RuntimeError fırlatır. NetGSM cevabı log'a yazılır.
    """
    s = get_settings()
    if not is_sms_configured():
        raise RuntimeError("SMS gönderimi için NetGSM env'leri eksik")

    api_url = (s.sms_api_url or DEFAULT_NETGSM_URL).strip()
    if not api_url.endswith("/sms/rest/v2/send"):
        # Önceden sadece base URL girildiyse path ekle
        api_url = api_url.rstrip("/") + "/sms/rest/v2/send"

    phone10 = normalize_phone(phone)

    basic = base64.b64encode(
        f"{s.sms_netgsm_username}:{s.sms_netgsm_password}".encode("utf-8")
    ).decode("ascii")

    payload = {
        "msgheader": s.sms_sender,
        "messages": [
            {
                "msg": message,
                "no": phone10,
            }
        ],
        "encoding": "TR",
        "iysfilter": "",
        "partnercode": "",
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "Authorization": f"Basic {basic}",
    }

    req = request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            body = resp.read().decode("utf-8", errors="replace")
            log.info("netgsm send status=%s body=%s", status, body[:300])
            if status < 200 or status >= 300:
                raise RuntimeError(f"NetGSM HTTP {status}: {body[:200]}")
            return {"status": status, "body": body}
    except error.HTTPError as exc:
        log.warning("netgsm http error: %s", exc)
        raise RuntimeError("NetGSM SMS gönderimi başarısız (HTTP hata)") from exc
    except error.URLError as exc:
        log.warning("netgsm url error: %s", exc)
        raise RuntimeError("NetGSM sunucusuna ulaşılamadı") from exc


def send_sms_allowlist_aware(phone: str, message: str) -> dict[str, Any]:
    """Allowlist-bilinçli SMS gönderim sarmalayıcısı.

    `SMS_TEST_PHONES` env'i tanımlıysa sadece o listedeki numaralara
    gerçek SMS gider (staging davranışı). Listede olmayan numaralar
    için ``{"status": "not_in_allowlist", "phone": <10 hane>}`` döner —
    SMS GÖNDERİLMEZ. Allowlist boşsa (production) tüm numaralara
    normal gönderim yapılır.

    Telefon normalize hatası raise eder (numara geçersizse caller'ın
    yakalamasını bekleriz). NetGSM hatası ``RuntimeError`` olarak
    yukarı yansır.
    """
    s = get_settings()
    phone10 = normalize_phone(phone)

    if s.sms_allowlist_enabled and phone10 not in s.sms_test_phones_set:
        log.info(
            "sms allowlist skip phone=%s (allowlist=%d numara)",
            phone10[:3] + "***" + phone10[-2:],
            len(s.sms_test_phones_set),
        )
        return {"status": "not_in_allowlist", "phone": phone10}

    result = send_sms(phone10, message)
    return {"status": "sent", "phone": phone10, "raw": result}


def send_otp_sms(phone: str, code: str, minutes: int = 5) -> None:
    """OTP kodu için kısa SMS gönder."""
    msg = DEFAULT_MESSAGE_TEMPLATE.format(code=code, minutes=minutes)
    send_sms(phone, msg)
