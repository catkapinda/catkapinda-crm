from __future__ import annotations

import base64
import hashlib
import hmac
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
    return (value or "").strip().lower()


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
    return conn.execute(
        "SELECT * FROM auth_users WHERE lower(email) = lower(?) LIMIT 1",
        (normalized_identity,),
    ).fetchone()


def build_login_logo_markup() -> str:
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }
    app_dir = Path(__file__).resolve().parent

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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_authenticated_user(user_row: Any, token: str | None = None) -> None:
    if not user_row:
        return
    st.session_state.authenticated = True
    st.session_state.username = str(_GET_ROW_VALUE(user_row, "email", "") or "")
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
    ]:
        st.session_state.pop(key, None)


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
                    email, full_name, role, role_display, password_hash,
                    is_active, must_change_password, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalize_auth_identity(user["email"]),
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
            SET email = ?, full_name = ?, role = ?, role_display = ?, password_hash = ?,
                is_active = 1, must_change_password = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalize_auth_identity(user["email"]),
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
