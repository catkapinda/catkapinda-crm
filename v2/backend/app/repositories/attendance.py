from __future__ import annotations

from datetime import date

import psycopg


def _restaurant_active_sql(column: str = "active") -> str:
    return f"COALESCE(LOWER(CAST({column} AS TEXT)), 'true') IN ('1', 't', 'true')"


def fetch_attendance_summary(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> dict[str, int]:
    month_start_text = reference_date.replace(day=1).isoformat()
    reference_date_text = reference_date.isoformat()
    row = conn.execute(
        f"""
        SELECT
            (SELECT COUNT(*) FROM daily_entries WHERE substr(COALESCE(entry_date, ''), 1, 10) = %s) AS today_count,
            (SELECT COUNT(*) FROM daily_entries WHERE substr(COALESCE(entry_date, ''), 1, 10) BETWEEN %s AND %s) AS month_count,
            (SELECT COUNT(*) FROM daily_entries) AS total_count,
            (SELECT COUNT(*) FROM restaurants WHERE {_restaurant_active_sql()}) AS active_restaurants
        """,
        (reference_date_text, month_start_text, reference_date_text),
    ).fetchone()
    if row is None:
        return {
            "today_count": 0,
            "month_count": 0,
            "total_count": 0,
            "active_restaurants": 0,
        }
    return {
        "today_count": int(row["today_count"] or 0),
        "month_count": int(row["month_count"] or 0),
        "total_count": int(row["total_count"] or 0),
        "active_restaurants": int(row["active_restaurants"] or 0),
    }


def fetch_recent_attendance_entries(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            d.id,
            d.entry_date,
            r.brand || ' - ' || r.branch AS restaurant,
            COALESCE(ap.full_name, pp.full_name, '-') AS employee_name,
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                     AND d.actual_personnel_id IS NOT NULL
                     AND d.planned_personnel_id <> d.actual_personnel_id
                    THEN COALESCE(NULLIF(d.coverage_type, ''), 'Destek')
                WHEN d.planned_personnel_id IS NOT NULL
                     AND d.actual_personnel_id IS NULL
                    THEN 'Haftalik Izin'
                ELSE 'Restoran Kuryesi'
            END AS entry_mode,
            COALESCE(d.absence_reason, '') AS absence_reason,
            COALESCE(d.coverage_type, '') AS coverage_type,
            COALESCE(d.worked_hours, 0) AS worked_hours,
            COALESCE(d.package_count, 0) AS package_count,
            COALESCE(d.monthly_invoice_amount, 0) AS monthly_invoice_amount,
            COALESCE(d.notes, '') AS notes
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        ORDER BY d.entry_date DESC, restaurant, d.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_attendance_restaurants(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT
            id,
            brand,
            branch,
            pricing_model,
            COALESCE(fixed_monthly_fee, 0) AS fixed_monthly_fee
        FROM restaurants
        WHERE {_restaurant_active_sql()}
        ORDER BY brand, branch
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_attendance_people(
    conn: psycopg.Connection,
    *,
    restaurant_id: int,
    include_all_active: bool = False,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, full_name, role
        FROM personnel
        WHERE status = 'Aktif'
          AND (
            %s = TRUE
            OR assigned_restaurant_id = %s
            OR role IN ('Joker', 'Bölge Müdürü', 'Saha Denetmen Şefi', 'Restoran Takım Şefi')
          )
        ORDER BY
            CASE
                WHEN role = 'Restoran Takım Şefi' THEN 1
                WHEN role = 'Saha Denetmen Şefi' THEN 2
                WHEN role = 'Bölge Müdürü' THEN 3
                WHEN role = 'Joker' THEN 4
                ELSE 5
            END,
            full_name
        """,
        (include_all_active, restaurant_id),
    ).fetchall()
    return [dict(row) for row in rows]


def insert_attendance_entry(conn: psycopg.Connection, values: dict) -> int:
    row = conn.execute(
        """
        INSERT INTO daily_entries (
            entry_date,
            restaurant_id,
            planned_personnel_id,
            actual_personnel_id,
            status,
            worked_hours,
            package_count,
            monthly_invoice_amount,
            absence_reason,
            coverage_type,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["entry_date"],
            values["restaurant_id"],
            values["planned_personnel_id"],
            values["actual_personnel_id"],
            values["status"],
            values["worked_hours"],
            values["package_count"],
            values["monthly_invoice_amount"],
            values["absence_reason"],
            values["coverage_type"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def fetch_attendance_management_entries(
    conn: psycopg.Connection,
    *,
    limit: int,
    restaurant_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    date_from_text = date_from.isoformat() if date_from else None
    date_to_text = date_to.isoformat() if date_to else None
    rows = conn.execute(
        """
        SELECT
            d.id,
            d.entry_date,
            d.restaurant_id,
            r.brand || ' - ' || r.branch AS restaurant,
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                     AND d.actual_personnel_id IS NOT NULL
                     AND d.planned_personnel_id <> d.actual_personnel_id
                    THEN COALESCE(NULLIF(d.coverage_type, ''), 'Destek')
                WHEN d.planned_personnel_id IS NOT NULL
                     AND d.actual_personnel_id IS NULL
                    THEN 'Haftalik Izin'
                ELSE 'Restoran Kuryesi'
            END AS entry_mode,
            d.planned_personnel_id AS primary_person_id,
            COALESCE(pp.full_name, '-') AS primary_person_label,
            d.actual_personnel_id AS replacement_person_id,
            CASE
                WHEN d.actual_personnel_id IS NULL THEN '-'
                WHEN d.planned_personnel_id = d.actual_personnel_id THEN '-'
                ELSE COALESCE(ap.full_name, '-')
            END AS replacement_person_label,
            COALESCE(d.absence_reason, '') AS absence_reason,
            COALESCE(d.coverage_type, '') AS coverage_type,
            COALESCE(d.worked_hours, 0) AS worked_hours,
            COALESCE(d.package_count, 0) AS package_count,
            COALESCE(d.monthly_invoice_amount, 0) AS monthly_invoice_amount,
            COALESCE(d.notes, '') AS notes
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        WHERE (%s IS NULL OR d.restaurant_id = %s)
          AND (%s IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) >= %s)
          AND (%s IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) <= %s)
          AND (
            %s IS NULL
            OR r.brand || ' - ' || r.branch ILIKE %s
            OR COALESCE(pp.full_name, '') ILIKE %s
            OR COALESCE(ap.full_name, '') ILIKE %s
            OR COALESCE(d.notes, '') ILIKE %s
          )
        ORDER BY d.entry_date DESC, restaurant, d.id DESC
        LIMIT %s
        """,
        (
            restaurant_id,
            restaurant_id,
            date_from_text,
            date_from_text,
            date_to_text,
            date_to_text,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_attendance_management_entries(
    conn: psycopg.Connection,
    *,
    restaurant_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    date_from_text = date_from.isoformat() if date_from else None
    date_to_text = date_to.isoformat() if date_to else None
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        WHERE (%s IS NULL OR d.restaurant_id = %s)
          AND (%s IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) >= %s)
          AND (%s IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) <= %s)
          AND (
            %s IS NULL
            OR r.brand || ' - ' || r.branch ILIKE %s
            OR COALESCE(pp.full_name, '') ILIKE %s
            OR COALESCE(ap.full_name, '') ILIKE %s
            OR COALESCE(d.notes, '') ILIKE %s
          )
        """,
        (
            restaurant_id,
            restaurant_id,
            date_from_text,
            date_from_text,
            date_to_text,
            date_to_text,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_attendance_management_entry_ids(
    conn: psycopg.Connection,
    *,
    restaurant_id: int | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[int]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    date_from_text = date_from.isoformat() if date_from else None
    date_to_text = date_to.isoformat() if date_to else None
    rows = conn.execute(
        """
        SELECT d.id
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        WHERE (%s IS NULL OR d.restaurant_id = %s)
          AND (%s IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) >= %s)
          AND (%s IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) <= %s)
          AND (
            %s IS NULL
            OR r.brand || ' - ' || r.branch ILIKE %s
            OR COALESCE(pp.full_name, '') ILIKE %s
            OR COALESCE(ap.full_name, '') ILIKE %s
            OR COALESCE(d.notes, '') ILIKE %s
          )
        ORDER BY d.id
        """,
        (
            restaurant_id,
            restaurant_id,
            date_from_text,
            date_from_text,
            date_to_text,
            date_to_text,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def fetch_attendance_entry_by_id(conn: psycopg.Connection, entry_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT
            d.id,
            d.entry_date,
            d.restaurant_id,
            r.brand || ' - ' || r.branch AS restaurant,
            CASE
                WHEN d.planned_personnel_id IS NOT NULL
                     AND d.actual_personnel_id IS NOT NULL
                     AND d.planned_personnel_id <> d.actual_personnel_id
                    THEN COALESCE(NULLIF(d.coverage_type, ''), 'Destek')
                WHEN d.planned_personnel_id IS NOT NULL
                     AND d.actual_personnel_id IS NULL
                    THEN 'Haftalik Izin'
                ELSE 'Restoran Kuryesi'
            END AS entry_mode,
            d.planned_personnel_id AS primary_person_id,
            COALESCE(pp.full_name, '-') AS primary_person_label,
            d.actual_personnel_id AS replacement_person_id,
            CASE
                WHEN d.actual_personnel_id IS NULL THEN '-'
                WHEN d.planned_personnel_id = d.actual_personnel_id THEN '-'
                ELSE COALESCE(ap.full_name, '-')
            END AS replacement_person_label,
            COALESCE(d.absence_reason, '') AS absence_reason,
            COALESCE(d.coverage_type, '') AS coverage_type,
            COALESCE(d.worked_hours, 0) AS worked_hours,
            COALESCE(d.package_count, 0) AS package_count,
            COALESCE(d.monthly_invoice_amount, 0) AS monthly_invoice_amount,
            COALESCE(d.notes, '') AS notes
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        WHERE d.id = %s
        """,
        (entry_id,),
    ).fetchone()
    return dict(row) if row else None


def fetch_attendance_entry_ids(
    conn: psycopg.Connection,
    *,
    entry_ids: list[int],
) -> list[int]:
    if not entry_ids:
        return []
    placeholders = ", ".join(["%s"] * len(entry_ids))
    rows = conn.execute(
        f"""
        SELECT id
        FROM daily_entries
        WHERE id IN ({placeholders})
        ORDER BY id
        """,
        tuple(entry_ids),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def update_attendance_entry(conn: psycopg.Connection, entry_id: int, values: dict) -> None:
    conn.execute(
        """
        UPDATE daily_entries
        SET
            entry_date = %s,
            restaurant_id = %s,
            planned_personnel_id = %s,
            actual_personnel_id = %s,
            status = %s,
            worked_hours = %s,
            package_count = %s,
            monthly_invoice_amount = %s,
            absence_reason = %s,
            coverage_type = %s,
            notes = %s
        WHERE id = %s
        """,
        (
            values["entry_date"],
            values["restaurant_id"],
            values["planned_personnel_id"],
            values["actual_personnel_id"],
            values["status"],
            values["worked_hours"],
            values["package_count"],
            values["monthly_invoice_amount"],
            values["absence_reason"],
            values["coverage_type"],
            values["notes"],
            entry_id,
        ),
    )


def delete_attendance_entry(conn: psycopg.Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM daily_entries WHERE id = %s", (entry_id,))


def delete_attendance_entries(conn: psycopg.Connection, entry_ids: list[int]) -> list[int]:
    if not entry_ids:
        return []
    placeholders = ", ".join(["%s"] * len(entry_ids))
    rows = conn.execute(
        f"""
        DELETE FROM daily_entries
        WHERE id IN ({placeholders})
        RETURNING id
        """,
        tuple(entry_ids),
    ).fetchall()
    return [int(row["id"]) for row in rows]
