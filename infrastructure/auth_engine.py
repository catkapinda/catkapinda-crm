from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import streamlit as st


_GET_ROW_VALUE: Callable[[Any, str, Any], Any] | None = None
_SAFE_INT: Callable[[Any, int], int] | None = None
_DEFAULT_AUTH_USERS: list[dict[str, Any]] = []
_DEFAULT_AUTH_PASSWORD = ""
_LEGACY_AUTH_IDENTITIES: set[str] = set()
_PASSWORD_HASH_ITERATIONS = 200_000
_LOGIN_LOGO_CANDIDATES: list[str] = []
_AUTH_QUERY_KEY = ""
_AUTH_SESSION_DAYS = 30
_MOBILE_AUTH_PERSONNEL_ROLES: tuple[str, ...] = ("Joker", "Bölge Müdürü")
_MOBILE_AUTH_EMAIL_DOMAIN = "auth.catkapinda.local"
_SMS_PHONE_AUTH_PERSONNEL_ROLES: tuple[str, ...] = ("Bölge Müdürü",)
PHONE_LOGIN_CODE_MINUTES = 10
_PHONE_LOGIN_CODE_ATTEMPT_LIMIT = 5


def configure_auth_engine(
    *,
    get_row_value_fn: Callable[[Any, str, Any], Any],
    safe_int_fn: Callable[[Any, int], int],
    default_auth_users: list[dict[str, Any]],
    default_auth_password: str,
    legacy_auth_identities: set[str],
    password_hash_iterations: int,
    login_logo_candidates: list[str],
    auth_query_key: str,
    auth_session_days: int,
) -> None:
    global _GET_ROW_VALUE
    global _SAFE_INT
    global _DEFAULT_AUTH_USERS
    global _DEFAULT_AUTH_PASSWORD
    global _LEGACY_AUTH_IDENTITIES
    global _PASSWORD_HASH_ITERATIONS
    global _LOGIN_LOGO_CANDIDATES
    global _AUTH_QUERY_KEY
    global _AUTH_SESSION_DAYS

    _GET_ROW_VALUE = get_row_value_fn
    _SAFE_INT = safe_int_fn
    _DEFAULT_AUTH_USERS = list(default_auth_users)
    _DEFAULT_AUTH_PASSWORD = str(default_auth_password or "")
    _LEGACY_AUTH_IDENTITIES = set(legacy_auth_identities)
    _PASSWORD_HASH_ITERATIONS = int(password_hash_iterations or 200_000)
    _LOGIN_LOGO_CANDIDATES = list(login_logo_candidates)
    _AUTH_QUERY_KEY = str(auth_query_key or "")
    _AUTH_SESSION_DAYS = int(auth_session_days or 30)


def normalize_auth_identity(value: str) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return ""
    if "@" in raw_value:
        return raw_value.lower()
    normalized_phone = normalize_auth_phone(raw_value)
    return normalized_phone or raw_value.lower()


def normalize_auth_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def build_mobile_auth_email(personnel_id: int) -> str:
    return f"mobile.personnel.{int(personnel_id)}@{_MOBILE_AUTH_EMAIL_DOMAIN}"


def is_mobile_auth_email(email: str) -> bool:
    normalized_email = normalize_auth_identity(email)
    return normalized_email.startswith("mobile.personnel.") and normalized_email.endswith(f"@{_MOBILE_AUTH_EMAIL_DOMAIN}")


def extract_mobile_auth_personnel_id(email: str) -> int:
    normalized_email = normalize_auth_identity(email)
    match = re.fullmatch(rf"mobile\.personnel\.(\d+)@{re.escape(_MOBILE_AUTH_EMAIL_DOMAIN)}", normalized_email)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


def can_email_temporary_password_for_user(user_row: Any) -> bool:
    email_value = str(_GET_ROW_VALUE(user_row, "email", "") or "")
    return bool(email_value and not is_mobile_auth_email(email_value))


def can_phone_login_for_user(user_row: Any) -> bool:
    return bool(normalize_auth_phone(str(_GET_ROW_VALUE(user_row, "phone", "") or "")))


def can_issue_phone_login_code(conn: Any, user_row: Any) -> bool:
    if not can_phone_login_for_user(user_row):
        return False
    email_value = str(_GET_ROW_VALUE(user_row, "email", "") or "")
    if not is_mobile_auth_email(email_value):
        return False
    personnel_id = extract_mobile_auth_personnel_id(email_value)
    if personnel_id <= 0:
        return False
    personnel_row = conn.execute(
        """
        SELECT role, status
        FROM personnel
        WHERE id = ?
        LIMIT 1
        """,
        (personnel_id,),
    ).fetchone()
    if not personnel_row:
        return False
    personnel_role = str(_GET_ROW_VALUE(personnel_row, "role", "") or "").strip()
    personnel_status = str(_GET_ROW_VALUE(personnel_row, "status", "") or "").strip()
    return personnel_status == "Aktif" and personnel_role in _SMS_PHONE_AUTH_PERSONNEL_ROLES


def mask_auth_phone(value: str) -> str:
    normalized_phone = normalize_auth_phone(value)
    if not normalized_phone:
        return str(value or "").strip()
    return f"0{normalized_phone[:3]} *** ** {normalized_phone[-2:]}"


def hash_auth_password(password: str, salt: str | None = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        resolved_salt.encode("utf-8"),
        _PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${_PASSWORD_HASH_ITERATIONS}${resolved_salt}${digest}"


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


def get_auth_user(conn: Any, identity: str) -> Any:
    normalized_identity = normalize_auth_identity(identity)
    if not normalized_identity:
        return None
    try:
        return conn.execute(
            """
            SELECT *
            FROM auth_users
            WHERE lower(COALESCE(email, '')) = lower(?)
               OR COALESCE(phone, '') = ?
            LIMIT 1
            """,
            (normalized_identity, normalized_identity),
        ).fetchone()
    except Exception as exc:
        # Older live databases may not have the phone column yet; allow bootstrap
        # and auth sync to continue using email-only lookup until schema is healed.
        if "phone" not in str(exc).lower():
            raise
        return conn.execute(
            """
            SELECT *
            FROM auth_users
            WHERE lower(COALESCE(email, '')) = lower(?)
            LIMIT 1
            """,
            (normalized_identity,),
        ).fetchone()


def build_login_logo_markup() -> str:
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }
    app_dir = Path(__file__).resolve().parent.parent

    for candidate in _LOGIN_LOGO_CANDIDATES:
        logo_path = app_dir / candidate
        if not logo_path.exists() or not logo_path.is_file():
            continue
        try:
            encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        except OSError:
            continue
        mime_type = mime_map.get(logo_path.suffix.lower(), "image/png")
        return (
            '<div class="ck-login-logo-mark ck-login-logo-mark-image">'
            f'<img src="data:{mime_type};base64,{encoded}" alt="Çat Kapında Logo" class="ck-login-logo-image" />'
            "</div>"
        )

    return '<div class="ck-login-logo-mark">CK</div>'


def init_auth_state() -> None:
    defaults = {
        "authenticated": False,
        "username": None,
        "role": None,
        "auth_token": None,
        "user_full_name": None,
        "user_role_display": None,
        "must_change_password": False,
        "login_help_visible": False,
        "login_transition_active": False,
        "pending_phone_code_identity": None,
        "pending_phone_code_masked": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_authenticated_user(user_row: Any, token: str | None = None) -> None:
    if not user_row:
        return
    phone_identity = normalize_auth_phone(str(_GET_ROW_VALUE(user_row, "phone", "") or ""))
    email_identity = str(_GET_ROW_VALUE(user_row, "email", "") or "")
    st.session_state.authenticated = True
    st.session_state.username = phone_identity or email_identity
    st.session_state.role = str(_GET_ROW_VALUE(user_row, "role", "") or "")
    st.session_state.auth_token = token
    st.session_state.user_full_name = str(_GET_ROW_VALUE(user_row, "full_name", "") or "")
    st.session_state.user_role_display = str(_GET_ROW_VALUE(user_row, "role_display", "") or "")
    st.session_state.must_change_password = bool(_SAFE_INT(_GET_ROW_VALUE(user_row, "must_change_password", 0), 0))


def clear_authenticated_user() -> None:
    for key in [
        "authenticated",
        "username",
        "role",
        "auth_token",
        "user_full_name",
        "user_role_display",
        "must_change_password",
        "login_transition_active",
        "pending_phone_code_identity",
        "pending_phone_code_masked",
    ]:
        st.session_state.pop(key, None)


def cleanup_auth_phone_codes(conn: Any) -> None:
    now_text = datetime.utcnow().isoformat(timespec="seconds")
    stale_consumed_before = (datetime.utcnow() - timedelta(days=1)).isoformat(timespec="seconds")
    conn.execute(
        """
        DELETE FROM auth_phone_codes
        WHERE expires_at <= ?
           OR (consumed_at IS NOT NULL AND consumed_at <= ?)
        """,
        (now_text, stale_consumed_before),
    )
    conn.commit()


def generate_phone_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def issue_phone_login_code(conn: Any, user_row: Any, *, purpose: str = "login") -> str:
    cleanup_auth_phone_codes(conn)
    auth_user_id = int(_GET_ROW_VALUE(user_row, "id", 0) or 0)
    phone_value = normalize_auth_phone(str(_GET_ROW_VALUE(user_row, "phone", "") or ""))
    if auth_user_id <= 0 or not phone_value:
        raise RuntimeError("Bu hesap için kullanılabilir bir telefon numarası bulunamadı.")

    now_text = datetime.utcnow().isoformat(timespec="seconds")
    expires_at = (datetime.utcnow() + timedelta(minutes=PHONE_LOGIN_CODE_MINUTES)).isoformat(timespec="seconds")
    login_code = generate_phone_login_code()
    conn.execute(
        """
        DELETE FROM auth_phone_codes
        WHERE auth_user_id = ?
          AND purpose = ?
          AND consumed_at IS NULL
        """,
        (auth_user_id, purpose),
    )
    conn.execute(
        """
        INSERT INTO auth_phone_codes (
            auth_user_id, phone, code_hash, purpose, created_at, expires_at, consumed_at, attempt_count, last_attempt_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, NULL)
        """,
        (
            auth_user_id,
            phone_value,
            hash_auth_password(login_code),
            purpose,
            now_text,
            expires_at,
        ),
    )
    return login_code


def verify_phone_login_code(conn: Any, phone: str, login_code: str, *, purpose: str = "login") -> Any:
    normalized_phone = normalize_auth_phone(phone)
    if not normalized_phone or not str(login_code or "").strip():
        return None

    cleanup_auth_phone_codes(conn)
    row = conn.execute(
        """
        SELECT
            c.id AS code_row_id,
            c.auth_user_id AS code_auth_user_id,
            c.code_hash AS code_hash,
            c.attempt_count AS code_attempt_count,
            u.*
        FROM auth_phone_codes c
        JOIN auth_users u ON u.id = c.auth_user_id
        WHERE c.phone = ?
          AND c.purpose = ?
          AND c.consumed_at IS NULL
          AND c.expires_at > ?
        ORDER BY c.created_at DESC, c.id DESC
        LIMIT 1
        """,
        (normalized_phone, purpose, datetime.utcnow().isoformat(timespec="seconds")),
    ).fetchone()
    if not row:
        return None

    code_row_id = int(_GET_ROW_VALUE(row, "code_row_id", 0) or 0)
    attempt_count = _SAFE_INT(_GET_ROW_VALUE(row, "code_attempt_count", 0), 0)
    if attempt_count >= _PHONE_LOGIN_CODE_ATTEMPT_LIMIT:
        return None

    if not verify_auth_password(str(login_code or "").strip(), str(_GET_ROW_VALUE(row, "code_hash", "") or "")):
        conn.execute(
            """
            UPDATE auth_phone_codes
            SET attempt_count = ?, last_attempt_at = ?
            WHERE id = ?
            """,
            (
                attempt_count + 1,
                datetime.utcnow().isoformat(timespec="seconds"),
                code_row_id,
            ),
        )
        conn.commit()
        return None

    conn.execute(
        """
        UPDATE auth_phone_codes
        SET consumed_at = ?, last_attempt_at = ?, attempt_count = ?
        WHERE id = ?
        """,
        (
            datetime.utcnow().isoformat(timespec="seconds"),
            datetime.utcnow().isoformat(timespec="seconds"),
            attempt_count + 1,
            code_row_id,
        ),
    )
    conn.commit()
    return row


def get_query_param(name: str) -> str | None:
    if hasattr(st, "query_params"):
        value = st.query_params.get(name)
    else:
        value = st.experimental_get_query_params().get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def set_query_param(name: str, value: str | None) -> None:
    if hasattr(st, "query_params"):
        if value is None:
            try:
                del st.query_params[name]
            except Exception:
                pass
        else:
            st.query_params[name] = value
        return

    params = st.experimental_get_query_params()
    if value is None:
        params.pop(name, None)
    else:
        params[name] = value
    st.experimental_set_query_params(**params)


def cleanup_auth_sessions(conn: Any) -> None:
    conn.execute(
        "DELETE FROM auth_sessions WHERE expires_at <= ?",
        (datetime.utcnow().isoformat(timespec="seconds"),),
    )
    conn.commit()


def sync_default_auth_users(conn: Any) -> None:
    now_text = datetime.utcnow().isoformat(timespec="seconds")

    for legacy_identity in _LEGACY_AUTH_IDENTITIES:
        conn.execute("DELETE FROM auth_users WHERE lower(email) = lower(?)", (legacy_identity,))
        conn.execute("DELETE FROM auth_sessions WHERE username = ?", (legacy_identity,))

    for user in _DEFAULT_AUTH_USERS:
        existing = get_auth_user(conn, user["email"])
        if existing is None:
            conn.execute(
                """
                INSERT INTO auth_users (
                    email, phone, full_name, role, role_display, password_hash,
                    is_active, must_change_password, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalize_auth_identity(user["email"]),
                    normalize_auth_phone(str(user.get("phone", "") or "")),
                    user["full_name"],
                    user["role"],
                    user["role_display"],
                    hash_auth_password(_DEFAULT_AUTH_PASSWORD),
                    1,
                    1,
                    now_text,
                    now_text,
                ),
            )
            continue

        password_hash = str(_GET_ROW_VALUE(existing, "password_hash", "") or "")
        must_change_password = _SAFE_INT(_GET_ROW_VALUE(existing, "must_change_password", 0), 0)
        if not password_hash:
            password_hash = hash_auth_password(_DEFAULT_AUTH_PASSWORD)
            must_change_password = 1
        conn.execute(
            """
            UPDATE auth_users
            SET email = ?, phone = ?, full_name = ?, role = ?, role_display = ?, password_hash = ?,
                is_active = 1, must_change_password = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalize_auth_identity(user["email"]),
                normalize_auth_phone(str(user.get("phone", "") or "")),
                user["full_name"],
                user["role"],
                user["role_display"],
                password_hash,
                must_change_password,
                now_text,
                int(_GET_ROW_VALUE(existing, "id", 0) or 0),
            ),
        )

    conn.commit()


def sync_mobile_auth_users(conn: Any) -> None:
    now_text = datetime.utcnow().isoformat(timespec="seconds")
    placeholder_emails: set[str] = set()
    mobile_email_pattern = f"mobile.personnel.%@{_MOBILE_AUTH_EMAIL_DOMAIN}".lower()
    existing_mobile_users = conn.execute(
        """
        SELECT id, email, phone
        FROM auth_users
        WHERE role = 'mobile_ops'
          AND lower(COALESCE(email, '')) LIKE ?
        """,
        (mobile_email_pattern,),
    ).fetchall()

    personnel_rows = conn.execute(
        f"""
        SELECT id, full_name, role, phone, status
        FROM personnel
        WHERE status = 'Aktif'
          AND role IN ({", ".join(["?"] * len(_MOBILE_AUTH_PERSONNEL_ROLES))})
        ORDER BY full_name
        """,
        _MOBILE_AUTH_PERSONNEL_ROLES,
    ).fetchall()

    for row in personnel_rows:
        personnel_id = int(_GET_ROW_VALUE(row, "id", 0) or 0)
        normalized_phone = normalize_auth_phone(str(_GET_ROW_VALUE(row, "phone", "") or ""))
        if personnel_id <= 0 or not normalized_phone:
            continue
        placeholder_email = build_mobile_auth_email(personnel_id)
        placeholder_emails.add(placeholder_email)
        existing = conn.execute(
            """
            SELECT *
            FROM auth_users
            WHERE lower(COALESCE(email, '')) = lower(?)
               OR COALESCE(phone, '') = ?
            LIMIT 1
            """,
            (placeholder_email, normalized_phone),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO auth_users (
                    email, phone, full_name, role, role_display, password_hash,
                    is_active, must_change_password, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    placeholder_email,
                    normalized_phone,
                    str(_GET_ROW_VALUE(row, "full_name", "") or ""),
                    "mobile_ops",
                    "Mobil Operasyon",
                    hash_auth_password(_DEFAULT_AUTH_PASSWORD),
                    1,
                    1,
                    now_text,
                    now_text,
                ),
            )
            continue

        password_hash = str(_GET_ROW_VALUE(existing, "password_hash", "") or "")
        must_change_password = _SAFE_INT(_GET_ROW_VALUE(existing, "must_change_password", 0), 0)
        if not password_hash:
            password_hash = hash_auth_password(_DEFAULT_AUTH_PASSWORD)
            must_change_password = 1
        old_phone = normalize_auth_phone(str(_GET_ROW_VALUE(existing, "phone", "") or ""))
        conn.execute(
            """
            UPDATE auth_users
            SET email = ?, phone = ?, full_name = ?, role = 'mobile_ops', role_display = ?,
                password_hash = ?, is_active = 1, must_change_password = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                placeholder_email,
                normalized_phone,
                str(_GET_ROW_VALUE(row, "full_name", "") or ""),
                "Mobil Operasyon",
                password_hash,
                must_change_password,
                now_text,
                int(_GET_ROW_VALUE(existing, "id", 0) or 0),
            ),
        )
        if old_phone and old_phone != normalized_phone:
            conn.execute("DELETE FROM auth_sessions WHERE username = ?", (old_phone,))

    for row in existing_mobile_users:
        auth_user_id = int(_GET_ROW_VALUE(row, "id", 0) or 0)
        auth_email = str(_GET_ROW_VALUE(row, "email", "") or "")
        auth_phone = normalize_auth_phone(str(_GET_ROW_VALUE(row, "phone", "") or ""))
        if not auth_email or auth_email in placeholder_emails:
            continue
        conn.execute(
            """
            UPDATE auth_users
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (now_text, auth_user_id),
        )
        conn.execute("DELETE FROM auth_sessions WHERE username = ?", (auth_email,))
        if auth_phone:
            conn.execute("DELETE FROM auth_sessions WHERE username = ?", (auth_phone,))

    conn.commit()


def create_auth_session(conn: Any, username: str) -> str:
    cleanup_auth_sessions(conn)
    token = secrets.token_urlsafe(32)
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=_AUTH_SESSION_DAYS)
    conn.execute(
        "INSERT INTO auth_sessions (token, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (
            token,
            username,
            created_at.isoformat(timespec="seconds"),
            expires_at.isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return token


def restore_auth_session(conn: Any) -> bool:
    if st.session_state.get("authenticated"):
        return True

    cleanup_auth_sessions(conn)
    token = get_query_param(_AUTH_QUERY_KEY)
    if not token:
        return False

    row = conn.execute(
        "SELECT username, expires_at FROM auth_sessions WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        set_query_param(_AUTH_QUERY_KEY, None)
        return False

    auth_user = get_auth_user(conn, str(row["username"] or ""))
    if not auth_user or _SAFE_INT(_GET_ROW_VALUE(auth_user, "is_active", 0), 0) != 1:
        conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
        conn.commit()
        set_query_param(_AUTH_QUERY_KEY, None)
        return False

    set_authenticated_user(auth_user, token)
    return True


def revoke_current_auth_session(conn: Any) -> None:
    token = st.session_state.get("auth_token") or get_query_param(_AUTH_QUERY_KEY)
    if token:
        conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
        conn.commit()
    set_query_param(_AUTH_QUERY_KEY, None)
    clear_authenticated_user()
