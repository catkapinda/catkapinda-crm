from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, fetch_df


def fetch_daily_entry_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT d.id, d.entry_date, r.brand || ' - ' || r.branch AS restoran,
               COALESCE(pp.full_name, '-') AS planlanan, COALESCE(ap.full_name, '-') AS calisan,
               d.status, d.worked_hours, d.package_count, COALESCE(d.notes, '') AS notes
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        ORDER BY d.entry_date DESC, restoran, d.id DESC
        LIMIT 500
        """,
    )


def fetch_daily_entry_by_id(conn: CompatConnection, entry_id: int):
    return conn.execute(
        """
        SELECT id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
               status, worked_hours, package_count, COALESCE(notes, '') AS notes
        FROM daily_entries
        WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()


def insert_daily_entry(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO daily_entries (
            entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
            status, worked_hours, package_count, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["entry_date"],
            values["restaurant_id"],
            values["planned_personnel_id"],
            values["actual_personnel_id"],
            values["status"],
            values["worked_hours"],
            values["package_count"],
            values["notes"],
        ),
    )


def update_daily_entry(conn: CompatConnection, entry_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE daily_entries
        SET entry_date = ?, restaurant_id = ?, planned_personnel_id = ?, actual_personnel_id = ?,
            status = ?, worked_hours = ?, package_count = ?, notes = ?
        WHERE id = ?
        """,
        (
            values["entry_date"],
            values["restaurant_id"],
            values["planned_personnel_id"],
            values["actual_personnel_id"],
            values["status"],
            values["worked_hours"],
            values["package_count"],
            values["notes"],
            entry_id,
        ),
    )


def delete_daily_entry(conn: CompatConnection, entry_id: int) -> None:
    conn.execute("DELETE FROM daily_entries WHERE id = ?", (entry_id,))


def fetch_bulk_attendance_people_rows(conn: CompatConnection, restaurant_id: int, include_all_active: bool):
    return conn.execute(
        """
        SELECT id, full_name, role
        FROM personnel
        WHERE status='Aktif'
          AND (? = 1 OR assigned_restaurant_id = ? OR role IN ('Joker', 'Bölge Müdürü', 'Saha Denetmen Şefi', 'Restoran Takım Şefi'))
        ORDER BY
            CASE
                WHEN role='Restoran Takım Şefi' THEN 1
                WHEN role='Saha Denetmen Şefi' THEN 2
                WHEN role='Bölge Müdürü' THEN 3
                WHEN role='Joker' THEN 4
                ELSE 5
            END,
            full_name
        """,
        (1 if include_all_active else 0, restaurant_id),
    ).fetchall()
