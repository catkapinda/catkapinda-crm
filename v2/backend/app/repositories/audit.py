from __future__ import annotations

from datetime import datetime, timedelta

import psycopg

from app.core.database import is_sqlite_backend


def _audit_text_sql(column: str) -> str:
    return f"COALESCE(CAST({column} AS TEXT), '')"


def _optional_text_equality_sql(column: str) -> str:
    return f"(%s::text IS NULL OR {_audit_text_sql(column)} = %s::text)"


def _optional_text_search_guard_sql() -> str:
    return "%s::text IS NULL"


def fetch_audit_summary(conn: psycopg.Connection) -> dict[str, int]:
    last_7_days_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat(timespec="seconds")
    if is_sqlite_backend(conn):
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS last_7_days,
                COUNT(DISTINCT COALESCE(NULLIF(actor_username, ''), actor_full_name, 'unknown')) AS unique_actors,
                COUNT(DISTINCT COALESCE(NULLIF(entity_type, ''), 'unknown')) AS unique_entities
            FROM audit_logs
            """,
            (last_7_days_cutoff,),
        ).fetchone()
    else:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_entries,
                COUNT(*) FILTER (
                    WHERE created_at >= %s
                ) AS last_7_days,
                COUNT(DISTINCT COALESCE(NULLIF({_audit_text_sql('actor_username')}, ''), {_audit_text_sql('actor_full_name')}, 'unknown')) AS unique_actors,
                COUNT(DISTINCT COALESCE(NULLIF({_audit_text_sql('entity_type')}, ''), 'unknown')) AS unique_entities
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
        f"""
        SELECT
            id,
            created_at,
            {_audit_text_sql('actor_username')} AS actor_username,
            {_audit_text_sql('actor_full_name')} AS actor_full_name,
            {_audit_text_sql('actor_role')} AS actor_role,
            {_audit_text_sql('entity_type')} AS entity_type,
            {_audit_text_sql('entity_id')} AS entity_id,
            {_audit_text_sql('action_type')} AS action_type,
            {_audit_text_sql('summary')} AS summary,
            {_audit_text_sql('details_json')} AS details_json
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
        f"""
        SELECT
            id,
            created_at,
            {_audit_text_sql('actor_username')} AS actor_username,
            {_audit_text_sql('actor_full_name')} AS actor_full_name,
            {_audit_text_sql('actor_role')} AS actor_role,
            {_audit_text_sql('entity_type')} AS entity_type,
            {_audit_text_sql('entity_id')} AS entity_id,
            {_audit_text_sql('action_type')} AS action_type,
            {_audit_text_sql('summary')} AS summary,
            {_audit_text_sql('details_json')} AS details_json
        FROM audit_logs
        WHERE {_optional_text_equality_sql('action_type')}
          AND {_optional_text_equality_sql('entity_type')}
          AND {_optional_text_equality_sql('actor_full_name')}
          AND (
            {_optional_text_search_guard_sql()}
            OR {_audit_text_sql('summary')} ILIKE %s
            OR {_audit_text_sql('details_json')} ILIKE %s
            OR {_audit_text_sql('entity_id')} ILIKE %s
            OR {_audit_text_sql('actor_full_name')} ILIKE %s
            OR {_audit_text_sql('actor_username')} ILIKE %s
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
        f"""
        SELECT COUNT(*) AS total_count
        FROM audit_logs
        WHERE {_optional_text_equality_sql('action_type')}
          AND {_optional_text_equality_sql('entity_type')}
          AND {_optional_text_equality_sql('actor_full_name')}
          AND (
            {_optional_text_search_guard_sql()}
            OR {_audit_text_sql('summary')} ILIKE %s
            OR {_audit_text_sql('details_json')} ILIKE %s
            OR {_audit_text_sql('entity_id')} ILIKE %s
            OR {_audit_text_sql('actor_full_name')} ILIKE %s
            OR {_audit_text_sql('actor_username')} ILIKE %s
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
        f"""
        SELECT DISTINCT {_audit_text_sql('action_type')} AS value
        FROM audit_logs
        WHERE {_audit_text_sql('action_type')} <> ''
        ORDER BY value
        """
    ).fetchall()
    entity_rows = conn.execute(
        f"""
        SELECT DISTINCT {_audit_text_sql('entity_type')} AS value
        FROM audit_logs
        WHERE {_audit_text_sql('entity_type')} <> ''
        ORDER BY value
        """
    ).fetchall()
    actor_rows = conn.execute(
        f"""
        SELECT DISTINCT {_audit_text_sql('actor_full_name')} AS value
        FROM audit_logs
        WHERE {_audit_text_sql('actor_full_name')} <> ''
        ORDER BY value
        """
    ).fetchall()
    return {
        "action_options": [str(row["value"]) for row in action_rows],
        "entity_options": [str(row["value"]) for row in entity_rows],
        "actor_options": [str(row["value"]) for row in actor_rows],
    }
