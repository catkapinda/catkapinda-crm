from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import streamlit as st


def build_audit_actor_payload() -> dict[str, str]:
    return {
        "actor_username": str(st.session_state.get("username") or "sistem"),
        "actor_full_name": str(st.session_state.get("user_full_name") or "Sistem"),
        "actor_role": str(st.session_state.get("role") or ""),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def serialize_audit_details(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    return json.dumps(details, ensure_ascii=False, default=str, sort_keys=True)
