from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import subprocess
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BACKEND_DATABASE_KEYS = ("CK_V2_DATABASE_URL", "DATABASE_URL")
BACKEND_PASSWORD_KEYS = ("CK_V2_DEFAULT_AUTH_PASSWORD", "DEFAULT_AUTH_PASSWORD")
BACKEND_PHONE_KEYS = ("AUTH_EBRU_PHONE", "AUTH_MERT_PHONE", "AUTH_MUHAMMED_PHONE")
FRONTEND_PROXY_KEYS = ("CK_V2_INTERNAL_API_BASE_URL", "CK_V2_INTERNAL_API_HOSTPORT")
FRONTEND_PUBLIC_API_BASE = "/v2-api"
FRONTEND_SERVICE_NAME = "crmcatkapinda-v2"
CURRENT_APP_PHONE_SECRET_KEYS = {
    "AUTH_EBRU_PHONE": "ebru_phone",
    "AUTH_MERT_PHONE": "mert_phone",
    "AUTH_MUHAMMED_PHONE": "muhammed_phone",
}

LOCAL_FRONTEND_URL = "http://127.0.0.1:3000"
LOCAL_API_URL = "http://127.0.0.1:8000"
LOCAL_FRONTEND_CANDIDATE_PORTS = (3000, 3001, 3002)
LOCAL_V2_ROOT = Path(__file__).resolve().parents[3]


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


def load_toml_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _looks_like_placeholder(value: str) -> bool:
    cleaned = _strip_wrapping_quotes(value).strip()
    upper = cleaned.upper()
    return any(token in upper for token in ("PAROLA", "PROJE_REF", "XXXXXXXX", "<", "YOUR-", "NETGSM_API_SIFRESI"))


def _normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def _discover_current_app_sources(current_app_root: Path) -> list[dict[str, object]]:
    return [
        {
            "label": "workspace_streamlit_secrets",
            "path": str(current_app_root / ".streamlit" / "secrets.toml"),
            "kind": "streamlit_secrets",
        },
        {
            "label": "workspace_secrets_toml",
            "path": str(current_app_root / "secrets.toml"),
            "kind": "streamlit_secrets",
        },
        {
            "label": "workspace_secrets_template",
            "path": str(current_app_root / "secrets.template.toml"),
            "kind": "streamlit_secrets",
        },
        {
            "label": "home_streamlit_secrets",
            "path": str(Path.home() / ".streamlit" / "secrets.toml"),
            "kind": "streamlit_secrets",
        },
    ]


def discover_current_app_seed_values(current_app_root: Path) -> dict[str, object]:
    values: dict[str, str] = {}
    sources_used: list[str] = []
    placeholders_detected: list[str] = []
    available_sources: list[dict[str, object]] = []

    for source in _discover_current_app_sources(current_app_root):
        source_path = Path(str(source["path"]))
        exists = source_path.exists()
        source_entry = {**source, "exists": exists}
        available_sources.append(source_entry)
        if not exists:
            continue

        parsed = load_toml_file(source_path)
        if not parsed:
            continue

        raw_database_url = _strip_wrapping_quotes(str(parsed.get("DATABASE_URL", "")))
        if raw_database_url:
            if _looks_like_placeholder(raw_database_url):
                placeholders_detected.append(f"{source['label']}:DATABASE_URL")
            elif "database_url" not in values:
                values["database_url"] = raw_database_url
                sources_used.append(f"{source['label']}:DATABASE_URL")

        auth_mapping = parsed.get("auth")
        if isinstance(auth_mapping, dict):
            for env_key, secret_key in CURRENT_APP_PHONE_SECRET_KEYS.items():
                raw_phone = _strip_wrapping_quotes(str(auth_mapping.get(secret_key, "")))
                if not raw_phone:
                    continue
                normalized = _normalize_phone(raw_phone)
                if normalized:
                    values.setdefault(env_key, f"0{normalized}")
                    sources_used.append(f"{source['label']}:auth.{secret_key}")
                else:
                    placeholders_detected.append(f"{source['label']}:auth.{secret_key}")

    return {
        "values": values,
        "sources_used": sources_used,
        "placeholders_detected": placeholders_detected,
        "available_sources": available_sources,
    }


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


def _discover_frontend_ports_from_processes(
    ports: tuple[int, ...] = LOCAL_FRONTEND_CANDIDATE_PORTS,
) -> list[int]:
    discovered_ports: set[int] = set()
    for port in ports:
        try:
            lsof_result = subprocess.run(  # noqa: S603 - fixed local diagnostics command
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            continue

        for line in lsof_result.stdout.splitlines():
            lowered = line.lower()
            if "listen" in lowered and ("node" in lowered or "next" in lowered):
                discovered_ports.add(port)
                break

    return [port for port in ports if port in discovered_ports]


def discover_local_frontend_urls(ports: tuple[int, ...] = LOCAL_FRONTEND_CANDIDATE_PORTS) -> list[str]:
    detected_urls: list[str] = []

    for port in ports:
        base_url = f"http://127.0.0.1:{port}"
        request = Request(f"{base_url}/api/health", headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=0.35) as response:  # noqa: S310 - local doctor only probes localhost
                if response.status != 200:
                    continue
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
            continue

        if isinstance(payload, dict) and payload.get("status") == "ok":
            detected_urls.append(base_url)

    if detected_urls:
        return detected_urls

    process_ports = _discover_frontend_ports_from_processes(ports=ports)
    if process_ports:
        return [f"http://127.0.0.1:{port}" for port in process_ports]

    return detected_urls


def resolve_suggested_frontend_url(detected_frontend_urls: list[str] | None = None) -> str:
    if detected_frontend_urls:
        return detected_frontend_urls[0]
    return LOCAL_FRONTEND_URL


def _quote_shell_arg(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _build_local_doctor_command(
    *,
    frontend_url: str,
    api_url: str,
    bootstrap_local: bool = False,
    write_backend_env: bool = False,
    write_backend_scaffold: bool = False,
    write_frontend_env: bool = False,
    sync_from_current_app: bool = False,
    overwrite_backend_env: bool = False,
    overwrite_frontend_env: bool = False,
    include_database_placeholder: bool = False,
) -> str:
    command = ["python", "v2/scripts/local_v2_doctor.py"]

    if bootstrap_local:
        command.append("--bootstrap-local")
    if write_backend_env:
        command.append("--write-backend-env")
    if write_backend_scaffold:
        command.append("--write-backend-scaffold")
    if write_frontend_env:
        command.append("--write-frontend-env")
    if include_database_placeholder:
        command.extend(["--database-url", "'<postgresql://...>'"])

    command.extend(["--frontend-url", _quote_shell_arg(frontend_url)])
    command.extend(["--api-url", _quote_shell_arg(api_url)])

    if sync_from_current_app:
        command.append("--sync-from-current-app")
    if overwrite_backend_env:
        command.append("--overwrite-backend-env")
    if overwrite_frontend_env:
        command.append("--overwrite-frontend-env")

    return " ".join(command)


def render_frontend_env(
    *,
    api_url: str = LOCAL_API_URL,
    frontend_service_name: str = FRONTEND_SERVICE_NAME,
) -> str:
    lines = [
        f"NEXT_PUBLIC_V2_API_BASE_URL={FRONTEND_PUBLIC_API_BASE}",
        f"CK_V2_FRONTEND_SERVICE_NAME={frontend_service_name}",
        f"CK_V2_INTERNAL_API_BASE_URL={api_url}",
    ]
    return "\n".join(lines) + "\n"


def render_backend_env(
    runtime_env: Mapping[str, str],
    *,
    existing_env_values: Mapping[str, str] | None = None,
    current_app_seed_values: Mapping[str, str] | None = None,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> str:
    env_file_values = existing_env_values or {}
    database_url, _ = _resolve_value(runtime_env, env_file_values, BACKEND_DATABASE_KEYS)
    if not database_url and current_app_seed_values:
        database_url = _strip_wrapping_quotes(str(current_app_seed_values.get("database_url", "")))
    if not database_url:
        raise ValueError("CK_V2_DATABASE_URL veya DATABASE_URL shell env icinde bulunamadi.")

    password, _ = _resolve_value(runtime_env, env_file_values, BACKEND_PASSWORD_KEYS)
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
        if not value:
            value = _strip_wrapping_quotes(env_file_values.get(key, ""))
        if not value and current_app_seed_values:
            value = _strip_wrapping_quotes(str(current_app_seed_values.get(key, "")))
        if value:
            lines.append(f"{key}={value}")

    return "\n".join(lines) + "\n"


def render_backend_env_scaffold(
    runtime_env: Mapping[str, str],
    *,
    existing_env_values: Mapping[str, str] | None = None,
    current_app_seed_values: Mapping[str, str] | None = None,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> str:
    env_file_values = existing_env_values or {}
    password, _ = _resolve_value(runtime_env, env_file_values, BACKEND_PASSWORD_KEYS)
    lines = [
        "CK_V2_APP_ENV=development",
        "# TODO: gercek PostgreSQL degerini yapistir",
        "# CK_V2_DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require",
        f"CK_V2_FRONTEND_BASE_URL={frontend_url}",
        f"CK_V2_PUBLIC_APP_URL={frontend_url}",
        f"CK_V2_API_PUBLIC_URL={api_url}",
        f"CK_V2_DEFAULT_AUTH_PASSWORD={password or '123456'}",
    ]

    for key in BACKEND_PHONE_KEYS:
        value = _strip_wrapping_quotes(runtime_env.get(key, ""))
        if not value:
            value = _strip_wrapping_quotes(env_file_values.get(key, ""))
        if not value and current_app_seed_values:
            value = _strip_wrapping_quotes(str(current_app_seed_values.get(key, "")))
        if value:
            lines.append(f"{key}={value}")

    return "\n".join(lines) + "\n"


def write_backend_env_file(
    v2_root: Path,
    runtime_env: Mapping[str, str],
    *,
    overwrite: bool = False,
    current_app_seed_values: Mapping[str, str] | None = None,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> Path:
    backend_env_path = v2_root / "backend" / ".env"
    existing_env_values = load_env_file(backend_env_path)
    if backend_env_path.exists() and not overwrite:
        raise FileExistsError(f"{backend_env_path} zaten var. Ezmek icin --overwrite-backend-env kullan.")

    backend_env_path.write_text(
        render_backend_env(
            runtime_env,
            existing_env_values=existing_env_values,
            current_app_seed_values=current_app_seed_values,
            frontend_url=frontend_url,
            api_url=api_url,
        ),
        encoding="utf-8",
    )
    return backend_env_path


def write_backend_env_scaffold_file(
    v2_root: Path,
    runtime_env: Mapping[str, str],
    *,
    overwrite: bool = False,
    current_app_seed_values: Mapping[str, str] | None = None,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> Path:
    backend_env_path = v2_root / "backend" / ".env"
    existing_env_values = load_env_file(backend_env_path)
    if backend_env_path.exists() and not overwrite:
        raise FileExistsError(f"{backend_env_path} zaten var. Ezmek icin --overwrite-backend-env kullan.")

    backend_env_path.write_text(
        render_backend_env_scaffold(
            runtime_env,
            existing_env_values=existing_env_values,
            current_app_seed_values=current_app_seed_values,
            frontend_url=frontend_url,
            api_url=api_url,
        ),
        encoding="utf-8",
    )
    return backend_env_path


def write_frontend_env_file(
    v2_root: Path,
    *,
    overwrite: bool = False,
    api_url: str = LOCAL_API_URL,
    frontend_service_name: str = FRONTEND_SERVICE_NAME,
) -> Path:
    frontend_env_path = v2_root / "frontend" / ".env.local"
    if frontend_env_path.exists() and not overwrite:
        raise FileExistsError(f"{frontend_env_path} zaten var. Ezmek icin --overwrite-frontend-env kullan.")

    frontend_env_path.write_text(
        render_frontend_env(
            api_url=api_url,
            frontend_service_name=frontend_service_name,
        ),
        encoding="utf-8",
    )
    return frontend_env_path


def bootstrap_local_setup_files(
    v2_root: Path,
    runtime_env: Mapping[str, str],
    *,
    current_app_seed_values: Mapping[str, str] | None = None,
    overwrite_backend_env: bool = False,
    overwrite_frontend_env: bool = False,
    frontend_url: str = LOCAL_FRONTEND_URL,
    api_url: str = LOCAL_API_URL,
) -> list[Path]:
    written_paths: list[Path] = []
    existing_backend_env_values = load_env_file(v2_root / "backend" / ".env")

    frontend_path = write_frontend_env_file(
        v2_root,
        overwrite=overwrite_frontend_env,
        api_url=api_url,
    )
    written_paths.append(frontend_path)

    backend_env_path = v2_root / "backend" / ".env"
    database_url, _ = _resolve_value(runtime_env, existing_backend_env_values, BACKEND_DATABASE_KEYS)
    if not database_url and current_app_seed_values:
        database_url = _strip_wrapping_quotes(str(current_app_seed_values.get("database_url", "")))

    if database_url:
        backend_path = write_backend_env_file(
            v2_root,
            runtime_env,
            overwrite=overwrite_backend_env,
            current_app_seed_values=current_app_seed_values,
            frontend_url=frontend_url,
            api_url=api_url,
        )
        written_paths.append(backend_path)
    elif not backend_env_path.exists():
        backend_path = write_backend_env_scaffold_file(
            v2_root,
            runtime_env,
            overwrite=overwrite_backend_env,
            current_app_seed_values=current_app_seed_values,
            frontend_url=frontend_url,
            api_url=api_url,
        )
        written_paths.append(backend_path)

    return written_paths


def build_local_doctor_report(
    v2_root: Path,
    runtime_env: Mapping[str, str],
    *,
    runtime_is_backend_process: bool = False,
) -> dict[str, object]:
    current_app_root = v2_root.parent
    backend_env_path = v2_root / "backend" / ".env"
    frontend_env_path = v2_root / "frontend" / ".env.local"

    backend_env_values = load_env_file(backend_env_path)
    frontend_env_values = load_env_file(frontend_env_path)
    current_app_seed = discover_current_app_seed_values(current_app_root)
    current_app_values = current_app_seed["values"]
    detected_frontend_urls = discover_local_frontend_urls()
    suggested_frontend_url = resolve_suggested_frontend_url(detected_frontend_urls)
    suggested_api_url = LOCAL_API_URL
    bootstrap_can_overwrite_backend = backend_env_path.exists() and bool(current_app_values.get("database_url"))
    suggested_bootstrap_command = _build_local_doctor_command(
        frontend_url=suggested_frontend_url,
        api_url=suggested_api_url,
        bootstrap_local=True,
        sync_from_current_app=bool(current_app_values),
        overwrite_backend_env=bootstrap_can_overwrite_backend,
        overwrite_frontend_env=frontend_env_path.exists(),
    )
    suggested_bootstrap_with_db_command = _build_local_doctor_command(
        frontend_url=suggested_frontend_url,
        api_url=suggested_api_url,
        bootstrap_local=True,
        overwrite_backend_env=backend_env_path.exists(),
        overwrite_frontend_env=frontend_env_path.exists(),
        include_database_placeholder=True,
    )
    suggested_scaffold_command = _build_local_doctor_command(
        frontend_url=suggested_frontend_url,
        api_url=suggested_api_url,
        write_backend_scaffold=True,
        sync_from_current_app=True,
        overwrite_backend_env=backend_env_path.exists(),
    )
    suggested_frontend_env_command = _build_local_doctor_command(
        frontend_url=suggested_frontend_url,
        api_url=suggested_api_url,
        write_frontend_env=True,
        overwrite_frontend_env=frontend_env_path.exists(),
    )
    suggested_env_write_command = _build_local_doctor_command(
        frontend_url=suggested_frontend_url,
        api_url=suggested_api_url,
        write_backend_env=True,
        overwrite_backend_env=backend_env_path.exists(),
        include_database_placeholder=True,
    )
    suggested_current_app_env_command = _build_local_doctor_command(
        frontend_url=suggested_frontend_url,
        api_url=suggested_api_url,
        write_backend_env=True,
        sync_from_current_app=True,
        overwrite_backend_env=backend_env_path.exists(),
    )
    suggested_backend_start_command = "cd v2/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

    runtime_database_url, runtime_database_source = _resolve_value(runtime_env, {}, BACKEND_DATABASE_KEYS)
    backend_env_database_url, backend_env_database_source = _resolve_value({}, backend_env_values, BACKEND_DATABASE_KEYS)
    database_url, database_source = _resolve_value(runtime_env, backend_env_values, BACKEND_DATABASE_KEYS)
    if not database_url and current_app_values.get("database_url"):
        database_url = _strip_wrapping_quotes(str(current_app_values["database_url"]))
        database_source = "current_app_seed:DATABASE_URL"
    default_password, password_source = _resolve_value(runtime_env, backend_env_values, BACKEND_PASSWORD_KEYS)
    proxy_target_raw, proxy_source = _resolve_value(runtime_env, frontend_env_values, FRONTEND_PROXY_KEYS)
    proxy_target = _normalize_proxy_target(proxy_target_raw)
    frontend_env_needs_sync = (not frontend_env_path.exists()) or (
        bool(proxy_target) and proxy_source == "file:CK_V2_INTERNAL_API_BASE_URL" and proxy_target != suggested_api_url
    )

    missing_phone_keys = [
        key
        for key in BACKEND_PHONE_KEYS
        if not _strip_wrapping_quotes(runtime_env.get(key, ""))
        and not _strip_wrapping_quotes(backend_env_values.get(key, ""))
        and not _strip_wrapping_quotes(str(current_app_values.get(key, "")))
    ]

    warnings: list[str] = []
    blocking_items: list[str] = []
    next_actions: list[str] = []
    backend_restart_required = runtime_is_backend_process and bool(backend_env_database_url) and (
        not runtime_database_url or backend_env_database_url != runtime_database_url
    )
    backend_restart_reason: str | None = None

    if backend_restart_required:
        if not runtime_database_url:
            backend_restart_reason = "backend/.env icinde DATABASE_URL var ama calisan backend sureci bu env ile baslamamis."
        else:
            backend_restart_reason = "backend/.env icindeki DATABASE_URL ile calisan backend surecinin DATABASE_URL degeri farkli."
        blocking_items.append("Backend .env guncel, fakat calisan backend sureci yeniden baslatilmali.")
        warnings.append(backend_restart_reason)
        next_actions.append(f"Backend'i guncellemek icin `{suggested_backend_start_command}` komutunu yeniden calistir.")

    if not database_url:
        blocking_items.append("Backend veritabani URL'i eksik. CK_V2_DATABASE_URL veya DATABASE_URL tanimlanmali.")
        if not backend_env_path.exists():
            next_actions.append(
                f"Ilk adim olarak `{suggested_bootstrap_command}` ile local env dosyalarini hazirla."
            )
        next_actions.append(
            f"Gercek PostgreSQL URL'ini alip `{suggested_bootstrap_with_db_command}` calistir."
        )
    elif database_source == "current_app_seed:DATABASE_URL" and not backend_env_path.exists():
        warnings.append("Veritabani URL'i current app kaynaklarinda bulundu ama v2 backend/.env henuz yazilmadi.")
        next_actions.append(
            f"Current app kaynaklarini kullanarak backend/.env yazmak icin `{suggested_current_app_env_command}` calistir."
        )

    if not proxy_target:
        blocking_items.append("Frontend proxy hedefi eksik. CK_V2_INTERNAL_API_BASE_URL veya CK_V2_INTERNAL_API_HOSTPORT bulunamadi.")
        next_actions.append(f"Frontend .env.local icin `{suggested_frontend_env_command}` kullan.")
    elif frontend_env_needs_sync:
        blocking_items.append("Frontend .env.local icindeki backend hedefi mevcut local API onerisiyle hizali degil.")
        next_actions.append(f"Frontend env'i guncellemek icin `{suggested_frontend_env_command}` kullan.")

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
        next_actions.append(f"Kalici local kurulum icin `{suggested_current_app_env_command if current_app_seed['values'] else _build_local_doctor_command(frontend_url=suggested_frontend_url, api_url=suggested_api_url, write_backend_env=True)}` kullan.")

    if not frontend_env_path.exists():
        warnings.append("frontend/.env.local bulunamadi.")
        next_actions.append(f"frontend/.env.local olusturmak icin `{suggested_frontend_env_command}` kullan.")

    if len(detected_frontend_urls) > 1:
        warnings.append("Birden fazla local frontend oturumu gorunuyor; port karmasasi olusabilir.")
        next_actions.append("Eski `next dev` sureclerini kapatip tek aktif frontend URL birak.")

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
        "runtime_database_url_present": bool(runtime_database_url),
        "runtime_database_url_source": runtime_database_source or None,
        "backend_env_database_url_present": bool(backend_env_database_url),
        "backend_env_database_url_source": backend_env_database_source or None,
        "backend_restart_required": backend_restart_required,
        "backend_restart_reason": backend_restart_reason,
        "default_auth_password_present": bool(default_password),
        "default_auth_password_source": password_source or None,
        "default_auth_password_is_default": default_password == "123456",
        "frontend_proxy_target_present": bool(proxy_target),
        "frontend_proxy_target": proxy_target or None,
        "frontend_proxy_source": proxy_source or None,
        "frontend_env_needs_sync": frontend_env_needs_sync,
        "detected_frontend_urls": detected_frontend_urls,
        "suggested_frontend_url": suggested_frontend_url,
        "suggested_api_url": suggested_api_url,
        "suggested_bootstrap_command": suggested_bootstrap_command,
        "suggested_bootstrap_with_db_command": suggested_bootstrap_with_db_command,
        "suggested_frontend_env_command": suggested_frontend_env_command,
        "suggested_scaffold_command": suggested_scaffold_command,
        "suggested_env_write_command": suggested_env_write_command,
        "suggested_current_app_env_command": suggested_current_app_env_command,
        "suggested_backend_start_command": suggested_backend_start_command,
        "current_app_seed_detected": bool(current_app_values),
        "current_app_seed_sources": current_app_seed["sources_used"],
        "current_app_seed_placeholders": current_app_seed["placeholders_detected"],
        "current_app_available_sources": current_app_seed["available_sources"],
        "missing_phone_keys": missing_phone_keys,
        "blocking_items": blocking_items,
        "warnings": warnings,
        "next_actions": next_actions,
    }
