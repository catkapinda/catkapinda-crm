"""AI Insights servisi — Claude API ile Akıllı İçgörü üretimi.

İş akışı:
  1. cache lookup (period bazlı). Cache taze ise direkt döner.
  2. Cache yoksa veya bayatsa: DB'den özet veri çek
     (page_insights + ek metrikler).
  3. Claude API'ye structured tool-use ile gönder.
  4. JSON cevabı parse et, ai_insights_cache'e yaz.
  5. Sonucu döndür.

Cache yapısı: (scope='personel', period='YYYY-MM') UNIQUE.
TTL: settings.ai_insights_ttl_seconds (default 48h).
Hata: Claude API başarısız olursa eski cache (varsa) + stale=True,
yoksa raise — caller fallback yapar.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.core.config import get_settings
from app.core.database import get_connection
from app.services.personel import page_insights

log = logging.getLogger(__name__)


# Tool schema — Claude'un dönmesi gereken JSON yapısı
INSIGHT_TOOL = {
    "name": "rapor_olustur",
    "description": (
        "Çat Kapında kurye operasyonu için tek bir akıllı içgörü "
        "raporu oluşturur. 4 kart, başlık ve 2-4 cümlelik anlatım üretir."
    ),
    "input_schema": {
        "type": "object",
        "required": ["headline", "narrative", "cards"],
        "properties": {
            "headline": {
                "type": "string",
                "description": (
                    "Tek cümlelik başlık. Sayılarla dolu olmalı. "
                    "Örn: '5 kurye 390 paket eşiğini aşmak üzere — "
                    "ay sonuna kadar ek 15K ₺ fatura potansiyeli.'"
                ),
            },
            "narrative": {
                "type": "string",
                "description": (
                    "2-4 cümlelik analiz. Hangi kuryeler/restoranlar "
                    "öne çıkıyor, neden, ne yapılmalı. Spesifik isim, "
                    "sayı ve restoran kullan."
                ),
            },
            "cards": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "required": ["key", "label", "value", "sub"],
                    "properties": {
                        "key": {
                            "type": "string",
                            "enum": [
                                "esik_asimi",
                                "eksik_kapasite",
                                "verimlilik",
                                "bekleyen_aksiyon",
                            ],
                        },
                        "label": {
                            "type": "string",
                            "description": "Kart üst başlığı (örn. 'Eşik Aşımı')",
                        },
                        "value": {
                            "type": "string",
                            "description": "Hero metriği (örn. '5 kurye')",
                        },
                        "sub": {
                            "type": "string",
                            "description": "Alt satır açıklama (örn. '+15K ₺ ek fatura potansiyeli')",
                        },
                        "tone": {
                            "type": "string",
                            "enum": ["positive", "warning", "neutral", "info"],
                        },
                    },
                },
            },
            "actions": {
                "type": "array",
                "description": "Eylem önerileri (Detaylı analiz altında listelenir).",
                "items": {
                    "type": "object",
                    "required": ["title", "detail"],
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["yuksek", "orta", "dusuk"],
                        },
                    },
                },
            },
        },
    },
}


SYSTEM_PROMPT = """Sen Çat Kapında'nın kurye operasyonu için kıdemli bir veri analistsin.
Hızlı tempolu bir restoran kurye yönetim şirketinin yöneticisine her gün taze, sayısal,
aksiyon alınabilir 'Akıllı İçgörü' raporu sunarsın.

Üslubun:
- Sade, profesyonel Türkçe. Slang yok.
- Mutlaka GERÇEK sayılar ve isimler kullan (ham veriden gelen).
- Tahminlerde 'civarı, yaklaşık' gibi yumuşatma yapabilirsin.
- Sayıları ₺ ile yaz ve binlik ayraç olarak nokta kullan (örn. '15.000 ₺').
  Çok büyük rakamlarda 'K ₺' kısaltması serbest (örn. '15K ₺').

İş modeli ve rol bazlı maliyet mantığı (KRİTİK):
- 'Kurye' / 'Kaptan': değişken maliyet. Attıkları her paket × restoran
  tarifesi ile faturalanır, çalıştıkları her saat × saat tarifesi ile
  faturalanır. Aldıkları para, yaptıkları işin bire bir karşılığıdır.
  → BUNLARIN 'COVER' DEĞERİ HESAPLANMAZ, anlamı yoktur. Performansları
    'paket sayısı / eşik aşımı / saat verimliliği' üzerinden konuşulur.
- 'Bölge Müdürü' (BM) ve 'Joker': SABİT AYLIK MAAŞ alır (bizim cebimizden).
  Bu maaş baz olarak hep gider. AMA bu kişiler saha çalışmasına çıkıp
  paket attığında / saat doldurduğunda, o paket ve saatler de restoran
  faturasına yansır → bu yansıma sayesinde sabit maaşı 'geri kazanırlar'.
  → 'COVER' KAVRAMI YALNIZCA BM ve JOKER İÇİN GEÇERLİDİR.
  → %50+ cover oranı güçlü; %25-50 orta; <%25 düşük.
- 'Restoran Takım Şefi' (RTŞ): maaşı restoran ödüyor, bizim cebimizden
  değil. Attığı her ekstra paket bize ek kâr olarak gelir (× ~32 ₺ + KDV).
  → RTŞ için 'cover' kavramı kullanma.

Domain bilgisi:
- 'Eşik' = restoranın paket başına ödediği fiyat aşımı noktası.
  Eşik altı düşük tarife (rate_low), eşik üstü yüksek tarife (rate_high).
  Bir kurye eşiği aşınca o ayki TÜM paketleri yüksek tarifeyle faturalanır.
- 'Kapasite açığı' = bir restoranda planlanan kurye sayısının altında
  aktif personel olması. Operasyon riski demek.
- 'Bekleyen aksiyon' = puantaj onayları, profil değişiklik talepleri,
  motor/muhasebe değişiklik talepleri — admin onayını bekleyen şeyler.

Verimlilik kartı kuralı:
- 'verimlilik' kartında SADECE Bölge Müdürü veya Joker bahsedilmeli
  (top_recovery dizisinde gelen kişiler). 'Seyfullah Aksu Kurye' gibi
  bir kişiyi cover hero olarak ASLA gösterme — onun cover değeri
  hesaplanmaz, sadece performans rakamı vardır.
- top_recovery boşsa: 'Bu ay BM/Joker cover verisi yok' tarzı kısa
  bir mesaj göster, başka rol kişisini buraya koyma.

Görev: rapor_olustur tool'unu çağırarak 4 kartlık özet üret.
Her kart 'key' alanı sabit ('esik_asimi', 'eksik_kapasite',
'verimlilik', 'bekleyen_aksiyon'). label/value/sub Türkçe ve sayısal.
Her seferinde aynı raporu üretme — farklı bakış açıları, farklı
vurgular, farklı kelime seçimleri kullan. Tek değişmemesi gereken şey
sayısal doğruluk.
"""


def _ensure_table_exists() -> None:
    """Eğer migration koşturulmadıysa boşa düşmeyelim."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_insights_cache (
                    id SERIAL PRIMARY KEY,
                    scope varchar(40) NOT NULL DEFAULT 'personel',
                    period varchar(7) NOT NULL,
                    generated_at timestamptz NOT NULL DEFAULT now(),
                    payload jsonb NOT NULL,
                    model varchar(80),
                    input_tokens integer,
                    output_tokens integer,
                    UNIQUE (scope, period)
                )
                """
            )
            conn.commit()


def get_cached(scope: str, period: str) -> dict | None:
    """Cache'ten oku. Yoksa None."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT generated_at, payload, model, input_tokens, output_tokens
                FROM ai_insights_cache
                WHERE scope = %s AND period = %s
                """,
                (scope, period),
            )
            row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def is_stale(generated_at: datetime, ttl_seconds: int) -> bool:
    """Cache TTL'den eski mi?"""
    if generated_at is None:
        return True
    now = datetime.now(timezone.utc)
    age = (now - generated_at).total_seconds()
    return age > ttl_seconds


def _summarize_for_ai(period: str) -> dict[str, Any]:
    """page_insights + ek bağlam — Claude'a verilecek özet."""
    base = page_insights(period)
    # Buraya isteğe bağlı ek metrikler eklenebilir.
    # Şu an base yeterli — restoran-bazlı capacity_gaps, kurye-bazlı
    # threshold_near, top_recovery, pending_actions sayısı.
    return {
        "period": period,
        "metrics": base,
    }


def _build_user_message(summary: dict[str, Any]) -> str:
    period = summary["period"]
    m = summary["metrics"]
    parts = [
        f"Dönem: {period}",
        "",
        "Ham veri (JSON):",
        json.dumps(m, ensure_ascii=False, indent=2),
        "",
        "Lütfen rapor_olustur tool'unu çağırarak 4 kartlık özet üret. "
        "Her kart için label, value (kısa metrik), sub (1 satır açıklama) "
        "doldur. headline tek cümlelik vurucu olmalı, narrative 2-4 "
        "cümlelik gerçek isim/restoran/sayı içeren analiz olmalı. "
        "actions opsiyonel — operasyonel aksiyon önerileri.",
    ]
    return "\n".join(parts)


def generate_via_claude(period: str) -> dict[str, Any]:
    """Claude API'ye structured istek gönder, AI payload üret."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY tanımlı değil.")

    # Import lazy — anthropic paketi yoksa diğer endpoint'ler etkilenmesin
    try:
        from anthropic import Anthropic
    except Exception as e:
        raise RuntimeError(f"anthropic SDK import edilemedi: {e}") from e

    summary = _summarize_for_ai(period)
    user_msg = _build_user_message(summary)

    client = Anthropic(api_key=settings.anthropic_api_key)
    log.info("ai_insights: claude'a istek gönderiliyor period=%s model=%s",
             period, settings.ai_insights_model)

    resp = client.messages.create(
        model=settings.ai_insights_model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[INSIGHT_TOOL],
        tool_choice={"type": "tool", "name": INSIGHT_TOOL["name"]},
        messages=[{"role": "user", "content": user_msg}],
    )

    # tool_use bloğunu bul
    tool_input: dict[str, Any] | None = None
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            tool_input = block.input  # type: ignore[assignment]
            break

    if not tool_input:
        raise RuntimeError("Claude tool_use cevabı dönmedi.")

    payload = {
        "ai": tool_input,
        "raw": summary["metrics"],
    }
    return {
        "payload": payload,
        "model": getattr(resp, "model", settings.ai_insights_model),
        "input_tokens": getattr(resp.usage, "input_tokens", 0),
        "output_tokens": getattr(resp.usage, "output_tokens", 0),
    }


def upsert_cache(
    scope: str, period: str, payload: dict, model: str,
    input_tokens: int, output_tokens: int,
) -> None:
    """ai_insights_cache'e yaz (UNIQUE scope+period; varsa overwrite)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_insights_cache
                    (scope, period, payload, model, input_tokens, output_tokens, generated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (scope, period) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        model = EXCLUDED.model,
                        input_tokens = EXCLUDED.input_tokens,
                        output_tokens = EXCLUDED.output_tokens,
                        generated_at = now()
                """,
                (scope, period, Json(payload), model, input_tokens, output_tokens),
            )
            conn.commit()


def get_or_generate(
    period: str,
    force: bool = False,
    scope: str = "personel",
) -> dict[str, Any]:
    """Cache lookup + gerekirse Claude'a sor.

    force=True ise cache by-pass, taze AI çağrısı yapılır.
    Hata durumunda eski cache (varsa) stale=True ile döner;
    cache yoksa hata yukarı atılır — caller fallback yapar.
    """
    settings = get_settings()
    _ensure_table_exists()

    cached = get_cached(scope, period)
    fresh = cached and not is_stale(cached["generated_at"], settings.ai_insights_ttl_seconds)
    if cached and fresh and not force:
        return _shape_response(cached, stale=False)

    # Refresh dene
    try:
        result = generate_via_claude(period)
        upsert_cache(
            scope=scope,
            period=period,
            payload=result["payload"],
            model=result["model"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
        )
        new = get_cached(scope, period)
        return _shape_response(new, stale=False) if new else {
            "stale": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": result["payload"],
            "model": result["model"],
        }
    except Exception as e:
        log.exception("ai_insights generate failed: %s", e)
        if cached:
            # Eski cache'i stale işaretiyle dön
            return _shape_response(cached, stale=True, error=str(e))
        # Hiçbir cache yok → caller fallback yapsın
        raise


def _shape_response(cache_row: dict, stale: bool, error: str | None = None) -> dict[str, Any]:
    generated_at = cache_row["generated_at"]
    if isinstance(generated_at, datetime):
        generated_at_str = generated_at.isoformat()
    else:
        generated_at_str = str(generated_at)
    out: dict[str, Any] = {
        "stale": stale,
        "generated_at": generated_at_str,
        "payload": cache_row["payload"],
        "model": cache_row.get("model"),
    }
    if error:
        out["error"] = error
    return out
