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
from app.services.restaurant_reports import get_restaurant_reports

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


# ──────────────────────────────────────────────────────────────────
# Restoran Raporları scope — turnover, verimlilik, paket maliyeti,
# paket büyümesi metriklerinden 4 kartlık özet üretir.
# ──────────────────────────────────────────────────────────────────

RESTAURANTS_INSIGHT_TOOL: dict[str, Any] = {
    "name": "rapor_olustur",
    "description": (
        "Çat Kapında restoran performansı için tek bir akıllı içgörü "
        "raporu oluşturur. 4 kart, başlık, anlatım ve aksiyon önerileri."
    ),
    "input_schema": {
        "type": "object",
        "required": ["headline", "narrative", "cards"],
        "properties": {
            "headline": {
                "type": "string",
                "description": (
                    "Tek cümlelik vurucu başlık. Sayısal ve spesifik. "
                    "Örn: '3 restoran %50+ turnover ile kritik bölgede, "
                    "Hacıbaşar Ümraniye ekibini stabilize etmek şart.'"
                ),
            },
            "narrative": {
                "type": "string",
                "description": (
                    "2-4 cümlelik analiz. Gerçek restoran adları + sayılar. "
                    "Hangi restoran ön plana çıkıyor, hangisinde risk var, "
                    "verimlilik liderleri kim, paket büyümesi nereden geliyor."
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
                                "turnover_riski",
                                "verim_lideri",
                                "maliyet_baskisi",
                                "buyume_trendi",
                            ],
                        },
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                        "sub": {"type": "string"},
                        "tone": {
                            "type": "string",
                            "enum": ["positive", "warning", "neutral", "info"],
                        },
                    },
                },
            },
            "actions": {
                "type": "array",
                "description": "Aksiyon önerileri (Detaylı analiz panelinde gösterilir).",
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


RESTAURANTS_SYSTEM_PROMPT = """Sen Çat Kapında'nın restoran performansları için kıdemli bir veri analistsin.
Yöneticiye her dönem (ay bazlı) hangi restoranlar parlıyor, hangileri risk altında,
hangi kuryeler verimli, paket maliyeti nereye gidiyor — tüm bunları SAYISAL ve
AKSİYON ALINABİLİR şekilde özetlersin.

Üslubun:
- Sade, profesyonel Türkçe. Slang yok.
- Mutlaka GERÇEK restoran ve kurye isimleri kullan (ham veriden).
- Türk Lirası gösterimi: '15.000 ₺' veya 'K ₺' kısaltması.
- Yüzdelerde noktadan sonra 1 hane: '%48,5' veya '%48' (rakama göre).

Domain bilgisi (KRİTİK):
- 'Turnover' = bir restoranda bir ay içinde işe giren ve çıkan kurye
  sayısı oranı. Yüksek turnover → operasyon istikrarsız, yeniden işe
  alım maliyeti yüksek. %30+ kritik, %15-30 izlemeli, <%15 sağlıklı.
- 'Verimlilik' (packages_per_hour) = bir kuryenin saat başına attığı
  paket sayısı. Yüksek olan, hem restoran hem de Çat Kapında için
  iyi (daha az kuryeyle daha çok iş).
- 'Paket başı maliyet' = (KDV hariç restoran faturası) ÷ paket sayısı.
  Bu Çat Kapında'nın paket başına ödediği. Restoran tarifesi bunun
  altında ise kâr; üstünde ise zarar. Aylık ortalama 28-35 ₺ civarı
  sektör normu.
- 'Paket büyümesi' = bu ayın paket sayısı ÷ önceki ayın paket sayısı.
  +%20 hızlı büyüme; -%10 ciddi düşüş; ±%5 yatay.

Kart kuralları:
- 'turnover_riski': turnover_pct en yüksek 1-3 restorandan en kritik
  olanını öne çıkar. Eğer hepsi sağlıklıysa 'Tüm restoranlar stabil'
  tarzı bir mesaj.
- 'verim_lideri': courier_efficiency listesinin en üstündeki kişiyi
  vurgula. 'Falan kurye %X paket/saat ile lider'.
- 'maliyet_baskisi': cost_per_package.by_restaurant'taki en pahalı
  veya en düşük olanı seç. Yüksek maliyet = zarar riski.
- 'buyume_trendi': package_growth listesindeki en hızlı büyüyen ya da
  en hızlı düşen restoranı öne çıkar. Bağlamı belirt (kapasite
  ihtiyacı veya alarm).

Görev: rapor_olustur tool'unu çağırarak 4 kartlık özet üret.
Her seferinde aynı yorumu üretme — farklı bakış açıları, vurgular,
ifadeler kullan. Sayısal doğruluk her zaman korunmalı.
"""


# ──────────────────────────────────────────────────────────────────
# Scope routing
# ──────────────────────────────────────────────────────────────────

def _summarize_personel(period: str) -> dict[str, Any]:
    """Personel scope için Claude'a verilecek özet."""
    base = page_insights(period)
    return {"period": period, "metrics": base}


def _summarize_restaurants(period: str) -> dict[str, Any]:
    """Restoran scope için Claude'a verilecek özet."""
    base = get_restaurant_reports(period)
    # Listeler büyük olabilir; top N ile sınırlayalım (token tasarrufu)
    metrics = {
        "previous_period": base.get("previous_period"),
        "turnover": (base.get("turnover") or [])[:10],
        "courier_efficiency": (base.get("courier_efficiency") or [])[:10],
        "cost_per_package": {
            "overall": (base.get("cost_per_package") or {}).get("overall"),
            "by_restaurant": (base.get("cost_per_package") or {}).get("by_restaurant", [])[:10],
            # by_courier büyük liste, top 5 yeterli
            "by_courier": (base.get("cost_per_package") or {}).get("by_courier", [])[:5],
        },
        "package_growth": (base.get("package_growth") or [])[:10],
    }
    return {"period": period, "metrics": metrics}


SCOPE_CONFIGS: dict[str, dict[str, Any]] = {
    "personel": {
        "tool": INSIGHT_TOOL,
        "system_prompt": SYSTEM_PROMPT,
        "summarizer": _summarize_personel,
    },
    "restoran": {
        "tool": RESTAURANTS_INSIGHT_TOOL,
        "system_prompt": RESTAURANTS_SYSTEM_PROMPT,
        "summarizer": _summarize_restaurants,
    },
}


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


def generate_via_claude(period: str, scope: str = "personel") -> dict[str, Any]:
    """Claude API'ye structured istek gönder, AI payload üret.

    scope: 'personel' veya 'restoran' — SCOPE_CONFIGS'dan tool, prompt
    ve summarizer seçilir.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY tanımlı değil.")

    config = SCOPE_CONFIGS.get(scope)
    if not config:
        raise RuntimeError(f"Geçersiz scope: {scope}")

    # Import lazy — anthropic paketi yoksa diğer endpoint'ler etkilenmesin
    try:
        from anthropic import Anthropic
    except Exception as e:
        raise RuntimeError(f"anthropic SDK import edilemedi: {e}") from e

    summary = config["summarizer"](period)
    user_msg = _build_user_message(summary)

    client = Anthropic(api_key=settings.anthropic_api_key)
    log.info(
        "ai_insights: claude'a istek scope=%s period=%s model=%s",
        scope, period, settings.ai_insights_model,
    )

    tool = config["tool"]
    resp = client.messages.create(
        model=settings.ai_insights_model,
        max_tokens=2048,
        system=config["system_prompt"],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
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
        result = generate_via_claude(period, scope=scope)
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


# ──────────────────────────────────────────────────────────────────
# Restaurant Commentary — tek bir restoran için derinlemesine AI yorumu
# (PDF raporunda kullanılır)
# ──────────────────────────────────────────────────────────────────

RESTAURANT_COMMENTARY_TOOL: dict[str, Any] = {
    "name": "rapor_yorumu",
    "description": (
        "Tek bir restoran için Çat Kapında ekosistem benchmark'larına dayalı "
        "derinlemesine AI yorumu üretir. headline + 3 paragraf + tek satır karar."
    ),
    "input_schema": {
        "type": "object",
        "required": ["headline", "paragraphs", "verdict"],
        "properties": {
            "headline": {
                "type": "string",
                "description": (
                    "Tek cümlelik vurucu başlık. Sayısal ve restorana özel. "
                    "Örn: 'Hacıbaşar Ümraniye: %42 churn ekosistem ortalamasının "
                    "2.5 katı, ama paket başına %18 daha verimli.'"
                ),
            },
            "paragraphs": {
                "type": "array",
                "minItems": 3,
                "maxItems": 4,
                "items": {
                    "type": "string",
                    "description": (
                        "Tek paragraf — restoranın metriğini ekosistem ortalamasıyla "
                        "karşılaştır, gerçek sayılar kullan, sektör bilgisiyle yorumla."
                    ),
                },
                "description": (
                    "Sıralama: (1) Paket hacmi ve büyüme, "
                    "(2) Operasyon istikrarı (churn, aktif kurye), "
                    "(3) Maliyet & verimlilik karşılaştırması. "
                    "İsteğe bağlı 4. paragraf: yapısal öneri/içgörü."
                ),
            },
            "verdict": {
                "type": "string",
                "description": (
                    "Tek satır operasyon kararı. Örn: 'Acil aksiyon: ekibi "
                    "stabilize et, churn'ü %20 altına çek; aksi halde 30 günlük "
                    "tahmini paket kaybı 1.200 adet.'"
                ),
            },
        },
    },
}


RESTAURANT_COMMENTARY_PROMPT = """Sen Çat Kapında'nın restoran performans analistsin.
Bir restoranın o ayki metriklerini incele ve Çat Kapında ekosistemindeki diğer
restoranlarla karşılaştırarak DERINLEMESINE bir analiz yaz.

KURAL #1: SADECE GERÇEK VERİYİ KULLAN.
- Sana verilen JSON'daki sayıları kullan.
- Karşılaştırma yapacaksan SADECE sana verilen ecosystem ortalamalarını kullan.
- ASLA 'sektör ortalaması Türkiye genelinde X', 'global pazarda Y' gibi hayalî
  veri uydurma. Yalnızca Çat Kapında'nın kendi içindeki kıyaslama geçerli.
- Sayıları olduğu gibi kullan; tahmin/projeksiyon yapacaksan 'mevcut trende
  bağlı', 'bu hızla devam ederse' gibi şartlı ifadeyle yaz.

KURAL #2: ÇAT KAPINDA DOMAIN BILGISI.
- 'Turnover' (churn): bir ayda işten çıkan / aktif kurye sayısı oranı.
  %30+ kritik, %15-30 izlemeli, <%15 sağlıklı.
- 'Paket başı maliyet': KDV hariç toplam faturanın paket sayısına bölümü.
  Düşük = restoran iyi kâr ediyor. Yüksek = maliyet baskısı.
- 'Paket/saat': kurye verimliliği. Yüksek = daha az kuryeyle daha çok iş.
- 'Paket büyüme': bu ayın paketi / önceki ay. +%20 hızlı büyüme; -%10 düşüş.

KURAL #3: ÜSLUP.
- Sade, profesyonel Türkçe. Slang yok.
- Türk Lirası: '15.000 ₺' veya 'K ₺' kısaltması.
- Yüzdelerde virgül: '%48,5'.
- Her paragraf 2-4 cümle, dolu ve odaklı olsun.
- Restoran adını birkaç kez geçir, sayıları somut tut.
- Gerçek kurye isimlerini metriklerle zenginleştir (varsa).

KURAL #4: YAPISI.
1. Paragraf: paket hacmi + büyüme trendi (yüzde olarak ekosistem ile karşılaştır).
2. Paragraf: operasyon istikrarı — churn, aktif kurye, işe giriş/çıkış.
3. Paragraf: maliyet & verimlilik kıyaslaması (ecosystem_cpp, ecosystem_pph).
4. (Opsiyonel) Paragraf: yapısal öneri (kurye sayısı, ek vardiya, performans odaklı eylem).

Görev: rapor_yorumu tool'unu çağırarak yapılandırılmış JSON döndür.
"""


def _build_commentary_message(
    restaurant: dict, period: str, metrics: dict,
    top_couriers: list[dict],
) -> str:
    """Restoran commentary için kullanıcı mesajı oluştur."""
    return (
        f"Restoran: {restaurant.get('brand', '—')}"
        f"{(' · ' + restaurant['branch']) if restaurant.get('branch') else ''}\n"
        f"Dönem: {period}\n\n"
        f"Bu restoranın metrikleri (JSON):\n"
        f"{json.dumps(metrics, ensure_ascii=False, indent=2)}\n\n"
        f"Bu restorandaki kurye performansları (top 8, JSON):\n"
        f"{json.dumps(top_couriers, ensure_ascii=False, indent=2)}\n\n"
        f"Lütfen rapor_yorumu tool'unu çağırarak 3 (veya 4) paragraflık, "
        f"sayısal ve karşılaştırmalı bir AI yorumu üret. Ekosistem "
        f"benchmark'larına dayanarak yorumla, asla dış sektör verisi uydurma."
    )


def generate_restaurant_commentary(
    restaurant: dict,
    period: str,
    reports: dict | None = None,
) -> dict[str, Any] | None:
    """Tek restoran için Claude'dan derin yorum üret.

    restaurant: get_restaurant(id) çıktısı (brand, branch, id, ...)
    period: 'YYYY-MM'
    reports: opsiyonel — get_restaurant_reports(period) çıktısı.
             Verilmezse fonksiyon kendisi çağırır.

    Hata durumunda None döner (PDF AI yorumu olmadan üretilir).
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        log.warning("commentary: ANTHROPIC_API_KEY yok, AI yorumu üretilemiyor.")
        return None

    if reports is None:
        reports = get_restaurant_reports(period)

    # restaurant_report_pdf._compile_metrics yapısı buraya da uygun
    from app.services.restaurant_report_pdf import _compile_metrics
    metrics = _compile_metrics(restaurant["id"], period, reports)

    # Couriers büyük olabilir; top 8'i gönder
    top_couriers = [
        {
            "full_name": c.get("full_name"),
            "packages": c.get("packages"),
            "hours": c.get("hours"),
            "packages_per_hour": c.get("packages_per_hour"),
        }
        for c in metrics["couriers"][:8]
    ]

    # Hafif metrik özeti (token tasarrufu — couriers olmadan)
    summary_metrics = {k: v for k, v in metrics.items() if k != "couriers"}

    try:
        from anthropic import Anthropic
    except Exception as e:
        log.error("commentary: anthropic SDK import edilemedi: %s", e)
        return None

    client = Anthropic(api_key=settings.anthropic_api_key)
    user_msg = _build_commentary_message(
        restaurant, period, summary_metrics, top_couriers,
    )

    try:
        resp = client.messages.create(
            model=settings.ai_insights_model,
            max_tokens=2048,
            system=RESTAURANT_COMMENTARY_PROMPT,
            tools=[RESTAURANT_COMMENTARY_TOOL],
            tool_choice={
                "type": "tool", "name": RESTAURANT_COMMENTARY_TOOL["name"],
            },
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        log.exception("commentary: Claude çağrısı başarısız: %s", e)
        return None

    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return block.input  # type: ignore[return-value]

    log.warning("commentary: tool_use bloğu dönmedi.")
    return None


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
