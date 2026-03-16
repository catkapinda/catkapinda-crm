from __future__ import annotations

import calendar
from io import BytesIO
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


USERS = {
    "catkapinda": {"password": "Cat2025.", "role": "admin", "display": "Yönetim Kurulu / Admin"},
    "chef": {"password": "Chef2025.", "role": "sef", "display": "Şef"},
}


def login_gate() -> bool:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None

    if st.session_state.authenticated:
        return True

    st.set_page_config(page_title="Çat Kapında Operasyon CRM", page_icon="📦", layout="wide")
    inject_global_styles()

    st.markdown("<div class='ck-login-gap'></div>", unsafe_allow_html=True)
    left, center, right = st.columns([1.2, 0.9, 1.2])

    with center:
        st.markdown("<div class='ck-login-card'>", unsafe_allow_html=True)
        st.markdown("<div class='ck-login-badge'>ÇAT KAPINDA</div>", unsafe_allow_html=True)
        st.markdown('<div class="ck-login-title">Operasyon CRM</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ck-login-subtitle">Operasyon, personel, puantaj, kesinti, ekipman, aylık hakediş ve kârlılık yönetimi.</div>',
            unsafe_allow_html=True,
        )
        username = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adınızı girin")
        password = st.text_input("Şifre", type="password", placeholder="Şifrenizi girin")
        if st.button("Giriş Yap", width='stretch'):
            user = USERS.get(username)
            if user and password == user["password"]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = user["role"]
                st.success("Giriş başarılı")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı")
        st.caption("Admin: catkapinda • Şef: chef")
        st.markdown("</div>", unsafe_allow_html=True)

    return False


def logout_button() -> None:
    role = st.session_state.get("role")
    display = USERS.get(st.session_state.get("username"), {}).get("display", role or "-")
    st.sidebar.markdown("## Çat Kapında CRM")
    st.sidebar.markdown(
        f"""
        <div class="ck-side-user">
            <div class="ck-side-user-name">{st.session_state.get("username", "-")}</div>
            <div class="ck-side-user-role">{display}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Çıkış Yap", width='stretch'):
        for key in ["authenticated", "username", "role"]:
            st.session_state.pop(key, None)
        st.rerun()


def allowed_menu_items(role: str) -> list[str]:
    if role == "admin":
        return [
            "🏠 Ana Dashboard",
            "🏢 Restoran Yönetimi",
            "👥 Personel Yönetimi",
            "📦 Ekipman & Zimmet",
            "🗓 Günlük Puantaj",
            "🗂 Toplu Puantaj",
            "💸 Kesinti Yönetimi",
            "🧾 Aylık Hakediş",
            "📊 Raporlar ve Karlılık",
        ]
    if role == "sef":
        return [
            "👥 Personel Yönetimi",
            "🗓 Günlük Puantaj",
            "🗂 Toplu Puantaj",
            "💸 Kesinti Yönetimi",
        ]
    return []


def ensure_role_access(menu: str, role: str) -> None:
    if menu not in allowed_menu_items(role):
        st.error("Bu sayfaya erişim yetkiniz yok.")
        st.stop()


def parse_whatsapp_bulk(text_value: str) -> list[dict]:
    rows = []
    if not text_value:
        return rows
    for raw in text_value.splitlines():
        line = raw.strip()
        if not line:
            continue
        normalized = line.replace("—", "-").replace("–", "-")
        # Ad Soyad - 10 saat - 38 paket - Joker
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
            elif low.title() in ["Normal", "Joker", "İzin", "Izin", "Gelmedi", "Çıkış", "Cikis"]:
                status = p.replace("Izin", "İzin").replace("Cikis", "Çıkış")
            elif nums and hours == 0:
                hours = float(nums[0].replace(",", "."))
            elif nums and packages == 0:
                packages = int(float(nums[0].replace(",", ".")))
            else:
                note = p
        rows.append({"person_label": name, "worked_hours": hours, "package_count": packages, "entry_status": status or "Normal", "notes": note})
    return rows

DB_PATH = Path(__file__).with_name("catkapinda_crm.db")
VAT_RATE_DEFAULT = 20.0
COURIER_HOURLY_COST = 250.0  # KDV dahil
COURIER_PACKAGE_COST_DEFAULT_LOW = 20.0
COURIER_PACKAGE_COST_DEFAULT_HIGH = 25.0
COURIER_PACKAGE_COST_QC = 25.0
PACKAGE_THRESHOLD_DEFAULT = 390


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


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    seed_initial_data(conn)
    migrate_data(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            branch TEXT NOT NULL,
            billing_group TEXT,
            pricing_model TEXT NOT NULL,
            hourly_rate REAL DEFAULT 0,
            package_rate REAL DEFAULT 0,
            package_threshold INTEGER,
            package_rate_low REAL DEFAULT 0,
            package_rate_high REAL DEFAULT 0,
            fixed_monthly_fee REAL DEFAULT 0,
            vat_rate REAL DEFAULT 20,
            target_headcount INTEGER DEFAULT 0,
            start_date TEXT,
            end_date TEXT,
            extra_headcount_request INTEGER DEFAULT 0,
            extra_headcount_request_date TEXT,
            reduce_headcount_request INTEGER DEFAULT 0,
            reduce_headcount_request_date TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            tax_office TEXT,
            tax_number TEXT,
            active INTEGER DEFAULT 1,
            notes TEXT,
            UNIQUE(brand, branch)
        );

        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_code TEXT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Aktif',
            phone TEXT,
            tc_no TEXT,
            iban TEXT,
            accounting_type TEXT DEFAULT '-',
            new_company_setup TEXT DEFAULT 'Hayır',
            accounting_revenue REAL DEFAULT 0,
            accountant_cost REAL DEFAULT 0,
            company_setup_revenue REAL DEFAULT 0,
            company_setup_cost REAL DEFAULT 0,
            assigned_restaurant_id INTEGER,
            vehicle_type TEXT,
            motor_rental TEXT DEFAULT 'Hayır',
            current_plate TEXT,
            start_date TEXT,
            exit_date TEXT,
            cost_model TEXT NOT NULL DEFAULT 'standard_courier',
            monthly_fixed_cost REAL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (assigned_restaurant_id) REFERENCES restaurants(id)
        );

        CREATE TABLE IF NOT EXISTS plate_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            plate TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            reason TEXT,
            active INTEGER DEFAULT 1,
            FOREIGN KEY (personnel_id) REFERENCES personnel(id)
        );

        CREATE TABLE IF NOT EXISTS daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            restaurant_id INTEGER NOT NULL,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            status TEXT NOT NULL,
            worked_hours REAL DEFAULT 0,
            package_count REAL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY (planned_personnel_id) REFERENCES personnel(id),
            FOREIGN KEY (actual_personnel_id) REFERENCES personnel(id)
        );

        CREATE TABLE IF NOT EXISTS deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            deduction_date TEXT NOT NULL,
            deduction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (personnel_id) REFERENCES personnel(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_date TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_invoice_amount REAL NOT NULL,
            unit_cost REAL NOT NULL,
            supplier TEXT,
            invoice_no TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS courier_equipment_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_cost REAL NOT NULL DEFAULT 0,
            unit_sale_price REAL NOT NULL DEFAULT 0,
            installment_count INTEGER NOT NULL DEFAULT 2,
            sale_type TEXT NOT NULL DEFAULT 'Satış',
            notes TEXT,
            FOREIGN KEY (personnel_id) REFERENCES personnel(id)
        );

        CREATE TABLE IF NOT EXISTS box_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL,
            return_date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            condition_status TEXT NOT NULL,
            payout_amount REAL NOT NULL DEFAULT 0,
            waived INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (personnel_id) REFERENCES personnel(id)
        );

        """
    )
    conn.commit()


def table_has_rows(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0] > 0


def seed_initial_data(conn: sqlite3.Connection) -> None:
    if not table_has_rows(conn, "restaurants"):
        restaurants = [
            ("Fasuli", "Beyoğlu", "Fasuli", "threshold_package", 273, 0, 390, 33.75, 47.25, 0, 20, 2, 1, "390 pakete kadar düşük prim, üstü yüksek prim."),
            ("Fasuli", "Vatan", "Fasuli", "threshold_package", 273, 0, 390, 33.75, 47.25, 0, 20, 2, 1, "390 pakete kadar düşük prim, üstü yüksek prim."),
            ("Köroğlu Pide", "Merkez", "Köroğlu Pide", "threshold_package", 260, 0, 390, 27, 40.5, 0, 20, 4, 1, "390 paket eşiği."),
            ("Sushi Inn", "Merkez", "Sushi Inn", "fixed_monthly", 0, 0, None, 0, 0, 79800, 20, 1, 1, "26 gün 10 saat çalışan 1 kurye için sabit ücret."),
            ("SushiCo", "Beyoğlu", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Standart SushiCo modeli."),
            ("SushiCo", "Sancaktepe", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Standart SushiCo modeli."),
            ("SushiCo", "İdealistpark", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Standart SushiCo modeli."),
            ("Quick China", "Ataşehir", "Quick China", "hourly_plus_package", 279, 32, None, 0, 0, 84500, 20, 5, 1, "Şube içinde 4+1 kurye/şef yapısı var."),
            ("Quick China", "Suadiye", "Quick China", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 4, 1, "Quick China standart şube."),
            ("Hacıbaşar", "Maltepe", "Hacıbaşar", "threshold_package", 254, 0, 390, 27, 40.5, 0, 20, 2, 1, "390 paket eşiği."),
            ("Hacıbaşar", "Ümraniye", "Hacıbaşar", "threshold_package", 254, 0, 390, 27, 40.5, 0, 20, 2, 1, "390 paket eşiği."),
            ("Yavuzbey İskender", "Merkez", "Yavuzbey İskender", "hourly_plus_package", 264, 33, None, 0, 0, 0, 20, 3, 1, "Saatlik + paket."),
            ("Burger@", "Kavacık", "Burger@", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 1, 1, "Saatlik + paket."),
            ("SushiCo", "Lens Kurtköy", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 2, 1, "Standart SushiCo modeli."),
            ("SushiCo", "Acr Loft", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 2, 1, "Standart SushiCo modeli."),
            ("SushiCo", "Çengelköy", "SushiCo Group", "hourly_plus_package", 279, 32, None, 0, 0, 0, 20, 5, 1, "Standart SushiCo modeli."),
            ("Doğu Otomotiv", "Merkez", "Doğu Otomotiv", "hourly_only", 330, 0, None, 0, 0, 0, 20, 4, 1, "Sadece saatlik."),
            ("SC Petshop", "Merkez", "SC Petshop", "fixed_monthly", 0, 0, None, 0, 0, 79800, 20, 1, 1, "10 saat çalışan 1 kurye için aylık sabit ücret."),
        ]
        conn.executemany(
            """
            INSERT INTO restaurants (
                brand, branch, billing_group, pricing_model, hourly_rate, package_rate,
                package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee,
                vat_rate, target_headcount, active, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            restaurants,
        )

    if not table_has_rows(conn, "personnel"):
        # Seed only the fixed-cost roles you explicitly gave.
        restaurant_map = {f"{row['brand']} - {row['branch']}": row['id'] for row in conn.execute("SELECT id, brand, branch FROM restaurants")}
        seeded_people = [
            ("CK-J01", "Evrem Karapınar", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_monthly", 82500, "Joker havuzu"),
            ("CK-J02", "Ali Kudret Bakar", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_monthly", 82500, "Joker havuzu"),
            ("CK-J03", "Cihan Can Çimen", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_monthly", 117475, "Joker havuzu"),
            ("CK-J04", "Yaşar Tunç Beratoğlu", "Joker", "Aktif", None, None, None, None, "", "Hayır", "", None, None, "fixed_monthly", 101600, "Joker havuzu"),
            ("CK-S01", "Recep Çevik", "Şef", "Aktif", None, None, None, restaurant_map.get("Quick China - Ataşehir"), "", "Hayır", "", None, None, "fixed_monthly", 72050, "Quick China Takım Şefi; saatlik/paket maliyeti yok"),
        ]
        conn.executemany(
            """
            INSERT INTO personnel (
                person_code, full_name, role, status, phone, tc_no, iban,
                assigned_restaurant_id, vehicle_type, motor_rental, current_plate,
                start_date, exit_date, cost_model, monthly_fixed_cost, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seeded_people,
        )
    conn.commit()


def migrate_data(conn: sqlite3.Connection) -> None:
    """Small idempotent data corrections for existing local DBs."""
    corrections = [
        ("Evrem", "Evrem Karapınar", "Joker"),
        ("Ali", "Ali Kudret Bakar", "Joker"),
        ("Cihan", "Cihan Can Çimen", "Joker"),
        ("Tunç", "Yaşar Tunç Beratoğlu", "Joker"),
        ("Quick China Ataşehir Şefi", "Recep Çevik", "Şef"),
    ]
    for old_name, new_name, role in corrections:
        conn.execute(
            "UPDATE personnel SET full_name = ? WHERE full_name = ? AND role = ?",
            (new_name, old_name, role),
        )
    conn.execute(
        "UPDATE personnel SET notes = 'Quick China Takım Şefi; saatlik/paket maliyeti yok' WHERE full_name = 'Recep Çevik' AND role = 'Şef'"
    )
    personnel_cols = {row["name"] for row in conn.execute("PRAGMA table_info(personnel)")}
    if "accounting_type" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN accounting_type TEXT DEFAULT '-'")
    if "new_company_setup" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN new_company_setup TEXT DEFAULT 'Hayır'")
    if "accounting_revenue" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN accounting_revenue REAL DEFAULT 0")
    if "accountant_cost" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN accountant_cost REAL DEFAULT 0")
    if "company_setup_revenue" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN company_setup_revenue REAL DEFAULT 0")
    if "company_setup_cost" not in personnel_cols:
        conn.execute("ALTER TABLE personnel ADD COLUMN company_setup_cost REAL DEFAULT 0")

    restaurant_cols = {row["name"] for row in conn.execute("PRAGMA table_info(restaurants)")}
    if "start_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN start_date TEXT")
    if "end_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN end_date TEXT")
    if "extra_headcount_request" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN extra_headcount_request INTEGER DEFAULT 0")
    if "extra_headcount_request_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN extra_headcount_request_date TEXT")
    if "reduce_headcount_request" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN reduce_headcount_request INTEGER DEFAULT 0")
    if "reduce_headcount_request_date" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN reduce_headcount_request_date TEXT")
    if "contact_name" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN contact_name TEXT")
    if "contact_phone" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN contact_phone TEXT")
    if "contact_email" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN contact_email TEXT")
    if "tax_office" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN tax_office TEXT")
    if "tax_number" not in restaurant_cols:
        conn.execute("ALTER TABLE restaurants ADD COLUMN tax_number TEXT")

    existing = {row["name"] for row in conn.execute("PRAGMA table_info(deductions)")}
    if "equipment_issue_id" not in existing:
        conn.execute("ALTER TABLE deductions ADD COLUMN equipment_issue_id INTEGER")
    conn.commit()


def latest_average_cost(conn: sqlite3.Connection, item_name: str) -> float:
    row = conn.execute(
        """
        SELECT CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount) / SUM(quantity) ELSE 0 END AS avg_cost
        FROM inventory_purchases
        WHERE item_name = ?
        """,
        (item_name,),
    ).fetchone()
    return float(row[0] or 0)


def post_equipment_installments(conn: sqlite3.Connection, issue_id: int, personnel_id: int, issue_date: date, item_name: str, total_sale_amount: float, installment_count: int) -> None:
    if installment_count <= 0 or total_sale_amount <= 0:
        return
    installment_amount = round(total_sale_amount / installment_count, 2)
    dates = [(pd.Timestamp(issue_date) + pd.DateOffset(months=i)).date().isoformat() for i in range(installment_count)]
    existing = conn.execute("SELECT COUNT(*) FROM deductions WHERE equipment_issue_id = ?", (issue_id,)).fetchone()[0]
    if existing:
        return
    for i, due_date in enumerate(dates, start=1):
        conn.execute(
            "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes, equipment_issue_id) VALUES (?, ?, ?, ?, ?, ?)",
            (personnel_id, due_date, "Zimmet Taksiti", installment_amount, f"{item_name} {i}/{installment_count}", issue_id),
        )
    conn.commit()


def fmt_try(v: float) -> str:
    try:
        num = float(v)
    except (TypeError, ValueError):
        return ""
    if abs(num - round(num)) < 0.005:
        s = f"{num:,.0f}"
    else:
        s = f"{num:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if s.endswith(",00"):
        s = s[:-3]
    return f"{s}₺"


def fmt_number(v: float) -> str:
    try:
        num = float(v)
    except (TypeError, ValueError):
        return ""
    if abs(num - round(num)) < 0.005:
        s = f"{num:,.0f}"
    else:
        s = f"{num:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if s.endswith(",00"):
        s = s[:-3]
    return s


def format_display_df(
    df: pd.DataFrame,
    currency_cols: list[str] | None = None,
    percent_cols: list[str] | None = None,
    number_cols: list[str] | None = None,
    rename_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    if rename_map:
        out = out.rename(columns=rename_map)
    for col in currency_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: fmt_try(x) if pd.notna(x) else "")
    for col in percent_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"%{fmt_number(x)}" if pd.notna(x) else "")
    for col in number_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: fmt_number(x) if pd.notna(x) else "")
    return out


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --ck-primary: #004AE0;
                --ck-border: #E7EDF6;
                --ck-text: #111827;
                --ck-muted: #6B7280;
                --ck-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            }

            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(0,74,224,0.05), transparent 20%),
                    linear-gradient(180deg, #F6F8FC 0%, #FCFDFE 100%);
            }

            .block-container {
                max-width: 1460px;
                padding-top: 2.1rem;
                padding-bottom: 2rem;
            }

            [data-testid="stSidebar"] {
                background: #FFFFFF;
                border-right: 1px solid var(--ck-border);
                padding-top: 0.4rem;
            }

            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
                color: var(--ck-text);
            }

            [data-testid="stSidebar"] .stRadio > label {
                font-size: 0.78rem;
                font-weight: 800;
                color: #8A94A6;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: 0.5rem;
            }

            [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 14px;
                padding: 10px 12px;
                margin-bottom: 6px;
                transition: all 0.15s ease;
            }

            [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
                background: #F8FAFF;
                border-color: #E4ECFB;
            }

            [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {
                display: none;
            }

            .ck-side-user {
                background: linear-gradient(180deg, #FFFFFF 0%, #FAFCFF 100%);
                border: 1px solid var(--ck-border);
                border-radius: 16px;
                padding: 12px 14px;
                margin: 0.3rem 0 1rem 0;
            }

            .ck-side-user-name {
                font-size: 0.94rem;
                font-weight: 800;
                color: var(--ck-text);
            }

            .ck-side-user-role {
                font-size: 0.8rem;
                color: var(--ck-muted);
                margin-top: 0.25rem;
            }

            .ck-login-gap { height: 4vh; }

            .ck-login-card {
                background: linear-gradient(180deg, #FFFFFF 0%, #FCFDFF 100%);
                border: 1px solid var(--ck-border);
                border-radius: 24px;
                padding: 28px 26px 22px 26px;
                box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            }

            .ck-login-badge {
                width: fit-content;
                margin: 0 auto 0.9rem auto;
                padding: 6px 10px;
                border-radius: 999px;
                background: #EEF4FF;
                color: #004AE0;
                border: 1px solid #D6E4FF;
                font-size: 0.76rem;
                font-weight: 800;
                letter-spacing: 0.12em;
            }

            .ck-login-title {
                font-size: 2rem;
                font-weight: 800;
                text-align: center;
                letter-spacing: -0.04em;
                color: var(--ck-text);
                margin-bottom: 0.45rem;
                line-height: 1.02;
            }

            .ck-login-subtitle {
                text-align: center;
                color: var(--ck-muted);
                line-height: 1.55;
                margin-bottom: 1.1rem;
                font-size: 0.96rem;
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

            .stButton > button, .stDownloadButton > button {
                border-radius: 14px;
                font-weight: 800;
                border: 1px solid #DCE7FA;
                background: #FFFFFF;
                min-height: 2.7rem;
            }

            .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
                background: #004AE0;
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
                gap: 0.45rem;
            }

            div[data-baseweb="tab-list"] button {
                border-radius: 14px;
                border: 1px solid #DCE7FA;
                background: #F8FAFF;
                padding-top: 0.48rem;
                padding-bottom: 0.48rem;
            }

            div[data-baseweb="tab-list"] button[aria-selected="true"] {
                background: #004AE0;
                border-color: #004AE0;
            }

            div[data-baseweb="tab-list"] button[aria-selected="true"] p {
                color: white !important;
            }

            div[data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
                font-size: 0.94rem;
                font-weight: 800;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_intro(title: str, caption: str) -> None:
    st.subheader(title)
    st.caption(caption)


def fetch_df(conn: sqlite3.Connection, query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, conn, params=params)


def get_restaurant_options(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT id, brand, branch FROM restaurants WHERE active=1 ORDER BY brand, branch").fetchall()
    return {f"{r['brand']} - {r['branch']}": r['id'] for r in rows}


def get_person_options(conn: sqlite3.Connection, active_only: bool = True) -> dict[str, int]:
    sql = "SELECT id, full_name, role, status FROM personnel"
    if active_only:
        sql += " WHERE status='Aktif'"
    sql += " ORDER BY full_name"
    rows = conn.execute(sql).fetchall()
    return {f"{r['full_name']} ({r['role']})": r['id'] for r in rows}


def role_code_prefix(role: str) -> str:
    mapping = {
        "Kurye": "K",
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
        m = re.search(rf"^CK-{re.escape(prefix)}(\d+)$", code)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"CK-{prefix}{max_num + 1:02d}"



def calculate_customer_invoice(group: pd.DataFrame, rule: PricingRule) -> tuple[float, float, float, float]:
    total_hours = float(group["worked_hours"].fillna(0).sum())
    total_packages = float(group["package_count"].fillna(0).sum())

    if rule.pricing_model == "hourly_plus_package":
        subtotal = total_hours * rule.hourly_rate + total_packages * rule.package_rate
    elif rule.pricing_model == "threshold_package":
        low_qty = min(total_packages, float(rule.package_threshold or 0))
        high_qty = max(total_packages - float(rule.package_threshold or 0), 0)
        subtotal = total_hours * rule.hourly_rate + low_qty * rule.package_rate_low + high_qty * rule.package_rate_high
    elif rule.pricing_model == "hourly_only":
        subtotal = total_hours * rule.hourly_rate
    elif rule.pricing_model == "fixed_monthly":
        subtotal = rule.fixed_monthly_fee
    else:
        subtotal = 0.0

    vat = subtotal * (rule.vat_rate / 100.0)
    grand_total = subtotal + vat
    return total_hours, total_packages, subtotal, grand_total


def calculate_personnel_cost(month_df: pd.DataFrame, personnel_df: pd.DataFrame, deductions_df: pd.DataFrame) -> pd.DataFrame:
    results = []
    if personnel_df.empty:
        return pd.DataFrame()

    grouped_entries = month_df.groupby(["actual_personnel_id", "restaurant_id"], dropna=False).agg(
        worked_hours=("worked_hours", "sum"), package_count=("package_count", "sum")
    ).reset_index()

    total_by_person = month_df.groupby("actual_personnel_id", dropna=False).agg(
        worked_hours=("worked_hours", "sum"), package_count=("package_count", "sum")
    ).reset_index()

    deduction_by_person = deductions_df.groupby("personnel_id", dropna=False)["amount"].sum().reset_index(name="deduction_total") if not deductions_df.empty else pd.DataFrame(columns=["personnel_id", "deduction_total"])

    required_cols = ["restaurant_id", "brand", "branch"]
    for col in ["pricing_model", "hourly_rate", "package_rate", "package_threshold", "package_rate_low", "package_rate_high", "fixed_monthly_fee", "vat_rate"]:
        if col not in month_df.columns:
            month_df[col] = None
    restaurant_rules = month_df[["restaurant_id", "pricing_model", "brand", "branch"]].drop_duplicates()

    for _, person in personnel_df.iterrows():
        person_id = person["id"]
        person_entries = grouped_entries[grouped_entries["actual_personnel_id"] == person_id].copy()
        totals = total_by_person[total_by_person["actual_personnel_id"] == person_id]
        worked_hours = float(totals["worked_hours"].sum()) if not totals.empty else 0.0
        packages = float(totals["package_count"].sum()) if not totals.empty else 0.0
        deductions = float(deduction_by_person.loc[deduction_by_person["personnel_id"] == person_id, "deduction_total"].sum()) if not deduction_by_person.empty else 0.0

        if person["cost_model"] == "fixed_monthly":
            gross_cost = float(person["monthly_fixed_cost"] or 0)
        else:
            hourly_cost = worked_hours * COURIER_HOURLY_COST
            package_cost = 0.0
            for _, e in person_entries.iterrows():
                rid = e["restaurant_id"]
                pkg = float(e["package_count"] or 0)
                rule_row = restaurant_rules[restaurant_rules["restaurant_id"] == rid]
                pricing_model = rule_row["pricing_model"].iloc[0] if not rule_row.empty else "hourly_plus_package"
                brand = rule_row["brand"].iloc[0] if not rule_row.empty else ""
                if brand == "Quick China":
                    package_cost += pkg * COURIER_PACKAGE_COST_QC
                else:
                    low_qty = min(pkg, PACKAGE_THRESHOLD_DEFAULT)
                    high_qty = max(pkg - PACKAGE_THRESHOLD_DEFAULT, 0)
                    package_cost += low_qty * COURIER_PACKAGE_COST_DEFAULT_LOW + high_qty * COURIER_PACKAGE_COST_DEFAULT_HIGH
            gross_cost = hourly_cost + package_cost

        net_cost = gross_cost - deductions
        results.append({
            "personnel_id": person_id,
            "personel": person["full_name"],
            "rol": person["role"],
            "durum": person["status"],
            "calisma_saati": worked_hours,
            "paket": packages,
            "brut_maliyet": gross_cost,
            "kesinti": deductions,
            "net_maliyet": net_cost,
            "maliyet_modeli": person["cost_model"],
        })
    return pd.DataFrame(results).sort_values(["rol", "personel"])


def month_bounds(selected_month: str) -> tuple[str, str]:
    year, month = map(int, selected_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"



def render_dashboard_panel(title: str, rows: list[tuple[str, str]]) -> None:
    body = ''.join([f'<div class="ck-list-row"><span>{left}</span><span class="ck-chip">{right}</span></div>' for left, right in rows])
    st.markdown(f'<div class="ck-panel"><div class="ck-panel-title">{title}</div>{body}</div>', unsafe_allow_html=True)


def dashboard_tab(conn: sqlite3.Connection) -> None:
    section_intro("Ana Dashboard", "Operasyonun genel görünümü, şube özeti ve öne çıkan içgörüler.")

    entries = fetch_df(conn, "SELECT * FROM daily_entries")
    active_restaurants = conn.execute("SELECT COUNT(*) FROM restaurants WHERE active=1").fetchone()[0]
    active_people = conn.execute("SELECT COUNT(*) FROM personnel WHERE status='Aktif'").fetchone()[0]
    joker_count = conn.execute("SELECT COUNT(*) FROM personnel WHERE role='Joker' AND status='Aktif'").fetchone()[0]

    total_packages = float(entries["package_count"].sum()) if not entries.empty else 0
    total_hours = float(entries["worked_hours"].sum()) if not entries.empty else 0
    today_packages = 0.0
    package_per_hour = (total_packages / total_hours) if total_hours else 0

    if not entries.empty and "entry_date" in entries.columns:
        tmp = entries.copy()
        tmp["entry_date"] = pd.to_datetime(tmp["entry_date"], errors="coerce").dt.date
        today_df = tmp[tmp["entry_date"] == date.today()]
        today_packages = float(today_df["package_count"].sum()) if not today_df.empty else 0

    row1 = st.columns(3, gap="large")
    row1[0].metric("Aktif Restoran", fmt_number(active_restaurants))
    row1[1].metric("Aktif Personel", fmt_number(active_people))
    row1[2].metric("Joker Havuzu", fmt_number(joker_count))

    row2 = st.columns(2, gap="large")
    row2[0].metric("Bugün Paket", fmt_number(today_packages))
    row2[1].metric("Paket / Saat", fmt_number(package_per_hour))

    if entries.empty:
        st.info("Henüz günlük puantaj kaydı yok.")
        return

    perf = fetch_df(conn, """
        SELECT
            r.brand || ' - ' || r.branch AS restoran,
            SUM(d.package_count) AS paket,
            SUM(d.worked_hours) AS saat
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        GROUP BY 1
        ORDER BY paket DESC
    """)
    perf["paket_saat"] = perf.apply(lambda x: (float(x["paket"]) / float(x["saat"])) if float(x["saat"] or 0) else 0, axis=1)

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown("##### Şube Operasyon Özeti")
        display = format_display_df(
            perf,
            number_cols=["paket", "saat", "paket_saat"],
            rename_map={
                "restoran": "Restoran",
                "paket": "Toplam Paket",
                "saat": "Toplam Saat",
                "paket_saat": "Paket / Saat",
            },
        )
        st.dataframe(display, width='stretch', hide_index=True)

    with right:
        top_rest = perf.iloc[0]["restoran"] if not perf.empty else "-"
        top_pkg = fmt_number(perf.iloc[0]["paket"]) if not perf.empty else "0"
        best_row = perf.sort_values("paket_saat", ascending=False).iloc[0] if not perf.empty else None
        best_name = best_row["restoran"] if best_row is not None else "-"
        best_eff = fmt_number(best_row["paket_saat"]) if best_row is not None else "0"

        render_dashboard_panel(
            "Hızlı İçgörüler",
            [
                ("En yüksek hacimli şube", f"{top_rest} · {top_pkg} paket"),
                ("En verimli şube", f"{best_name} · {best_eff}"),
                ("Toplam çalışma saati", fmt_number(total_hours)),
            ],
        )

        role_df = fetch_df(conn, "SELECT role, COUNT(*) AS adet FROM personnel WHERE status='Aktif' GROUP BY role ORDER BY adet DESC")
        role_rows = [(row["role"], fmt_number(row["adet"])) for _, row in role_df.iterrows()] if not role_df.empty else [("Veri", "0")]
        render_dashboard_panel("Aktif Kadro Dağılımı", role_rows)


def restaurants_tab(conn: sqlite3.Connection) -> None:
    st.subheader("Restoran Yönetimi | Şube, fiyat modeli ve aktif/pasif durumu")
    st.caption("Yeni restoran ekle, fiyat modelini tanımla, aktif/pasif yönet ve yanlış test kayıtlarını sil.")
    df = fetch_df(conn, "SELECT * FROM restaurants ORDER BY brand, branch")
    st.dataframe(df, width='stretch', hide_index=True)

    st.markdown("### Restoran durumu yönetimi")
    if not df.empty:
        action_labels = {
            f"{row['brand']} - {row['branch']} (ID: {row['id']})": int(row['id'])
            for _, row in df.iterrows()
        }
        c1, c2, c3 = st.columns([3, 1, 1])
        selected_label = c1.selectbox("Restoran / şube seç", list(action_labels.keys()), key="restaurant_action_select")
        selected_id = action_labels[selected_label]
        selected_row = df.loc[df["id"] == selected_id].iloc[0]
        current_active = int(selected_row["active"])
        if c2.button("Pasife al" if current_active == 1 else "Aktifleştir", width='stretch'):
            conn.execute("UPDATE restaurants SET active = ? WHERE id = ?", (0 if current_active == 1 else 1, selected_id))
            conn.commit()
            st.success("Restoran durumu güncellendi.")
            st.rerun()
        if c3.button("Kalıcı sil", width='stretch'):
            linked_people = conn.execute("SELECT COUNT(*) FROM personnel WHERE assigned_restaurant_id = ?", (selected_id,)).fetchone()[0]
            linked_puantaj = conn.execute("SELECT COUNT(*) FROM daily_entries WHERE restaurant_id = ?", (selected_id,)).fetchone()[0]
            linked_deductions = conn.execute(
                """
                SELECT COUNT(*)
                FROM deductions d
                JOIN personnel p ON p.id = d.personnel_id
                WHERE p.assigned_restaurant_id = ?
                """,
                (selected_id,),
            ).fetchone()[0]
            if linked_people or linked_puantaj or linked_deductions:
                st.error("Bu restorana bağlı personel, puantaj veya kesinti kaydı var. Önce pasife alman daha doğru olur.")
            else:
                conn.execute("DELETE FROM restaurants WHERE id = ?", (selected_id,))
                conn.commit()
                st.success("Restoran kalıcı olarak silindi.")
                st.rerun()
    else:
        st.info("Henüz kayıtlı restoran yok.")
        selected_row = None

    with st.expander("Yeni restoran / şube ekle"):
        with st.form("restaurant_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            brand = c1.text_input("Marka")
            branch = c2.text_input("Şube")
            billing_group = c3.text_input("Fatura grubu / vergi levhası")
            pricing_model = st.selectbox("Fiyat modeli", ["hourly_plus_package", "threshold_package", "hourly_only", "fixed_monthly"])
            c4, c5, c6 = st.columns(3)
            hourly_rate = c4.number_input("Saatlik ücret", min_value=0.0, value=0.0, step=1.0)
            package_rate = c5.number_input("Paket primi", min_value=0.0, value=0.0, step=1.0)
            package_threshold = c6.number_input("Paket eşiği", min_value=0, value=390, step=1)
            c7, c8, c9 = st.columns(3)
            package_rate_low = c7.number_input("Eşik altı prim", min_value=0.0, value=0.0, step=0.25)
            package_rate_high = c8.number_input("Eşik üstü prim", min_value=0.0, value=0.0, step=0.25)
            fixed_fee = c9.number_input("Sabit aylık ücret", min_value=0.0, value=0.0, step=100.0)
            c10, c11 = st.columns(2)
            vat_rate = c10.number_input("KDV %", min_value=0.0, value=20.0, step=1.0)
            headcount = c11.number_input("Hedef kadro", min_value=0, value=0, step=1)

            c12, c13 = st.columns(2)
            start_date_val = c12.date_input("Başlangıç tarihi", value=None)
            end_date_val = c13.date_input("Bitiş tarihi", value=None)

            c14, c15, c16 = st.columns(3)
            extra_req = c14.number_input("Ek kurye talep sayısı", min_value=0, value=0, step=1)
            extra_req_date = c15.date_input("Ek kurye talep tarihi", value=None)
            reduce_req = c16.number_input("Kurye azaltma talep sayısı", min_value=0, value=0, step=1)

            c17, c18 = st.columns(2)
            reduce_req_date = c17.date_input("Kurye azaltma talep tarihi", value=None)
            contact_name = c18.text_input("Yetkili ad soyad")

            c19, c20, c21 = st.columns(3)
            contact_phone = c19.text_input("Yetkili telefon")
            contact_email = c20.text_input("Yetkili mail")
            tax_office = c21.text_input("Vergi Dairesi")

            tax_number = st.text_input("Vergi Numarası")
            notes = st.text_area("Notlar")
            submitted = st.form_submit_button("Kaydet")
            if submitted and brand and branch:
                conn.execute(
                    """
                    INSERT INTO restaurants (
                        brand, branch, billing_group, pricing_model, hourly_rate, package_rate,
                        package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee,
                        vat_rate, target_headcount, start_date, end_date,
                        extra_headcount_request, extra_headcount_request_date,
                        reduce_headcount_request, reduce_headcount_request_date,
                        contact_name, contact_phone, contact_email, tax_office, tax_number,
                        active, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        brand, branch, billing_group, pricing_model, hourly_rate, package_rate,
                        package_threshold, package_rate_low, package_rate_high, fixed_fee,
                        vat_rate, headcount,
                        start_date_val.isoformat() if isinstance(start_date_val, date) else None,
                        end_date_val.isoformat() if isinstance(end_date_val, date) else None,
                        extra_req,
                        extra_req_date.isoformat() if isinstance(extra_req_date, date) else None,
                        reduce_req,
                        reduce_req_date.isoformat() if isinstance(reduce_req_date, date) else None,
                        contact_name, contact_phone, contact_email, tax_office, tax_number,
                        notes
                    ),
                )
                conn.commit()
                st.success("Restoran kaydedildi. Sayfayı yenilemeden sekmeler arasında geçiş yapabilirsin.")
                st.rerun()

    if selected_row is not None:
        st.markdown("### Restoran detaylarını güncelle")
        with st.form("restaurant_edit_form"):
            c1, c2, c3 = st.columns(3)
            edit_brand = c1.text_input("Marka", value=selected_row["brand"] or "")
            edit_branch = c2.text_input("Şube", value=selected_row["branch"] or "")
            edit_billing_group = c3.text_input("Fatura grubu / vergi levhası", value=selected_row["billing_group"] or "")
            pricing_models = ["hourly_plus_package", "threshold_package", "hourly_only", "fixed_monthly"]
            edit_pricing_model = st.selectbox("Fiyat modeli", pricing_models, index=pricing_models.index(selected_row["pricing_model"]) if selected_row["pricing_model"] in pricing_models else 0)

            c4, c5, c6 = st.columns(3)
            edit_hourly_rate = c4.number_input("Saatlik ücret", min_value=0.0, value=float(selected_row["hourly_rate"] or 0.0), step=1.0)
            edit_package_rate = c5.number_input("Paket primi", min_value=0.0, value=float(selected_row["package_rate"] or 0.0), step=1.0)
            edit_package_threshold = c6.number_input("Paket eşiği", min_value=0, value=int(selected_row["package_threshold"] or 0), step=1)

            c7, c8, c9 = st.columns(3)
            edit_package_rate_low = c7.number_input("Eşik altı prim", min_value=0.0, value=float(selected_row["package_rate_low"] or 0.0), step=0.25)
            edit_package_rate_high = c8.number_input("Eşik üstü prim", min_value=0.0, value=float(selected_row["package_rate_high"] or 0.0), step=0.25)
            edit_fixed_fee = c9.number_input("Sabit aylık ücret", min_value=0.0, value=float(selected_row["fixed_monthly_fee"] or 0.0), step=100.0)

            c10, c11 = st.columns(2)
            edit_vat_rate = c10.number_input("KDV %", min_value=0.0, value=float(selected_row["vat_rate"] or 20.0), step=1.0)
            edit_headcount = c11.number_input("Hedef kadro", min_value=0, value=int(selected_row["target_headcount"] or 0), step=1)

            c12, c13 = st.columns(2)
            sd = datetime.strptime(selected_row["start_date"], "%Y-%m-%d").date() if selected_row["start_date"] else None
            ed = datetime.strptime(selected_row["end_date"], "%Y-%m-%d").date() if selected_row["end_date"] else None
            edit_start_date = c12.date_input("Başlangıç tarihi", value=sd)
            edit_end_date = c13.date_input("Bitiş tarihi", value=ed)

            c14, c15, c16 = st.columns(3)
            edit_extra_req = c14.number_input("Ek kurye talep sayısı", min_value=0, value=int(selected_row["extra_headcount_request"] or 0), step=1)
            erd = datetime.strptime(selected_row["extra_headcount_request_date"], "%Y-%m-%d").date() if selected_row["extra_headcount_request_date"] else None
            edit_extra_req_date = c15.date_input("Ek kurye talep tarihi", value=erd)
            edit_reduce_req = c16.number_input("Kurye azaltma talep sayısı", min_value=0, value=int(selected_row["reduce_headcount_request"] or 0), step=1)

            c17, c18 = st.columns(2)
            rrd = datetime.strptime(selected_row["reduce_headcount_request_date"], "%Y-%m-%d").date() if selected_row["reduce_headcount_request_date"] else None
            edit_reduce_req_date = c17.date_input("Kurye azaltma talep tarihi", value=rrd)
            edit_contact_name = c18.text_input("Yetkili ad soyad", value=selected_row["contact_name"] or "")

            c19, c20, c21 = st.columns(3)
            edit_contact_phone = c19.text_input("Yetkili telefon", value=selected_row["contact_phone"] or "")
            edit_contact_email = c20.text_input("Yetkili mail", value=selected_row["contact_email"] or "")
            edit_tax_office = c21.text_input("Vergi Dairesi", value=selected_row["tax_office"] or "")

            edit_tax_number = st.text_input("Vergi Numarası", value=selected_row["tax_number"] or "")
            edit_notes = st.text_area("Notlar", value=selected_row["notes"] or "")

            if st.form_submit_button("Restoranı güncelle"):
                conn.execute(
                    """
                    UPDATE restaurants
                    SET brand = ?, branch = ?, billing_group = ?, pricing_model = ?, hourly_rate = ?, package_rate = ?,
                        package_threshold = ?, package_rate_low = ?, package_rate_high = ?, fixed_monthly_fee = ?,
                        vat_rate = ?, target_headcount = ?, start_date = ?, end_date = ?,
                        extra_headcount_request = ?, extra_headcount_request_date = ?,
                        reduce_headcount_request = ?, reduce_headcount_request_date = ?,
                        contact_name = ?, contact_phone = ?, contact_email = ?, tax_office = ?, tax_number = ?, notes = ?
                    WHERE id = ?
                    """,
                    (
                        edit_brand, edit_branch, edit_billing_group, edit_pricing_model, edit_hourly_rate, edit_package_rate,
                        edit_package_threshold, edit_package_rate_low, edit_package_rate_high, edit_fixed_fee,
                        edit_vat_rate, edit_headcount,
                        edit_start_date.isoformat() if isinstance(edit_start_date, date) else None,
                        edit_end_date.isoformat() if isinstance(edit_end_date, date) else None,
                        edit_extra_req,
                        edit_extra_req_date.isoformat() if isinstance(edit_extra_req_date, date) else None,
                        edit_reduce_req,
                        edit_reduce_req_date.isoformat() if isinstance(edit_reduce_req_date, date) else None,
                        edit_contact_name, edit_contact_phone, edit_contact_email, edit_tax_office, edit_tax_number, edit_notes,
                        selected_id
                    ),
                )
                conn.commit()
                st.success("Restoran güncellendi.")
                st.rerun()
def personnel_tab(conn: sqlite3.Connection) -> None:
    st.subheader("Personel Yönetimi | Kurye, Joker, Şef ve motor bilgileri")
    st.caption("Personel kartı oluştur, düzenle, aktif/pasif yap ve motor/plaka geçmişini takip et.")
    q = """
    SELECT p.*, r.brand || ' - ' || r.branch AS restoran
    FROM personnel p
    LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
    ORDER BY p.full_name
    """
    df = fetch_df(conn, q)
    st.dataframe(df, width='stretch', hide_index=True)

    rest_opts = get_restaurant_options(conn)
    rest_opts_with_blank = {"-": None, **rest_opts}

    with st.expander("Yeni personel ekle"):
        with st.form("personnel_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            full_name = c1.text_input("Ad soyad")
            role = c2.selectbox("Rol", ["Kurye", "Joker", "Şef"])
            code_preview = next_person_code(conn, role)
            c3.text_input("Otomatik personel kodu", value=code_preview, disabled=True)

            c4, c5, c6 = st.columns(3)
            status = c4.selectbox("Durum", ["Aktif", "Pasif"])
            phone = c5.text_input("Telefon")
            assigned_label = c6.selectbox("Ana restoran", list(rest_opts_with_blank.keys()))

            c7, c8, c9 = st.columns(3)
            tc_no = c7.text_input("TC Kimlik No")
            iban = c8.text_input("IBAN")
            accounting_type = c9.selectbox("Muhasebe", ["-", "Çat Kapında Muhasebe", "Kendi Muhasebecisi"])

            c10, c11, c12 = st.columns(3)
            new_company_setup = c10.selectbox("Yeni şirket açılışı", ["Hayır", "Evet"])
            accounting_revenue = c11.number_input("Muhasebeden aldığımız ücret", min_value=0.0, value=0.0, step=100.0)
            accountant_cost = c12.number_input("Muhasebeciye ödediğimiz", min_value=0.0, value=0.0, step=100.0)

            c13, c14 = st.columns(2)
            company_setup_revenue = c13.number_input("Şirket açılışından aldığımız ücret", min_value=0.0, value=0.0, step=100.0)
            company_setup_cost = c14.number_input("Şirket açılış maliyeti", min_value=0.0, value=0.0, step=100.0)

            c15, c16, c17 = st.columns(3)
            vehicle_type = c15.selectbox("Motor tipi", ["", "Çat Kapında", "Kendi"])
            motor_rental = c16.selectbox("Motor kiralama", ["Hayır", "Evet"])
            current_plate = c17.text_input("Güncel plaka")

            c18, c19, c20 = st.columns(3)
            cost_model = c18.selectbox("Maliyet modeli", ["standard_courier", "fixed_monthly"])
            monthly_fixed_cost = c19.number_input("Aylık sabit maliyet", min_value=0.0, value=0.0, step=100.0)
            start_date = c20.date_input("İşe giriş tarihi", value=None)

            notes = st.text_area("Notlar")
            submitted = st.form_submit_button("Kaydet")
            if submitted and full_name:
                assigned_id = rest_opts_with_blank.get(assigned_label)
                start_date_str = start_date.isoformat() if isinstance(start_date, date) else None
                auto_code = next_person_code(conn, role)
                conn.execute(
                    """
                    INSERT INTO personnel (
                        person_code, full_name, role, status, phone, tc_no, iban,
                        accounting_type, new_company_setup, accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost,
                        assigned_restaurant_id, vehicle_type, motor_rental, current_plate, start_date,
                        cost_model, monthly_fixed_cost, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (auto_code, full_name, role, status, phone, tc_no, iban,
                     accounting_type, new_company_setup, accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost,
                     assigned_id, vehicle_type, motor_rental, current_plate, start_date_str,
                     cost_model, monthly_fixed_cost, notes),
                )
                conn.commit()
                st.success(f"Personel kaydedildi. Kod: {auto_code}")
                st.rerun()

    st.markdown("### Personel düzenle / pasife al")
    if not df.empty:
        person_labels = {
            f"{row['full_name']} | {row['role']} | Kod: {row['person_code'] or '-'} | ID: {row['id']}": int(row['id'])
            for _, row in df.iterrows()
        }
        selected_label = st.selectbox("Düzenlenecek personel", list(person_labels.keys()), key="edit_person_select")
        selected_id = person_labels[selected_label]
        row = df.loc[df['id'] == selected_id].iloc[0]

        assigned_value = row['restoran'] if pd.notna(row['restoran']) and row['restoran'] in rest_opts else '-'
        status_options = ["Aktif", "Pasif"]
        role_options = ["Kurye", "Joker", "Şef"]
        vehicle_options = ["", "Çat Kapında", "Kendi"]
        rental_options = ["Hayır", "Evet"]
        cost_options = ["standard_courier", "fixed_monthly"]

        with st.form("personnel_edit_form"):
            edit_prefix = role_code_prefix(row['role'])
            current_num = ""
            m = re.search(rf"^CK-{re.escape(edit_prefix)}(\d+)$", row['person_code'] or "")
            if m:
                current_num = m.group(1)

            c1, c2, c3 = st.columns(3)
            edit_role = c1.selectbox("Rol", role_options, index=role_options.index(row['role']) if row['role'] in role_options else 0)
            suggested_code = next_person_code(conn, edit_role, exclude_id=selected_id)
            new_prefix = role_code_prefix(edit_role)
            existing_num = ""
            m2 = re.search(rf"^CK-{re.escape(new_prefix)}(\d+)$", row['person_code'] or "")
            if m2:
                existing_num = m2.group(1)
            code_default = row['person_code'] if row['role'] == edit_role and row['person_code'] else (f"CK-{new_prefix}{existing_num or suggested_code.split(new_prefix)[1]}")
            edit_code = c2.text_input("Personel kodu", value=code_default or suggested_code)
            c3.caption(f"Önerilen kod: {suggested_code}")

            c4, c5, c6 = st.columns(3)
            edit_name = c4.text_input("Ad soyad", value=row['full_name'] or "")
            edit_status = c5.selectbox("Durum", status_options, index=status_options.index(row['status']) if row['status'] in status_options else 0)
            edit_phone = c6.text_input("Telefon", value=row['phone'] or "")

            c7, c8, c9 = st.columns(3)
            edit_tc = c7.text_input("TC Kimlik No", value=row['tc_no'] or "")
            edit_iban = c8.text_input("IBAN", value=row['iban'] or "")
            accounting_options = ["-", "Çat Kapında Muhasebe", "Kendi Muhasebecisi"]
            current_acc = row['accounting_type'] if pd.notna(row['accounting_type']) else "-"
            edit_accounting = c9.selectbox("Muhasebe", accounting_options, index=accounting_options.index(current_acc) if current_acc in accounting_options else 0)

            c10, c11, c12 = st.columns(3)
            new_company_options = ["Hayır", "Evet"]
            current_newco = row['new_company_setup'] if pd.notna(row['new_company_setup']) else "Hayır"
            edit_new_company = c10.selectbox("Yeni şirket açılışı", new_company_options, index=new_company_options.index(current_newco) if current_newco in new_company_options else 0)
            edit_accounting_revenue = c11.number_input("Muhasebeden aldığımız ücret", min_value=0.0, value=float(row['accounting_revenue'] or 0.0), step=100.0)
            edit_accountant_cost = c12.number_input("Muhasebeciye ödediğimiz", min_value=0.0, value=float(row['accountant_cost'] or 0.0), step=100.0)

            c13, c14 = st.columns(2)
            edit_company_setup_revenue = c13.number_input("Şirket açılışından aldığımız ücret", min_value=0.0, value=float(row['company_setup_revenue'] or 0.0), step=100.0)
            edit_company_setup_cost = c14.number_input("Şirket açılış maliyeti", min_value=0.0, value=float(row['company_setup_cost'] or 0.0), step=100.0)

            c15, c16, c17 = st.columns(3)
            edit_restaurant = c15.selectbox("Ana restoran", list(rest_opts_with_blank.keys()), index=list(rest_opts_with_blank.keys()).index(assigned_value) if assigned_value in rest_opts_with_blank else 0)
            edit_vehicle = c16.selectbox("Motor tipi", vehicle_options, index=vehicle_options.index(row['vehicle_type']) if row['vehicle_type'] in vehicle_options else 0)
            edit_rental = c17.selectbox("Motor kiralama", rental_options, index=rental_options.index(row['motor_rental']) if row['motor_rental'] in rental_options else 0)

            c18, c19, c20 = st.columns(3)
            edit_plate = c18.text_input("Güncel plaka", value=row['current_plate'] or "")
            edit_cost_model = c19.selectbox("Maliyet modeli", cost_options, index=cost_options.index(row['cost_model']) if row['cost_model'] in cost_options else 0)
            edit_monthly_cost = c20.number_input("Aylık sabit maliyet", min_value=0.0, value=float(row['monthly_fixed_cost'] or 0.0), step=100.0)

            c21, c22 = st.columns(2)
            start_val = datetime.strptime(row['start_date'], "%Y-%m-%d").date() if row['start_date'] else None
            edit_start_date = c21.date_input("İşe giriş tarihi", value=start_val)
            edit_notes = st.text_area("Notlar", value=row['notes'] or "")

            c23, c24 = st.columns(2)
            update_clicked = c23.form_submit_button("Personeli güncelle", width='stretch')
            toggle_clicked = c24.form_submit_button("Aktif/Pasif durumunu değiştir", width='stretch')

            if update_clicked:
                assigned_id = rest_opts_with_blank.get(edit_restaurant)
                start_date_str = edit_start_date.isoformat() if isinstance(edit_start_date, date) else None
                conn.execute(
                    """
                    UPDATE personnel
                    SET person_code=?, full_name=?, role=?, status=?, phone=?, tc_no=?, iban=?,
                        accounting_type=?, new_company_setup=?, accounting_revenue=?, accountant_cost=?, company_setup_revenue=?, company_setup_cost=?, assigned_restaurant_id=?,
                        vehicle_type=?, motor_rental=?, current_plate=?, start_date=?,
                        cost_model=?, monthly_fixed_cost=?, notes=?
                    WHERE id=?
                    """,
                    (edit_code, edit_name, edit_role, edit_status, edit_phone, edit_tc, edit_iban,
                     edit_accounting, edit_new_company, edit_accounting_revenue, edit_accountant_cost, edit_company_setup_revenue, edit_company_setup_cost, assigned_id,
                     edit_vehicle, edit_rental, edit_plate, start_date_str,
                     edit_cost_model, edit_monthly_cost, edit_notes, selected_id),
                )
                conn.commit()
                st.success("Personel kaydı güncellendi.")
                st.rerun()

            if toggle_clicked:
                new_status = "Pasif" if row['status'] == "Aktif" else "Aktif"
                exit_date = date.today().isoformat() if new_status == "Pasif" else None
                conn.execute("UPDATE personnel SET status=?, exit_date=? WHERE id=?", (new_status, exit_date, selected_id))
                conn.commit()
                st.success(f"Personel durumu {new_status} olarak güncellendi.")
                st.rerun()
    else:
        st.info("Henüz personel kaydı yok.")

    with st.expander("Plaka değişimi / motor zimmeti ekle"):
        person_opts = get_person_options(conn, active_only=False)
        if person_opts:
            with st.form("plate_form", clear_on_submit=True):
                person_label = st.selectbox("Personel", list(person_opts.keys()))
                plate = st.text_input("Yeni plaka")
                c1, c2 = st.columns(2)
                start_dt = c1.date_input("Başlangıç", value=date.today())
                end_dt = c2.date_input("Bitiş", value=None)
                reason = st.selectbox("Sebep", ["Yeni zimmet", "Kaza", "Bakım", "Geçici değişim", "Diğer"])
                submitted = st.form_submit_button("Plaka geçmişine ekle")
                if submitted and plate:
                    pid = person_opts[person_label]
                    conn.execute("UPDATE plate_history SET active=0, end_date=? WHERE personnel_id=? AND active=1", (start_dt.isoformat(), pid))
                    conn.execute(
                        "INSERT INTO plate_history (personnel_id, plate, start_date, end_date, reason, active) VALUES (?, ?, ?, ?, ?, 1)",
                        (pid, plate, start_dt.isoformat(), end_dt.isoformat() if isinstance(end_dt, date) else None, reason),
                    )
                    conn.execute("UPDATE personnel SET current_plate=? WHERE id=?", (plate, pid))
                    conn.commit()
                    st.success("Plaka geçmişi güncellendi.")
                    st.rerun()
        else:
            st.info("Önce personel eklenmeli.")


def daily_entries_tab(conn: sqlite3.Connection) -> None:
    st.subheader("Günlük Puantaj | Saat, paket ve fiilen çalışan personel kaydı")
    st.caption("WhatsApp teyidi sonrası şube bazlı günlük saat ve paket girişlerini bu ekrandan yap.")
    rest_opts = get_restaurant_options(conn)
    person_opts = get_person_options(conn)
    with st.form("daily_entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        entry_date = c1.date_input("Tarih", value=date.today())
        rest_label = c2.selectbox("Restoran / şube", list(rest_opts.keys()))
        status = c3.selectbox("Durum", ["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"])
        c4, c5 = st.columns(2)
        planned_label = c4.selectbox("Planlanan personel", ["-"] + list(person_opts.keys()))
        actual_label = c5.selectbox("Fiilen çalışan personel", ["-"] + list(person_opts.keys()))
        c6, c7 = st.columns(2)
        worked_hours = c6.number_input("Çalışılan saat", min_value=0.0, value=10.0, step=0.5)
        package_count = c7.number_input("Paket", min_value=0.0, value=0.0, step=1.0)
        notes = st.text_area("Not")
        submitted = st.form_submit_button("Kaydet")
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
    st.dataframe(df, width='stretch', hide_index=True)

    if not df.empty:
        entry_map = {
            f"{row['entry_date']} | {row['restoran']} | {row['calisan']} | {row['package_count']} paket | ID:{row['id']}": int(row['id'])
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

        current_rest_label = next((label for label, rid in rest_opts.items() if rid == selected['restaurant_id']), list(rest_opts.keys())[0])
        planned_default = "-"
        actual_default = "-"
        for label, pid in person_opts.items():
            if selected['planned_personnel_id'] == pid:
                planned_default = label
            if selected['actual_personnel_id'] == pid:
                actual_default = label

        with st.form(f"daily_entry_edit_form_{selected_id}"):
            e1, e2, e3 = st.columns(3)
            edit_date = e1.date_input("Tarih", value=datetime.fromisoformat(selected['entry_date']).date())
            rest_labels = list(rest_opts.keys())
            edit_rest_label = e2.selectbox("Restoran / şube", rest_labels, index=rest_labels.index(current_rest_label))
            edit_status = e3.selectbox(
                "Durum",
                ["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"],
                index=["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"].index(selected['status']) if selected['status'] in ["Normal", "Joker", "İzin", "Gelmedi", "Çıkış yaptı", "Şef"] else 0,
            )
            e4, e5 = st.columns(2)
            person_labels = ["-"] + list(person_opts.keys())
            edit_planned_label = e4.selectbox("Planlanan personel", person_labels, index=person_labels.index(planned_default))
            edit_actual_label = e5.selectbox("Fiilen çalışan personel", person_labels, index=person_labels.index(actual_default))
            e6, e7 = st.columns(2)
            edit_hours = e6.number_input("Çalışılan saat", min_value=0.0, value=float(selected['worked_hours'] or 0), step=0.5)
            edit_package = e7.number_input("Paket", min_value=0.0, value=float(selected['package_count'] or 0), step=1.0)
            edit_notes = st.text_area("Not", value=selected['notes'])
            u1, u2 = st.columns(2)
            update_clicked = u1.form_submit_button("Kaydı güncelle", width='stretch')
            delete_clicked = u2.form_submit_button("Kaydı sil", width='stretch')

            if update_clicked:
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
                st.success("Günlük puantaj kaydı güncellendi.")
                st.rerun()

            if delete_clicked:
                conn.execute("DELETE FROM daily_entries WHERE id = ?", (selected_id,))
                conn.commit()
                st.success("Günlük puantaj kaydı silindi.")
                st.rerun()
    else:
        st.info("Henüz günlük puantaj kaydı yok.")


def deductions_tab(conn: sqlite3.Connection) -> None:
    section_intro("💸 Kesinti Yönetimi | Motor kira, yakıt, HGS, ceza, muhasebe ve şirket açılış ücretleri", "Personel bazlı düşülecek tutarları buradan kaydet; raporlarda net maliyete yansır.")
    person_opts = get_person_options(conn, active_only=False)
    deduction_types = ["Motor kira", "Yakıt", "HGS", "İdari ceza", "Hasar", "Zimmet", "Muhasebe Ücreti", "Şirket Açılış Ücreti", "Fatura Edilmeyen Tutar", "Diğer"]

    with st.form("deduction_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        person_label = c1.selectbox("Personel", list(person_opts.keys()))
        ded_date = c2.date_input("Tarih", value=date.today())
        ded_type = c3.selectbox("Kesinti türü", deduction_types)
        amount = st.number_input("Tutar", min_value=0.0, value=0.0, step=50.0)
        notes = st.text_input("Açıklama")
        submitted = st.form_submit_button("Kesinti ekle")
        if submitted and amount > 0:
            conn.execute(
                "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes) VALUES (?, ?, ?, ?, ?)",
                (person_opts[person_label], ded_date.isoformat(), ded_type, amount, notes),
            )
            conn.commit()
            st.success("Kesinti kaydedildi.")
            st.rerun()

    raw_df = fetch_df(conn, """
        SELECT d.id, d.personnel_id, d.deduction_date, p.full_name AS personel, d.deduction_type, d.amount, d.notes
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        ORDER BY d.deduction_date DESC, d.id DESC
    """)

    display_df = format_display_df(
        raw_df.drop(columns=["id", "personnel_id"], errors="ignore"),
        currency_cols=["Tutar"],
        rename_map={
            "deduction_date": "Tarih",
            "personel": "Personel",
            "deduction_type": "Kesinti Türü",
            "amount": "Tutar",
            "notes": "Açıklama",
        },
    )
    st.dataframe(display_df, width='stretch', hide_index=True)

    st.markdown("### Mevcut kesinti kaydı düzenle / sil")
    if raw_df.empty:
        st.info("Henüz kesinti kaydı yok.")
        return

    deduction_options = {
        f"#{int(row['id'])} | {row['deduction_date']} | {row['personel']} | {row['deduction_type']} | {fmt_try(row['amount'])}": int(row["id"])
        for _, row in raw_df.iterrows()
    }
    selected_label = st.selectbox("Düzenlenecek kayıt", list(deduction_options.keys()), key="deduction_edit_select")
    selected_id = deduction_options[selected_label]
    row = raw_df.loc[raw_df["id"] == selected_id].iloc[0]

    reverse_person = {v: k for k, v in person_opts.items()}
    edit_person_label = reverse_person.get(int(row["personnel_id"]))
    edit_person_index = list(person_opts.keys()).index(edit_person_label) if edit_person_label in person_opts else 0
    edit_type_index = deduction_types.index(row["deduction_type"]) if row["deduction_type"] in deduction_types else len(deduction_types) - 1

    with st.form("deduction_edit_form"):
        c1, c2, c3 = st.columns(3)
        edit_person = c1.selectbox("Personel", list(person_opts.keys()), index=edit_person_index)
        current_date = datetime.strptime(str(row["deduction_date"]), "%Y-%m-%d").date()
        edit_date = c2.date_input("Tarih", value=current_date, key="deduction_edit_date")
        edit_type = c3.selectbox("Kesinti türü", deduction_types, index=edit_type_index, key="deduction_edit_type")
        edit_amount = st.number_input("Tutar", min_value=0.0, value=float(row["amount"] or 0.0), step=50.0, key="deduction_edit_amount")
        edit_notes = st.text_input("Açıklama", value=row["notes"] or "", key="deduction_edit_notes")
        c4, c5 = st.columns(2)
        update_clicked = c4.form_submit_button("Kesinti güncelle", width='stretch')
        delete_clicked = c5.form_submit_button("Kesinti sil", width='stretch')

        if update_clicked and edit_amount > 0:
            conn.execute(
                """
                UPDATE deductions
                SET personnel_id = ?, deduction_date = ?, deduction_type = ?, amount = ?, notes = ?
                WHERE id = ?
                """,
                (person_opts[edit_person], edit_date.isoformat(), edit_type, edit_amount, edit_notes, selected_id),
            )
            conn.commit()
            st.success("Kesinti güncellendi.")
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
          AND (? = 1 OR assigned_restaurant_id = ? OR role IN ('Joker', 'Şef'))
        ORDER BY CASE WHEN role='Şef' THEN 1 WHEN role='Joker' THEN 2 ELSE 3 END, full_name
        """,
        (1 if include_all_active else 0, restaurant_id),
    ).fetchall()

    person_label_map = {f"{r['full_name']} ({r['role']})": r['id'] for r in people_rows}
    name_to_label = {r['full_name'].strip().lower(): f"{r['full_name']} ({r['role']})" for r in people_rows}

    if "bulk_editor_rows" not in st.session_state:
        st.session_state.bulk_editor_rows = None

    default_rows = []
    if st.session_state.bulk_editor_rows:
        default_rows = st.session_state.bulk_editor_rows
    else:
        for label in person_label_map.keys():
            default_rows.append({
                "Personel": label,
                "Saat": 0.0,
                "Paket": 0,
                "Durum": "Normal",
                "Not": "",
            })

    with st.expander("WhatsApp metninden tablo oluştur", expanded=False):
        st.caption("Örnek satır formatı: Ali Yılmaz - 10 saat - 38 paket - Normal")
        raw_text = st.text_area("Mesajı yapıştır", height=160, key="bulk_whatsapp_text")
        if st.button("Metni tabloya aktar", key="bulk_parse_btn", width='stretch'):
            parsed = parse_whatsapp_bulk(raw_text)
            rows = []
            for row in parsed:
                guess = name_to_label.get(str(row['person_label']).strip().lower())
                rows.append({
                    "Personel": guess or row['person_label'],
                    "Saat": float(row['worked_hours'] or 0),
                    "Paket": int(row['package_count'] or 0),
                    "Durum": row['entry_status'] or 'Normal',
                    "Not": row.get('notes', ''),
                })
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
        width='stretch',
        hide_index=True,
        num_rows='dynamic',
        key='bulk_editor',
        column_config={
            'Personel': st.column_config.SelectboxColumn('Personel', options=list(person_label_map.keys()), required=False),
            'Saat': st.column_config.NumberColumn('Saat', min_value=0.0, max_value=24.0, step=0.5, format='%.1f'),
            'Paket': st.column_config.NumberColumn('Paket', min_value=0, step=1),
            'Durum': st.column_config.SelectboxColumn('Durum', options=['Normal', 'Joker', 'İzin', 'Gelmedi', 'Çıkış']),
            'Not': st.column_config.TextColumn('Not'),
        }
    )

    csave, cclear = st.columns([1,1])
    if csave.button('Tümünü Kaydet', key='bulk_save_btn', width='stretch'):
        inserted = 0
        for _, row in edited_df.iterrows():
            person_label = str(row.get('Personel', '')).strip()
            if not person_label or person_label not in person_label_map:
                continue
            hours = float(row.get('Saat') or 0)
            packages = int(row.get('Paket') or 0)
            status = str(row.get('Durum') or 'Normal').strip()
            notes = str(row.get('Not') or '').strip()
            if hours == 0 and packages == 0 and status in ['Normal', '']:
                continue
            person_id = person_label_map[person_label]
            conn.execute(
                """
                INSERT INTO daily_entries (entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count, entry_status, data_source, confirmed_by, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (selected_date.isoformat(), restaurant_id, person_id, person_id, hours, packages, status, 'Toplu Puantaj', st.session_state.get('username', 'sistem'), notes),
            )
            inserted += 1
        conn.commit()
        st.session_state.bulk_editor_rows = None
        st.success(f"{inserted} satır kaydedildi.")
        st.rerun()

    if cclear.button('Tabloyu Sıfırla', key='bulk_clear_btn', width='stretch'):
        st.session_state.bulk_editor_rows = None
        st.rerun()

EQUIPMENT_ITEMS = [
    "Box+Punch",
    "Polar",
    "Tişört",
    "Korumalı Mont",
    "Yelek",
    "Yağmurluk",
    "Kask",
    "Telefon Tutacağı",
]

NON_RETURNABLE_ITEMS = {
    "Polar",
    "Tişört",
    "Korumalı Mont",
    "Yelek",
    "Yağmurluk",
    "Kask",
    "Telefon Tutacağı",
}

def equipment_tab(conn: sqlite3.Connection) -> None:
    section_intro(
        "📦 Ekipman & Zimmet | Satın alma, kurye satışı, 2 taksit kesinti ve box geri alım",
        "Ekipman satın alma maliyetini, kuryeye satış fiyatını, otomatik taksit kesintilerini ve box geri alımını tek panelden yönet."
    )
    person_opts = get_person_options(conn, active_only=False)
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧾 Satın Alma",
        "👷 Kurye Zimmet / Satış",
        "🔄 Box Geri Alım",
        "📈 Ekipman Kârlılığı",
    ])

    with tab1:
        st.markdown("#### Satın alma faturası girişi")
        with st.form("purchase_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            purchase_date = c1.date_input("Fatura tarihi", value=date.today(), key="purchase_date")
            item_name = c2.selectbox("Ürün", EQUIPMENT_ITEMS, key="purchase_item")
            quantity = c3.number_input("Adet", min_value=1, value=1, step=1, key="purchase_qty")
            c4, c5, c6 = st.columns(3)
            total_invoice_amount = c4.number_input("Toplam fatura tutarı", min_value=0.0, value=0.0, step=100.0, key="purchase_total")
            supplier = c5.text_input("Tedarikçi", key="purchase_supplier")
            invoice_no = c6.text_input("Fatura no", key="purchase_invoice_no")
            notes = st.text_input("Not", key="purchase_notes")
            submitted = st.form_submit_button("Satın alma kaydet")
            if submitted and quantity > 0 and total_invoice_amount > 0:
                unit_cost = round(total_invoice_amount / quantity, 2)
                conn.execute(
                    """INSERT INTO inventory_purchases
                    (purchase_date, item_name, quantity, total_invoice_amount, unit_cost, supplier, invoice_no, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (purchase_date.isoformat(), item_name, int(quantity), total_invoice_amount, unit_cost, supplier, invoice_no, notes),
                )
                conn.commit()
                st.success(f"Satın alma kaydedildi. Birim maliyet: {fmt_try(unit_cost)}")

        purchases = fetch_df(conn, "SELECT purchase_date, item_name, quantity, total_invoice_amount, unit_cost, supplier, invoice_no, notes FROM inventory_purchases ORDER BY purchase_date DESC, id DESC")
        if not purchases.empty:
            purchases_display = format_display_df(
                purchases,
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
            st.dataframe(purchases_display, width="stretch", hide_index=True)

    with tab2:
        st.markdown("#### Kurye zimmet / satış kaydı")
        with st.form("equipment_issue_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            person_label = c1.selectbox("Personel", list(person_opts.keys()), key="issue_person")
            issue_date = c2.date_input("Zimmet tarihi", value=date.today(), key="issue_date")
            item_name = c3.selectbox("Ürün", EQUIPMENT_ITEMS, key="issue_item")
            suggested_cost = latest_average_cost(conn, item_name)
            c4, c5, c6 = st.columns(3)
            quantity = c4.number_input("Adet", min_value=1, value=1, step=1, key="issue_qty")
            unit_cost = c5.number_input("Birim maliyet", min_value=0.0, value=float(suggested_cost), step=50.0, key="issue_cost")
            unit_sale_price = c6.number_input("Kuryeye satış fiyatı", min_value=0.0, value=float(suggested_cost), step=50.0, key="issue_sale")
            c7, c8, c9 = st.columns(3)
            installment_count = c7.selectbox("Taksit sayısı", [1, 2, 3], index=1, key="issue_installment")
            sale_type = c8.selectbox("İşlem tipi", ["Satış", "Depozit / Teslim"], key="issue_sale_type")
            notes = c9.text_input("Not", key="issue_notes")
            submitted = st.form_submit_button("Zimmet kaydet ve taksit oluştur")
            if submitted:
                person_id = person_opts[person_label]
                conn.execute(
                    """INSERT INTO courier_equipment_issues
                    (personnel_id, issue_date, item_name, quantity, unit_cost, unit_sale_price, installment_count, sale_type, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (person_id, issue_date.isoformat(), item_name, int(quantity), unit_cost, unit_sale_price, int(installment_count), sale_type, notes),
                )
                issue_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                total_sale_amount = float(quantity) * float(unit_sale_price)
                post_equipment_installments(conn, issue_id, person_id, issue_date, item_name, total_sale_amount, int(installment_count))
                st.success(f"Zimmet kaydedildi. Toplam satış: {fmt_try(total_sale_amount)} | {installment_count} taksit oluşturuldu.")

        issues = fetch_df(
            conn,
            """
            SELECT i.id, i.issue_date, p.full_name, i.item_name, i.quantity, i.unit_cost, i.unit_sale_price,
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
            issues_display = format_display_df(
                issues,
                currency_cols=["unit_cost", "unit_sale_price", "total_cost", "total_sale", "gross_profit"],
                number_cols=["quantity", "installment_count"],
                rename_map={
                    "id": "ID",
                    "issue_date": "Tarih",
                    "full_name": "Personel",
                    "item_name": "Ürün",
                    "quantity": "Adet",
                    "unit_cost": "Birim Maliyet",
                    "unit_sale_price": "Birim Satış",
                    "total_cost": "Toplam Maliyet",
                    "total_sale": "Toplam Satış",
                    "gross_profit": "Brüt Kâr",
                    "installment_count": "Taksit",
                    "sale_type": "İşlem Tipi",
                    "notes": "Not",
                },
            )
            st.dataframe(issues_display, width="stretch", hide_index=True)

        installment_df = fetch_df(
            conn,
            """
            SELECT d.deduction_date, p.full_name, d.deduction_type, d.amount, d.notes
            FROM deductions d
            JOIN personnel p ON p.id = d.personnel_id
            WHERE d.equipment_issue_id IS NOT NULL
            ORDER BY d.deduction_date DESC, d.id DESC
            """,
        )
        if not installment_df.empty:
            st.markdown("#### Oluşan zimmet taksitleri")
            installment_display = format_display_df(
                installment_df,
                currency_cols=["amount"],
                rename_map={
                    "deduction_date": "Tarih",
                    "full_name": "Personel",
                    "deduction_type": "Tür",
                    "amount": "Tutar",
                    "notes": "Açıklama",
                },
            )
            st.dataframe(installment_display, width="stretch", hide_index=True)

    with tab3:
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
            submitted = st.form_submit_button("Box geri alımı kaydet")
            if submitted:
                person_id = person_opts[person_label]
                waived = 1 if condition_status == "Parasını istemedi" else 0
                conn.execute(
                    """INSERT INTO box_returns (personnel_id, return_date, quantity, condition_status, payout_amount, waived, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
            # select subset to avoid raw waived column
            cols = ["Tarih", "Personel", "Adet", "Durum", "Geri Ödeme", "Parasını İstemedi", "Not"]
            st.dataframe(returns_display[cols], width="stretch", hide_index=True)

    with tab4:
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
            st.dataframe(sales_display, width="stretch", hide_index=True)

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
            st.dataframe(stock_display, width="stretch", hide_index=True)


def build_branch_profitability(month_df: pd.DataFrame, personnel_df: pd.DataFrame, deductions_df: pd.DataFrame, invoice_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if month_df.empty or invoice_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    work = month_df.groupby(["brand", "branch", "actual_personnel_id"], dropna=False).agg(
        saat=("worked_hours", "sum"), paket=("package_count", "sum")
    ).reset_index()

    people = personnel_df[["id", "full_name", "role", "cost_model", "monthly_fixed_cost", "assigned_restaurant_id"]].rename(columns={"id": "actual_personnel_id"})
    work = work.merge(people, how="left", on="actual_personnel_id")

    # restaurant metadata for fallback allocation of fixed staff with no monthly entries
    restaurant_meta = month_df[["restaurant_id", "brand", "branch"]].drop_duplicates()

    ded_by_person = (
        deductions_df.groupby("personnel_id", dropna=False)["amount"].sum().reset_index(name="toplam_kesinti")
        if not deductions_df.empty else pd.DataFrame(columns=["personnel_id", "toplam_kesinti"])
    )

    # Variable-cost personnel allocation based on actual branch work
    allocation_rows = []
    for _, r in work.iterrows():
        person_id = r["actual_personnel_id"]
        if pd.isna(person_id):
            continue
        role = r.get("role") or "Kurye"
        cost_model = r.get("cost_model") or "standard_courier"
        hours = float(r["saat"] or 0)
        packages = float(r["paket"] or 0)
        brand = r["brand"]
        if cost_model == "fixed_monthly":
            continue
        if brand == "Quick China":
            package_cost = packages * COURIER_PACKAGE_COST_QC
        else:
            low_qty = min(packages, PACKAGE_THRESHOLD_DEFAULT)
            high_qty = max(packages - PACKAGE_THRESHOLD_DEFAULT, 0)
            package_cost = low_qty * COURIER_PACKAGE_COST_DEFAULT_LOW + high_qty * COURIER_PACKAGE_COST_DEFAULT_HIGH
        allocation_rows.append({
            "restoran": f"{brand} - {r['branch']}",
            "personel": r.get("full_name") or "-",
            "rol": role,
            "saat": hours,
            "paket": packages,
            "maliyet": hours * COURIER_HOURLY_COST + package_cost,
            "kaynak": "Degisken maliyet",
        })

    # Fixed monthly roles allocation: if they have entries, split by hour share; else fall back to assigned restaurant
    fixed_people = personnel_df[personnel_df["cost_model"] == "fixed_monthly"].copy()
    for _, p in fixed_people.iterrows():
        pid = p["id"]
        gross = float(p["monthly_fixed_cost"] or 0)
        total_ded = float(ded_by_person.loc[ded_by_person["personnel_id"] == pid, "toplam_kesinti"].sum()) if not ded_by_person.empty else 0.0
        net = gross - total_ded
        per_work = work[work["actual_personnel_id"] == pid].copy()
        if not per_work.empty and float(per_work["saat"].sum()) > 0:
            total_hours = float(per_work["saat"].sum())
            for _, r in per_work.iterrows():
                share = float(r["saat"] or 0) / total_hours
                allocation_rows.append({
                    "restoran": f"{r['brand']} - {r['branch']}",
                    "personel": p["full_name"],
                    "rol": p["role"],
                    "saat": float(r["saat"] or 0),
                    "paket": float(r["paket"] or 0),
                    "maliyet": net * share,
                    "kaynak": "Sabit maliyet payi",
                })
        else:
            rid = p.get("assigned_restaurant_id")
            row = restaurant_meta[restaurant_meta["restaurant_id"] == rid]
            if not row.empty:
                brand = row.iloc[0]["brand"]
                branch = row.iloc[0]["branch"]
                allocation_rows.append({
                    "restoran": f"{brand} - {branch}",
                    "personel": p["full_name"],
                    "rol": p["role"],
                    "saat": 0.0,
                    "paket": 0.0,
                    "maliyet": net,
                    "kaynak": "Sabit maliyet tam atama",
                })

    alloc_df = pd.DataFrame(allocation_rows)
    if alloc_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    branch_cost = alloc_df.groupby("restoran", dropna=False).agg(
        toplam_personel_maliyeti=("maliyet", "sum")
    ).reset_index()

    profit_df = invoice_df.merge(branch_cost, how="left", on="restoran").fillna({"toplam_personel_maliyeti": 0})
    profit_df["brut_fark"] = profit_df["kdv_dahil"] - profit_df["toplam_personel_maliyeti"]
    profit_df["kar_marji_%"] = profit_df.apply(lambda x: (x["brut_fark"] / x["kdv_dahil"] * 100) if x["kdv_dahil"] else 0, axis=1)
    profit_df = profit_df.sort_values("brut_fark", ascending=False)

    person_distribution = alloc_df.sort_values(["restoran", "rol", "personel"]).reset_index(drop=True)
    return profit_df, person_distribution





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

    def write_line(text: str, x: int, y: float, size: int = 10):
        c.setFont(font_name, size)
        c.drawString(x, y, str(text))

    y = height - 50
    write_line("Cat Kapinda", 40, y, 16)
    y -= 22
    write_line("Kurye Hakedis Raporu", 40, y, 14)
    y -= 28

    lines = [
        f"Personel: {payroll_row.get('personel','-')}",
        f"Kod: {payroll_row.get('person_code','-')}",
        f"Rol: {payroll_row.get('rol','-')}",
        f"Ay: {selected_month}",
        f"Durum: {payroll_row.get('durum','-')}",
        "Restoranlar: " + (", ".join(restaurant_names) if restaurant_names else "-"),
    ]
    for line in lines:
        write_line(line, 40, y, 10)
        y -= 16

    y -= 4
    c.line(40, y, width - 40, y)
    y -= 20

    write_line("Calisma Ozeti", 40, y, 12)
    y -= 18
    write_line(f"Toplam Saat: {int(float(payroll_row.get('calisma_saati', 0) or 0))}", 40, y)
    y -= 16
    write_line(f"Toplam Paket: {int(float(payroll_row.get('paket', 0) or 0))}", 40, y)
    y -= 22

    write_line("Hakedis Ozeti", 40, y, 12)
    y -= 18
    write_line(f"Brut Hakedis: {fmt_currency_pdf(payroll_row.get('brut_maliyet', 0))}", 40, y)
    y -= 16
    write_line(f"Toplam Kesinti: {fmt_currency_pdf(payroll_row.get('kesinti', 0))}", 40, y)
    y -= 16
    write_line(f"Net Odeme: {fmt_currency_pdf(payroll_row.get('net_maliyet', 0))}", 40, y, 11)
    y -= 24

    write_line("Kesinti Detayi", 40, y, 12)
    y -= 18
    if deduction_rows is None or deduction_rows.empty:
        write_line("Bu ay icin kesinti kaydi bulunamadi.", 40, y)
        y -= 16
    else:
        grouped = deduction_rows.groupby("deduction_type", dropna=False)["amount"].sum().reset_index()
        for _, r in grouped.iterrows():
            write_line(f"{r['deduction_type']}: -{fmt_currency_pdf(r['amount'])}", 40, y)
            y -= 16
            if y < 80:
                c.showPage()
                y = height - 50

    y -= 8
    c.line(40, y, width - 40, y)
    y -= 16
    write_line("Cat Kapinda Operasyon CRM tarafindan olusturuldu.", 40, y, 9)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def monthly_payroll_tab(conn: sqlite3.Connection) -> None:
    section_intro("🧾 Aylık Hakediş | Personel bazlı brüt, kesinti ve net ödeme özeti", "Aylık puantaj ve kesinti verilerini personel bazında hesaplar; CSV dışa aktarma sağlar.")

    entries = fetch_df(conn, """
        SELECT d.*, r.brand, r.branch, r.pricing_model, r.hourly_rate, r.package_rate,
               r.package_threshold, r.package_rate_low, r.package_rate_high,
               r.fixed_monthly_fee, r.vat_rate
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
    """)
    deductions = fetch_df(conn, "SELECT * FROM deductions")
    personnel_df = fetch_df(conn, "SELECT * FROM personnel")

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
    role_filter = c2.selectbox("Rol", ["Tümü", "Kurye", "Joker", "Şef"])
    restaurant_choices = ["Tümü"]
    if not entries.empty:
        restaurant_choices += sorted((entries["brand"] + " - " + entries["branch"]).dropna().unique().tolist())
    restaurant_filter = c3.selectbox("Restoran filtresi", restaurant_choices)

    start_date, end_date = month_bounds(selected_month)
    month_entries = entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy() if not entries.empty else pd.DataFrame()
    month_deductions = deductions[(deductions["deduction_date"] >= start_date) & (deductions["deduction_date"] <= end_date)].copy() if not deductions.empty else pd.DataFrame()

    if restaurant_filter != "Tümü" and not month_entries.empty:
        month_entries = month_entries[(month_entries["brand"] + " - " + month_entries["branch"]) == restaurant_filter].copy()

    cost_df = calculate_personnel_cost(month_entries, personnel_df, month_deductions)
    if cost_df.empty:
        st.warning("Seçilen filtre için hakediş verisi bulunamadı.")
        return

    if role_filter != "Tümü":
        cost_df = cost_df[cost_df["rol"] == role_filter].copy()

    by_person_branch = month_entries.groupby("actual_personnel_id", dropna=False).agg(
        restoran_sayisi=("restaurant_id", "nunique")
    ).reset_index().rename(columns={"actual_personnel_id": "personnel_id"}) if not month_entries.empty else pd.DataFrame(columns=["personnel_id","restoran_sayisi"])
    cost_df = cost_df.merge(by_person_branch, on="personnel_id", how="left")
    cost_df["restoran_sayisi"] = cost_df["restoran_sayisi"].fillna(0).astype(int)
    cost_df["ay"] = selected_month

    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Brüt Hakediş", fmt_try(float(cost_df["brut_maliyet"].sum())))
    m2.metric("Toplam Kesinti", fmt_try(float(cost_df["kesinti"].sum())))
    m3.metric("Toplam Net Ödeme", fmt_try(float(cost_df["net_maliyet"].sum())))

    payroll_display = format_display_df(
        cost_df[["ay","personel","rol","durum","calisma_saati","paket","brut_maliyet","kesinti","net_maliyet","restoran_sayisi","maliyet_modeli"]],
        currency_cols=["Brüt Hakediş","Toplam Kesinti","Net Ödeme"],
        number_cols=["Toplam Saat","Toplam Paket","Restoran Sayısı"],
        rename_map={
            "ay":"Ay",
            "personel":"Personel",
            "rol":"Rol",
            "durum":"Durum",
            "calisma_saati":"Toplam Saat",
            "paket":"Toplam Paket",
            "brut_maliyet":"Brüt Hakediş",
            "kesinti":"Toplam Kesinti",
            "net_maliyet":"Net Ödeme",
            "restoran_sayisi":"Restoran Sayısı",
            "maliyet_modeli":"Maliyet Modeli",
        }
    )
    st.dataframe(payroll_display, width='stretch', hide_index=True)
    st.download_button(
        "Aylık hakediş CSV indir",
        data=cost_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"catkapinda_aylik_hakedis_{selected_month}.csv",
        mime="text/csv",
    )


    st.markdown("### PDF Hakediş İndir")
    pdf_person_options = {f"{row['personel']} | {row['rol']}": row['personnel_id'] for _, row in cost_df.sort_values("personel").iterrows()}
    if pdf_person_options:
        selected_pdf_label = st.selectbox("PDF oluşturulacak personel", list(pdf_person_options.keys()))
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
            "PDF hakediş indir",
            data=pdf_bytes,
            file_name=f"hakedis_{safe_name}_{selected_month}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("PDF oluşturmak için önce hakediş tablosunda personel verisi oluşmalı.")


def reports_tab(conn: sqlite3.Connection) -> None:
    section_intro("📊 Raporlar ve Karlılık | Fatura, personel maliyeti, yan gelir ve restoran kârlılığı", "Aylık müşteri faturası, personel maliyeti, restoran bazlı kârlılık, yan gelir analizi ve personel-şube dağılımı.")

    entries = fetch_df(conn, """
        SELECT d.*, r.brand, r.branch, r.pricing_model, r.hourly_rate, r.package_rate,
               r.package_threshold, r.package_rate_low, r.package_rate_high,
               r.fixed_monthly_fee, r.vat_rate
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
    """)
    if entries.empty:
        st.info("Rapor üretebilmek için önce günlük puantaj girişi yap.")
        return

    entries["entry_date"] = pd.to_datetime(entries["entry_date"])
    month_options = sorted(entries["entry_date"].dt.strftime("%Y-%m").unique(), reverse=True)
    selected_month = st.selectbox("Rapor Ayı", month_options)
    start_date, end_date = month_bounds(selected_month)

    month_df = entries[(entries["entry_date"] >= start_date) & (entries["entry_date"] <= end_date)].copy()
    if month_df.empty:
        st.warning("Bu ay için kayıt yok.")
        return

    invoicing_rows = []
    for (restaurant_id, brand, branch), group in month_df.groupby(["restaurant_id", "brand", "branch"]):
        first = group.iloc[0]
        rule = PricingRule(
            pricing_model=first["pricing_model"],
            hourly_rate=float(first["hourly_rate"] or 0),
            package_rate=float(first["package_rate"] or 0),
            package_threshold=int(first["package_threshold"] or 0) if pd.notna(first["package_threshold"]) else 0,
            package_rate_low=float(first["package_rate_low"] or 0),
            package_rate_high=float(first["package_rate_high"] or 0),
            fixed_monthly_fee=float(first["fixed_monthly_fee"] or 0),
            vat_rate=float(first["vat_rate"] or VAT_RATE_DEFAULT),
        )
        hours, packages, subtotal, grand_total = calculate_customer_invoice(group, rule)
        invoicing_rows.append({
            "restoran": f"{brand} - {branch}",
            "model": rule.pricing_model,
            "saat": hours,
            "paket": packages,
            "kdv_haric": subtotal,
            "kdv_dahil": grand_total,
        })
    invoice_df = pd.DataFrame(invoicing_rows).sort_values("restoran")

    personnel_df = fetch_df(conn, "SELECT * FROM personnel")
    deductions_df = fetch_df(conn, "SELECT * FROM deductions WHERE deduction_date BETWEEN ? AND ?", (start_date, end_date))
    cost_df = calculate_personnel_cost(month_df, personnel_df, deductions_df)

    revenue = float(invoice_df["kdv_dahil"].sum()) if not invoice_df.empty else 0.0
    personnel_cost = float(cost_df["net_maliyet"].sum()) if not cost_df.empty else 0.0
    gross_profit = revenue - personnel_cost

    equipment_sales_df = fetch_df(conn, "SELECT * FROM courier_equipment_issues")
    if not equipment_sales_df.empty:
        equipment_sales_df["issue_date"] = pd.to_datetime(equipment_sales_df["issue_date"])
        equipment_sales_df = equipment_sales_df[(equipment_sales_df["issue_date"] >= start_date) & (equipment_sales_df["issue_date"] <= end_date)].copy()
        equipment_sales_df["toplam_satis"] = equipment_sales_df["quantity"] * equipment_sales_df["unit_sale_price"]
        equipment_sales_df["toplam_maliyet"] = equipment_sales_df["quantity"] * equipment_sales_df["unit_cost"]
    accounting_ded = deductions_df[deductions_df["deduction_type"] == "Muhasebe Ücreti"].copy() if not deductions_df.empty else pd.DataFrame()
    setup_ded = deductions_df[deductions_df["deduction_type"] == "Şirket Açılış Ücreti"].copy() if not deductions_df.empty else pd.DataFrame()

    accounting_rev = float(accounting_ded["amount"].sum()) if not accounting_ded.empty else 0.0
    setup_rev = float(setup_ded["amount"].sum()) if not setup_ded.empty else 0.0

    accounting_person_ids = accounting_ded["personnel_id"].dropna().astype(int).unique().tolist() if not accounting_ded.empty else []
    setup_person_ids = setup_ded["personnel_id"].dropna().astype(int).unique().tolist() if not setup_ded.empty else []

    accountant_cost_total = float(personnel_df.loc[personnel_df["id"].isin(accounting_person_ids), "accountant_cost"].fillna(0).sum()) if accounting_person_ids and "accountant_cost" in personnel_df.columns else 0.0
    setup_cost = float(personnel_df.loc[personnel_df["id"].isin(setup_person_ids), "company_setup_cost"].fillna(0).sum()) if setup_person_ids and "company_setup_cost" in personnel_df.columns else 0.0

    equipment_rev = float(equipment_sales_df["toplam_satis"].sum()) if not equipment_sales_df.empty else 0.0
    equipment_cost = float(equipment_sales_df["toplam_maliyet"].sum()) if not equipment_sales_df.empty else 0.0
    side_income_net = (accounting_rev - accountant_cost_total) + (setup_rev - setup_cost) + (equipment_rev - equipment_cost)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aylık restoran faturası | KDV dahil", fmt_try(revenue))
    c2.metric("Toplam kurye maliyeti", fmt_try(personnel_cost))
    c3.metric("Brüt operasyon farkı", fmt_try(gross_profit))
    c4.metric("Yan gelir neti", fmt_try(side_income_net))

    profit_df, person_distribution_df = build_branch_profitability(month_df, personnel_df, deductions_df, invoice_df)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🧾 Restoran Faturası", "👥 Kurye Maliyeti", "📈 Restoran Karlılığı", "🔀 Personel-Şube Dağılımı", "💼 Yan Gelir Analizi"])
    with tab1:
        invoice_display_df = format_display_df(
            invoice_df,
            currency_cols=["Restoran KDV Hariç", "Restoran KDV Dahil"],
            number_cols=["Toplam Saat", "Toplam Paket"],
            rename_map={
                "restoran": "Restoran / Şube",
                "model": "Fiyat Modeli",
                "saat": "Toplam Saat",
                "paket": "Toplam Paket",
                "kdv_haric": "Restoran KDV Hariç",
                "kdv_dahil": "Restoran KDV Dahil",
            },
        )
        st.dataframe(invoice_display_df, width='stretch', hide_index=True)
        st.download_button(
            "Fatura raporunu CSV indir",
            data=invoice_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_fatura_{selected_month}.csv",
            mime="text/csv",
        )
    with tab2:
        cost_display_df = format_display_df(
            cost_df,
            currency_cols=["Brüt Kurye Maliyeti", "Toplam Kesinti", "Net Kurye Maliyeti"],
            number_cols=["Toplam Saat", "Toplam Paket"],
            rename_map={
                "personel": "Personel",
                "rol": "Rol",
                "durum": "Durum",
                "calisma_saati": "Toplam Saat",
                "paket": "Toplam Paket",
                "brut_maliyet": "Brüt Kurye Maliyeti",
                "kesinti": "Toplam Kesinti",
                "net_maliyet": "Net Kurye Maliyeti",
                "maliyet_modeli": "Maliyet Modeli",
            },
        )
        st.dataframe(cost_display_df, width='stretch', hide_index=True)
        st.download_button(
            "Personel maliyetini CSV indir",
            data=cost_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"catkapinda_personel_maliyet_{selected_month}.csv",
            mime="text/csv",
        )
    with tab3:
        if profit_df.empty:
            st.info("Restoran kârlılığı için veri yok.")
        else:
            p1, p2, p3 = st.columns(3)
            p1.metric("En yüksek restoran faturası | KDV dahil", fmt_try(float(profit_df["kdv_dahil"].max())))
            p2.metric("En yüksek kurye maliyeti", fmt_try(float(profit_df["toplam_personel_maliyeti"].max())))
            p3.metric("En yüksek brüt fark", fmt_try(float(profit_df["brut_fark"].max())))
            profit_display_df = format_display_df(
                profit_df,
                currency_cols=["Restoran KDV Hariç", "Restoran KDV Dahil", "Toplam Kurye Maliyeti", "Brüt Fark"],
                percent_cols=["Kâr Marjı"],
                number_cols=["Toplam Saat", "Toplam Paket"],
                rename_map={
                    "restoran": "Restoran / Şube",
                    "saat": "Toplam Saat",
                    "paket": "Toplam Paket",
                    "kdv_haric": "Restoran KDV Hariç",
                    "kdv_dahil": "Restoran KDV Dahil",
                    "toplam_personel_maliyeti": "Toplam Kurye Maliyeti",
                    "brut_fark": "Brüt Fark",
                    "kar_marji_%": "Kâr Marjı",
                    "model": "Fiyat Modeli",
                },
            )
            st.dataframe(profit_display_df, width='stretch', hide_index=True)
            st.download_button(
                "Restoran kârlılık CSV indir",
                data=profit_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"catkapinda_restoran_karlilik_{selected_month}.csv",
                mime="text/csv",
            )
    with tab4:
        if person_distribution_df.empty:
            st.info("Personel-şube dağılımı için veri yok.")
        else:
            distribution_display_df = format_display_df(
                person_distribution_df,
                currency_cols=["Maliyet Payı"],
                number_cols=["Saat", "Paket"],
                rename_map={
                    "restoran": "Restoran / Şube",
                    "personel": "Personel",
                    "rol": "Rol",
                    "saat": "Saat",
                    "paket": "Paket",
                    "maliyet": "Maliyet Payı",
                    "kaynak": "Maliyet Kaynağı",
                },
            )
            st.dataframe(distribution_display_df, width='stretch', hide_index=True)
            st.download_button(
                "Personel-şube dağılımı CSV indir",
                data=person_distribution_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"catkapinda_personel_sube_dagilim_{selected_month}.csv",
                mime="text/csv",
            )



    with tab5:
        side_df = pd.DataFrame([
            {"kalem": "Muhasebe Hizmeti", "gelir": accounting_rev, "maliyet": accountant_cost_total, "net_kar": accounting_rev - accountant_cost_total},
            {"kalem": "Şirket Açılışı", "gelir": setup_rev, "maliyet": setup_cost, "net_kar": setup_rev - setup_cost},
            {"kalem": "Ekipman Satışı", "gelir": equipment_rev, "maliyet": equipment_cost, "net_kar": equipment_rev - equipment_cost},
        ])
        s1, s2, s3 = st.columns(3)
        s1.metric("Toplam Yan Gelir", fmt_try(float(side_df["gelir"].sum())))
        s2.metric("Toplam Yan Gelir Maliyeti", fmt_try(float(side_df["maliyet"].sum())))
        s3.metric("Toplam Yan Gelir Neti", fmt_try(float(side_df["net_kar"].sum())))
        side_display_df = format_display_df(
            side_df,
            currency_cols=["Gelir", "Maliyet", "Net Kâr"],
            rename_map={"kalem": "Kalem", "gelir": "Gelir", "maliyet": "Maliyet", "net_kar": "Net Kâr"},
        )
        st.dataframe(side_display_df, width='stretch', hide_index=True)

def main() -> None:
    if not login_gate():
        return

    st.set_page_config(page_title="Çat Kapında Operasyon CRM", page_icon="📦", layout="wide")
    inject_global_styles()

    conn = get_conn()
    role = st.session_state.get("role", "")

    menu = st.sidebar.radio("Ana Menü", allowed_menu_items(role))
    logout_button()

    ensure_role_access(menu, role)

    if menu == "🏠 Ana Dashboard":
        dashboard_tab(conn)
    elif menu == "🏢 Restoran Yönetimi":
        restaurants_tab(conn)
    elif menu == "👥 Personel Yönetimi":
        personnel_tab(conn)
    elif menu == "📦 Ekipman & Zimmet":
        equipment_tab(conn)
    elif menu == "🗓 Günlük Puantaj":
        daily_entries_tab(conn)
    elif menu == "🗂 Toplu Puantaj":
        toplu_puantaj_tab(conn)
    elif menu == "💸 Kesinti Yönetimi":
        deductions_tab(conn)
    elif menu == "🧾 Aylık Hakediş":
        monthly_payroll_tab(conn)
    elif menu == "📊 Raporlar ve Karlılık":
        reports_tab(conn)

    conn.close()


if __name__ == "__main__":
    main()
