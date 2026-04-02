from __future__ import annotations

from datetime import datetime, timedelta

import psycopg


def fetch_audit_summary(conn: psycopg.Connection) -> dict[str, int]:
    last_7_days_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat(timespec="seconds")
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_entries,
            COUNT(*) FILTER (
                WHERE created_at >= %s
            ) AS last_7_days,
            COUNT(DISTINCT COALESCE(NULLIF(actor_username, ''), actor_full_name, 'unknown')) AS unique_actors,
            COUNT(DISTINCT COALESCE(NULLIF(entity_type, ''), 'unknown')) AS unique_entities
        FROM audit_logs
        """,
        (last_7_days_cutoff,),
    ).fetchone()
    if row is None:
        return {
            "total_entries": 0,
            "last_7_days": 0,
            "unique_actors": 0,
            "unique_entities": 0,
        }
    return {
        "total_entries": int(row["total_entries"] or 0),
        "last_7_days": int(row["last_7_days"] or 0),
        "unique_actors": int(row["unique_actors"] or 0),
        "unique_entities": int(row["unique_entities"] or 0),
    }


def fetch_recent_audit_records(
    conn: psycopg.Connection,
    *,
    limit: int,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            id,
            created_at,
            COALESCE(actor_username, '') AS actor_username,
            COALESCE(actor_full_name, '') AS actor_full_name,
            COALESCE(actor_role, '') AS actor_role,
            COALESCE(entity_type, '') AS entity_type,
            COALESCE(entity_id, '') AS entity_id,
            COALESCE(action_type, '') AS action_type,
            COALESCE(summary, '') AS summary,
            COALESCE(details_json, '') AS details_json
        FROM audit_logs
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_audit_management_records(
    conn: psycopg.Connection,
    *,
    limit: int,
    action_type: str | None = None,
    entity_type: str | None = None,
    actor_name: str | None = None,
    search: str | None = None,
) -> list[dict]:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    rows = conn.execute(
        """
        SELECT
            id,
            created_at,
            COALESCE(actor_username, '') AS actor_username,
            COALESCE(actor_full_name, '') AS actor_full_name,
            COALESCE(actor_role, '') AS actor_role,
            COALESCE(entity_type, '') AS entity_type,
            COALESCE(entity_id, '') AS entity_id,
            COALESCE(action_type, '') AS action_type,
            COALESCE(summary, '') AS summary,
            COALESCE(details_json, '') AS details_json
        FROM audit_logs
        WHERE (%s IS NULL OR action_type = %s)
          AND (%s IS NULL OR entity_type = %s)
          AND (%s IS NULL OR actor_full_name = %s)
          AND (
            %s IS NULL
            OR COALESCE(summary, '') ILIKE %s
            OR COALESCE(details_json, '') ILIKE %s
            OR COALESCE(entity_id, '') ILIKE %s
            OR COALESCE(actor_full_name, '') ILIKE %s
            OR COALESCE(actor_username, '') ILIKE %s
          )
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (
            action_type,
            action_type,
            entity_type,
            entity_type,
            actor_name,
            actor_name,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ),
    ).fetchall()
    return [dict(row) for row in rows]


def count_audit_management_records(
    conn: psycopg.Connection,
    *,
    action_type: str | None = None,
    entity_type: str | None = None,
    actor_name: str | None = None,
    search: str | None = None,
) -> int:
    search_pattern = f"%{search.strip()}%" if search and search.strip() else None
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_count
        FROM audit_logs
        WHERE (%s IS NULL OR action_type = %s)
          AND (%s IS NULL OR entity_type = %s)
          AND (%s IS NULL OR actor_full_name = %s)
          AND (
            %s IS NULL
            OR COALESCE(summary, '') ILIKE %s
            OR COALESCE(details_json, '') ILIKE %s
            OR COALESCE(entity_id, '') ILIKE %s
            OR COALESCE(actor_full_name, '') ILIKE %s
            OR COALESCE(actor_username, '') ILIKE %s
          )
        """,
        (
            action_type,
            action_type,
            entity_type,
            entity_type,
            actor_name,
            actor_name,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    ).fetchone()
    return int(row["total_count"] or 0) if row else 0


def fetch_audit_filter_options(conn: psycopg.Connection) -> dict[str, list[str]]:
    action_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(action_type, '') AS value
        FROM audit_logs
        WHERE COALESCE(action_type, '') <> ''
        ORDER BY value
        """
    ).fetchall()
    entity_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(entity_type, '') AS value
        FROM audit_logs
        WHERE COALESCE(entity_type, '') <> ''
        ORDER BY value
        """
    ).fetchall()
    actor_rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(actor_full_name, '') AS value
        FROM audit_logs
        WHERE COALESCE(actor_full_name, '') <> ''
        ORDER BY value
        """
    ).fetchall()
    return {
        "action_options": [str(row["value"]) for row in action_rows],
        "entity_options": [str(row["value"]) for row in entity_rows],
        "actor_options": [str(row["value"]) for row in actor_rows],
    }
