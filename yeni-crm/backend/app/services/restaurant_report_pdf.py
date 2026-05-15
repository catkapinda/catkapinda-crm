"""Restoran Performans Raporu PDF üretimi.

Çat Kapında brand'ine uygun, premium tasarımlı A4 raporu:
 • Hero (saks gradient + restoran adı + dönem)
 • 4 KPI kartı
 • Bu dönem vs. önceki dönem karşılaştırma
 • En verimli kurye listesi (top 8)
 • Paket büyümesi mini-bar
 • AI yorumu (Çat Kapında ekosistem benchmark'larına dayalı)

`get_restaurant_reports(period)` çıktısı + `restaurant_id` ile çalışır.
Sektör benchmark'ları için diğer restoranların ortalamaları kullanılır,
böylece AI uydurmaz — hepsi gerçek veriye dayanır.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ─── Font kayıt (payroll_pdf ile aynı pattern) ──────────────────────
FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"
FONT_REGULAR = "DejaVu"
FONT_BOLD = "DejaVu-Bold"
_fonts_registered = False


def _register_fonts() -> None:
    global _fonts_registered
    if _fonts_registered:
        return
    try:
        pdfmetrics.registerFont(
            TTFont(FONT_REGULAR, str(FONT_DIR / "DejaVuSans.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont(FONT_BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf"))
        )
        _fonts_registered = True
    except Exception:
        pass


# ─── Çat Kapında brand palet ────────────────────────────────────────
BRAND = colors.HexColor("#0F52BA")           # saks mavisi
BRAND_DARK = colors.HexColor("#0A3F8F")
BRAND_SOFT = colors.HexColor("#E8EFFB")
CREAM_50 = colors.HexColor("#FDFAF3")
CREAM_100 = colors.HexColor("#F5EDD8")
CREAM_300 = colors.HexColor("#C9AE7A")
TEXT = colors.HexColor("#0B0D17")
TEXT_2 = colors.HexColor("#4D5468")
TEXT_3 = colors.HexColor("#8B92A7")
BORDER = colors.HexColor("#ECEEF3")
DANGER = colors.HexColor("#B91C1C")
DANGER_SOFT = colors.HexColor("#FEE2E2")
SUCCESS = colors.HexColor("#15803D")
SUCCESS_SOFT = colors.HexColor("#D1FAE5")
AMBER = colors.HexColor("#92400E")
AMBER_SOFT = colors.HexColor("#FEF3C7")
PURPLE = colors.HexColor("#6B21A8")
PURPLE_SOFT = colors.HexColor("#F3E8FF")

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


def _format_period(period: str) -> str:
    try:
        y, m = period.split("-")
        return f"{TR_MONTHS[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return period


def _money(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _int(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", ".")


def _pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",") + "%"


def _styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    return {
        "hero_eyebrow": ParagraphStyle(
            "he", fontName=FONT_BOLD, fontSize=8.5,
            textColor=colors.HexColor("#C9AE7A"), leading=11,
        ),
        "hero_title": ParagraphStyle(
            "ht", fontName=FONT_BOLD, fontSize=24,
            textColor=colors.white, leading=28,
        ),
        "hero_sub": ParagraphStyle(
            "hs", fontName=FONT_REGULAR, fontSize=11,
            textColor=colors.HexColor("#CCDDF5"), leading=15,
        ),
        "hero_doc_label": ParagraphStyle(
            "hdl", fontName=FONT_BOLD, fontSize=7,
            textColor=colors.HexColor("#A8C0E8"), leading=10,
            alignment=TA_RIGHT,
        ),
        "hero_doc_val": ParagraphStyle(
            "hdv", fontName=FONT_REGULAR, fontSize=9.5,
            textColor=colors.white, leading=12,
            alignment=TA_RIGHT,
        ),
        "section_title": ParagraphStyle(
            "st", fontName=FONT_BOLD, fontSize=10,
            textColor=TEXT, leading=14, spaceAfter=4,
        ),
        "section_eyebrow": ParagraphStyle(
            "se", fontName=FONT_BOLD, fontSize=8,
            textColor=BRAND_DARK, leading=12, spaceAfter=2,
        ),
        "label": ParagraphStyle(
            "lbl", fontName=FONT_BOLD, fontSize=7,
            textColor=TEXT_3, leading=10, alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "kpiv", fontName=FONT_BOLD, fontSize=16,
            textColor=TEXT, leading=20, alignment=TA_CENTER,
        ),
        "kpi_sub": ParagraphStyle(
            "kpis", fontName=FONT_REGULAR, fontSize=7.5,
            textColor=TEXT_3, leading=10, alignment=TA_CENTER,
        ),
        "body": ParagraphStyle(
            "body", fontName=FONT_REGULAR, fontSize=9.5,
            textColor=TEXT_2, leading=14,
        ),
        "body_bold": ParagraphStyle(
            "bb", fontName=FONT_BOLD, fontSize=9.5,
            textColor=TEXT, leading=14,
        ),
        "small": ParagraphStyle(
            "sm", fontName=FONT_REGULAR, fontSize=8,
            textColor=TEXT_3, leading=11,
        ),
        "footer": ParagraphStyle(
            "ft", fontName=FONT_REGULAR, fontSize=7.5,
            textColor=TEXT_3, leading=10,
        ),
        "ai_para": ParagraphStyle(
            "ai", fontName=FONT_REGULAR, fontSize=9.5,
            textColor=TEXT, leading=15, spaceAfter=6,
        ),
        "ai_quote": ParagraphStyle(
            "aiq", fontName=FONT_BOLD, fontSize=11,
            textColor=BRAND_DARK, leading=16, spaceAfter=6,
        ),
    }


# ─── Render fonksiyonları ────────────────────────────────────────────

def _make_hero(restaurant: dict, period: str, styles: dict) -> Table:
    """Premium hero: minimal saks blok + altın krem accent çizgi."""
    period_label = _format_period(period)
    rest_brand = restaurant.get("brand") or "—"
    rest_branch = restaurant.get("branch") or ""
    rest_label = f"{rest_brand} · {rest_branch}" if rest_branch else rest_brand
    doc_no = f"RR-{period.replace('-', '')}-{str(restaurant.get('id', 0)).zfill(4)}"

    left = [
        Paragraph("ÇAT KAPINDA — PERFORMANS RAPORU", styles["hero_eyebrow"]),
        Spacer(1, 6),
        Paragraph(rest_label, styles["hero_title"]),
        Spacer(1, 4),
        Paragraph(f"{period_label} dönemi", styles["hero_sub"]),
    ]
    right = [
        Paragraph("BELGE NO", styles["hero_doc_label"]),
        Paragraph(doc_no, styles["hero_doc_val"]),
        Spacer(1, 8),
        Paragraph("DÜZENLEME", styles["hero_doc_label"]),
        Paragraph(date.today().strftime("%d.%m.%Y"), styles["hero_doc_val"]),
    ]

    t = Table([[left, right]], colWidths=[120 * mm, 54 * mm], rowHeights=[40 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        # İncelikli alt çizgi — krem accent, premium dokun
        ("LINEBELOW", (0, 0), (-1, -1), 2, CREAM_300),
    ]))
    return t


def _kpi_cell(
    label: str, value: str, sub: str, styles: dict,
    bg=BRAND_SOFT, value_color=BRAND,
) -> list:
    """Tek KPI hücresi içeriği."""
    return [
        Paragraph(label.upper(), styles["label"]),
        Spacer(1, 2),
        Paragraph(value, ParagraphStyle(
            "_v", fontName=FONT_BOLD, fontSize=15,
            textColor=value_color, leading=18, alignment=TA_CENTER,
        )),
        Spacer(1, 2),
        Paragraph(sub, styles["kpi_sub"]),
    ]


def _make_kpi_row(metrics: dict, styles: dict) -> Table:
    """4 KPI kartı: paket, fatura, paket başı maliyet, ort. paket/saat.

    Sub-değerler restoranın KENDİ verisinden (önceki ay karşılaştırması,
    en iyi kurye performansı vs.) türetilmiştir; başka restoranlarla
    kıyas yapılmaz.
    """
    growth = metrics.get("growth_pct", 0.0)
    growth_str = ("+" if growth >= 0 else "") + _pct(growth)
    top_courier = (metrics.get("couriers") or [{}])[0]
    top_pph = float(top_courier.get("packages_per_hour", 0))

    cells = [
        _kpi_cell(
            "Toplam Paket",
            _int(metrics["packages"]),
            f"Önceki dönem: {_int(metrics['previous_packages'])}  ·  {growth_str}",
            styles, value_color=BRAND,
        ),
        _kpi_cell(
            "Toplam Fatura (KDV H.)",
            _money(metrics["billing"]) + " ₺",
            f"Aktif kurye: {metrics['active_count']}",
            styles, value_color=SUCCESS,
        ),
        _kpi_cell(
            "Paket Başı Maliyet",
            _money(metrics["cost_per_package"]) + " ₺",
            "Bu dönem ortalaması",
            styles, value_color=AMBER,
        ),
        _kpi_cell(
            "Ort. Paket/Saat",
            f"{metrics['avg_pph']:.2f}".replace(".", ","),
            (f"En iyi: {top_pph:.2f}".replace(".", ",") if top_pph > 0
             else "Bu dönem ortalaması"),
            styles, value_color=PURPLE,
        ),
    ]
    col_w = (174 * mm) / 4
    t = Table([cells], colWidths=[col_w] * 4)
    t.setStyle(TableStyle([
        # Kart arka planları — minimal renk, beyaz alan dominantta
        ("BACKGROUND", (0, 0), (0, 0), BRAND_SOFT),
        ("BACKGROUND", (1, 0), (1, 0), SUCCESS_SOFT),
        ("BACKGROUND", (2, 0), (2, 0), AMBER_SOFT),
        ("BACKGROUND", (3, 0), (3, 0), PURPLE_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.white),
        # Üstte hafif vurgu çizgisi (her kart için kendi rengi)
        ("LINEABOVE", (0, 0), (0, 0), 1.5, BRAND),
        ("LINEABOVE", (1, 0), (1, 0), 1.5, SUCCESS),
        ("LINEABOVE", (2, 0), (2, 0), 1.5, AMBER),
        ("LINEABOVE", (3, 0), (3, 0), 1.5, PURPLE),
    ]))
    return t


def _make_comparison_box(metrics: dict, styles: dict) -> Table:
    """Bu dönem vs. önceki dönem karşılaştırma tablosu.

    Notlar:
    - Karşılaştırma yalnızca restoranın kendi geçmişi üzerinden yapılır;
      başka restoranlarla kıyaslama içermez.
    - Turnover/churn için sektörün doğası gereği yüksek olabilen değerleri
      keskin alarm diliyle nitelendirmez ('Kritik' yerine yapıcı etiketler).
    """
    growth_pct = metrics["growth_pct"]
    growth_color = SUCCESS if growth_pct >= 0 else DANGER
    growth_str = ("+" if growth_pct >= 0 else "") + _pct(growth_pct)

    # Yapıcı tonlu churn etiketleri
    tov = metrics["turnover_pct"]
    if tov >= 30:
        tov_label = "Stabilizasyon fırsatı"
    elif tov >= 15:
        tov_label = "İzleme önerilir"
    else:
        tov_label = "Stabil"

    rows = [
        ["Metrik", "Bu Dönem", "Önceki Dönem", "Değerlendirme"],
        [
            "Paket sayısı",
            _int(metrics["packages"]),
            _int(metrics["previous_packages"]),
            growth_str,
        ],
        [
            "Aktif kurye",
            str(metrics["active_count"]),
            "—",
            f"+{metrics['started_count']} giriş / "
            f"-{metrics['exited_count']} çıkış",
        ],
        [
            "Devir oranı",
            _pct(tov),
            "—",
            tov_label,
        ],
        [
            "Paket başı maliyet",
            _money(metrics["cost_per_package"]) + " ₺",
            "—",
            "—",
        ],
    ]

    t = Table(rows, colWidths=[55 * mm, 40 * mm, 40 * mm, 39 * mm])
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), FONT_BOLD, 8.5),
        ("FONT", (0, 1), (-1, -1), FONT_REGULAR, 9),
        ("FONT", (0, 1), (0, -1), FONT_BOLD, 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        # Tek satırlı zebra (premium görünüm)
        ("BACKGROUND", (0, 2), (-1, 2), CREAM_50),
        ("BACKGROUND", (0, 4), (-1, 4), CREAM_50),
    ])
    # Paket değişimi rengi
    style.add("TEXTCOLOR", (3, 1), (3, 1), growth_color)
    style.add("FONT", (3, 1), (3, 1), FONT_BOLD, 9)
    # Devir oranı rengi — yapıcı tonda, kırmızı yerine amber
    tov_color = AMBER if tov >= 30 else AMBER if tov >= 15 else SUCCESS
    style.add("TEXTCOLOR", (3, 3), (3, 3), tov_color)
    style.add("FONT", (3, 3), (3, 3), FONT_BOLD, 9)

    t.setStyle(style)
    return t


def _make_courier_table(couriers: list[dict], styles: dict) -> Table:
    """En verimli ilk 8 kurye."""
    rows = [["Kurye", "Paket", "Saat", "Paket/Saat", "Brüt"]]
    if not couriers:
        rows.append(["Bu dönemde kayıt yok.", "", "", "", ""])
    else:
        for c in couriers[:8]:
            rows.append([
                c.get("full_name") or "—",
                _int(c.get("packages")),
                f"{c.get('hours', 0):.1f}".replace(".", ","),
                f"{c.get('packages_per_hour', 0):.2f}".replace(".", ","),
                _money(c.get("billing")) + " ₺",
            ])
    t = Table(rows, colWidths=[60 * mm, 26 * mm, 26 * mm, 30 * mm, 32 * mm])
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CREAM_100),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEXT),
        ("FONT", (0, 0), (-1, 0), FONT_BOLD, 8),
        ("FONT", (0, 1), (-1, -1), FONT_REGULAR, 9),
        ("FONT", (0, 1), (0, -1), FONT_BOLD, 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        # Top kurye altın badge
        ("BACKGROUND", (3, 1), (3, 1), AMBER_SOFT),
        ("TEXTCOLOR", (3, 1), (3, 1), AMBER),
        ("FONT", (3, 1), (3, 1), FONT_BOLD, 9.5),
    ]) if couriers else TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CREAM_100),
        ("FONT", (0, 0), (-1, 0), FONT_BOLD, 8),
        ("FONT", (0, 1), (-1, -1), FONT_REGULAR, 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("TEXTCOLOR", (0, 1), (0, 1), TEXT_3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
    ])
    t.setStyle(style)
    return t


def _make_ai_commentary(
    commentary: dict | None, styles: dict
) -> list:
    """AI yorumu bölümü.

    commentary: ai_insights.generate_restaurant_commentary çıktısı.
      {
        "headline": str,
        "paragraphs": [str, str, ...],  // 2-4 paragraf
        "verdict": str,                  // tek satır karar
      }
    """
    flow: list = []
    flow.append(Paragraph("DÖNEM ANALİZİ", styles["section_eyebrow"]))
    flow.append(Paragraph(
        "Bu bölümdeki yorum, restoranın bu dönemine ait gerçekleşen "
        "puantaj, tarife ve bordro verisi üzerinden Claude AI tarafından "
        "hazırlanmıştır. Yorum tamamen bu restoranın kendi metriklerine "
        "odaklıdır; başka restoranlarla kıyaslama içermez.",
        styles["small"]
    ))
    flow.append(Spacer(1, 8))

    if not commentary:
        # AI yoksa kurumsal tonlu kısa uyarı
        warn = Table(
            [[Paragraph(
                "Dönem analizi bu rapor için hazırlanamadı. Yukarıdaki "
                "metrikler ve karşılaştırma tablosu gerçekleşen veriler "
                "üzerinden hesaplanmıştır.",
                styles["small"]
            )]],
            colWidths=[174 * mm],
        )
        warn.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CREAM_50),
            ("BOX", (0, 0), (-1, -1), 0.4, CREAM_300),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        flow.append(warn)
        return flow

    headline = commentary.get("headline") or ""
    paragraphs = commentary.get("paragraphs") or []
    verdict = commentary.get("verdict") or ""

    if headline:
        flow.append(Paragraph(headline, styles["ai_quote"]))
        flow.append(Spacer(1, 4))

    for para in paragraphs:
        flow.append(Paragraph(para, styles["ai_para"]))

    if verdict:
        flow.append(Spacer(1, 4))
        verdict_box = Table(
            [[Paragraph(
                f"<b>Karar:</b> {verdict}",
                ParagraphStyle(
                    "vd", fontName=FONT_REGULAR, fontSize=9.5,
                    textColor=BRAND_DARK, leading=14,
                ),
            )]],
            colWidths=[174 * mm],
        )
        verdict_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEBEFORE", (0, 0), (0, -1), 3, BRAND),
        ]))
        flow.append(verdict_box)

    return flow


def _make_footer(restaurant: dict, period: str, styles: dict) -> Table:
    period_label = _format_period(period)
    doc_no = f"RR-{period.replace('-', '')}-{str(restaurant.get('id', 0)).zfill(4)}"
    branch_suffix = (
        f" · {restaurant.get('branch')}" if restaurant.get('branch') else ""
    )
    foot = (
        f"Bu rapor <b>{period_label}</b> dönemi için "
        f"<b>{restaurant.get('brand')}{branch_suffix}</b> restoranının "
        f"performans göstergelerini özetler. Tüm sayılar bu döneme ait "
        f"puantaj kayıtları, restoran tarifeleri ve bordro verisi üzerinden "
        f"hesaplanmıştır. Dönem analizi bölümü, aynı veri seti üzerinde "
        f"Claude AI tarafından hazırlanmıştır."
    )
    p1 = Paragraph(foot, styles["footer"])
    p2 = Paragraph(
        f"<b>Çat Kapında CRM</b>      Belge: {doc_no}      "
        f"info@catkapinda.com",
        styles["footer"],
    )
    t = Table([[p1], [Spacer(1, 3)], [p2]], colWidths=[174 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CREAM_50),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, CREAM_300),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


# ─── Metrik derleme ─────────────────────────────────────────────────

def _compile_metrics(
    restaurant_id: int, period: str, reports: dict,
) -> dict:
    """get_restaurant_reports çıktısından bir restoranın metriklerini
    derler. Ekosistem ortalamasını da hesaplar (sektör benchmark)."""
    turnover_list = reports.get("turnover", []) or []
    cost_data = reports.get("cost_per_package", {}) or {}
    by_rest = cost_data.get("by_restaurant", []) or []
    growth_list = reports.get("package_growth", []) or []
    eff_list = reports.get("courier_efficiency", []) or []
    by_courier = cost_data.get("by_courier", []) or []

    # Bu restoran
    tov = next((r for r in turnover_list if r["restaurant_id"] == restaurant_id), None)
    cost = next((r for r in by_rest if r["restaurant_id"] == restaurant_id), None)
    growth = next((r for r in growth_list if r["restaurant_id"] == restaurant_id), None)
    own_couriers = [
        c for c in eff_list
        if c.get("rest_brand") and tov and c.get("rest_brand") == tov.get("brand")
        and c.get("rest_branch") == tov.get("branch")
    ]
    own_courier_cost = [
        c for c in by_courier
        if c.get("rest_brand") and tov and c.get("rest_brand") == tov.get("brand")
    ]
    # billing'i kurye listesinden topla (own_courier_cost varsa)
    courier_billing_map: dict[str, float] = {
        c.get("full_name", ""): float(c.get("billing", 0))
        for c in own_courier_cost
    }
    for c in own_couriers:
        c["billing"] = courier_billing_map.get(c.get("full_name", ""), 0)

    # Ekosistem ortalamaları (diğer restoranlarla benchmark)
    other_cpps = [r["cost_per_package"] for r in by_rest if r["cost_per_package"] > 0]
    ecosystem_cpp = sum(other_cpps) / len(other_cpps) if other_cpps else 0

    other_pphs = [c["packages_per_hour"] for c in eff_list if c["packages_per_hour"] > 0]
    ecosystem_pph = sum(other_pphs) / len(other_pphs) if other_pphs else 0

    other_tovs = [r["turnover_pct"] for r in turnover_list if r["active_count"] > 0]
    ecosystem_tov = sum(other_tovs) / len(other_tovs) if other_tovs else 0

    other_growths = [r["growth_pct"] for r in growth_list]
    ecosystem_growth = sum(other_growths) / len(other_growths) if other_growths else 0

    avg_pph = (
        sum(c["packages_per_hour"] for c in own_couriers) / len(own_couriers)
        if own_couriers else 0
    )

    return {
        "restaurant_id": restaurant_id,
        "period": period,
        "previous_period": reports.get("previous_period"),
        "packages": (growth or {}).get("current_packages", 0),
        "previous_packages": (growth or {}).get("previous_packages", 0),
        "growth_pct": (growth or {}).get("growth_pct", 0.0),
        "billing": (cost or {}).get("billing_excl_vat", 0),
        "cost_per_package": (cost or {}).get("cost_per_package", 0),
        "active_count": (tov or {}).get("active_count", 0),
        "started_count": (tov or {}).get("started_count", 0),
        "exited_count": (tov or {}).get("exited_count", 0),
        "turnover_pct": (tov or {}).get("turnover_pct", 0.0),
        "avg_pph": avg_pph,
        "couriers": sorted(
            own_couriers, key=lambda c: c["packages_per_hour"], reverse=True,
        ),
        "ecosystem_cpp": ecosystem_cpp,
        "ecosystem_pph": ecosystem_pph,
        "ecosystem_tov": ecosystem_tov,
        "ecosystem_growth": ecosystem_growth,
    }


# ─── Ana fonksiyon ─────────────────────────────────────────────────

def generate_restaurant_report_pdf(
    restaurant: dict,
    period: str,
    reports: dict,
    commentary: dict | None = None,
) -> bytes:
    """Bir restoran için premium performans raporu üret.

    restaurant: get_restaurant(id) çıktısı (brand, branch, contact_email, ...)
    period: 'YYYY-MM'
    reports: get_restaurant_reports(period) çıktısı (tüm restoranlar)
    commentary: ai_insights.generate_restaurant_commentary çıktısı (opsiyonel)
    """
    _register_fonts()
    styles = _styles()
    metrics = _compile_metrics(restaurant["id"], period, reports)

    buf = BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"Performans Raporu {restaurant.get('brand', '')} {period}",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="main",
    )
    doc.addPageTemplates([PageTemplate(id="single", frames=[frame])])

    flow: list = []
    flow.append(_make_hero(restaurant, period, styles))
    flow.append(Spacer(1, 14))

    # 4 KPI kartı
    flow.append(Paragraph("ANA METRİKLER", styles["section_eyebrow"]))
    flow.append(Spacer(1, 4))
    flow.append(_make_kpi_row(metrics, styles))
    flow.append(Spacer(1, 16))

    # Dönem karşılaştırma
    flow.append(Paragraph("DÖNEM KARŞILAŞTIRMASI", styles["section_eyebrow"]))
    flow.append(Spacer(1, 4))
    flow.append(_make_comparison_box(metrics, styles))
    flow.append(Spacer(1, 16))

    # Kurye performansı
    flow.append(Paragraph(
        f"KURYE PERFORMANSI · TOP {min(8, len(metrics['couriers']))}",
        styles["section_eyebrow"],
    ))
    flow.append(Spacer(1, 4))
    flow.append(_make_courier_table(metrics["couriers"], styles))
    flow.append(Spacer(1, 16))

    # AI yorumu
    flow += _make_ai_commentary(commentary, styles)
    flow.append(Spacer(1, 12))

    # Footer
    flow.append(_make_footer(restaurant, period, styles))

    doc.build(flow)
    return buf.getvalue()
