from __future__ import annotations

from typing import Any, Sequence

from infrastructure.db_engine import CompatConnection, cache_db_read, fetch_df


@cache_db_read(ttl=30)
def fetch_deduction_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT d.id, d.personnel_id, d.deduction_date, p.full_name AS personel, d.deduction_type, d.amount, d.notes, d.auto_source_key
        FROM deductions d
        JOIN personnel p ON p.id = d.personnel_id
        ORDER BY d.deduction_date DESC, d.id DESC
        """,
    )


def insert_deduction_record(conn: CompatConnection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO deductions (personnel_id, deduction_date, deduction_type, amount, notes) VALUES (?, ?, ?, ?, ?)",
        (
            values["personnel_id"],
            values["deduction_date"],
            values["deduction_type"],
            values["amount"],
            values["notes"],
        ),
    )


def update_deduction_record(conn: CompatConnection, deduction_id: int, values: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE deductions
        SET personnel_id = ?, deduction_date = ?, deduction_type = ?, amount = ?, notes = ?
        WHERE id = ?
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


def delete_deduction_record(conn: CompatConnection, deduction_id: int) -> None:
    conn.execute("DELETE FROM deductions WHERE id = ?", (deduction_id,))


def delete_deduction_records(conn: CompatConnection, deduction_ids: Sequence[int]) -> int:
    if not deduction_ids:
        return 0
    placeholders = ", ".join(["?"] * len(deduction_ids))
    conn.execute(f"DELETE FROM deductions WHERE id IN ({placeholders})", tuple(deduction_ids))
    return len(deduction_ids)
