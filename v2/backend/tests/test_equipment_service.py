from datetime import date
import sqlite3

from app.core.database import CompatConnection
from app.schemas.equipment import EquipmentIssueCreateRequest
from app.services.equipment import build_equipment_form_options, create_equipment_issue_entry


def _build_conn() -> CompatConnection:
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    raw_conn.executescript(
        """
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            branch TEXT
        );
        CREATE TABLE personnel (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            status TEXT,
            assigned_restaurant_id INTEGER
        );
        CREATE TABLE inventory_purchases (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            quantity REAL,
            total_invoice_amount REAL
        );
        CREATE TABLE courier_equipment_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER,
            issue_date TEXT,
            item_name TEXT,
            quantity INTEGER,
            unit_cost REAL,
            unit_sale_price REAL,
            vat_rate REAL,
            installment_count INTEGER,
            sale_type TEXT,
            notes TEXT,
            auto_source_key TEXT
        );
        CREATE TABLE deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER,
            deduction_date TEXT,
            deduction_type TEXT,
            amount REAL,
            notes TEXT,
            equipment_issue_id INTEGER
        );
        """
    )
    raw_conn.execute(
        "INSERT INTO restaurants (id, brand, branch) VALUES (1, 'Quick China', 'Ataşehir')"
    )
    raw_conn.execute(
        """
        INSERT INTO personnel (id, full_name, role, status, assigned_restaurant_id)
        VALUES (10, 'Neçirvan Bulgan', 'Kurye', 'Aktif', 1)
        """
    )
    raw_conn.commit()
    return CompatConnection(raw_conn, "sqlite")


def test_build_equipment_form_options_includes_elcik():
    conn = _build_conn()

    payload = build_equipment_form_options(conn)

    assert "Elcik" in payload.issue_items
    assert "Elcik" in payload.item_defaults


def test_create_equipment_issue_entry_uses_item_name_for_installments():
    conn = _build_conn()

    response = create_equipment_issue_entry(
        conn,
        payload=EquipmentIssueCreateRequest(
            personnel_id=10,
            issue_date=date(2026, 5, 2),
            item_name="Elcik",
            quantity=1,
            unit_cost=500,
            unit_sale_price=1200,
            installment_count=2,
            sale_type="Satış",
            notes="Test zimmet",
        ),
    )

    assert response.equipment_issue_id > 0

    rows = conn.execute(
        """
        SELECT deduction_type, amount, notes
        FROM deductions
        WHERE equipment_issue_id = %s
        ORDER BY deduction_date, id
        """,
        (response.equipment_issue_id,),
    ).fetchall()

    assert len(rows) == 2
    assert [row["deduction_type"] for row in rows] == ["Elcik", "Elcik"]
    assert [row["notes"] for row in rows] == ["Elcik 1/2", "Elcik 2/2"]
    assert round(float(rows[0]["amount"]), 2) == 600.0
    assert round(float(rows[1]["amount"]), 2) == 600.0
