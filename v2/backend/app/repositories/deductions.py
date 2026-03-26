from __future__ import annotations

from datetime import date

import psycopg


def fetch_deduction_summary(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_entries,
            COUNT(*) FILTER (
                WHERE DATE_TRUNC('month', deduction_date) = DATE_TRUNC('month', %s::date)
            ) AS this_month_entries,
            COUNT(*) FILTER (
                WHERE COALESCE(auto_source_key, '') = ''
            ) AS manual_entries,
            COUNT(*) FILTER (
                WHERE COALESCE(auto_source_key, '') <> ''
            ) AS auto_entries
        FROM deductions
        """,
        (reference_date,),
    ).fetchone()
    if row is None:
        return {
            "total_entries": 0,
            "this_month_entries": 0,
            "manual_entries": 0,
            "auto_entries": 0,
        }
    return {
        "total_entries": int(row["total_entries"] or 0),
        "this_month_entries": int(row["this_month_entries"] or 0),
        "manual_entries": int(row["manual_entries"] or 0),
        "auto_entries": int(row["auto_entries"] or 0),
    }


def fetch_recent_deduction_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            d.id,
            d.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            d.deduction_date,
            COALESCE(d.deduction_type, '') AS deduction_type,
            COALESCE(d.amount, 0) AS amount,
            COALESCE(d.notes, '') AS notes,
            COALESCE(d.auto_source_key, '') AS auto_source_key
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        ORDER BY d.deduction_date DESC, d.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_deduction_personnel_options(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.full_name, '-') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE COALESCE(p.status, '') = 'Aktif'
        ORDER BY p.full_name, p.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_deduction_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    personnel_id: int | None = None,
    deduction_type: str | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        """
        SELECT
            d.id,
            d.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            d.deduction_date,
            COALESCE(d.deduction_type, '') AS deduction_type,
            COALESCE(d.amount, 0) AS amount,
            COALESCE(d.notes, '') AS notes,
            COALESCE(d.auto_source_key, '') AS auto_source_key
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        WHERE (%s IS NULL OR d.personnel_id = %s)
          AND (%s IS NULL OR d.deduction_type = %s)
          AND (
            %s IS NULL
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(d.deduction_type, '') ILIKE %s
            OR COALESCE(d.notes, '') ILIKE %s
          )
        ORDER BY d.deduction_date DESC, d.id DESC
        LIMIT %s
        """,
        (
            personnel_id,
            personnel_id,
            deduction_type,
            deduction_type,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_deduction_management_records(
    conn: psycopg.Connection,
    *,
    personnel_id: int | None = None,
    deduction_type: str | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        WHERE (%s IS NULL OR d.personnel_id = %s)
          AND (%s IS NULL OR d.deduction_type = %s)
          AND (
            %s IS NULL
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(d.deduction_type, '') ILIKE %s
            OR COALESCE(d.notes, '') ILIKE %s
          )
        """,
        (
            personnel_id,
            personnel_id,
            deduction_type,
            deduction_type,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_deduction_record_by_id(
    conn: psycopg.Connection,
    deduction_id: int,
) -> dict | None:
    row = conn.execute(
        """
        SELECT
            d.id,
            d.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            d.deduction_date,
            COALESCE(d.deduction_type, '') AS deduction_type,
            COALESCE(d.amount, 0) AS amount,
            COALESCE(d.notes, '') AS notes,
            COALESCE(d.auto_source_key, '') AS auto_source_key
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        WHERE d.id = %s
        """,
        (deduction_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_deduction_record(
    conn: psycopg.Connection,
    values: dict[str, object],
) -> int:
    row = conn.execute(
        """
        INSERT INTO deductions (
            personnel_id,
            deduction_date,
            deduction_type,
            amount,
            notes
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["personnel_id"],
            values["deduction_date"],
            values["deduction_type"],
            values["amount"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def update_deduction_record(
    conn: psycopg.Connection,
    deduction_id: int,
    values: dict[str, object],
) -> None:
    conn.execute(
        """
        UPDATE deductions
        SET
            personnel_id = %s,
            deduction_date = %s,
            deduction_type = %s,
            amount = %s,
            notes = %s
        WHERE id = %s
        """,
        (
            values["personnel_id"],
            values["deduction_date"],
            values["deduction_type"],
            values["amount"],
            values["notes"],
            deduction_id,
        ),
    )


def delete_deduction_record(conn: psycopg.Connection, deduction_id: int) -> None:
    conn.execute("DELETE FROM deductions WHERE id = %s", (deduction_id,))
