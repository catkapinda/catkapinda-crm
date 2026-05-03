"""Bordro PDF üretimi (ReportLab).

`get_personnel_payroll(...)` çıktısını alıp profesyonel A4 PDF döner.
Türkçe karakter için DejaVu Sans fontu (backend/app/assets/fonts/) kullanılır.
"""
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
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
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ─── Font kayıt ─────────────────────────────────────────────────────────────
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
        # Fallback: ReportLab default Helvetica (Türkçe karakterler bozulur)
        pass


# ─── Renkler ────────────────────────────────────────────────────────────────
BRAND = colors.HexColor("#0F52BA")
BRAND_DARK = colors.HexColor("#0A3F8F")
BRAND_SOFT = colors.HexColor("#E8EFFB")
TEXT = colors.HexColor("#0B0D17")
TEXT_2 = colors.HexColor("#4D5468")
TEXT_3 = colors.HexColor("#8B92A7")
BORDER = colors.HexColor("#ECEEF3")
CREAM_50 = colors.HexColor("#FDFAF3")
DANGER = colors.HexColor("#B91C1C")
ORANGE = colors.HexColor("#9A3412")
PURPLE = colors.HexColor("#6B21A8")
SUCCESS = colors.HexColor("#15803D")

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


# V2'den gelen kayıtlarda Türkçe karakter eksikse / küçük harfse normalize et
TR_NORMALIZE: dict[str, str] = {
    "yakit": "Yakıt",
    "yakıt": "Yakıt",
    "idari ceza": "İdari Ceza",
    "trafik cezasi": "Trafik Cezası",
    "trafik cezası": "Trafik Cezası",
    "fatura edilmeyen tutar": "Fatura Edilmeyen Tutar",
    "fatura edilemeyen tutar": "Fatura Edilemeyen Tutar",
    "bakim": "Bakım",
    "bakım": "Bakım",
    "agir bakim": "Ağır Bakım",
    "ağır bakım": "Ağır Bakım",
    "motor servis bakim": "Motor Servis Bakım",
    "motor servis bakım": "Motor Servis Bakım",
    "motor hasar": "Motor Hasarı",
    "motor hasarı": "Motor Hasarı",
    "korumali mont": "Korumalı Mont",
    "korumalı mont": "Korumalı Mont",
    "yagmurluk": "Yağmurluk",
    "yağmurluk": "Yağmurluk",
    "tshirt": "T-shirt",
    "t-shirt": "T-shirt",
    "gogus cantasi": "Göğüs Çantası",
    "göğüs çantası": "Göğüs Çantası",
    "telefon tutacagi": "Telefon Tutacağı",
    "telefon tutacağı": "Telefon Tutacağı",
    "elcik": "Elcik",
    "kask": "Kask",
    "avans": "Avans",
}


def _normalize_tr(text: str | None) -> str:
    if not text:
        return ""
    key = text.strip().lower()
    return TR_NORMALIZE.get(key, text.strip())


def _format_period(period: str) -> str:
    try:
        y, m = period.split("-")
        return f"{TR_MONTHS[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return period


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    formatted = f"{value:,.2f}"
    # 1,234,567.89 → 1.234.567,89
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    return {
        "header_eyebrow": ParagraphStyle(
            name="he", fontName=FONT_BOLD, fontSize=8,
            textColor=colors.white, leading=10, spaceAfter=2,
        ),
        "header_title": ParagraphStyle(
            name="ht", fontName=FONT_BOLD, fontSize=18,
            textColor=colors.white, leading=22,
        ),
        "section_title": ParagraphStyle(
            name="st", fontName=FONT_BOLD, fontSize=8,
            textColor=TEXT_3, leading=11, spaceAfter=4,
        ),
        "label": ParagraphStyle(
            name="lbl", fontName=FONT_REGULAR, fontSize=8,
            textColor=TEXT_3, leading=10,
        ),
        "value": ParagraphStyle(
            name="val", fontName=FONT_BOLD, fontSize=10,
            textColor=TEXT, leading=14,
        ),
        "small": ParagraphStyle(
            name="sm", fontName=FONT_REGULAR, fontSize=8,
            textColor=TEXT_3, leading=10,
        ),
        "italic": ParagraphStyle(
            name="it", fontName=FONT_REGULAR, fontSize=7.5,
            textColor=TEXT_3, leading=9,
        ),
        "net_label": ParagraphStyle(
            name="nl", fontName=FONT_BOLD, fontSize=9,
            textColor=colors.white, leading=11,
        ),
        "net_value": ParagraphStyle(
            name="nv", fontName=FONT_BOLD, fontSize=22,
            textColor=colors.white, leading=24, alignment=TA_RIGHT,
        ),
        "net_meta": ParagraphStyle(
            name="nm", fontName=FONT_REGULAR, fontSize=8,
            textColor=colors.HexColor("#CCDDF5"), leading=10,
        ),
    }


def _make_header(payroll: dict, period: str, styles: dict) -> Table:
    period_label = _format_period(period)
    belge = (
        f"BR-{period.replace('-', '')}-"
        f"{str(payroll['id']).zfill(4)}"
    )
    left = [
        Paragraph("Çat Kapında · Kurye Bordrosu", styles["header_eyebrow"]),
        Paragraph(period_label, styles["header_title"]),
    ]
    right = [
        Paragraph("Belge No", styles["header_eyebrow"]),
        Paragraph(
            belge,
            ParagraphStyle(
                "br", fontName=FONT_REGULAR, fontSize=10,
                textColor=colors.white, alignment=TA_RIGHT, leading=12,
            ),
        ),
    ]
    t = Table(
        [[left, right]], colWidths=[110 * mm, 60 * mm], rowHeights=[24 * mm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return t


def _make_info(payroll: dict, personnel: dict | None, styles: dict) -> Table:
    rest = payroll.get("rest_brand") or "—"
    branch = payroll.get("rest_branch")
    rest_label = f"{rest} · {branch}" if branch else rest

    left_data = [
        ("Adı Soyadı", payroll.get("full_name") or "—"),
        ("Personel Kodu", payroll.get("person_code") or "—"),
        ("Görev", payroll.get("role") or "—"),
    ]
    right_data = [
        ("Restoran", rest_label),
    ]
    if personnel and personnel.get("tc_no"):
        right_data.append(("TC Kimlik No", personnel["tc_no"]))
    if personnel and personnel.get("iban"):
        right_data.append(("IBAN", personnel["iban"]))
    if personnel and personnel.get("tax_office") and personnel.get("tax_number"):
        right_data.append((
            "Vergi Dairesi / No",
            f"{personnel['tax_office']} · {personnel['tax_number']}",
        ))

    def _build_lines(data):
        lines = []
        for label, value in data:
            lines.append(Paragraph(label.upper(), styles["label"]))
            lines.append(Paragraph(str(value), styles["value"]))
            lines.append(Spacer(1, 4))
        return lines

    t = Table(
        [[_build_lines(left_data), _build_lines(right_data)]],
        colWidths=[85 * mm, 85 * mm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER),
    ]))
    return t


def _make_stats(payroll: dict, styles: dict) -> Table:
    cells = [
        ("Çalışılan Gün", str(payroll.get("ana_days", 0))),
        ("Saat", str(int(payroll.get("ana_hours") or 0))),
        ("Paket", str(int(payroll.get("ana_packages") or 0))),
        (
            "Destek Günü",
            f"+{payroll['destek_days']}" if payroll.get("destek_days") else "—",
        ),
    ]
    rows = [[
        [
            Paragraph(label.upper(), styles["label"]),
            Spacer(1, 2),
            Paragraph(value, ParagraphStyle(
                "stv", fontName=FONT_BOLD, fontSize=16,
                textColor=TEXT, leading=18, alignment=TA_CENTER,
            )),
        ]
        for label, value in cells
    ]]
    col_w = (170 * mm) / 4
    t = Table(rows, colWidths=[col_w] * 4)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _make_brut_section(payroll: dict, styles: dict) -> list:
    flowables: list = []
    flowables.append(
        Paragraph("BRÜT HAKEDİŞ", styles["section_title"])
    )
    flowables.append(Spacer(1, 4))

    rows = []

    # Ana atama satırı sadece destek/ekstra/kaptan varsa görünür
    has_extras = (
        payroll.get("destek_brut", 0) > 0
        or payroll.get("kaptan_bonus", 0) > 0
        or payroll.get("ekstra_mesai_brut", 0) > 0
    )
    if has_extras:
        ana_label = (
            "Sabit aylık tutar"
            if payroll.get("is_fixed_salary")
            else "Ana atama"
        )
        rows.append([ana_label, _money(payroll.get("ana_brut", 0)) + " ₺", None])

    if payroll.get("ekstra_mesai_brut", 0) > 0:
        days = payroll.get("ekstra_mesai_days", 0)
        rows.append([
            f"Bayram / ekstra mesai ({days:g} gün)",
            "+" + _money(payroll["ekstra_mesai_brut"]) + " ₺",
            "extra",
        ])

    if payroll.get("destek_brut", 0) > 0:
        rows.append([
            f"Destek vardiyaları ({payroll['destek_days']} gün)",
            "+" + _money(payroll["destek_brut"]) + " ₺",
            "destek",
        ])

    if payroll.get("kaptan_bonus", 0) > 0:
        rows.append([
            "Kaptan bonusu",
            "+" + _money(payroll["kaptan_bonus"]) + " ₺",
            "kaptan",
        ])

    rows.append([
        "Toplam Brüt",
        _money(payroll.get("toplam_brut", 0)) + " ₺",
        "total",
    ])

    fatura = payroll.get("tevkifat_breakdown", {}).get("fatura_total", 0) or 0
    if fatura > 0:
        rows.append([
            "Fatura Tutarı (KDV %20 dahil)",
            _money(fatura) + " ₺",
            "fatura",
        ])

    table_data = [[r[0], r[1]] for r in rows]
    t = Table(table_data, colWidths=[120 * mm, 50 * mm])
    style = TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT_REGULAR, 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    for i, r in enumerate(rows):
        kind = r[2]
        if kind == "extra":
            style.add("TEXTCOLOR", (1, i), (1, i), PURPLE)
        elif kind == "destek":
            style.add("TEXTCOLOR", (1, i), (1, i), ORANGE)
        elif kind == "kaptan":
            style.add("TEXTCOLOR", (1, i), (1, i), SUCCESS)
        elif kind == "total":
            style.add("FONT", (0, i), (-1, i), FONT_BOLD, 11)
            style.add("LINEABOVE", (0, i), (-1, i), 0.5, BORDER)
            style.add("TOPPADDING", (0, i), (-1, i), 6)
        elif kind == "fatura":
            style.add("FONT", (0, i), (-1, i), FONT_BOLD, 10)
    t.setStyle(style)
    flowables.append(t)

    # KDV breakdown italik
    tev = payroll.get("tevkifat_breakdown", {})
    if (tev.get("invoice_base_amount") or 0) > 0:
        flowables.append(Spacer(1, 4))
        kdv_text = (
            f"↳ <b>KDV hariç matrah:</b> {_money(tev['invoice_base_amount'])} ₺  ·  "
            f"<b>KDV (%20):</b> {_money(tev['vat_amount'])} ₺"
        )
        flowables.append(Paragraph(
            kdv_text,
            ParagraphStyle(
                "kdv", fontName=FONT_REGULAR, fontSize=8.5,
                textColor=TEXT_2, leading=11,
            ),
        ))
    return flowables


def _make_kesinti_section(payroll: dict, styles: dict) -> list:
    flowables: list = []
    flowables.append(Paragraph("KESİNTİLER & ZİMMET", styles["section_title"]))
    flowables.append(Spacer(1, 4))

    rows: list[list] = []
    if payroll.get("motor_taksit", 0) > 0:
        rows.append(["Motor Satış Taksiti", "−" + _money(payroll["motor_taksit"]) + " ₺"])
    if payroll.get("motor_kira", 0) > 0:
        days = payroll.get("ana_days", 30)
        suffix = f" ({days} gün × aylık/30)" if days < 28 else ""
        rows.append([
            f"Motor Kirası{suffix}", "−" + _money(payroll["motor_kira"]) + " ₺",
        ])
    if payroll.get("muhasebe", 0) > 0:
        rows.append(["ÇK Muhasebe Bedeli", "−" + _money(payroll["muhasebe"]) + " ₺"])
    if payroll.get("sirket_acilis", 0) > 0:
        rows.append(["Şirket Açılış Bedeli (1×)", "−" + _money(payroll["sirket_acilis"]) + " ₺"])

    for g in payroll.get("kesinti_groups", []):
        # Türkçe normalize + "(N kayıt)" suffix kaldırıldı (kullanıcı isteği)
        type_label = _normalize_tr(g.get("type", ""))
        rows.append([
            type_label,
            "−" + _money(g.get("total", 0)) + " ₺",
        ])

    if payroll.get("tevkifat", 0) > 0:
        rows.append([
            "KDV Tevkifatı (2/10) — Zorunlu devlet kesintisidir",
            "−" + _money(payroll["tevkifat"]) + " ₺",
        ])

    if not rows:
        return []  # hiç kesinti yoksa bölümü gösterme

    total_kesinti = (
        payroll.get("sabit_total", 0)
        + payroll.get("kesinti_total", 0)
        + payroll.get("tevkifat", 0)
    )
    rows.append(["Toplam Kesinti", "−" + _money(total_kesinti) + " ₺"])

    t = Table(rows, colWidths=[120 * mm, 50 * mm])
    style = TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT_REGULAR, 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (1, 0), (1, -1), DANGER),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    last = len(rows) - 1
    style.add("FONT", (0, last), (-1, last), FONT_BOLD, 11)
    style.add("LINEABOVE", (0, last), (-1, last), 0.5, BORDER)
    style.add("TOPPADDING", (0, last), (-1, last), 6)
    t.setStyle(style)
    flowables.append(t)
    return flowables


def _make_net(payroll: dict, styles: dict) -> Table:
    total_kesinti = (
        payroll.get("sabit_total", 0)
        + payroll.get("kesinti_total", 0)
        + payroll.get("tevkifat", 0)
    )
    left = [
        Paragraph("NET AYLIK HAKEDİŞ", styles["net_label"]),
        Spacer(1, 4),
        Paragraph(
            f"Brüt {_money(payroll['toplam_brut'])} ₺ − Kesinti {_money(total_kesinti)} ₺",
            styles["net_meta"],
        ),
    ]
    right = [
        Paragraph(_money(payroll["net"]) + " ₺", styles["net_value"]),
    ]
    t = Table(
        [[left, right]], colWidths=[100 * mm, 70 * mm], rowHeights=[28 * mm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return t


def _make_signatures(payroll: dict, styles: dict) -> Table:
    from datetime import date
    today_str = date.today().strftime("%d.%m.%Y")

    def block(title: str, name: str, date_str: str):
        return [
            Paragraph(title.upper(), styles["section_title"]),
            Spacer(1, 32),  # imza için boşluk
            Paragraph(name, ParagraphStyle(
                "sn", fontName=FONT_REGULAR, fontSize=10,
                textColor=TEXT_2, leading=12,
                borderPadding=(0, 0, 4, 0),
            )),
            Paragraph(
                f"Tarih: {date_str}",
                ParagraphStyle(
                    "sd", fontName=FONT_REGULAR, fontSize=8,
                    textColor=TEXT_3, leading=10,
                ),
            ),
        ]

    left = block(
        "Düzenleyen",
        "Çat Kapında Teknoloji Lojistik ve Dış Ticaret A.Ş.",
        today_str,
    )
    right = block(
        "Kurye İmza",
        payroll.get("full_name") or "—",
        "____________________",
    )

    t = Table(
        [[left, right]], colWidths=[85 * mm, 85 * mm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return t


def _make_footer(payroll: dict, period: str) -> Table:
    period_label = _format_period(period)
    belge = (
        f"BR-{period.replace('-', '')}-"
        f"{str(payroll['id']).zfill(4)}"
    )
    foot_text = (
        f"Bu belge <b>{period_label}</b> ayına ait kurye hakediş bordrosudur. "
        f"Tutarlar puantaj kayıtları, restoran tarifeleri, kesintiler ve "
        f"zimmet taksitleri üzerinden hesaplanmıştır."
    )
    bottom = (
        f"<b>Çat Kapında CRM Sistemi</b>      Belge: <font face='{FONT_REGULAR}'>{belge}</font>"
    )
    p1 = Paragraph(foot_text, ParagraphStyle(
        "ft", fontName=FONT_REGULAR, fontSize=7.5,
        textColor=TEXT_3, leading=10,
    ))
    p2 = Paragraph(bottom, ParagraphStyle(
        "ft2", fontName=FONT_REGULAR, fontSize=7.5,
        textColor=TEXT_3, leading=10,
    ))
    t = Table([[p1], [Spacer(1, 4)], [p2]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CREAM_50),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, BORDER),
    ]))
    return t


def generate_payroll_pdf(payroll: dict, personnel: dict | None, period: str) -> bytes:
    """Tek kurye için bordro PDF üret. Bytes döner."""
    _register_fonts()
    styles = _styles()

    buf = BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Bordro {payroll.get('full_name','')} {period}",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="main",
    )
    doc.addPageTemplates([PageTemplate(id="single", frames=[frame])])

    flow = []
    flow.append(_make_header(payroll, period, styles))
    flow.append(Spacer(1, 0))
    flow.append(_make_info(payroll, personnel, styles))
    flow.append(Spacer(1, 8))
    flow.append(_make_stats(payroll, styles))
    flow.append(Spacer(1, 12))
    flow += _make_brut_section(payroll, styles)
    flow.append(Spacer(1, 14))
    kesinti = _make_kesinti_section(payroll, styles)
    if kesinti:
        flow += kesinti
        flow.append(Spacer(1, 14))
    flow.append(_make_net(payroll, styles))
    flow.append(Spacer(1, 12))
    flow.append(_make_signatures(payroll, styles))
    flow.append(Spacer(1, 8))
    flow.append(_make_footer(payroll, period))

    doc.build(flow)
    return buf.getvalue()
