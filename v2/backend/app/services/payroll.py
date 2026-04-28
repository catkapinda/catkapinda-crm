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
    return f"{sign}{whole.replace(',', '.')},{decimal} ₺"


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


def _register_pdf_font() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        (
            "/System/Library/Fonts/SFNS.ttf",
            "/System/Library/Fonts/SFNS.ttf",
        ),
        (
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/SFCompact.ttf",
        ),
        (
            "/System/Library/Fonts/Geneva.ttf",
            "/System/Library/Fonts/Geneva.ttf",
        ),
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        (
            "/System/Library/Fonts/Supplemental/Verdana.ttf",
            "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
        ),
        (
            "/System/Library/Fonts/Supplemental/Tahoma.ttf",
            "/System/Library/Fonts/Supplemental/Tahoma Bold.ttf",
        ),
        (
            "/Library/Fonts/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/local/share/fonts/DejaVuSans.ttf",
            "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
        ),
    ]
    for regular_path, bold_path in candidates:
        regular = Path(regular_path)
        bold = Path(bold_path)
        if not regular.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("CRMFont", str(regular)))
            if bold.exists():
                pdfmetrics.registerFont(TTFont("CRMFontBold", str(bold)))
            else:
                pdfmetrics.registerFont(TTFont("CRMFontBold", str(regular)))
            return "CRMFont", "CRMFontBold"
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"


def _payroll_logo_path() -> Path:
    return _repo_root() / "v2/frontend/public/catkapinda_logo.png"


def _render_payroll_document_pdf(payload: PayrollDocumentPayload) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader, simpleSplit
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError:
        return _render_basic_payroll_pdf(payload)

    try:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        font_name, font_bold = _register_pdf_font()
        margin_x = 36
        top_y = height - 36
        page_width = width - (margin_x * 2)

        palette = {
            "navy": (17 / 255, 24 / 255, 39 / 255),
            "navy_soft": (31 / 255, 41 / 255, 55 / 255),
            "paper": (1, 1, 1),
            "surface": (248 / 255, 250 / 255, 252 / 255),
            "line": (226 / 255, 232 / 255, 240 / 255),
            "text": (17 / 255, 24 / 255, 39 / 255),
            "muted": (107 / 255, 114 / 255, 128 / 255),
            "accent": (107 / 255, 114 / 255, 128 / 255),
            "accent_soft": (243 / 255, 244 / 255, 246 / 255),
            "green": (22 / 255, 163 / 255, 74 / 255),
            "green_soft": (236 / 255, 253 / 255, 245 / 255),
            "red": (220 / 255, 38 / 255, 38 / 255),
            "red_soft": (254 / 255, 242 / 255, 242 / 255),
            "blue_soft": (241 / 255, 245 / 255, 249 / 255),
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

        def write_center(
            text: str,
            center_x: float,
            y: float,
            size: int = 10,
            *,
            color_key: str = "text",
            font_override: str | None = None,
        ) -> None:
            set_fill(color_key)
            selected_font = font_override or font_name
            pdf.setFont(selected_font, size)
            pdf.drawCentredString(center_x, y, str(text))

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

        def draw_logo(
            x: float,
            y: float,
            logo_width: float,
            logo_height: float,
        ) -> bool:
            logo_path = _payroll_logo_path()
            if not logo_path.exists():
                return False
            try:
                pdf.drawImage(
                    ImageReader(str(logo_path)),
                    x,
                    y,
                    width=logo_width,
                    height=logo_height,
                    mask="auto",
                    preserveAspectRatio=True,
                    anchor="c",
                )
                return True
            except Exception:
                return False

        def write_right(
            text: str,
            right_x: float,
            y: float,
            size: int = 10,
            *,
            color_key: str = "text",
            font_override: str | None = None,
        ) -> None:
            set_fill(color_key)
            selected_font = font_override or font_name
            pdf.setFont(selected_font, size)
            pdf.drawRightString(right_x, y, str(text))

        def text_width(text: str, size: int, *, font_override: str | None = None) -> float:
            selected_font = font_override or font_name
            pdf.setFont(selected_font, size)
            return pdf.stringWidth(str(text), selected_font, size)

        def fit_text_size(
            text: str,
            max_width: float,
            preferred_size: int,
            min_size: int,
            *,
            font_override: str | None = None,
        ) -> int:
            for size in range(preferred_size, min_size - 1, -1):
                if text_width(text, size, font_override=font_override) <= max_width:
                    return size
            return min_size

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

        def draw_shadow_card(
            x: float,
            y: float,
            card_width: float,
            card_height: float,
            *,
            fill_key: str = "paper",
            radius: float = 14,
        ) -> None:
            pdf.saveState()
            pdf.setFillAlpha(0.03)
            pdf.setFillColorRGB(15 / 255, 23 / 255, 42 / 255)
            pdf.roundRect(x, y - 1.5, card_width, card_height, radius, stroke=0, fill=1)
            pdf.restoreState()
            draw_rounded_card(x, y, card_width, card_height, fill_key=fill_key, stroke_key="line", radius=radius)

        def draw_section_marker(x: float, y: float, *, color_key: str = "accent") -> None:
            set_fill(color_key)
            pdf.circle(x + 2, y + 2, 2, stroke=0, fill=1)
            set_stroke(color_key)
            pdf.setLineWidth(1.2)
            pdf.line(x + 8, y + 2, x + 18, y + 2)

        def ensure_space(current_y: float, needed_height: float) -> float:
            if current_y - needed_height >= 40:
                return current_y
            pdf.showPage()
            return height - 50

        month_label = _format_month_label(payload.selected_month)
        restaurant_text = ", ".join(payload.restaurant_names) if payload.restaurant_names else "Bu ay restoran kaydı bulunamadı."
        restaurant_count = len(payload.restaurant_names)

        deduction_rows: list[tuple[list[str], str, float]] = []
        if payload.deduction_items:
            for deduction_type, amount in payload.deduction_items:
                deduction_rows.append(([str(deduction_type or "Kesinti")], f"-{_format_currency_pdf(amount)}", 22.0))
        else:
            deduction_rows.append((["Bu ay için kesinti kaydı bulunamadı."], "-", 22.0))

        set_fill("surface")
        pdf.rect(0, 0, width, height, stroke=0, fill=1)

        margin_x = 36
        top_y = height - 36
        page_width = width - (margin_x * 2)
        section_gap = 16
        inner_gap = 8
        card_padding = 16
        header_height = 86
        flow_height = 68
        detail_height = 136
        deductions_header_height = 24
        deductions_intro_height = 40
        table_x = margin_x + card_padding
        table_width = page_width - (card_padding * 2)
        amount_column_width = 146
        amount_right_x = table_x + table_width - 8
        amount_left_x = amount_right_x - amount_column_width
        label_column_width = amount_left_x - table_x - 12

        for index, (label_lines, amount_text, _) in enumerate(deduction_rows):
            wrapped = simpleSplit(label_lines[0], font_name, 9, label_column_width)
            row_height = max(22.0, len(wrapped) * 11.0 + 8.0)
            deduction_rows[index] = (wrapped, amount_text, row_height)

        deductions_height = deductions_intro_height + deductions_header_height + sum(row_height for _, _, row_height in deduction_rows) + 8
        total_required_height = (
            header_height
            + section_gap
            + flow_height
            + section_gap
            + detail_height
            + section_gap
            + deductions_height
            + 24
        )
        top_y = ensure_space(top_y, total_required_height)

        header_bottom = top_y - header_height
        draw_shadow_card(margin_x, header_bottom, page_width, header_height, fill_key="paper", radius=16)

        set_fill("blue_soft")
        pdf.circle(margin_x + 52, top_y - 34, 30, stroke=0, fill=1)
        has_logo = draw_logo(margin_x + 16, top_y - 70, 72, 72)
        text_x = margin_x + (96 if has_logo else 20)
        title_size = fit_text_size("Kurye Hakediş Belgesi", page_width - 150, 25, 22, font_override=font_bold)
        write_line("Kurye Hakediş Belgesi", text_x, top_y - 27, title_size, color_key="text", font_override=font_bold)
        write_line(
            f"{month_label} • Oluşturma: {date.today().strftime('%d.%m.%Y')}",
            text_x,
            top_y - 49,
            9,
            color_key="muted",
        )

        flow_top = header_bottom - section_gap
        flow_bottom = flow_top - flow_height
        draw_shadow_card(margin_x, flow_bottom, page_width, flow_height, fill_key="paper", radius=16)

        flow_inner_x = margin_x + 18
        flow_usable_width = page_width - 36
        symbol_gap = 24
        segment_width = (flow_usable_width - (symbol_gap * 2)) / 3
        label_y = flow_top - 18
        value_y = flow_top - 42
        flow_segments = [
            ("Brüt Kazanç", _format_currency_pdf(payload.gross_pay), "text", 17),
            ("Toplam Kesinti", _format_currency_pdf(payload.total_deductions), "red", 17),
            ("Net Ödeme", _format_currency_pdf(payload.net_payment), "green", 19),
        ]
        for index, (label, value, value_color, value_size) in enumerate(flow_segments):
            segment_left = flow_inner_x + index * (segment_width + symbol_gap)
            segment_center = segment_left + (segment_width / 2)
            write_center(label, segment_center, label_y, 7, color_key="muted")
            write_center(value, segment_center, value_y, value_size, color_key=value_color, font_override=font_bold)
        write_center("–", flow_inner_x + segment_width + (symbol_gap / 2), value_y + 1, 16, color_key="muted", font_override=font_bold)
        write_center("=", flow_inner_x + (segment_width * 2) + symbol_gap + (symbol_gap / 2), value_y + 1, 16, color_key="muted", font_override=font_bold)

        details_top = flow_bottom - section_gap
        details_bottom = details_top - detail_height
        left_column_x = margin_x
        left_column_width = (page_width - section_gap) * 0.56
        right_column_x = left_column_x + left_column_width + section_gap
        right_column_width = page_width - left_column_width - section_gap
        draw_shadow_card(left_column_x, details_bottom, left_column_width, detail_height, fill_key="paper", radius=16)
        draw_shadow_card(right_column_x, details_bottom, right_column_width, detail_height, fill_key="paper", radius=16)

        person_name_size = fit_text_size(payload.personnel, left_column_width - 32, 18, 13, font_override=font_bold)
        write_line(payload.personnel, left_column_x + 16, details_top - 30, person_name_size, color_key="text", font_override=font_bold)

        meta_items = [
            ("Kod", payload.person_code or "-"),
            ("Rol", payload.role or "-"),
            ("Durum", payload.status or "-"),
        ]
        meta_cell_width = (left_column_width - 32 - (inner_gap * 2)) / 3
        meta_y = details_top - 56
        for index, (label, value) in enumerate(meta_items):
            meta_x = left_column_x + 16 + index * (meta_cell_width + inner_gap)
            write_line(label, meta_x, meta_y, 8, color_key="muted")
            write_line(str(value), meta_x, meta_y - 14, 10, color_key="text", font_override=font_bold)

        set_stroke("line")
        pdf.setLineWidth(1)
        divider_y = details_top - 78
        pdf.line(left_column_x + 16, divider_y, left_column_x + left_column_width - 16, divider_y)

        work_items = [
            ("Saat", _format_number_pdf(payload.total_hours, 1)),
            ("Paket", _format_number_pdf(payload.total_packages, 0)),
            ("Şube", str(restaurant_count)),
        ]
        metric_width = (left_column_width - 32 - (inner_gap * 2)) / 3
        metric_y = divider_y - 24
        for index, (label, value) in enumerate(work_items):
            metric_x = left_column_x + 16 + index * (metric_width + inner_gap)
            write_center(label, metric_x + (metric_width / 2), metric_y, 8, color_key="muted")
            write_center(value, metric_x + (metric_width / 2), metric_y - 22, 16, color_key="text", font_override=font_bold)

        write_line("Çalışılan Restoranlar", right_column_x + 16, details_top - 24, 9, color_key="muted", font_override=font_bold)
        badge_text = f"{restaurant_count} şube"
        badge_width = max(48, text_width(badge_text, 8, font_override=font_bold) + 14)
        badge_x = right_column_x + right_column_width - badge_width - 16
        badge_y = details_top - 30
        set_fill("accent_soft")
        pdf.roundRect(badge_x, badge_y, badge_width, 18, 9, stroke=0, fill=1)
        write_center(badge_text, badge_x + (badge_width / 2), badge_y + 5, 8, color_key="muted", font_override=font_bold)
        write_line("Ay içinde puantaj görülen şubeler", right_column_x + 16, details_top - 48, 8, color_key="muted")
        restaurant_lines = simpleSplit(restaurant_text, font_name, 10, right_column_width - 32)[:5]
        line_y = details_top - 82
        for restaurant_line in restaurant_lines:
            write_line(restaurant_line, right_column_x + 16, line_y, 11, color_key="text", font_override=font_bold)
            line_y -= 16

        deductions_top = details_bottom - section_gap
        deductions_bottom = deductions_top - deductions_height
        draw_shadow_card(margin_x, deductions_bottom, page_width, deductions_height, fill_key="paper", radius=16)
        write_line("Kesinti Kalemleri", margin_x + 16, deductions_top - 20, 11, color_key="text", font_override=font_bold)
        write_right(
            "Toplam Kesinti",
            margin_x + page_width - 16,
            deductions_top - 16,
            8,
            color_key="muted",
            font_override=font_bold,
        )
        write_right(
            _format_currency_pdf(payload.total_deductions),
            margin_x + page_width - 16,
            deductions_top - 31,
            12,
            color_key="red",
            font_override=font_bold,
        )

        table_top = deductions_top - deductions_intro_height
        set_fill("surface")
        pdf.roundRect(table_x, table_top - deductions_header_height, table_width, deductions_header_height, 8, stroke=0, fill=1)
        write_line("Kalem", table_x + 10, table_top - 16, 8, color_key="muted", font_override=font_bold)
        write_right("Tutar", amount_right_x, table_top - 16, 8, color_key="muted", font_override=font_bold)

        table_body_top = table_top - deductions_header_height
        content_y = table_body_top
        set_stroke("line")
        pdf.setLineWidth(0.8)
        pdf.line(table_x, table_body_top, table_x + table_width, table_body_top)
        for label_lines, amount_text, row_height in deduction_rows:
            row_top = content_y
            row_bottom = row_top - row_height
            text_y = row_top - 13
            for label_line in label_lines:
                write_line(label_line, table_x + 10, text_y, 9, color_key="text")
                text_y -= 11
            write_right(
                amount_text,
                amount_right_x,
                row_bottom + (row_height / 2) - 4,
                9,
                color_key="red" if amount_text != "-" else "muted",
                font_override=font_bold if amount_text != "-" else None,
            )
            pdf.line(table_x, row_bottom, table_x + table_width, row_bottom)
            content_y = row_bottom

        footer_y = max(deductions_bottom - 14, 18)
        write_line("Bu belge aylık kurye ödeme özetini gösterir.", margin_x, footer_y, 7, color_key="muted")

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
