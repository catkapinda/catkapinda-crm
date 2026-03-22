from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, fetch_df


def fetch_personnel_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT p.*, r.brand || ' - ' || r.branch AS restoran
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY p.full_name
        """,
    )


def fetch_active_restaurant_options(conn: CompatConnection) -> dict[str, int]:
    rows = conn.execute("SELECT id, brand, branch FROM restaurants WHERE active=1 ORDER BY brand, branch").fetchall()
    return {f"{r['brand']} - {r['branch']}": r['id'] for r in rows}


def fetch_person_options_map(conn: CompatConnection, active_only: bool = True) -> dict[str, int]:
    sql = "SELECT id, full_name, role, status FROM personnel"
    if active_only:
        sql += " WHERE status='Aktif'"
    sql += " ORDER BY full_name"
    rows = conn.execute(sql).fetchall()
    return {f"{r['full_name']} ({r['role']})": r['id'] for r in rows}


def fetch_person_code_values(conn: CompatConnection, prefix: str, exclude_id: int | None = None) -> list[str]:
    sql = "SELECT person_code FROM personnel WHERE person_code LIKE ?"
    params: list[object] = [f"CK-{prefix}%"]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [str(row["person_code"] or "") for row in rows]


def insert_personnel_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO personnel (
            person_code, full_name, role, status, phone, address, tc_no, iban,
            emergency_contact_name, emergency_contact_phone,
            accounting_type, new_company_setup, accounting_revenue, accountant_cost, company_setup_revenue, company_setup_cost,
            assigned_restaurant_id, vehicle_type, motor_rental, motor_purchase, motor_purchase_start_date, motor_purchase_commitment_months,
            motor_rental_monthly_amount, motor_purchase_sale_price, motor_purchase_monthly_amount, motor_purchase_installment_count, current_plate, start_date,
            cost_model, monthly_fixed_cost, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["person_code"],
            values["full_name"],
            values["role"],
            values["status"],
            values["phone"],
            values["address"],
            values["tc_no"],
            values["iban"],
            values["emergency_contact_name"],
            values["emergency_contact_phone"],
            values["accounting_type"],
            values["new_company_setup"],
            values["accounting_revenue"],
            values["accountant_cost"],
            values["company_setup_revenue"],
            values["company_setup_cost"],
            values["assigned_restaurant_id"],
            values["vehicle_type"],
            values["motor_rental"],
            values["motor_purchase"],
            values["motor_purchase_start_date"],
            values["motor_purchase_commitment_months"],
            values["motor_rental_monthly_amount"],
            values["motor_purchase_sale_price"],
            values["motor_purchase_monthly_amount"],
            values["motor_purchase_installment_count"],
            values["current_plate"],
            values["start_date"],
            values["cost_model"],
            values["monthly_fixed_cost"],
            values["notes"],
        ),
    )


def update_personnel_record(conn: CompatConnection, person_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE personnel
        SET person_code=?, full_name=?, role=?, status=?, phone=?, address=?, tc_no=?, iban=?,
            emergency_contact_name=?, emergency_contact_phone=?,
            accounting_type=?, new_company_setup=?, accounting_revenue=?, accountant_cost=?, company_setup_revenue=?, company_setup_cost=?, assigned_restaurant_id=?,
            vehicle_type=?, motor_rental=?, motor_purchase=?, motor_purchase_start_date=?, motor_purchase_commitment_months=?, motor_rental_monthly_amount=?, motor_purchase_sale_price=?, motor_purchase_monthly_amount=?, motor_purchase_installment_count=?, current_plate=?, start_date=?,
            cost_model=?, monthly_fixed_cost=?, notes=?
        WHERE id=?
        """,
        (
            values["person_code"],
            values["full_name"],
            values["role"],
            values["status"],
            values["phone"],
            values["address"],
            values["tc_no"],
            values["iban"],
            values["emergency_contact_name"],
            values["emergency_contact_phone"],
            values["accounting_type"],
            values["new_company_setup"],
            values["accounting_revenue"],
            values["accountant_cost"],
            values["company_setup_revenue"],
            values["company_setup_cost"],
            values["assigned_restaurant_id"],
            values["vehicle_type"],
            values["motor_rental"],
            values["motor_purchase"],
            values["motor_purchase_start_date"],
            values["motor_purchase_commitment_months"],
            values["motor_rental_monthly_amount"],
            values["motor_purchase_sale_price"],
            values["motor_purchase_monthly_amount"],
            values["motor_purchase_installment_count"],
            values["current_plate"],
            values["start_date"],
            values["cost_model"],
            values["monthly_fixed_cost"],
            values["notes"],
            person_id,
        ),
    )


def update_personnel_status(conn: CompatConnection, person_id: int, status: str, exit_date: str | None) -> None:
    conn.execute("UPDATE personnel SET status=?, exit_date=? WHERE id=?", (status, exit_date, person_id))


def fetch_personnel_by_id(conn: CompatConnection, person_id: int):
    return conn.execute("SELECT * FROM personnel WHERE id = ?", (person_id,)).fetchone()


def fetch_personnel_by_code(conn: CompatConnection, person_code: str):
    return conn.execute("SELECT * FROM personnel WHERE person_code = ? ORDER BY id DESC", (person_code,)).fetchone()
