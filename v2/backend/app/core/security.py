from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import re
import secrets

from app.core.config import settings

PASSWORD_HASH_ITERATIONS = 200_000
MOBILE_AUTH_EMAIL_DOMAIN = "auth.catkapinda.local"

ROLE_ACTIONS = {
    "admin": {
        "dashboard.view",
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "attendance.delete",
        "attendance.bulk_delete",
        "audit.view",
        "deduction.view",
        "deduction.create",
        "deduction.update",
        "deduction.delete",
        "equipment.view",
        "equipment.create",
        "equipment.bulk_update",
        "equipment.bulk_delete",
        "equipment.box_return",
        "payroll.view",
        "personnel.view",
        "personnel.list",
        "personnel.create",
        "personnel.update",
        "personnel.status_change",
        "personnel.delete",
        "purchase.view",
        "purchase.create",
        "purchase.update",
        "purchase.delete",
        "restaurant.view",
        "restaurant.create",
        "restaurant.update",
        "restaurant.status_change",
        "restaurant.delete",
        "reporting.view",
        "sales.view",
        "sales.create",
        "sales.update",
        "sales.delete",
    },
    "sef": {
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "attendance.delete",
        "attendance.bulk_delete",
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


def mask_auth_phone(value: str) -> str:
    normalized_phone = normalize_auth_phone(value)
    if not normalized_phone:
        return str(value or "").strip()
    return f"0{normalized_phone[:3]} *** ** {normalized_phone[-2:]}"


def normalize_auth_identity(value: str) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return ""
    if "@" in raw_value:
        return raw_value.lower()
    normalized_phone = normalize_auth_phone(raw_value)
    return normalized_phone or raw_value.lower()


def build_mobile_auth_email(personnel_id: int) -> str:
    return f"mobile.personnel.{int(personnel_id)}@{MOBILE_AUTH_EMAIL_DOMAIN}"


def is_mobile_auth_email(email: str) -> bool:
    normalized_email = normalize_auth_identity(email)
    return normalized_email.startswith("mobile.personnel.") and normalized_email.endswith(
        f"@{MOBILE_AUTH_EMAIL_DOMAIN}"
    )


def extract_mobile_auth_personnel_id(email: str) -> int:
    normalized_email = normalize_auth_identity(email)
    match = re.fullmatch(
        rf"mobile\.personnel\.(\d+)@{re.escape(MOBILE_AUTH_EMAIL_DOMAIN)}",
        normalized_email,
    )
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


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


def generate_phone_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def build_session_window() -> tuple[str, str]:
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=settings.auth_session_days or 30)
    return (
        created_at.isoformat(timespec="seconds"),
        expires_at.isoformat(timespec="seconds"),
    )


def resolve_allowed_actions(role: str) -> list[str]:
    return sorted(ROLE_ACTIONS.get(str(role or "").strip(), set()))
