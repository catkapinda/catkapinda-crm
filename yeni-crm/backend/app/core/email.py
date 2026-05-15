"""SMTP üzerinden e-posta gönderimi.

Şu an sadece restoran performans raporu PDF'lerini gönderim için kullanılıyor.
Genişletilebilir bir EmailMessage helper'ı var.

Render env vars:
  SMTP_HOST       — örn. smtp.gmail.com / smtp.zoho.com / smtp.yandex.com.tr
  SMTP_PORT       — 587 (STARTTLS, default) / 465 (SSL) / 25 (plain)
  SMTP_USER       — info@catkapinda.com
  SMTP_PASS       — şifre veya uygulama şifresi
  SMTP_FROM       — gönderen adres (boşsa SMTP_USER kullanılır)
  SMTP_FROM_NAME  — gönderen ismi (default: 'Çat Kapında')
  SMTP_USE_TLS    — STARTTLS (587 için True, varsayılan True)
  SMTP_USE_SSL    — SMTPS (465 için True, varsayılan False)
  SMTP_BCC        — opsiyonel audit BCC (virgülle ayrılmış)
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import get_settings

log = logging.getLogger(__name__)


class EmailError(RuntimeError):
    """E-posta gönderim hatası."""


@dataclass
class Attachment:
    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"


def is_configured() -> bool:
    """SMTP minimum yapılandırma yapılmış mı?"""
    s = get_settings()
    return bool(s.smtp_host and s.smtp_user and s.smtp_pass)


def send_email(
    *,
    to: list[str] | str,
    subject: str,
    html_body: str | None = None,
    text_body: str | None = None,
    attachments: list[Attachment] | None = None,
    cc: list[str] | str | None = None,
) -> dict:
    """Tek bir e-posta gönder.

    Args:
        to: alıcı(lar)
        subject: konu
        html_body: HTML gövde (opsiyonel; text_body veya bu olmalı)
        text_body: plain-text gövde
        attachments: ek dosyalar
        cc: CC alıcılar

    Returns:
        {'sent': True, 'recipients': [...], 'message_id': '...'}

    Raises:
        EmailError: SMTP yapılandırması eksikse veya gönderim başarısızsa.
    """
    s = get_settings()
    if not is_configured():
        raise EmailError(
            "SMTP yapılandırması eksik. Render env vars: SMTP_HOST, "
            "SMTP_USER, SMTP_PASS gerekli."
        )
    if not html_body and not text_body:
        raise EmailError("html_body veya text_body en az biri gerekli.")

    to_list = [to] if isinstance(to, str) else list(to)
    cc_list = [cc] if isinstance(cc, str) else (list(cc) if cc else [])
    bcc_list = [
        b.strip() for b in (s.smtp_bcc or "").split(",") if b.strip()
    ]

    msg = EmailMessage()
    from_addr = (s.smtp_from or s.smtp_user).strip()
    msg["From"] = formataddr((s.smtp_from_name, from_addr))
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=from_addr.split("@", 1)[-1])

    # Plain-text fallback (HTML preview göstermeyen client'lar için)
    if text_body:
        msg.set_content(text_body)
    else:
        # html'den kaba bir text türetelim
        import re
        plain = re.sub(r"<[^>]+>", "", html_body or "").strip()
        msg.set_content(plain or " ")

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    # Ek dosyalar
    for att in attachments or []:
        maintype, _, subtype = att.mime_type.partition("/")
        if not subtype:
            maintype, subtype = "application", "octet-stream"
        msg.add_attachment(
            att.content,
            maintype=maintype,
            subtype=subtype,
            filename=att.filename,
        )

    all_recipients = list({*to_list, *cc_list, *bcc_list})

    try:
        if s.smtp_use_ssl:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                s.smtp_host, s.smtp_port, timeout=30,
            )
        else:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30)
            if s.smtp_use_tls:
                server.starttls()

        try:
            server.login(s.smtp_user, s.smtp_pass)
            server.send_message(msg, to_addrs=all_recipients)
        finally:
            try:
                server.quit()
            except Exception:
                pass

    except smtplib.SMTPAuthenticationError as e:
        log.exception("smtp auth error: %s", e)
        raise EmailError(
            "SMTP kimlik doğrulama başarısız. SMTP_USER / SMTP_PASS yanlış "
            "veya uygulama şifresi gerekiyor."
        ) from e
    except smtplib.SMTPException as e:
        log.exception("smtp error: %s", e)
        raise EmailError(f"SMTP hatası: {e}") from e
    except OSError as e:
        log.exception("smtp connection error: %s", e)
        raise EmailError(
            f"SMTP sunucuya bağlanılamadı ({s.smtp_host}:{s.smtp_port}): {e}"
        ) from e

    return {
        "sent": True,
        "recipients": all_recipients,
        "to": to_list,
        "cc": cc_list,
        "bcc": bcc_list,
        "message_id": msg["Message-ID"],
    }
