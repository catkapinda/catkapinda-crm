from __future__ import annotations

import psycopg

from app.core.database import is_sqlite_backend


def fetch_sales_summary(conn: psycopg.Connection) -> dict[str, int]:
    if is_sqlite_backend(conn):
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                SUM(CASE
                    WHEN status IN (
                        'Yeni Talep',
                        'İlk Görüşme Yapıldı',
                        'Teklif Hazırlanıyor',
                        'Teklif İletildi',
                        'Tekrar Aranacak',
                        'Toplantı Planlandı'
                    ) THEN 1 ELSE 0
                END) AS open_follow_up,
                SUM(CASE
                    WHEN status IN ('Teklif Hazırlanıyor', 'Teklif İletildi') THEN 1 ELSE 0
                END) AS proposal_stage,
                SUM(CASE
                    WHEN status = 'Sözleşme İmzalandı' THEN 1 ELSE 0
                END) AS won_count
            FROM sales_leads
            """
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                COUNT(*) FILTER (
                    WHERE status IN (
                        'Yeni Talep',
                        'İlk Görüşme Yapıldı',
                        'Teklif Hazırlanıyor',
                        'Teklif İletildi',
                        'Tekrar Aranacak',
                        'Toplantı Planlandı'
                    )
                ) AS open_follow_up,
                COUNT(*) FILTER (
                    WHERE status IN ('Teklif Hazırlanıyor', 'Teklif İletildi')
                ) AS proposal_stage,
                COUNT(*) FILTER (
                    WHERE status = 'Sözleşme İmzalandı'
                ) AS won_count
            FROM sales_leads
            """
        ).fetchone()
    return {
        "total_entries": int(row["total_entries"] or 0) if row else 0,
        "open_follow_up": int(row["open_follow_up"] or 0) if row else 0,
        "proposal_stage": int(row["proposal_stage"] or 0) if row else 0,
        "won_count": int(row["won_count"] or 0) if row else 0,
    }


def fetch_recent_sales_records(conn: psycopg.Connection, *, limit: int) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT *
        FROM sales_leads
        ORDER BY updated_at DESC NULLS LAST, id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return list(rows)


def fetch_sales_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    status: str | None = None,
    lead_source: str | None = None,
    search: str | None = None,
) -> list[dict[str, object]]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if lead_source:
        clauses.append("lead_source = %s")
        params.append(lead_source)
    if search:
        clauses.append(
            """
            (
              restaurant_name ILIKE %s
              OR city ILIKE %s
              OR district ILIKE %s
              OR contact_name ILIKE %s
              OR assigned_owner ILIKE %s
            )
            """
        )
        wildcard = f"%{search.strip()}%"
        params.extend([wildcard] * 5)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"""
        SELECT *
        FROM sales_leads
        {where_sql}
        ORDER BY updated_at DESC NULLS LAST, id DESC
        LIMIT %s
        """,
        (*params, limit),
    ).fetchall()
    return list(rows)


def count_sales_management_records(
    conn: psycopg.Connection,
    *,
    status: str | None = None,
    lead_source: str | None = None,
    search: str | None = None,
) -> int:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if lead_source:
        clauses.append("lead_source = %s")
        params.append(lead_source)
    if search:
        clauses.append(
            """
            (
              restaurant_name ILIKE %s
              OR city ILIKE %s
              OR district ILIKE %s
              OR contact_name ILIKE %s
              OR assigned_owner ILIKE %s
            )
            """
        )
        wildcard = f"%{search.strip()}%"
        params.extend([wildcard] * 5)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    row = conn.execute(
        f"SELECT COUNT(*) AS count FROM sales_leads {where_sql}",
        tuple(params),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def fetch_sales_record_by_id(conn: psycopg.Connection, sales_id: int) -> dict[str, object] | None:
    return conn.execute("SELECT * FROM sales_leads WHERE id = %s", (sales_id,)).fetchone()


def insert_sales_record(conn: psycopg.Connection, values: dict[str, object]) -> int:
    row = conn.execute(
        """
        INSERT INTO sales_leads (
            restaurant_name,
            city,
            district,
            address,
            contact_name,
            contact_phone,
            contact_email,
            requested_courier_count,
            lead_source,
            proposed_quote,
            pricing_model,
            hourly_rate,
            package_rate,
            package_threshold,
            package_rate_low,
            package_rate_high,
            fixed_monthly_fee,
            pricing_model_hint,
            status,
            next_follow_up_date,
            assigned_owner,
            notes,
            created_at,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            values["restaurant_name"],
            values["city"],
            values["district"],
            values["address"],
            values["contact_name"],
            values["contact_phone"],
            values["contact_email"],
            values["requested_courier_count"],
            values["lead_source"],
            values["proposed_quote"],
            values["pricing_model"],
            values["hourly_rate"],
            values["package_rate"],
            values["package_threshold"],
            values["package_rate_low"],
            values["package_rate_high"],
            values["fixed_monthly_fee"],
            values["pricing_model_hint"],
            values["status"],
            values["next_follow_up_date"],
            values["assigned_owner"],
            values["notes"],
            values["created_at"],
            values["updated_at"],
        ),
    ).fetchone()
    return int(row["id"] or 0) if row else 0


def update_sales_record(conn: psycopg.Connection, sales_id: int, values: dict[str, object]) -> None:
    conn.execute(
        """
        UPDATE sales_leads
        SET restaurant_name = %s,
            city = %s,
            district = %s,
            address = %s,
            contact_name = %s,
            contact_phone = %s,
            contact_email = %s,
            requested_courier_count = %s,
            lead_source = %s,
            proposed_quote = %s,
            pricing_model = %s,
            hourly_rate = %s,
            package_rate = %s,
            package_threshold = %s,
            package_rate_low = %s,
            package_rate_high = %s,
            fixed_monthly_fee = %s,
            pricing_model_hint = %s,
            status = %s,
            next_follow_up_date = %s,
            assigned_owner = %s,
            notes = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            values["restaurant_name"],
            values["city"],
            values["district"],
            values["address"],
            values["contact_name"],
            values["contact_phone"],
            values["contact_email"],
            values["requested_courier_count"],
            values["lead_source"],
            values["proposed_quote"],
            values["pricing_model"],
            values["hourly_rate"],
            values["package_rate"],
            values["package_threshold"],
            values["package_rate_low"],
            values["package_rate_high"],
            values["fixed_monthly_fee"],
            values["pricing_model_hint"],
            values["status"],
            values["next_follow_up_date"],
            values["assigned_owner"],
            values["notes"],
            values["updated_at"],
            sales_id,
        ),
    )


def delete_sales_record(conn: psycopg.Connection, sales_id: int) -> None:
    conn.execute("DELETE FROM sales_leads WHERE id = %s", (sales_id,))
