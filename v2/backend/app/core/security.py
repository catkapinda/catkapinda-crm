from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import re
import secrets

from app.core.config import settings

PASSWORD_HASH_ITERATIONS = 200_000

ROLE_ACTIONS = {
    "admin": {
        "dashboard.view",
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "attendance.delete",
        "deduction.view",
        "deduction.create",
        "deduction.update",
        "deduction.delete",
        "equipment.view",
        "equipment.create",
        "equipment.bulk_update",
        "equipment.bulk_delete",
        "equipment.box_return",
        "personnel.view",
        "personnel.list",
        "personnel.create",
        "personnel.update",
        "restaurant.view",
        "restaurant.create",
        "restaurant.update",
        "restaurant.status_change",
        "restaurant.delete",
    },
    "sef": {
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "attendance.delete",
        "deduction.view",
        "deduction.create",
        "deduction.update",
        "deduction.delete",
        "personnel.view",
        "personnel.list",
        "personnel.create",
        "personnel.update",
    },
    "mobile_ops": {
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "personnel.view",
        "personnel.create",
    },
}


@dataclass(slots=True)
class AuthenticatedUser:
    id: int
    identity: str
    email: str
    phone: str
    full_name: str
    role: str
    role_display: str
    must_change_password: bool
    allowed_actions: list[str]
    expires_at: str
    token: str


def normalize_auth_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def normalize_auth_identity(value: str) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return ""
    if "@" in raw_value:
        return raw_value.lower()
    normalized_phone = normalize_auth_phone(raw_value)
    return normalized_phone or raw_value.lower()


def verify_auth_password(password: str, stored_hash: str) -> bool:
    parts = str(stored_hash or "").split("$", 3)
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return hmac.compare_digest(str(stored_hash or ""), str(password or ""))
    _, iterations_text, salt, digest = parts
    try:
        iterations = int(iterations_text)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def hash_auth_password(password: str, *, salt: str | None = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        resolved_salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${resolved_salt}${digest}"


def build_session_token() -> str:
    return secrets.token_urlsafe(32)


def build_session_window() -> tuple[str, str]:
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=settings.auth_session_days or 30)
    return (
        created_at.isoformat(timespec="seconds"),
        expires_at.isoformat(timespec="seconds"),
    )


def resolve_allowed_actions(role: str) -> list[str]:
    return sorted(ROLE_ACTIONS.get(str(role or "").strip(), set()))
