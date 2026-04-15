from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

BACKEND_DATABASE_KEYS = ("CK_V2_DATABASE_URL", "DATABASE_URL")
BACKEND_PASSWORD_KEYS = ("CK_V2_DEFAULT_AUTH_PASSWORD", "DEFAULT_AUTH_PASSWORD")
BACKEND_PHONE_KEYS = ("AUTH_EBRU_PHONE", "AUTH_MERT_PHONE", "AUTH_MUHAMMED_PHONE")
FRONTEND_PROXY_KEYS = ("CK_V2_INTERNAL_API_BASE_URL", "CK_V2_INTERNAL_API_HOSTPORT")

LOCAL_FRONTEND_URL = "http://127.0.0.1:3000"
LOCAL_API_URL = "http://127.0.0.1:8000"


def _strip_wrapping_quotes(value: str) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        return cleaned[1:-1]
    return cleaned


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = _strip_wrapping_quotes(raw_value)
    return values


def _resolve_value(
    runtime_env: Mapping[str, str],
    env_file_values: Mapping[str, str],
    keys: tuple[str, ...],
) -> tuple[str, str]:
    for key in keys:
        value = _strip_wrapping_quotes(runtime_env.get(key, ""))
        if value:
            return value, f"shell:{key}"
    for key in keys:
        value = _strip_wrapping_quotes(env_file_values.get(key, ""))
        if value:
            return value, f"file:{key}"
    return "", ""


def _normalize_proxy_target(raw_target: str) -> str:
    target = _strip_wrapping_quotes(raw_target)
    if not target:
        return ""
    if target.startswith("http://") or target.startswith("https://"):
        return target.rstrip("/")
    return f"http://{target.rstrip('/')}"


def render_backend_env(
    runtime_env: Mapping[str, str],
    *,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> str:
    database_url, _ = _resolve_value(runtime_env, {}, BACKEND_DATABASE_KEYS)
    if not database_url:
        raise ValueError("CK_V2_DATABASE_URL veya DATABASE_URL shell env icinde bulunamadi.")

    password, _ = _resolve_value(runtime_env, {}, BACKEND_PASSWORD_KEYS)
    lines = [
        "CK_V2_APP_ENV=development",
        f"CK_V2_DATABASE_URL={database_url}",
        f"CK_V2_FRONTEND_BASE_URL={frontend_url}",
        f"CK_V2_PUBLIC_APP_URL={frontend_url}",
        f"CK_V2_API_PUBLIC_URL={api_url}",
        f"CK_V2_DEFAULT_AUTH_PASSWORD={password or '123456'}",
    ]

    for key in BACKEND_PHONE_KEYS:
        value = _strip_wrapping_quotes(runtime_env.get(key, ""))
        if value:
            lines.append(f"{key}={value}")

    return "\n".join(lines) + "\n"


def write_backend_env_file(
    v2_root: Path,
    runtime_env: Mapping[str, str],
    *,
    overwrite: bool = False,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> Path:
    backend_env_path = v2_root / "backend" / ".env"
    if backend_env_path.exists() and not overwrite:
        raise FileExistsError(f"{backend_env_path} zaten var. Ezmek icin --overwrite-backend-env kullan.")

    backend_env_path.write_text(
        render_backend_env(runtime_env, frontend_url=frontend_url, api_url=api_url),
        encoding="utf-8",
    )
    return backend_env_path


def build_local_doctor_report(
    v2_root: Path,
    runtime_env: Mapping[str, str],
) -> dict[str, object]:
    backend_env_path = v2_root / "backend" / ".env"
    frontend_env_path = v2_root / "frontend" / ".env.local"

    backend_env_values = load_env_file(backend_env_path)
    frontend_env_values = load_env_file(frontend_env_path)

    database_url, database_source = _resolve_value(runtime_env, backend_env_values, BACKEND_DATABASE_KEYS)
    default_password, password_source = _resolve_value(runtime_env, backend_env_values, BACKEND_PASSWORD_KEYS)
    proxy_target_raw, proxy_source = _resolve_value(runtime_env, frontend_env_values, FRONTEND_PROXY_KEYS)
    proxy_target = _normalize_proxy_target(proxy_target_raw)

    missing_phone_keys = [
        key
        for key in BACKEND_PHONE_KEYS
        if not _strip_wrapping_quotes(runtime_env.get(key, "")) and not _strip_wrapping_quotes(backend_env_values.get(key, ""))
    ]

    warnings: list[str] = []
    blocking_items: list[str] = []
    next_actions: list[str] = []

    if not database_url:
        blocking_items.append("Backend veritabani URL'i eksik. CK_V2_DATABASE_URL veya DATABASE_URL tanimlanmali.")
        next_actions.append(
            "Mevcut PostgreSQL URL'ini shell env'e koyup `python v2/scripts/local_v2_doctor.py --write-backend-env` calistir."
        )

    if not proxy_target:
        blocking_items.append("Frontend proxy hedefi eksik. CK_V2_INTERNAL_API_BASE_URL veya CK_V2_INTERNAL_API_HOSTPORT bulunamadi.")
        next_actions.append("frontend/.env.local icinde CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000 kullan.")

    if default_password == "123456":
        warnings.append("CK_V2_DEFAULT_AUTH_PASSWORD hala varsayilan degerde.")
        next_actions.append("Gercek login denemesi oncesi CK_V2_DEFAULT_AUTH_PASSWORD icin guclu bir deger belirle.")
    elif not default_password:
        warnings.append("CK_V2_DEFAULT_AUTH_PASSWORD shell veya backend/.env icinde acikca tanimli degil; backend varsayilan 123456 ile acilir.")
        next_actions.append("Giris testleri icin CK_V2_DEFAULT_AUTH_PASSWORD degerini backend/.env icine yaz.")

    if missing_phone_keys:
        warnings.append(
            "Telefon/SMS allowlist eksik. SMS login ve sifre kurtarma icin tum yonetici telefonlari yok."
        )
        next_actions.append("SMS login gerekiyorsa AUTH_EBRU_PHONE / AUTH_MERT_PHONE / AUTH_MUHAMMED_PHONE alanlarini doldur.")

    if not backend_env_path.exists() and database_url:
        warnings.append("Backend .env dosyasi henuz yok; shell env kaybolursa local backend yeniden kurulum ister.")
        next_actions.append("Kalici local kurulum icin `python v2/scripts/local_v2_doctor.py --write-backend-env` kullan.")

    if not frontend_env_path.exists():
        warnings.append("frontend/.env.local bulunamadi.")
        next_actions.append("frontend/.env.example dosyasini .env.local olarak kopyalayip proxy hedefini koru.")

    if not next_actions:
        next_actions.append("Local v2 omurgasi hazir. Backend'i 8000'de, frontend'i 3000/3001'de ayaga kaldirip login akisini test et.")

    return {
        "ready": not blocking_items,
        "backend_env_path": str(backend_env_path),
        "frontend_env_path": str(frontend_env_path),
        "backend_env_exists": backend_env_path.exists(),
        "frontend_env_exists": frontend_env_path.exists(),
        "database_url_present": bool(database_url),
        "database_url_source": database_source or None,
        "default_auth_password_present": bool(default_password),
        "default_auth_password_source": password_source or None,
        "default_auth_password_is_default": default_password == "123456",
        "frontend_proxy_target_present": bool(proxy_target),
        "frontend_proxy_target": proxy_target or None,
        "frontend_proxy_source": proxy_source or None,
        "missing_phone_keys": missing_phone_keys,
        "blocking_items": blocking_items,
        "warnings": warnings,
        "next_actions": next_actions,
    }
