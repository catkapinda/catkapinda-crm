from __future__ import annotations

from datetime import UTC, datetime

import psycopg


def fetch_restaurant_id_label_map(conn: psycopg.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT id, COALESCE(brand || ' - ' || branch, '-') AS restaurant_label
        FROM restaurants
        """
    ).fetchall()
    return {
        str(row["restaurant_label"] or "-"): int(row["id"])
        for row in rows
        if row["id"] is not None
    }


def restaurant_exists(conn: psycopg.Connection, restaurant_id: int) -> bool:
    row = conn.execute(
        "SELECT id FROM restaurants WHERE id = %s",
        (restaurant_id,),
    ).fetchone()
    return row is not None


def fetch_restaurant_collection_rows(
    conn: psycopg.Connection,
    *,
    collection_month: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.restaurant_id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            c.collection_month,
            COALESCE(c.status, 'Bekliyor') AS status,
            c.due_date,
            COALESCE(c.collected_amount, 0) AS collected_amount,
            c.payment_date,
            c.last_contact_date,
            COALESCE(c.responsible_name, '') AS responsible_name,
            COALESCE(c.note, '') AS note
        FROM restaurant_collections c
        JOIN restaurants r ON r.id = c.restaurant_id
        WHERE c.collection_month = %s
        ORDER BY restaurant
        """,
        (collection_month,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_restaurant_collection_row(
    conn: psycopg.Connection,
    *,
    restaurant_id: int,
    collection_month: str,
) -> dict[str, object] | None:
    row = conn.execute(
        """
        SELECT
            id,
            restaurant_id,
            collection_month,
            COALESCE(status, 'Bekliyor') AS status,
            due_date,
            COALESCE(collected_amount, 0) AS collected_amount,
            payment_date,
            last_contact_date,
            COALESCE(responsible_name, '') AS responsible_name,
            COALESCE(note, '') AS note
        FROM restaurant_collections
        WHERE restaurant_id = %s AND collection_month = %s
        """,
        (restaurant_id, collection_month),
    ).fetchone()
    return dict(row) if row else None


def insert_restaurant_collection_row(
    conn: psycopg.Connection,
    values: dict[str, object],
) -> int:
    row = conn.execute(
        """
        INSERT INTO restaurant_collections (
            restaurant_id,
            collection_month,
            status,
            due_date,
            collected_amount,
            payment_date,
            last_contact_date,
            responsible_name,
            note,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["restaurant_id"],
            values["collection_month"],
            values["status"],
            values["due_date"],
            values["collected_amount"],
            values["payment_date"],
            values["last_contact_date"],
            values["responsible_name"],
            values["note"],
            values["created_at"],
            values["updated_at"],
        ),
    ).fetchone()
    return int(row["id"])


def update_restaurant_collection_row(
    conn: psycopg.Connection,
    collection_id: int,
    values: dict[str, object],
) -> None:
    conn.execute(
        """
        UPDATE restaurant_collections
        SET
            status = %s,
            due_date = %s,
            collected_amount = %s,
            payment_date = %s,
            last_contact_date = %s,
            responsible_name = %s,
            note = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            values["status"],
            values["due_date"],
            values["collected_amount"],
            values["payment_date"],
            values["last_contact_date"],
            values["responsible_name"],
            values["note"],
            values["updated_at"],
            collection_id,
        ),
    )


def build_collection_values(
    *,
    restaurant_id: int,
    collection_month: str,
    status: str,
    due_date: object,
    collected_amount: float,
    payment_date: object,
    last_contact_date: object,
    responsible_name: str,
    note: str,
) -> dict[str, object]:
    timestamp = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    return {
        "restaurant_id": restaurant_id,
        "collection_month": collection_month,
        "status": status,
        "due_date": due_date,
        "collected_amount": collected_amount,
        "payment_date": payment_date,
        "last_contact_date": last_contact_date,
        "responsible_name": responsible_name,
        "note": note,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def build_collection_update_values(
    *,
    status: str,
    due_date: object,
    collected_amount: float,
    payment_date: object,
    last_contact_date: object,
    responsible_name: str,
    note: str,
) -> dict[str, object]:
    timestamp = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    return {
        "status": status,
        "due_date": due_date,
        "collected_amount": collected_amount,
        "payment_date": payment_date,
        "last_contact_date": last_contact_date,
        "responsible_name": responsible_name,
        "note": note,
        "updated_at": timestamp,
    }
