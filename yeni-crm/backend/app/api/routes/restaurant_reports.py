"""Restoran Raporları endpoint'leri."""
import logging

from fastapi import APIRouter, HTTPException, Response

from app.core.email import Attachment, EmailError, is_configured, send_email
from app.services.ai_insights import (
    generate_restaurant_commentary,
    get_or_generate as get_or_generate_ai,
)
from app.services.restaurant_report_pdf import generate_restaurant_report_pdf
from app.services.restaurant_reports import get_restaurant_reports
from app.services.restaurants import get_restaurant

log = logging.getLogger(__name__)

router = APIRouter()


_TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


def _format_period_tr(period: str) -> str:
    try:
        y, m = period.split("-")
        return f"{_TR_MONTHS[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return period


def _ascii_safe(text: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in (text or "").encode("ascii", "ignore").decode("ascii"))
    return out or "rapor"


@router.get("")
async def get_reports(period: str = "2026-03") -> dict:
    """Tüm restoran raporlarını getir (turnover, efficiency, cost, growth).

    Query params:
    - period: "YYYY-MM" (default: "2026-03")

    Returns:
    {
        "period": "2026-03",
        "previous_period": "2026-02",
        "turnover": [...],
        "courier_efficiency": [...],
        "cost_per_package": {...},
        "package_growth": [...]
    }
    """
    return get_restaurant_reports(period)


@router.get("/ai-insights")
async def get_ai_insights(period: str = "2026-03", force: bool = False) -> dict:
    """Restoran raporları için Claude AI özet — 4 kart + headline + actions.

    Cache: 48 saat TTL (ai_insights_cache scope='restoran').
    force=true: cache by-pass, taze Claude çağrısı.

    Hata durumunda 503; frontend deterministik fallback gösterir.
    """
    try:
        return get_or_generate_ai(period=period, force=force, scope="restoran")
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ai_unavailable",
                "message": str(e),
            },
        ) from e


@router.get("/{restaurant_id}/pdf")
async def get_restaurant_report_pdf(
    restaurant_id: int,
    period: str = "2026-03",
    skip_ai: bool = False,
) -> Response:
    """Tek restoran için premium performans raporu (PDF).

    Query params:
    - period: "YYYY-MM"
    - skip_ai: true → AI yorumu üretme (hızlı preview için).
               Varsayılan false: Claude'dan derin yorum çek.

    Response: application/pdf
    """
    restaurant = get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(404, detail="Restoran bulunamadı.")

    reports = get_restaurant_reports(period)

    commentary = None
    if not skip_ai:
        try:
            commentary = generate_restaurant_commentary(
                restaurant, period, reports=reports,
            )
        except Exception as e:
            # AI başarısız olsa bile PDF üretmeye devam et
            log.warning("restaurant pdf: commentary üretilemedi: %s", e)
            commentary = None

    try:
        pdf_bytes = generate_restaurant_report_pdf(
            restaurant=restaurant,
            period=period,
            reports=reports,
            commentary=commentary,
        )
    except Exception as e:
        log.exception("restaurant pdf üretilemedi: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_generation_failed",
                "message": str(e),
            },
        ) from e

    # Filename: ASCII-safe ve tireli (HTTP header Latin-1 olmalı)
    filename = f"performans_{_ascii_safe(restaurant.get('brand') or '')}_{period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{restaurant_id}/send-email")
async def send_restaurant_report_email(
    restaurant_id: int,
    period: str = "2026-03",
) -> dict:
    """Bir restorana performans raporu PDF'ini e-posta ile gönder.

    Alıcı: restoranın contact_email alanı.
    Gönderim: SMTP üzerinden (Render env vars'ta tanımlı).
    PDF aynı endpoint mantığıyla (AI yorumu dahil) yeniden üretilir.

    Query params:
    - period: "YYYY-MM"

    Returns:
        {
            "sent": true,
            "recipient": "ornek@restoran.com",
            "message": "Rapor başarıyla gönderildi.",
            "message_id": "<...>"
        }
    """
    restaurant = get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(404, detail="Restoran bulunamadı.")

    recipient = (restaurant.get("contact_email") or "").strip()
    if not recipient:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "no_contact_email",
                "message": (
                    f"{restaurant.get('brand')} restoranının iletişim e-posta "
                    f"adresi (contact_email) tanımlı değil. Restoran kaydını "
                    f"güncelleyin."
                ),
            },
        )

    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "smtp_unavailable",
                "message": (
                    "SMTP yapılandırması yapılmamış. Render env vars: "
                    "SMTP_HOST, SMTP_USER, SMTP_PASS gerekli."
                ),
            },
        )

    # Raporu üret (AI yorumlu)
    try:
        reports = get_restaurant_reports(period)
        commentary = None
        try:
            commentary = generate_restaurant_commentary(
                restaurant, period, reports=reports,
            )
        except Exception as e:
            log.warning("send-email: commentary üretilemedi: %s", e)
            commentary = None

        pdf_bytes = generate_restaurant_report_pdf(
            restaurant=restaurant,
            period=period,
            reports=reports,
            commentary=commentary,
        )
    except Exception as e:
        log.exception("send-email: PDF üretilemedi: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_generation_failed",
                "message": str(e),
            },
        ) from e

    brand_label = restaurant.get("brand") or "Restoran"
    branch = restaurant.get("branch")
    if branch:
        brand_label = f"{brand_label} · {branch}"
    period_label = _format_period_tr(period)

    subject = f"{period_label} — {brand_label} Performans Raporu"
    filename = f"performans_{_ascii_safe(restaurant.get('brand') or '')}_{period}.pdf"

    contact_name = (restaurant.get("contact_name") or "").strip() or "Yetkili"
    html_body = f"""<!doctype html>
<html lang="tr">
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #0B0D17;">
  <div style="border-top: 4px solid #0F52BA; padding-top: 24px;">
    <div style="font-size: 11px; letter-spacing: 0.2em; color: #0F52BA; font-weight: 700; text-transform: uppercase; margin-bottom: 8px;">
      Çat Kapında · Performans Raporu
    </div>
    <h1 style="font-size: 22px; margin: 0 0 4px; color: #0A3F8F;">{brand_label}</h1>
    <div style="color: #4D5468; font-size: 14px; margin-bottom: 24px;">
      {period_label} dönemi
    </div>

    <p style="line-height: 1.6;">Merhaba {contact_name},</p>
    <p style="line-height: 1.6;">
      {period_label} dönemi için <b>{brand_label}</b> performans raporunuz
      ekte yer alıyor. Bu rapor; paket hacmi, ekibinizdeki kurye verimliliği,
      paket başı maliyet ve Çat Kapında ekosistemiyle karşılaştırmalı
      analizleri içerir. Raporun son bölümünde Claude AI tarafından üretilen,
      tamamen ham veriye dayalı bir yorum bulacaksınız.
    </p>
    <p style="line-height: 1.6;">
      Sorularınız veya görüşmek istediğiniz bir nokta olursa bu e-postayı
      yanıtlayabilirsiniz.
    </p>
    <p style="line-height: 1.6;">İyi çalışmalar,<br><b>Çat Kapında</b></p>
  </div>
  <hr style="border: none; border-top: 1px solid #ECEEF3; margin: 24px 0;">
  <div style="font-size: 11px; color: #8B92A7;">
    Çat Kapında Teknoloji Lojistik ve Dış Ticaret A.Ş. ·
    <a href="mailto:info@catkapinda.com" style="color: #0F52BA; text-decoration: none;">info@catkapinda.com</a>
  </div>
</body>
</html>"""

    text_body = (
        f"Merhaba {contact_name},\n\n"
        f"{period_label} dönemi için {brand_label} performans raporunuz "
        f"ekte yer alıyor. Bu rapor; paket hacmi, kurye verimliliği, "
        f"paket başı maliyet ve Çat Kapında ekosistemiyle karşılaştırmalı "
        f"analizleri içerir. Son bölümde Claude AI tarafından ham veriye "
        f"dayalı bir yorum bulacaksınız.\n\n"
        f"İyi çalışmalar,\n"
        f"Çat Kapında\n"
        f"info@catkapinda.com"
    )

    try:
        result = send_email(
            to=recipient,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            attachments=[
                Attachment(
                    filename=filename,
                    content=pdf_bytes,
                    mime_type="application/pdf",
                ),
            ],
        )
    except EmailError as e:
        log.exception("send-email failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "smtp_send_failed",
                "message": str(e),
            },
        ) from e

    return {
        "sent": True,
        "recipient": recipient,
        "message": f"Rapor {recipient} adresine gönderildi.",
        "message_id": result.get("message_id"),
    }
