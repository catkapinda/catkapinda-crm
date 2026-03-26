from __future__ import annotations

import psycopg


def fetch_personnel_summary(conn: psycopg.Connection) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_personnel,
            COUNT(*) FILTER (WHERE status = 'Aktif') AS active_personnel,
            COUNT(*) FILTER (WHERE status = 'Pasif') AS passive_personnel,
            COUNT(DISTINCT assigned_restaurant_id) FILTER (
                WHERE status = 'Aktif' AND assigned_restaurant_id IS NOT NULL
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
        """
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(p.phone, '') AS phone,
            p.assigned_restaurant_id AS restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
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
        """
        SELECT id, brand, branch
        FROM restaurants
        WHERE active = TRUE
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
        """
        SELECT
            p.id,
            COALESCE(p.person_code, '') AS person_code,
            COALESCE(p.full_name, '') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(p.status, '') AS status,
            COALESCE(p.phone, '') AS phone,
            p.assigned_restaurant_id AS restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
            COALESCE(p.current_plate, '') AS current_plate,
            p.start_date,
            COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
            COALESCE(p.notes, '') AS notes
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE (%s IS NULL OR p.assigned_restaurant_id = %s)
          AND (%s IS NULL OR p.role = %s)
          AND (
            %s IS NULL
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(p.person_code, '') ILIKE %s
            OR COALESCE(p.phone, '') ILIKE %s
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
        """
        SELECT COUNT(*) AS total_count
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE (%s IS NULL OR p.assigned_restaurant_id = %s)
          AND (%s IS NULL OR p.role = %s)
          AND (
            %s IS NULL
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(p.person_code, '') ILIKE %s
            OR COALESCE(p.phone, '') ILIKE %s
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
            p.assigned_restaurant_id AS restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.vehicle_type, '') AS vehicle_type,
            COALESCE(p.motor_rental, 'Hayır') AS motor_rental,
            COALESCE(p.motor_purchase, 'Hayır') AS motor_purchase,
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
          AND (%s IS NULL OR id <> %s)
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
            accounting_type,
            new_company_setup,
            assigned_restaurant_id,
            vehicle_type,
            motor_rental,
            motor_purchase,
            current_plate,
            start_date,
            cost_model,
            monthly_fixed_cost,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["person_code"],
            values["full_name"],
            values["role"],
            values["status"],
            values["phone"],
            values["accounting_type"],
            values["new_company_setup"],
            values["assigned_restaurant_id"],
            values["vehicle_type"],
            values["motor_rental"],
            values["motor_purchase"],
            values["current_plate"],
            values["start_date"],
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
            assigned_restaurant_id = %s,
            vehicle_type = %s,
            motor_rental = %s,
            motor_purchase = %s,
            current_plate = %s,
            start_date = %s,
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
            values["assigned_restaurant_id"],
            values["vehicle_type"],
            values["motor_rental"],
            values["motor_purchase"],
            values["current_plate"],
            values["start_date"],
            values["cost_model"],
            values["monthly_fixed_cost"],
            values["notes"],
            person_id,
        ),
    )
