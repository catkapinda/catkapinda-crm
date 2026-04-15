from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg

from app.core.security import AuthenticatedUser


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if isinstance(response, dict):
        return response
    return {}


def safe_record_audit_event(
    conn: psycopg.Connection,
    *,
    user: AuthenticatedUser | None,
    entity_type: str,
    action_type: str,
    summary: str,
    entity_id: Any = None,
    details: dict[str, Any] | None = None,
) -> bool:
    try:
        conn.execute(
            """
            INSERT INTO audit_logs (
                created_at,
                actor_username,
                actor_full_name,
                actor_role,
                entity_type,
                entity_id,
                action_type,
                summary,
                details_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                datetime.utcnow().isoformat(timespec="seconds"),
                getattr(user, "identity", "") if user else "",
                getattr(user, "full_name", "") if user else "",
                getattr(user, "role_display", "") if user else "",
                str(entity_type or ""),
                "" if entity_id is None else str(entity_id),
                str(action_type or ""),
                str(summary or ""),
                json.dumps(details or {}, ensure_ascii=False, default=_json_default),
            ),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
