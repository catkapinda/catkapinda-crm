from __future__ import annotations

import sqlite3
from unittest import TestCase

from infrastructure.db_engine import CompatConnection
from repositories.personnel_repository import (
    fetch_active_restaurant_options,
    fetch_person_code_values,
    fetch_person_options_map,
    fetch_personnel_by_code,
    fetch_personnel_by_id,
    fetch_personnel_management_df,
    insert_personnel_record,
    update_personnel_record,
    update_personnel_status,
)


def _make_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    conn = CompatConnection(raw_conn, "sqlite")
    conn.executescript(
        """
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            branch TEXT NOT NULL,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_code TEXT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            tc_no TEXT,
            iban TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            accounting_type TEXT,
            new_company_setup TEXT,
            accounting_revenue REAL,
            accountant_cost REAL,
            company_setup_revenue REAL,
            company_setup_cost REAL,
            assigned_restaurant_id INTEGER,
            vehicle_type TEXT,
            motor_rental TEXT,
            motor_purchase TEXT,
            motor_purchase_start_date TEXT,
            motor_purchase_commitment_months INTEGER,
            motor_rental_monthly_amount REAL,
            motor_purchase_sale_price REAL,
            motor_purchase_monthly_amount REAL,
            motor_purchase_installment_count INTEGER,
            current_plate TEXT,
            start_date TEXT,
            exit_date TEXT,
            cost_model TEXT,
            monthly_fixed_cost REAL,
            notes TEXT
        );
        """
    )
    return conn


def _personnel_values() -> dict[str, object]:
    return {
        "person_code": "CK-K001",
        "full_name": "Ali Veli",
        "role": "Kurye",
        "status": "Aktif",
        "phone": "5550000000",
        "address": "Istanbul",
        "tc_no": "11111111111",
        "iban": "TR000000000000000000000001",
        "emergency_contact_name": "Ayse",
        "emergency_contact_phone": "5551111111",
        "accounting_type": "Kendi Muhasebecisi",
        "new_company_setup": "Hayır",
        "accounting_revenue": 0.0,
        "accountant_cost": 0.0,
        "company_setup_revenue": 0.0,
        "company_setup_cost": 0.0,
        "assigned_restaurant_id": 1,
        "vehicle_type": "Kendi Motoru",
        "motor_rental": "Hayır",
        "motor_purchase": "Hayır",
        "motor_purchase_start_date": None,
        "motor_purchase_commitment_months": 0,
        "motor_rental_monthly_amount": 0.0,
        "motor_purchase_sale_price": 0.0,
        "motor_purchase_monthly_amount": 0.0,
        "motor_purchase_installment_count": 0,
        "current_plate": "34ABC123",
        "start_date": "2026-03-01",
        "cost_model": "Kurye",
        "monthly_fixed_cost": 0.0,
        "notes": "Not",
    }


class PersonnelRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.conn = _make_conn()
        self.conn.execute("INSERT INTO restaurants (brand, branch, active) VALUES (?, ?, ?)", ("Fasuli", "Beyoglu", 1))
        self.conn.execute("INSERT INTO restaurants (brand, branch, active) VALUES (?, ?, ?)", ("Quick China", "Atasehir", 0))
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_and_fetch_personnel_management_df(self) -> None:
        insert_personnel_record(self.conn, _personnel_values())
        self.conn.commit()

        df = fetch_personnel_management_df(self.conn)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["full_name"], "Ali Veli")
        self.assertEqual(df.iloc[0]["restoran"], "Fasuli - Beyoglu")

    def test_fetch_active_restaurant_options_returns_only_active_restaurants(self) -> None:
        options = fetch_active_restaurant_options(self.conn)
        self.assertEqual(options, {"Fasuli - Beyoglu": 1})

    def test_fetch_person_options_map_respects_active_filter(self) -> None:
        active_values = _personnel_values()
        passive_values = _personnel_values()
        passive_values["person_code"] = "CK-K002"
        passive_values["full_name"] = "Mehmet Kaya"
        passive_values["status"] = "Pasif"
        insert_personnel_record(self.conn, active_values)
        insert_personnel_record(self.conn, passive_values)
        self.conn.commit()

        active_only = fetch_person_options_map(self.conn, active_only=True)
        all_people = fetch_person_options_map(self.conn, active_only=False)

        self.assertEqual(list(active_only.keys()), ["Ali Veli (Kurye)"])
        self.assertEqual(set(all_people.keys()), {"Ali Veli (Kurye)", "Mehmet Kaya (Kurye)"})

    def test_fetch_person_code_values_filters_by_prefix_and_exclude_id(self) -> None:
        first = _personnel_values()
        second = _personnel_values()
        second["person_code"] = "CK-K002"
        second["full_name"] = "Mehmet Kaya"
        third = _personnel_values()
        third["person_code"] = "CK-J001"
        third["full_name"] = "Ayse Yilmaz"
        third["role"] = "Joker"
        insert_personnel_record(self.conn, first)
        insert_personnel_record(self.conn, second)
        insert_personnel_record(self.conn, third)
        self.conn.commit()

        codes = fetch_person_code_values(self.conn, "K")
        codes_excluding_first = fetch_person_code_values(self.conn, "K", exclude_id=1)

        self.assertEqual(set(codes), {"CK-K001", "CK-K002"})
        self.assertEqual(codes_excluding_first, ["CK-K002"])

    def test_update_personnel_record_and_fetch_by_id_and_code(self) -> None:
        insert_personnel_record(self.conn, _personnel_values())
        self.conn.commit()

        updated = _personnel_values()
        updated["person_code"] = "CK-K009"
        updated["full_name"] = "Ali Veli Guncel"
        updated["assigned_restaurant_id"] = None
        updated["current_plate"] = "34XYZ987"
        update_personnel_record(self.conn, 1, updated)
        self.conn.commit()

        by_id = fetch_personnel_by_id(self.conn, 1)
        by_code = fetch_personnel_by_code(self.conn, "CK-K009")
        self.assertEqual(by_id["full_name"], "Ali Veli Guncel")
        self.assertEqual(by_id["current_plate"], "34XYZ987")
        self.assertIsNone(by_id["assigned_restaurant_id"])
        self.assertEqual(by_code["id"], 1)

    def test_update_personnel_status_sets_exit_date(self) -> None:
        insert_personnel_record(self.conn, _personnel_values())
        self.conn.commit()

        update_personnel_status(self.conn, 1, "Pasif", "2026-03-22")
        self.conn.commit()

        row = self.conn.execute("SELECT status, exit_date FROM personnel WHERE id = ?", (1,)).fetchone()
        self.assertEqual(row["status"], "Pasif")
        self.assertEqual(row["exit_date"], "2026-03-22")
