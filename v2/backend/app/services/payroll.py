from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
_PAYROLL_VAT_RATE = 0.20
_PAYROLL_TEVKIFAT_RATE = 0.20
_PAYROLL_TEVKIFAT_THRESHOLD = 12000.0
_SUPPORT_HOLIDAY_DAY_DIVISOR = 30.0
_PAYROLL_IGNORED_DEDUCTION_SQL = "('Partner Kart Indirimi', 'Partner Kart İndirimi')"
_MOTOR_RENTAL_DEDUCTION_SQL = "('Motor Kirası', 'Motor Kirasi')"
_MOTOR_PURCHASE_DEDUCTION_SQL = "('Motor Satış Taksiti', 'Motor Satis Taksiti', 'Motor Satın Alım', 'Motor Satin Alim')"
_INVOICE_BASE_REDUCING_DEDUCTION_TYPES = {"Fatura Edilmeyen Tutar"}
_SUPPORT_HOLIDAY_DOUBLE_COST_MODELS = {"fixed_joker", "fixed_bolge_muduru"}
_SUPPORT_HOLIDAY_DOUBLE_ROLES = {"Joker", "Bölge Müdürü", "Bolge Muduru"}
_RELIGIOUS_HOLIDAY_DOUBLE_DATES = {
    date(2025, 3, 30),
    date(2025, 3, 31),
    date(2025, 6, 6),
    date(2025, 6, 7),
    date(2026, 3, 20),
    date(2026, 3, 21),
    date(2026, 5, 28),
    date(2026, 5, 29),
}


@dataclass(frozen=True)
class PayrollTevkifatBreakdown:
    invoice_base_amount: float
    vat_amount: float
    tevkifat_amount: float


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
    invoice_base_amount: float
    invoice_vat_amount: float
    tevkifat_amount: float
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


def _parse_attendance_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _count_support_holiday_bonus_days(attendance_dates: set[date]) -> int:
    return sum(1 for entry_date in attendance_dates if entry_date in _RELIGIOUS_HOLIDAY_DOUBLE_DATES)


def _calculate_support_holiday_bonus(
    *,
    selected_month: str,
    cost_model: object,
    role: object,
    monthly_fixed_cost: float,
    start_date: object = None,
    attendance_dates: set[date],
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    if fixed_cost <= 0:
        return 0.0
    normalized_cost_model = str(cost_model or "").strip()
    normalized_role = str(role or "").strip()
    if (
        normalized_cost_model not in _SUPPORT_HOLIDAY_DOUBLE_COST_MODELS
        and normalized_role not in _SUPPORT_HOLIDAY_DOUBLE_ROLES
    ):
        return 0.0
    start_month_prefix = str(selected_month or "").strip()
    eligible_holiday_dates = [
        holiday_date for holiday_date in _RELIGIOUS_HOLIDAY_DOUBLE_DATES if holiday_date.isoformat().startswith(start_month_prefix)
    ]
    if not eligible_holiday_dates:
        return 0.0
    parsed_start_date = _parse_attendance_date(start_date)
    active_holiday_dates = [
        holiday_date
        for holiday_date in eligible_holiday_dates
        if parsed_start_date is None or parsed_start_date <= holiday_date
    ]
    if not active_holiday_dates:
        return 0.0
    bonus_days = len(active_holiday_dates)
    if attendance_dates:
        bonus_days = max(bonus_days, _count_support_holiday_bonus_days(attendance_dates))
    if bonus_days <= 0:
        return 0.0
    return _safe_float((fixed_cost / _SUPPORT_HOLIDAY_DAY_DIVISOR) * bonus_days)


def _is_fixed_cost_model(cost_model: object) -> bool:
    model = str(cost_model or "").strip()
    return model == "fixed_monthly" or model.startswith("fixed_")


def _calculate_personnel_gross_pay(
    *,
    selected_month: str,
    cost_model: object,
    role: object,
    monthly_fixed_cost: float,
    start_date: object = None,
    total_hours: float,
    total_packages: float,
    segments: list[dict[str, object]],
    attendance_dates: set[date] | None = None,
) -> float:
    fixed_cost = _safe_float(monthly_fixed_cost)
    has_attendance = total_hours > 0 or total_packages > 0
    holiday_bonus = _calculate_support_holiday_bonus(
        selected_month=selected_month,
        cost_model=cost_model,
        role=role,
        monthly_fixed_cost=fixed_cost,
        start_date=start_date,
        attendance_dates=attendance_dates or set(),
    )
    if _is_fixed_cost_model(cost_model) and fixed_cost > 0:
        return fixed_cost + holiday_bonus
    if not has_attendance:
        return fixed_cost + holiday_bonus
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


def _calculate_payroll_tevkifat_breakdown(invoice_total: float) -> PayrollTevkifatBreakdown:
    normalized_total = max(_safe_float(invoice_total), 0.0)
    if normalized_total <= 0:
        return PayrollTevkifatBreakdown(0.0, 0.0, 0.0)

    invoice_base_amount = normalized_total / (1 + _PAYROLL_VAT_RATE)
    vat_amount = normalized_total - invoice_base_amount
    tevkifat_amount = (
        vat_amount * _PAYROLL_TEVKIFAT_RATE
        if normalized_total >= _PAYROLL_TEVKIFAT_THRESHOLD
        else 0.0
    )
    return PayrollTevkifatBreakdown(
        invoice_base_amount=_safe_float(invoice_base_amount),
        vat_amount=_safe_float(vat_amount),
        tevkifat_amount=_safe_float(tevkifat_amount),
    )


def _deduction_reduces_invoice_base(deduction_type: object) -> bool:
    normalized_type = str(deduction_type or "").strip()
    if not normalized_type:
        return False
    return (
        normalized_type in _INVOICE_BASE_REDUCING_DEDUCTION_TYPES
        or is_motor_rental_deduction_type(normalized_type)
        or is_motor_purchase_deduction_type(normalized_type)
    )


def _apply_payroll_tevkifat_as_deduction(
    *,
    gross_pay: float,
    base_deductions: float,
    invoice_base_reducing_deductions: float,
) -> tuple[float, PayrollTevkifatBreakdown, float]:
    # Payroll net payment is computed after withholding is added as a real deduction line.
    normalized_gross = max(_safe_float(gross_pay), 0.0)
    normalized_base_deductions = max(_safe_float(base_deductions), 0.0)
    normalized_invoice_base_reducing_deductions = max(_safe_float(invoice_base_reducing_deductions), 0.0)
    invoice_total = max(normalized_gross - normalized_invoice_base_reducing_deductions, 0.0)
    tevkifat = _calculate_payroll_tevkifat_breakdown(invoice_total)
    total_deductions = normalized_base_deductions + tevkifat.tevkifat_amount
    net_payment = max(normalized_gross - total_deductions, 0.0)
    return total_deductions, tevkifat, net_payment


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
            "/Library/Fonts/Inter-Regular.ttf",
            "/Library/Fonts/Inter-SemiBold.ttf",
        ),
        (
            "/Library/Fonts/Inter.ttf",
            "/Library/Fonts/Inter Bold.ttf",
        ),
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
        pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
        width, height = A4
        font_name, font_bold = _register_pdf_font()

        palette = {
            "page": (247 / 255, 248 / 255, 250 / 255),
            "paper": (1, 1, 1),
            "surface": (249 / 255, 250 / 255, 251 / 255),
            "line": (229 / 255, 231 / 255, 235 / 255),
            "text": (31 / 255, 41 / 255, 55 / 255),
            "muted": (107 / 255, 114 / 255, 128 / 255),
            "navy": (15 / 255, 30 / 255, 54 / 255),
            "green": (34 / 255, 197 / 255, 94 / 255),
            "green_soft": (236 / 255, 253 / 255, 245 / 255),
            "red": (239 / 255, 68 / 255, 68 / 255),
            "red_soft": (254 / 255, 242 / 255, 242 / 255),
            "shadow": (15 / 255, 23 / 255, 42 / 255),
        }

        margin = 24
        gap = 20
        content_x = margin
        content_width = width - (margin * 2)
        top_y = height - margin

        month_label = _format_month_label(payload.selected_month)
        created_label = date.today().strftime("%d.%m.%Y")
        restaurant_names = [str(value).strip() for value in payload.restaurant_names if str(value).strip()]
        restaurant_count = len(restaurant_names)
        restaurant_text = ", ".join(restaurant_names) if restaurant_names else "—"
        payment_status = "Ödeme Hazır"
        invoice_total = _safe_float(payload.invoice_base_amount + payload.invoice_vat_amount)
        hours_text = _format_number_pdf(payload.total_hours, 1)
        packages_text = _format_number_pdf(payload.total_packages, 0)
        branch_text = str(restaurant_count)

        deduction_rows: list[tuple[str, float | None]] = [
            (str(deduction_type or "Kesinti"), _safe_float(amount))
            for deduction_type, amount in payload.deduction_items
        ]
        if not deduction_rows:
            deduction_rows = [("—", None)]

        def set_fill(color_key: str) -> None:
            pdf.setFillColorRGB(*palette[color_key])

        def set_stroke(color_key: str) -> None:
            pdf.setStrokeColorRGB(*palette[color_key])

        def text_width(text: str, size: float, *, font_override: str | None = None) -> float:
            selected_font = font_override or font_name
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

        def write_text(
            text: str,
            x: float,
            y: float,
            size: int,
            *,
            color_key: str = "text",
            font_override: str | None = None,
        ) -> None:
            set_fill(color_key)
            pdf.setFont(font_override or font_name, size)
            pdf.drawString(x, y, str(text))

        def write_right(
            text: str,
            x: float,
            y: float,
            size: int,
            *,
            color_key: str = "text",
            font_override: str | None = None,
        ) -> None:
            set_fill(color_key)
            pdf.setFont(font_override or font_name, size)
            pdf.drawRightString(x, y, str(text))

        def write_center(
            text: str,
            center_x: float,
            y: float,
            size: int,
            *,
            color_key: str = "text",
            font_override: str | None = None,
        ) -> None:
            set_fill(color_key)
            pdf.setFont(font_override or font_name, size)
            pdf.drawCentredString(center_x, y, str(text))

        def wrap_text(text: str, max_width: float, preferred_size: int, min_size: int, *, font_override: str | None = None, max_lines: int | None = None) -> tuple[list[str], int]:
            selected_font = font_override or font_name
            size = preferred_size
            lines = simpleSplit(str(text), selected_font, size, max_width)
            while size > min_size and max_lines is not None and len(lines) > max_lines:
                size -= 1
                lines = simpleSplit(str(text), selected_font, size, max_width)
            if max_lines is not None and len(lines) > max_lines:
                lines = lines[:max_lines]
            return lines, size

        def draw_logo(x: float, y: float, logo_width: float, logo_height: float) -> bool:
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

        def draw_card(
            x: float,
            y: float,
            card_width: float,
            card_height: float,
            *,
            fill_key: str = "paper",
            radius: float = 20,
            shadow_alpha: float = 0.05,
        ) -> None:
            pdf.saveState()
            try:
                pdf.setFillAlpha(shadow_alpha)
            except Exception:
                pass
            pdf.setFillColorRGB(*palette["shadow"])
            pdf.roundRect(x, y - 2, card_width, card_height, radius, stroke=0, fill=1)
            pdf.restoreState()
            set_fill(fill_key)
            set_stroke("line")
            pdf.setLineWidth(0.8)
            pdf.roundRect(x, y, card_width, card_height, radius, stroke=1, fill=1)

        def draw_badge(
            text: str,
            x: float,
            y: float,
            *,
            fill_key: str = "surface",
            color_key: str = "muted",
        ) -> float:
            badge_width = max(54, text_width(text, 9, font_override=font_bold) + 18)
            badge_height = 22
            set_fill(fill_key)
            set_stroke("line")
            pdf.setLineWidth(0.6)
            pdf.roundRect(x, y, badge_width, badge_height, 11, stroke=1, fill=1)
            write_center(text, x + (badge_width / 2), y + 7, 9, color_key=color_key, font_override=font_bold)
            return badge_width

        def draw_avatar_icon(x: float, y: float, size: float) -> None:
            set_fill("navy")
            pdf.circle(x + (size / 2), y + (size / 2), size / 2, stroke=0, fill=1)
            pdf.saveState()
            try:
                pdf.setLineCap(1)
            except Exception:
                pass
            set_stroke("paper")
            pdf.setLineWidth(1.3)
            pdf.circle(x + (size / 2), y + (size * 0.63), size * 0.12, stroke=1, fill=0)
            pdf.arc(x + (size * 0.28), y + (size * 0.18), x + (size * 0.72), y + (size * 0.48), 20, 140)
            pdf.restoreState()

        def draw_footer_icon(x: float, y: float, size: float) -> None:
            set_fill("surface")
            set_stroke("line")
            pdf.setLineWidth(0.8)
            pdf.circle(x + (size / 2), y + (size / 2), size / 2, stroke=1, fill=1)
            set_stroke("muted")
            pdf.setLineWidth(1.2)
            center_x = x + (size / 2)
            top_icon_y = y + size - 8
            shield = pdf.beginPath()
            shield.moveTo(center_x, top_icon_y)
            shield.lineTo(center_x + 6, top_icon_y - 3)
            shield.lineTo(center_x + 4, top_icon_y - 11)
            shield.lineTo(center_x, top_icon_y - 15)
            shield.lineTo(center_x - 4, top_icon_y - 11)
            shield.lineTo(center_x - 6, top_icon_y - 3)
            shield.close()
            pdf.drawPath(shield, stroke=1, fill=0)

        def negative_currency(amount: float | None) -> str:
            if amount is None:
                return "—"
            return f"-{_format_currency_pdf(amount).lstrip('-')}"

        pdf.setTitle("Kurye Hakediş Belgesi")
        set_fill("page")
        pdf.rect(0, 0, width, height, stroke=0, fill=1)

        row_height = 24
        for index, (label, amount) in enumerate(deduction_rows):
            if amount is None:
                deduction_rows[index] = (label, None)
                continue
            wrapped_lines, _ = wrap_text(label, 210, 10, 8, max_lines=2)
            if len(wrapped_lines) > 1:
                row_height = max(row_height, 30)

        header_height = 96
        hero_height = 204
        person_height = hero_height
        deductions_height = max(196, 76 + len(deduction_rows) * row_height + 40)
        invoice_height = deductions_height
        restaurant_height = 118
        footer_height = 52

        hero_width = 332
        person_width = content_width - hero_width - gap
        mid_width = (content_width - gap) / 2

        header_top = top_y
        title_block_top = header_top - 8
        top_grid_y = header_top - header_height - hero_height
        mid_grid_y = top_grid_y - gap - deductions_height
        restaurant_y = mid_grid_y - gap - restaurant_height
        footer_y = restaurant_y - gap - footer_height

        has_logo = draw_logo(content_x, title_block_top - 24, 28, 28)
        company_x = content_x + (36 if has_logo else 0)
        write_text("ÇAT KAPINDA", company_x, title_block_top - 10, 10, color_key="navy", font_override=font_bold)
        write_right(month_label, content_x + content_width, title_block_top - 8, 11, color_key="navy", font_override=font_bold)
        write_right(f"Oluşturma: {created_label}", content_x + content_width, title_block_top - 24, 10, color_key="muted")
        title_size = fit_text_size("Kurye Hakediş Belgesi", content_width - 40, 28, 22, font_override=font_bold)
        write_text("Kurye Hakediş Belgesi", content_x, title_block_top - 62, title_size, color_key="navy", font_override=font_bold)
        write_text("Bu belge aylık kurye ödeme özetini gösterir.", content_x, title_block_top - 82, 11, color_key="muted")

        hero_x = content_x
        hero_y = top_grid_y
        draw_card(hero_x, hero_y, hero_width, hero_height, fill_key="navy", radius=22, shadow_alpha=0.12)

        pdf.saveState()
        try:
            path = pdf.beginPath()
            path.roundRect(hero_x, hero_y, hero_width, hero_height, 22)
            pdf.clipPath(path, stroke=0, fill=0)
        except Exception:
            pass
        try:
            pdf.setStrokeAlpha(0.1)
        except Exception:
            pass
        pdf.setStrokeColorRGB(1, 1, 1)
        pdf.setLineWidth(0.8)
        for radius in range(42, 170, 12):
            pdf.circle(hero_x + hero_width - 24, hero_y + hero_height - 28, radius, stroke=1, fill=0)
        pdf.restoreState()

        hero_pad = 24
        write_text("NET ÖDEME", hero_x + hero_pad, hero_y + hero_height - 34, 11, color_key="paper", font_override=font_bold)
        net_size = fit_text_size(_format_currency_pdf(payload.net_payment), hero_width - (hero_pad * 2), 30, 23, font_override=font_bold)
        write_text(_format_currency_pdf(payload.net_payment), hero_x + hero_pad, hero_y + hero_height - 84, net_size, color_key="paper", font_override=font_bold)
        set_stroke("line")
        pdf.saveState()
        try:
            pdf.setStrokeAlpha(0.16)
        except Exception:
            pass
        pdf.setLineWidth(0.8)
        pdf.line(hero_x + hero_pad, hero_y + 78, hero_x + hero_width - hero_pad, hero_y + 78)
        pdf.restoreState()

        column_width = (hero_width - (hero_pad * 2)) / 3
        hero_metrics_y = hero_y + 22
        hero_metrics = [
            ("BRÜT KAZANÇ", _format_currency_pdf(payload.gross_pay), "paper"),
            ("TOPLAM KESİNTİ", _format_currency_pdf(payload.total_deductions), "red"),
        ]
        for index, (label, value, color_key) in enumerate(hero_metrics):
            block_x = hero_x + hero_pad + (column_width * index)
            write_text(label, block_x, hero_metrics_y + 34, 8, color_key="paper" if color_key == "paper" else "paper", font_override=font_bold)
            write_right(value, block_x + column_width - 8, hero_metrics_y + 10, 13, color_key=color_key, font_override=font_bold)

        status_x = hero_x + hero_pad + (column_width * 2)
        set_fill("green")
        pdf.circle(status_x + 10, hero_metrics_y + 26, 8, stroke=0, fill=1)
        write_text("ÖDEME DURUMU", status_x + 24, hero_metrics_y + 34, 8, color_key="paper", font_override=font_bold)
        write_text(payment_status, status_x + 24, hero_metrics_y + 10, 13, color_key="green", font_override=font_bold)

        person_x = hero_x + hero_width + gap
        person_y = top_grid_y
        draw_card(person_x, person_y, person_width, person_height, radius=22)

        person_pad = 20
        avatar_size = 46
        avatar_x = person_x + person_pad
        avatar_y = person_y + person_height - person_pad - avatar_size
        draw_avatar_icon(avatar_x, avatar_y, avatar_size)
        name_x = avatar_x + avatar_size + 14
        name_width = person_width - (person_pad * 2) - avatar_size - 14
        name_size = fit_text_size(payload.personnel or "—", name_width, 18, 13, font_override=font_bold)
        write_text(payload.personnel or "—", name_x, person_y + person_height - 40, name_size, color_key="navy", font_override=font_bold)
        write_text(payload.role or "—", name_x, person_y + person_height - 60, 11, color_key="muted")

        rows_top_y = person_y + person_height - 88
        row_gap = 16
        value_right_x = person_x + person_width - person_pad
        person_rows = [
            ("Kod", payload.person_code or "—"),
            ("Rol", payload.role or "—"),
            ("Durum", payload.status or "—"),
            ("Saat", hours_text or "—"),
            ("Paket", packages_text or "—"),
            ("Şube", branch_text or "—"),
        ]
        for index, (label, value) in enumerate(person_rows):
            row_y = rows_top_y - (index * row_gap)
            write_text(label, person_x + person_pad, row_y, 10, color_key="muted")
            if label == "Durum":
                badge_width = max(54, text_width(str(value), 9, font_override=font_bold) + 18)
                draw_badge(str(value), value_right_x - badge_width, row_y - 8, fill_key="green_soft", color_key="green")
                continue
            value_size = fit_text_size(str(value), 84, 11, 8, font_override=font_bold)
            write_right(str(value), value_right_x, row_y, value_size, color_key="text", font_override=font_bold)

        left_mid_x = content_x
        right_mid_x = content_x + mid_width + gap
        draw_card(left_mid_x, mid_grid_y, mid_width, deductions_height, radius=20)
        draw_card(right_mid_x, mid_grid_y, mid_width, invoice_height, radius=20)

        card_pad = 24
        deductions_top_y = mid_grid_y + deductions_height - card_pad
        write_text("KESİNTİ KALEMLERİ", left_mid_x + card_pad, deductions_top_y, 12, color_key="navy", font_override=font_bold)
        write_right(_format_currency_pdf(payload.total_deductions), left_mid_x + mid_width - card_pad, deductions_top_y, 12, color_key="red", font_override=font_bold)
        write_right("TOPLAM KESİNTİ", left_mid_x + mid_width - card_pad, deductions_top_y + 14, 8, color_key="muted", font_override=font_bold)

        table_left = left_mid_x + card_pad
        table_right = left_mid_x + mid_width - card_pad
        table_top = deductions_top_y - 26
        write_text("Kalem", table_left, table_top, 9, color_key="muted", font_override=font_bold)
        write_right("Tutar", table_right, table_top, 9, color_key="muted", font_override=font_bold)
        set_stroke("line")
        pdf.setLineWidth(0.8)
        pdf.line(table_left, table_top - 8, table_right, table_top - 8)

        row_y = table_top - 26
        label_max_width = table_right - table_left - 120
        for label, amount in deduction_rows:
            wrapped_lines, label_size = wrap_text(label, label_max_width, 10, 8, max_lines=2)
            block_height = max(row_height, len(wrapped_lines) * (label_size + 2) + 8)
            current_line_y = row_y
            for line in wrapped_lines:
                write_text(line, table_left, current_line_y, label_size, color_key="text")
                current_line_y -= label_size + 2
            write_right(
                negative_currency(amount),
                table_right,
                row_y,
                10,
                color_key="red" if amount is not None else "muted",
                font_override=font_bold if amount is not None else None,
            )
            pdf.line(table_left, row_y - block_height + 6, table_right, row_y - block_height + 6)
            row_y -= block_height

        summary_bar_y = mid_grid_y + 18
        summary_bar_h = 34
        set_fill("surface")
        set_stroke("line")
        pdf.setLineWidth(0.6)
        pdf.roundRect(left_mid_x + card_pad, summary_bar_y, mid_width - (card_pad * 2), summary_bar_h, 12, stroke=1, fill=1)
        write_text("Toplam Kesinti", left_mid_x + card_pad + 14, summary_bar_y + 12, 10, color_key="navy", font_override=font_bold)
        write_right(_format_currency_pdf(payload.total_deductions), left_mid_x + mid_width - card_pad - 14, summary_bar_y + 12, 11, color_key="red", font_override=font_bold)

        invoice_top_y = mid_grid_y + invoice_height - card_pad
        write_text("FATURA DETAYLARI", right_mid_x + card_pad, invoice_top_y, 12, color_key="navy", font_override=font_bold)
        invoice_rows = [
            ("Fatura Matrahı", _format_currency_pdf(payload.invoice_base_amount)),
            (f"KDV (%{int(_PAYROLL_VAT_RATE * 100)})", _format_currency_pdf(payload.invoice_vat_amount)),
            ("Tevkifat", _format_currency_pdf(payload.tevkifat_amount)),
        ]
        detail_row_y = invoice_top_y - 30
        detail_row_gap = 28
        for label, value in invoice_rows:
            write_text(label, right_mid_x + card_pad, detail_row_y, 11, color_key="text")
            write_right(value, right_mid_x + mid_width - card_pad, detail_row_y, 11, color_key="navy", font_override=font_bold)
            set_stroke("line")
            pdf.setLineWidth(0.8)
            pdf.line(right_mid_x + card_pad, detail_row_y - 10, right_mid_x + mid_width - card_pad, detail_row_y - 10)
            detail_row_y -= detail_row_gap

        invoice_bar_y = mid_grid_y + 16
        invoice_bar_h = 48
        set_fill("surface")
        set_stroke("line")
        pdf.setLineWidth(0.6)
        pdf.roundRect(right_mid_x + card_pad, invoice_bar_y, mid_width - (card_pad * 2), invoice_bar_h, 14, stroke=1, fill=1)
        write_text("FATURA TOPLAMI", right_mid_x + card_pad + 14, invoice_bar_y + 28, 10, color_key="navy", font_override=font_bold)
        write_right(_format_currency_pdf(invoice_total), right_mid_x + mid_width - card_pad - 14, invoice_bar_y + 14, 17, color_key="navy", font_override=font_bold)

        draw_card(content_x, restaurant_y, content_width, restaurant_height, radius=20)
        rest_pad = 24
        title_y = restaurant_y + restaurant_height - rest_pad
        write_text("ÇALIŞILAN RESTORAN / OPERASYON NOKTASI", content_x + rest_pad, title_y, 12, color_key="navy", font_override=font_bold)
        write_text("Ay içinde puantaj görülen operasyon noktası", content_x + rest_pad, title_y - 18, 10, color_key="muted")

        restaurant_info_width = 248
        restaurant_lines, restaurant_font_size = wrap_text(restaurant_text, 170, 17, 12, font_override=font_bold, max_lines=2)
        set_fill("surface")
        set_stroke("line")
        pdf.setLineWidth(0.8)
        pdf.circle(content_x + rest_pad + 18, restaurant_y + 38, 18, stroke=1, fill=1)
        write_text(restaurant_lines[0] if restaurant_lines else "—", content_x + rest_pad + 46, restaurant_y + 48, restaurant_font_size, color_key="navy", font_override=font_bold)
        if len(restaurant_lines) > 1:
            write_text(restaurant_lines[1], content_x + rest_pad + 46, restaurant_y + 48 - restaurant_font_size - 2, restaurant_font_size, color_key="navy", font_override=font_bold)
            branch_y = restaurant_y + 16
        else:
            branch_y = restaurant_y + 28
        write_text(f"{restaurant_count} şube" if restaurant_count else "—", content_x + rest_pad + 46, branch_y, 10, color_key="muted")

        kpi_area_x = content_x + restaurant_info_width
        kpi_area_width = content_width - restaurant_info_width - rest_pad
        kpi_col_width = kpi_area_width / 3
        set_stroke("line")
        pdf.setLineWidth(0.8)
        pdf.line(kpi_area_x, restaurant_y + 18, kpi_area_x, restaurant_y + restaurant_height - 22)
        pdf.line(kpi_area_x + kpi_col_width, restaurant_y + 18, kpi_area_x + kpi_col_width, restaurant_y + restaurant_height - 22)
        pdf.line(kpi_area_x + (kpi_col_width * 2), restaurant_y + 18, kpi_area_x + (kpi_col_width * 2), restaurant_y + restaurant_height - 22)

        kpis = [
            ("TOPLAM SAAT", hours_text, "saat"),
            ("TOPLAM PAKET", packages_text, "paket"),
            ("TOPLAM ŞUBE", branch_text, "şube"),
        ]
        for index, (label, value, unit) in enumerate(kpis):
            col_x = kpi_area_x + (kpi_col_width * index) + 18
            write_text(label, col_x, restaurant_y + restaurant_height - 46, 8, color_key="muted", font_override=font_bold)
            value_size = fit_text_size(value or "—", kpi_col_width - 36, 18, 13, font_override=font_bold)
            write_text(value or "—", col_x, restaurant_y + 38, value_size, color_key="navy", font_override=font_bold)
            write_text(unit, col_x, restaurant_y + 20, 10, color_key="muted")

        draw_card(content_x, footer_y, content_width, footer_height, radius=18, shadow_alpha=0.04)
        footer_icon_x = content_x + 18
        footer_icon_y = footer_y + 10
        draw_footer_icon(footer_icon_x, footer_icon_y, 24)
        write_text(
            "Bu belge, kurye hak edişlerine ilişkin bilgilendirme amacıyla hazırlanmıştır.",
            footer_icon_x + 34,
            footer_y + 19,
            9,
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
        ("10", f"Fatura Matrahi: {_format_currency_pdf(payload.invoice_base_amount)}"),
        ("10", f"KDV: {_format_currency_pdf(payload.invoice_vat_amount)}"),
        ("10", f"Tevkifat: {_format_currency_pdf(payload.tevkifat_amount)}"),
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
        personnel_match_mask = (
            month_entries["actual_personnel_id"].fillna(month_entries["planned_personnel_id"]) == personnel_id
        )
        rest_series = (
            month_entries.loc[personnel_match_mask, "brand"].fillna("").astype(str)
            + " - "
            + month_entries.loc[personnel_match_mask, "branch"].fillna("").astype(str)
        )
        restaurant_names = [value.strip(" -") for value in sorted(rest_series.unique().tolist()) if value.strip(" -")]

    attendance_dates = {
        parsed_date
        for entry_value in month_entries.loc[
            month_entries["actual_personnel_id"].fillna(month_entries["planned_personnel_id"]) == personnel_id, "entry_date"
        ].tolist()
        if (parsed_date := _parse_attendance_date(entry_value)) is not None
    }
    person_cost_model = (
        str(person_match.iloc[0]["cost_model"] or "")
        if not person_match.empty and "cost_model" in person_match.columns
        else ""
    )
    person_fixed_cost = (
        _safe_float(person_match.iloc[0]["monthly_fixed_cost"])
        if not person_match.empty and "monthly_fixed_cost" in person_match.columns
        else 0.0
    )
    gross_pay = _safe_float(payroll_row.get("brut_maliyet")) + _calculate_support_holiday_bonus(
        selected_month=resolved_month,
        cost_model=person_cost_model,
        role=payroll_row.get("rol"),
        monthly_fixed_cost=person_fixed_cost,
        start_date=person_match.iloc[0]["start_date"] if not person_match.empty and "start_date" in person_match.columns else None,
        attendance_dates=attendance_dates,
    )
    base_deductions = _safe_float(payroll_row.get("kesinti"))
    invoice_base_reducing_deductions = _safe_float(
        sum(
            amount
            for deduction_type, amount in deduction_items
            if _deduction_reduces_invoice_base(deduction_type)
        )
    )
    total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
        gross_pay=gross_pay,
        base_deductions=base_deductions,
        invoice_base_reducing_deductions=invoice_base_reducing_deductions,
    )
    if tevkifat.tevkifat_amount > 0:
        deduction_items.append(("Tevkifat", tevkifat.tevkifat_amount))

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
        net_payment=net_payment,
        invoice_base_amount=tevkifat.invoice_base_amount,
        invoice_vat_amount=tevkifat.vat_amount,
        tevkifat_amount=tevkifat.tevkifat_amount,
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
    attendance_date_rows = conn.execute(
        f"""
        SELECT DISTINCT substr(COALESCE(d.entry_date, ''), 1, 10) AS entry_date
        FROM daily_entries d
        WHERE {_month_key_sql('d.entry_date')} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) = %s
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
        selected_month=resolved_month,
        cost_model=person_data["cost_model"],
        role=person_data["role"],
        monthly_fixed_cost=_safe_float(person_data["monthly_fixed_cost"]),
        start_date=person_data.get("start_date"),
        total_hours=total_hours,
        total_packages=total_packages,
        segments=attendance_segments,
        attendance_dates={
            parsed_date
            for row in attendance_date_rows
            if (parsed_date := _parse_attendance_date(row["entry_date"])) is not None
        },
    )
    base_deductions = _safe_float(sum(_safe_float(row["total_amount"]) for row in deduction_rows))
    invoice_base_reducing_deductions = _safe_float(
        sum(
            _safe_float(row["total_amount"])
            for row in deduction_rows
            if _deduction_reduces_invoice_base(row["deduction_type"])
        )
    )
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
    base_deductions += auto_motor_rental
    base_deductions += auto_motor_purchase
    invoice_base_reducing_deductions += auto_motor_rental
    invoice_base_reducing_deductions += auto_motor_purchase
    total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
        gross_pay=gross_pay,
        base_deductions=base_deductions,
        invoice_base_reducing_deductions=invoice_base_reducing_deductions,
    )
    restaurant_names = [str(row["restaurant_label"]) for row in restaurant_rows if str(row["restaurant_label"]).strip()]
    deduction_items = [(str(row["deduction_type"]), _safe_float(row["total_amount"])) for row in deduction_rows]
    if auto_motor_rental > 0:
        deduction_items.append((MOTOR_RENTAL_DEDUCTION_TYPE, auto_motor_rental))
    if auto_motor_purchase > 0:
        deduction_items.append((MOTOR_PURCHASE_DEDUCTION_TYPE, auto_motor_purchase))
    if tevkifat.tevkifat_amount > 0:
        deduction_items.append(("Tevkifat", tevkifat.tevkifat_amount))

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
        invoice_base_amount=tevkifat.invoice_base_amount,
        invoice_vat_amount=tevkifat.vat_amount,
        tevkifat_amount=tevkifat.tevkifat_amount,
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
    attendance_date_rows = conn.execute(
        """
        SELECT
            COALESCE(d.actual_personnel_id, d.planned_personnel_id) AS personnel_id,
            substr(COALESCE(d.entry_date, ''), 1, 10) AS entry_date
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE {month_key_sql} = %s
          AND COALESCE(d.actual_personnel_id, d.planned_personnel_id) IS NOT NULL
        {restaurant_filter_clause}
        GROUP BY
            COALESCE(d.actual_personnel_id, d.planned_personnel_id),
            substr(COALESCE(d.entry_date, ''), 1, 10)
        """.format(
            month_key_sql=_month_key_sql("d.entry_date"),
            restaurant_filter_clause="" if selected_restaurant == "Tümü" else "AND COALESCE(r.brand || ' - ' || r.branch, '-') = %s",
        ),
        tuple(attendance_params),
    ).fetchall()

    deduction_rows = conn.execute(
        f"""
        SELECT
            personnel_id,
            COALESCE(deduction_type, 'Kesinti') AS deduction_type,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM deductions
        WHERE {_month_key_sql('deduction_date')} = %s
          AND personnel_id IS NOT NULL
          AND COALESCE(deduction_type, '') NOT IN {_PAYROLL_IGNORED_DEDUCTION_SQL}
        GROUP BY personnel_id, COALESCE(deduction_type, 'Kesinti')
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
    attendance_dates_by_person: dict[int, set[date]] = {}
    for row in attendance_date_rows:
        if row["personnel_id"] is None:
            continue
        parsed_date = _parse_attendance_date(row["entry_date"])
        if parsed_date is None:
            continue
        attendance_dates_by_person.setdefault(int(row["personnel_id"]), set()).add(parsed_date)
    deductions_by_person: dict[int, float] = {}
    invoice_base_reducing_deductions_by_person: dict[int, float] = {}
    for row in deduction_rows:
        if row["personnel_id"] is None:
            continue
        person_id = int(row["personnel_id"])
        amount = _safe_float(row["total_amount"])
        deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + amount
        if _deduction_reduces_invoice_base(row["deduction_type"]):
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + amount
            )
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
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + auto_motor_rental
            )
        auto_motor_purchase = calculate_company_motor_purchase_deduction(
            dict(person),
            resolved_month,
            existing_amount=existing_motor_purchase_by_person.get(person_id, 0.0),
        )
        if auto_motor_purchase > 0:
            auto_motor_purchase_by_person[person_id] = auto_motor_purchase
            deductions_by_person[person_id] = _safe_float(deductions_by_person.get(person_id)) + auto_motor_purchase
            invoice_base_reducing_deductions_by_person[person_id] = (
                _safe_float(invoice_base_reducing_deductions_by_person.get(person_id)) + auto_motor_purchase
            )

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
            selected_month=resolved_month,
            cost_model=person["cost_model"],
            role=person["role"],
            monthly_fixed_cost=_safe_float(person["monthly_fixed_cost"]),
            start_date=person["start_date"],
            total_hours=total_hours,
            total_packages=total_packages,
            segments=segments if isinstance(segments, list) else [],
            attendance_dates=attendance_dates_by_person.get(person_id, set()),
        )
        base_deductions = _safe_float(deductions_by_person.get(person_id))
        invoice_base_reducing_deductions = _safe_float(invoice_base_reducing_deductions_by_person.get(person_id))
        total_deductions, tevkifat, net_payment = _apply_payroll_tevkifat_as_deduction(
            gross_pay=gross_pay,
            base_deductions=base_deductions,
            invoice_base_reducing_deductions=invoice_base_reducing_deductions,
        )
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
                tevkifat_amount=tevkifat.tevkifat_amount,
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
            total_tevkifat=_safe_float(sum(entry.tevkifat_amount for entry in entries_payload)),
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
