import sqlite3

import pytest

from app.core.database import CompatConnection
from app.schemas.invoices import InvoiceCollectionUpsertRequest
from app.schemas.reports import (
    ReportInvoiceEntry,
    ReportSideIncomeSnapshot,
    ReportsCoverageSummary,
    ReportsDashboardResponse,
    ReportsSummary,
)
from app.services import invoices as invoices_service
from app.services.invoices import build_invoices_dashboard, upsert_invoice_collection


def _build_invoices_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            monthly_fixed_cost REAL,
            cost_model TEXT,
            status TEXT,
            start_date TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            vehicle_type TEXT,
            motor_rental_monthly_amount REAL,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_deduction REAL
        );
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT,
            active INTEGER,
            pricing_model TEXT,
            hourly_rate REAL,
            package_rate REAL,
            package_threshold INTEGER,
            package_rate_low REAL,
            package_rate_high REAL,
            fixed_monthly_fee REAL,
            vat_rate REAL
        );
        CREATE TABLE daily_entries (
            id INTEGER PRIMARY KEY,
            entry_date TEXT,
            restaurant_id INTEGER,
            planned_personnel_id INTEGER,
            actual_personnel_id INTEGER,
            worked_hours REAL,
            package_count REAL,
            monthly_invoice_amount REAL
        );
        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY,
            personnel_id INTEGER,
            deduction_date TEXT,
            deduction_type TEXT,
            amount REAL
        );
        CREATE TABLE restaurant_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            collection_month TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Bekliyor',
            due_date TEXT NULL,
            collected_amount REAL NOT NULL DEFAULT 0,
            payment_date TEXT NULL,
            last_contact_date TEXT NULL,
            responsible_name TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (restaurant_id, collection_month)
        );
        """
    )
    raw_conn.executemany(
        """
        INSERT INTO personnel (
            id, full_name, role, monthly_fixed_cost, cost_model, status, start_date, motor_rental, motor_purchase, vehicle_type, motor_rental_monthly_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "Ali Kurye", "Kurye", 0, "standard_courier", "Aktif", "2026-01-01", "Hayır", "Hayır", "Kendi Motoru", 13000),
            (2, "Ayşe Kurye", "Kurye", 0, "standard_courier", "Aktif", "2026-01-01", "Hayır", "Hayır", "Kendi Motoru", 13000),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO restaurants (
            id, brand, branch, active, pricing_model, hourly_rate, package_rate, package_threshold, package_rate_low, package_rate_high, fixed_monthly_fee, vat_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (10, "Quick China", "Ataşehir", 1, "hourly_plus_package", 279, 32, 390, 0, 0, 0, 20),
            (11, "Burger@", "Kavacık", 1, "hourly_plus_package", 279, 32, 390, 0, 0, 0, 20),
        ],
    )
    raw_conn.executemany(
        """
        INSERT INTO daily_entries (
            id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id, worked_hours, package_count, monthly_invoice_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "2026-04-10", 10, 1, 1, 10, 12, 0),
            (2, "2026-04-10", 10, 2, 2, 8, 10, 0),
            (3, "2026-04-11", 11, 1, 1, 6, 8, 0),
        ],
    )
    raw_conn.execute(
        """
        INSERT INTO restaurant_collections (
            restaurant_id, collection_month, status, due_date, collected_amount, payment_date, last_contact_date, responsible_name, note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            10,
            "2026-04",
            "Kısmi Tahsilat",
            "2026-04-20",
            1000.0,
            None,
            "2026-04-18",
            "Ebru",
            "İlk arama yapıldı",
            "2026-04-18 10:00:00",
            "2026-04-18 10:00:00",
        ),
    )
    raw_conn.commit()
    return CompatConnection(raw_conn, "sqlite")


def test_invoices_dashboard_merges_collections_with_invoice_rows():
    payload = build_invoices_dashboard(
        _build_invoices_conn(),
        selected_month="2026-04",
        limit=20,
    )

    collection_by_restaurant = {
        entry.restaurant: entry
        for entry in payload.collection_entries
    }

    assert payload.selected_month == "2026-04"
    assert payload.collection_summary.tracked_restaurant_count == 2
    assert payload.collection_summary.total_collected_amount == 1000

    qc_entry = collection_by_restaurant["Quick China - Ataşehir"]
    assert qc_entry.status == "Kısmi Tahsilat"
    assert qc_entry.collected_amount == 1000
    assert qc_entry.remaining_amount == qc_entry.gross_invoice - 1000
    assert qc_entry.responsible_name == "Ebru"
    qc_drilldown = next(
        entry
        for entry in payload.invoice_drilldown_entries
        if entry.restaurant == "Quick China - Ataşehir" and entry.personnel == "Ali Kurye"
    )
    assert qc_drilldown.net_invoice_amount == 3174
    assert qc_drilldown.gross_invoice_amount == pytest.approx(3808.8)

    burger_entry = collection_by_restaurant["Burger@ - Kavacık"]
    assert burger_entry.status == "Bekliyor"
    assert burger_entry.collected_amount == 0
    assert burger_entry.remaining_amount == burger_entry.gross_invoice


def test_upsert_invoice_collection_creates_and_updates_same_month_record():
    conn = _build_invoices_conn()

    created = upsert_invoice_collection(
        conn,
        payload=InvoiceCollectionUpsertRequest(
            restaurant_id=11,
            collection_month="2026-04",
            status="Planlandı",
            due_date="2026-04-28",
            collected_amount=500,
            payment_date=None,
            last_contact_date="2026-04-19",
            responsible_name="Cihan",
            note="İlk takip",
        ),
    )
    assert created.record.restaurant_id == 11
    assert created.record.status == "Planlandı"
    assert created.record.collected_amount == 500

    updated = upsert_invoice_collection(
        conn,
        payload=InvoiceCollectionUpsertRequest(
            restaurant_id=11,
            collection_month="2026-04",
            status="Tahsil Edildi",
            due_date="2026-04-28",
            collected_amount=1750,
            payment_date="2026-04-29",
            last_contact_date="2026-04-29",
            responsible_name="Tunç",
            note="Kapanış alındı",
        ),
    )
    assert updated.record.id == created.record.id
    assert updated.record.status == "Tahsil Edildi"
    assert updated.record.collected_amount == 1750
    assert updated.record.payment_date == "2026-04-29"
    assert updated.record.responsible_name == "Tunç"


def test_invoices_dashboard_backfills_courier_drilldown_from_attendance_when_reports_payload_is_empty(monkeypatch):
    conn = _build_invoices_conn()

    def _fake_reports_dashboard(_conn, *, selected_month=None, limit=200):
        return ReportsDashboardResponse(
            module="reports",
            status="active",
            month_options=["2026-04"],
            selected_month="2026-04",
            summary=ReportsSummary(
                selected_month="2026-04",
                restaurant_count=2,
                courier_count=2,
                total_hours=24,
                total_packages=30,
                total_revenue=7305.6,
                total_personnel_cost=0,
                gross_profit=7305.6,
                side_income_net=0,
            ),
            invoice_entries=[
                ReportInvoiceEntry(
                    restaurant="Quick China - Ataşehir",
                    pricing_model="Saat + Paket",
                    total_hours=18,
                    total_packages=22,
                    net_invoice=6088,
                    gross_invoice=7305.6,
                ),
                ReportInvoiceEntry(
                    restaurant="Burger@ - Kavacık",
                    pricing_model="Saat + Paket",
                    total_hours=6,
                    total_packages=8,
                    net_invoice=1930,
                    gross_invoice=2316,
                ),
            ],
            cost_entries=[],
            profit_entries=[],
            model_breakdown=[],
            top_restaurants=[],
            top_couriers=[],
            coverage=ReportsCoverageSummary(
                covered_restaurant_count=2,
                operational_restaurant_count=2,
            ),
            shared_overhead_entries=[],
            distribution_entries=[],
            invoice_drilldown_entries=[],
            side_income_entries=[],
            side_income_snapshot=ReportSideIncomeSnapshot(
                fuel_reflection_amount=0,
                company_fuel_reflection_amount=0,
                utts_fuel_discount_amount=0,
                partner_card_discount_amount=0,
            ),
        )

    monkeypatch.setattr(invoices_service, "build_reports_dashboard", _fake_reports_dashboard)

    payload = invoices_service.build_invoices_dashboard(
        conn,
        selected_month="2026-04",
        limit=20,
    )

    quick_china_entries = [
        entry
        for entry in payload.invoice_drilldown_entries
        if entry.restaurant == "Quick China - Ataşehir"
    ]

    assert len(quick_china_entries) == 2
    assert {entry.personnel for entry in quick_china_entries} == {"Ali Kurye", "Ayşe Kurye"}
