from __future__ import annotations

from typing import Any

from infrastructure.db_engine import CompatConnection, cache_db_read, fetch_df


@cache_db_read(ttl=30)
def fetch_attendance_hero_stats(conn: CompatConnection, today_iso: str, month_start_iso: str):
    row = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM daily_entries WHERE entry_date = ?) AS today_count,
            (SELECT COUNT(*) FROM daily_entries WHERE entry_date BETWEEN ? AND ?) AS month_count,
            (SELECT COUNT(*) FROM daily_entries) AS total_count,
            (SELECT COUNT(*) FROM restaurants WHERE active = 1) AS active_restaurants
        """,
        (today_iso, month_start_iso, today_iso),
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


@cache_db_read(ttl=30)
def fetch_daily_entry_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT d.id, d.entry_date, d.planned_personnel_id, d.actual_personnel_id,
               r.brand || ' - ' || r.branch AS restoran,
               COALESCE(ap.full_name, pp.full_name, '-') AS calisan_personel,
               CASE
                   WHEN d.planned_personnel_id IS NOT NULL
                        AND d.actual_personnel_id IS NOT NULL
                        AND d.planned_personnel_id != d.actual_personnel_id
                        THEN COALESCE(NULLIF(d.coverage_type, ''), 'Destek')
                   WHEN d.planned_personnel_id IS NOT NULL
                        AND d.actual_personnel_id IS NULL THEN 'Haftalık İzin'
                   ELSE 'Restoran Kuryesi'
               END AS vardiya_akisi,
               COALESCE(d.absence_reason, '') AS neden_girmedi,
               COALESCE(d.coverage_type, '') AS yerine_giren_tipi,
               d.status, d.worked_hours, d.package_count, COALESCE(d.monthly_invoice_amount, 0) AS monthly_invoice_amount,
               COALESCE(d.notes, '') AS notes
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel pp ON pp.id = d.planned_personnel_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        ORDER BY d.entry_date DESC, restoran, d.id DESC
        """,
    )


@cache_db_read(ttl=30)
def fetch_daily_entry_by_id(conn: CompatConnection, entry_id: int):
    row = conn.execute(
        """
        SELECT id, entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
               status, worked_hours, package_count, COALESCE(monthly_invoice_amount, 0) AS monthly_invoice_amount,
               COALESCE(absence_reason, '') AS absence_reason,
               COALESCE(coverage_type, '') AS coverage_type,
               COALESCE(notes, '') AS notes
        FROM daily_entries
        WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def insert_daily_entry(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO daily_entries (
            entry_date, restaurant_id, planned_personnel_id, actual_personnel_id,
            status, worked_hours, package_count, monthly_invoice_amount, absence_reason, coverage_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["entry_date"],
            values["restaurant_id"],
            values["planned_personnel_id"],
            values["actual_personnel_id"],
            values["status"],
            values["worked_hours"],
            values["package_count"],
            values.get("monthly_invoice_amount", 0.0),
            values.get("absence_reason", ""),
            values.get("coverage_type", ""),
            values["notes"],
        ),
    )


def update_daily_entry(conn: CompatConnection, entry_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE daily_entries
        SET entry_date = ?, restaurant_id = ?, planned_personnel_id = ?, actual_personnel_id = ?,
            status = ?, worked_hours = ?, package_count = ?, monthly_invoice_amount = ?, absence_reason = ?, coverage_type = ?, notes = ?
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
            values.get("monthly_invoice_amount", 0.0),
            values.get("absence_reason", ""),
            values.get("coverage_type", ""),
            values["notes"],
            entry_id,
        ),
    )


def delete_daily_entry(conn: CompatConnection, entry_id: int) -> None:
    conn.execute("DELETE FROM daily_entries WHERE id = ?", (entry_id,))


def delete_daily_entries(conn: CompatConnection, entry_ids: list[int]) -> int:
    if not entry_ids:
        return 0
    placeholders = ", ".join("?" for _ in entry_ids)
    cursor = conn.execute(
        f"DELETE FROM daily_entries WHERE id IN ({placeholders})",
        tuple(entry_ids),
    )
    return max(int(cursor.rowcount or 0), 0)


@cache_db_read(ttl=30)
def fetch_attendance_restaurant_pricing_rows(conn: CompatConnection):
    rows = conn.execute(
        """
        SELECT id, brand, branch, pricing_model, fixed_monthly_fee
        FROM restaurants
        WHERE active = 1
        ORDER BY brand, branch
        """
    ).fetchall()
    return [dict(row) for row in rows]


@cache_db_read(ttl=30)
def fetch_bulk_attendance_people_rows(conn: CompatConnection, restaurant_id: int, include_all_active: bool):
    rows = conn.execute(
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
    return [dict(row) for row in rows]
