from __future__ import annotations

import calendar
import html
from io import BytesIO
import os
import re
import secrets
import smtplib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from builders.analytics_builders import (
    build_dashboard_brand_summary,
    build_dashboard_priority_alerts,
    build_dashboard_profit_snapshots,
)
from ui.dashboard_sections import (
    render_dashboard_action_sections,
    render_dashboard_activity_sections,
    render_dashboard_finance_and_hygiene_sections,
    render_dashboard_focus_sections,
    render_dashboard_summary_cards,
)
from infrastructure.db_engine import (
    CompatConnection,
    adapt_sql,
    configure_db_engine,
    connect_database,
    fetch_df,
)
from builders.entity_builders import (
    build_personnel_hero_stats,
    build_personnel_list_rows,
    build_personnel_preview_options,
    build_personnel_preview_snapshot_items,
    build_personnel_recent_snapshot_items,
    build_restaurant_hero_stats,
    build_restaurant_list_rows,
    build_restaurant_snapshot_items,
    ensure_dataframe_columns,
)
from rules.form_rules import (
    build_motor_usage_payload,
    clear_new_person_onboarding_state,
    collect_onboarding_equipment_payloads,
    configure_form_rules,
    initialize_onboarding_equipment_state,
    onboarding_equipment_state_key,
    render_motor_deduction_snapshot_from_payload,
    render_motor_purchase_proration_caption,
    render_vehicle_transition_caption,
    validate_onboarding_equipment_payloads,
    validate_personnel_form,
    validate_restaurant_form,
)
from builders.ops_builders import (
    build_auto_deduction_warning_text,
    build_bulk_deduction_option_map,
    build_deduction_grid_rows,
    build_deduction_option_map,
    build_purchase_grid_rows,
    build_purchase_option_map,
    filter_deductions_by_source,
    get_deduction_source_filter_caption,
)
from rules.personnel_rules import (
    configure_personnel_rules,
    get_role_fixed_cost_label,
    initialize_edit_person_transition_state,
    is_fixed_cost_model,
    normalize_cost_model_value,
    resolve_accounting_defaults,
    resolve_company_setup_defaults,
    resolve_cost_role_option,
    resolve_effective_role_from_transition,
    resolve_fixed_cost_model,
    resolve_motor_rental_value,
    resolve_motor_usage_fields,
    resolve_motor_usage_mode,
    resolve_vehicle_type_value,
    role_requires_primary_restaurant,
    validate_role_transition_inputs,
)
from ui.personnel_sections import (
    render_personnel_add_workspace,
    render_personnel_edit_workspace,
    render_personnel_list_workspace,
    render_personnel_plate_workspace,
)
from rules.equipment_rules import (
    configure_equipment_rules,
    describe_auto_source_key,
    equipment_issue_generates_installments,
    get_default_equipment_sale_price,
    get_default_equipment_unit_cost,
    get_default_issue_installment_count,
    get_equipment_cost_snapshot,
    get_equipment_vat_rate,
    latest_average_cost,
    normalize_equipment_issue_installment_count,
)
from rules.reporting_rules import (
    build_invoice_summary_df,
    build_restaurant_export_filename,
    calculate_customer_invoice,
    configure_reporting_rules,
    get_operational_restaurant_names_for_period,
    month_bounds,
)
from engines.finance_engine import (
    build_branch_profitability,
    calculate_personnel_cost,
    configure_finance_engine,
)
from infrastructure.bootstrap_engine import (
    configure_bootstrap_engine,
    database_has_operational_data,
    ensure_runtime_bootstrap,
    import_sqlite_into_current_db,
)
from infrastructure.auth_engine import (
    build_login_logo_markup,
    cleanup_auth_sessions,
    clear_authenticated_user,
    configure_auth_engine,
    create_auth_session,
    get_auth_user,
    get_query_param,
    hash_auth_password,
    init_auth_state,
    normalize_auth_identity,
    restore_auth_session,
    revoke_current_auth_session,
    set_authenticated_user,
    set_query_param,
    sync_default_auth_users,
    verify_auth_password,
)
from ui.backup_sections import (
    configure_backup_sections,
    render_backup_tools_content,
)
from ui.report_sections import (
    render_cost_report_tab,
    render_distribution_report_tab,
    render_invoice_report_tab,
    render_profit_report_tab,
    render_shared_overhead_report_tab,
    render_side_income_report_tab,
)
from ui.restaurant_sections import (
    render_restaurant_add_workspace,
    render_restaurant_edit_workspace,
    render_restaurant_list_workspace,
)
from ui.ui_helpers import (
    apply_text_search,
    build_grid_rows,
    fmt_number,
    fmt_try,
    format_display_df,
    render_action_card,
    render_alert_stack,
    render_dashboard_data_grid,
    render_dashboard_section_header,
    render_executive_metrics,
    render_field_label,
    render_management_hero,
    render_record_snapshot,
    render_tab_header,
    render_workspace_loading_shell,
    section_intro,
)
from services.reporting_service import (
    build_reports_workspace_payload,
    load_reporting_entries_and_month_options,
)
from services.personnel_service import (
    load_personnel_workspace_payload,
)
from repositories.personnel_repository import (
    fetch_active_restaurant_options,
    fetch_person_options_map,
)


DEFAULT_AUTH_PASSWORD = "123456"
APP_PAGE_TITLE = "Çat Kapında | Operasyon Paneli"
APP_PAGE_ICON = "🧭"
RUNTIME_BOOTSTRAP_VERSION = "2026-03-22-manual-motor-deductions"
LOGIN_LOGO_CANDIDATES = [
    "assets/catkapinda_logo.png",
    "assets/catkapinda_logo.jpg",
    "assets/catkapinda_logo.jpeg",
    "assets/catkapinda_logo.svg",
    "catkapinda_logo.png",
    "catkapinda_logo.jpg",
    "catkapinda_logo.jpeg",
    "catkapinda_logo.svg",
    "logo.png",
    "logo.jpg",
    "logo.jpeg",
    "logo.svg",
]
DEFAULT_AUTH_USERS = [
    {
        "email": "ebru@catkapinda.com",
        "full_name": "Ebru Aslan",
        "role": "admin",
        "role_display": "Yönetim Kurulu / Yönetici",
    },
    {
        "email": "mert.kurtulus@catkapinda.com",
        "full_name": "Mert Kurtuluş",
        "role": "admin",
        "role_display": "Yönetim Kurulu / Yönetici",
    },
    {
        "email": "muhammed.terim@catkapinda.com",
        "full_name": "Muhammed Terim",
        "role": "admin",
        "role_display": "Yönetim Kurulu / Yönetici",
    },
]
LEGACY_AUTH_IDENTITIES = {"catkapinda", "chef"}
PASSWORD_HASH_ITERATIONS = 200_000
TEMP_PASSWORD_LENGTH = 10
SMTP_PORT_DEFAULT = 587

APP_DATA_DIR = Path.home() / "Documents" / "CatKapindaData"
DB_PATH = APP_DATA_DIR / "catkapinda_crm.db"
LEGACY_DB_PATHS = [
    Path(__file__).with_name("catkapinda_crm.db"),
    Path.home() / "Desktop" / "catkapinda_crm.db",
    Path.home() / "Desktop" / "catkapinda_crm_v1" / "catkapinda_crm.db",
]
configure_db_engine(
    app_data_dir=APP_DATA_DIR,
    db_path=DB_PATH,
    legacy_db_paths=LEGACY_DB_PATHS,
)
AUTH_QUERY_KEY = "ck_session"
AUTH_SESSION_DAYS = 30
VAT_RATE_DEFAULT = 20.0
COURIER_HOURLY_COST = 250.0  # KDV dahil
COURIER_PACKAGE_COST_DEFAULT_LOW = 20.0
COURIER_PACKAGE_COST_DEFAULT_HIGH = 25.0
COURIER_PACKAGE_COST_QC = 25.0
PACKAGE_THRESHOLD_DEFAULT = 390
AUTO_MOTOR_RENTAL_DEDUCTION = 13000.0
MOTOR_RENTAL_STANDARD_MONTH_DAYS = 30
MOTOR_RENTAL_VAT_RATE = 20.0
AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION = 11250.0
AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT = 12
AUTO_MOTOR_PURCHASE_TOTAL_PRICE = AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION * AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT
MOTOR_PURCHASE_COMMITMENT_OPTIONS = [12, 15, 18]
MOTOR_USAGE_MODE_OPTIONS = ["Kendi Motoru", "Çat Kapında Motor Kirası", "Çat Kapında Motor Satışı"]
DEDUCTION_SOURCE_FILTER_OPTIONS = [
    "Tümü",
    "Manuel Kayıtlar",
]
SYSTEM_PERSONNEL_AUTO_DEDUCTION_PREFIXES = (
    "auto:motor_rental:",
    "auto:motor_purchase:",
    "auto:accounting:",
    "auto:company_setup",
)
AUTO_ACCOUNTING_DEDUCTION = 2000.0
AUTO_ACCOUNTANT_COST = 1400.0
AUTO_COMPANY_SETUP_DEDUCTION = 1500.0
AUTO_COMPANY_SETUP_REVENUE = 1500.0
AUTO_COMPANY_SETUP_COST = 500.0
AUTO_EQUIPMENT_INSTALLMENT_COUNT = 2
EQUIPMENT_REDUCED_VAT_START_DATE = date(2026, 3, 1)
EQUIPMENT_VAT_RATE_BEFORE_REDUCTION = 20.0
EQUIPMENT_VAT_RATE_AFTER_REDUCTION = 10.0
EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS = {"Kask", "Telefon Tutacağı", "Motor Kirası", "Motor Satın Alım"}
TEXTILE_ITEM_NAMES = {"Polar", "Tişört", "Korumalı Mont", "Yelek", "Yağmurluk"}
AUTO_ONBOARDING_ITEMS = [
    {"key": "box", "item_name": "Box", "unit_sale_price": 3200.0, "vat_rate": 20.0},
    {"key": "punch", "item_name": "Punch", "unit_sale_price": 2000.0, "vat_rate": 20.0},
    {"key": "korumali_mont", "item_name": "Korumalı Mont", "unit_sale_price": 4750.0, "vat_rate": 10.0},
]
AUTO_ONBOARDING_EXCLUDED_KEYS_BY_BRAND = {
    "Köroğlu Pide": {"box", "punch"},
    "Doğu Otomotiv": {"box", "punch"},
}
PRICING_MODEL_LABELS = {
    "hourly_plus_package": "Hacimsiz Primli",
    "threshold_package": "Hacimli Primli",
    "hourly_only": "Sadece Saatlik",
    "fixed_monthly": "Sabit Aylık Ücret",
}
MENU_DISPLAY_LABELS = {
    "Genel Bakış": "Genel Bakış",
    "Restoran Yönetimi": "Restoran Yönetimi",
    "Personel Yönetimi": "Personel Yönetimi",
    "Puantaj": "Puantaj",
    "Satın Alma": "Satın Alma",
    "Kesinti Yönetimi": "Kesinti Yönetimi",
    "Aylık Hakediş": "Aylık Hakediş",
    "Raporlar ve Karlılık": "Raporlar ve Karlılık",
    "Güncellemeler ve Duyurular": "Güncellemeler ve Duyurular",
}
MENU_SECTIONS = [
    ("Kontrol", ["Genel Bakış"]),
    ("Operasyon", ["Puantaj", "Kesinti Yönetimi"]),
    ("Kayıtlar", ["Restoran Yönetimi", "Personel Yönetimi", "Satın Alma"]),
    ("Finans", ["Aylık Hakediş", "Raporlar ve Karlılık"]),
    ("Kurumsal", ["Güncellemeler ve Duyurular"]),
]
FIXED_COST_MODEL_BY_ROLE = {
    "Kurye": "fixed_kurye",
    "Bölge Müdürü": "fixed_bolge_muduru",
    "Saha Denetmen Şefi": "fixed_saha_denetmen_sefi",
    "Restoran Takım Şefi": "fixed_restoran_takim_sefi",
    "Joker": "fixed_joker",
}
PERSONNEL_ROLE_OPTIONS = ["Kurye", "Bölge Müdürü", "Saha Denetmen Şefi", "Restoran Takım Şefi", "Joker"]
MANAGEMENT_ROLE_OPTIONS = ["Bölge Müdürü", "Saha Denetmen Şefi", "Restoran Takım Şefi"]
FIXED_COST_MODEL_LABELS = {
    "fixed_kurye": "Kurye",
    "fixed_bolge_muduru": "Bölge Müdürü",
    "fixed_saha_denetmen_sefi": "Saha Denetmen Şefi",
    "fixed_restoran_takim_sefi": "Restoran Takım Şefi",
    "fixed_joker": "Joker",
}
VISIBLE_COST_MODEL_OPTIONS = PERSONNEL_ROLE_OPTIONS
COST_MODEL_LABELS = {
    "standard_courier": "Kurye",
    **FIXED_COST_MODEL_LABELS,
    "fixed_monthly": "Sabit Aylık Ücret",
}
configure_personnel_rules(
    auto_accounting_deduction=AUTO_ACCOUNTING_DEDUCTION,
    auto_accountant_cost=AUTO_ACCOUNTANT_COST,
    auto_company_setup_revenue=AUTO_COMPANY_SETUP_REVENUE,
    auto_company_setup_cost=AUTO_COMPANY_SETUP_COST,
    fixed_cost_model_by_role=FIXED_COST_MODEL_BY_ROLE,
    personnel_role_options=PERSONNEL_ROLE_OPTIONS,
)
ACTIVE_STATUS_LABELS = {
    1: "Aktif",
    0: "Pasif",
    "1": "Aktif",
    "0": "Pasif",
}
ALLOCATION_SOURCE_LABELS = {
    "Degisken maliyet": "Değişken maliyet",
    "Sabit maliyet payi": "Sabit maliyet payı",
    "Sabit maliyet tam atama": "Sabit maliyet tam atama",
    "Paylasilan yonetim maliyeti": "Ortak Operasyon Payı",
}
SHARED_OVERHEAD_ROLES = {"Joker", "Bölge Müdürü"}
TABLE_EXPORT_ORDER = [
    "restaurants",
    "personnel",
    "personnel_role_history",
    "personnel_vehicle_history",
    "plate_history",
    "daily_entries",
    "deductions",
    "inventory_purchases",
    "courier_equipment_issues",
    "box_returns",
    "auth_users",
    "auth_sessions",
]


@dataclass
class PricingRule:
    pricing_model: str
    hourly_rate: float
    package_rate: float
    package_threshold: int
    package_rate_low: float
    package_rate_high: float
    fixed_monthly_fee: float
    vat_rate: float


def first_row_value(row: Any, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        values = list(row.values())
        return values[0] if values else default
    try:
        return row[0]
    except Exception:
        pass
    if hasattr(row, "keys"):
        try:
            keys = list(row.keys())
            if keys:
                return row[keys[0]]
        except Exception:
            pass
    try:
        return next(iter(row))
    except Exception:
        return default


def get_row_value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        value = row.get(key, default)
    else:
        try:
            value = row[key]
        except Exception:
            try:
                value = row.get(key, default)
            except Exception:
                value = default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return value


def parse_date_value(value: Any) -> date | None:
    if value in [None, ""]:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value)
    except Exception:
        return None
    if pd.isna(parsed):
        return None
    return parsed.date()


def coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "evet"}


def generate_temporary_password(length: int = TEMP_PASSWORD_LENGTH) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_smtp_config() -> dict[str, Any] | None:
    try:
        if "smtp" in st.secrets:
            smtp_secrets = st.secrets["smtp"]
            host = str(smtp_secrets.get("host", "") or "").strip()
            from_email = str(smtp_secrets.get("from_email", "") or "").strip()
            if host and from_email:
                return {
                    "host": host,
                    "port": int(smtp_secrets.get("port", SMTP_PORT_DEFAULT)),
                    "username": str(smtp_secrets.get("username", "") or "").strip(),
                    "password": str(smtp_secrets.get("password", "") or ""),
                    "from_email": from_email,
                    "from_name": str(smtp_secrets.get("from_name", "Çat Kapında CRM") or "Çat Kapında CRM").strip(),
                    "use_ssl": coerce_bool(smtp_secrets.get("use_ssl"), default=False),
                    "starttls": coerce_bool(smtp_secrets.get("starttls"), default=True),
                }
    except Exception:
        pass

    host = str(os.getenv("SMTP_HOST", "") or "").strip()
    from_email = str(os.getenv("SMTP_FROM_EMAIL", "") or "").strip()
    if not host or not from_email:
        return None

    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", str(SMTP_PORT_DEFAULT)) or SMTP_PORT_DEFAULT),
        "username": str(os.getenv("SMTP_USERNAME", "") or "").strip(),
        "password": str(os.getenv("SMTP_PASSWORD", "") or ""),
        "from_email": from_email,
        "from_name": str(os.getenv("SMTP_FROM_NAME", "Çat Kapında CRM") or "Çat Kapında CRM").strip(),
        "use_ssl": coerce_bool(os.getenv("SMTP_USE_SSL"), default=False),
        "starttls": coerce_bool(os.getenv("SMTP_STARTTLS"), default=True),
    }


def send_temporary_password_email(recipient_email: str, full_name: str, temporary_password: str) -> None:
    smtp_config = get_smtp_config()
    if not smtp_config:
        raise RuntimeError("Şifre sıfırlama maili için SMTP ayarları henüz tanımlı değil.")

    message = EmailMessage()
    message["Subject"] = "Çat Kapında CRM | Geçici Giriş Şifresi"
    message["From"] = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
    message["To"] = recipient_email
    message.set_content(
        f"""Merhaba {full_name or 'Çat Kapında ekibi'},

Çat Kapında Operasyon CRM hesabın için yeni geçici giriş şifren oluşturuldu.

Geçici Şifre: {temporary_password}

Giriş yaptıktan sonra sağ üstteki Profil alanından şifreni hemen güncellemeni öneririz.

Giriş adresi: https://crmcatkapinda.com

Bu işlemi sen yapmadıysan lütfen sistem yöneticisine hemen bilgi ver.

Çat Kapında CRM
"""
    )

    try:
        if smtp_config["use_ssl"]:
            with smtplib.SMTP_SSL(smtp_config["host"], int(smtp_config["port"]), timeout=20) as server:
                if smtp_config["username"]:
                    server.login(smtp_config["username"], smtp_config["password"])
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_config["host"], int(smtp_config["port"]), timeout=20) as server:
                if smtp_config["starttls"]:
                    server.starttls()
                if smtp_config["username"]:
                    server.login(smtp_config["username"], smtp_config["password"])
                server.send_message(message)
    except Exception as exc:
        raise RuntimeError("Şifre sıfırlama maili gönderilemedi. SMTP ayarlarını kontrol et.") from exc


def set_flash_message(level: str, text: str) -> None:
    st.session_state["ck_flash_message"] = {
        "level": str(level or "info"),
        "text": str(text or ""),
    }


def render_flash_message() -> None:
    payload = st.session_state.pop("ck_flash_message", None)
    if not payload:
        return
    level = str(payload.get("level", "info") or "info").strip().lower()
    message_text = str(payload.get("text", "") or "").strip()
    if not message_text:
        return

    toast_icon = {
        "success": ":material/check_circle:",
        "warning": ":material/warning:",
        "error": ":material/error:",
        "info": ":material/info:",
    }.get(level, ":material/info:")
    st.toast(message_text, icon=toast_icon)

    if level == "success":
        st.success(message_text)
    elif level == "warning":
        st.warning(message_text)
    elif level == "error":
        st.error(message_text)
    else:
        st.info(message_text)


def insert_equipment_issue_and_get_id(
    conn: CompatConnection,
    personnel_id: int,
    issue_date_str: str,
    item_name: str,
    quantity: int,
    unit_cost: float,
    unit_sale_price: float,
    installment_count: int,
    sale_type: str,
    notes: str,
    vat_rate: float = VAT_RATE_DEFAULT,
    auto_source_key: str | None = None,
) -> int:
    if conn.backend == "postgres":
        row = conn.execute(
            """
            INSERT INTO courier_equipment_issues
            (personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, installment_count, sale_type, auto_source_key, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (personnel_id, issue_date_str, item_name, quantity, unit_cost, unit_sale_price, vat_rate, installment_count, sale_type, auto_source_key, notes),
        ).fetchone()
        return int(first_row_value(row, 0))

    conn.execute(
        """
        INSERT INTO courier_equipment_issues
        (personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, installment_count, sale_type, auto_source_key, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (personnel_id, issue_date_str, item_name, quantity, unit_cost, unit_sale_price, vat_rate, installment_count, sale_type, auto_source_key, notes),
    )
    return int(first_row_value(conn.execute("SELECT last_insert_rowid()").fetchone(), 0))


def get_conn() -> CompatConnection:
    conn = connect_database()
    ensure_runtime_bootstrap(conn)
    return conn


def login_gate(conn: sqlite3.Connection) -> bool:
    init_auth_state()

    if st.session_state.authenticated or restore_auth_session(conn):
        return True

    logo_markup = build_login_logo_markup()
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewContainer"] > .main {
            background:
                radial-gradient(circle at 12% 16%, rgba(14, 92, 233, 0.16), transparent 18%),
                radial-gradient(circle at 86% 10%, rgba(30, 196, 255, 0.14), transparent 18%),
                linear-gradient(180deg, #F4F8FF 0%, #EEF5FF 100%);
        }

        .main .block-container {
            max-width: 1240px;
            padding-top: clamp(1.25rem, 4vw, 2.6rem);
            padding-bottom: clamp(2rem, 4vw, 3.6rem);
        }

        .ck-login-gap {
            display: none;
        }

        .ck-login-hero-card {
            position: relative;
            overflow: hidden;
            min-height: 700px;
            padding: 34px 34px 30px;
            border-radius: 34px;
            color: #FFFFFF;
            background:
                radial-gradient(circle at 88% 14%, rgba(92, 204, 255, 0.34), transparent 24%),
                radial-gradient(circle at 10% 0%, rgba(255,255,255,0.16), transparent 26%),
                linear-gradient(140deg, #04153D 0%, #0A44C2 45%, #10A7E8 100%);
            box-shadow: 0 34px 80px rgba(4, 21, 61, 0.32);
        }

        .ck-login-hero-card::before {
            content: "";
            position: absolute;
            inset: auto -110px -150px auto;
            width: 320px;
            height: 320px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(255,255,255,0.20) 0%, rgba(255,255,255,0) 66%);
            pointer-events: none;
        }

        .ck-login-hero-card::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0) 34%);
            pointer-events: none;
        }

        .ck-login-hero-brand {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 1.4rem;
        }

        .ck-login-hero-brand-note {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 9px 14px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.16);
            background: rgba(255,255,255,0.12);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.10);
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: rgba(255,255,255,0.90);
        }

        .ck-login-logo-showcase .ck-login-logo-mark {
            width: 168px;
            height: 168px;
            flex: 0 0 168px;
            border-radius: 44px;
            background: rgba(255,255,255,0.10);
            box-shadow: 0 28px 48px rgba(0, 8, 34, 0.28);
        }

        .ck-login-logo-showcase .ck-login-logo-mark-image {
            background: rgba(255,255,255,0.95);
            border: 1px solid rgba(255,255,255,0.30);
            padding: 10px;
        }

        .ck-login-logo-showcase .ck-login-logo-image {
            object-fit: contain;
            border-radius: 34px;
            image-rendering: auto;
        }

        .ck-login-hero-kicker {
            position: relative;
            z-index: 1;
            color: rgba(255,255,255,0.82);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.9rem;
        }

        .ck-login-hero-title {
            position: relative;
            z-index: 1;
            margin: 0;
            color: #FFFFFF;
            font-size: clamp(2.42rem, 3.7vw, 4.05rem);
            line-height: 0.98;
            letter-spacing: -0.075em;
            font-weight: 880;
            max-width: 720px;
        }

        .ck-login-hero-subtitle {
            position: relative;
            z-index: 1;
            margin: 1.2rem 0 1.55rem;
            max-width: 630px;
            color: rgba(255,255,255,0.84);
            font-size: 0.96rem;
            line-height: 1.72;
        }

        .ck-login-hero-proof-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 1.4rem;
        }

        .ck-login-hero-proof-card {
            min-height: 150px;
            padding: 18px 18px 16px;
            border-radius: 24px;
            background: linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08));
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
            backdrop-filter: blur(14px);
        }

        .ck-login-hero-proof-card span {
            display: block;
            margin-bottom: 0.6rem;
            color: rgba(255,255,255,0.74);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .ck-login-hero-proof-card strong {
            display: block;
            color: #FFFFFF;
            font-size: 0.94rem;
            line-height: 1.62;
            font-weight: 760;
        }

        .ck-login-hero-stats {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
        }

        .ck-login-hero-stat {
            padding: 18px 20px;
            border-radius: 24px;
            background: linear-gradient(180deg, rgba(4, 15, 44, 0.34), rgba(4, 15, 44, 0.18));
            border: 1px solid rgba(255,255,255,0.14);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
        }

        .ck-login-hero-stat small {
            display: block;
            color: rgba(255,255,255,0.76);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .ck-login-hero-stat strong {
            display: block;
            color: #FFFFFF;
            font-size: 0.94rem;
            line-height: 1.66;
            font-weight: 760;
        }

        .ck-login-panel-head {
            position: relative;
            overflow: hidden;
            border-radius: 32px;
            padding: 26px 26px 22px;
            background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(248,252,255,0.96) 100%);
            border: 1px solid rgba(220, 231, 250, 0.90);
            box-shadow: 0 22px 56px rgba(18, 31, 61, 0.08);
            margin-bottom: 14px;
        }

        .ck-login-panel-head::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 170px;
            background:
                radial-gradient(circle at 100% 0%, rgba(46, 165, 255, 0.18), transparent 36%),
                radial-gradient(circle at 0% 40%, rgba(13, 76, 205, 0.12), transparent 24%);
            pointer-events: none;
        }

        .ck-login-panel-kicker,
        .ck-login-form-title {
            position: relative;
            z-index: 1;
            color: #4D6E9F;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.13em;
            text-transform: uppercase;
        }

        .ck-login-panel-title {
            position: relative;
            z-index: 1;
            margin-top: 0.8rem;
            color: #111F39;
            font-size: 1.82rem;
            line-height: 1.02;
            font-weight: 860;
            letter-spacing: -0.06em;
        }

        .ck-login-panel-subtitle,
        .ck-login-form-subtitle {
            position: relative;
            z-index: 1;
            margin-top: 0.7rem;
            color: #60738F;
            line-height: 1.68;
            font-size: 0.9rem;
        }

        .ck-login-panel-badges {
            position: relative;
            z-index: 1;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 1.05rem;
        }

        .ck-login-panel-badges span {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            border: 1px solid #DBE7FB;
            background: rgba(255,255,255,0.82);
            color: #0D4CCD;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.04em;
        }

        div[data-testid="stForm"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(249,252,255,0.98) 100%);
            border: 1px solid rgba(220, 231, 250, 0.92);
            border-radius: 30px;
            padding: 20px 22px 14px;
            box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(16px);
            margin-bottom: 12px;
        }

        div[data-testid="stForm"] label p,
        .stCheckbox label {
            color: #324766 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stForm"] [data-testid="stTextInputRootElement"] input {
            min-height: 56px;
            height: 56px;
            border-radius: 18px;
            background: #F7FAFF;
            border: 1px solid #DCE7FA;
            padding: 0 18px !important;
            line-height: 1.2 !important;
            display: flex;
            align-items: center;
        }

        div[data-testid="stForm"] [data-baseweb="input"] {
            align-items: center;
        }

        div[data-testid="stForm"] [data-baseweb="input"] > div {
            min-height: 56px;
            background: transparent !important;
            border: none !important;
            display: flex;
            align-items: center;
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {
            min-height: 3.2rem;
            border-radius: 18px;
            border: none;
            background: linear-gradient(135deg, #0C49D8 0%, #12A3EA 100%);
            color: white;
            box-shadow: 0 20px 36px rgba(12, 73, 216, 0.24);
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button p {
            color: white !important;
        }

        .stButton > button {
            min-height: 3rem;
            border-radius: 18px;
            border: 1px solid #D9E6FB;
            background: rgba(255,255,255,0.92);
            color: #0D4CCD;
            font-weight: 820;
            box-shadow: 0 14px 28px rgba(17, 37, 77, 0.05);
        }

        .ck-login-help-card {
            margin-top: 0.85rem;
            padding: 18px 18px 16px;
            border-radius: 26px;
            background: linear-gradient(180deg, #F8FBFF 0%, #F1F6FF 100%);
            border: 1px solid #DCE7FB;
            box-shadow: 0 16px 30px rgba(14, 34, 69, 0.06);
        }

        .ck-login-help-title {
            color: #10203A;
            font-size: 1rem;
            font-weight: 840;
            margin-bottom: 0.4rem;
        }

        .ck-login-help-text {
            color: #4E617D;
            font-size: 0.86rem;
            line-height: 1.64;
        }

        .ck-login-help-steps {
            display: grid;
            gap: 9px;
            margin-top: 0.85rem;
        }

        .ck-login-help-step {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            color: #294467;
            font-size: 0.83rem;
            line-height: 1.5;
        }

        .ck-login-help-step-badge {
            width: 24px;
            height: 24px;
            flex: 0 0 24px;
            border-radius: 999px;
            background: #E8F0FF;
            color: #0D4CCD;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.76rem;
            font-weight: 900;
        }

        .ck-login-footer-note {
            margin-top: 0.4rem;
            padding: 14px 16px;
            border-radius: 20px;
            background: rgba(255,255,255,0.74);
            border: 1px solid rgba(219,228,245,0.88);
            color: #5E6E89;
            line-height: 1.64;
            font-size: 0.86rem;
        }

        @media (max-width: 1200px) {
            .ck-login-hero-proof-grid,
            .ck-login-hero-stats {
                grid-template-columns: 1fr;
            }

            .ck-login-hero-title {
                font-size: clamp(2.35rem, 4vw, 3.6rem);
            }
        }

        @media (max-width: 992px) {
            .ck-login-hero-card {
                min-height: auto;
            }

            .ck-login-logo-showcase .ck-login-logo-mark {
                width: 142px;
                height: 142px;
                flex: 0 0 142px;
                border-radius: 36px;
            }
        }

        @media (max-width: 640px) {
            .main .block-container {
                padding-top: 0.9rem;
                padding-left: 0.95rem;
                padding-right: 0.95rem;
            }

            .ck-login-hero-card {
                padding: 22px 20px 18px;
                border-radius: 28px;
            }

            .ck-login-logo-showcase .ck-login-logo-mark {
                width: 118px;
                height: 118px;
                flex: 0 0 118px;
                border-radius: 30px;
            }

            .ck-login-panel-head {
                padding: 20px 18px 18px;
                border-radius: 26px;
            }

            .ck-login-panel-title {
                font-size: 1.52rem;
            }

            .ck-login-hero-title {
                font-size: 2rem;
            }

            .ck-login-hero-subtitle {
                font-size: 0.9rem;
            }

            div[data-testid="stForm"] {
                padding: 16px 16px 12px;
                border-radius: 26px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([0.04, 1.0, 0.04])
    with center:
        hero_col, form_col = st.columns([1.12, 0.88], gap="large")

        with hero_col:
            st.markdown(
                f"""
                <div class="ck-login-hero-card">
                    <div class="ck-login-hero-brand">
                        <div class="ck-login-hero-brand-note">TESLİMAT OPERASYONU KOMUTA MERKEZİ</div>
                        <div class="ck-login-logo-showcase">{logo_markup}</div>
                    </div>
                    <div class="ck-login-hero-kicker">ÇAT KAPINDA OPERASYON CRM</div>
                    <div class="ck-login-hero-title">Teslimat operasyonunun tüm katmanlarını tek merkezde yönetin.</div>
                    <div class="ck-login-hero-subtitle">Çat Kapında Operasyon CRM, şube yapısından saha akışına ve finansal performansa kadar tüm operasyonu tek panelde birleştirir. Dağınık süreçleri ortadan kaldırır, karar alma hızını artırır ve operasyonu ölçeklenebilir bir yapıya dönüştürür.</div>
                    <div class="ck-login-hero-proof-grid">
                        <div class="ck-login-hero-proof-card">
                            <span>Şube Yönetimi</span>
                            <strong>Şube ağı, anlaşma yapıları ve operasyonel durum tek merkezden kontrol edilir.</strong>
                        </div>
                        <div class="ck-login-hero-proof-card">
                            <span>Saha Operasyonu</span>
                            <strong>Kurye hareketleri, puantaj ve zimmet süreçleri anlık olarak izlenir ve yönetilir.</strong>
                        </div>
                        <div class="ck-login-hero-proof-card">
                            <span>Finans Yönetimi</span>
                            <strong>Hakediş, maliyet ve kârlılık verileri tek panelde toplanarak finansal görünürlük sağlanır.</strong>
                        </div>
                    </div>
                    <div class="ck-login-hero-stats">
                        <div class="ck-login-hero-stat">
                            <small>Operasyonel Veriyi Yönetime Dönüştüren Altyapı</small>
                            <strong>Tüm operasyon katmanlarının tek sistemde birleşmesi, veri kaybını ortadan kaldırır ve sürdürülebilir büyüme için gerekli olan kontrol, şeffaflık ve standardizasyonu sağlar.</strong>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with form_col:
            st.markdown(
                """
                <div class="ck-login-panel-head">
                    <div class="ck-login-panel-kicker">Karar süreçlerini hızlandıran erişim</div>
                    <div class="ck-login-panel-title">Operasyonel verilere anlık erişim sağlayın</div>
                    <div class="ck-login-panel-subtitle">Operasyonel verilere anlık erişim sağlayarak yönetim süreçlerini gecikmesiz şekilde sürdürün. Sahadaki değişimlere hızlı tepki verin, kontrolü kaybetmeden operasyonu yönetin.</div>
                    <div class="ck-login-panel-badges">
                        <span>Anlık veri erişimi</span>
                        <span>Hızlı karar alma</span>
                        <span>Kesintisiz yönetim</span>
                    </div>
                </div>
                <div class="ck-login-form-title">Hesap Bilgileri</div>
                <div class="ck-login-form-subtitle">Kurumsal e-posta adresin ve güncel şifrenle girişini tamamla.</div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("E-posta Adresi", placeholder="ornek@catkapinda.com")
                password = st.text_input("Şifre", type="password", placeholder="Şifreni gir")
                remember_me = st.checkbox("Bu Cihazı Hatırla", value=True, help="Kişisel cihazlarda açık bırakabilirsin.")
                submitted = st.form_submit_button("Panele Gir", use_container_width=True)

            st.markdown(
                """
                <div class="ck-login-footer-note">Giriş bilgilerin kurumsal e-posta hesabına tanımlıdır. Parolan unutulursa sistem yeni geçici şifreni e-posta kutuna otomatik iletir; panele girdikten sonra Profil alanından şifreni hemen güncelleyebilirsin.</div>
                """,
                unsafe_allow_html=True,
            )

            forgot_email = ""
            forgot_submitted = False

            if st.button("Şifremi Unuttum", key="login_help_toggle", use_container_width=True):
                st.session_state.login_help_visible = not st.session_state.get("login_help_visible", False)

            if st.session_state.get("login_help_visible"):
                st.markdown(
                    """
                    <div class="ck-login-help-card">
                        <div class="ck-login-help-title">Sifre Destegi</div>
                        <div class="ck-login-help-text">Kurumsal e-posta adresini gir. Sistem, aktif hesabina yeni bir gecici sifre uretip e-posta ile iletsin.</div>
                        <div class="ck-login-help-steps">
                            <div class="ck-login-help-step"><span class="ck-login-help-step-badge">1</span><span>Kurumsal e-posta adresini yaz ve yeni gecici sifreyi talep et.</span></div>
                            <div class="ck-login-help-step"><span class="ck-login-help-step-badge">2</span><span>Gecici sifre e-posta adresine gelsin ve bu sifreyle giris yap.</span></div>
                            <div class="ck-login-help-step"><span class="ck-login-help-step-badge">3</span><span>Panele girdikten sonra sag ustteki <strong>Profil</strong> alanindan sifreni hemen degistir.</span></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.form("forgot_password_form", clear_on_submit=True):
                    forgot_email = st.text_input("Kurumsal E-Posta Adresi", placeholder="ornek@catkapinda.com")
                    forgot_submitted = st.form_submit_button("Yeni Geçici Şifre Gönder", use_container_width=True)

            if forgot_submitted:
                reset_identity = normalize_auth_identity(forgot_email)
                reset_user = get_auth_user(conn, reset_identity)
                if not reset_user or safe_int(get_row_value(reset_user, "is_active", 0), 0) != 1:
                    st.error("Bu e-posta adresi için aktif bir hesap bulunamadı.")
                else:
                    temporary_password = generate_temporary_password()
                    try:
                        conn.execute(
                            """
                            UPDATE auth_users
                            SET password_hash = ?, must_change_password = 1, updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                hash_auth_password(temporary_password),
                                datetime.utcnow().isoformat(timespec="seconds"),
                                int(get_row_value(reset_user, "id", 0) or 0),
                            ),
                        )
                        send_temporary_password_email(
                            reset_identity,
                            str(get_row_value(reset_user, "full_name", "") or ""),
                            temporary_password,
                        )
                        conn.commit()
                        st.session_state.login_help_visible = False
                        st.success("Yeni geçici şifren e-posta adresine gönderildi. Giriş yaptıktan sonra Profil alanından şifreni güncelle.")
                    except RuntimeError as exc:
                        conn.rollback()
                        st.error(str(exc))
                    except Exception:
                        conn.rollback()
                        st.error("Şifre sıfırlama işlemi tamamlanamadı. Birkaç dakika sonra tekrar dene.")

        if submitted:
            entered_username = normalize_auth_identity(username)
            user = get_auth_user(conn, entered_username)
            if user and safe_int(get_row_value(user, "is_active", 0), 0) == 1 and verify_auth_password(password, str(get_row_value(user, "password_hash", "") or "")):
                token = create_auth_session(conn, entered_username) if remember_me else None
                if token:
                    set_query_param(AUTH_QUERY_KEY, token)
                else:
                    set_query_param(AUTH_QUERY_KEY, None)
                set_authenticated_user(user, token)
                st.session_state.login_help_visible = False
                st.session_state.login_transition_active = True
                st.rerun()
            else:
                st.error("E-posta adresi veya şifre hatalı.")
    return False


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="ck-side-brand-shell">
            <div class="ck-side-brand-kicker">Teslimat Operasyonu</div>
            <div class="ck-side-brand-title">Çat Kapında Operasyon CRM</div>
            <div class="ck-side-brand-copy">Teslimat operasyonu yönetim paneli</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_navigation(menu_items: list[str], current_menu: str) -> str:
    resolved_menu = current_menu if current_menu in menu_items else (menu_items[0] if menu_items else "")
    for section_title, section_items in MENU_SECTIONS:
        visible_items = [item for item in section_items if item in menu_items]
        if not visible_items:
            continue
        st.sidebar.markdown(
            f"<div class='ck-side-section-title'>{html.escape(section_title)}</div>",
            unsafe_allow_html=True,
        )
        for item in visible_items:
            is_selected = item == resolved_menu
            clicked = st.sidebar.button(
                MENU_DISPLAY_LABELS.get(item, item),
                key=f"sidebar_nav_{item}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            )
            if clicked and not is_selected:
                st.session_state["ck_main_menu"] = item
                st.rerun()
    return resolved_menu


def render_boot_shell() -> Any:
    if st.session_state.get("_ck_boot_shell_rendered"):
        return None
    placeholder = st.empty()
    placeholder.markdown(
        """
        <style>
            .ck-boot-shell {
                display: grid;
                place-items: center;
                min-height: 62vh;
                padding: 2rem 1rem 1rem;
            }

            .ck-boot-card {
                width: min(520px, 100%);
                padding: 1.5rem 1.5rem 1.35rem;
                border-radius: 28px;
                border: 1px solid rgba(201, 216, 242, 0.92);
                background:
                    radial-gradient(circle at top right, rgba(42, 132, 255, 0.12), transparent 34%),
                    linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,251,255,0.96) 100%);
                box-shadow: 0 24px 60px rgba(15, 23, 42, 0.10);
            }

            .ck-boot-kicker {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.45rem 0.8rem;
                border-radius: 999px;
                background: #F1F6FF;
                border: 1px solid #D7E4FA;
                color: #2857AF;
                font-size: 0.74rem;
                font-weight: 800;
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }

            .ck-boot-title {
                margin-top: 1rem;
                color: #111F39;
                font-size: clamp(1.7rem, 3vw, 2.35rem);
                line-height: 1.06;
                letter-spacing: -0.05em;
                font-weight: 880;
            }

            .ck-boot-copy {
                margin-top: 0.8rem;
                color: #5A6D89;
                font-size: 0.98rem;
                line-height: 1.7;
            }

            .ck-boot-loader {
                margin-top: 1.15rem;
                width: 100%;
                height: 10px;
                overflow: hidden;
                border-radius: 999px;
                background: #EAF1FB;
            }

            .ck-boot-loader-bar {
                width: 42%;
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, #0C4BCB 0%, #1A9EF0 100%);
                animation: ckBootPulse 1.2s ease-in-out infinite;
                transform-origin: left center;
            }

            @keyframes ckBootPulse {
                0% { transform: translateX(-18%) scaleX(0.82); opacity: 0.72; }
                50% { transform: translateX(92%) scaleX(1.04); opacity: 1; }
                100% { transform: translateX(210%) scaleX(0.88); opacity: 0.72; }
            }
        </style>
        <div class="ck-boot-shell">
            <div class="ck-boot-card">
                <div class="ck-boot-kicker">🧭 Operasyon Paneli Hazırlanıyor</div>
                <div class="ck-boot-title">Çat Kapında sistem bileşenleri yükleniyor.</div>
                <div class="ck-boot-copy">Veritabanı bağlantısı ve oturum kontrolleri hazırlanıyor. İlk açılışta kısa bir yüklenme süresi görülebilir.</div>
                <div class="ck-boot-loader"><div class="ck-boot-loader-bar"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return placeholder


def render_login_transition_overlay() -> None:
    if not st.session_state.get("login_transition_active"):
        return

    st.markdown(
        """
        <style>
            .ck-login-transition-overlay {
                position: fixed;
                inset: 0;
                z-index: 999999;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1.25rem;
                background:
                    radial-gradient(circle at top right, rgba(10, 76, 210, 0.10), transparent 22%),
                    linear-gradient(180deg, rgba(247, 250, 255, 0.98) 0%, rgba(240, 246, 255, 0.98) 100%);
                backdrop-filter: blur(12px);
                animation: ckLoginOverlayFade 1.05s ease forwards;
                pointer-events: none;
            }

            .ck-login-transition-card {
                width: min(460px, 100%);
                padding: 1.35rem 1.35rem 1.2rem;
                border-radius: 26px;
                border: 1px solid rgba(207, 220, 243, 0.96);
                background: rgba(255,255,255,0.92);
                box-shadow: 0 26px 60px rgba(15, 23, 42, 0.12);
            }

            .ck-login-transition-kicker {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.42rem 0.76rem;
                border-radius: 999px;
                background: #EEF5FF;
                border: 1px solid #D5E3FB;
                color: #295AB3;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }

            .ck-login-transition-title {
                margin-top: 0.9rem;
                color: #13233D;
                font-size: clamp(1.45rem, 3vw, 1.95rem);
                line-height: 1.08;
                letter-spacing: -0.04em;
                font-weight: 880;
            }

            .ck-login-transition-text {
                margin-top: 0.7rem;
                color: #5F7290;
                font-size: 0.94rem;
                line-height: 1.7;
            }

            .ck-login-transition-loader {
                margin-top: 0.95rem;
                width: 100%;
                height: 10px;
                overflow: hidden;
                border-radius: 999px;
                background: #E9F1FB;
            }

            .ck-login-transition-loader-bar {
                width: 38%;
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, #0C4BCB 0%, #1A9EF0 100%);
                animation: ckLoginOverlayPulse 0.95s ease-in-out infinite;
                transform-origin: left center;
            }

            @keyframes ckLoginOverlayPulse {
                0% { transform: translateX(-20%) scaleX(0.86); opacity: 0.76; }
                50% { transform: translateX(108%) scaleX(1.02); opacity: 1; }
                100% { transform: translateX(228%) scaleX(0.9); opacity: 0.76; }
            }

            @keyframes ckLoginOverlayFade {
                0%, 65% { opacity: 1; visibility: visible; }
                100% { opacity: 0; visibility: hidden; }
            }
        </style>
        <div class="ck-login-transition-overlay">
            <div class="ck-login-transition-card">
                <div class="ck-login-transition-kicker">🧭 Oturum Açıldı</div>
                <div class="ck-login-transition-title">Çalışma alanı hazırlanıyor.</div>
                <div class="ck-login-transition-text">Panel yüklenirken önceki giriş ekranı gizleniyor. Operasyon görünümü birkaç saniye içinde hazır olacak.</div>
                <div class="ck-login-transition-loader"><div class="ck-login-transition-loader-bar"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.login_transition_active = False


def logout_button(conn: sqlite3.Connection) -> None:
    if st.sidebar.button("Oturumu Kapat", use_container_width=True):
        revoke_current_auth_session(conn)
        st.rerun()


def render_top_profile(conn: CompatConnection) -> None:
    current_user = get_auth_user(conn, str(st.session_state.get("username") or ""))
    if not current_user:
        return

    _, right_col = st.columns([7, 1.45])
    with right_col:
        full_name = str(get_row_value(current_user, "full_name", "") or st.session_state.get("user_full_name") or "Kullanıcı")
        email = str(get_row_value(current_user, "email", "") or st.session_state.get("username") or "")
        role_display = str(get_row_value(current_user, "role_display", "") or st.session_state.get("user_role_display") or "")
        password_status = "Geçici Şifre" if st.session_state.get("must_change_password") else "Güncel Şifre"
        name_parts = [part for part in full_name.split() if part.strip()]
        initials = "".join(part[:1] for part in name_parts[:2]).upper() or "CK"

        with st.popover("Profil ve Ayarlar", use_container_width=True):
            st.markdown(
                f"""
                <div class="ck-profile-shell">
                    <div class="ck-profile-hero">
                        <div class="ck-profile-avatar">{html.escape(initials)}</div>
                        <div>
                            <div class="ck-profile-kicker">Hesap Merkezi</div>
                            <div class="ck-profile-name">{html.escape(full_name)}</div>
                            <div class="ck-profile-mail">{html.escape(email)}</div>
                        </div>
                    </div>
                    <div class="ck-profile-chip-row">
                        <span class="ck-profile-chip">{html.escape(role_display)}</span>
                        <span class="ck-profile-chip">{html.escape(password_status)}</span>
                        <span class="ck-profile-chip">Kurumsal Erişim</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.session_state.get("must_change_password"):
                st.info("Geçici şifre kullanıyorsun. Güvenlik için aşağıdaki alandan yeni şifre belirle.")

            st.markdown("##### Hesap Özeti")
            st.markdown(f"**Ad Soyad:** {full_name}")
            st.markdown(f"**E-posta:** {email}")
            st.markdown(f"**Yetki:** {role_display}")
            st.markdown(f"**Şifre Durumu:** {password_status}")
            st.divider()
            st.markdown("##### Güvenlik Ayarları")

            with st.form("change_password_form", clear_on_submit=True):
                current_password = st.text_input("Mevcut Şifre", type="password")
                new_password = st.text_input("Yeni Şifre", type="password")
                confirm_password = st.text_input("Yeni Şifre Tekrar", type="password")
                password_submitted = st.form_submit_button("Şifreyi Güncelle", use_container_width=True)

            if password_submitted:
                stored_hash = str(get_row_value(current_user, "password_hash", "") or "")
                if not verify_auth_password(current_password, stored_hash):
                    st.error("Mevcut şifreyi doğru girmelisin.")
                elif len(new_password or "") < 6:
                    st.error("Yeni şifre en az 6 karakter olmalı.")
                elif new_password != confirm_password:
                    st.error("Yeni şifre alanları birbiriyle aynı olmalı.")
                else:
                    conn.execute(
                        """
                        UPDATE auth_users
                        SET password_hash = ?, must_change_password = 0, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            hash_auth_password(new_password),
                            datetime.utcnow().isoformat(timespec="seconds"),
                            int(get_row_value(current_user, "id", 0) or 0),
                        ),
                    )
                    conn.commit()
                    st.session_state.must_change_password = False
                    st.success("Şifren güncellendi.")
                    st.rerun()

            if st.session_state.get("role") == "admin":
                st.divider()
                with st.expander("Veri Yönetimi ve Yedekleme", expanded=False):
                    st.caption("Yedek alma, dışa aktarma ve gerekirse veri aktarma işlemlerini bu alandan yönetebilirsin.")
                    render_backup_tools_content(conn)

            if st.button("Oturumu Kapat", key="profile_logout_btn", use_container_width=True):
                revoke_current_auth_session(conn)
                st.rerun()


def allowed_menu_items(role: str) -> list[str]:
    if role == "admin":
        return [
            "Genel Bakış",
            "Restoran Yönetimi",
            "Personel Yönetimi",
            "Puantaj",
            "Satın Alma",
            "Kesinti Yönetimi",
            "Aylık Hakediş",
            "Raporlar ve Karlılık",
            "Güncellemeler ve Duyurular",
        ]
    if role == "sef":
        return [
            "Personel Yönetimi",
            "Puantaj",
            "Kesinti Yönetimi",
            "Güncellemeler ve Duyurular",
        ]
    return []


def ensure_role_access(menu: str, role: str) -> None:
    if menu not in allowed_menu_items(role):
        st.error("Bu sayfaya erişim yetkiniz yok.")
        st.stop()


def normalize_entry_status(value: str) -> str:
    mapping = {
        "normal": "Normal",
        "joker": "Joker",
        "izin": "İzin",
        "i̇zin": "İzin",
        "gelmedi": "Gelmedi",
        "çıkış": "Çıkış yaptı",
        "cikis": "Çıkış yaptı",
        "çıkış yaptı": "Çıkış yaptı",
        "sef": "Şef",
        "şef": "Şef",
    }
    normalized = (value or "").strip().lower()
    return mapping.get(normalized, value or "Normal")


def parse_whatsapp_bulk(text_value: str) -> list[dict]:
    rows = []
    if not text_value:
        return rows
    for raw in text_value.splitlines():
        line = raw.strip()
        if not line:
            continue
        normalized = line.replace("—", "-").replace("–", "-")
        parts = [p.strip() for p in re.split(r"\s*\|\s*|\s*;\s*|\s+-\s+", normalized) if p.strip()]
        if not parts:
            continue
        name = parts[0]
        hours = 0.0
        packages = 0
        status = "Normal"
        note = ""
        for p in parts[1:]:
            low = p.lower()
            nums = re.findall(r"\d+[\.,]?\d*", low)
            if "saat" in low and nums:
                hours = float(nums[0].replace(",", "."))
            elif "paket" in low and nums:
                packages = int(float(nums[0].replace(",", ".")))
            elif normalize_entry_status(p) in ["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"]:
                status = normalize_entry_status(p)
            elif nums and hours == 0:
                hours = float(nums[0].replace(",", "."))
            elif nums and packages == 0:
                packages = int(float(nums[0].replace(",", ".")))
            else:
                note = p
        rows.append(
            {
                "person_label": name,
                "worked_hours": hours,
                "package_count": packages,
                "entry_status": status or "Normal",
                "notes": note,
            }
        )
    return rows


def is_system_personnel_auto_deduction_key(auto_source_key: Any) -> bool:
    key = str(auto_source_key or "").strip()
    return any(key.startswith(prefix) for prefix in SYSTEM_PERSONNEL_AUTO_DEDUCTION_PREFIXES)


def post_equipment_installments(
    conn: sqlite3.Connection,
    issue_id: int,
    personnel_id: int,
    issue_date: date | str,
    item_name: str,
    total_sale_amount: float,
    installment_count: int,
    sale_type: str = "Satış",
    auto_source_key_prefix: str | None = None,
) -> None:
    installment_count = normalize_equipment_issue_installment_count(sale_type, installment_count)
    if not equipment_issue_generates_installments(sale_type, total_sale_amount, installment_count):
        return
    issue_date_value = parse_date_value(issue_date) or date.today()
    installment_amount = round(total_sale_amount / installment_count, 2)
    dates = [
        normalize_deduction_date((pd.Timestamp(issue_date_value) + pd.DateOffset(months=i)).date()).isoformat()
        for i in range(installment_count)
    ]

    if not auto_source_key_prefix:
        existing = int(first_row_value(conn.execute("SELECT COUNT(*) FROM deductions WHERE equipment_issue_id = ?", (issue_id,)).fetchone(), 0) or 0)
        if existing:
            return
        for i, due_date in enumerate(dates, start=1):
            conn.execute(
                "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes, equipment_issue_id) VALUES (?, ?, ?, ?, ?, ?)",
                (personnel_id, due_date, "Zimmet Taksiti", installment_amount, f"{item_name} {i}/{installment_count}", issue_id),
            )
        conn.commit()
        return

    expected_rows = [
        {
            "deduction_date": due_date,
            "deduction_type": "Zimmet Taksiti",
            "amount": installment_amount,
            "notes": f"{item_name} {i}/{installment_count}",
            "auto_source_key": f"{auto_source_key_prefix}:installment:{i}",
        }
        for i, due_date in enumerate(dates, start=1)
    ]

    existing_rows = fetch_df(
        conn,
        "SELECT id, deduction_date, deduction_type, amount, notes, auto_source_key FROM deductions WHERE equipment_issue_id = ?",
        (issue_id,),
    )
    needs_rebuild = existing_rows.empty or len(existing_rows) != len(expected_rows)
    if not needs_rebuild:
        existing_map = {str(row["auto_source_key"] or ""): row for _, row in existing_rows.iterrows()}
        expected_keys = {row["auto_source_key"] for row in expected_rows}
        if set(existing_map.keys()) != expected_keys:
            needs_rebuild = True
        else:
            for expected in expected_rows:
                current = existing_map.get(expected["auto_source_key"])
                current_amount = float(current["amount"] or 0) if current is not None else 0.0
                if (
                    current is None
                    or str(current["deduction_date"]) != expected["deduction_date"]
                    or str(current["deduction_type"]) != expected["deduction_type"]
                    or abs(current_amount - expected["amount"]) > 0.01
                    or str(current["notes"] or "") != expected["notes"]
                ):
                    needs_rebuild = True
                    break

    if not needs_rebuild:
        return

    conn.execute("DELETE FROM deductions WHERE equipment_issue_id = ?", (issue_id,))
    for expected in expected_rows:
        conn.execute(
            """
            INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes, equipment_issue_id, auto_source_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                personnel_id,
                expected["deduction_date"],
                expected["deduction_type"],
                expected["amount"],
                expected["notes"],
                issue_id,
                expected["auto_source_key"],
            ),
        )
    conn.commit()


def safe_int(v, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default


def safe_float(v, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def iter_month_starts(start_value: date, end_value: date) -> list[date]:
    current = date(start_value.year, start_value.month, 1)
    last = date(end_value.year, end_value.month, 1)
    months = []
    while current <= last:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def add_months(value: date, month_count: int) -> date:
    base_month = date(value.year, value.month, 1)
    month_index = (base_month.month - 1) + int(month_count or 0)
    target_year = base_month.year + (month_index // 12)
    target_month = (month_index % 12) + 1
    return date(target_year, target_month, 1)


def end_of_month(value: date) -> date:
    last_day = calendar.monthrange(value.year, value.month)[1]
    return date(value.year, value.month, last_day)


configure_reporting_rules(
    safe_int_fn=safe_int,
    safe_float_fn=safe_float,
    parse_date_value_fn=parse_date_value,
    end_of_month_fn=end_of_month,
    normalize_cost_model_value_fn=normalize_cost_model_value,
    pricing_rule_cls=PricingRule,
    vat_rate_default=VAT_RATE_DEFAULT,
    courier_hourly_cost=COURIER_HOURLY_COST,
    courier_package_cost_default_low=COURIER_PACKAGE_COST_DEFAULT_LOW,
    courier_package_cost_default_high=COURIER_PACKAGE_COST_DEFAULT_HIGH,
    courier_package_cost_qc=COURIER_PACKAGE_COST_QC,
    package_threshold_default=PACKAGE_THRESHOLD_DEFAULT,
)

def normalize_deduction_date(value: date | str | None) -> date:
    base_value = parse_date_value(value) or date.today()
    return end_of_month(base_value)


def build_monthly_deduction_date(start_value: date, month_start_value: date) -> date:
    return normalize_deduction_date(month_start_value)


def normalize_existing_deduction_dates(conn: CompatConnection) -> None:
    deduction_rows = fetch_df(conn, "SELECT id, deduction_date FROM deductions")
    if deduction_rows.empty:
        return

    changed = False
    for _, row in deduction_rows.iterrows():
        deduction_id = safe_int(row.get("id"))
        current_date = parse_date_value(row.get("deduction_date"))
        if deduction_id <= 0 or current_date is None:
            continue
        normalized_date = normalize_deduction_date(current_date).isoformat()
        if str(row.get("deduction_date") or "") == normalized_date:
            continue
        conn.execute("UPDATE deductions SET deduction_date = ? WHERE id = ?", (normalized_date, deduction_id))
        changed = True

    if changed:
        conn.commit()


def calculate_prorated_monthly_cost(monthly_cost: float, period_start: date, period_end: date) -> float:
    if monthly_cost <= 0 or period_end < period_start:
        return 0.0
    active_days = (period_end - period_start).days + 1
    return round((float(monthly_cost) / 30.0) * float(active_days), 2)


configure_finance_engine(
    safe_int_fn=safe_int,
    safe_float_fn=safe_float,
    is_fixed_cost_model_fn=is_fixed_cost_model,
    calculate_prorated_monthly_cost_fn=calculate_prorated_monthly_cost,
    shared_overhead_roles=SHARED_OVERHEAD_ROLES,
    courier_hourly_cost=COURIER_HOURLY_COST,
)


def upsert_person_role_snapshot(
    conn: CompatConnection,
    personnel_id: int,
    effective_date_value: date | str | None,
    role: str,
    cost_model: str,
    monthly_fixed_cost: float,
    notes: str = "",
) -> None:
    resolved_personnel_id = safe_int(personnel_id)
    if resolved_personnel_id <= 0:
        return
    effective_date = parse_date_value(effective_date_value) or date.today()
    normalized_role = str(role or "Kurye").strip() or "Kurye"
    normalized_cost_model = normalize_cost_model_value(cost_model, normalized_role)
    fixed_cost_value = float(monthly_fixed_cost or 0.0)
    existing = conn.execute(
        """
        SELECT id
        FROM personnel_role_history
        WHERE personnel_id = ? AND effective_date = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (resolved_personnel_id, effective_date.isoformat()),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE personnel_role_history
            SET role = ?, cost_model = ?, monthly_fixed_cost = ?, notes = ?
            WHERE id = ?
            """,
            (
                normalized_role,
                normalized_cost_model,
                fixed_cost_value,
                notes,
                safe_int(get_row_value(existing, "id")),
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO personnel_role_history
            (personnel_id, role, cost_model, monthly_fixed_cost, effective_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_personnel_id,
                normalized_role,
                normalized_cost_model,
                fixed_cost_value,
                effective_date.isoformat(),
                notes,
            ),
        )


def ensure_person_role_history_baseline(
    conn: CompatConnection,
    person_row: Any,
    role_override: str | None = None,
    cost_model_override: str | None = None,
    monthly_fixed_cost_override: float | None = None,
    notes: str = "Sistem: Başlangıç rol kaydı",
) -> None:
    person_id = safe_int(get_row_value(person_row, "id"))
    if person_id <= 0:
        return
    existing_count = int(first_row_value(conn.execute("SELECT COUNT(*) FROM personnel_role_history WHERE personnel_id = ?", (person_id,)).fetchone(), 0) or 0)
    if existing_count > 0:
        return
    start_date_value = parse_date_value(get_row_value(person_row, "start_date")) or date.today()
    baseline_role = str(role_override or get_row_value(person_row, "role", "Kurye") or "Kurye").strip() or "Kurye"
    baseline_cost_model = str(cost_model_override or get_row_value(person_row, "cost_model", "standard_courier") or "standard_courier")
    baseline_fixed_cost = float(
        monthly_fixed_cost_override
        if monthly_fixed_cost_override is not None
        else safe_float(get_row_value(person_row, "monthly_fixed_cost"), 0.0)
    )
    upsert_person_role_snapshot(
        conn,
        person_id,
        start_date_value,
        baseline_role,
        baseline_cost_model,
        baseline_fixed_cost,
        notes=notes,
    )


def sync_person_current_role_snapshot(conn: CompatConnection, person_row: Any) -> None:
    person_id = safe_int(get_row_value(person_row, "id"))
    if person_id <= 0:
        return
    latest = conn.execute(
        """
        SELECT id
        FROM personnel_role_history
        WHERE personnel_id = ?
        ORDER BY effective_date DESC, id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    if latest:
        conn.execute(
            """
            UPDATE personnel_role_history
            SET role = ?, cost_model = ?, monthly_fixed_cost = ?
            WHERE id = ?
            """,
            (
                str(get_row_value(person_row, "role", "Kurye") or "Kurye"),
                normalize_cost_model_value(
                    str(get_row_value(person_row, "cost_model", "standard_courier") or "standard_courier"),
                    str(get_row_value(person_row, "role", "Kurye") or "Kurye"),
                ),
                safe_float(get_row_value(person_row, "monthly_fixed_cost"), 0.0),
                safe_int(get_row_value(latest, "id")),
            ),
        )
        return
    ensure_person_role_history_baseline(conn, person_row)


def record_person_role_transition(
    conn: CompatConnection,
    original_person_row: Any,
    updated_person_row: Any,
    previous_role: str,
    transition_date_value: date | str | None,
    previous_monthly_fixed_cost: float = 0.0,
) -> None:
    person_id = safe_int(get_row_value(updated_person_row, "id"))
    if person_id <= 0:
        return
    transition_date = parse_date_value(transition_date_value)
    if transition_date is None:
        return

    current_role = str(get_row_value(updated_person_row, "role", "Kurye") or "Kurye")
    current_cost_model = str(get_row_value(updated_person_row, "cost_model", "standard_courier") or "standard_courier")
    current_fixed_cost = safe_float(get_row_value(updated_person_row, "monthly_fixed_cost"), 0.0)
    previous_role_name = str(previous_role or get_row_value(original_person_row, "role", "Kurye") or "Kurye").strip() or "Kurye"
    previous_cost_model = normalize_cost_model_value("", previous_role_name)
    baseline_date = parse_date_value(get_row_value(original_person_row, "start_date")) or date.today()

    existing_history = fetch_df(
        conn,
        """
        SELECT id, role, effective_date
        FROM personnel_role_history
        WHERE personnel_id = ?
        ORDER BY effective_date, id
        """,
        (person_id,),
    )
    if existing_history.empty:
        upsert_person_role_snapshot(
            conn,
            person_id,
            baseline_date,
            previous_role_name,
            previous_cost_model,
            previous_monthly_fixed_cost,
            notes="Sistem: Rol geçişi öncesi başlangıç kaydı",
        )
    elif len(existing_history) == 1:
        first_row = existing_history.iloc[0]
        first_effective_date = parse_date_value(first_row["effective_date"])
        if (
            first_effective_date == baseline_date
            and str(first_row["role"] or "") == current_role
            and previous_role_name != current_role
        ):
            conn.execute(
                """
                UPDATE personnel_role_history
                SET role = ?, cost_model = ?, monthly_fixed_cost = ?, notes = ?
                WHERE id = ?
                """,
                (
                    previous_role_name,
                    previous_cost_model,
                    float(previous_monthly_fixed_cost or 0.0),
                    "Sistem: Rol geçişi öncesi başlangıç kaydı",
                    safe_int(first_row["id"]),
                ),
            )

    upsert_person_role_snapshot(
        conn,
        person_id,
        transition_date,
        current_role,
        current_cost_model,
        current_fixed_cost,
        notes="Sistem: Rol geçiş kaydı",
    )


def ensure_all_person_role_histories(conn: CompatConnection) -> None:
    people_df = fetch_df(conn, "SELECT * FROM personnel")
    if people_df.empty:
        return
    changed = False
    for _, row in people_df.iterrows():
        person_row = row.to_dict()
        person_id = safe_int(person_row.get("id"))
        if person_id <= 0:
            continue
        count_row = conn.execute("SELECT COUNT(*) FROM personnel_role_history WHERE personnel_id = ?", (person_id,)).fetchone()
        if int(first_row_value(count_row, 0) or 0) > 0:
            continue
        ensure_person_role_history_baseline(conn, person_row)
        changed = True
    if changed:
        conn.commit()


def upsert_person_vehicle_snapshot(
    conn: CompatConnection,
    personnel_id: int,
    effective_date_value: date | str | None,
    vehicle_type: str,
    motor_rental: str,
    motor_rental_monthly_amount: float = AUTO_MOTOR_RENTAL_DEDUCTION,
    motor_purchase: str = "Hayır",
    motor_purchase_commitment_months: int | None = None,
    motor_purchase_sale_price: float = 0.0,
    motor_purchase_monthly_amount: float = AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
    notes: str = "",
) -> None:
    resolved_personnel_id = safe_int(personnel_id)
    if resolved_personnel_id <= 0:
        return
    effective_date = parse_date_value(effective_date_value) or date.today()
    normalized_vehicle_type = resolve_vehicle_type_value(vehicle_type, motor_rental)
    normalized_motor_rental = resolve_motor_rental_value(normalized_vehicle_type, motor_rental)
    normalized_motor_purchase = "Evet" if str(motor_purchase or "Hayır").strip() == "Evet" else "Hayır"
    normalized_motor_rental = resolve_motor_rental_value(normalized_vehicle_type, motor_rental, normalized_motor_purchase)
    existing = conn.execute(
        """
        SELECT id
        FROM personnel_vehicle_history
        WHERE personnel_id = ? AND effective_date = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (resolved_personnel_id, effective_date.isoformat()),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE personnel_vehicle_history
            SET vehicle_type = ?, motor_rental = ?, motor_rental_monthly_amount = ?, motor_purchase = ?, motor_purchase_commitment_months = ?, motor_purchase_sale_price = ?, motor_purchase_monthly_amount = ?, notes = ?
            WHERE id = ?
            """,
            (
                normalized_vehicle_type,
                normalized_motor_rental,
                safe_float(motor_rental_monthly_amount, AUTO_MOTOR_RENTAL_DEDUCTION),
                normalized_motor_purchase,
                safe_int(motor_purchase_commitment_months, 0) or None,
                safe_float(motor_purchase_sale_price, 0.0) or None,
                safe_float(motor_purchase_monthly_amount, AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
                notes,
                safe_int(get_row_value(existing, "id")),
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO personnel_vehicle_history
            (personnel_id, vehicle_type, motor_rental, motor_rental_monthly_amount, motor_purchase, motor_purchase_commitment_months, motor_purchase_sale_price, motor_purchase_monthly_amount, effective_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_personnel_id,
                normalized_vehicle_type,
                normalized_motor_rental,
                safe_float(motor_rental_monthly_amount, AUTO_MOTOR_RENTAL_DEDUCTION),
                normalized_motor_purchase,
                safe_int(motor_purchase_commitment_months, 0) or None,
                safe_float(motor_purchase_sale_price, 0.0) or None,
                safe_float(motor_purchase_monthly_amount, AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
                effective_date.isoformat(),
                notes,
            ),
        )


def ensure_person_vehicle_history_baseline(
    conn: CompatConnection,
    person_row: Any,
    vehicle_type_override: str | None = None,
    motor_rental_override: str | None = None,
    motor_rental_monthly_amount_override: float | None = None,
    motor_purchase_override: str | None = None,
    motor_purchase_commitment_months_override: int | None = None,
    motor_purchase_sale_price_override: float | None = None,
    motor_purchase_monthly_amount_override: float | None = None,
    notes: str = "Sistem: Başlangıç araç kaydı",
) -> None:
    person_id = safe_int(get_row_value(person_row, "id"))
    if person_id <= 0:
        return
    existing_count = int(first_row_value(conn.execute("SELECT COUNT(*) FROM personnel_vehicle_history WHERE personnel_id = ?", (person_id,)).fetchone(), 0) or 0)
    if existing_count > 0:
        return
    start_date_value = parse_date_value(get_row_value(person_row, "start_date")) or date.today()
    baseline_vehicle_type = resolve_vehicle_type_value(
        str(vehicle_type_override or get_row_value(person_row, "vehicle_type", "") or ""),
        str(motor_rental_override or get_row_value(person_row, "motor_rental", "Hayır") or "Hayır"),
    )
    baseline_motor_rental = resolve_motor_rental_value(
        baseline_vehicle_type,
        str(motor_rental_override or get_row_value(person_row, "motor_rental", "Hayır") or "Hayır"),
        str(motor_purchase_override or get_row_value(person_row, "motor_purchase", "Hayır") or "Hayır"),
    )
    upsert_person_vehicle_snapshot(
        conn,
        person_id,
        start_date_value,
        baseline_vehicle_type,
        baseline_motor_rental,
        motor_rental_monthly_amount=safe_float(
            motor_rental_monthly_amount_override if motor_rental_monthly_amount_override is not None else get_row_value(person_row, "motor_rental_monthly_amount", AUTO_MOTOR_RENTAL_DEDUCTION),
            AUTO_MOTOR_RENTAL_DEDUCTION,
        ),
        motor_purchase=str(motor_purchase_override or get_row_value(person_row, "motor_purchase", "Hayır") or "Hayır"),
        motor_purchase_commitment_months=safe_int(
            motor_purchase_commitment_months_override if motor_purchase_commitment_months_override is not None else get_row_value(person_row, "motor_purchase_commitment_months", 0),
            0,
        ),
        motor_purchase_sale_price=safe_float(
            motor_purchase_sale_price_override if motor_purchase_sale_price_override is not None else get_row_value(person_row, "motor_purchase_sale_price", 0.0),
            0.0,
        ),
        motor_purchase_monthly_amount=safe_float(
            motor_purchase_monthly_amount_override if motor_purchase_monthly_amount_override is not None else get_row_value(person_row, "motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
            AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
        ),
        notes=notes,
    )


def sync_person_current_vehicle_snapshot(conn: CompatConnection, person_row: Any) -> None:
    person_id = safe_int(get_row_value(person_row, "id"))
    if person_id <= 0:
        return
    latest = conn.execute(
        """
        SELECT id
        FROM personnel_vehicle_history
        WHERE personnel_id = ?
        ORDER BY effective_date DESC, id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    normalized_vehicle_type = resolve_vehicle_type_value(
        str(get_row_value(person_row, "vehicle_type", "") or ""),
        str(get_row_value(person_row, "motor_rental", "Hayır") or "Hayır"),
    )
    normalized_motor_rental = resolve_motor_rental_value(
        normalized_vehicle_type,
        str(get_row_value(person_row, "motor_rental", "Hayır") or "Hayır"),
        str(get_row_value(person_row, "motor_purchase", "Hayır") or "Hayır"),
    )
    motor_rental_monthly_amount = safe_float(get_row_value(person_row, "motor_rental_monthly_amount", AUTO_MOTOR_RENTAL_DEDUCTION), AUTO_MOTOR_RENTAL_DEDUCTION)
    motor_purchase = str(get_row_value(person_row, "motor_purchase", "Hayır") or "Hayır")
    motor_purchase_commitment_months = safe_int(get_row_value(person_row, "motor_purchase_commitment_months", 0), 0)
    motor_purchase_sale_price = safe_float(get_row_value(person_row, "motor_purchase_sale_price", 0.0), 0.0)
    motor_purchase_monthly_amount = safe_float(get_row_value(person_row, "motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION), AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION)
    if latest:
        conn.execute(
            """
            UPDATE personnel_vehicle_history
            SET vehicle_type = ?, motor_rental = ?, motor_rental_monthly_amount = ?, motor_purchase = ?, motor_purchase_commitment_months = ?, motor_purchase_sale_price = ?, motor_purchase_monthly_amount = ?
            WHERE id = ?
            """,
            (
                normalized_vehicle_type,
                normalized_motor_rental,
                motor_rental_monthly_amount,
                motor_purchase,
                motor_purchase_commitment_months or None,
                motor_purchase_sale_price or None,
                motor_purchase_monthly_amount,
                safe_int(get_row_value(latest, "id")),
            ),
        )
        return
    ensure_person_vehicle_history_baseline(conn, person_row)


def record_person_vehicle_transition(
    conn: CompatConnection,
    original_person_row: Any,
    updated_person_row: Any,
    previous_vehicle_type: str,
    transition_date_value: date | str | None,
    previous_motor_rental: str = "Hayır",
    previous_motor_rental_monthly_amount: float | None = None,
    previous_motor_purchase: str | None = None,
    previous_motor_purchase_commitment_months: int | None = None,
    previous_motor_purchase_sale_price: float | None = None,
    previous_motor_purchase_monthly_amount: float | None = None,
) -> None:
    person_id = safe_int(get_row_value(updated_person_row, "id"))
    if person_id <= 0:
        return
    transition_date = parse_date_value(transition_date_value)
    if transition_date is None:
        return

    current_vehicle_type = resolve_vehicle_type_value(
        str(get_row_value(updated_person_row, "vehicle_type", "") or ""),
        str(get_row_value(updated_person_row, "motor_rental", "Hayır") or "Hayır"),
    )
    current_motor_purchase = str(get_row_value(updated_person_row, "motor_purchase", "Hayır") or "Hayır")
    current_motor_rental = resolve_motor_rental_value(
        current_vehicle_type,
        str(get_row_value(updated_person_row, "motor_rental", "Hayır") or "Hayır"),
        current_motor_purchase,
    )
    current_motor_rental_monthly_amount = safe_float(get_row_value(updated_person_row, "motor_rental_monthly_amount", AUTO_MOTOR_RENTAL_DEDUCTION), AUTO_MOTOR_RENTAL_DEDUCTION)
    current_motor_purchase_commitment_months = safe_int(get_row_value(updated_person_row, "motor_purchase_commitment_months", 0), 0)
    current_motor_purchase_sale_price = safe_float(get_row_value(updated_person_row, "motor_purchase_sale_price", 0.0), 0.0)
    current_motor_purchase_monthly_amount = safe_float(get_row_value(updated_person_row, "motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION), AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION)
    previous_vehicle_type_value = resolve_vehicle_type_value(previous_vehicle_type, previous_motor_rental)
    previous_motor_rental_value = resolve_motor_rental_value(
        previous_vehicle_type_value,
        previous_motor_rental,
        str(previous_motor_purchase or get_row_value(original_person_row, "motor_purchase", "Hayır") or "Hayır"),
    )
    baseline_date = parse_date_value(get_row_value(original_person_row, "start_date")) or date.today()

    existing_history = fetch_df(
        conn,
        """
        SELECT id, vehicle_type, motor_purchase, effective_date
        FROM personnel_vehicle_history
        WHERE personnel_id = ?
        ORDER BY effective_date, id
        """,
        (person_id,),
    )
    if existing_history.empty:
        upsert_person_vehicle_snapshot(
            conn,
            person_id,
            baseline_date,
            previous_vehicle_type_value,
            previous_motor_rental_value,
            motor_rental_monthly_amount=safe_float(previous_motor_rental_monthly_amount, AUTO_MOTOR_RENTAL_DEDUCTION),
            motor_purchase=str(previous_motor_purchase or get_row_value(original_person_row, "motor_purchase", "Hayır") or "Hayır"),
            motor_purchase_commitment_months=safe_int(previous_motor_purchase_commitment_months if previous_motor_purchase_commitment_months is not None else get_row_value(original_person_row, "motor_purchase_commitment_months", 0), 0),
            motor_purchase_sale_price=safe_float(previous_motor_purchase_sale_price if previous_motor_purchase_sale_price is not None else get_row_value(original_person_row, "motor_purchase_sale_price", 0.0), 0.0),
            motor_purchase_monthly_amount=safe_float(previous_motor_purchase_monthly_amount if previous_motor_purchase_monthly_amount is not None else get_row_value(original_person_row, "motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION), AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
            notes="Sistem: Araç değişimi öncesi başlangıç kaydı",
        )
    elif len(existing_history) == 1:
        first_row = existing_history.iloc[0]
        first_effective_date = parse_date_value(first_row["effective_date"])
        if (
            first_effective_date == baseline_date
            and str(first_row["vehicle_type"] or "") == current_vehicle_type
            and str(first_row.get("motor_purchase") or "Hayır") == current_motor_purchase
            and (
                previous_vehicle_type_value != current_vehicle_type
                or str(previous_motor_purchase or get_row_value(original_person_row, "motor_purchase", "Hayır") or "Hayır") != current_motor_purchase
            )
        ):
            conn.execute(
                """
                UPDATE personnel_vehicle_history
                SET vehicle_type = ?, motor_rental = ?, motor_rental_monthly_amount = ?, motor_purchase = ?, motor_purchase_commitment_months = ?, motor_purchase_sale_price = ?, motor_purchase_monthly_amount = ?, notes = ?
                WHERE id = ?
                """,
                (
                    previous_vehicle_type_value,
                    previous_motor_rental_value,
                    safe_float(previous_motor_rental_monthly_amount, AUTO_MOTOR_RENTAL_DEDUCTION),
                    str(previous_motor_purchase or get_row_value(original_person_row, "motor_purchase", "Hayır") or "Hayır"),
                    safe_int(previous_motor_purchase_commitment_months if previous_motor_purchase_commitment_months is not None else get_row_value(original_person_row, "motor_purchase_commitment_months", 0), 0) or None,
                    safe_float(previous_motor_purchase_sale_price if previous_motor_purchase_sale_price is not None else get_row_value(original_person_row, "motor_purchase_sale_price", 0.0), 0.0) or None,
                    safe_float(previous_motor_purchase_monthly_amount if previous_motor_purchase_monthly_amount is not None else get_row_value(original_person_row, "motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION), AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
                    "Sistem: Araç değişimi öncesi başlangıç kaydı",
                    safe_int(first_row["id"]),
                ),
            )

    upsert_person_vehicle_snapshot(
        conn,
        person_id,
        transition_date,
        current_vehicle_type,
        current_motor_rental,
        motor_rental_monthly_amount=current_motor_rental_monthly_amount,
        motor_purchase=current_motor_purchase,
        motor_purchase_commitment_months=current_motor_purchase_commitment_months,
        motor_purchase_sale_price=current_motor_purchase_sale_price,
        motor_purchase_monthly_amount=current_motor_purchase_monthly_amount,
        notes="Sistem: Araç tipi geçiş kaydı",
    )


def ensure_all_person_vehicle_histories(conn: CompatConnection) -> None:
    people_df = fetch_df(conn, "SELECT * FROM personnel")
    if people_df.empty:
        return
    changed = False
    for _, row in people_df.iterrows():
        person_row = row.to_dict()
        person_id = safe_int(person_row.get("id"))
        if person_id <= 0:
            continue
        count_row = conn.execute("SELECT COUNT(*) FROM personnel_vehicle_history WHERE personnel_id = ?", (person_id,)).fetchone()
        if int(first_row_value(count_row, 0) or 0) > 0:
            continue
        ensure_person_vehicle_history_baseline(conn, person_row)
        changed = True
    if changed:
        conn.commit()


def build_person_vehicle_segments(
    person_row: Any,
    vehicle_history_df: pd.DataFrame,
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    person_id = safe_int(get_row_value(person_row, "id"))
    if person_id <= 0 or period_end < period_start:
        return []

    if vehicle_history_df is None or vehicle_history_df.empty or "personnel_id" not in vehicle_history_df.columns:
        history_rows = pd.DataFrame()
    else:
        history_rows = vehicle_history_df[vehicle_history_df["personnel_id"] == person_id].copy()

    snapshots: list[dict[str, Any]] = []
    if not history_rows.empty:
        history_rows["effective_date_value"] = history_rows["effective_date"].apply(parse_date_value)
        history_rows = history_rows[history_rows["effective_date_value"].notna()].sort_values(["effective_date_value"])
        for _, row in history_rows.iterrows():
            effective_date_value = parse_date_value(row.get("effective_date_value"))
            if effective_date_value is None or effective_date_value > period_end:
                continue
            normalized_vehicle_type = resolve_vehicle_type_value(
                str(row.get("vehicle_type", "") or ""),
                str(row.get("motor_rental", "Hayır") or "Hayır"),
            )
            snapshots.append(
                {
                    "effective_date": effective_date_value,
                    "vehicle_type": normalized_vehicle_type,
                    "motor_rental": resolve_motor_rental_value(
                        normalized_vehicle_type,
                        str(row.get("motor_rental", "Hayır") or "Hayır"),
                        str(row.get("motor_purchase", "Hayır") or "Hayır"),
                    ),
                    "motor_rental_monthly_amount": safe_float(row.get("motor_rental_monthly_amount", AUTO_MOTOR_RENTAL_DEDUCTION), AUTO_MOTOR_RENTAL_DEDUCTION),
                    "motor_purchase": str(row.get("motor_purchase", "Hayır") or "Hayır"),
                    "motor_purchase_commitment_months": safe_int(row.get("motor_purchase_commitment_months", 0), 0),
                    "motor_purchase_sale_price": safe_float(row.get("motor_purchase_sale_price", 0.0), 0.0),
                    "motor_purchase_monthly_amount": safe_float(row.get("motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION), AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
                }
            )

    if not snapshots:
        baseline_vehicle_type = resolve_vehicle_type_value(
            str(get_row_value(person_row, "vehicle_type", "") or ""),
            str(get_row_value(person_row, "motor_rental", "Hayır") or "Hayır"),
        )
        snapshots.append(
            {
                "effective_date": parse_date_value(get_row_value(person_row, "start_date")) or period_start,
                "vehicle_type": baseline_vehicle_type,
                "motor_rental": resolve_motor_rental_value(
                    baseline_vehicle_type,
                    str(get_row_value(person_row, "motor_rental", "Hayır") or "Hayır"),
                    str(get_row_value(person_row, "motor_purchase", "Hayır") or "Hayır"),
                ),
                "motor_rental_monthly_amount": safe_float(get_row_value(person_row, "motor_rental_monthly_amount", AUTO_MOTOR_RENTAL_DEDUCTION), AUTO_MOTOR_RENTAL_DEDUCTION),
                "motor_purchase": str(get_row_value(person_row, "motor_purchase", "Hayır") or "Hayır"),
                "motor_purchase_commitment_months": safe_int(get_row_value(person_row, "motor_purchase_commitment_months", 0), 0),
                "motor_purchase_sale_price": safe_float(get_row_value(person_row, "motor_purchase_sale_price", 0.0), 0.0),
                "motor_purchase_monthly_amount": safe_float(get_row_value(person_row, "motor_purchase_monthly_amount", AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION), AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION),
            }
        )

    segments: list[dict[str, Any]] = []
    for index, snapshot in enumerate(snapshots):
        next_snapshot = snapshots[index + 1] if index + 1 < len(snapshots) else None
        segment_start = max(snapshot["effective_date"], period_start)
        segment_end = period_end if next_snapshot is None else min(period_end, next_snapshot["effective_date"] - timedelta(days=1))
        if segment_end < segment_start:
            continue
        segments.append(
            {
                "start_date": segment_start,
                "end_date": segment_end,
                "vehicle_type": snapshot["vehicle_type"],
                "motor_rental": snapshot["motor_rental"],
                "motor_rental_monthly_amount": snapshot["motor_rental_monthly_amount"],
                "motor_purchase": snapshot["motor_purchase"],
                "motor_purchase_commitment_months": snapshot["motor_purchase_commitment_months"],
                "motor_purchase_sale_price": snapshot["motor_purchase_sale_price"],
                "motor_purchase_monthly_amount": snapshot["motor_purchase_monthly_amount"],
            }
        )
    return segments


def normalize_equipment_issue_costs_and_vat(conn: CompatConnection) -> None:
    issue_rows = fetch_df(conn, "SELECT id, issue_date, item_name, unit_cost, vat_rate FROM courier_equipment_issues")
    if issue_rows.empty:
        return

    changed = False
    for _, row in issue_rows.iterrows():
        issue_id = safe_int(row.get("id"))
        item_name = str(row.get("item_name") or "").strip()
        if issue_id <= 0 or not item_name:
            continue

        target_cost = get_default_equipment_unit_cost(conn, item_name)
        target_vat_rate = get_equipment_vat_rate(item_name, row.get("issue_date"))
        current_cost = safe_float(row.get("unit_cost"), 0.0)
        current_vat_rate = safe_float(row.get("vat_rate"), VAT_RATE_DEFAULT)

        if (target_cost > 0 and abs(current_cost - target_cost) > 0.01) or abs(current_vat_rate - target_vat_rate) > 0.01:
            conn.execute(
                "UPDATE courier_equipment_issues SET unit_cost = ?, vat_rate = ? WHERE id = ?",
                (
                    target_cost if target_cost > 0 else current_cost,
                    target_vat_rate,
                    issue_id,
                ),
            )
            changed = True

    if changed:
        conn.commit()


def delete_equipment_issue_records(conn: CompatConnection, issue_ids: Iterable[int]) -> int:
    resolved_issue_ids = []
    seen = set()
    for issue_id in issue_ids:
        resolved_id = safe_int(issue_id, 0)
        if resolved_id <= 0 or resolved_id in seen:
            continue
        seen.add(resolved_id)
        resolved_issue_ids.append(resolved_id)

    if not resolved_issue_ids:
        return 0

    placeholders = ", ".join(["?"] * len(resolved_issue_ids))
    conn.execute(f"DELETE FROM deductions WHERE equipment_issue_id IN ({placeholders})", tuple(resolved_issue_ids))
    conn.execute(f"DELETE FROM courier_equipment_issues WHERE id IN ({placeholders})", tuple(resolved_issue_ids))
    conn.commit()
    return len(resolved_issue_ids)


def bulk_update_equipment_issue_records(
    conn: CompatConnection,
    issue_ids: Iterable[int],
    *,
    issue_date_value: date | None = None,
    unit_cost_value: float | None = None,
    unit_sale_price_value: float | None = None,
    vat_rate_value: float | None = None,
    installment_count_value: int | None = None,
    sale_type_value: str | None = None,
    note_append_text: str = "",
) -> int:
    resolved_issue_ids = []
    seen = set()
    for issue_id in issue_ids:
        resolved_id = safe_int(issue_id, 0)
        if resolved_id <= 0 or resolved_id in seen:
            continue
        seen.add(resolved_id)
        resolved_issue_ids.append(resolved_id)

    if not resolved_issue_ids:
        return 0

    placeholders = ", ".join(["?"] * len(resolved_issue_ids))
    issues_df = fetch_df(
        conn,
        f"""
        SELECT id, personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, vat_rate, installment_count, sale_type, notes
        FROM courier_equipment_issues
        WHERE id IN ({placeholders})
        ORDER BY issue_date DESC, id DESC
        """,
        tuple(resolved_issue_ids),
    )
    if issues_df.empty:
        return 0

    updated_count = 0
    normalized_note_text = str(note_append_text or "").strip()
    for _, row in issues_df.iterrows():
        issue_id = safe_int(row["id"], 0)
        personnel_id = safe_int(row["personnel_id"], 0)
        if issue_id <= 0 or personnel_id <= 0:
            continue

        resolved_issue_date = issue_date_value or parse_date_value(row["issue_date"]) or date.today()
        resolved_unit_cost = unit_cost_value if unit_cost_value is not None else safe_float(row["unit_cost"], 0.0)
        resolved_unit_sale_price = unit_sale_price_value if unit_sale_price_value is not None else safe_float(row["unit_sale_price"], 0.0)
        resolved_vat_rate = vat_rate_value if vat_rate_value is not None else safe_float(row["vat_rate"], VAT_RATE_DEFAULT)
        resolved_sale_type = sale_type_value if sale_type_value is not None else str(row["sale_type"] or "Satış")
        resolved_installment_count = normalize_equipment_issue_installment_count(
            resolved_sale_type,
            installment_count_value if installment_count_value is not None else safe_int(row["installment_count"], 1),
        )
        existing_notes = str(row["notes"] or "").strip()
        resolved_notes = existing_notes
        if normalized_note_text:
            resolved_notes = " | ".join([part for part in [existing_notes, normalized_note_text] if part])

        conn.execute(
            """
            UPDATE courier_equipment_issues
            SET issue_date = ?, unit_cost = ?, unit_sale_price = ?, vat_rate = ?, installment_count = ?, sale_type = ?, notes = ?
            WHERE id = ?
            """,
            (
                resolved_issue_date.isoformat(),
                resolved_unit_cost,
                resolved_unit_sale_price,
                resolved_vat_rate,
                resolved_installment_count,
                resolved_sale_type,
                resolved_notes,
                issue_id,
            ),
        )
        conn.execute("DELETE FROM deductions WHERE equipment_issue_id = ?", (issue_id,))
        total_sale_amount = safe_float(row["quantity"], 0.0) * resolved_unit_sale_price
        post_equipment_installments(
            conn,
            issue_id,
            personnel_id,
            resolved_issue_date,
            str(row["item_name"] or ""),
            total_sale_amount,
            resolved_installment_count,
            resolved_sale_type,
        )
        updated_count += 1

    conn.commit()
    return updated_count


def update_equipment_issue_record(
    conn: CompatConnection,
    issue_id: int,
    *,
    issue_date_value: date,
    item_name: str,
    quantity: int,
    unit_cost: float,
    unit_sale_price: float,
    vat_rate: float,
    installment_count: int,
    sale_type: str,
    notes: str,
) -> bool:
    resolved_issue_id = safe_int(issue_id, 0)
    if resolved_issue_id <= 0:
        return False

    existing_row = conn.execute(
        """
        SELECT id, personnel_id
        FROM courier_equipment_issues
        WHERE id = ?
        LIMIT 1
        """,
        (resolved_issue_id,),
    ).fetchone()
    if not existing_row:
        return False

    personnel_id = safe_int(get_row_value(existing_row, "personnel_id"), 0)
    if personnel_id <= 0:
        return False

    resolved_sale_type = str(sale_type or "Satış").strip() or "Satış"
    resolved_installment_count = normalize_equipment_issue_installment_count(resolved_sale_type, installment_count)

    conn.execute(
        """
        UPDATE courier_equipment_issues
        SET issue_date = ?, item_name = ?, quantity = ?, unit_cost = ?, unit_sale_price = ?, vat_rate = ?, installment_count = ?, sale_type = ?, notes = ?
        WHERE id = ?
        """,
        (
            issue_date_value.isoformat(),
            str(item_name or "").strip(),
            max(safe_int(quantity, 1), 1),
            safe_float(unit_cost, 0.0),
            safe_float(unit_sale_price, 0.0),
            safe_float(vat_rate, VAT_RATE_DEFAULT),
            resolved_installment_count,
            resolved_sale_type,
            str(notes or "").strip(),
            resolved_issue_id,
        ),
    )
    conn.execute("DELETE FROM deductions WHERE equipment_issue_id = ?", (resolved_issue_id,))
    total_sale_amount = max(safe_int(quantity, 1), 1) * safe_float(unit_sale_price, 0.0)
    post_equipment_installments(
        conn,
        resolved_issue_id,
        personnel_id,
        issue_date_value,
        str(item_name or "").strip(),
        total_sale_amount,
        resolved_installment_count,
        resolved_sale_type,
    )
    conn.commit()
    return True


def count_person_worked_days_in_range(
    conn: CompatConnection,
    personnel_id: int,
    period_start: date,
    period_end: date,
) -> int:
    if personnel_id <= 0 or period_end < period_start:
        return 0

    row = conn.execute(
        """
        SELECT COUNT(DISTINCT entry_date)
        FROM daily_entries
        WHERE actual_personnel_id = ?
          AND entry_date BETWEEN ? AND ?
          AND (
              status NOT IN ('İzin', 'Gelmedi')
              OR worked_hours > 0
              OR package_count > 0
          )
        """,
        (personnel_id, period_start.isoformat(), period_end.isoformat()),
    ).fetchone()
    return max(int(first_row_value(row, 0) or 0), 0)


def calculate_prorated_monthly_deduction_amount(monthly_amount: float, billable_days: int) -> float:
    billable_days = min(max(int(billable_days or 0), 0), MOTOR_RENTAL_STANDARD_MONTH_DAYS)
    if monthly_amount <= 0 or billable_days <= 0:
        return 0.0
    return round((float(monthly_amount) / MOTOR_RENTAL_STANDARD_MONTH_DAYS) * billable_days, 2)


def calculate_prorated_motor_rental_amount(billable_days: int, monthly_amount: float = AUTO_MOTOR_RENTAL_DEDUCTION) -> float:
    return calculate_prorated_monthly_deduction_amount(monthly_amount, billable_days)


def sync_person_auto_deductions(
    conn: CompatConnection,
    person_row: Any,
    as_of: date | None = None,
    full_history: bool = True,
) -> None:
    person_id = safe_int(get_row_value(person_row, "id"))
    if person_id <= 0:
        return

    conn.execute("DELETE FROM deductions WHERE personnel_id = ? AND auto_source_key LIKE ?", (person_id, "auto:motor_rental:%"))
    conn.execute("DELETE FROM deductions WHERE personnel_id = ? AND auto_source_key LIKE ?", (person_id, "auto:motor_purchase:%"))
    conn.commit()


def sync_person_auto_onboarding(conn: CompatConnection, person_row: Any, create_missing: bool = True) -> None:
    return


def cleanup_auto_onboarding_records(conn: CompatConnection) -> None:
    issue_rows = fetch_df(
        conn,
        """
        SELECT id
        FROM courier_equipment_issues
        WHERE auto_source_key LIKE ?
        """,
        ("auto:onboarding:%",),
    )
    if issue_rows.empty:
        return

    for issue_id in issue_rows["id"].tolist():
        resolved_issue_id = safe_int(issue_id)
        if resolved_issue_id <= 0:
            continue
        conn.execute("DELETE FROM deductions WHERE equipment_issue_id = ?", (resolved_issue_id,))
    conn.execute("DELETE FROM deductions WHERE auto_source_key LIKE ?", ("auto:onboarding:%",))
    conn.execute("DELETE FROM courier_equipment_issues WHERE auto_source_key LIKE ?", ("auto:onboarding:%",))
    conn.commit()


def cleanup_auto_personnel_deduction_records(conn: CompatConnection) -> None:
    changed = False
    for prefix in SYSTEM_PERSONNEL_AUTO_DEDUCTION_PREFIXES:
        row = conn.execute("SELECT COUNT(*) FROM deductions WHERE auto_source_key LIKE ?", (f"{prefix}%",)).fetchone()
        if safe_int(first_row_value(row, 0), 0) <= 0:
            continue
        conn.execute("DELETE FROM deductions WHERE auto_source_key LIKE ?", (f"{prefix}%",))
        changed = True
    if changed:
        conn.commit()


def sync_person_business_rules(
    conn: CompatConnection,
    person_row: Any,
    create_onboarding: bool = True,
    full_history: bool = True,
) -> None:
    ensure_person_role_history_baseline(conn, person_row)
    ensure_person_vehicle_history_baseline(conn, person_row)
    sync_person_auto_deductions(conn, person_row, full_history=full_history)
    sync_person_auto_onboarding(conn, person_row, create_missing=create_onboarding)


def sync_personnel_business_rules_for_ids(
    conn: CompatConnection,
    personnel_ids: Iterable[int],
    create_onboarding: bool = False,
    full_history: bool = True,
) -> None:
    unique_ids = []
    seen = set()
    for personnel_id in personnel_ids:
        resolved_id = safe_int(personnel_id)
        if resolved_id <= 0 or resolved_id in seen:
            continue
        seen.add(resolved_id)
        unique_ids.append(resolved_id)

    for personnel_id in unique_ids:
        person_row = conn.execute("SELECT * FROM personnel WHERE id = ?", (personnel_id,)).fetchone()
        if person_row:
            sync_person_business_rules(conn, person_row, create_onboarding=create_onboarding, full_history=full_history)


def sync_all_personnel_business_rules(conn: CompatConnection, full_history: bool = False) -> None:
    people_df = fetch_df(conn, "SELECT * FROM personnel")
    if people_df.empty:
        return
    for _, row in people_df.iterrows():
        resolved_vehicle_type = resolve_vehicle_type_value(
            str(row.get("vehicle_type", "") or ""),
            str(row.get("motor_rental", "Hayır") or "Hayır"),
        )
        effective_motor_rental = resolve_motor_rental_value(
            resolved_vehicle_type,
            str(row.get("motor_rental", "Hayır") or "Hayır"),
            str(row.get("motor_purchase", "Hayır") or "Hayır"),
        )
        normalized_cost_model = normalize_cost_model_value(str(row.get("cost_model", "standard_courier") or "standard_courier"), str(row.get("role", "Kurye") or "Kurye"))
        if (
            str(row.get("vehicle_type", "") or "") != resolved_vehicle_type
            or
            str(row.get("motor_rental", "Hayır") or "Hayır") != effective_motor_rental
            or str(row.get("cost_model", "standard_courier") or "standard_courier") != normalized_cost_model
        ):
            conn.execute(
                """
                UPDATE personnel
                SET vehicle_type = ?, motor_rental = ?, cost_model = ?
                WHERE id = ?
                """,
                (
                    resolved_vehicle_type,
                    effective_motor_rental,
                    normalized_cost_model,
                    int(row["id"]),
                ),
            )
            conn.commit()
            row["vehicle_type"] = resolved_vehicle_type
            row["motor_rental"] = effective_motor_rental
            row["cost_model"] = normalized_cost_model
        sync_person_current_vehicle_snapshot(conn, row)
        sync_person_auto_deductions(conn, row, full_history=full_history)
        sync_person_auto_onboarding(conn, row, create_missing=False)


configure_auth_engine(
    get_row_value_fn=get_row_value,
    safe_int_fn=safe_int,
    default_auth_users=DEFAULT_AUTH_USERS,
    default_auth_password=DEFAULT_AUTH_PASSWORD,
    legacy_auth_identities=LEGACY_AUTH_IDENTITIES,
    password_hash_iterations=PASSWORD_HASH_ITERATIONS,
    login_logo_candidates=LOGIN_LOGO_CANDIDATES,
    auth_query_key=AUTH_QUERY_KEY,
    auth_session_days=AUTH_SESSION_DAYS,
)


configure_bootstrap_engine(
    first_row_value_fn=first_row_value,
    legacy_db_paths=LEGACY_DB_PATHS,
    db_path=DB_PATH,
    table_export_order=TABLE_EXPORT_ORDER,
    fixed_cost_model_by_role=FIXED_COST_MODEL_BY_ROLE,
    auto_motor_rental_deduction=AUTO_MOTOR_RENTAL_DEDUCTION,
    auto_motor_purchase_monthly_deduction=AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
    auto_motor_purchase_installment_count=AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT,
    runtime_bootstrap_version=RUNTIME_BOOTSTRAP_VERSION,
    normalize_existing_deduction_dates_fn=normalize_existing_deduction_dates,
    normalize_equipment_issue_costs_and_vat_fn=normalize_equipment_issue_costs_and_vat,
    cleanup_auto_onboarding_records_fn=cleanup_auto_onboarding_records,
    cleanup_auto_personnel_deduction_records_fn=cleanup_auto_personnel_deduction_records,
    ensure_all_person_role_histories_fn=ensure_all_person_role_histories,
    ensure_all_person_vehicle_histories_fn=ensure_all_person_vehicle_histories,
    sync_all_personnel_business_rules_fn=sync_all_personnel_business_rules,
    sync_default_auth_users_fn=sync_default_auth_users,
    cleanup_auth_sessions_fn=cleanup_auth_sessions,
)


def get_personnel_dependency_counts(conn: CompatConnection, personnel_id: int) -> dict[str, int]:
    return {
        "puantaj": int(
            first_row_value(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM daily_entries
                    WHERE planned_personnel_id = ? OR actual_personnel_id = ?
                    """,
                    (personnel_id, personnel_id),
                ).fetchone(),
                0,
            )
            or 0
        ),
        "kesinti": int(first_row_value(conn.execute("SELECT COUNT(*) FROM deductions WHERE personnel_id = ?", (personnel_id,)).fetchone(), 0) or 0),
        "rol_gecmisi": int(first_row_value(conn.execute("SELECT COUNT(*) FROM personnel_role_history WHERE personnel_id = ?", (personnel_id,)).fetchone(), 0) or 0),
        "plaka": int(first_row_value(conn.execute("SELECT COUNT(*) FROM plate_history WHERE personnel_id = ?", (personnel_id,)).fetchone(), 0) or 0),
        "zimmet": int(
            first_row_value(
                conn.execute("SELECT COUNT(*) FROM courier_equipment_issues WHERE personnel_id = ?", (personnel_id,)).fetchone(),
                0,
            )
            or 0
        ),
        "box_iade": int(first_row_value(conn.execute("SELECT COUNT(*) FROM box_returns WHERE personnel_id = ?", (personnel_id,)).fetchone(), 0) or 0),
    }


def delete_personnel_and_dependencies(conn: CompatConnection, personnel_id: int) -> None:
    equipment_df = fetch_df(conn, "SELECT id FROM courier_equipment_issues WHERE personnel_id = ?", (personnel_id,))
    equipment_ids = [safe_int(value) for value in equipment_df["id"].tolist()] if not equipment_df.empty and "id" in equipment_df.columns else []

    try:
        if equipment_ids:
            placeholders = ", ".join(["?"] * len(equipment_ids))
            conn.execute(f"DELETE FROM deductions WHERE equipment_issue_id IN ({placeholders})", tuple(equipment_ids))
        conn.execute("DELETE FROM deductions WHERE personnel_id = ?", (personnel_id,))
        conn.execute("DELETE FROM box_returns WHERE personnel_id = ?", (personnel_id,))
        conn.execute("DELETE FROM personnel_role_history WHERE personnel_id = ?", (personnel_id,))
        conn.execute("DELETE FROM plate_history WHERE personnel_id = ?", (personnel_id,))
        conn.execute("DELETE FROM daily_entries WHERE planned_personnel_id = ? OR actual_personnel_id = ?", (personnel_id, personnel_id))
        conn.execute("DELETE FROM courier_equipment_issues WHERE personnel_id = ?", (personnel_id,))
        conn.execute("DELETE FROM personnel WHERE id = ?", (personnel_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def format_restaurants_table(df: pd.DataFrame) -> pd.DataFrame:
    visible_df = df.drop(columns=["billing_group"], errors="ignore")
    return format_display_df(
        visible_df,
        currency_cols=["hourly_rate", "package_rate", "package_rate_low", "package_rate_high", "fixed_monthly_fee"],
        percent_cols=["vat_rate"],
        number_cols=["package_threshold", "target_headcount", "extra_headcount_request", "reduce_headcount_request"],
        rename_map={
            "id": "ID",
            "brand": "Marka",
            "branch": "Şube",
            "pricing_model": "Fiyat Modeli",
            "hourly_rate": "Saatlik Ücret",
            "package_rate": "Paket Primi",
            "package_threshold": "Paket Eşiği",
            "package_rate_low": "Eşik Altı Prim",
            "package_rate_high": "Eşik Üstü Prim",
            "fixed_monthly_fee": "Sabit Aylık Ücret",
            "vat_rate": "KDV",
            "target_headcount": "Hedef Kadro",
            "start_date": "Başlangıç Tarihi",
            "end_date": "Bitiş Tarihi",
            "extra_headcount_request": "Ek Kurye Talebi",
            "extra_headcount_request_date": "Ek Talep Tarihi",
            "reduce_headcount_request": "Kurye Azaltma Talebi",
            "reduce_headcount_request_date": "Azaltma Talep Tarihi",
            "contact_name": "Yetkili Adı",
            "contact_phone": "Yetkili Telefon",
            "contact_email": "Yetkili E-posta",
            "company_title": "Ünvan",
            "address": "Adres",
            "tax_office": "Vergi Dairesi",
            "tax_number": "Vergi Numarası",
            "active": "Durum",
            "notes": "Notlar",
        },
        value_maps={
            "pricing_model": PRICING_MODEL_LABELS,
            "active": ACTIVE_STATUS_LABELS,
        },
    )


def format_personnel_table(df: pd.DataFrame) -> pd.DataFrame:
    visible_df = df.drop(
        columns=[
            "assigned_restaurant_id",
            "motor_rental",
            "motor_purchase",
            "motor_purchase_monthly_amount",
            "motor_purchase_installment_count",
        ],
        errors="ignore",
    )
    return format_display_df(
        visible_df,
        currency_cols=["accounting_revenue", "accountant_cost", "company_setup_revenue", "company_setup_cost", "motor_rental_monthly_amount", "motor_purchase_sale_price", "monthly_fixed_cost"],
        rename_map={
            "id": "ID",
            "person_code": "Personel Kodu",
            "full_name": "Ad Soyad",
            "role": "Rol",
            "status": "Durum",
            "phone": "Telefon",
            "emergency_contact_name": "Acil Durum İletişim Kişisi",
            "emergency_contact_phone": "Acil Durum Telefonu",
            "address": "Adres",
            "tc_no": "TC Kimlik No",
            "iban": "IBAN",
            "accounting_type": "Muhasebe",
            "new_company_setup": "Yeni Şirket Açılışı",
            "accounting_revenue": "Muhasebe Geliri",
            "accountant_cost": "Muhasebeci Maliyeti",
            "company_setup_revenue": "Şirket Açılış Geliri",
            "company_setup_cost": "Şirket Açılış Maliyeti",
            "vehicle_type": "Motor Tipi",
            "motor_rental_monthly_amount": "Aylık Motor Kira Tutarı",
            "motor_purchase_start_date": "Motor Satın Alım Tarihi",
            "motor_purchase_commitment_months": "Taahhüt Süresi (Ay)",
            "motor_purchase_sale_price": "Aylık Motor Satış Taksiti",
            "current_plate": "Güncel Plaka",
            "start_date": "İşe Giriş Tarihi",
            "exit_date": "Çıkış Tarihi",
            "cost_model": "Maliyet Modeli",
            "monthly_fixed_cost": "Aylık Sabit Maliyet",
            "notes": "Notlar",
            "restoran": "Ana Restoran",
        },
        value_maps={
            "cost_model": COST_MODEL_LABELS,
        },
    )


def format_motor_purchase_summary(row: Any) -> str:
    if str(get_row_value(row, "motor_purchase", "Hayır") or "Hayır") != "Evet":
        return "-"
    monthly_amount = safe_float(
        get_row_value(
            row,
            "motor_purchase_monthly_amount",
            get_row_value(row, "motor_purchase_sale_price", 0.0),
        ),
        0.0,
    )
    commitment_months = safe_int(get_row_value(row, "motor_purchase_commitment_months", 0), 0)
    start_date_text = str(get_row_value(row, "motor_purchase_start_date", "") or "").strip()
    parts = []
    if monthly_amount > 0:
        parts.append(f"{fmt_try(monthly_amount)} / ay")
    if commitment_months > 0:
        parts.append(f"{commitment_months} ay")
    if start_date_text:
        parts.append(start_date_text)
    return " | ".join(parts) if parts else "Tanımlı"


def format_motor_rental_summary(row: Any) -> str:
    vehicle_type = str(get_row_value(row, "vehicle_type", "") or "").strip()
    motor_purchase = str(get_row_value(row, "motor_purchase", "Hayır") or "Hayır").strip()
    if motor_purchase == "Evet":
        return "Motor satışı aktif | kira uygulanmaz"
    if vehicle_type != "Çat Kapında":
        return "-"
    monthly_amount = safe_float(get_row_value(row, "motor_rental_monthly_amount", AUTO_MOTOR_RENTAL_DEDUCTION), AUTO_MOTOR_RENTAL_DEDUCTION)
    return f"{fmt_try(monthly_amount)} / ay"


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --ck-primary: #0A4CD2;
                --ck-primary-soft: #EFF5FF;
                --ck-border: #E7EDF6;
                --ck-text: #111827;
                --ck-muted: #667085;
                --ck-shadow: 0 16px 36px rgba(15, 23, 42, 0.07);
            }

            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(10,76,210,0.07), transparent 22%),
                    radial-gradient(circle at top left, rgba(14,165,233,0.06), transparent 18%),
                    linear-gradient(180deg, #F5F8FD 0%, #FBFCFE 100%);
            }

            header[data-testid="stHeader"] {
                background: rgba(245, 248, 253, 0.72);
            }

            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"],
            #MainMenu {
                display: none !important;
            }

            [data-testid="stToolbar"] {
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
            }

            header[data-testid="stHeader"] button[kind="header"] {
                display: inline-flex !important;
                align-items: center;
                justify-content: center;
                opacity: 1 !important;
                visibility: visible !important;
            }

            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapsedControl"] {
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
            }

            .block-container {
                max-width: 1460px;
                padding-top: 1.85rem;
                padding-bottom: 2rem;
            }

            [data-testid="stSidebar"] {
                background: #FFFFFF;
                border-right: 1px solid var(--ck-border);
                padding-top: 0.25rem;
            }

            section[data-testid="stSidebar"][aria-expanded="true"] {
                min-width: 17.4rem !important;
                max-width: 17.4rem !important;
            }

            section[data-testid="stSidebar"][aria-expanded="true"] > div {
                width: 17.4rem !important;
            }

            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
                color: var(--ck-text);
            }

            .ck-side-brand-shell {
                margin: 0.05rem 0 1rem;
                padding: 0.15rem 0 1rem 0.08rem;
                border-bottom: 1px solid #E7EDF6;
            }

            .ck-side-brand-kicker {
                color: #7A889E;
                font-size: 0.72rem;
                font-weight: 820;
                letter-spacing: 0.11em;
                text-transform: uppercase;
                margin-bottom: 0.55rem;
            }

            .ck-side-brand-title {
                font-size: 1.1rem;
                font-weight: 900;
                letter-spacing: -0.04em;
                color: #132238;
                line-height: 1.2;
            }

            .ck-side-brand-copy {
                margin-top: 0.28rem;
                color: #74839B;
                font-size: 0.8rem;
                line-height: 1.45;
                font-weight: 640;
            }

            .ck-side-section-title {
                margin: 0.3rem 0 0.42rem 0.08rem;
                color: #8A94A6;
                font-size: 0.7rem;
                font-weight: 860;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }

            [data-testid="stSidebar"] .stButton > button {
                width: 100%;
                justify-content: flex-start;
                text-align: left;
                border-radius: 15px;
                border: 1px solid #E3EAF5;
                background: #FFFFFF;
                min-height: 2.72rem;
                margin-bottom: 0.38rem;
                padding: 0.72rem 0.88rem;
                font-size: 0.9rem;
                font-weight: 770;
                letter-spacing: -0.01em;
                color: #23324A;
                transition: all 0.18s ease;
                box-shadow: none;
            }

            [data-testid="stSidebar"] .stButton > button:hover {
                border-color: #C6D7F4;
                background: #F8FBFF;
            }

            [data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: linear-gradient(180deg, #F5F9FF 0%, #EFF5FF 100%);
                border-color: #B8CEF3;
                color: #0C4BCB;
                box-shadow: inset 3px 0 0 #0C4BCB, 0 10px 22px rgba(12, 75, 203, 0.06);
            }

            .ck-profile-shell {
                margin-bottom: 0.35rem;
            }

            .ck-profile-hero {
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 14px;
                border-radius: 22px;
                background:
                    radial-gradient(circle at top right, rgba(255,255,255,0.18), transparent 26%),
                    linear-gradient(140deg, #0E2248 0%, #0C4BCB 58%, #13A4DE 100%);
                color: #FFFFFF;
                box-shadow: 0 22px 42px rgba(12, 75, 203, 0.2);
            }

            .ck-profile-avatar {
                width: 56px;
                height: 56px;
                border-radius: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(255,255,255,0.16);
                border: 1px solid rgba(255,255,255,0.18);
                font-size: 1.05rem;
                font-weight: 900;
            }

            .ck-profile-kicker {
                color: rgba(255,255,255,0.72);
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }

            .ck-profile-name {
                margin-top: 0.2rem;
                color: #FFFFFF;
                font-size: 1.05rem;
                font-weight: 860;
                letter-spacing: -0.03em;
            }

            .ck-profile-mail {
                margin-top: 0.2rem;
                color: rgba(255,255,255,0.82);
                font-size: 0.82rem;
                line-height: 1.45;
            }

            .ck-profile-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 0.75rem;
            }

            .ck-profile-chip {
                display: inline-flex;
                align-items: center;
                padding: 7px 11px;
                border-radius: 999px;
                background: #F5F8FF;
                border: 1px solid #D8E6FB;
                color: #294B7C;
                font-size: 0.76rem;
                font-weight: 800;
            }

            .crm-section {
                margin-bottom: 1rem;
            }

            .crm-section h3 {
                margin: 0;
                font-size: 1.35rem;
                line-height: 1.1;
                letter-spacing: -0.04em;
                color: var(--ck-text);
                font-weight: 800;
            }

            .crm-section p {
                margin: 0.35rem 0 0;
                color: var(--ck-muted);
                line-height: 1.6;
                font-size: 0.95rem;
            }

            .ck-hero {
                position: relative;
                overflow: hidden;
                border-radius: 28px;
                padding: 28px 26px 24px;
                margin: 0 0 1.2rem 0;
                background:
                    radial-gradient(circle at top right, rgba(255,255,255,0.24), transparent 22%),
                    linear-gradient(135deg, #0D4CCD 0%, #0B67D8 48%, #1695D3 100%);
                box-shadow: 0 22px 52px rgba(10, 76, 210, 0.22);
                color: #FFFFFF;
            }

            .ck-hero::after {
                content: "";
                position: absolute;
                right: -50px;
                top: -50px;
                width: 180px;
                height: 180px;
                border-radius: 50%;
                background: rgba(255,255,255,0.09);
            }

            .ck-hero-kicker {
                display: inline-flex;
                width: fit-content;
                padding: 7px 12px;
                border-radius: 999px;
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.18);
                font-size: 0.76rem;
                font-weight: 800;
                letter-spacing: 0.12em;
                margin-bottom: 0.9rem;
            }

            .ck-hero-title {
                position: relative;
                z-index: 1;
                font-size: 2rem;
                font-weight: 900;
                letter-spacing: -0.05em;
                line-height: 1.02;
                max-width: 760px;
            }

            .ck-hero-subtitle {
                position: relative;
                z-index: 1;
                margin-top: 0.6rem;
                max-width: 760px;
                color: rgba(255,255,255,0.9);
                line-height: 1.7;
                font-size: 0.98rem;
            }

            .ck-hero-grid {
                position: relative;
                z-index: 1;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 12px;
                margin-top: 1.25rem;
            }

            .ck-hero-stat {
                background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 18px;
                padding: 14px 14px 12px;
                backdrop-filter: blur(8px);
            }

            .ck-hero-value {
                font-size: 1.35rem;
                line-height: 1;
                font-weight: 900;
                letter-spacing: -0.04em;
            }

            .ck-hero-label {
                margin-top: 0.45rem;
                font-size: 0.82rem;
                color: rgba(255,255,255,0.82);
                line-height: 1.4;
            }

            .ck-exec-strip {
                display: grid;
                gap: 14px;
                margin: 0.1rem 0 1rem;
            }

            .ck-exec-strip-head {
                display: flex;
                align-items: end;
                justify-content: space-between;
                gap: 12px;
            }

            .ck-exec-strip-title {
                color: var(--ck-text);
                font-size: 1.02rem;
                font-weight: 860;
                letter-spacing: -0.03em;
            }

            .ck-exec-strip-copy {
                color: var(--ck-muted);
                font-size: 0.86rem;
                line-height: 1.55;
            }

            .ck-exec-strip-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
                gap: 12px;
            }

            .ck-exec-card {
                position: relative;
                overflow: hidden;
                border-radius: 22px;
                border: 1px solid #DFE8F7;
                background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
                padding: 16px 16px 15px;
                box-shadow: 0 16px 28px rgba(15, 23, 42, 0.05);
            }

            .ck-exec-card::after {
                content: "";
                position: absolute;
                inset: 0 0 auto 0;
                height: 3px;
                background: linear-gradient(90deg, #D8E5FB 0%, #EDF3FD 100%);
            }

            .ck-exec-card-positive::after {
                background: linear-gradient(90deg, #1D8F57 0%, #7FD4A6 100%);
            }

            .ck-exec-card-warning::after {
                background: linear-gradient(90deg, #C98A12 0%, #F5D27B 100%);
            }

            .ck-exec-card-critical::after {
                background: linear-gradient(90deg, #C53B5C 0%, #F2A3B6 100%);
            }

            .ck-exec-card-label {
                color: #6A7A92;
                font-size: 0.72rem;
                font-weight: 860;
                letter-spacing: 0.12em;
                text-transform: uppercase;
            }

            .ck-exec-card-value {
                margin-top: 0.72rem;
                color: #10203A;
                font-size: 1.38rem;
                font-weight: 900;
                letter-spacing: -0.05em;
                line-height: 1.05;
            }

            .ck-exec-card-note {
                margin-top: 0.58rem;
                color: #71819A;
                font-size: 0.82rem;
                line-height: 1.45;
                font-weight: 620;
            }

            .ck-tab-header {
                background: linear-gradient(180deg, #FFFFFF 0%, #F9FBFF 100%);
                border: 1px solid var(--ck-border);
                border-radius: 22px;
                padding: 18px 18px 16px;
                box-shadow: var(--ck-shadow);
                margin: 0.15rem 0 1rem 0;
            }

            .ck-tab-header-title {
                font-size: 1.1rem;
                font-weight: 850;
                color: var(--ck-text);
                letter-spacing: -0.03em;
            }

            .ck-tab-header-subtitle {
                margin-top: 0.35rem;
                color: var(--ck-muted);
                line-height: 1.65;
                font-size: 0.93rem;
            }

            .ck-action-card {
                background: linear-gradient(180deg, #FFFFFF 0%, #F9FBFF 100%);
                border: 1px solid #DFE9F8;
                border-radius: 22px;
                padding: 18px 18px 16px;
                box-shadow: var(--ck-shadow);
                min-height: 158px;
                height: 158px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }

            .ck-action-card-highlight {
                background:
                    radial-gradient(circle at top right, rgba(255,255,255,0.22), transparent 22%),
                    linear-gradient(135deg, #0C4BCB 0%, #127ADB 100%);
                border-color: transparent;
                box-shadow: 0 18px 38px rgba(12, 75, 203, 0.22);
            }

            .ck-action-card-title {
                font-size: 1.02rem;
                font-weight: 860;
                color: var(--ck-text);
                letter-spacing: -0.03em;
            }

            .ck-action-card-highlight .ck-action-card-title {
                color: #FFFFFF;
            }

            .ck-action-card-subtitle {
                margin-top: 0.45rem;
                color: var(--ck-muted);
                line-height: 1.65;
                font-size: 0.9rem;
            }

            .ck-action-card-highlight .ck-action-card-subtitle {
                color: rgba(255,255,255,0.86);
            }

            .ck-workspace-shell {
                margin-bottom: 1rem;
                padding: 1.15rem 1.2rem 1rem;
                border-radius: 24px;
                border: 1px solid #DCE6F5;
                background:
                    radial-gradient(circle at top right, rgba(35, 114, 244, 0.12), transparent 28%),
                    linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,251,255,0.98) 100%);
                box-shadow: 0 20px 40px rgba(15, 23, 42, 0.06);
            }

            .ck-workspace-shell-kicker {
                color: #4E6FA7;
                font-size: 0.76rem;
                font-weight: 900;
                letter-spacing: 0.12em;
                text-transform: uppercase;
            }

            .ck-workspace-shell-title {
                margin-top: 0.6rem;
                color: #13233D;
                font-size: 1.35rem;
                line-height: 1.12;
                font-weight: 840;
                letter-spacing: -0.04em;
            }

            .ck-workspace-shell-text {
                margin-top: 0.55rem;
                color: #617491;
                font-size: 0.95rem;
                line-height: 1.7;
            }

            .ck-workspace-shell-loader {
                margin-top: 0.95rem;
                width: 100%;
                height: 9px;
                overflow: hidden;
                border-radius: 999px;
                background: #EAF1FB;
            }

            .ck-workspace-shell-loader-bar {
                width: 36%;
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, #0C4BCB 0%, #1A9EF0 100%);
                animation: ckWorkspaceShellPulse 1.15s ease-in-out infinite;
                transform-origin: left center;
            }

            @keyframes ckWorkspaceShellPulse {
                0% { transform: translateX(-22%) scaleX(0.84); opacity: 0.75; }
                50% { transform: translateX(108%) scaleX(1.02); opacity: 1; }
                100% { transform: translateX(230%) scaleX(0.9); opacity: 0.75; }
            }

            .ck-field-label {
                margin: 0.1rem 0 0.35rem;
                color: #324766;
                font-size: 0.95rem;
                font-weight: 700;
                line-height: 1.35;
            }

            .ck-required-star {
                color: #E11D48;
                font-weight: 900;
                margin-left: 0.15rem;
            }

            .ck-login-gap {
                height: clamp(24px, 5vh, 56px);
            }

            .ck-login-card {
                position: relative;
                overflow: hidden;
                background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,251,255,0.98) 100%);
                border: 1px solid rgba(231, 237, 246, 0.92);
                border-radius: 32px;
                padding: 28px 28px 24px;
                box-shadow: 0 24px 60px rgba(15, 23, 42, 0.10);
                backdrop-filter: blur(10px);
            }

            .ck-login-card::before {
                content: "";
                position: absolute;
                inset: 0 0 auto 0;
                height: 180px;
                background: radial-gradient(circle at top right, rgba(20,145,212,0.16), transparent 34%);
                pointer-events: none;
            }

            .ck-login-logo {
                display: flex;
                align-items: center;
                gap: 14px;
                margin-bottom: 1rem;
                position: relative;
                z-index: 1;
            }

            .ck-login-logo-mark {
                width: 96px;
                height: 96px;
                flex: 0 0 96px;
                border-radius: 26px;
                background: linear-gradient(135deg, #0D4CCD 0%, #1491D4 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                color: white;
                font-size: 1.6rem;
                font-weight: 900;
                letter-spacing: 0.08em;
                box-shadow: 0 18px 34px rgba(13, 76, 205, 0.22);
            }

            .ck-login-logo-mark-image {
                background: linear-gradient(180deg, #FFFFFF 0%, #F4F8FF 100%);
                border: 1px solid #DCE7FF;
                padding: 2px;
            }

            .ck-login-logo-image {
                width: 100%;
                height: 100%;
                display: block;
                object-fit: contain;
                border-radius: 22px;
                image-rendering: -webkit-optimize-contrast;
                image-rendering: crisp-edges;
            }

            .ck-login-logo-copy {
                display: flex;
                flex-direction: column;
                gap: 0.18rem;
            }

            .ck-login-logo-eyebrow {
                color: #5A7198;
                font-size: 0.78rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.12em;
            }

            .ck-login-logo-line {
                color: var(--ck-text);
                font-size: 1.28rem;
                font-weight: 850;
                letter-spacing: -0.04em;
            }

            .ck-login-kicker {
                width: fit-content;
                margin: 0 0 1rem 0;
                padding: 7px 12px;
                border-radius: 999px;
                background: var(--ck-primary-soft);
                color: var(--ck-primary);
                border: 1px solid #D8E5FF;
                font-size: 0.74rem;
                font-weight: 800;
                letter-spacing: 0.12em;
                position: relative;
                z-index: 1;
            }

            .ck-login-title {
                font-size: 2.2rem;
                font-weight: 850;
                letter-spacing: -0.06em;
                color: var(--ck-text);
                margin-bottom: 0.55rem;
                line-height: 1.02;
                max-width: 700px;
                position: relative;
                z-index: 1;
            }

            .ck-login-subtitle {
                color: var(--ck-muted);
                line-height: 1.7;
                margin-bottom: 1.15rem;
                font-size: 0.97rem;
                max-width: 690px;
                position: relative;
                z-index: 1;
            }

            .ck-login-feature-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
                margin-bottom: 1.25rem;
                position: relative;
                z-index: 1;
            }

            .ck-login-feature-card {
                min-height: 96px;
                padding: 14px 15px;
                border-radius: 18px;
                background: rgba(255,255,255,0.82);
                border: 1px solid #E2EBFA;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.65);
            }

            .ck-login-feature-card span {
                display: block;
                margin-bottom: 0.45rem;
                color: #3F6EA9;
                font-size: 0.76rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .ck-login-feature-card strong {
                display: block;
                color: var(--ck-text);
                font-size: 0.93rem;
                line-height: 1.5;
                font-weight: 760;
            }

            .ck-login-form-shell {
                position: relative;
                z-index: 1;
                background: rgba(255,255,255,0.96);
                border: 1px solid #E4ECF8;
                border-radius: 24px;
                padding: 20px 18px 16px;
                box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
            }

            .ck-login-form-title {
                color: var(--ck-text);
                font-size: 1.06rem;
                font-weight: 850;
                letter-spacing: -0.03em;
            }

            .ck-login-form-subtitle {
                color: var(--ck-muted);
                margin: 0.32rem 0 1rem;
                font-size: 0.9rem;
                line-height: 1.6;
            }

            .ck-login-card [data-testid="stTextInputRootElement"] input {
                border-radius: 14px;
            }

            .ck-login-card .stCheckbox label {
                color: #42526B;
                font-weight: 600;
            }

            .ck-login-card div[data-testid="stFormSubmitButton"] button {
                background: linear-gradient(135deg, #0D4CCD 0%, #1491D4 100%);
                color: white;
                border: none;
                box-shadow: 0 16px 30px rgba(13, 76, 205, 0.24);
            }

            .ck-login-card div[data-testid="stFormSubmitButton"] button p {
                color: white !important;
            }

            .ck-login-help-card {
                margin-top: 0.85rem;
                padding: 14px 15px;
                border-radius: 18px;
                background: #F7FAFF;
                border: 1px solid #DCE8FB;
            }

            .ck-login-help-title {
                color: var(--ck-text);
                font-size: 0.98rem;
                font-weight: 820;
                margin-bottom: 0.35rem;
            }

            .ck-login-help-text {
                color: #4B5E7A;
                font-size: 0.88rem;
                line-height: 1.6;
            }

            .ck-login-help-steps {
                display: grid;
                gap: 8px;
                margin-top: 0.78rem;
            }

            .ck-login-help-step {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                color: #294467;
                font-size: 0.86rem;
                line-height: 1.55;
            }

            .ck-login-help-step-badge {
                width: 24px;
                height: 24px;
                flex: 0 0 24px;
                border-radius: 999px;
                background: #E8F0FF;
                color: #0D4CCD;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.76rem;
                font-weight: 900;
            }

            div[data-testid="stMetric"] {
                background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%);
                border: 1px solid var(--ck-border);
                border-radius: 18px;
                padding: 15px 16px;
                box-shadow: var(--ck-shadow);
            }

            div[data-testid="stMetric"] label {
                font-weight: 800;
            }

            div[data-testid="stDataFrame"] {
                border: 1px solid var(--ck-border);
                border-radius: 18px;
                overflow: hidden;
                background: white;
                box-shadow: var(--ck-shadow);
            }

            .ck-panel {
                background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%);
                border: 1px solid var(--ck-border);
                border-radius: 20px;
                padding: 18px;
                box-shadow: var(--ck-shadow);
                height: 100%;
            }

            .ck-panel-title {
                font-size: 1rem;
                font-weight: 800;
                color: var(--ck-text);
                margin-bottom: 0.85rem;
            }

            .ck-dashboard-section-subtitle {
                margin-top: -0.35rem;
                margin-bottom: 0.9rem;
                color: #657894;
                font-size: 0.84rem;
                line-height: 1.55;
            }

            .ck-dashboard-quick-note {
                margin-top: -0.35rem;
                margin-bottom: 0.85rem;
                color: #657894;
                font-size: 0.82rem;
                line-height: 1.5;
            }

            .ck-dashboard-spacer-sm {
                height: 0.4rem;
            }

            @media (min-width: 1200px) {
                .main .block-container {
                    max-width: 1460px;
                }

                .ck-panel {
                    padding: 20px;
                }

                .ck-panel-title {
                    font-size: 1.02rem;
                }
            }

            .ck-list-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                padding: 11px 0;
                border-bottom: 1px solid #EEF2F7;
                font-size: 0.92rem;
                color: var(--ck-text);
            }

            .ck-list-row:last-child {
                border-bottom: none;
            }

            .ck-chip {
                background: #EEF4FF;
                border: 1px solid #D7E6FF;
                color: #004AE0;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 0.78rem;
                font-weight: 800;
                white-space: nowrap;
            }

            .ck-alert-stack {
                display: grid;
                gap: 10px;
            }

            .ck-alert-item {
                border-radius: 18px;
                border: 1px solid #E4EBF7;
                background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
                padding: 13px 14px 12px;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
            }

            .ck-alert-item-critical {
                border-color: #F5C8CF;
                background: linear-gradient(180deg, #FFF6F7 0%, #FFFDFD 100%);
            }

            .ck-alert-item-warning {
                border-color: #F4E1B8;
                background: linear-gradient(180deg, #FFFBEF 0%, #FFFDFC 100%);
            }

            .ck-alert-item-info {
                border-color: #D8E6FF;
                background: linear-gradient(180deg, #F7FAFF 0%, #FFFFFF 100%);
            }

            .ck-alert-item-success {
                border-color: #CDE7D7;
                background: linear-gradient(180deg, #F4FBF6 0%, #FFFFFF 100%);
            }

            .ck-alert-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
            }

            .ck-alert-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 6px 9px;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 900;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .ck-alert-badge-critical {
                background: #FFE2E8;
                color: #B12043;
            }

            .ck-alert-badge-warning {
                background: #FFF0C9;
                color: #9B6A00;
            }

            .ck-alert-badge-info {
                background: #EAF2FF;
                color: #1E56BF;
            }

            .ck-alert-badge-success {
                background: #E2F5E8;
                color: #197A42;
            }

            .ck-alert-title {
                color: var(--ck-text);
                font-size: 0.96rem;
                font-weight: 820;
                letter-spacing: -0.02em;
                line-height: 1.4;
            }

            .ck-alert-detail {
                margin-top: 0.42rem;
                color: #617491;
                font-size: 0.88rem;
                line-height: 1.55;
            }

            .ck-data-grid-table {
                display: grid;
                gap: 10px;
                margin-top: 0.35rem;
            }

            .ck-data-grid-head {
                display: grid;
                grid-template-columns: repeat(var(--ck-cols), minmax(0, 1fr));
                gap: 12px;
                padding: 0 6px;
            }

            .ck-data-grid-head-item {
                color: #74839B;
                font-size: 0.72rem;
                font-weight: 900;
                letter-spacing: 0.11em;
                text-transform: uppercase;
            }

            .ck-data-grid-row {
                display: grid;
                grid-template-columns: repeat(var(--ck-cols), minmax(0, 1fr));
                gap: 12px;
                border: 1px solid #E3ECFA;
                border-radius: 18px;
                background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
                padding: 14px 15px;
                box-shadow: 0 12px 24px rgba(15, 23, 42, 0.04);
            }

            .ck-data-cell {
                min-width: 0;
            }

            .ck-data-cell-label {
                display: none;
                color: #74839B;
                font-size: 0.7rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.22rem;
            }

            .ck-data-cell-value {
                color: var(--ck-text);
                font-size: 0.92rem;
                font-weight: 700;
                line-height: 1.45;
                word-break: break-word;
            }

            .ck-data-cell-value-muted {
                color: #5F738F;
                font-weight: 620;
            }

            .ck-data-pill {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 6px 10px;
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 900;
                letter-spacing: 0.05em;
                white-space: nowrap;
            }

            .ck-data-pill-critical {
                background: #FFE4EA;
                color: #B51D45;
            }

            .ck-data-pill-warning {
                background: #FFF1CE;
                color: #966400;
            }

            .ck-data-pill-info {
                background: #EAF2FF;
                color: #1656C0;
            }

            .ck-data-pill-success {
                background: #E3F7EA;
                color: #177241;
            }

            .stButton > button, .stDownloadButton > button {
                border-radius: 14px;
                font-weight: 800;
                border: 1px solid #DCE7FA;
                background: #FFFFFF;
                min-height: 2.7rem;
            }

            .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
                background: var(--ck-primary);
                color: #FFFFFF;
                border: none;
            }

            .stTextInput input, .stNumberInput input, .stTextArea textarea {
                border-radius: 14px;
            }

            .stSelectbox [data-baseweb="select"] > div, .stDateInput > div > div {
                border-radius: 14px;
            }

            div[data-baseweb="tab-list"] {
                gap: 0.5rem;
                background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
                border: 1px solid #E3ECFA;
                border-radius: 22px;
                padding: 0.45rem;
                box-shadow: 0 14px 32px rgba(15, 23, 42, 0.06);
            }

            div[data-baseweb="tab-list"] button {
                border-radius: 16px;
                border: 1px solid #DCE7FA;
                background: #F8FAFF;
                padding-top: 0.7rem;
                padding-bottom: 0.7rem;
                min-height: 58px;
                transition: all 0.18s ease;
            }

            div[data-baseweb="tab-list"] button[aria-selected="true"] {
                background: linear-gradient(135deg, #0D4CCD 0%, #1184DB 100%);
                border-color: transparent;
                box-shadow: 0 14px 28px rgba(13, 76, 205, 0.22);
                transform: translateY(-1px);
            }

            div[data-baseweb="tab-list"] button[aria-selected="true"] p {
                color: white !important;
            }

            div[data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
                font-size: 0.95rem;
                font-weight: 850;
            }

            @media (max-width: 960px) {
                .ck-hero-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .ck-login-feature-grid {
                    grid-template-columns: 1fr;
                }

                .ck-login-title {
                    font-size: 1.8rem;
                }
            }

            @media (max-width: 640px) {
                .ck-hero {
                    padding: 22px 18px 18px;
                }

                .ck-hero-title {
                    font-size: 1.55rem;
                }

                .ck-hero-grid {
                    grid-template-columns: 1fr;
                }

                .ck-action-card {
                    height: auto;
                    min-height: 132px;
                }

                .ck-login-card {
                    padding: 22px 18px 18px;
                    border-radius: 26px;
                }

                .ck-login-logo-mark {
                    width: 74px;
                    height: 74px;
                    flex: 0 0 74px;
                    border-radius: 22px;
                }

                .ck-login-logo-line {
                    font-size: 1.08rem;
                }

                .ck-login-title {
                    font-size: 1.55rem;
                }

                .ck-login-form-shell {
                    padding: 18px 14px 14px;
                }

                .ck-data-grid-head {
                    display: none;
                }

                .ck-data-grid-row {
                    grid-template-columns: 1fr;
                    gap: 10px;
                    padding: 13px 14px;
                }

                .ck-data-cell-label {
                    display: block;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

configure_backup_sections(
    fetch_df_fn=fetch_df,
    table_export_order=TABLE_EXPORT_ORDER,
    db_path=DB_PATH,
    database_has_operational_data_fn=database_has_operational_data,
    import_sqlite_into_current_db_fn=import_sqlite_into_current_db,
)


configure_equipment_rules(
    first_row_value_fn=first_row_value,
    get_row_value_fn=get_row_value,
    safe_int_fn=safe_int,
    safe_float_fn=safe_float,
    parse_date_value_fn=parse_date_value,
    fetch_df_fn=fetch_df,
    equipment_always_standard_vat_items=EQUIPMENT_ALWAYS_STANDARD_VAT_ITEMS,
    equipment_vat_rate_before_reduction=EQUIPMENT_VAT_RATE_BEFORE_REDUCTION,
    equipment_vat_rate_after_reduction=EQUIPMENT_VAT_RATE_AFTER_REDUCTION,
    equipment_reduced_vat_start_date=EQUIPMENT_REDUCED_VAT_START_DATE,
    auto_motor_rental_deduction=AUTO_MOTOR_RENTAL_DEDUCTION,
    auto_motor_purchase_monthly_deduction=AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
    auto_motor_purchase_installment_count=AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT,
    auto_equipment_installment_count=AUTO_EQUIPMENT_INSTALLMENT_COUNT,
    auto_onboarding_items=AUTO_ONBOARDING_ITEMS,
)


def get_restaurant_options(conn: sqlite3.Connection) -> dict[str, int]:
    return fetch_active_restaurant_options(conn)


def get_person_options(conn: sqlite3.Connection, active_only: bool = True) -> dict[str, int]:
    return fetch_person_options_map(conn, active_only=active_only)


def role_code_prefix(role: str) -> str:
    mapping = {
        "Kurye": "K",
        "Bölge Müdürü": "BM",
        "Saha Denetmen Şefi": "SDS",
        "Restoran Takım Şefi": "RTS",
        "Joker": "J",
        "Şef": "TŞ",
    }
    return mapping.get(role or "Kurye", "K")


def next_person_code(conn: sqlite3.Connection, role: str, exclude_id: int | None = None) -> str:
    prefix = role_code_prefix(role)
    sql = "SELECT person_code FROM personnel WHERE person_code LIKE ?"
    params = [f"CK-{prefix}%"]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    rows = conn.execute(sql, tuple(params)).fetchall()
    max_num = 0
    for row in rows:
        code = row["person_code"] or ""
        match = re.search(rf"^CK-{re.escape(prefix)}(\d+)$", code)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"CK-{prefix}{max_num + 1:02d}"


def dashboard_tab(conn: sqlite3.Connection) -> None:
    today_value = date.today()
    selected_month = today_value.strftime("%Y-%m")
    month_start, month_end = month_bounds(selected_month)

    entries = fetch_df(
        conn,
        """
        SELECT d.*, r.brand, r.branch, r.target_headcount, r.pricing_model, r.hourly_rate, r.package_rate,
               r.package_threshold, r.package_rate_low, r.package_rate_high, r.fixed_monthly_fee, r.vat_rate
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        """,
    )
    active_restaurants_df = fetch_df(conn, "SELECT * FROM restaurants WHERE active = 1 ORDER BY brand, branch")
    personnel_df = fetch_df(conn, "SELECT * FROM personnel")
    role_history_df = fetch_df(conn, "SELECT * FROM personnel_role_history ORDER BY personnel_id, effective_date, id")
    month_deductions = fetch_df(conn, "SELECT * FROM deductions WHERE deduction_date BETWEEN ? AND ?", (month_start, month_end))

    for optional_column, default_value in {
        "company_title": "",
        "address": "",
        "contact_name": "",
        "contact_phone": "",
        "contact_email": "",
        "tax_office": "",
        "tax_number": "",
        "target_headcount": 0,
    }.items():
        if optional_column not in active_restaurants_df.columns:
            active_restaurants_df[optional_column] = default_value

    active_restaurants = len(active_restaurants_df)
    active_people_df = personnel_df[personnel_df["status"].fillna("").astype(str) == "Aktif"].copy() if not personnel_df.empty else pd.DataFrame()
    active_people = len(active_people_df)

    if not entries.empty:
        entries["entry_date_value"] = pd.to_datetime(entries["entry_date"], errors="coerce").dt.date
        entries = entries[entries["entry_date_value"].notna()].copy()
    else:
        entries = pd.DataFrame(
            columns=[
                "entry_date",
                "entry_date_value",
                "restaurant_id",
                "actual_personnel_id",
                "status",
                "worked_hours",
                "package_count",
                "brand",
                "branch",
                "target_headcount",
                "pricing_model",
                "hourly_rate",
                "package_rate",
                "package_threshold",
                "package_rate_low",
                "package_rate_high",
                "fixed_monthly_fee",
                "vat_rate",
            ]
        )

    month_entries = (
        entries[(entries["entry_date_value"] >= parse_date_value(month_start)) & (entries["entry_date_value"] <= parse_date_value(month_end))].copy()
        if not entries.empty
        else pd.DataFrame(columns=entries.columns)
    )
    today_entries = entries[entries["entry_date_value"] == today_value].copy() if not entries.empty else pd.DataFrame(columns=entries.columns)
    working_today_entries = (
        today_entries[
            (~today_entries["status"].fillna("").isin(["İzin", "Gelmedi"]))
            | (today_entries["worked_hours"].fillna(0) > 0)
            | (today_entries["package_count"].fillna(0) > 0)
        ].copy()
        if not today_entries.empty
        else pd.DataFrame(columns=today_entries.columns)
    )

    today_working_people = (
        int(working_today_entries["actual_personnel_id"].dropna().astype(int).nunique())
        if not working_today_entries.empty and "actual_personnel_id" in working_today_entries.columns
        else 0
    )
    month_packages = float(month_entries["package_count"].sum()) if not month_entries.empty else 0.0

    invoice_df = build_invoice_summary_df(month_entries)
    profit_df, _, shared_overhead_df = build_branch_profitability(
        month_entries,
        personnel_df,
        month_deductions,
        invoice_df,
        role_history_df,
        restaurants_df=active_restaurants_df,
    )
    month_revenue = float(invoice_df["kdv_dahil"].sum()) if not invoice_df.empty else 0.0
    month_operation_gap = float(profit_df["brut_fark"].sum()) if not profit_df.empty else 0.0

    today_restaurant_ids = (
        today_entries["restaurant_id"].dropna().astype(int).unique().tolist()
        if not today_entries.empty and "restaurant_id" in today_entries.columns
        else []
    )
    missing_attendance_df = (
        active_restaurants_df[~active_restaurants_df["id"].astype(int).isin(today_restaurant_ids)][["brand", "branch"]].copy()
        if not active_restaurants_df.empty
        else pd.DataFrame(columns=["brand", "branch"])
    )

    if not working_today_entries.empty:
        today_headcount_df = (
            working_today_entries.groupby("restaurant_id", dropna=False)["actual_personnel_id"]
            .nunique()
            .reset_index(name="bugun_kadro")
        )
    else:
        today_headcount_df = pd.DataFrame(columns=["restaurant_id", "bugun_kadro"])

    restaurant_headcount_df = active_restaurants_df[["id", "brand", "branch", "target_headcount"]].copy()
    restaurant_headcount_df["target_headcount"] = restaurant_headcount_df["target_headcount"].apply(lambda value: safe_int(value, 0))
    under_target_df = restaurant_headcount_df.merge(
        today_headcount_df,
        how="left",
        left_on="id",
        right_on="restaurant_id",
    ).fillna({"bugun_kadro": 0})
    under_target_df["bugun_kadro"] = under_target_df["bugun_kadro"].apply(lambda value: safe_int(value, 0))
    under_target_df["acik_kadro"] = under_target_df["target_headcount"] - under_target_df["bugun_kadro"]
    under_target_df = under_target_df[(under_target_df["target_headcount"] > 0) & (under_target_df["acik_kadro"] > 0)].copy()
    under_target_df = under_target_df.sort_values(["acik_kadro", "brand", "branch"], ascending=[False, True, True])

    people_lookup = personnel_df[["id", "full_name", "role"]].rename(
        columns={"id": "actual_personnel_id", "full_name": "personel", "role": "personel_rolu"}
    ) if not personnel_df.empty else pd.DataFrame(columns=["actual_personnel_id", "personel", "personel_rolu"])
    joker_usage_df = pd.DataFrame(columns=["restoran", "joker_sayisi", "paket"])
    if not working_today_entries.empty:
        joker_entries = working_today_entries.merge(people_lookup, how="left", on="actual_personnel_id")
        joker_entries = joker_entries[
            (joker_entries["status"].fillna("").astype(str) == "Joker")
            | (joker_entries["personel_rolu"].fillna("").astype(str) == "Joker")
        ].copy()
        if not joker_entries.empty:
            joker_usage_df = (
                joker_entries.groupby(["brand", "branch"], dropna=False)
                .agg(joker_sayisi=("actual_personnel_id", "nunique"), paket=("package_count", "sum"))
                .reset_index()
            )
            joker_usage_df["restoran"] = joker_usage_df["brand"] + " - " + joker_usage_df["branch"]
            joker_usage_df = joker_usage_df[["restoran", "joker_sayisi", "paket"]].sort_values(["joker_sayisi", "paket"], ascending=[False, False])

    missing_personnel_rows = []
    if not active_people_df.empty:
        for _, row in active_people_df.iterrows():
            missing_fields = []
            if not str(row.get("phone") or "").strip():
                missing_fields.append("Telefon")
            if not str(row.get("tc_no") or "").strip():
                missing_fields.append("TC")
            if not str(row.get("iban") or "").strip():
                missing_fields.append("IBAN")
            if not str(row.get("current_plate") or "").strip():
                missing_fields.append("Plaka")
            if role_requires_primary_restaurant(str(row.get("role") or "")) and not safe_int(row.get("assigned_restaurant_id"), 0):
                missing_fields.append("Ana restoran")
            if missing_fields:
                missing_personnel_rows.append(
                    {
                        "personel": str(row.get("full_name") or "-"),
                        "rol": str(row.get("role") or "-"),
                        "eksik_alanlar": ", ".join(missing_fields),
                    }
                )
    missing_personnel_df = pd.DataFrame(missing_personnel_rows)

    missing_restaurant_rows = []
    if not active_restaurants_df.empty:
        for _, row in active_restaurants_df.iterrows():
            missing_fields = []
            for field_label, field_name in [
                ("Yetkili", "contact_name"),
                ("Telefon", "contact_phone"),
                ("E-posta", "contact_email"),
                ("Ünvan", "company_title"),
                ("Adres", "address"),
                ("Vergi Dairesi", "tax_office"),
                ("Vergi No", "tax_number"),
            ]:
                if not str(row.get(field_name) or "").strip():
                    missing_fields.append(field_label)
            if missing_fields:
                missing_restaurant_rows.append(
                    {
                        "restoran": f"{row['brand']} - {row['branch']}",
                        "eksik_alanlar": ", ".join(missing_fields),
                    }
                )
    missing_restaurant_df = pd.DataFrame(missing_restaurant_rows)

    critical_alert_count = (
        len(missing_attendance_df)
        + len(under_target_df)
        + len(missing_personnel_df)
        + len(missing_restaurant_df)
    )

    render_management_hero(
        "GENEL BAKIŞ",
        "Operasyonun güncel ritmi, riski ve finansal görünümü",
        "Bugünkü saha yükünü, eksik kadroları ve bu ayki finansal fotoğrafı tek panelde gör; yönetim kararlarını daha hızlı ve daha kontrollü ver.",
        [
            ("Aktif Restoran", active_restaurants),
            ("Aktif Personel", active_people),
            ("Bugün Çalışan", today_working_people),
            ("Bu Ay Paket", fmt_number(month_packages)),
            ("Bu Ay Fatura", fmt_try(month_revenue)),
            ("Kritik Uyarı", critical_alert_count),
            ("Bu Ay Operasyon Farkı", fmt_try(month_operation_gap)),
        ],
    )

    top_profit_items, risk_items = build_dashboard_profit_snapshots(profit_df, fmt_try_fn=fmt_try)
    priority_alerts = build_dashboard_priority_alerts(
        missing_attendance_df,
        under_target_df,
        profit_df,
        safe_int_fn=safe_int,
        fmt_try_fn=fmt_try,
    )
    brand_summary_df = build_dashboard_brand_summary(
        month_entries,
        invoice_df,
        profit_df,
        safe_float_fn=safe_float,
    )

    shared_overhead_total = float(shared_overhead_df["aylik_net_maliyet"].sum()) if not shared_overhead_df.empty else 0.0
    render_dashboard_summary_cards(
        missing_attendance_count=len(missing_attendance_df),
        under_target_count=len(under_target_df),
        joker_usage_count=len(joker_usage_df),
        missing_personnel_count=len(missing_personnel_df),
        missing_restaurant_count=len(missing_restaurant_df),
        month_revenue=month_revenue,
        month_operation_gap=month_operation_gap,
        shared_overhead_total=shared_overhead_total,
        profit_df=profit_df,
        render_record_snapshot_fn=render_record_snapshot,
        fmt_try_fn=fmt_try,
    )
    render_dashboard_focus_sections(
        priority_alerts=priority_alerts,
        brand_summary_df=brand_summary_df,
        render_alert_stack_fn=render_alert_stack,
        render_dashboard_data_grid_fn=render_dashboard_data_grid,
        fmt_number_fn=fmt_number,
        fmt_try_fn=fmt_try,
    )

    if entries.empty:
        st.info("Henüz günlük puantaj kaydı yok. İlk kayıtlar geldikçe dashboard operasyon akışını burada gösterecek.")
    daily_trend = entries.groupby("entry_date_value", dropna=False).agg(
        paket=("package_count", "sum"),
        saat=("worked_hours", "sum"),
    ).reset_index().rename(columns={"entry_date_value": "gun"}) if not entries.empty else pd.DataFrame(columns=["gun", "paket", "saat"])
    daily_trend = daily_trend.sort_values("gun").tail(14)
    daily_trend["gun_label"] = pd.to_datetime(daily_trend["gun"]).dt.strftime("%d %b")
    month_perf = (
        month_entries.groupby(["brand", "branch"], dropna=False).agg(paket=("package_count", "sum"), saat=("worked_hours", "sum")).reset_index()
        if not month_entries.empty
        else pd.DataFrame(columns=["brand", "branch", "paket", "saat"])
    )
    if not month_perf.empty:
        month_perf["restoran"] = month_perf["brand"] + " - " + month_perf["branch"]
        month_perf = month_perf[["restoran", "paket", "saat"]].sort_values(["paket", "saat"], ascending=[False, False])

    render_dashboard_activity_sections(
        entries_empty=entries.empty,
        daily_trend=daily_trend,
        month_perf=month_perf,
        render_dashboard_section_header_fn=render_dashboard_section_header,
        render_record_snapshot_fn=render_record_snapshot,
        fmt_number_fn=fmt_number,
    )
    render_dashboard_action_sections(
        missing_attendance_df=missing_attendance_df,
        under_target_df=under_target_df,
        joker_usage_df=joker_usage_df,
        safe_int_fn=safe_int,
        fmt_number_fn=fmt_number,
        render_alert_stack_fn=render_alert_stack,
        render_dashboard_data_grid_fn=render_dashboard_data_grid,
        render_dashboard_section_header_fn=render_dashboard_section_header,
    )
    render_dashboard_finance_and_hygiene_sections(
        month_revenue=month_revenue,
        month_operation_gap=month_operation_gap,
        shared_overhead_total=shared_overhead_total,
        top_profit_items=top_profit_items,
        risk_items=risk_items,
        missing_personnel_df=missing_personnel_df,
        missing_restaurant_df=missing_restaurant_df,
        render_dashboard_section_header_fn=render_dashboard_section_header,
        render_record_snapshot_fn=render_record_snapshot,
        render_dashboard_data_grid_fn=render_dashboard_data_grid,
        fmt_try_fn=fmt_try,
    )


def restaurants_tab(conn: sqlite3.Connection) -> None:
    df = fetch_df(conn, "SELECT * FROM restaurants ORDER BY brand, branch")
    df = ensure_dataframe_columns(df, {
        "company_title": "",
        "address": "",
        "contact_name": "",
        "contact_phone": "",
        "contact_email": "",
        "tax_office": "",
        "tax_number": "",
    })
    render_management_hero(
        "RESTORAN YÖNETİMİ",
        "Şube kartları, fiyat anlaşmaları ve operasyon durumu",
        "Filtrelenebilir liste, hızlı aksiyon paneli ve tüm fiyat modeli dağılımını aynı alanda net biçimde görerek yeni şube ekleme ya da güncelleme işlemlerini daha rahat yönet.",
        build_restaurant_hero_stats(df, safe_int_fn=safe_int),
    )
    render_flash_message()

    workspace_key = "restaurant_workspace_mode"
    if workspace_key not in st.session_state:
        st.session_state[workspace_key] = "add"

    c1, c2, c3 = st.columns(3)
    with c1:
        render_action_card("Yeni Şube Oluştur", "Yeni restoran ya da yeni şube açılışını ana form üzerinden başlat.", highlight=st.session_state[workspace_key] == "add")
        if st.button("Yeni Şube Formunu Aç", key="restaurant_workspace_add", use_container_width=True):
            st.session_state[workspace_key] = "add"
    with c2:
        render_action_card("Şube Listesini Gör", "Tüm restoran kartlarını filtrele, ara ve seçili kayıt üzerinde işlem yap.", highlight=st.session_state[workspace_key] == "list")
        if st.button("Listeyi Aç", key="restaurant_workspace_list", use_container_width=True):
            st.session_state[workspace_key] = "list"
    with c3:
        render_action_card("Şube Kartını Güncelle", "Mevcut anlaşmaları, fiyatları ve iletişim bilgilerini düzenle.", highlight=st.session_state[workspace_key] == "edit")
        if st.button("Güncelleme Alanını Aç", key="restaurant_workspace_edit", use_container_width=True):
            st.session_state[workspace_key] = "edit"

    workspace_mode = st.session_state[workspace_key]

    if workspace_mode == "list":
        render_restaurant_list_workspace(
            conn,
            df,
            pricing_model_labels=PRICING_MODEL_LABELS,
            active_status_labels=ACTIVE_STATUS_LABELS,
            safe_int_fn=safe_int,
            fmt_number_fn=fmt_number,
            apply_text_search_fn=apply_text_search,
            build_restaurant_list_rows_fn=build_restaurant_list_rows,
            build_restaurant_snapshot_items_fn=build_restaurant_snapshot_items,
            render_tab_header_fn=render_tab_header,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            render_record_snapshot_fn=render_record_snapshot,
            set_flash_message_fn=set_flash_message,
            first_row_value_fn=first_row_value,
        )

    elif workspace_mode == "add":
        render_restaurant_add_workspace(
            conn,
            pricing_model_labels=PRICING_MODEL_LABELS,
            render_tab_header_fn=render_tab_header,
            render_field_label_fn=render_field_label,
            validate_restaurant_form_fn=validate_restaurant_form,
            set_flash_message_fn=set_flash_message,
        )

    else:
        render_restaurant_edit_workspace(
            conn,
            df,
            pricing_model_labels=PRICING_MODEL_LABELS,
            active_status_labels=ACTIVE_STATUS_LABELS,
            safe_int_fn=safe_int,
            safe_float_fn=safe_float,
            validate_restaurant_form_fn=validate_restaurant_form,
            render_tab_header_fn=render_tab_header,
            render_field_label_fn=render_field_label,
            render_record_snapshot_fn=render_record_snapshot,
            set_flash_message_fn=set_flash_message,
        )


def personnel_tab(conn: sqlite3.Connection) -> None:
    personnel_payload = load_personnel_workspace_payload(
        conn,
        recently_created_payload=st.session_state.get("personnel_recently_created"),
        ensure_dataframe_columns_fn=ensure_dataframe_columns,
        safe_int_fn=safe_int,
        get_row_value_fn=get_row_value,
        auto_motor_rental_deduction=AUTO_MOTOR_RENTAL_DEDUCTION,
        auto_motor_purchase_monthly_deduction=AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
        auto_motor_purchase_installment_count=AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT,
    )
    df = personnel_payload.df
    rest_opts = personnel_payload.rest_opts
    rest_opts_with_blank = personnel_payload.rest_opts_with_blank
    passive_count = personnel_payload.passive_count

    render_management_hero(
        "PERSONEL YÖNETİMİ",
        "Kurye, yönetim ve operasyon kartları",
        "Filtrelenebilir personel listesi, daha belirgin sekmeler ve düzenli kart yapısı ile yeni personel ekleme ve düzenleme akışlarını sadeleştir.",
        build_personnel_hero_stats(df, management_role_options=MANAGEMENT_ROLE_OPTIONS),
    )
    render_flash_message()
    create_success_message = str(st.session_state.get("personnel_create_success_message", "") or "").strip()

    recently_created_id = personnel_payload.recently_created_id

    if recently_created_id > 0 and not df.empty:
        recent_match = df[df["id"] == recently_created_id]
        if not recent_match.empty:
            recent_row = recent_match.iloc[0]
            render_record_snapshot(
                "Son Eklenen Personel",
                build_personnel_recent_snapshot_items(
                    recent_row,
                    motor_rental_summary_fn=format_motor_rental_summary,
                    motor_purchase_summary_fn=format_motor_purchase_summary,
                ),
            )
        else:
            st.session_state.pop("personnel_recently_created", None)
            st.session_state.pop("personnel_create_success_message", None)

    if passive_count:
        st.caption(f"Pasif personel sayısı: {passive_count}")

    workspace_key = "personnel_workspace_mode"
    if workspace_key not in st.session_state:
        st.session_state[workspace_key] = "add"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_action_card("Yeni Personel Ekle", "Kurye, yönetim ya da operasyon kartını görünür ana form üzerinden oluştur.", highlight=st.session_state[workspace_key] == "add")
        if st.button("Yeni Personel Formunu Aç", key="personnel_workspace_add", use_container_width=True):
            st.session_state.pop("personnel_create_success_message", None)
            st.session_state.pop("personnel_recently_created", None)
            st.session_state[workspace_key] = "add"
    with c2:
        render_action_card("Personel Listesi", "Tüm kayıtları filtrele, ara ve seçili personeli tek bakışta incele.", highlight=st.session_state[workspace_key] == "list")
        if st.button("Listeyi Aç", key="personnel_workspace_list", use_container_width=True):
            st.session_state.pop("personnel_create_success_message", None)
            st.session_state.pop("personnel_recently_created", None)
            st.session_state[workspace_key] = "list"
    with c3:
        render_action_card("Personel Düzenle", "Kart bilgilerini, görev rolünü ve maliyet ayarlarını güncelle.", highlight=st.session_state[workspace_key] == "edit")
        if st.button("Düzenleme Alanını Aç", key="personnel_workspace_edit", use_container_width=True):
            st.session_state.pop("personnel_create_success_message", None)
            st.session_state.pop("personnel_recently_created", None)
            st.session_state[workspace_key] = "edit"
    with c4:
        render_action_card("Plaka / Motor", "Araç, plaka ve zimmet geçmişini ayrı çalışma alanında yönet.", highlight=st.session_state[workspace_key] == "plate")
        if st.button("Plaka Alanını Aç", key="personnel_workspace_plate", use_container_width=True):
            st.session_state.pop("personnel_create_success_message", None)
            st.session_state.pop("personnel_recently_created", None)
            st.session_state[workspace_key] = "plate"

    workspace_mode = st.session_state[workspace_key]

    if workspace_mode == "list":
        render_personnel_list_workspace(
            df,
            recently_created_id=recently_created_id,
            personnel_role_options=PERSONNEL_ROLE_OPTIONS,
            apply_text_search_fn=apply_text_search,
            build_personnel_preview_options_fn=build_personnel_preview_options,
            build_personnel_list_rows_fn=build_personnel_list_rows,
            build_personnel_preview_snapshot_items_fn=build_personnel_preview_snapshot_items,
            format_motor_rental_summary_fn=format_motor_rental_summary,
            format_motor_purchase_summary_fn=format_motor_purchase_summary,
            render_tab_header_fn=render_tab_header,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            render_record_snapshot_fn=render_record_snapshot,
        )

    elif workspace_mode == "add":
        render_personnel_add_workspace(
            conn,
            df,
            recently_created_id=recently_created_id,
            workspace_key=workspace_key,
            rest_opts_with_blank=rest_opts_with_blank,
            personnel_role_options=PERSONNEL_ROLE_OPTIONS,
            motor_usage_mode_options=MOTOR_USAGE_MODE_OPTIONS,
            motor_purchase_commitment_options=MOTOR_PURCHASE_COMMITMENT_OPTIONS,
            equipment_items=EQUIPMENT_ITEMS,
            cost_model_labels=COST_MODEL_LABELS,
            auto_motor_rental_deduction=AUTO_MOTOR_RENTAL_DEDUCTION,
            auto_motor_purchase_monthly_deduction=AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
            auto_motor_purchase_installment_count=AUTO_MOTOR_PURCHASE_INSTALLMENT_COUNT,
            render_tab_header_fn=render_tab_header,
            render_record_snapshot_fn=render_record_snapshot,
            build_personnel_recent_snapshot_items_fn=build_personnel_recent_snapshot_items,
            format_motor_rental_summary_fn=format_motor_rental_summary,
            format_motor_purchase_summary_fn=format_motor_purchase_summary,
            render_field_label_fn=render_field_label,
            role_requires_primary_restaurant_fn=role_requires_primary_restaurant,
            resolve_cost_role_option_fn=resolve_cost_role_option,
            is_fixed_cost_model_fn=is_fixed_cost_model,
            get_role_fixed_cost_label_fn=get_role_fixed_cost_label,
            next_person_code_fn=next_person_code,
            clear_new_person_onboarding_state_fn=clear_new_person_onboarding_state,
            initialize_onboarding_equipment_state_fn=initialize_onboarding_equipment_state,
            onboarding_equipment_state_key_fn=onboarding_equipment_state_key,
            collect_onboarding_equipment_payloads_fn=collect_onboarding_equipment_payloads,
            validate_onboarding_equipment_payloads_fn=validate_onboarding_equipment_payloads,
            build_motor_usage_payload_fn=build_motor_usage_payload,
            render_motor_deduction_snapshot_from_payload_fn=render_motor_deduction_snapshot_from_payload,
            render_motor_purchase_proration_caption_fn=render_motor_purchase_proration_caption,
            get_equipment_cost_snapshot_fn=get_equipment_cost_snapshot,
            validate_personnel_form_fn=validate_personnel_form,
            safe_int_fn=safe_int,
            safe_float_fn=safe_float,
            fmt_number_fn=fmt_number,
            fmt_try_fn=fmt_try,
            normalize_cost_model_value_fn=normalize_cost_model_value,
            insert_equipment_issue_and_get_id_fn=insert_equipment_issue_and_get_id,
            post_equipment_installments_fn=post_equipment_installments,
            sync_person_current_role_snapshot_fn=sync_person_current_role_snapshot,
            sync_person_business_rules_fn=sync_person_business_rules,
            set_flash_message_fn=set_flash_message,
        )

    elif workspace_mode == "edit":
        render_personnel_edit_workspace(
            conn,
            df,
            rest_opts=rest_opts,
            rest_opts_with_blank=rest_opts_with_blank,
            personnel_role_options=PERSONNEL_ROLE_OPTIONS,
            motor_usage_mode_options=MOTOR_USAGE_MODE_OPTIONS,
            motor_purchase_commitment_options=MOTOR_PURCHASE_COMMITMENT_OPTIONS,
            issue_items=ISSUE_ITEMS,
            cost_model_labels=COST_MODEL_LABELS,
            auto_motor_rental_deduction=AUTO_MOTOR_RENTAL_DEDUCTION,
            auto_motor_purchase_monthly_deduction=AUTO_MOTOR_PURCHASE_MONTHLY_DEDUCTION,
            render_tab_header_fn=render_tab_header,
            fetch_df_fn=fetch_df,
            parse_date_value_fn=parse_date_value,
            resolve_vehicle_type_value_fn=resolve_vehicle_type_value,
            resolve_motor_usage_mode_fn=resolve_motor_usage_mode,
            initialize_edit_person_transition_state_fn=initialize_edit_person_transition_state,
            role_requires_primary_restaurant_fn=role_requires_primary_restaurant,
            format_motor_rental_summary_fn=format_motor_rental_summary,
            format_motor_purchase_summary_fn=format_motor_purchase_summary,
            resolve_cost_role_option_fn=resolve_cost_role_option,
            format_display_df_fn=format_display_df,
            render_record_snapshot_fn=render_record_snapshot,
            render_field_label_fn=render_field_label,
            resolve_effective_role_from_transition_fn=resolve_effective_role_from_transition,
            is_fixed_cost_model_fn=is_fixed_cost_model,
            get_role_fixed_cost_label_fn=get_role_fixed_cost_label,
            next_person_code_fn=next_person_code,
            role_code_prefix_fn=role_code_prefix,
            build_motor_usage_payload_fn=build_motor_usage_payload,
            render_vehicle_transition_caption_fn=render_vehicle_transition_caption,
            render_motor_purchase_proration_caption_fn=render_motor_purchase_proration_caption,
            render_motor_deduction_snapshot_from_payload_fn=render_motor_deduction_snapshot_from_payload,
            safe_float_fn=safe_float,
            safe_int_fn=safe_int,
            validate_personnel_form_fn=validate_personnel_form,
            validate_role_transition_inputs_fn=validate_role_transition_inputs,
            normalize_cost_model_value_fn=normalize_cost_model_value,
            record_person_role_transition_fn=record_person_role_transition,
            sync_person_current_role_snapshot_fn=sync_person_current_role_snapshot,
            record_person_vehicle_transition_fn=record_person_vehicle_transition,
            sync_person_current_vehicle_snapshot_fn=sync_person_current_vehicle_snapshot,
            sync_person_business_rules_fn=sync_person_business_rules,
            set_flash_message_fn=set_flash_message,
            get_personnel_dependency_counts_fn=get_personnel_dependency_counts,
            delete_personnel_and_dependencies_fn=delete_personnel_and_dependencies,
            get_equipment_cost_snapshot_fn=get_equipment_cost_snapshot,
            get_default_equipment_unit_cost_fn=get_default_equipment_unit_cost,
            get_default_equipment_sale_price_fn=get_default_equipment_sale_price,
            get_default_issue_installment_count_fn=get_default_issue_installment_count,
            latest_average_cost_fn=latest_average_cost,
            get_equipment_vat_rate_fn=get_equipment_vat_rate,
            fmt_number_fn=fmt_number,
            fmt_try_fn=fmt_try,
            normalize_equipment_issue_installment_count_fn=normalize_equipment_issue_installment_count,
            equipment_issue_generates_installments_fn=equipment_issue_generates_installments,
            insert_equipment_issue_and_get_id_fn=insert_equipment_issue_and_get_id,
            post_equipment_installments_fn=post_equipment_installments,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            update_equipment_issue_record_fn=update_equipment_issue_record,
            delete_equipment_issue_records_fn=delete_equipment_issue_records,
        )

    else:
        render_personnel_plate_workspace(
            conn,
            get_person_options_fn=get_person_options,
            fetch_df_fn=fetch_df,
            safe_int_fn=safe_int,
            format_display_df_fn=format_display_df,
            render_tab_header_fn=render_tab_header,
        )

def attendance_tab(conn: sqlite3.Connection) -> None:
    today_value = date.today()
    month_start = today_value.replace(day=1).isoformat()
    today_count = int(first_row_value(conn.execute("SELECT COUNT(*) FROM daily_entries WHERE entry_date = ?", (today_value.isoformat(),)).fetchone(), 0) or 0)
    month_count = int(first_row_value(conn.execute("SELECT COUNT(*) FROM daily_entries WHERE entry_date BETWEEN ? AND ?", (month_start, today_value.isoformat())).fetchone(), 0) or 0)
    total_count = int(first_row_value(conn.execute("SELECT COUNT(*) FROM daily_entries").fetchone(), 0) or 0)
    active_restaurants = int(first_row_value(conn.execute("SELECT COUNT(*) FROM restaurants WHERE active=1").fetchone(), 0) or 0)

    render_management_hero(
        "PUANTAJ",
        "Günlük ve toplu giriş akışları",
        "Tek menü altında günlük puantaj ve toplu puantaj ekranlarını aç; operasyon ekibi için daha temiz bir giriş alanı kullan.",
        [
            ("Toplam Kayıt", total_count),
            ("Bugünkü Kayıt", today_count),
            ("Bu Ay Kayıt", month_count),
            ("Aktif Restoran", active_restaurants),
        ],
    )

    workspace_key = "attendance_workspace_mode"
    if workspace_key not in st.session_state:
        st.session_state[workspace_key] = "daily"

    c1, c2 = st.columns(2)
    with c1:
        render_action_card("Günlük Puantaj", "Şube, saat, paket ve fiilen çalışan personel bilgisini tek kayıt olarak gir.", highlight=st.session_state[workspace_key] == "daily")
        if st.button("Günlük Alanını Aç", key="attendance_workspace_daily", use_container_width=True):
            st.session_state[workspace_key] = "daily"
    with c2:
        render_action_card("Toplu Puantaj", "Bir şubedeki çoklu personel kaydını tablo halinde veya WhatsApp metniyle içeri al.", highlight=st.session_state[workspace_key] == "bulk")
        if st.button("Toplu Alanı Aç", key="attendance_workspace_bulk", use_container_width=True):
            st.session_state[workspace_key] = "bulk"

    if st.session_state[workspace_key] == "daily":
        render_tab_header("Günlük Puantaj", "Şube bazlı tekil puantaj kayıtlarını gir, düzelt ve yönet.")
        daily_entries_tab(conn)
    else:
        render_tab_header("Toplu Puantaj", "Aynı gün içinde çoklu personel kayıtlarını tablo veya metin aktarımıyla yönet.")
        toplu_puantaj_tab(conn)


def daily_entries_tab(conn: sqlite3.Connection) -> None:
    status_options = ["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"]
    st.subheader("Günlük Puantaj | Saat, paket ve fiilen çalışan personel kaydı")
    st.caption("WhatsApp teyidi sonrası şube bazlı günlük saat ve paket girişlerini bu ekrandan yap.")
    rest_opts = get_restaurant_options(conn)
    person_opts = get_person_options(conn)
    with st.form("daily_entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        entry_date = c1.date_input("Tarih", value=date.today())
        rest_label = c2.selectbox("Restoran / şube", list(rest_opts.keys()))
        status = c3.selectbox("Durum", status_options)
        c4, c5 = st.columns(2)
        planned_label = c4.selectbox("Planlanan personel", ["-"] + list(person_opts.keys()))
        actual_label = c5.selectbox("Fiilen çalışan personel", ["-"] + list(person_opts.keys()))
        c6, c7 = st.columns(2)
        worked_hours = c6.number_input("Çalışılan saat", min_value=0.0, value=10.0, step=0.5)
        package_count = c7.number_input("Paket", min_value=0.0, value=0.0, step=1.0)
        notes = st.text_area("Not")
        submitted = st.form_submit_button("Kaydet", use_container_width=True)
        if submitted:
            planned_id = person_opts[planned_label] if planned_label != "-" else None
            actual_id = person_opts[actual_label] if actual_label != "-" else None
            conn.execute(
                """
                INSERT INTO daily_entries (
                    entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
                    status, worked_hours, package_count, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_date.isoformat(), rest_opts[rest_label], planned_id, actual_id, status, worked_hours, package_count, notes),
            )
            conn.commit()
            sync_personnel_business_rules_for_ids(conn, [actual_id], create_onboarding=False, full_history=True)
            st.success("Günlük kayıt eklendi.")
            st.rerun()

    st.markdown("### Günlük kayıtları yönet")
    q = """
    SELECT d.id, d.entry_date, r.brand || ' - ' || r.branch AS restoran,
           COALESCE(pp.full_name, '-') AS planlanan, COALESCE(ap.full_name, '-') AS calisan,
           d.status, d.worked_hours, d.package_count, COALESCE(d.notes, '') AS notes
    FROM daily_entries d
    JOIN restaurants r ON r.id = d.restaurant_id
    LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
    LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
    ORDER BY d.entry_date DESC, restoran, d.id DESC
    LIMIT 500
    """
    df = fetch_df(conn, q)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        entry_map = {
            f"{row['entry_date']} | {row['restoran']} | {row['calisan']} | {row['package_count']} paket | ID:{row['id']}": int(row["id"])
            for _, row in df.iterrows()
        }

        st.markdown("#### Kayıt düzelt / sil")
        selected_label = st.selectbox("Düzeltmek veya silmek istediğin kaydı seç", list(entry_map.keys()), key="daily_entry_manage_select")
        selected_id = entry_map[selected_label]
        selected = conn.execute(
            """
            SELECT id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
                   status, worked_hours, package_count, COALESCE(notes, '') AS notes
            FROM daily_entries
            WHERE id = ?
            """,
            (selected_id,),
        ).fetchone()

        current_rest_label = next((label for label, rid in rest_opts.items() if rid == selected["restaurant_id"]), list(rest_opts.keys())[0])
        planned_default = "-"
        actual_default = "-"
        for label, pid in person_opts.items():
            if selected["planned_personnel_id"] == pid:
                planned_default = label
            if selected["actual_personnel_id"] == pid:
                actual_default = label

        with st.form(f"daily_entry_edit_form_{selected_id}"):
            e1, e2, e3 = st.columns(3)
            edit_date = e1.date_input("Tarih", value=datetime.fromisoformat(selected["entry_date"]).date())
            rest_labels = list(rest_opts.keys())
            edit_rest_label = e2.selectbox("Restoran / şube", rest_labels, index=rest_labels.index(current_rest_label))
            edit_status = e3.selectbox(
                "Durum",
                status_options,
                index=status_options.index(selected["status"]) if selected["status"] in status_options else 0,
            )
            e4, e5 = st.columns(2)
            person_labels = ["-"] + list(person_opts.keys())
            edit_planned_label = e4.selectbox("Planlanan personel", person_labels, index=person_labels.index(planned_default))
            edit_actual_label = e5.selectbox("Fiilen çalışan personel", person_labels, index=person_labels.index(actual_default))
            e6, e7 = st.columns(2)
            edit_hours = e6.number_input("Çalışılan saat", min_value=0.0, value=float(selected["worked_hours"] or 0), step=0.5)
            edit_package = e7.number_input("Paket", min_value=0.0, value=float(selected["package_count"] or 0), step=1.0)
            edit_notes = st.text_area("Not", value=selected["notes"])
            u1, u2 = st.columns(2)
            update_clicked = u1.form_submit_button("Kaydı güncelle", use_container_width=True)
            delete_clicked = u2.form_submit_button("Kaydı sil", use_container_width=True)

            if update_clicked:
                previous_actual_id = safe_int(selected["actual_personnel_id"], 0)
                planned_id = person_opts[edit_planned_label] if edit_planned_label != "-" else None
                actual_id = person_opts[edit_actual_label] if edit_actual_label != "-" else None
                conn.execute(
                    """
                    UPDATE daily_entries
                    SET entry_date = ?, restaurant_id = ?, planned_personnel_id = ?, actual_personnel_id = ?,
                        status = ?, worked_hours = ?, package_count = ?, notes = ?
                    WHERE id = ?
                    """,
                    (
                        edit_date.isoformat(),
                        rest_opts[edit_rest_label],
                        planned_id,
                        actual_id,
                        edit_status,
                        edit_hours,
                        edit_package,
                        edit_notes,
                        selected_id,
                    ),
                )
                conn.commit()
                sync_personnel_business_rules_for_ids(conn, [previous_actual_id, actual_id], create_onboarding=False, full_history=True)
                st.success("Günlük puantaj kaydı güncellendi.")
                st.rerun()

            if delete_clicked:
                deleted_actual_id = safe_int(selected["actual_personnel_id"], 0)
                conn.execute("DELETE FROM daily_entries WHERE id = ?", (selected_id,))
                conn.commit()
                sync_personnel_business_rules_for_ids(conn, [deleted_actual_id], create_onboarding=False, full_history=True)
                st.success("Günlük puantaj kaydı silindi.")
                st.rerun()
    else:
        st.info("Henüz günlük puantaj kaydı yok.")


def deductions_tab(conn: sqlite3.Connection) -> None:
    section_intro("💸 Kesinti Yönetimi | Motor kira, bakım, yakıt, HGS, ceza, muhasebe ve şirket açılış ücretleri", "Personel bazlı düşülecek tutarları buradan manuel kaydet ve yönet.")
    person_opts = get_person_options(conn, active_only=False)
    deduction_types = ["Bakım", "Yakıt", "HGS", "İdari ceza", "Hasar", "Fatura Edilmeyen Tutar"]

    with st.form("deduction_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        person_label = c1.selectbox("Personel", list(person_opts.keys()))
        ded_date = c2.date_input("Tarih", value=date.today())
        ded_type = c3.selectbox("Kesinti türü", deduction_types)
        amount = st.number_input("Tutar", min_value=0.0, value=0.0, step=50.0)
        notes = st.text_input("Açıklama")
        submitted = st.form_submit_button("Kesinti ekle", use_container_width=True)
        if submitted and amount > 0:
            deduction_due_date = normalize_deduction_date(ded_date)
            conn.execute(
                "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes) VALUES (?, ?, ?, ?, ?)",
                (person_opts[person_label], deduction_due_date.isoformat(), ded_type, amount, notes),
            )
            conn.commit()
            st.success(f"Kesinti ay sonuna kaydedildi: {deduction_due_date.isoformat()}")
            st.rerun()

    st.caption("Girilen kesinti hangi aya aitse, kayıt o ayın son gününe yazılır ve hakedişten ay sonu düşülür.")

    raw_df = fetch_df(
        conn,
        """
        SELECT d.id, d.personnel_id, d.deduction_date, p.full_name AS personel, d.deduction_type, d.amount, d.notes, d.auto_source_key
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        ORDER BY d.deduction_date DESC, d.id DESC
        """,
    )
    raw_df["source_text"] = raw_df["auto_source_key"].apply(describe_auto_source_key) if not raw_df.empty else []
    source_filter = st.selectbox("Kesinti Kaynağı", DEDUCTION_SOURCE_FILTER_OPTIONS, key="deduction_source_filter")
    filtered_raw_df = filter_deductions_by_source(raw_df, source_filter)
    source_filter_caption = get_deduction_source_filter_caption(source_filter)
    if source_filter_caption:
        st.caption(source_filter_caption)
    deductions_display_df = format_display_df(
        filtered_raw_df.drop(columns=["id", "personnel_id", "auto_source_key"], errors="ignore"),
        currency_cols=["Tutar"],
        rename_map={
            "deduction_date": "Tarih",
            "personel": "Personel",
            "deduction_type": "Kesinti Türü",
            "amount": "Tutar",
            "source_text": "Kaynak",
            "notes": "Açıklama",
        },
    )
    deduction_rows = build_deduction_grid_rows(deductions_display_df)
    render_dashboard_data_grid(
        "Kesinti Listesi",
        "Manuel ve sistem kaynaklı kesintileri daha düzenli satırlarda izle.",
        ["Tarih", "Personel", "Tür", "Tutar", "Kaynak", "Açıklama"],
        deduction_rows,
        "Henüz kesinti kaydı yok.",
        muted_columns={"Kaynak", "Açıklama"},
    )

    st.markdown("### Toplu kesinti sil")
    manual_deductions_df = raw_df[raw_df["auto_source_key"].fillna("").astype(str).str.strip() == ""].copy() if not raw_df.empty else pd.DataFrame()
    if manual_deductions_df.empty:
        st.info("Toplu silme için uygun manuel kesinti kaydı görünmüyor.")
    else:
        bulk_deduction_options = build_bulk_deduction_option_map(manual_deductions_df, fmt_try_fn=fmt_try)
        selected_bulk_deduction_labels = st.multiselect(
            "Toplu silinecek kesinti kayıtları",
            list(bulk_deduction_options.keys()),
            key="bulk_deduction_delete_select",
        )
        if st.button("Seçili Kesintileri Toplu Sil", use_container_width=True, key="bulk_deduction_delete_button"):
            selected_bulk_deduction_ids = [bulk_deduction_options[label] for label in selected_bulk_deduction_labels]
            if not selected_bulk_deduction_ids:
                st.error("Önce en az bir manuel kesinti kaydı seçmelisin.")
            else:
                placeholders = ", ".join(["?"] * len(selected_bulk_deduction_ids))
                conn.execute(
                    f"DELETE FROM deductions WHERE id IN ({placeholders})",
                    tuple(selected_bulk_deduction_ids),
                )
                conn.commit()
                st.success(f"{len(selected_bulk_deduction_ids)} manuel kesinti kaydı toplu olarak silindi.")
                st.rerun()

    st.markdown("### Kesinti düzenle / sil")
    if raw_df.empty:
        st.info("Henüz kesinti kaydı yok.")
        return

    deduction_options = build_deduction_option_map(raw_df, fmt_try_fn=fmt_try)
    selected_label = st.selectbox("Kayıt seç", list(deduction_options.keys()))
    selected_id = deduction_options[selected_label]
    row = raw_df.loc[raw_df["id"] == selected_id].iloc[0]

    reverse_person = {v: k for k, v in person_opts.items()}
    current_person = reverse_person.get(int(row["personnel_id"]), list(person_opts.keys())[0])
    person_index = list(person_opts.keys()).index(current_person) if current_person in person_opts else 0
    type_index = deduction_types.index(row["deduction_type"]) if row["deduction_type"] in deduction_types else len(deduction_types) - 1
    current_date = datetime.strptime(str(row["deduction_date"]), "%Y-%m-%d").date()
    is_auto_record = is_system_personnel_auto_deduction_key(row.get("auto_source_key"))
    if is_auto_record:
        st.warning(
            build_auto_deduction_warning_text(
                row.get("auto_source_key"),
                describe_auto_source_key_fn=describe_auto_source_key,
            )
        )

    with st.form("deduction_edit_form"):
        c1, c2, c3 = st.columns(3)
        edit_person = c1.selectbox("Personel", list(person_opts.keys()), index=person_index)
        edit_date = c2.date_input("Tarih", value=current_date)
        edit_type = c3.selectbox("Kesinti türü", deduction_types, index=type_index)
        edit_amount = st.number_input("Tutar", min_value=0.0, value=safe_float(row["amount"]), step=50.0)
        edit_notes = st.text_input("Açıklama", value=row["notes"] or "")
        c4, c5 = st.columns(2)
        update_clicked = c4.form_submit_button("Kesinti güncelle", use_container_width=True, disabled=is_auto_record)
        delete_clicked = c5.form_submit_button("Kesinti sil", use_container_width=True, disabled=is_auto_record)

        if update_clicked and edit_amount > 0:
            deduction_due_date = normalize_deduction_date(edit_date)
            conn.execute(
                """
                UPDATE deductions
                SET personnel_id = ?, deduction_date = ?, deduction_type = ?, amount = ?, notes = ?
                WHERE id = ?
                """,
                (person_opts[edit_person], deduction_due_date.isoformat(), edit_type, edit_amount, edit_notes, selected_id),
            )
            conn.commit()
            st.success(f"Kesinti ay sonuna güncellendi: {deduction_due_date.isoformat()}")
            st.rerun()

        if delete_clicked:
            conn.execute("DELETE FROM deductions WHERE id = ?", (selected_id,))
            conn.commit()
            st.success("Kesinti silindi.")
            st.rerun()


def toplu_puantaj_tab(conn: sqlite3.Connection) -> None:
    section_intro("🗂 Toplu Puantaj | Şube bazlı hızlı satır girişi ve WhatsApp metni aktarımı", "Bir şubedeki birden fazla kurye için saat, paket ve durumu Excel gibi tek ekranda gir. İstersen WhatsApp metnini yapıştırıp tabloya aktar.")

    restaurant_opts = get_restaurant_options(conn)
    if not restaurant_opts:
        st.info("Önce en az bir aktif restoran tanımlayın.")
        return

    today = date.today()
    c1, c2, c3 = st.columns([1, 2, 1])
    selected_date = c1.date_input("Tarih", value=today, key="bulk_date")
    restaurant_label = c2.selectbox("Restoran / Şube", list(restaurant_opts.keys()), key="bulk_restaurant")
    include_all_active = c3.checkbox("Tüm aktif personeli göster", value=False, key="bulk_all_people")
    restaurant_id = restaurant_opts[restaurant_label]

    people_rows = conn.execute(
        """
        SELECT id, full_name, role
        FROM personnel
        WHERE status='Aktif'
          AND (? = 1 OR assigned_restaurant_id = ? OR role IN ('Joker', 'Bölge Müdürü', 'Saha Denetmen Şefi', 'Restoran Takım Şefi'))
        ORDER BY
            CASE
                WHEN role='Restoran Takım Şefi' THEN 1
                WHEN role='Saha Denetmen Şefi' THEN 2
                WHEN role='Bölge Müdürü' THEN 3
                WHEN role='Joker' THEN 4
                ELSE 5
            END,
            full_name
        """,
        (1 if include_all_active else 0, restaurant_id),
    ).fetchall()

    person_label_map = {f"{r['full_name']} ({r['role']})": r["id"] for r in people_rows}
    name_to_label = {r["full_name"].strip().lower(): f"{r['full_name']} ({r['role']})" for r in people_rows}

    if "bulk_editor_rows" not in st.session_state:
        st.session_state.bulk_editor_rows = None

    if st.session_state.bulk_editor_rows:
        default_rows = st.session_state.bulk_editor_rows
    else:
        default_rows = [
            {
                "Personel": label,
                "Saat": 0.0,
                "Paket": 0,
                "Durum": "Normal",
                "Not": "",
            }
            for label in person_label_map.keys()
        ]

    with st.expander("WhatsApp metninden tablo oluştur", expanded=False):
        st.caption("Örnek satır formatı: Ali Yılmaz - 10 saat - 38 paket - Normal")
        raw_text = st.text_area("Mesajı yapıştır", height=160, key="bulk_whatsapp_text")
        if st.button("Metni tabloya aktar", key="bulk_parse_btn", use_container_width=True):
            parsed = parse_whatsapp_bulk(raw_text)
            rows = []
            for row in parsed:
                guess = name_to_label.get(str(row["person_label"]).strip().lower())
                rows.append(
                    {
                        "Personel": guess or row["person_label"],
                        "Saat": float(row["worked_hours"] or 0),
                        "Paket": int(row["package_count"] or 0),
                        "Durum": normalize_entry_status(row["entry_status"] or "Normal"),
                        "Not": row.get("notes", ""),
                    }
                )
            if rows:
                st.session_state.bulk_editor_rows = rows
                st.success(f"{len(rows)} satır tabloya aktarıldı. Kaydetmeden önce düzenleyebilirsin.")
                st.rerun()
            else:
                st.warning("Okunabilir bir satır bulunamadı. Örnek formatı kullanmayı dene.")

    st.markdown("#### Şube bazlı toplu giriş")
    editor_df = pd.DataFrame(default_rows)
    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="bulk_editor",
        column_config={
            "Personel": st.column_config.SelectboxColumn("Personel", options=list(person_label_map.keys()), required=False),
            "Saat": st.column_config.NumberColumn("Saat", min_value=0.0, max_value=24.0, step=0.5, format="%.1f"),
            "Paket": st.column_config.NumberColumn("Paket", min_value=0, step=1),
            "Durum": st.column_config.SelectboxColumn("Durum", options=["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"]),
            "Not": st.column_config.TextColumn("Not"),
        },
    )

    csave, cclear = st.columns([1, 1])
    if csave.button("Tümünü Kaydet", key="bulk_save_btn", use_container_width=True):
        inserted = 0
        affected_person_ids = []
        for _, row in edited_df.iterrows():
            person_label = str(row.get("Personel", "")).strip()
            if not person_label or person_label not in person_label_map:
                continue
            hours = float(row.get("Saat") or 0)
            packages = int(row.get("Paket") or 0)
            status = normalize_entry_status(str(row.get("Durum") or "Normal").strip())
            notes = str(row.get("Not") or "").strip()
            if hours == 0 and packages == 0 and status == "Normal":
                continue
            person_id = person_label_map[person_label]
            note_parts = [part for part in [notes, "Kaynak: Toplu Puantaj", f"Kaydeden: {st.session_state.get('username', 'sistem')}"] if part]
            conn.execute(
                """
                INSERT INTO daily_entries (
                    entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
                    status, worked_hours, package_count, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    selected_date.isoformat(),
                    restaurant_id,
                    person_id,
                    person_id,
                    status,
                    hours,
                    packages,
                    " | ".join(note_parts),
                ),
            )
            inserted += 1
            affected_person_ids.append(person_id)
        conn.commit()
        sync_personnel_business_rules_for_ids(conn, affected_person_ids, create_onboarding=False, full_history=True)
        st.session_state.bulk_editor_rows = None
        st.success(f"{inserted} satır kaydedildi.")
        st.rerun()

    if cclear.button("Tabloyu Sıfırla", key="bulk_clear_btn", use_container_width=True):
        st.session_state.bulk_editor_rows = None
        st.rerun()


EQUIPMENT_ITEMS = [
    "Box",
    "Punch",
    "Polar",
    "Tişört",
    "Korumalı Mont",
    "Yelek",
    "Reflektörlü Yelek",
    "Yağmurluk",
    "Göğüs Çantası",
    "Kask",
    "Telefon Tutacağı",
]

PURCHASE_ITEMS = [
    *EQUIPMENT_ITEMS,
    "Motor Bakım",
]

ISSUE_ITEMS = [
    *EQUIPMENT_ITEMS,
    "Motor Kirası",
    "Motor Satın Alım",
]

NON_RETURNABLE_ITEMS = {
    "Polar",
    "Tişört",
    "Korumalı Mont",
    "Yelek",
    "Reflektörlü Yelek",
    "Yağmurluk",
    "Göğüs Çantası",
    "Kask",
    "Telefon Tutacağı",
    "Motor Kirası",
    "Motor Satın Alım",
}

configure_form_rules(
    safe_int_fn=safe_int,
    safe_float_fn=safe_float,
    fmt_try_fn=fmt_try,
    render_record_snapshot_fn=render_record_snapshot,
    resolve_motor_usage_fields_fn=resolve_motor_usage_fields,
    resolve_motor_rental_value_fn=resolve_motor_rental_value,
    role_requires_primary_restaurant_fn=role_requires_primary_restaurant,
    is_fixed_cost_model_fn=is_fixed_cost_model,
    get_equipment_vat_rate_fn=get_equipment_vat_rate,
    get_default_equipment_sale_price_fn=get_default_equipment_sale_price,
    get_default_issue_installment_count_fn=get_default_issue_installment_count,
    get_default_equipment_unit_cost_fn=get_default_equipment_unit_cost,
    auto_motor_rental_deduction=AUTO_MOTOR_RENTAL_DEDUCTION,
    equipment_items=EQUIPMENT_ITEMS,
)


def purchases_tab(conn: sqlite3.Connection) -> None:
    section_intro(
        "🛒 Satın Alma | Fatura girişi ve birim maliyet takibi",
        "Ekipman satın alma faturalarını ayrı ekranda yönet; ürün bazlı birim maliyeti ve geçmiş alımları tek listede takip et.",
    )

    if st.session_state.get("purchase_item") == "Box+Punch":
        st.session_state["purchase_item"] = "Box"

    with st.form("purchase_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        purchase_date = c1.date_input("Fatura Tarihi", value=date.today(), key="purchase_date")
        item_name = c2.selectbox("Ürün", PURCHASE_ITEMS, key="purchase_item")
        quantity = c3.number_input("Adet", min_value=1, value=1, step=1, key="purchase_qty")
        c4, c5, c6 = st.columns(3)
        total_invoice_amount = c4.number_input("Toplam Fatura Tutarı", min_value=0.0, value=0.0, step=100.0, key="purchase_total")
        supplier = c5.text_input("Tedarikçi", key="purchase_supplier")
        invoice_no = c6.text_input("Fatura No", key="purchase_invoice_no")
        notes = st.text_input("Not", key="purchase_notes")
        submitted = st.form_submit_button("Satın Alma Kaydet", use_container_width=True)
        if submitted and quantity > 0 and total_invoice_amount > 0:
            unit_cost = round(total_invoice_amount / quantity, 2)
            conn.execute(
                """
                INSERT INTO inventory_purchases
                (purchase_date, item_name, quantity, total_invoice_amount, unit_cost, supplier, invoice_no, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (purchase_date.isoformat(), item_name, int(quantity), total_invoice_amount, unit_cost, supplier, invoice_no, notes),
            )
            conn.commit()
            st.success(f"Satın alma kaydedildi. Birim maliyet: {fmt_try(unit_cost)}")
            st.rerun()

    purchases = fetch_df(
        conn,
        """
        SELECT id, purchase_date, item_name, quantity, total_invoice_amount, unit_cost, supplier, invoice_no, notes
        FROM inventory_purchases
        ORDER BY purchase_date DESC, id DESC
        """,
    )
    if purchases.empty:
        st.info("Henüz satın alma faturası kaydı yok.")
        return

    purchases_display = format_display_df(
        purchases.drop(columns=["id"], errors="ignore"),
        currency_cols=["total_invoice_amount", "unit_cost"],
        number_cols=["quantity"],
        rename_map={
            "purchase_date": "Tarih",
            "item_name": "Ürün",
            "quantity": "Adet",
            "total_invoice_amount": "Toplam Fatura",
            "unit_cost": "Birim Maliyet",
            "supplier": "Tedarikçi",
            "invoice_no": "Fatura No",
            "notes": "Not",
        },
    )
    purchase_rows = build_purchase_grid_rows(purchases_display)
    render_dashboard_data_grid(
        "Satın Alma Listesi",
        "Fatura kayıtlarını ürün, maliyet ve tedarikçi bazında daha şık satırlarda takip et.",
        ["Tarih", "Ürün", "Adet", "Toplam Fatura", "Birim Maliyet", "Tedarikçi"],
        purchase_rows,
        "Henüz satın alma faturası kaydı yok.",
        muted_columns={"Tedarikçi"},
    )

    st.markdown("### Satın alma kaydı düzenle / sil")
    purchase_options = build_purchase_option_map(purchases, fmt_try_fn=fmt_try)
    selected_label = st.selectbox("Düzenlenecek kayıt", list(purchase_options.keys()), key="purchase_manage_select")
    selected_id = purchase_options[selected_label]
    row = purchases.loc[purchases["id"] == selected_id].iloc[0]
    current_date = datetime.strptime(str(row["purchase_date"]), "%Y-%m-%d").date()
    item_options = PURCHASE_ITEMS
    current_item = str(row["item_name"] or "")
    item_index = item_options.index(current_item) if current_item in item_options else 0

    with st.form("purchase_edit_form"):
        c1, c2, c3 = st.columns(3)
        edit_purchase_date = c1.date_input("Fatura Tarihi", value=current_date)
        edit_item_name = c2.selectbox("Ürün", item_options, index=item_index)
        edit_quantity = c3.number_input("Adet", min_value=1, value=max(safe_int(row["quantity"], 1), 1), step=1)
        c4, c5, c6 = st.columns(3)
        edit_total_invoice_amount = c4.number_input("Toplam Fatura Tutarı", min_value=0.0, value=max(safe_float(row["total_invoice_amount"]), 0.0), step=100.0)
        edit_supplier = c5.text_input("Tedarikçi", value=str(row["supplier"] or ""))
        edit_invoice_no = c6.text_input("Fatura No", value=str(row["invoice_no"] or ""))
        edit_notes = st.text_input("Not", value=str(row["notes"] or ""))
        recalculated_unit_cost = round(edit_total_invoice_amount / edit_quantity, 2) if edit_quantity > 0 and edit_total_invoice_amount > 0 else 0.0
        st.caption(f"Yeni birim maliyet: {fmt_try(recalculated_unit_cost)}")
        b1, b2 = st.columns(2)
        update_clicked = b1.form_submit_button("Satın Alma Kaydını Güncelle", use_container_width=True)
        delete_clicked = b2.form_submit_button("Satın Alma Kaydını Sil", use_container_width=True)

        if update_clicked:
            if edit_quantity <= 0:
                st.error("Adet en az 1 olmalı.")
            elif edit_total_invoice_amount <= 0:
                st.error("Toplam fatura tutarı 0'dan büyük olmalı.")
            else:
                conn.execute(
                    """
                    UPDATE inventory_purchases
                    SET purchase_date = ?, item_name = ?, quantity = ?, total_invoice_amount = ?, unit_cost = ?, supplier = ?, invoice_no = ?, notes = ?
                    WHERE id = ?
                    """,
                    (
                        edit_purchase_date.isoformat(),
                        edit_item_name,
                        int(edit_quantity),
                        edit_total_invoice_amount,
                        recalculated_unit_cost,
                        edit_supplier,
                        edit_invoice_no,
                        edit_notes,
                        selected_id,
                    ),
                )
                conn.commit()
                st.success(f"Satın alma kaydı güncellendi. Yeni birim maliyet: {fmt_try(recalculated_unit_cost)}")
                st.rerun()

        if delete_clicked:
            conn.execute("DELETE FROM inventory_purchases WHERE id = ?", (selected_id,))
            conn.commit()
            st.success("Satın alma kaydı silindi.")
            st.rerun()


def equipment_tab(conn: sqlite3.Connection) -> None:
    section_intro(
        "📦 Ekipman Hareketleri | Sonradan satış, düzeltme, iade ve box geri alım",
        "İşe girişten sonra oluşan tüm ekipman hareketlerini, düzeltmeleri, box geri alımlarını ve ekipman kârlılığını bu panelden yönet.",
    )
    person_opts = get_person_options(conn, active_only=False)
    tab1, tab2, tab3 = st.tabs([
        "👷 Kurye Zimmet / Satış",
        "🔄 Box Geri Alım",
        "📈 Ekipman Kârlılığı",
    ])

    with tab1:
        st.markdown("#### Sonradan ekipman hareketi")
        if not person_opts:
            st.info("Önce personel eklenmeli.")
        else:
            if st.session_state.get("issue_item") == "Box+Punch":
                st.session_state["issue_item"] = "Box"
            if st.session_state.get("issue_item") not in ISSUE_ITEMS:
                st.session_state["issue_item"] = ISSUE_ITEMS[0]
            if st.session_state.get("issue_last_item") not in ISSUE_ITEMS:
                st.session_state["issue_last_item"] = st.session_state.get("issue_item", ISSUE_ITEMS[0])
            active_item_name = st.session_state.get("issue_item", ISSUE_ITEMS[0])
            active_cost_snapshot = get_equipment_cost_snapshot(conn, active_item_name)
            active_average_cost = active_cost_snapshot[3]
            if "issue_cost" not in st.session_state:
                st.session_state["issue_cost"] = float(get_default_equipment_unit_cost(conn, active_item_name))
                st.session_state["issue_cost_source_snapshot"] = active_cost_snapshot
            if "issue_sale" not in st.session_state:
                initial_sale = get_default_equipment_sale_price(active_item_name) or st.session_state["issue_cost"]
                st.session_state["issue_sale"] = float(initial_sale)
            if "issue_installment" not in st.session_state:
                st.session_state["issue_installment"] = int(get_default_issue_installment_count(active_item_name))
            if tuple(st.session_state.get("issue_cost_source_snapshot") or ()) != tuple(active_cost_snapshot):
                st.session_state["issue_cost"] = float(active_average_cost)
                st.session_state["issue_cost_source_snapshot"] = active_cost_snapshot

            c1, c2, c3 = st.columns(3)
            person_label = c1.selectbox("Personel", list(person_opts.keys()), key="issue_person")
            issue_date = c2.date_input("Zimmet tarihi", value=date.today(), key="issue_date")
            item_name = c3.selectbox("Ürün", ISSUE_ITEMS, key="issue_item")
            if st.session_state.get("issue_last_item") != item_name:
                refreshed_snapshot = get_equipment_cost_snapshot(conn, item_name)
                refreshed_cost = refreshed_snapshot[3]
                if refreshed_cost <= 0:
                    refreshed_cost = latest_average_cost(conn, item_name)
                refreshed_sale = get_default_equipment_sale_price(item_name) or refreshed_cost
                st.session_state["issue_cost"] = float(refreshed_cost)
                st.session_state["issue_sale"] = float(refreshed_sale)
                st.session_state["issue_cost_source_snapshot"] = refreshed_snapshot
                st.session_state["issue_installment"] = int(get_default_issue_installment_count(item_name))
                st.session_state["issue_last_item"] = item_name
            vat_rate = get_equipment_vat_rate(item_name, issue_date)
            c4, c5, c6 = st.columns(3)
            quantity = c4.number_input("Adet", min_value=1, value=1, step=1, key="issue_qty")
            unit_cost = c5.number_input("Birim maliyet", min_value=0.0, step=50.0, key="issue_cost")
            unit_sale_price = c6.number_input("Kuryeye satış fiyatı | KDV dahil", min_value=0.0, step=50.0, key="issue_sale")
            c7, c8, c9 = st.columns(3)
            sale_type = c7.selectbox("İşlem tipi", ["Satış", "Depozit / Teslim"], key="issue_sale_type")
            installment_count_options = [1, 2, 3, 6, 12]
            issue_installment_value = safe_int(st.session_state.get("issue_installment"), get_default_issue_installment_count(item_name))
            if issue_installment_value not in installment_count_options:
                issue_installment_value = get_default_issue_installment_count(item_name)
                st.session_state["issue_installment"] = issue_installment_value
            if sale_type == "Satış":
                c8.selectbox(
                    "Taksit sayısı",
                    installment_count_options,
                    key="issue_installment",
                )
                installment_count = safe_int(st.session_state.get("issue_installment"), issue_installment_value)
            else:
                c8.selectbox(
                    "Taksit sayısı",
                    [1],
                    index=0,
                    disabled=True,
                    key="issue_installment_disabled_display",
                )
                installment_count = 1
            notes = c9.text_input("Not", key="issue_notes")
            st.caption(f"Bu ürün için varsayılan KDV oranı: %{fmt_number(vat_rate)}")
            if active_average_cost > 0:
                st.caption(f"Varsayılan birim maliyet satın alma kayıtlarındaki ağırlıklı ortalamadan geliyor: {fmt_try(active_average_cost)}")
            if item_name == "Motor Kirası":
                st.caption("Motor Kirası seçildiğinde varsayılan satış fiyatı 13.000₺ ve taksit sayısı 1 olarak gelir.")
            elif item_name == "Motor Satın Alım":
                st.caption("Motor Satın Alım seçildiğinde varsayılan satış fiyatı 135.000₺ ve taksit sayısı 12 olarak gelir.")
            effective_installment_count = normalize_equipment_issue_installment_count(sale_type, installment_count)
            total_sale_amount = float(quantity) * float(unit_sale_price)
            generates_installments = equipment_issue_generates_installments(sale_type, total_sale_amount, effective_installment_count)
            if sale_type != "Satış":
                st.caption("Depozit / Teslim seçildiğinde bağlı zimmet taksiti oluşturulmaz.")
            submit_label = "Zimmet Kaydet ve Taksit Oluştur" if generates_installments else "Zimmet Kaydet"
            submitted = st.button(submit_label, use_container_width=True, key="issue_submit")
            if submitted:
                person_id = person_opts[person_label]
                issue_id = insert_equipment_issue_and_get_id(
                    conn,
                    person_id,
                    issue_date.isoformat(),
                    item_name,
                    int(quantity),
                    unit_cost,
                    unit_sale_price,
                    int(effective_installment_count),
                    sale_type,
                    notes,
                    vat_rate=vat_rate,
                )
                post_equipment_installments(
                    conn,
                    issue_id,
                    person_id,
                    issue_date,
                    item_name,
                    total_sale_amount,
                    int(effective_installment_count),
                    sale_type,
                )
                st.session_state["issue_qty"] = 1
                st.session_state["issue_notes"] = ""
                if generates_installments:
                    st.success(f"Zimmet kaydedildi. Toplam satış: {fmt_try(total_sale_amount)} | {effective_installment_count} taksit oluşturuldu.")
                else:
                    st.success(f"Zimmet kaydedildi. Toplam işlem tutarı: {fmt_try(total_sale_amount)}")
                st.rerun()

        issues = fetch_df(
            conn,
            """
            SELECT i.id, i.issue_date, p.full_name, i.item_name, i.quantity, i.unit_cost, i.unit_sale_price, i.vat_rate, i.auto_source_key,
                   (i.quantity * i.unit_cost) AS total_cost,
                   (i.quantity * i.unit_sale_price) AS total_sale,
                   ((i.quantity * i.unit_sale_price) - (i.quantity * i.unit_cost)) AS gross_profit,
                   i.installment_count, i.sale_type, i.notes
            FROM courier_equipment_issues i
            JOIN personnel p ON p.id = i.personnel_id
            ORDER BY i.issue_date DESC, i.id DESC
            """,
        )
        if not issues.empty:
            issues["source_text"] = issues["auto_source_key"].apply(describe_auto_source_key)
            issues_display = format_display_df(
                issues.drop(columns=["auto_source_key"], errors="ignore"),
                currency_cols=["unit_cost", "unit_sale_price", "total_cost", "total_sale", "gross_profit"],
                number_cols=["quantity", "installment_count"],
                percent_cols=["vat_rate"],
                rename_map={
                    "id": "ID",
                    "issue_date": "Tarih",
                    "full_name": "Personel",
                    "item_name": "Ürün",
                    "quantity": "Adet",
                    "unit_cost": "Birim Maliyet",
                    "unit_sale_price": "Birim Satış",
                    "vat_rate": "KDV",
                    "total_cost": "Toplam Maliyet",
                    "total_sale": "Toplam Satış",
                    "gross_profit": "Brüt Kâr",
                    "installment_count": "Taksit",
                    "sale_type": "İşlem Tipi",
                    "source_text": "Kaynak",
                    "notes": "Not",
                },
            )
            issue_columns = [
                "Tarih",
                "Personel",
                "Ürün",
                "Adet",
                "Birim Maliyet",
                "Birim Satış",
                "Toplam Satış",
                "Taksit",
                "İşlem Tipi",
                "Kaynak",
            ]
            render_dashboard_data_grid(
                "Zimmet Kayıtları",
                "Kurye bazlı satış ve teslim kayıtlarını düzenli satırlarda izle.",
                issue_columns,
                build_grid_rows(issues_display, issue_columns),
                "Henüz zimmet kaydı yok.",
                muted_columns={"Kaynak"},
            )

            st.markdown("#### Toplu güncelle / sil")
            bulk_issue_options = {
                f"{row['issue_date']} | {row['full_name']} | {row['item_name']} | {safe_int(row['quantity'], 0)} adet | ID:{safe_int(row['id'], 0)}": int(row["id"])
                for _, row in issues.iterrows()
            }
            selected_bulk_labels = st.multiselect(
                "İşlem yapılacak zimmet kayıtları",
                list(bulk_issue_options.keys()),
                key="equipment_bulk_issue_select",
            )
            selected_bulk_issue_ids = [bulk_issue_options[label] for label in selected_bulk_labels]

            with st.form("equipment_bulk_manage_form"):
                st.caption("Seçili zimmet kayıtlarını tek seferde güncelleyebilir veya silebilirsin. Boş bıraktığın güncelleme alanları mevcut değerleri korur.")
                b1, b2, b3 = st.columns(3)
                bulk_update_date_enabled = b1.checkbox("Tarihi güncelle", value=False)
                bulk_update_cost_enabled = b2.checkbox("Birim maliyeti güncelle", value=False)
                bulk_update_sale_enabled = b3.checkbox("Birim satışı güncelle", value=False)
                b4, b5, b6 = st.columns(3)
                bulk_update_vat_enabled = b4.checkbox("KDV güncelle", value=False)
                bulk_update_installment_enabled = b5.checkbox("Taksit sayısını güncelle", value=False)
                bulk_update_sale_type_enabled = b6.checkbox("İşlem tipini güncelle", value=False)

                c1, c2, c3 = st.columns(3)
                bulk_issue_date = c1.date_input("Yeni zimmet tarihi", value=date.today(), disabled=not bulk_update_date_enabled)
                bulk_unit_cost = c2.number_input("Yeni birim maliyet", min_value=0.0, value=0.0, step=50.0, disabled=not bulk_update_cost_enabled)
                bulk_unit_sale_price = c3.number_input("Yeni birim satış", min_value=0.0, value=0.0, step=50.0, disabled=not bulk_update_sale_enabled)
                c4, c5, c6 = st.columns(3)
                bulk_vat_rate = c4.number_input("Yeni KDV oranı", min_value=0.0, max_value=100.0, value=VAT_RATE_DEFAULT, step=5.0, disabled=not bulk_update_vat_enabled)
                bulk_installment_count = c5.selectbox("Yeni taksit sayısı", [1, 2, 3, 6, 12], index=1, disabled=not bulk_update_installment_enabled)
                bulk_sale_type = c6.selectbox("Yeni işlem tipi", ["Satış", "Depozit / Teslim"], disabled=not bulk_update_sale_type_enabled)
                bulk_note_text = st.text_input("Seçili kayıtlara eklenecek not", placeholder="Örn: Mart revizyonu")

                a1, a2 = st.columns(2)
                bulk_update_clicked = a1.form_submit_button("Seçili Kayıtları Güncelle", use_container_width=True)
                bulk_delete_clicked = a2.form_submit_button("Seçili Kayıtları Sil", use_container_width=True)

                if bulk_update_clicked:
                    if not selected_bulk_issue_ids:
                        st.error("Önce en az bir zimmet kaydı seçmelisin.")
                    elif not any(
                        [
                            bulk_update_date_enabled,
                            bulk_update_cost_enabled,
                            bulk_update_sale_enabled,
                            bulk_update_vat_enabled,
                            bulk_update_installment_enabled,
                            bulk_update_sale_type_enabled,
                            str(bulk_note_text or "").strip(),
                        ]
                    ):
                        st.error("Toplu güncelleme için en az bir alan seçmeli veya not eklemelisin.")
                    else:
                        updated_count = bulk_update_equipment_issue_records(
                            conn,
                            selected_bulk_issue_ids,
                            issue_date_value=bulk_issue_date if bulk_update_date_enabled else None,
                            unit_cost_value=bulk_unit_cost if bulk_update_cost_enabled else None,
                            unit_sale_price_value=bulk_unit_sale_price if bulk_update_sale_enabled else None,
                            vat_rate_value=bulk_vat_rate if bulk_update_vat_enabled else None,
                            installment_count_value=bulk_installment_count if bulk_update_installment_enabled else None,
                            sale_type_value=bulk_sale_type if bulk_update_sale_type_enabled else None,
                            note_append_text=bulk_note_text,
                        )
                        st.success(f"{updated_count} zimmet kaydı toplu olarak güncellendi.")
                        st.rerun()

                if bulk_delete_clicked:
                    if not selected_bulk_issue_ids:
                        st.error("Önce en az bir zimmet kaydı seçmelisin.")
                    else:
                        deleted_count = delete_equipment_issue_records(conn, selected_bulk_issue_ids)
                        st.success(f"{deleted_count} zimmet kaydı ve bağlı taksitleri silindi.")
                        st.rerun()

        installment_df = fetch_df(
            conn,
            """
            SELECT d.deduction_date, p.full_name, d.deduction_type, d.amount, d.notes, d.auto_source_key
            FROM deductions d
            JOIN personnel p ON p.id = d.personnel_id
            WHERE d.equipment_issue_id IS NOT NULL
            ORDER BY d.deduction_date DESC, d.id DESC
            """,
        )
        if not installment_df.empty:
            st.markdown("#### Oluşan zimmet taksitleri")
            installment_df["source_text"] = installment_df["auto_source_key"].apply(describe_auto_source_key)
            installment_display = format_display_df(
                installment_df.drop(columns=["auto_source_key"], errors="ignore"),
                currency_cols=["amount"],
                rename_map={
                    "deduction_date": "Tarih",
                    "full_name": "Personel",
                    "deduction_type": "Tür",
                    "amount": "Tutar",
                    "source_text": "Kaynak",
                    "notes": "Açıklama",
                },
            )
            installment_columns = ["Tarih", "Personel", "Tür", "Tutar", "Kaynak", "Açıklama"]
            render_dashboard_data_grid(
                "Zimmet Taksitleri",
                "Zimmet kayıtlarından doğan kesintileri ay sonu planıyla takip et.",
                installment_columns,
                build_grid_rows(installment_display, installment_columns),
                "Henüz zimmet taksiti oluşmadı.",
                muted_columns={"Kaynak", "Açıklama"},
            )

    with tab2:
        st.markdown("#### Box geri alım")
        with st.form("box_return_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            person_label = c1.selectbox("Personel", list(person_opts.keys()), key="box_person")
            return_date = c2.date_input("Geri alım tarihi", value=date.today(), key="box_return_date")
            condition_status = c3.selectbox("Durum", ["Temiz", "Hasarlı", "Parasını istemedi"], key="box_condition")
            c4, c5, c6 = st.columns(3)
            quantity = c4.number_input("Adet", min_value=1, value=1, step=1, key="box_qty")
            payout_amount = c5.number_input("Kurye geri ödeme tutarı", min_value=0.0, value=0.0, step=100.0, key="box_payout")
            notes = c6.text_input("Not", key="box_notes")
            submitted = st.form_submit_button("Box geri alımı kaydet", use_container_width=True)
            if submitted:
                person_id = person_opts[person_label]
                waived = 1 if condition_status == "Parasını istemedi" else 0
                conn.execute(
                    """
                    INSERT INTO box_returns (personnel_id, return_date, quantity, condition_status, payout_amount, waived, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (person_id, return_date.isoformat(), int(quantity), condition_status, payout_amount, waived, notes),
                )
                conn.commit()
                st.success("Box geri alım kaydı oluşturuldu.")

        returns_df = fetch_df(
            conn,
            """
            SELECT b.return_date, p.full_name, b.quantity, b.condition_status, b.payout_amount, b.waived, b.notes
            FROM box_returns b
            JOIN personnel p ON p.id = b.personnel_id
            ORDER BY b.return_date DESC, b.id DESC
            """,
        )
        if not returns_df.empty:
            returns_df["waived_text"] = returns_df["waived"].apply(lambda x: "Evet" if x else "Hayır")
            returns_display = format_display_df(
                returns_df,
                currency_cols=["payout_amount"],
                number_cols=["quantity"],
                rename_map={
                    "return_date": "Tarih",
                    "full_name": "Personel",
                    "quantity": "Adet",
                    "condition_status": "Durum",
                    "payout_amount": "Geri Ödeme",
                    "waived_text": "Parasını İstemedi",
                    "notes": "Not",
                },
            )
            cols = ["Tarih", "Personel", "Adet", "Durum", "Geri Ödeme", "Parasını İstemedi", "Not"]
            render_dashboard_data_grid(
                "Box Geri Alım Kayıtları",
                "İade edilen box kayıtlarını durum ve geri ödeme bazında izle.",
                cols,
                build_grid_rows(returns_display[cols], cols),
                "Henüz box geri alım kaydı yok.",
                muted_columns={"Not"},
            )

    with tab3:
        st.markdown("#### Ekipman satış ve kârlılık özeti")
        sales_profit = fetch_df(
            conn,
            """
            SELECT item_name,
                   SUM(quantity) AS sold_qty,
                   SUM(quantity * unit_cost) AS total_cost,
                   SUM(quantity * unit_sale_price) AS total_sale,
                   SUM((quantity * unit_sale_price) - (quantity * unit_cost)) AS gross_profit
            FROM courier_equipment_issues
            WHERE sale_type = 'Satış'
            GROUP BY item_name
            ORDER BY total_sale DESC
            """,
        )
        stock_purchase = fetch_df(
            conn,
            """
            SELECT item_name,
                   SUM(quantity) AS purchased_qty,
                   SUM(total_invoice_amount) AS purchased_total,
                   CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount)/SUM(quantity) ELSE 0 END AS weighted_unit_cost
            FROM inventory_purchases
            GROUP BY item_name
            ORDER BY item_name
            """,
        )

        c1, c2, c3 = st.columns(3)
        total_purchase = float(stock_purchase["purchased_total"].sum()) if not stock_purchase.empty else 0.0
        total_sale = float(sales_profit["total_sale"].sum()) if not sales_profit.empty else 0.0
        total_profit = float(sales_profit["gross_profit"].sum()) if not sales_profit.empty else 0.0
        c1.metric("Toplam satın alma", fmt_try(total_purchase))
        c2.metric("Kuryeye toplam satış", fmt_try(total_sale))
        c3.metric("Brüt ekipman kârı", fmt_try(total_profit))
        st.caption("Bu özet yalnızca `Satış` tipindeki zimmet kayıtlarını gelir ve kârlılık hesabına dahil eder. `Depozit / Teslim` kayıtları bu satış özetine girmez.")

        if not sales_profit.empty:
            sales_display = format_display_df(
                sales_profit,
                currency_cols=["total_cost", "total_sale", "gross_profit"],
                number_cols=["sold_qty"],
                rename_map={
                    "item_name": "Ürün",
                    "sold_qty": "Satılan Adet",
                    "total_cost": "Toplam Maliyet",
                    "total_sale": "Toplam Satış",
                    "gross_profit": "Brüt Kâr",
                },
            )
            sales_columns = ["Ürün", "Satılan Adet", "Toplam Maliyet", "Toplam Satış", "Brüt Kâr"]
            render_dashboard_data_grid(
                "Satış Özeti",
                "Yalnızca satış tipindeki zimmet kayıtlarının kârlılık kırılımı.",
                sales_columns,
                build_grid_rows(sales_display, sales_columns),
                "Henüz satış tipinde zimmet kaydı yok.",
            )

        if not stock_purchase.empty:
            st.markdown("#### Satın alma özeti")
            stock_display = format_display_df(
                stock_purchase,
                currency_cols=["purchased_total", "weighted_unit_cost"],
                number_cols=["purchased_qty"],
                rename_map={
                    "item_name": "Ürün",
                    "purchased_qty": "Alınan Adet",
                    "purchased_total": "Toplam Fatura",
                    "weighted_unit_cost": "Ağırlıklı Birim Maliyet",
                },
            )
            stock_columns = ["Ürün", "Alınan Adet", "Toplam Fatura", "Ağırlıklı Birim Maliyet"]
            render_dashboard_data_grid(
                "Satın Alma Özeti",
                "Satın alma faturalarının ürün bazlı maliyet ortalaması.",
                stock_columns,
                build_grid_rows(stock_display, stock_columns),
                "Henüz satın alma özeti yok.",
            )

def fmt_currency_pdf(value: float) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", ".") + " TL"
    except Exception:
        return "0 TL"


def register_pdf_font() -> str:
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


def build_payroll_pdf(selected_month: str, payroll_row: dict, deduction_rows: pd.DataFrame, restaurant_names: list[str]) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = register_pdf_font()

    def write_line(text: str, x: int, y: float, size: int = 10) -> None:
        c.setFont(font_name, size)
        c.drawString(x, y, str(text))

    y = height - 50
    write_line("Çat Kapında", 40, y, 16)
    y -= 22
    write_line("Kurye Hakediş Raporu", 40, y, 14)
    y -= 28

    lines = [
        f"Personel: {payroll_row.get('personel', '-')}",
        f"Kod: {payroll_row.get('person_code', '-')}",
        f"Rol: {payroll_row.get('rol', '-')}",
        f"Ay: {selected_month}",
        f"Durum: {payroll_row.get('durum', '-')}",
        "Restoranlar: " + (", ".join(restaurant_names) if restaurant_names else "-"),
    ]
    for line in lines:
        write_line(line, 40, y, 10)
        y -= 16

    y -= 4
    c.line(40, y, width - 40, y)
    y -= 20

    write_line("Çalışma Özeti", 40, y, 12)
    y -= 18
    write_line(f"Toplam Saat: {int(float(payroll_row.get('calisma_saati', 0) or 0))}", 40, y)
    y -= 16
    write_line(f"Toplam Paket: {int(float(payroll_row.get('paket', 0) or 0))}", 40, y)
    y -= 22

    write_line("Hakediş Özeti", 40, y, 12)
    y -= 18
    write_line(f"Brüt Hakediş: {fmt_currency_pdf(payroll_row.get('brut_maliyet', 0))}", 40, y)
    y -= 16
    write_line(f"Toplam Kesinti: {fmt_currency_pdf(payroll_row.get('kesinti', 0))}", 40, y)
    y -= 16
    write_line(f"Net Ödeme: {fmt_currency_pdf(payroll_row.get('net_maliyet', 0))}", 40, y, 11)
    y -= 24

    write_line("Kesinti Detayı", 40, y, 12)
    y -= 18
    if deduction_rows is None or deduction_rows.empty:
        write_line("Bu ay için kesinti kaydı bulunamadı.", 40, y)
        y -= 16
    else:
        grouped = deduction_rows.groupby("deduction_type", dropna=False)["amount"].sum().reset_index()
        for _, row in grouped.iterrows():
            write_line(f"{row['deduction_type']}: -{fmt_currency_pdf(row['amount'])}", 40, y)
            y -= 16
            if y < 80:
                c.showPage()
                y = height - 50

    y -= 8
    c.line(40, y, width - 40, y)
    y -= 16
    write_line("Çat Kapında Operasyon CRM tarafından oluşturuldu.", 40, y, 9)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def monthly_payroll_tab(conn: sqlite3.Connection) -> None:
    section_intro("🧾 Aylık Hakediş | Personel bazlı brüt, kesinti ve net ödeme özeti", "Aylık puantaj ve kesinti verilerini personel bazında hesaplar; tablo dosyası olarak dışa aktarma sağlar.")

    entries = fetch_df(
        conn,
        """
        SELECT d.*, r.brand, r.branch, r.pricing_model, r.hourly_rate, r.package_rate,
               r.package_threshold, r.package_rate_low, r.package_rate_high,
               r.fixed_monthly_fee, r.vat_rate
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        """,
    )
    deductions = fetch_df(conn, "SELECT * FROM deductions")
    personnel_df = fetch_df(conn, "SELECT * FROM personnel")
    role_history_df = fetch_df(conn, "SELECT * FROM personnel_role_history ORDER BY personnel_id, effective_date, id")

    if entries.empty and deductions.empty:
        st.info("Hakediş hesabı için günlük puantaj veya kesinti verisi bulunamadı.")
        return

    date_series = []
    if not entries.empty:
        entries["entry_date"] = pd.to_datetime(entries["entry_date"])
        date_series.extend(entries["entry_date"].dt.strftime("%Y-%m").tolist())
    if not deductions.empty:
        deductions["deduction_date"] = pd.to_datetime(deductions["deduction_date"])
        date_series.extend(deductions["deduction_date"].dt.strftime("%Y-%m").tolist())

    month_options = sorted(pd.Series(date_series).dropna().unique().tolist(), reverse=True)
    if not month_options:
        st.warning("Ay seçeneği bulunamadı.")
        return

    c1, c2, c3 = st.columns(3)
    selected_month = c1.selectbox("Hakediş Ayı", month_options)
    role_filter = c2.selectbox("Rol", ["Tümü"] + PERSONNEL_ROLE_OPTIONS)
    restaurant_choices = ["Tümü"]
    if not entries.empty:
        restaurant_choices += sorted((entries["brand"] + " - " + entries["branch"]).dropna().unique().tolist())
    restaurant_filter = c3.selectbox("Restoran filtresi", restaurant_choices)

    start_date, end_date = month_bounds(selected_month)
    month_entries = entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy() if not entries.empty else pd.DataFrame()
    month_deductions = deductions[(deductions["deduction_date"] >= start_date) & (deductions["deduction_date"] <= end_date)].copy() if not deductions.empty else pd.DataFrame()

    st.caption(
        "Hakediş notu: Kesintiler seçilen ayın son gününe yazılır. Bu ekrandaki net ödeme, ay kapanışına göre hesaplanır; ödeme akışı ayın 15'inde yapılır."
    )

    if restaurant_filter != "Tümü" and not month_entries.empty:
        month_entries = month_entries[(month_entries["brand"] + " - " + month_entries["branch"]) == restaurant_filter].copy()

    cost_df = calculate_personnel_cost(month_entries, personnel_df, month_deductions, role_history_df=role_history_df)
    if cost_df.empty:
        st.warning("Seçilen filtre için hakediş verisi bulunamadı.")
        return

    if role_filter != "Tümü":
        cost_df = cost_df[cost_df["rol"].fillna("").astype(str).str.contains(role_filter, regex=False)].copy()

    if not month_entries.empty:
        by_person_branch = month_entries.groupby("actual_personnel_id", dropna=False).agg(restoran_sayisi=("restaurant_id", "nunique")).reset_index().rename(columns={"actual_personnel_id": "personnel_id"})
    else:
        by_person_branch = pd.DataFrame(columns=["personnel_id", "restoran_sayisi"])
    cost_df = cost_df.merge(by_person_branch, on="personnel_id", how="left")
    cost_df["restoran_sayisi"] = cost_df["restoran_sayisi"].fillna(0).astype(int)
    cost_df["ay"] = selected_month

    render_executive_metrics(
        [
            {
                "label": "Toplam Brüt Hakediş",
                "value": fmt_try(float(cost_df["brut_maliyet"].sum())),
                "note": f"{selected_month} çalışma toplamı",
            },
            {
                "label": "Toplam Kesinti",
                "value": fmt_try(float(cost_df["kesinti"].sum())),
                "note": "Ay sonu kesinti toplamı",
                "tone": "warning",
            },
            {
                "label": "Toplam Net Ödeme",
                "value": fmt_try(float(cost_df["net_maliyet"].sum())),
                "note": "Hakediş kapanış özeti",
                "tone": "positive",
            },
        ],
        title="Hakediş Yönetim Özeti",
        subtitle="Seçilen ayın brüt, kesinti ve net ödeme seviyesini yönetim bakışıyla özetler.",
    )

    payroll_display = format_display_df(
        cost_df[["ay", "personel", "rol", "durum", "calisma_saati", "paket", "brut_maliyet", "kesinti", "net_maliyet", "restoran_sayisi", "maliyet_modeli"]],
        currency_cols=["Brüt Hakediş", "Toplam Kesinti", "Net Ödeme"],
        number_cols=["Toplam Saat", "Toplam Paket", "Restoran Sayısı"],
        rename_map={
            "ay": "Ay",
            "personel": "Personel",
            "rol": "Rol",
            "durum": "Durum",
            "calisma_saati": "Toplam Saat",
            "paket": "Toplam Paket",
            "brut_maliyet": "Brüt Hakediş",
            "kesinti": "Toplam Kesinti",
            "net_maliyet": "Net Ödeme",
            "restoran_sayisi": "Restoran Sayısı",
            "maliyet_modeli": "Maliyet Modeli",
        },
        value_maps={
            "maliyet_modeli": COST_MODEL_LABELS,
        },
    )
    with st.container(border=True):
        payroll_columns = ["Personel", "Rol", "Toplam Saat", "Toplam Paket", "Brüt Hakediş", "Toplam Kesinti", "Net Ödeme", "Maliyet Modeli"]
        render_dashboard_data_grid(
            "Hakediş Özeti",
            "Personel bazlı çalışma, kesinti ve net ödeme görünümünü daha temiz satırlarda incele.",
            payroll_columns,
            build_grid_rows(payroll_display, payroll_columns),
            "Seçilen filtre için hakediş verisi bulunamadı.",
            muted_columns={"Maliyet Modeli"},
        )
        st.download_button(
            "Aylık hakediş tablosunu indir",
            data=cost_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_aylik_hakedis_{selected_month}.csv",
            mime="text/csv",
        )

    st.markdown("### Hakediş Belgesini İndir")
    pdf_person_options = {f"{row['personel']} | {row['rol']}": row["personnel_id"] for _, row in cost_df.sort_values("personel").iterrows()}
    if pdf_person_options:
        selected_pdf_label = st.selectbox("Belgesi oluşturulacak personel", list(pdf_person_options.keys()))
        selected_pdf_id = pdf_person_options[selected_pdf_label]
        payroll_row = cost_df[cost_df["personnel_id"] == selected_pdf_id].iloc[0].to_dict()

        person_match = personnel_df[personnel_df["id"] == selected_pdf_id]
        payroll_row["person_code"] = person_match.iloc[0]["person_code"] if not person_match.empty else ""

        deduction_rows = month_deductions[month_deductions["personnel_id"] == selected_pdf_id].copy() if not month_deductions.empty else pd.DataFrame()
        worked_restaurants = []
        if not month_entries.empty:
            rest_series = (
                month_entries.loc[month_entries["actual_personnel_id"] == selected_pdf_id, "brand"].fillna("") + " - " +
                month_entries.loc[month_entries["actual_personnel_id"] == selected_pdf_id, "branch"].fillna("")
            )
            worked_restaurants = [r.strip(" -") for r in sorted(rest_series.unique().tolist()) if r.strip(" -")]

        pdf_bytes = build_payroll_pdf(selected_month, payroll_row, deduction_rows, worked_restaurants)
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(payroll_row.get("personel", "personel")))
        st.download_button(
            "Hakediş belgesini indir",
            data=pdf_bytes,
            file_name=f"hakedis_{safe_name}_{selected_month}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("Belge oluşturmak için önce hakediş tablosunda personel verisi oluşmalı.")


def announcements_tab() -> None:
    render_management_hero(
        "GÜNCELLEMELER VE DUYURULAR",
        "Sistemdeki son iyileştirmeler ve takip notları",
        "Operasyon ekibinin son yayınlanan geliştirmeleri tek ekranda görmesi için hazırlanan hızlı özet alanı.",
        [
            ("Giriş Deneyimi", "Yenilendi"),
            ("Personel Formları", "Güncellendi"),
            ("Restoran Fiyatlama", "Dinamik"),
            ("Motor Kira Hesabı", "Gün Bazlı"),
        ],
    )

    section_intro(
        "Son Yayınlanan İyileştirmeler",
        "Yakın dönemde canlıya alınan başlıca düzenlemeler aşağıda özetlenmiştir.",
    )

    c1, c2 = st.columns(2)
    with c1:
        render_record_snapshot(
            "Operasyon ve Form Akışları",
            [
                ("Personel Yönetimi", "Ekleme sonrası görünür başarı mesajı ve son eklenen kartı"),
                ("Zorunlu Alanlar", "Kırmızı * ile işaretlenir ve boş geçilemez"),
                ("Rol / Maliyet Modeli", "Personel formunda otomatik eşlenir"),
                ("Restoran Fiyat Modelleri", "Seçime göre sadece ilgili alanlar görünür"),
            ],
        )
    with c2:
        render_record_snapshot(
            "Finans ve Hesaplama",
            [
                ("Motor Kira", "13.000 / 30 x çalışılan gün formülüyle hesaplanır"),
                ("Kesinti Senkronu", "Puantaj ekleme, güncelleme ve silmede otomatik yenilenir"),
                ("Hakediş / Raporlar", "Açılırken sistem kesintileri yeniden senkronlanır"),
                ("Şifre Sıfırlama", "Mail ile geçici şifre gönderimi desteklenir"),
            ],
        )

    st.markdown("##### Notlar")
    st.info(
        "Canlı ortamda bir değişiklik görünmüyorsa Render tarafında bazen `Manual Deploy` çalıştırmak gerekebilir. "
        "Deploy tamamlandıktan sonra sayfayı sert yenilemek en güvenli kontroldür."
    )
    st.caption("Bu alan sabit duyuru panosu gibi çalışır; yeni operasyon notları gerektiğinde genişletilebilir.")


def reports_tab(conn: sqlite3.Connection) -> None:
    section_intro("📊 Raporlar ve Karlılık | Fatura, personel maliyeti, yan gelir ve restoran kârlılığı", "Aylık müşteri faturası, personel maliyeti, restoran bazlı kârlılık, ekipman satış kârlılığı, yan gelir analizi ve personel-şube dağılımı.")

    entries, month_options = load_reporting_entries_and_month_options(conn)
    if entries.empty:
        st.info("Rapor üretebilmek için önce günlük puantaj girişi yap.")
        return

    selected_month = st.selectbox("Rapor Ayı", month_options)
    report_payload = build_reports_workspace_payload(conn, entries, selected_month)
    if report_payload.month_df.empty:
        st.warning("Bu ay için kayıt yok.")
        return

    render_executive_metrics(
        [
            {
                "label": "Aylık Restoran Faturası",
                "value": fmt_try(report_payload.revenue),
                "note": f"{selected_month} | KDV dahil",
            },
            {
                "label": "Toplam Kurye Maliyeti",
                "value": fmt_try(report_payload.personnel_cost),
                "note": "Net maliyet toplamı",
            },
            {
                "label": "Brüt Operasyon Farkı",
                "value": fmt_try(report_payload.gross_profit),
                "note": "Fatura ve personel maliyeti farkı",
                "tone": "positive" if report_payload.gross_profit >= 0 else "critical",
            },
            {
                "label": "Yan Gelir Neti",
                "value": fmt_try(report_payload.side_income_net),
                "note": "Muhasebe, motor ve ekipman katkısı",
                "tone": "positive" if report_payload.side_income_net >= 0 else "warning",
            },
        ],
        title="Rapor Yönetim Özeti",
        subtitle="Seçilen ayın gelir, maliyet ve ek katkılarını aynı bakışta özetler.",
    )

    covered_restaurant_count = int(report_payload.invoice_df["restoran"].dropna().astype(str).nunique()) if not report_payload.invoice_df.empty else 0
    operational_restaurant_count = len(report_payload.operational_restaurant_names)
    if operational_restaurant_count > 0 and covered_restaurant_count < operational_restaurant_count:
        st.warning(
            f"{selected_month} için rapor şu an kısmi veriyle çalışıyor: {covered_restaurant_count} restoranın puantaj/fatura verisi var, "
            f"{operational_restaurant_count} restoran operasyonel havuzda görünüyor. Ortak operasyon payı bu havuza bölünür."
        )
    st.caption(
        "Ortak Operasyon Payı notu: Joker ve Bölge Müdürü maliyeti, dönem içinde operasyonel kabul edilen restoranlara eşit dağıtılır. "
        "Bu dağıtım restoran faturalarını değiştirmez; yalnızca kârlılık hesabına yansır."
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🧾 Restoran Faturası", "👥 Kurye Maliyeti", "📈 Restoran Karlılığı", "🧩 Ortak Operasyon Payı", "🔀 Personel-Şube Dağılımı", "💼 Yan Gelir Analizi"])
    with tab1:
        render_invoice_report_tab(
            report_payload.invoice_df,
            report_payload.invoice_drilldown_map,
            report_payload.invoice_attendance_export_map,
            selected_month,
            format_display_df_fn=format_display_df,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            pricing_model_labels=PRICING_MODEL_LABELS,
            fmt_number_fn=fmt_number,
            fmt_try_fn=fmt_try,
            build_restaurant_export_filename_fn=build_restaurant_export_filename,
        )
    with tab2:
        render_cost_report_tab(
            report_payload.cost_df,
            selected_month,
            format_display_df_fn=format_display_df,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            cost_model_labels=COST_MODEL_LABELS,
        )
    with tab3:
        render_profit_report_tab(
            report_payload.profit_df,
            selected_month,
            format_display_df_fn=format_display_df,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            render_executive_metrics_fn=render_executive_metrics,
            fmt_try_fn=fmt_try,
            pricing_model_labels=PRICING_MODEL_LABELS,
        )
    with tab4:
        render_shared_overhead_report_tab(
            report_payload.shared_overhead_df,
            selected_month,
            format_display_df_fn=format_display_df,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            render_executive_metrics_fn=render_executive_metrics,
            fmt_try_fn=fmt_try,
        )

    with tab5:
        render_distribution_report_tab(
            report_payload.person_distribution_df,
            selected_month,
            format_display_df_fn=format_display_df,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            allocation_source_labels=ALLOCATION_SOURCE_LABELS,
        )

    with tab6:
        render_side_income_report_tab(
            report_payload.side_df,
            report_payload.equipment_profit_df,
            report_payload.equipment_purchase_df,
            report_payload.fuel_reflection_amount,
            format_display_df_fn=format_display_df,
            build_grid_rows_fn=build_grid_rows,
            render_dashboard_data_grid_fn=render_dashboard_data_grid,
            render_executive_metrics_fn=render_executive_metrics,
            render_record_snapshot_fn=render_record_snapshot,
            fmt_try_fn=fmt_try,
        )


def main() -> None:
    st.set_page_config(page_title=APP_PAGE_TITLE, page_icon=APP_PAGE_ICON, layout="wide", initial_sidebar_state="expanded")
    inject_global_styles()
    render_login_transition_overlay()
    boot_placeholder = render_boot_shell()

    try:
        conn = get_conn()
        if boot_placeholder is not None:
            boot_placeholder.empty()
            st.session_state["_ck_boot_shell_rendered"] = True
    except RuntimeError as exc:
        st.error(str(exc))
        st.info(
            "Supabase baglantisi kurulamadigi icin uygulama acilmadi. "
            "Streamlit Secrets icindeki [database] bilgilerini Supabase Connect ekranindaki host/user "
            "alanlariyla tekrar karsilastir."
        )
        st.code(
            '[database]\n'
            'host = "..." \n'
            'port = 5432\n'
            'dbname = "postgres"\n'
            'user = "..." \n'
            'password = "..." \n'
            'sslmode = "require"\n',
            language="toml",
        )
        return
    try:
        if not login_gate(conn):
            return

        role = st.session_state.get("role", "")
        render_sidebar_brand()
        menu_items = allowed_menu_items(role)
        target_menu = st.session_state.pop("ck_sidebar_target_menu", None)
        if target_menu in menu_items:
            st.session_state["ck_main_menu"] = target_menu
        if st.session_state.get("ck_main_menu") not in menu_items:
            st.session_state["ck_main_menu"] = menu_items[0]
        menu = render_sidebar_navigation(menu_items, st.session_state.get("ck_main_menu", menu_items[0]))
        st.session_state["ck_main_menu"] = menu

        ensure_role_access(menu, role)
        render_top_profile(conn)
        content_placeholder = st.empty()
        with content_placeholder.container():
            render_workspace_loading_shell(MENU_DISPLAY_LABELS.get(menu, menu))
        with content_placeholder.container():
            if menu == "Genel Bakış":
                dashboard_tab(conn)
            elif menu == "Güncellemeler ve Duyurular":
                announcements_tab()
            elif menu == "Restoran Yönetimi":
                restaurants_tab(conn)
            elif menu == "Personel Yönetimi":
                personnel_tab(conn)
            elif menu == "Puantaj":
                attendance_tab(conn)
            elif menu == "Satın Alma":
                purchases_tab(conn)
            elif menu == "Kesinti Yönetimi":
                deductions_tab(conn)
            elif menu == "Aylık Hakediş":
                monthly_payroll_tab(conn)
            elif menu == "Raporlar ve Karlılık":
                reports_tab(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
