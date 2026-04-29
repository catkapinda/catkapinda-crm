import sqlite3

from app.core.database import CompatConnection
from app.services.restaurants import build_restaurants_dashboard


def _build_restaurants_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL,
            target_headcount INTEGER,
            start_date TEXT,
            end_date TEXT,
            extra_headcount_request INTEGER,
            extra_headcount_request_date TEXT,
            reduce_headcount_request INTEGER,
            reduce_headcount_request_date TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            company_title TEXT,
            address TEXT,
            tax_office TEXT,
            tax_number TEXT,
            active INTEGER,
            notes TEXT
        );

        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            status TEXT,
            assigned_restaurant_id INTEGER
        );
        """
    )
    raw_conn.execute(
        """
        INSERT INTO restaurants (
            id, brand, branch, pricing_model, hourly_rate, package_rate, package_threshold,
            package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate, target_headcount,
            start_date, end_date, extra_headcount_request, extra_headcount_request_date,
            reduce_headcount_request, reduce_headcount_request_date, contact_name, contact_phone,
            contact_email, company_title, address, tax_office, tax_number, active, notes
        )
        VALUES (10, 'SushiCo', 'Çengelköy', 'hourly_plus_package', 279, 32, 390, 0, 0, 0, 20, 6,
            NULL, NULL, 0, NULL, 0, NULL, 'Yetkili', '', '', '', '', '', '', 1, '')
        """
    )
    raw_conn.executemany(
        """
        INSERT INTO personnel (id, full_name, role, status, assigned_restaurant_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, "Ana Kurye", "Kurye", "Aktif", 10),
            (2, "Joker Destek", "Joker", "Aktif", 10),
            (3, "Bolge Yonetimi", "Bolge Muduru", "Aktif", 10),
            (4, "Destek Kisi", "Destek", "Aktif", 10),
            (5, "Pasif Kurye", "Kurye", "Pasif", 10),
        ],
    )
    raw_conn.commit()
    return CompatConnection(raw_conn, "sqlite")


def test_restaurants_dashboard_counts_only_primary_active_restaurant_staff():
    payload = build_restaurants_dashboard(_build_restaurants_conn(), limit=10)

    assert payload.recent_entries[0].active_personnel_count == 1
    assert [entry.full_name for entry in payload.recent_entries[0].active_personnel] == ["Ana Kurye"]
