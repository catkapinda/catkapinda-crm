from __future__ import annotations

import psycopg

from app.core.database import is_sqlite_backend


def _restaurant_active_sql(column: str = "active") -> str:
    return f"COALESCE(LOWER(CAST({column} AS TEXT)), 'true') IN ('1', 't', 'true')"


def _personnel_active_sql(column: str = "status") -> str:
    return (
        f"COALESCE(LOWER(TRIM(CAST({column} AS TEXT))), '') "
        "IN ('aktif', 'active', '1', 't', 'true')"
    )


def _personnel_passive_sql(column: str = "status") -> str:
    return f"COALESCE(LOWER(TRIM(CAST({column} AS TEXT))), '') IN ('pasif', 'passive', '0', 'f', 'false')"


def _coalesced_history_date_sql(date_column: str, changed_at_column: str) -> str:
    return (
        f"COALESCE(NULLIF(CAST({date_column} AS TEXT), ''), "
        f"SUBSTR(CAST({changed_at_column} AS TEXT), 1, 10))"
    )


def _truthy_sql(column: str) -> str:
    return f"COALESCE(LOWER(CAST({column} AS TEXT)), 'false') IN ('1', 't', 'true')"


def _optional_bigint_filter_sql(column: str) -> str:
    return f"(%s::bigint IS NULL OR {column} = %s::bigint)"


def _optional_text_equality_sql(column: str) -> str:
    return f"(%s::text IS NULL OR COALESCE(CAST({column} AS TEXT), '') = %s::text)"


def _optional_text_search_guard_sql() -> str:
    return "%s::text IS NULL"


def _active_storage_value(value: bool) -> int:
    return 1 if bool(value) else 0


def fetch_personnel_summary(conn: psycopg.Connection) -> dict[str, int]:
    if is_sqlite_backend(conn):
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_personnel,
                SUM(CASE WHEN {_personnel_active_sql()} THEN 1 ELSE 0 END) AS active_personnel,
                SUM(CASE WHEN {_personnel_passive_sql()} THEN 1 ELSE 0 END) AS passive_personnel,
                COUNT(DISTINCT CASE
                    WHEN {_personnel_active_sql()} AND assigned_restaurant_id IS NOT NULL THEN assigned_restaurant_id
                    ELSE NULL
                END) AS assigned_restaurants
            FROM personnel
            """
        ).fetchone()
    else:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_personnel,
                COUNT(*) FILTER (WHERE {_personnel_active_sql()}) AS active_personnel,
                COUNT(*) FILTER (WHERE {_personnel_passive_sql()}) AS passive_personnel,
                COUNT(DISTINCT assigned_restaurant_id) FILTER (
                    WHERE {_personnel_active_sql()} AND assigned_restaurant_id IS NOT NULL
                ) AS assigned_restaurants
            FROM personnel
            """
        ).fetchone()
    if row is None:
        return {
            "total_personnel": 0,
            "active_personnel": 0,
            "passive_personnel": 0,
            "assigned_restaurants": 0,
        }
    return {
        "total_personnel": int(row["total_personnel"] or 0),
        "active_personnel": int(row["active_personnel"] or 0),
        "passive_personnel": int(row["passive_personnel"] or 0),
        "assigned_restaurants": int(row["assigned_restaurants"] or 0),
    }


def fetch_recent_personnel_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(p.phone, '') AS phone,
            COALESCE(p.address, '') AS address,
            COALESCE(p.iban, '') AS iban,
            COALESCE(p.tax_number, '') AS tax_number,
            COALESCE(p.tax_office, '') AS tax_office,
            COALESCE(p.emergency_contact_name, '') AS emergency_contact_name,
            COALESCE(p.emergency_contact_phone, '') AS emergency_contact_phone,
            p.assigned_restaurant_id AS restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            p.motor_purchase_start_date,
            COALESCE(p.motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(p.motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(p.motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            COALESCE(p.current_plate, '') AS current_plate,
            p.start_date,
            COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(p.notes, '') AS notes
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY p.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_personnel_restaurants(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT id, brand, branch
        FROM restaurants
        WHERE {_restaurant_active_sql("active")}
        ORDER BY brand, branch
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_personnel_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    restaurant_id: int | None = None,
    role: str | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        f"""
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(p.phone, '') AS phone,
            COALESCE(p.address, '') AS address,
            COALESCE(p.iban, '') AS iban,
            COALESCE(p.tax_number, '') AS tax_number,
            COALESCE(p.tax_office, '') AS tax_office,
            COALESCE(p.emergency_contact_name, '') AS emergency_contact_name,
            COALESCE(p.emergency_contact_phone, '') AS emergency_contact_phone,
            p.assigned_restaurant_id AS restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            p.motor_purchase_start_date,
            COALESCE(p.motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(p.motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(p.motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            COALESCE(p.current_plate, '') AS current_plate,
            p.start_date,
            COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(p.notes, '') AS notes
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE {_optional_bigint_filter_sql('p.assigned_restaurant_id')}
          AND {_optional_text_equality_sql('p.role')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(p.person_code, '') ILIKE %s
            OR COALESCE(p.phone, '') ILIKE %s
            OR COALESCE(p.iban, '') ILIKE %s
            OR COALESCE(p.tax_number, '') ILIKE %s
            OR COALESCE(p.tax_office, '') ILIKE %s
            OR COALESCE(p.emergency_contact_name, '') ILIKE %s
            OR COALESCE(p.emergency_contact_phone, '') ILIKE %s
            OR COALESCE(r.brand || ' - ' || r.branch, '') ILIKE %s
          )
        ORDER BY p.full_name, p.id DESC
        LIMIT %s
        """,
        (
            restaurant_id,
            restaurant_id,
            role,
            role,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_personnel_management_records(
    conn: psycopg.Connection,
    *,
    restaurant_id: int | None = None,
    role: str | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE {_optional_bigint_filter_sql('p.assigned_restaurant_id')}
          AND {_optional_text_equality_sql('p.role')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(p.person_code, '') ILIKE %s
            OR COALESCE(p.phone, '') ILIKE %s
            OR COALESCE(p.iban, '') ILIKE %s
            OR COALESCE(p.tax_number, '') ILIKE %s
            OR COALESCE(p.tax_office, '') ILIKE %s
            OR COALESCE(p.emergency_contact_name, '') ILIKE %s
            OR COALESCE(p.emergency_contact_phone, '') ILIKE %s
            OR COALESCE(r.brand || ' - ' || r.branch, '') ILIKE %s
          )
        """,
        (
            restaurant_id,
            restaurant_id,
            role,
            role,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_personnel_record_by_id(
    conn: psycopg.Connection,
    person_id: int,
) -> dict | None:
    row = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(p.phone, '') AS phone,
            COALESCE(p.address, '') AS address,
            COALESCE(p.iban, '') AS iban,
            COALESCE(p.tax_number, '') AS tax_number,
            COALESCE(p.tax_office, '') AS tax_office,
            COALESCE(p.emergency_contact_name, '') AS emergency_contact_name,
            COALESCE(p.emergency_contact_phone, '') AS emergency_contact_phone,
            p.assigned_restaurant_id AS restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            p.motor_purchase_start_date,
            COALESCE(p.motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(p.motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(p.motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            COALESCE(p.current_plate, '') AS current_plate,
            p.start_date,
            COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(p.notes, '') AS notes
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE p.id = %s
        """,
        (person_id,),
    ).fetchone()
    return dict(row) if row else None


def fetch_person_code_values(
    conn: psycopg.Connection,
    prefix: str,
    *,
    exclude_id: int | None = None,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT person_code
        FROM personnel
        WHERE person_code ILIKE %s
          AND (%s::bigint IS NULL OR id <> %s::bigint)
        """,
        (f"CK-{prefix}%", exclude_id, exclude_id),
    ).fetchall()
    return [str(row["person_code"] or "") for row in rows]


def insert_personnel_record(conn: psycopg.Connection, values: dict) -> int:
    row = conn.execute(
        """
        INSERT INTO personnel (
            person_code,
            full_name,
            role,
            status,
            phone,
            address,
            iban,
            tax_number,
            tax_office,
            emergency_contact_name,
            emergency_contact_phone,
            accounting_type,
            new_company_setup,
            assigned_restaurant_id,
            vehicle_type,
            motor_rental,
            motor_purchase,
            motor_rental_monthly_amount,
            motor_purchase_start_date,
            motor_purchase_commitment_months,
            motor_purchase_sale_price,
            motor_purchase_monthly_deduction,
            current_plate,
            start_date,
            exit_date,
            cost_model,
            monthly_fixed_cost,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["person_code"],
            values["full_name"],
            values["role"],
            values["status"],
            values["phone"],
            values["address"],
            values["iban"],
            values["tax_number"],
            values["tax_office"],
            values["emergency_contact_name"],
            values["emergency_contact_phone"],
            values["accounting_type"],
            values["new_company_setup"],
            values["assigned_restaurant_id"],
            values["vehicle_type"],
            values["motor_rental"],
            values["motor_purchase"],
            values["motor_rental_monthly_amount"],
            values["motor_purchase_start_date"],
            values["motor_purchase_commitment_months"],
            values["motor_purchase_sale_price"],
            values["motor_purchase_monthly_deduction"],
            values["current_plate"],
            values["start_date"],
            values["exit_date"],
            values["cost_model"],
            values["monthly_fixed_cost"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def update_personnel_record(
    conn: psycopg.Connection,
    person_id: int,
    values: dict,
) -> None:
    conn.execute(
        """
        UPDATE personnel
        SET
            person_code = %s,
            full_name = %s,
            role = %s,
            status = %s,
            phone = %s,
            address = %s,
            iban = %s,
            tax_number = %s,
            tax_office = %s,
            emergency_contact_name = %s,
            emergency_contact_phone = %s,
            assigned_restaurant_id = %s,
            vehicle_type = %s,
            motor_rental = %s,
            motor_purchase = %s,
            motor_rental_monthly_amount = %s,
            motor_purchase_start_date = %s,
            motor_purchase_commitment_months = %s,
            motor_purchase_sale_price = %s,
            motor_purchase_monthly_deduction = %s,
            current_plate = %s,
            start_date = %s,
            exit_date = %s,
            cost_model = %s,
            monthly_fixed_cost = %s,
            notes = %s
        WHERE id = %s
        """,
        (
            values["person_code"],
            values["full_name"],
            values["role"],
            values["status"],
            values["phone"],
            values["address"],
            values["iban"],
            values["tax_number"],
            values["tax_office"],
            values["emergency_contact_name"],
            values["emergency_contact_phone"],
            values["assigned_restaurant_id"],
            values["vehicle_type"],
            values["motor_rental"],
            values["motor_purchase"],
            values["motor_rental_monthly_amount"],
            values["motor_purchase_start_date"],
            values["motor_purchase_commitment_months"],
            values["motor_purchase_sale_price"],
            values["motor_purchase_monthly_deduction"],
            values["current_plate"],
            values["start_date"],
            values["exit_date"],
            values["cost_model"],
            values["monthly_fixed_cost"],
            values["notes"],
            person_id,
        ),
    )


def update_personnel_status(
    conn: psycopg.Connection,
    person_id: int,
    *,
    status: str,
    exit_date: str | None,
) -> None:
    conn.execute(
        """
        UPDATE personnel
        SET status = %s, exit_date = %s
        WHERE id = %s
        """,
        (status, exit_date, person_id),
    )


def fetch_personnel_plate_baseline_candidates(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.current_plate, '') AS current_plate,
            p.start_date,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM plate_history ph
                    WHERE ph.personnel_id = p.id
                ),
                0
            ) AS plate_history_count
        FROM personnel p
        WHERE TRIM(COALESCE(p.current_plate, '')) <> ''
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_personnel_plate_candidates(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.current_plate, '') AS current_plate,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM plate_history ph
                    WHERE ph.personnel_id = p.id
                ),
                0
            ) AS plate_history_count
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            CASE WHEN COALESCE(p.status, '') = 'Aktif' THEN 0 ELSE 1 END,
            CASE WHEN TRIM(COALESCE(p.current_plate, '')) <> '' THEN 0 ELSE 1 END,
            p.full_name,
            p.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_plate_history_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    resolved_start_date_sql = "NULLIF(CAST(ph.start_date AS TEXT), '')"
    rows = conn.execute(
        f"""
        SELECT
            ph.id,
            ph.personnel_id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.current_plate, '') AS current_plate,
            COALESCE(ph.plate, '') AS plate,
            {resolved_start_date_sql} AS start_date,
            NULLIF(CAST(ph.end_date AS TEXT), '') AS end_date,
            COALESCE(ph.reason, '') AS reason,
            {_truthy_sql('ph.active')} AS active
        FROM plate_history ph
        JOIN personnel p ON p.id = ph.personnel_id
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            CASE WHEN {_truthy_sql('ph.active')} THEN 0 ELSE 1 END,
            {resolved_start_date_sql} DESC,
            ph.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def count_total_plate_history_records(conn: psycopg.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM plate_history
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_active_plate_history_records(conn: psycopg.Connection) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM plate_history
        WHERE {_truthy_sql('active')}
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_active_personnel_missing_plate(conn: psycopg.Connection) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM personnel
        WHERE {_personnel_active_sql()}
          AND TRIM(COALESCE(current_plate, '')) = ''
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_active_catkapinda_vehicle_personnel(conn: psycopg.Connection) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM personnel
        WHERE {_personnel_active_sql()}
          AND (
            COALESCE(vehicle_type, '') = 'Çat Kapında'
            OR COALESCE(motor_rental, 'Hayır') = 'Evet'
            OR COALESCE(motor_purchase, 'Hayır') = 'Evet'
          )
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_plate_history_records_for_personnel(
    conn: psycopg.Connection,
    person_id: int,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM plate_history
        WHERE personnel_id = %s
        """,
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_active_plate_history_record(
    conn: psycopg.Connection,
    person_id: int,
) -> dict | None:
    resolved_start_date_sql = "NULLIF(CAST(start_date AS TEXT), '')"
    row = conn.execute(
        f"""
        SELECT
            id,
            plate,
            {resolved_start_date_sql} AS start_date,
            NULLIF(CAST(end_date AS TEXT), '') AS end_date,
            reason
        FROM plate_history
        WHERE personnel_id = %s
          AND {_truthy_sql('active')}
        ORDER BY {resolved_start_date_sql} DESC, id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    return dict(row) if row else None


def close_active_plate_history_records(
    conn: psycopg.Connection,
    person_id: int,
    *,
    end_date: str,
) -> None:
    conn.execute(
        f"""
        UPDATE plate_history
        SET active = %s, end_date = %s
        WHERE personnel_id = %s
          AND {_truthy_sql('active')}
        """,
        (_active_storage_value(False), end_date, person_id),
    )


def insert_plate_history_record(
    conn: psycopg.Connection,
    *,
    personnel_id: int,
    plate: str,
    start_date: str,
    end_date: str | None,
    reason: str,
    active: bool,
) -> int:
    row = conn.execute(
        """
        INSERT INTO plate_history (
            personnel_id,
            plate,
            start_date,
            end_date,
            reason,
            active
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (personnel_id, plate, start_date, end_date, reason, _active_storage_value(active)),
    ).fetchone()
    return int(row["id"])


def update_personnel_current_plate(
    conn: psycopg.Connection,
    person_id: int,
    plate: str,
) -> None:
    conn.execute(
        """
        UPDATE personnel
        SET current_plate = %s
        WHERE id = %s
        """,
        (plate, person_id),
    )


def fetch_personnel_vehicle_baseline_candidates(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            p.start_date,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            p.motor_purchase_start_date,
            COALESCE(p.motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(p.motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(p.motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM personnel_vehicle_history pvh
                    WHERE pvh.personnel_id = p.id
                ),
                0
            ) AS vehicle_history_count
        FROM personnel p
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_personnel_vehicle_candidates(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            p.motor_purchase_start_date,
            COALESCE(p.motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(p.motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(p.motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            COALESCE(p.current_plate, '') AS current_plate,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM personnel_vehicle_history pvh
                    WHERE pvh.personnel_id = p.id
                ),
                0
            ) AS vehicle_history_count
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            CASE WHEN COALESCE(p.status, '') = 'Aktif' THEN 0 ELSE 1 END,
            CASE WHEN COALESCE(p.vehicle_type, '') = 'Çat Kapında' THEN 0 ELSE 1 END,
            p.full_name,
            p.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_vehicle_history_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    resolved_effective_date_sql = _coalesced_history_date_sql(
        "pvh.effective_date",
        "pvh.changed_at",
    )
    rows = conn.execute(
        f"""
        SELECT
            pvh.id,
            pvh.personnel_id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.current_plate, '') AS current_plate,
            COALESCE(pvh.vehicle_type, '') AS vehicle_type,
            COALESCE(pvh.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(pvh.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(pvh.motor_rental_monthly_amount, 13000) AS motor_rental_monthly_amount,
            pvh.motor_purchase_start_date,
            COALESCE(pvh.motor_purchase_commitment_months, 0) AS motor_purchase_commitment_months,
            COALESCE(pvh.motor_purchase_sale_price, 0) AS motor_purchase_sale_price,
            COALESCE(pvh.motor_purchase_monthly_deduction, 0) AS motor_purchase_monthly_deduction,
            {resolved_effective_date_sql} AS effective_date,
            COALESCE(pvh.notes, '') AS notes
        FROM personnel_vehicle_history pvh
        JOIN personnel p ON p.id = pvh.personnel_id
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            {resolved_effective_date_sql} DESC,
            pvh.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def count_total_vehicle_history_records(conn: psycopg.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM personnel_vehicle_history
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_active_motor_rental_cards(conn: psycopg.Connection) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM personnel
        WHERE {_personnel_active_sql()}
          AND COALESCE(motor_rental, 'Hayır') = 'Evet'
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_active_motor_sale_cards(conn: psycopg.Connection) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM personnel
        WHERE {_personnel_active_sql()}
          AND COALESCE(motor_purchase, 'Hayır') = 'Evet'
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_vehicle_history_records_for_personnel(
    conn: psycopg.Connection,
    person_id: int,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM personnel_vehicle_history
        WHERE personnel_id = %s
        """,
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_latest_vehicle_history_record(
    conn: psycopg.Connection,
    person_id: int,
) -> dict | None:
    resolved_effective_date_sql = _coalesced_history_date_sql(
        "effective_date",
        "changed_at",
    )
    row = conn.execute(
        f"""
        SELECT
            id,
            vehicle_type,
            motor_rental,
            motor_rental_monthly_amount,
            motor_purchase,
            motor_purchase_start_date,
            motor_purchase_commitment_months,
            motor_purchase_sale_price,
            motor_purchase_monthly_deduction,
            effective_date,
            notes
        FROM personnel_vehicle_history
        WHERE personnel_id = %s
        ORDER BY {resolved_effective_date_sql} DESC, id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_vehicle_history_record(
    conn: psycopg.Connection,
    *,
    personnel_id: int,
    vehicle_type: str,
    motor_rental: str,
    motor_rental_monthly_amount: float,
    motor_purchase: str,
    motor_purchase_start_date: str | None,
    motor_purchase_commitment_months: int,
    motor_purchase_sale_price: float,
    motor_purchase_monthly_deduction: float,
    effective_date: str,
    notes: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO personnel_vehicle_history (
            personnel_id,
            vehicle_type,
            motor_rental,
            motor_rental_monthly_amount,
            motor_purchase,
            motor_purchase_start_date,
            motor_purchase_commitment_months,
            motor_purchase_sale_price,
            motor_purchase_monthly_deduction,
            effective_date,
            changed_at,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        RETURNING id
        """,
        (
            personnel_id,
            vehicle_type,
            motor_rental,
            motor_rental_monthly_amount,
            motor_purchase,
            motor_purchase_start_date,
            motor_purchase_commitment_months,
            motor_purchase_sale_price,
            motor_purchase_monthly_deduction,
            effective_date,
            notes,
        ),
    ).fetchone()
    return int(row["id"])


def update_personnel_vehicle_fields(
    conn: psycopg.Connection,
    person_id: int,
    *,
    vehicle_type: str,
    motor_rental: str,
    motor_rental_monthly_amount: float,
    motor_purchase: str,
    motor_purchase_start_date: str | None,
    motor_purchase_commitment_months: int,
    motor_purchase_sale_price: float,
    motor_purchase_monthly_deduction: float,
) -> None:
    conn.execute(
        """
        UPDATE personnel
        SET
            vehicle_type = %s,
            motor_rental = %s,
            motor_rental_monthly_amount = %s,
            motor_purchase = %s,
            motor_purchase_start_date = %s,
            motor_purchase_commitment_months = %s,
            motor_purchase_sale_price = %s,
            motor_purchase_monthly_deduction = %s
        WHERE id = %s
        """,
        (
            vehicle_type,
            motor_rental,
            motor_rental_monthly_amount,
            motor_purchase,
            motor_purchase_start_date,
            motor_purchase_commitment_months,
            motor_purchase_sale_price,
            motor_purchase_monthly_deduction,
            person_id,
        ),
    )


def fetch_personnel_role_baseline_candidates(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            p.start_date,
            COALESCE(p.role, '') AS role,
            COALESCE(p.cost_model, '') AS cost_model,
            COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM personnel_role_history prh
                    WHERE prh.personnel_id = p.id
                ),
                0
            ) AS role_history_count
        FROM personnel p
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_personnel_role_candidates(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.cost_model, '') AS cost_model,
            COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM personnel_role_history prh
                    WHERE prh.personnel_id = p.id
                ),
                0
            ) AS role_history_count
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            CASE WHEN COALESCE(p.status, '') = 'Aktif' THEN 0 ELSE 1 END,
            p.full_name,
            p.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_role_history_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    resolved_effective_date_sql = _coalesced_history_date_sql(
        "prh.effective_date",
        "prh.changed_at",
    )
    rows = conn.execute(
        f"""
        SELECT
            prh.id,
            prh.personnel_id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.status, '') AS status,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(prh.role, '') AS role,
            COALESCE(prh.cost_model, '') AS cost_model,
            COALESCE(prh.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            {resolved_effective_date_sql} AS effective_date,
            COALESCE(prh.notes, '') AS notes
        FROM personnel_role_history prh
        JOIN personnel p ON p.id = prh.personnel_id
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            {resolved_effective_date_sql} DESC,
            prh.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def count_total_role_history_records(conn: psycopg.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM personnel_role_history
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_active_personnel_records(conn: psycopg.Connection) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM personnel
        WHERE {_personnel_active_sql()}
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_distinct_role_history_roles(conn: psycopg.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT COALESCE(role, '')) AS total_count
        FROM personnel_role_history
        """
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_role_history_records_for_personnel(
    conn: psycopg.Connection,
    person_id: int,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM personnel_role_history
        WHERE personnel_id = %s
        """,
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_latest_role_history_record(
    conn: psycopg.Connection,
    person_id: int,
) -> dict | None:
    resolved_effective_date_sql = _coalesced_history_date_sql(
        "effective_date",
        "changed_at",
    )
    row = conn.execute(
        f"""
        SELECT id, role, cost_model, monthly_fixed_cost, effective_date, notes
        FROM personnel_role_history
        WHERE personnel_id = %s
        ORDER BY {resolved_effective_date_sql} DESC, id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_role_history_record(
    conn: psycopg.Connection,
    *,
    personnel_id: int,
    role: str,
    cost_model: str,
    monthly_fixed_cost: float,
    effective_date: str,
    notes: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO personnel_role_history (
            personnel_id,
            role,
            cost_model,
            monthly_fixed_cost,
            effective_date,
            changed_at,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        RETURNING id
        """,
        (personnel_id, role, cost_model, monthly_fixed_cost, effective_date, notes),
    ).fetchone()
    return int(row["id"])


def update_personnel_role_fields(
    conn: psycopg.Connection,
    person_id: int,
    *,
    role: str,
    cost_model: str,
    monthly_fixed_cost: float,
) -> None:
    conn.execute(
        """
        UPDATE personnel
        SET role = %s,
            cost_model = %s,
            monthly_fixed_cost = %s
        WHERE id = %s
        """,
        (role, cost_model, monthly_fixed_cost, person_id),
    )


def count_personnel_linked_daily_entries(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM daily_entries
        WHERE planned_personnel_id = %s OR actual_personnel_id = %s
        """,
        (person_id, person_id),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_personnel_linked_deductions(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM deductions
        WHERE personnel_id = %s
           OR equipment_issue_id IN (
                SELECT id
                FROM courier_equipment_issues
                WHERE personnel_id = %s
           )
        """,
        (person_id, person_id),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_personnel_linked_role_history(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM personnel_role_history WHERE personnel_id = %s",
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_personnel_linked_vehicle_history(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM personnel_vehicle_history WHERE personnel_id = %s",
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_personnel_linked_plate_history(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM plate_history WHERE personnel_id = %s",
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_personnel_linked_equipment_issues(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM courier_equipment_issues WHERE personnel_id = %s",
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def count_personnel_linked_box_returns(conn: psycopg.Connection, person_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total_count FROM box_returns WHERE personnel_id = %s",
        (person_id,),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_personnel_equipment_issue_ids(conn: psycopg.Connection, person_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM courier_equipment_issues WHERE personnel_id = %s",
        (person_id,),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def delete_personnel_and_dependencies(conn: psycopg.Connection, person_id: int) -> None:
    equipment_issue_ids = fetch_personnel_equipment_issue_ids(conn, person_id)
    if equipment_issue_ids:
        placeholders = ", ".join(["%s"] * len(equipment_issue_ids))
        conn.execute(
            f"DELETE FROM deductions WHERE equipment_issue_id IN ({placeholders})",
            tuple(equipment_issue_ids),
        )
    conn.execute("DELETE FROM deductions WHERE personnel_id = %s", (person_id,))
    conn.execute("DELETE FROM box_returns WHERE personnel_id = %s", (person_id,))
    conn.execute("DELETE FROM personnel_role_history WHERE personnel_id = %s", (person_id,))
    conn.execute("DELETE FROM personnel_vehicle_history WHERE personnel_id = %s", (person_id,))
    conn.execute("DELETE FROM plate_history WHERE personnel_id = %s", (person_id,))
    conn.execute(
        "DELETE FROM daily_entries WHERE planned_personnel_id = %s OR actual_personnel_id = %s",
        (person_id, person_id),
    )
    conn.execute("DELETE FROM courier_equipment_issues WHERE personnel_id = %s", (person_id,))
    conn.execute("DELETE FROM personnel WHERE id = %s", (person_id,))
