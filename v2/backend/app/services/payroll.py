from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
import re
import sys
from pathlib import Path

import pandas as pd
import psycopg

from app.core.database import is_sqlite_backend
from app.services.motor_rental import (
    MOTOR_PURCHASE_DEDUCTION_TYPE,
    MOTOR_RENTAL_DEDUCTION_TYPE,
    calculate_company_motor_purchase_deduction,
    calculate_company_motor_rental_deduction,
    is_motor_purchase_deduction_type,
    is_motor_rental_deduction_type,
)
from app.schemas.payroll import (
    PayrollCostModelBreakdownEntry,
    PayrollDashboardResponse,
    PayrollEntry,
    PayrollModuleStatus,
    PayrollRoleBreakdownEntry,
    PayrollSummary,
    PayrollTopPersonnelEntry,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_repo_root_on_path() -> None:
    repo_root = str(_repo_root())
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _build_compat_connection(conn: psycopg.Connection):
    _ensure_repo_root_on_path()
    from infrastructure.db_engine import CompatConnection

    info = getattr(conn, "info", None)
    host = getattr(info, "host", "?") if info else "?"
    port = getattr(info, "port", 5432) if info else 5432
    dbname = getattr(info, "dbname", "postgres") if info else "postgres"
    user = getattr(info, "user", "?") if info else "?"
    cache_key = f"postgres:{host}:{port}/{dbname}:{user}"
    return CompatConnection(conn, "postgres", cache_key=cache_key)


def _safe_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return 0.0


def _month_key_sql(column: str) -> str:
    return f"substr(COALESCE(CAST({column} AS TEXT), ''), 1, 7)"


_COST_MODEL_LABELS = {
    "standard_courier": "Standart Kurye",
    "fixed_monthly": "Sabit Aylık",
    "fixed_kurye": "Kurye Sabit",
    "fixed_bolge_muduru": "Bölge Müdürü",
    "fixed_saha_denetmen_sefi": "Saha Denetmen Şefi",
    "fixed_restoran_takim_sefi": "Restoran Takım Şefi",
    "fixed_joker": "Joker Sabit",
    "hourly_only": "Sadece Saatlik",
    "hourly_plus_package": "Saat + Paket",
    "threshold_package": "Eşikli Paket",
}

_COURIER_HOURLY_COST = 250.0
_COURIER_HOURLY_COST_DOGU_OTOMOTIV = 295.0
_COURIER_PACKAGE_COST_DEFAULT_LOW = 20.0
_COURIER_PACKAGE_COST_DEFAULT_HIGH = 25.0
_COURIER_PACKAGE_COST_QC = 25.0
_PACKAGE_THRESHOLD_DEFAULT = 390
_PAYROLL_IGNORED_DEDUCTION_SQL = "('Partner Kart Indirimi', 'Partner Kart İndirimi')"
_MOTOR_RENTAL_DEDUCTION_SQL = "('Motor Kirası', 'Motor Kirasi')"
_MOTOR_PURCHASE_DEDUCTION_SQL = "('Motor Satış Taksiti', 'Motor Satis Taksiti', 'Motor Satın Alım', 'Motor Satin Alim')"


@dataclass
class PayrollDocumentPayload:
    selected_month: str
    personnel_id: int
    personnel: str
    person_code: str
    role: str
    status: str
    total_hours: float
    total_packages: float
    gross_pay: float
    total_deductions: float
    net_payment: float
    restaurant_names: list[str]
    deduction_items: list[tuple[str, float]]


def _normalized_brand_key(brand: object) -> str:
    return str(brand or "").strip().lower()


def _is_quick_china_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) == "quick china"


def _is_dogu_otomotiv_brand(brand: object) -> bool:
    return _normalized_brand_key(brand) in {"doğu otomotiv", "dogu otomotiv"}


def _calculate_standard_package_cost(total_packages: float, *, brand: object = "") -> float:
    package_total = _safe_float(total_packages)
    if _is_dogu_otomotiv_brand(brand):
        return 0.0
    if _is_quick_china_brand(brand):
        return package_total * _COURIER_PACKAGE_COST_QC
    package_rate = (
        _COURIER_PACKAGE_COST_DEFAULT_LOW
        if package_total <= float(_PACKAGE_THRESHOLD_DEFAULT)
        else _COURIER_PACKAGE_COST_DEFAULT_HIGH
    )
    return package_total * package_rate


def _calculate_standard_courier_cost(
    total_hours: float,
    total_packages: float,
    *,
    brand: object = "",
) -> float:
    hourly_cost = _COURIER_HOURLY_COST_DOGU_OTOMOTIV if _is_dogu_otomotiv_brand(brand) else _COURIER_HOURLY_COST
    return _safe_float(total_hours) * hourly_cost + _calculate_standard_package_cost(
        total_packages,
        brand=brand,
    )


def _calculate_variable_courier_gross_cost(segments: list[dict[str, object]]) -> float:
    standard_threshold_packages = 0.0
    gross_cost = 0.0

    for segment in segments:
        brand = segment.get("brand")
        total_hours = _safe_float(segment.get("total_hours"))
        total_packages = _safe_float(segment.get("total_packages"))

        if _is_dogu_otomotiv_brand(brand):
            gross_cost += total_hours * _COURIER_HOURLY_COST_DOGU_OTOMOTIV
            continue

        gross_cost += total_hours * _COURIER_HOURLY_COST
        if _is_quick_china_brand(brand):
            gross_cost += total_packages * _COURIER_PACKAGE_COST_QC
        else:
            standard_threshold_packages += total_packages

    if standard_threshold_packages > 0:
        package_rate = (
            _COURIER_PACKAGE_COST_DEFAULT_HIGH
            if standard_threshold_packages > float(_PACKAGE_THRESHOLD_DEFAULT)
            else _COURIER_PACKAGE_COST_DEFAULT_LOW
        )
        gross_cost += standard_threshold_packages * package_rate

    return _safe_float(gross_cost)


def _is_fixed_cost_model(cost_model: object) -> bool:
    model = str(cost_model or "").strip()
    return model == "fixed_monthly" or model.startswith("fixed_")


def _calculate_personnel_gross_pay(
    *,
    cost_model: object,
    monthly_fixed_cost: float,
    total_hours: float,
    total_packages: float,
    segments: list[dict[str, object]],
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    has_attendance = total_hours > 0 or total_packages > 0
    if _is_fixed_cost_model(cost_model) and fixed_cost > 0:
        return fixed_cost
    if not has_attendance:
        return fixed_cost
    return _calculate_variable_courier_gross_cost(segments)


def build_payroll_status() -> PayrollModuleStatus:
    return PayrollModuleStatus(
        module="payroll",
        status="active",
        next_slice="payroll-dashboard",
    )


def _format_currency_pdf(value: float) -> str:
    amount = _safe_float(value)
    sign = "-" if amount < 0 else ""
    normalized = abs(amount)
    formatted = f"{normalized:,.2f}"
    whole, decimal = formatted.split(".")
    return f"{sign}{whole.replace(',', '.')},{decimal} TL"


def _format_number_pdf(value: float, decimals: int = 0) -> str:
    normalized = _safe_float(value)
    formatted = f"{normalized:,.{decimals}f}"
    if decimals <= 0:
        return formatted.replace(",", ".")
    whole, decimal = formatted.split(".")
    return f"{whole.replace(',', '.')},{decimal}"


def _format_month_label(value: str) -> str:
    month_map = {
        "01": "Ocak",
        "02": "Şubat",
        "03": "Mart",
        "04": "Nisan",
        "05": "Mayıs",
        "06": "Haziran",
        "07": "Temmuz",
        "08": "Ağustos",
        "09": "Eylül",
        "10": "Ekim",
        "11": "Kasım",
        "12": "Aralık",
    }
    parts = str(value or "").split("-")
    if len(parts) != 2:
        return str(value or "-")
    year, month = parts
    return f"{month_map.get(month, month)} {year}"


def _register_pdf_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont("CRMFont", path))
                return "CRMFont"
            except Exception:
                continue
    return "Helvetica"


def _render_payroll_document_pdf(payload: PayrollDocumentPayload) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import simpleSplit
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError:
        return _render_basic_payroll_pdf(payload)

    try:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        font_name = _register_pdf_font()
        margin_x = 42
        top_y = height - 42
        page_width = width - (margin_x * 2)

        palette = {
            "navy": (24 / 255, 40 / 255, 59 / 255),
            "navy_soft": (40 / 255, 60 / 255, 86 / 255),
            "paper": (250 / 255, 246 / 255, 238 / 255),
            "line": (220 / 255, 226 / 255, 235 / 255),
            "text": (24 / 255, 40 / 255, 59 / 255),
            "muted": (104 / 255, 116 / 255, 133 / 255),
            "accent": (181 / 255, 118 / 255, 46 / 255),
            "accent_soft": (243 / 255, 233 / 255, 214 / 255),
            "green": (34 / 255, 102 / 255, 60 / 255),
            "green_soft": (227 / 255, 241 / 255, 231 / 255),
            "red": (158 / 255, 36 / 255, 48 / 255),
            "red_soft": (247 / 255, 231 / 255, 233 / 255),
            "blue_soft": (230 / 255, 239 / 255, 252 / 255),
        }

        def set_fill(color_key: str) -> None:
            pdf.setFillColorRGB(*palette[color_key])

        def set_stroke(color_key: str) -> None:
            pdf.setStrokeColorRGB(*palette[color_key])

        def write_line(
            text: str,
            x: float,
            y: float,
            size: int = 10,
            *,
            color_key: str = "text",
            font_override: str | None = None,
        ) -> None:
            set_fill(color_key)
            pdf.setFont(font_name, size)
            if font_override:
                pdf.setFont(font_override, size)
            pdf.drawString(x, y, str(text))

        def write_wrapped_text(
            text: str,
            x: float,
            y: float,
            width_limit: float,
            *,
            size: int = 10,
            color_key: str = "text",
            leading: float | None = None,
        ) -> float:
            lines = simpleSplit(str(text or ""), font_name, size, width_limit)
            step = leading if leading is not None else size + 4
            current_y = y
            for line in lines:
                write_line(line, x, current_y, size, color_key=color_key)
                current_y -= step
            return current_y

        def draw_rounded_card(
            x: float,
            y: float,
            card_width: float,
            card_height: float,
            *,
            fill_key: str,
            stroke_key: str = "line",
            radius: float = 18,
            stroke_width: float = 1,
        ) -> None:
            set_fill(fill_key)
            set_stroke(stroke_key)
            pdf.setLineWidth(stroke_width)
            pdf.roundRect(x, y, card_width, card_height, radius, stroke=1, fill=1)

        def draw_label_value(
            label: str,
            value: str,
            x: float,
            y: float,
            width_limit: float,
        ) -> float:
            write_line(label, x, y, 8, color_key="muted")
            return write_wrapped_text(value, x, y - 14, width_limit, size=11, color_key="text", leading=15)

        def ensure_space(current_y: float, needed_height: float) -> float:
            if current_y - needed_height >= 40:
                return current_y
            pdf.showPage()
            return height - 50

        month_label = _format_month_label(payload.selected_month)
        restaurant_text = ", ".join(payload.restaurant_names) if payload.restaurant_names else "Bu ay restoran kaydı bulunamadı."
        restaurant_count = len(payload.restaurant_names)

        header_height = 112
        header_bottom = top_y - header_height
        draw_rounded_card(margin_x, header_bottom, page_width, header_height, fill_key="navy", stroke_key="navy")

        write_line("Çat Kapında", margin_x + 20, top_y - 26, 12, color_key="paper")
        write_line("Kurye Hakediş Belgesi", margin_x + 20, top_y - 56, 24, color_key="paper")
        write_line("Aylık ödeme özeti ve kesinti dökümü", margin_x + 20, top_y - 76, 10, color_key="paper")

        chip_width = 132
        chip_height = 34
        chip_x = margin_x + page_width - chip_width - 18
        chip_y = top_y - 48
        draw_rounded_card(chip_x, chip_y, chip_width, chip_height, fill_key="accent_soft", stroke_key="accent_soft", radius=16)
        write_line("DÖNEM", chip_x + 12, chip_y + 21, 8, color_key="accent")
        write_line(month_label, chip_x + 12, chip_y + 8, 11, color_key="navy")
        write_line(f"Oluşturma: {date.today().strftime('%d.%m.%Y')}", chip_x, chip_y - 16, 9, color_key="paper")

        info_top = header_bottom - 14
        info_height = 112
        info_bottom = info_top - info_height
        draw_rounded_card(margin_x, info_bottom, page_width, info_height, fill_key="paper")

        left_col_x = margin_x + 18
        right_col_x = margin_x + (page_width / 2) + 8
        label_top = info_top - 18
        left_value_y = draw_label_value("Personel", payload.personnel, left_col_x, label_top, page_width / 2 - 40)
        draw_label_value("Kod", payload.person_code or "-", left_col_x, left_value_y - 4, page_width / 2 - 40)
        draw_label_value("Rol", payload.role or "-", left_col_x, left_value_y - 34, page_width / 2 - 40)

        right_value_y = draw_label_value("Durum", payload.status or "-", right_col_x, label_top, page_width / 2 - 40)
        draw_label_value("Çalışılan Şube", str(restaurant_count), right_col_x, right_value_y - 4, page_width / 2 - 40)
        draw_label_value("Dönem", month_label, right_col_x, right_value_y - 34, page_width / 2 - 40)

        summary_top = info_bottom - 14
        summary_card_height = 88
        gap = 10
        summary_card_width = (page_width - (gap * 2)) / 3
        summary_items = [
            ("Kesinti Öncesi", _format_currency_pdf(payload.gross_pay), "Kurye hakedişi", "blue_soft", "navy"),
            ("Toplam Kesinti", _format_currency_pdf(payload.total_deductions), "Ay içi düşümler", "red_soft", "red"),
            ("Net Kurye Ödemesi", _format_currency_pdf(payload.net_payment), "Nihai ödeme tutarı", "green_soft", "green"),
        ]
        for index, (label, value, note, fill_key, title_color) in enumerate(summary_items):
            card_x = margin_x + index * (summary_card_width + gap)
            card_bottom = summary_top - summary_card_height
            draw_rounded_card(card_x, card_bottom, summary_card_width, summary_card_height, fill_key=fill_key, stroke_key=fill_key, radius=18)
            write_line(label, card_x + 14, summary_top - 20, 8, color_key="muted")
            write_line(value, card_x + 14, summary_top - 48, 16, color_key="text")
            write_line(note, card_x + 14, summary_top - 67, 9, color_key="muted")
            pdf.setStrokeColorRGB(*palette[title_color])
            pdf.setLineWidth(3)
            pdf.line(card_x + 14, summary_top - 8, card_x + 54, summary_top - 8)

        panel_top = summary_top - summary_card_height - 16
        left_panel_width = (page_width * 0.42)
        right_panel_width = page_width - left_panel_width - 12
        panel_height = 154
        left_panel_bottom = panel_top - panel_height
        right_panel_x = margin_x + left_panel_width + 12
        draw_rounded_card(margin_x, left_panel_bottom, left_panel_width, panel_height, fill_key="paper")
        draw_rounded_card(right_panel_x, left_panel_bottom, right_panel_width, panel_height, fill_key="paper")

        write_line("Çalışma Özeti", margin_x + 16, panel_top - 20, 11, color_key="text")
        metric_y = panel_top - 52
        work_items = [
            ("Toplam Saat", f"{_format_number_pdf(payload.total_hours, 1)} saat"),
            ("Toplam Paket", f"{_format_number_pdf(payload.total_packages, 0)} paket"),
            ("Şube Sayısı", f"{restaurant_count} şube"),
        ]
        for label, value in work_items:
            write_line(label, margin_x + 16, metric_y, 8, color_key="muted")
            write_line(value, margin_x + 16, metric_y - 18, 14, color_key="text")
            metric_y -= 40

        write_line("Çalışılan Restoranlar", right_panel_x + 16, panel_top - 20, 11, color_key="text")
        restaurant_bottom_y = write_wrapped_text(
            restaurant_text,
            right_panel_x + 16,
            panel_top - 46,
            right_panel_width - 32,
            size=10,
            color_key="text",
            leading=15,
        )
        write_line(
            "Dağılım, seçili ay içinde puantaj görülen şubeleri gösterir.",
            right_panel_x + 16,
            max(restaurant_bottom_y - 8, left_panel_bottom + 18),
            8,
            color_key="muted",
        )

        deductions_top = left_panel_bottom - 16
        deductions_header_height = 22
        row_height = 22
        deduction_count = max(len(payload.deduction_items), 1)
        deductions_height = 44 + deductions_header_height + (deduction_count * row_height)
        current_top = ensure_space(deductions_top, deductions_height + 10)
        deductions_top = current_top
        deductions_bottom = deductions_top - deductions_height
        draw_rounded_card(margin_x, deductions_bottom, page_width, deductions_height, fill_key="paper")
        write_line("Kesinti Detayı", margin_x + 16, deductions_top - 20, 11, color_key="text")
        write_line(
            "Bu ay hakedişten düşen kalemler aşağıda listelenir.",
            margin_x + 16,
            deductions_top - 36,
            8,
            color_key="muted",
        )

        table_top = deductions_top - 56
        set_fill("navy_soft")
        pdf.roundRect(margin_x + 12, table_top - deductions_header_height, page_width - 24, deductions_header_height, 10, stroke=0, fill=1)
        write_line("Kalem", margin_x + 22, table_top - 15, 9, color_key="paper")
        write_line("Tutar", margin_x + page_width - 86, table_top - 15, 9, color_key="paper")

        content_y = table_top - deductions_header_height - 8
        if payload.deduction_items:
            for index, (deduction_type, amount) in enumerate(payload.deduction_items):
                row_bottom = content_y - row_height + 4
                if index % 2 == 0:
                    set_fill("blue_soft")
                    pdf.roundRect(margin_x + 12, row_bottom, page_width - 24, row_height - 2, 8, stroke=0, fill=1)
                write_line(str(deduction_type or "Kesinti"), margin_x + 22, content_y - 10, 10, color_key="text")
                set_fill("red")
                pdf.setFont(font_name, 10)
                pdf.drawRightString(margin_x + page_width - 24, content_y - 10, f"-{_format_currency_pdf(amount)}")
                content_y -= row_height
        else:
            write_line("Bu ay için kesinti kaydı bulunamadı.", margin_x + 22, content_y - 10, 10, color_key="muted")
            content_y -= row_height

        footer_y = max(deductions_bottom - 22, 24)
        set_stroke("line")
        pdf.setLineWidth(1)
        pdf.line(margin_x, footer_y + 8, width - margin_x, footer_y + 8)
        write_line(
            "Bu belge Çat Kapında CRM tarafından oluşturuldu. Tüm tutarlar kurye ödeme görünümünü özetler.",
            margin_x,
            footer_y - 4,
            8,
            color_key="muted",
        )

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        return _render_basic_payroll_pdf(payload)


def _render_basic_payroll_pdf(payload: PayrollDocumentPayload) -> bytes:
    transliteration = str.maketrans(
        {
            "Ç": "C",
            "ç": "c",
            "Ğ": "G",
            "ğ": "g",
            "İ": "I",
            "ı": "i",
            "Ö": "O",
            "ö": "o",
            "Ş": "S",
            "ş": "s",
            "Ü": "U",
            "ü": "u",
        }
    )

    def escape_pdf_text(value: str) -> str:
        normalized = str(value).translate(transliteration)
        return normalized.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = [
        ("16", "Cat Kapinda"),
        ("14", "Kurye Hakedis Raporu"),
        ("10", f"Personel: {payload.personnel}"),
        ("10", f"Kod: {payload.person_code or '-'}"),
        ("10", f"Rol: {payload.role or '-'}"),
        ("10", f"Ay: {payload.selected_month}"),
        ("10", f"Durum: {payload.status or '-'}"),
        ("10", "Restoranlar: " + (", ".join(payload.restaurant_names) if payload.restaurant_names else "-")),
        ("12", "Çalışma Özeti"),
        ("10", f"Toplam Saat: {int(_safe_float(payload.total_hours))}"),
        ("10", f"Toplam Paket: {int(_safe_float(payload.total_packages))}"),
        ("12", "Hakediş Özeti"),
        ("10", f"Brut Hakedis: {_format_currency_pdf(payload.gross_pay)}"),
        ("10", f"Toplam Kesinti: {_format_currency_pdf(payload.total_deductions)}"),
        ("11", f"Net Odeme: {_format_currency_pdf(payload.net_payment)}"),
        ("12", "Kesinti Detayi"),
    ]
    if payload.deduction_items:
        lines.extend(
            [("10", f"{deduction_type}: -{_format_currency_pdf(amount)}") for deduction_type, amount in payload.deduction_items]
        )
    else:
        lines.append(("10", "Bu ay icin kesinti kaydi bulunamadi."))

    content_lines = ["BT"]
    y_position = 800
    for index, (font_size, text) in enumerate(lines):
        if index == 0:
            content_lines.append(f"/F1 {font_size} Tf")
            content_lines.append(f"40 {y_position} Td")
        else:
            step = 22 if index == 1 else 16
            y_position -= step
            content_lines.append(f"1 0 0 1 40 {y_position} Tm")
            content_lines.append(f"/F1 {font_size} Tf")
        content_lines.append(f"({escape_pdf_text(text)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines) + "\n"
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1") + stream_bytes + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(pdf)


def _resolve_month_key(month_options: list[str], selected_month: str | None) -> str:
    if not month_options:
        raise ValueError("Belge oluşturmak için önce hakediş verisi oluşmalı.")
    return selected_month if selected_month in month_options else month_options[0]


def _fetch_payroll_month_options(conn: psycopg.Connection) -> tuple[list[str], list[str]]:
    attendance_rows = conn.execute(
        f"""
        SELECT DISTINCT {_month_key_sql('entry_date')} AS month_key
        FROM daily_entries
        WHERE COALESCE(CAST(entry_date AS TEXT), '') <> ''
        ORDER BY month_key DESC
        """
    ).fetchall()
    deduction_rows = conn.execute(
        f"""
        SELECT DISTINCT {_month_key_sql('deduction_date')} AS month_key
        FROM deductions
        WHERE COALESCE(CAST(deduction_date AS TEXT), '') <> ''
        ORDER BY month_key DESC
        """
    ).fetchall()
    attendance_month_options = [str(row["month_key"]) for row in attendance_rows if row["month_key"]]
    deduction_month_options = [str(row["month_key"]) for row in deduction_rows if row["month_key"]]
    month_options = sorted(set(attendance_month_options) | set(deduction_month_options), reverse=True)
    return month_options, attendance_month_options


def _resolve_payroll_dashboard_month(
    month_options: list[str],
    attendance_month_options: list[str],
    selected_month: str | None,
) -> str:
    if selected_month in month_options:
        return str(selected_month)
    if attendance_month_options:
        return attendance_month_options[0]
    return _resolve_month_key(month_options, selected_month)


def build_payroll_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None = None,
    role_filter: str | None = None,
    restaurant_filter: str | None = None,
    limit: int = 300,
) -> PayrollDashboardResponse:
    return _build_local_payroll_dashboard(
        conn,
        selected_month=selected_month,
        role_filter=role_filter,
        restaurant_filter=restaurant_filter,
        limit=limit,
    )


def build_payroll_document_file(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    personnel_id: int,
) -> tuple[str, bytes]:
    payload = _build_local_payroll_document_payload(
        conn,
        selected_month=selected_month,
        personnel_id=personnel_id,
    )
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", payload.personnel).strip("_") or f"personel_{payload.personnel_id}"
    file_name = f"hakedis_{safe_name}_{payload.selected_month}.pdf"
    return file_name, _render_payroll_document_pdf(payload)


def _build_remote_payroll_document_payload(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    personnel_id: int,
) -> PayrollDocumentPayload:
    _ensure_repo_root_on_path()
    from engines.finance_engine import calculate_personnel_cost
    from rules.deduction_rules import filter_payroll_effective_deductions_df
    from rules.reporting_rules import month_bounds
    from services.reporting_service import load_monthly_payroll_source_payload

    compat_conn = _build_compat_connection(conn)
    payload = load_monthly_payroll_source_payload(compat_conn)
    month_options = payload.month_options
    resolved_month = _resolve_month_key(month_options, selected_month)

    entries = payload.entries.copy() if not payload.entries.empty else pd.DataFrame()
    deductions = payload.deductions.copy() if not payload.deductions.empty else pd.DataFrame()
    personnel_df = payload.personnel_df.copy() if not payload.personnel_df.empty else pd.DataFrame()
    role_history_df = (
        payload.role_history_df.copy()
        if payload.role_history_df is not None and not payload.role_history_df.empty
        else pd.DataFrame()
    )

    start_date, end_date = month_bounds(resolved_month)
    month_entries = (
        entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy()
        if not entries.empty
        else pd.DataFrame()
    )
    month_deductions = (
        deductions[(deductions["deduction_date"] >= start_date) & (deductions["deduction_date"] <= end_date)].copy()
        if not deductions.empty
        else pd.DataFrame()
    )
    payroll_deductions = filter_payroll_effective_deductions_df(month_deductions, personnel_df)
    cost_df = calculate_personnel_cost(
        month_entries,
        personnel_df,
        payroll_deductions,
        role_history_df=role_history_df if not role_history_df.empty else None,
    )
    if cost_df.empty or "personnel_id" not in cost_df.columns:
        raise LookupError("Belgesi oluşturulacak personel için hakediş kaydı bulunamadı.")

    match_rows = cost_df[cost_df["personnel_id"] == personnel_id]
    if match_rows.empty:
        raise LookupError("Belgesi oluşturulacak personel için hakediş kaydı bulunamadı.")
    payroll_row = match_rows.iloc[0]

    person_match = personnel_df[personnel_df["id"] == personnel_id] if not personnel_df.empty else pd.DataFrame()
    person_code = str(person_match.iloc[0]["person_code"] or "") if not person_match.empty and "person_code" in person_match.columns else ""

    deduction_items: list[tuple[str, float]] = []
    if not payroll_deductions.empty:
        person_deductions = payroll_deductions[payroll_deductions["personnel_id"] == personnel_id].copy()
        if not person_deductions.empty:
            grouped = (
                person_deductions.groupby("deduction_type", dropna=False)["amount"]
                .sum()
                .reset_index()
            )
            deduction_items = [
                (str(row["deduction_type"] or "Kesinti"), _safe_float(row["amount"]))
                for _, row in grouped.iterrows()
            ]

    restaurant_names: list[str] = []
    if not month_entries.empty:
        rest_series = (
            month_entries.loc[month_entries["actual_personnel_id"] == personnel_id, "brand"].fillna("").astype(str)
            + " - "
            + month_entries.loc[month_entries["actual_personnel_id"] == personnel_id, "branch"].fillna("").astype(str)
        )
        restaurant_names = [value.strip(" -") for value in sorted(rest_series.unique().tolist()) if value.strip(" -")]

    gross_pay = _safe_float(payroll_row.get("brut_maliyet"))
    total_deductions = _safe_float(payroll_row.get("kesinti"))

    return PayrollDocumentPayload(
        selected_month=resolved_month,
        personnel_id=personnel_id,
        personnel=str(payroll_row.get("personel") or "-"),
        person_code=person_code,
        role=str(payroll_row.get("rol") or "-"),
        status=str(payroll_row.get("durum") or "-"),
        total_hours=_safe_float(payroll_row.get("calisma_saati")),
        total_packages=_safe_float(payroll_row.get("paket")),
        gross_pay=gross_pay,
        total_deductions=total_deductions,
        net_payment=_safe_float(payroll_row.get("net_maliyet")),
        restaurant_names=restaurant_names,
        deduction_items=deduction_items,
    )


def _build_local_payroll_document_payload(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    personnel_id: int,
) -> PayrollDocumentPayload:
    month_options, attendance_month_options = _fetch_payroll_month_options(conn)
    resolved_month = _resolve_payroll_dashboard_month(month_options, attendance_month_options, selected_month)

    person_row = conn.execute(
        """
        SELECT
            id,
            COALESCE(full_name, '-') AS full_name,
            COALESCE(person_code, '') AS person_code,
            COALESCE(role, '-') AS role,
            COALESCE(status, '-') AS status,
            COALESCE(cost_model, '-') AS cost_model,
            COALESCE(monthly_fixed_cost, 0) AS monthly_fixed_cost,
            start_date,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, 'Hayır') AS motor_rental,
            COALESCE(motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            motor_purchase_start_date,
            COALESCE(motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction
        FROM personnel
        WHERE id = %s
        """,
        (personnel_id,),
    ).fetchone()
    if person_row is None:
        raise LookupError("Belgesi oluşturulacak personel bulunamadı.")
    person_data = dict(person_row)

    attendance_rows = conn.execute(
        f"""
        SELECT
            d.restaurant_id,
            COALESCE(r.brand, '') AS brand,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
        GROUP BY
            d.restaurant_id,
            COALESCE(r.brand, '')
        """,
        (resolved_month, personnel_id),
    ).fetchall()

    deduction_rows = conn.execute(
        f"""
        SELECT
            COALESCE(deduction_type, 'Kesinti') AS deduction_type,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id = %s
          AND COALESCE(deduction_type, '') NOT IN {_PAYROLL_IGNORED_DEDUCTION_SQL}
        GROUP BY COALESCE(deduction_type, 'Kesinti')
        ORDER BY deduction_type
        """,
        (resolved_month, personnel_id),
    ).fetchall()

    restaurant_rows = conn.execute(
        f"""
        SELECT DISTINCT COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
        ORDER BY restaurant_label
        """,
        (resolved_month, personnel_id),
    ).fetchall()

    attendance_segments = [
        {
            "brand": str(row["brand"] or ""),
            "total_hours": _safe_float(row["total_hours"]),
            "total_packages": _safe_float(row["total_packages"]),
        }
        for row in attendance_rows
    ]
    total_hours = _safe_float(sum(_safe_float(row["total_hours"]) for row in attendance_rows))
    total_packages = _safe_float(sum(_safe_float(row["total_packages"]) for row in attendance_rows))
    gross_pay = _calculate_personnel_gross_pay(
        cost_model=person_data["cost_model"],
        monthly_fixed_cost=_safe_float(person_data["monthly_fixed_cost"]),
        total_hours=total_hours,
        total_packages=total_packages,
        segments=attendance_segments,
    )
    total_deductions = _safe_float(sum(_safe_float(row["total_amount"]) for row in deduction_rows))
    existing_motor_rental = sum(
        _safe_float(row["total_amount"])
        for row in deduction_rows
        if is_motor_rental_deduction_type(row["deduction_type"])
    )
    existing_motor_purchase = sum(
        _safe_float(row["total_amount"])
        for row in deduction_rows
        if is_motor_purchase_deduction_type(row["deduction_type"])
    )
    auto_motor_rental = calculate_company_motor_rental_deduction(
        person_data,
        resolved_month,
        existing_amount=existing_motor_rental,
    )
    auto_motor_purchase = calculate_company_motor_purchase_deduction(
        person_data,
        resolved_month,
        existing_amount=existing_motor_purchase,
    )
    total_deductions += auto_motor_rental
    total_deductions += auto_motor_purchase
    net_payment = max(gross_pay - total_deductions, 0.0)
    restaurant_names = [str(row["restaurant_label"]) for row in restaurant_rows if str(row["restaurant_label"]).strip()]
    deduction_items = [(str(row["deduction_type"]), _safe_float(row["total_amount"])) for row in deduction_rows]
    if auto_motor_rental > 0:
        deduction_items.append((MOTOR_RENTAL_DEDUCTION_TYPE, auto_motor_rental))
    if auto_motor_purchase > 0:
        deduction_items.append((MOTOR_PURCHASE_DEDUCTION_TYPE, auto_motor_purchase))

    return PayrollDocumentPayload(
        selected_month=resolved_month,
        personnel_id=personnel_id,
        personnel=str(person_data["full_name"] or "-"),
        person_code=str(person_data["person_code"] or ""),
        role=str(person_data["role"] or "-"),
        status=str(person_data["status"] or "-"),
        total_hours=total_hours,
        total_packages=total_packages,
        gross_pay=gross_pay,
        total_deductions=total_deductions,
        net_payment=net_payment,
        restaurant_names=restaurant_names,
        deduction_items=deduction_items,
    )


def _build_local_payroll_dashboard(
    conn: psycopg.Connection,
    *,
    selected_month: str | None,
    role_filter: str | None,
    restaurant_filter: str | None,
    limit: int,
) -> PayrollDashboardResponse:
    month_options, attendance_month_options = _fetch_payroll_month_options(conn)
    if not month_options:
        return PayrollDashboardResponse(
            module="payroll",
            status="active",
            month_options=[],
            selected_month=None,
            role_options=[],
            restaurant_options=[],
            selected_role="Tümü",
            selected_restaurant="Tümü",
            summary=None,
            entries=[],
            cost_model_breakdown=[],
            role_breakdown=[],
            top_personnel=[],
        )

    resolved_month = _resolve_payroll_dashboard_month(month_options, attendance_month_options, selected_month)
    selected_role = role_filter or "Tümü"
    selected_restaurant = restaurant_filter or "Tümü"

    role_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(role, '-') AS role
        FROM personnel
        WHERE COALESCE(role, '') <> ''
        ORDER BY role
        """
    ).fetchall()
    role_options = ["Tümü", *[str(row["role"]) for row in role_rows if row["role"]]]
    role_options = list(dict.fromkeys(role_options))
    if selected_role not in role_options:
        selected_role = "Tümü"

    restaurant_rows = conn.execute(
        f"""
        SELECT DISTINCT COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {_month_key_sql('d.entry_date')} = %s
        ORDER BY restaurant_label
        """,
        (resolved_month,),
    ).fetchall()
    restaurant_options = ["Tümü", *[str(row["restaurant_label"]) for row in restaurant_rows if row["restaurant_label"]]]
    restaurant_options = list(dict.fromkeys(restaurant_options))
    if selected_restaurant not in restaurant_options:
        selected_restaurant = "Tümü"

    attendance_query = """
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            d.restaurant_id,
            COALESCE(r.brand, '') AS brand,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {month_key_sql} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
    """.format(month_key_sql=_month_key_sql("d.entry_date"))
    attendance_params: list[object] = [resolved_month]
    if selected_restaurant != "Tümü":
        attendance_query += """
          AND COALESCE(r.brand || ' - ' || r.branch, '-') = %s
        """
        attendance_params.append(selected_restaurant)
    attendance_query += """
        GROUP BY
            COALESCE(d.actual_personnel_id, d.planned_personnel_id),
            d.restaurant_id,
            COALESCE(r.brand, '')
    """
    attendance_rows = conn.execute(attendance_query, tuple(attendance_params)).fetchall()

    deductions_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_deductions
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') NOT IN {_PAYROLL_IGNORED_DEDUCTION_SQL}
        GROUP BY personnel_id
        """,
        (resolved_month,),
    ).fetchall()
    existing_motor_rental_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_motor_rental
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') IN {_MOTOR_RENTAL_DEDUCTION_SQL}
        GROUP BY personnel_id
        """,
        (resolved_month,),
    ).fetchall()

    personnel_rows = conn.execute(
        """
        SELECT
            id,
            COALESCE(full_name, '-') AS full_name,
            COALESCE(role, '-') AS role,
            COALESCE(status, '-') AS status,
            COALESCE(cost_model, '-') AS cost_model,
            COALESCE(monthly_fixed_cost, 0) AS monthly_fixed_cost,
            start_date,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, 'Hayır') AS motor_rental,
            COALESCE(motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            motor_purchase_start_date,
            COALESCE(motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction
        FROM personnel
        """
    ).fetchall()

    attendance_by_person: dict[int, dict[str, object]] = {}
    for row in attendance_rows:
        if row["personnel_id"] is None:
            continue
        person_id = int(row["personnel_id"])
        bucket = attendance_by_person.setdefault(
            person_id,
            {
                "total_hours": 0.0,
                "total_packages": 0.0,
                "restaurant_ids": set(),
                "segments": [],
            },
        )
        total_hours = _safe_float(row["total_hours"])
        total_packages = _safe_float(row["total_packages"])
        bucket["total_hours"] = _safe_float(bucket.get("total_hours")) + total_hours
        bucket["total_packages"] = _safe_float(bucket.get("total_packages")) + total_packages
        restaurant_ids = bucket["restaurant_ids"]
        if isinstance(restaurant_ids, set) and row["restaurant_id"] is not None:
            restaurant_ids.add(int(row["restaurant_id"]))
        segments = bucket["segments"]
        if isinstance(segments, list):
            segments.append(
                {
                    "brand": str(row["brand"] or ""),
                    "total_hours": total_hours,
                    "total_packages": total_packages,
                }
            )
    for bucket in attendance_by_person.values():
        restaurant_ids = bucket.get("restaurant_ids")
        bucket["restaurant_count"] = len(restaurant_ids) if isinstance(restaurant_ids, set) else 0
        bucket.pop("restaurant_ids", None)
    deductions_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_deductions"])
        for row in deductions_rows
        if row["personnel_id"] is not None
    }
    existing_motor_rental_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_motor_rental"])
        for row in existing_motor_rental_rows
        if row["personnel_id"] is not None
    }
    existing_motor_purchase_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(SUM(amount), 0) AS total_motor_purchase
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') IN {_MOTOR_PURCHASE_DEDUCTION_SQL}
        GROUP BY personnel_id
        """,
        (resolved_month,),
    ).fetchall()
    existing_motor_purchase_by_person = {
        int(row["personnel_id"]): _safe_float(row["total_motor_purchase"])
        for row in existing_motor_purchase_rows
        if row["personnel_id"] is not None
    }

    personnel_index = {int(row["id"]): row for row in personnel_rows if row["id"] is not None}
    auto_motor_rental_by_person: dict[int, float] = {}
    auto_motor_purchase_by_person: dict[int, float] = {}
    for person_id, person in personnel_index.items():
        auto_motor_rental = calculate_company_motor_rental_deduction(
            dict(person),
            resolved_month,
            existing_amount=existing_motor_rental_by_person.get(person_id, 0.0),
        )
        if auto_motor_rental > 0:
            auto_motor_rental_by_person[person_id] = auto_motor_rental
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_rental
        auto_motor_purchase = calculate_company_motor_purchase_deduction(
            dict(person),
            resolved_month,
            existing_amount=existing_motor_purchase_by_person.get(person_id, 0.0),
        )
        if auto_motor_purchase > 0:
            auto_motor_purchase_by_person[person_id] = auto_motor_purchase
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_purchase

    relevant_personnel_ids = sorted(
        set(attendance_by_person)
        | set(deductions_by_person)
        | set(auto_motor_rental_by_person)
        | set(auto_motor_purchase_by_person)
    )

    entries_payload: list[PayrollEntry] = []
    for person_id in relevant_personnel_ids:
        person = personnel_index.get(person_id)
        if person is None:
            continue
        role = str(person["role"] or "-")
        if selected_role != "Tümü" and role != selected_role:
            continue

        attendance = attendance_by_person.get(person_id, {})
        total_hours = _safe_float(attendance.get("total_hours"))
        total_packages = _safe_float(attendance.get("total_packages"))
        restaurant_count = int(attendance.get("restaurant_count") or 0)
        segments = attendance.get("segments")
        gross_pay = _calculate_personnel_gross_pay(
            cost_model=person["cost_model"],
            monthly_fixed_cost=_safe_float(person["monthly_fixed_cost"]),
            total_hours=total_hours,
            total_packages=total_packages,
            segments=segments if isinstance(segments, list) else [],
        )
        total_deductions = _safe_float(deductions_by_person.get(person_id))
        net_payment = max(gross_pay - total_deductions, 0.0)
        cost_model_key = str(person["cost_model"] or "-")

        entries_payload.append(
            PayrollEntry(
                personnel_id=person_id,
                personnel=str(person["full_name"] or "-"),
                role=role,
                status=str(person["status"] or "-"),
                total_hours=total_hours,
                total_packages=total_packages,
                gross_pay=gross_pay,
                total_deductions=total_deductions,
                net_payment=net_payment,
                restaurant_count=restaurant_count,
                cost_model=_COST_MODEL_LABELS.get(cost_model_key, cost_model_key),
            )
        )

    entries_payload.sort(key=lambda row: (-row.net_payment, row.personnel))
    entries_payload = entries_payload[:limit]

    cost_model_breakdown: list[PayrollCostModelBreakdownEntry] = []
    if entries_payload:
        grouped_entries: dict[str, dict[str, float | int]] = {}
        for entry in entries_payload:
            bucket = grouped_entries.setdefault(
                entry.cost_model,
                {
                    "personnel_count": 0,
                    "total_hours": 0.0,
                    "total_packages": 0.0,
                    "net_payment": 0.0,
                },
            )
            bucket["personnel_count"] = int(bucket["personnel_count"]) + 1
            bucket["total_hours"] = float(bucket["total_hours"]) + entry.total_hours
            bucket["total_packages"] = float(bucket["total_packages"]) + entry.total_packages
            bucket["net_payment"] = float(bucket["net_payment"]) + entry.net_payment

        cost_model_breakdown = [
            PayrollCostModelBreakdownEntry(
                cost_model=cost_model,
                personnel_count=int(values["personnel_count"]),
                total_hours=float(values["total_hours"]),
                total_packages=float(values["total_packages"]),
                net_payment=float(values["net_payment"]),
            )
            for cost_model, values in sorted(
                grouped_entries.items(),
                key=lambda item: float(item[1]["net_payment"]),
                reverse=True,
            )
        ]

    role_breakdown: list[PayrollRoleBreakdownEntry] = []
    if entries_payload:
        grouped_roles: dict[str, dict[str, float | int]] = {}
        for entry in entries_payload:
            bucket = grouped_roles.setdefault(
                entry.role,
                {
                    "personnel_count": 0,
                    "total_hours": 0.0,
                    "total_packages": 0.0,
                    "net_payment": 0.0,
                },
            )
            bucket["personnel_count"] = int(bucket["personnel_count"]) + 1
            bucket["total_hours"] = float(bucket["total_hours"]) + entry.total_hours
            bucket["total_packages"] = float(bucket["total_packages"]) + entry.total_packages
            bucket["net_payment"] = float(bucket["net_payment"]) + entry.net_payment

        role_breakdown = [
            PayrollRoleBreakdownEntry(
                role=role,
                personnel_count=int(values["personnel_count"]),
                total_hours=float(values["total_hours"]),
                total_packages=float(values["total_packages"]),
                net_payment=float(values["net_payment"]),
            )
            for role, values in sorted(
                grouped_roles.items(),
                key=lambda item: float(item[1]["net_payment"]),
                reverse=True,
            )
        ]

    top_personnel = [
        PayrollTopPersonnelEntry(
            personnel_id=entry.personnel_id,
            personnel=entry.personnel,
            role=entry.role,
            total_hours=entry.total_hours,
            total_packages=entry.total_packages,
            total_deductions=entry.total_deductions,
            net_payment=entry.net_payment,
            restaurant_count=entry.restaurant_count,
            cost_model=entry.cost_model,
        )
        for entry in entries_payload[:8]
    ]

    summary = None
    if entries_payload:
        summary = PayrollSummary(
            selected_month=resolved_month,
            personnel_count=len(entries_payload),
            total_hours=_safe_float(sum(entry.total_hours for entry in entries_payload)),
            total_packages=_safe_float(sum(entry.total_packages for entry in entries_payload)),
            gross_payroll=_safe_float(sum(entry.gross_pay for entry in entries_payload)),
            total_deductions=_safe_float(sum(entry.total_deductions for entry in entries_payload)),
            net_payment=_safe_float(sum(entry.net_payment for entry in entries_payload)),
        )

    return PayrollDashboardResponse(
        module="payroll",
        status="active",
        month_options=month_options,
        selected_month=resolved_month,
        role_options=role_options,
        restaurant_options=restaurant_options,
        selected_role=selected_role,
        selected_restaurant=selected_restaurant,
        summary=summary,
        entries=entries_payload,
        cost_model_breakdown=cost_model_breakdown,
        role_breakdown=role_breakdown,
        top_personnel=top_personnel,
    )
