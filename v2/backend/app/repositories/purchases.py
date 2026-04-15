from __future__ import annotations

from datetime import date

import psycopg

from app.core.database import is_sqlite_backend


def fetch_purchase_summary(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> dict[str, float | int]:
    if is_sqlite_backend(conn):
        month_key = reference_date.strftime("%Y-%m")
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                SUM(CASE WHEN substr(COALESCE(purchase_date, ''), 1, 7) = %s THEN 1 ELSE 0 END) AS this_month_entries,
                COALESCE(SUM(CASE WHEN substr(COALESCE(purchase_date, ''), 1, 7) = %s THEN COALESCE(total_invoice_amount, 0) ELSE 0 END), 0) AS this_month_total_invoice,
                COUNT(DISTINCT NULLIF(TRIM(COALESCE(supplier, '')), '')) AS distinct_suppliers
            FROM inventory_purchases
            """,
            (month_key, month_key),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', purchase_date) = DATE_TRUNC('month', %s::date)
                ) AS this_month_entries,
                COALESCE(SUM(total_invoice_amount) FILTER (
                    WHERE DATE_TRUNC('month', purchase_date) = DATE_TRUNC('month', %s::date)
                ), 0) AS this_month_total_invoice,
                COUNT(DISTINCT NULLIF(TRIM(COALESCE(supplier, '')), '')) AS distinct_suppliers
            FROM inventory_purchases
            """,
            (reference_date, reference_date),
        ).fetchone()
    if row is None:
        return {
            "total_entries": 0,
            "this_month_entries": 0,
            "this_month_total_invoice": 0.0,
            "distinct_suppliers": 0,
        }
    return {
        "total_entries": int(row["total_entries"] or 0),
        "this_month_entries": int(row["this_month_entries"] or 0),
        "this_month_total_invoice": float(row["this_month_total_invoice"] or 0),
        "distinct_suppliers": int(row["distinct_suppliers"] or 0),
    }


def fetch_recent_purchase_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            id,
            purchase_date,
            COALESCE(item_name, '') AS item_name,
            COALESCE(quantity, 0) AS quantity,
            COALESCE(total_invoice_amount, 0) AS total_invoice_amount,
            COALESCE(unit_cost, 0) AS unit_cost,
            COALESCE(supplier, '') AS supplier,
            COALESCE(invoice_no, '') AS invoice_no,
            COALESCE(notes, '') AS notes
        FROM inventory_purchases
        ORDER BY purchase_date DESC, id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_purchase_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    item_name: str | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        """
        SELECT
            id,
            purchase_date,
            COALESCE(item_name, '') AS item_name,
            COALESCE(quantity, 0) AS quantity,
            COALESCE(total_invoice_amount, 0) AS total_invoice_amount,
            COALESCE(unit_cost, 0) AS unit_cost,
            COALESCE(supplier, '') AS supplier,
            COALESCE(invoice_no, '') AS invoice_no,
            COALESCE(notes, '') AS notes
        FROM inventory_purchases
        WHERE (%s IS NULL OR item_name = %s)
          AND (
            %s IS NULL
            OR COALESCE(item_name, '') ILIKE %s
            OR COALESCE(supplier, '') ILIKE %s
            OR COALESCE(invoice_no, '') ILIKE %s
            OR COALESCE(notes, '') ILIKE %s
          )
        ORDER BY purchase_date DESC, id DESC
        LIMIT %s
        """,
        (
            item_name,
            item_name,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_purchase_management_records(
    conn: psycopg.Connection,
    *,
    item_name: str | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM inventory_purchases
        WHERE (%s IS NULL OR item_name = %s)
          AND (
            %s IS NULL
            OR COALESCE(item_name, '') ILIKE %s
            OR COALESCE(supplier, '') ILIKE %s
            OR COALESCE(invoice_no, '') ILIKE %s
            OR COALESCE(notes, '') ILIKE %s
          )
        """,
        (
            item_name,
            item_name,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_purchase_record_by_id(
    conn: psycopg.Connection,
    purchase_id: int,
) -> dict | None:
    row = conn.execute(
        """
        SELECT
            id,
            purchase_date,
            COALESCE(item_name, '') AS item_name,
            COALESCE(quantity, 0) AS quantity,
            COALESCE(total_invoice_amount, 0) AS total_invoice_amount,
            COALESCE(unit_cost, 0) AS unit_cost,
            COALESCE(supplier, '') AS supplier,
            COALESCE(invoice_no, '') AS invoice_no,
            COALESCE(notes, '') AS notes
        FROM inventory_purchases
        WHERE id = %s
        """,
        (purchase_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_purchase_record(
    conn: psycopg.Connection,
    values: dict[str, object],
) -> int:
    row = conn.execute(
        """
        INSERT INTO inventory_purchases (
            purchase_date,
            item_name,
            quantity,
            total_invoice_amount,
            unit_cost,
            supplier,
            invoice_no,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["purchase_date"],
            values["item_name"],
            values["quantity"],
            values["total_invoice_amount"],
            values["unit_cost"],
            values["supplier"],
            values["invoice_no"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def update_purchase_record(
    conn: psycopg.Connection,
    purchase_id: int,
    values: dict[str, object],
) -> None:
    conn.execute(
        """
        UPDATE inventory_purchases
        SET
            purchase_date = %s,
            item_name = %s,
            quantity = %s,
            total_invoice_amount = %s,
            unit_cost = %s,
            supplier = %s,
            invoice_no = %s,
            notes = %s
        WHERE id = %s
        """,
        (
            values["purchase_date"],
            values["item_name"],
            values["quantity"],
            values["total_invoice_amount"],
            values["unit_cost"],
            values["supplier"],
            values["invoice_no"],
            values["notes"],
            purchase_id,
        ),
    )


def delete_purchase_record(conn: psycopg.Connection, purchase_id: int) -> None:
    conn.execute("DELETE FROM inventory_purchases WHERE id = %s", (purchase_id,))
