from __future__ import annotations

from datetime import date

import psycopg

from app.core.database import is_sqlite_backend


def _optional_bigint_filter_sql(column: str) -> str:
    return f"(%s::bigint IS NULL OR {column} = %s::bigint)"


def _optional_text_equality_sql(column: str) -> str:
    return f"(%s::text IS NULL OR {column} = %s::text)"


def _optional_text_search_guard_sql() -> str:
    return "%s::text IS NULL"


def fetch_equipment_summary(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> dict[str, float]:
    if is_sqlite_backend(conn):
        month_key = reference_date.strftime("%Y-%m")
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_issues,
                SUM(CASE WHEN substr(COALESCE(issue_date, ''), 1, 7) = %s THEN 1 ELSE 0 END) AS this_month_issues,
                COUNT(DISTINCT COALESCE(item_name, '')) AS distinct_items
            FROM courier_equipment_issues
            """,
            (month_key,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_issues,
                COUNT(*) FILTER (
                    WHERE DATE_TRUNC('month', issue_date::date) = DATE_TRUNC('month', %s::date)
                ) AS this_month_issues,
                COUNT(DISTINCT COALESCE(item_name, '')) AS distinct_items
            FROM courier_equipment_issues
            """,
            (reference_date,),
        ).fetchone()
    installment_row = conn.execute(
        "SELECT COUNT(*) AS installment_rows FROM deductions WHERE equipment_issue_id IS NOT NULL"
    ).fetchone()
    return_row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_box_returns,
            COALESCE(SUM(payout_amount), 0) AS total_box_payout
        FROM box_returns
        """
    ).fetchone()
    return {
        "total_issues": int(row["total_issues"] or 0) if row else 0,
        "this_month_issues": int(row["this_month_issues"] or 0) if row else 0,
        "distinct_items": int(row["distinct_items"] or 0) if row else 0,
        "installment_rows": int(installment_row["installment_rows"] or 0) if installment_row else 0,
        "total_box_returns": int(return_row["total_box_returns"] or 0) if return_row else 0,
        "total_box_payout": float(return_row["total_box_payout"] or 0) if return_row else 0.0,
    }


def fetch_equipment_personnel_options(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            COALESCE(p.full_name, '-') AS full_name,
            COALESCE(p.role, '') AS role,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant_label,
            COALESCE(p.status, '') AS status
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY
            CASE WHEN COALESCE(p.status, '') = 'Aktif' THEN 0 ELSE 1 END,
            p.full_name,
            p.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_equipment_cost_defaults(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            item_name,
            SUM(quantity) AS purchased_qty,
            COALESCE(SUM(total_invoice_amount), 0) AS purchased_total,
            CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount) / SUM(quantity) ELSE 0 END AS weighted_unit_cost
        FROM inventory_purchases
        GROUP BY item_name
        ORDER BY item_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_equipment_issues(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            i.id,
            i.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            i.issue_date,
            COALESCE(i.item_name, '') AS item_name,
            COALESCE(i.quantity, 0) AS quantity,
            COALESCE(i.unit_cost, 0) AS unit_cost,
            COALESCE(i.unit_sale_price, 0) AS unit_sale_price,
            COALESCE(i.vat_rate, 20) AS vat_rate,
            COALESCE(i.installment_count, 1) AS installment_count,
            COALESCE(i.sale_type, 'Satış') AS sale_type,
            COALESCE(i.notes, '') AS notes,
            COALESCE(i.auto_source_key, '') AS auto_source_key,
            COALESCE(i.quantity, 0) * COALESCE(i.unit_cost, 0) AS total_cost,
            COALESCE(i.quantity, 0) * COALESCE(i.unit_sale_price, 0) AS total_sale,
            (COALESCE(i.quantity, 0) * COALESCE(i.unit_sale_price, 0))
              - (COALESCE(i.quantity, 0) * COALESCE(i.unit_cost, 0)) AS gross_profit
        FROM courier_equipment_issues i
        LEFT JOIN personnel p ON p.id = i.personnel_id
        ORDER BY i.issue_date DESC, i.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_box_returns(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            b.id,
            b.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            b.return_date,
            COALESCE(b.quantity, 0) AS quantity,
            COALESCE(b.condition_status, '') AS condition_status,
            COALESCE(b.payout_amount, 0) AS payout_amount,
            COALESCE(b.waived, 0) AS waived,
            COALESCE(b.notes, '') AS notes
        FROM box_returns b
        LEFT JOIN personnel p ON p.id = b.personnel_id
        ORDER BY b.return_date DESC, b.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_equipment_installments(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            d.deduction_date,
            COALESCE(p.full_name, '-') AS personnel_label,
            COALESCE(d.deduction_type, '') AS deduction_type,
            COALESCE(d.amount, 0) AS amount,
            COALESCE(d.notes, '') AS notes,
            COALESCE(d.auto_source_key, '') AS auto_source_key
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        WHERE d.equipment_issue_id IS NOT NULL
        ORDER BY d.deduction_date DESC, d.id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_equipment_sales_profit(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            COALESCE(item_name, '') AS item_name,
            COALESCE(SUM(quantity), 0) AS sold_qty,
            COALESCE(SUM(quantity * unit_cost), 0) AS total_cost,
            COALESCE(SUM(quantity * unit_sale_price), 0) AS total_sale,
            COALESCE(SUM((quantity * unit_sale_price) - (quantity * unit_cost)), 0) AS gross_profit
        FROM courier_equipment_issues
        WHERE sale_type = 'Satış'
        GROUP BY item_name
        ORDER BY total_sale DESC, item_name
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_equipment_purchase_summary(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            item_name,
            SUM(quantity) AS purchased_qty,
            COALESCE(SUM(total_invoice_amount), 0) AS purchased_total,
            CASE WHEN SUM(quantity) > 0 THEN SUM(total_invoice_amount) / SUM(quantity) ELSE 0 END AS weighted_unit_cost
        FROM inventory_purchases
        GROUP BY item_name
        ORDER BY item_name
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_equipment_issue_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    personnel_id: int | None = None,
    item_name: str | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        f"""
        SELECT
            i.id,
            i.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            i.issue_date,
            COALESCE(i.item_name, '') AS item_name,
            COALESCE(i.quantity, 0) AS quantity,
            COALESCE(i.unit_cost, 0) AS unit_cost,
            COALESCE(i.unit_sale_price, 0) AS unit_sale_price,
            COALESCE(i.vat_rate, 20) AS vat_rate,
            COALESCE(i.installment_count, 1) AS installment_count,
            COALESCE(i.sale_type, 'Satış') AS sale_type,
            COALESCE(i.notes, '') AS notes,
            COALESCE(i.auto_source_key, '') AS auto_source_key,
            COALESCE(i.quantity, 0) * COALESCE(i.unit_cost, 0) AS total_cost,
            COALESCE(i.quantity, 0) * COALESCE(i.unit_sale_price, 0) AS total_sale,
            (COALESCE(i.quantity, 0) * COALESCE(i.unit_sale_price, 0))
              - (COALESCE(i.quantity, 0) * COALESCE(i.unit_cost, 0)) AS gross_profit
        FROM courier_equipment_issues i
        LEFT JOIN personnel p ON p.id = i.personnel_id
        WHERE {_optional_bigint_filter_sql('i.personnel_id')}
          AND {_optional_text_equality_sql('i.item_name')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(i.item_name, '') ILIKE %s
            OR COALESCE(i.sale_type, '') ILIKE %s
            OR COALESCE(i.notes, '') ILIKE %s
          )
        ORDER BY i.issue_date DESC, i.id DESC
        LIMIT %s
        """,
        (
            personnel_id,
            personnel_id,
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


def count_equipment_issue_management_records(
    conn: psycopg.Connection,
    *,
    personnel_id: int | None = None,
    item_name: str | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM courier_equipment_issues i
        LEFT JOIN personnel p ON p.id = i.personnel_id
        WHERE {_optional_bigint_filter_sql('i.personnel_id')}
          AND {_optional_text_equality_sql('i.item_name')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(i.item_name, '') ILIKE %s
            OR COALESCE(i.sale_type, '') ILIKE %s
            OR COALESCE(i.notes, '') ILIKE %s
          )
        """,
        (
            personnel_id,
            personnel_id,
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


def fetch_equipment_issue_by_id(conn: psycopg.Connection, issue_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT
            i.id,
            i.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            i.issue_date,
            COALESCE(i.item_name, '') AS item_name,
            COALESCE(i.quantity, 0) AS quantity,
            COALESCE(i.unit_cost, 0) AS unit_cost,
            COALESCE(i.unit_sale_price, 0) AS unit_sale_price,
            COALESCE(i.vat_rate, 20) AS vat_rate,
            COALESCE(i.installment_count, 1) AS installment_count,
            COALESCE(i.sale_type, 'Satış') AS sale_type,
            COALESCE(i.notes, '') AS notes,
            COALESCE(i.auto_source_key, '') AS auto_source_key,
            COALESCE(i.quantity, 0) * COALESCE(i.unit_cost, 0) AS total_cost,
            COALESCE(i.quantity, 0) * COALESCE(i.unit_sale_price, 0) AS total_sale,
            (COALESCE(i.quantity, 0) * COALESCE(i.unit_sale_price, 0))
              - (COALESCE(i.quantity, 0) * COALESCE(i.unit_cost, 0)) AS gross_profit
        FROM courier_equipment_issues i
        LEFT JOIN personnel p ON p.id = i.personnel_id
        WHERE i.id = %s
        """,
        (issue_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_equipment_issue_record(conn: psycopg.Connection, values: dict[str, object]) -> int:
    row = conn.execute(
        """
        INSERT INTO courier_equipment_issues (
            personnel_id,
            issue_date,
            item_name,
            quantity,
            unit_cost,
            unit_sale_price,
            vat_rate,
            installment_count,
            sale_type,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["personnel_id"],
            values["issue_date"],
            values["item_name"],
            values["quantity"],
            values["unit_cost"],
            values["unit_sale_price"],
            values["vat_rate"],
            values["installment_count"],
            values["sale_type"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def update_equipment_issue_record(conn: psycopg.Connection, issue_id: int, values: dict[str, object]) -> None:
    conn.execute(
        """
        UPDATE courier_equipment_issues
        SET
            personnel_id = %s,
            issue_date = %s,
            item_name = %s,
            quantity = %s,
            unit_cost = %s,
            unit_sale_price = %s,
            vat_rate = %s,
            installment_count = %s,
            sale_type = %s,
            notes = %s
        WHERE id = %s
        """,
        (
            values["personnel_id"],
            values["issue_date"],
            values["item_name"],
            values["quantity"],
            values["unit_cost"],
            values["unit_sale_price"],
            values["vat_rate"],
            values["installment_count"],
            values["sale_type"],
            values["notes"],
            issue_id,
        ),
    )


def delete_equipment_issue_installments(conn: psycopg.Connection, issue_id: int) -> None:
    conn.execute("DELETE FROM deductions WHERE equipment_issue_id = %s", (issue_id,))


def delete_equipment_issue_record(conn: psycopg.Connection, issue_id: int) -> None:
    conn.execute("DELETE FROM courier_equipment_issues WHERE id = %s", (issue_id,))


def fetch_box_return_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    personnel_id: int | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        f"""
        SELECT
            b.id,
            b.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            b.return_date,
            COALESCE(b.quantity, 0) AS quantity,
            COALESCE(b.condition_status, '') AS condition_status,
            COALESCE(b.payout_amount, 0) AS payout_amount,
            COALESCE(b.waived, 0) AS waived,
            COALESCE(b.notes, '') AS notes
        FROM box_returns b
        LEFT JOIN personnel p ON p.id = b.personnel_id
        WHERE {_optional_bigint_filter_sql('b.personnel_id')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(b.condition_status, '') ILIKE %s
            OR COALESCE(b.notes, '') ILIKE %s
          )
        ORDER BY b.return_date DESC, b.id DESC
        LIMIT %s
        """,
        (
            personnel_id,
            personnel_id,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_box_return_management_records(
    conn: psycopg.Connection,
    *,
    personnel_id: int | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total_count
        FROM box_returns b
        LEFT JOIN personnel p ON p.id = b.personnel_id
        WHERE {_optional_bigint_filter_sql('b.personnel_id')}
          AND (
            {_optional_text_search_guard_sql()}
            OR COALESCE(p.full_name, '') ILIKE %s
            OR COALESCE(b.condition_status, '') ILIKE %s
            OR COALESCE(b.notes, '') ILIKE %s
          )
        """,
        (
            personnel_id,
            personnel_id,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_box_return_by_id(conn: psycopg.Connection, box_return_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT
            b.id,
            b.personnel_id,
            COALESCE(p.full_name, '-') AS personnel_label,
            b.return_date,
            COALESCE(b.quantity, 0) AS quantity,
            COALESCE(b.condition_status, '') AS condition_status,
            COALESCE(b.payout_amount, 0) AS payout_amount,
            COALESCE(b.waived, 0) AS waived,
            COALESCE(b.notes, '') AS notes
        FROM box_returns b
        LEFT JOIN personnel p ON p.id = b.personnel_id
        WHERE b.id = %s
        """,
        (box_return_id,),
    ).fetchone()
    return dict(row) if row else None


def insert_box_return_record(conn: psycopg.Connection, values: dict[str, object]) -> int:
    row = conn.execute(
        """
        INSERT INTO box_returns (
            personnel_id,
            return_date,
            quantity,
            condition_status,
            payout_amount,
            waived,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            values["personnel_id"],
            values["return_date"],
            values["quantity"],
            values["condition_status"],
            values["payout_amount"],
            values["waived"],
            values["notes"],
        ),
    ).fetchone()
    return int(row["id"])


def update_box_return_record(conn: psycopg.Connection, box_return_id: int, values: dict[str, object]) -> None:
    conn.execute(
        """
        UPDATE box_returns
        SET
            personnel_id = %s,
            return_date = %s,
            quantity = %s,
            condition_status = %s,
            payout_amount = %s,
            waived = %s,
            notes = %s
        WHERE id = %s
        """,
        (
            values["personnel_id"],
            values["return_date"],
            values["quantity"],
            values["condition_status"],
            values["payout_amount"],
            values["waived"],
            values["notes"],
            box_return_id,
        ),
    )


def delete_box_return_record(conn: psycopg.Connection, box_return_id: int) -> None:
    conn.execute("DELETE FROM box_returns WHERE id = %s", (box_return_id,))
