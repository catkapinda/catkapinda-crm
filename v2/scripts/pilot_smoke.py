#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


DEFAULT_TIMEOUT = 12


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def normalize_base_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("Base URL bos olamaz.")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value.rstrip("/")


def fetch_json(base_url: str, path: str, timeout: int) -> tuple[int, dict]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        payload = json.loads(response.read().decode("utf-8"))
        return status, payload


def post_json(base_url: str, path: str, payload: dict, timeout: int, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        response_payload = json.loads(response.read().decode("utf-8"))
        return status, response_payload


def fetch_text(base_url: str, path: str, timeout: int) -> tuple[int, str, str]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        content_type = response.headers.get("Content-Type", "")
        payload = response.read().decode("utf-8", errors="replace")
        return status, content_type, payload


def run_smoke_checks(base_url: str, timeout: int, identity: str | None = None, password: str | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []

    try:
        status, payload = fetch_json(base_url, "/api/health", timeout)
        ok = status == 200 and payload.get("status") == "ok"
        results.append(
            CheckResult(
                name="frontend_health",
                ok=ok,
                detail=f"HTTP {status} • service={payload.get('service', '-')}",
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("frontend_health", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/api/ready", timeout)
        ok = status == 200 and bool(payload.get("proxyConfigured")) and bool(payload.get("backendReachable"))
        results.append(
            CheckResult(
                name="frontend_ready",
                ok=ok,
                detail=(
                    f"HTTP {status} • proxyConfigured={payload.get('proxyConfigured')} • "
                    f"backendReachable={payload.get('backendReachable')} • backendStatus={payload.get('backendStatus')}"
                ),
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("frontend_ready", False, str(exc)))

    try:
        status, content_type, _ = fetch_text(base_url, "/status", timeout)
        ok = status == 200 and "text/html" in content_type.lower()
        results.append(
            CheckResult(
                name="status_page",
                ok=ok,
                detail=f"HTTP {status} • content-type={content_type or '-'}",
            )
        )
    except urllib.error.URLError as exc:
        results.append(CheckResult("status_page", False, str(exc)))

    try:
        status, content_type, _ = fetch_text(base_url, "/login", timeout)
        ok = status == 200 and "text/html" in content_type.lower()
        results.append(
            CheckResult(
                name="login_page",
                ok=ok,
                detail=f"HTTP {status} • content-type={content_type or '-'}",
            )
        )
    except urllib.error.URLError as exc:
        results.append(CheckResult("login_page", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/v2-api/health", timeout)
        ok = status == 200 and payload.get("status") == "ok"
        results.append(
            CheckResult(
                name="backend_health",
                ok=ok,
                detail=f"HTTP {status} • service={payload.get('service', '-')}",
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_health", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/v2-api/health/ready", timeout)
        check_count = len(payload.get("checks", []))
        ok = status == 200 and payload.get("status") in {"ok", "degraded"} and check_count > 0
        results.append(
            CheckResult(
                name="backend_ready",
                ok=ok,
                detail=f"HTTP {status} • status={payload.get('status')} • checks={check_count}",
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_ready", False, str(exc)))

    try:
        status, payload = fetch_json(base_url, "/v2-api/health/pilot", timeout)
        module_count = len(payload.get("modules", []))
        auth = payload.get("auth", {})
        cutover = payload.get("cutover", {})
        required_missing_envs = payload.get("required_missing_env_vars", [])
        optional_missing_envs = payload.get("optional_missing_env_vars", [])
        modules_ready_count = int(cutover.get("modules_ready_count") or 0)
        ok = (
            status == 200
            and payload.get("status") in {"ok", "degraded"}
            and module_count >= 8
            and bool(auth.get("email_login"))
            and bool(auth.get("phone_login"))
            and len(required_missing_envs) == 0
            and cutover.get("phase") in {"ready_for_pilot", "ready_for_cutover"}
            and bool(cutover.get("ready"))
        )
        results.append(
            CheckResult(
                name="backend_pilot",
                ok=ok,
                detail=(
                    f"HTTP {status} • status={payload.get('status')} • "
                    f"phase={cutover.get('phase', '-')} • "
                    f"modules={modules_ready_count}/{module_count} • "
                    f"sms={auth.get('sms_login')} • "
                    f"required_missing={len(required_missing_envs)} • "
                    f"optional_missing={len(optional_missing_envs)}"
                ),
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_pilot", False, str(exc)))

    if identity and password:
        try:
            status, payload = post_json(
                base_url,
                "/v2-api/auth/login",
                {"identity": identity, "password": password},
                timeout,
            )
            token = str(payload.get("access_token") or "")
            login_ok = status == 200 and bool(token)
            results.append(
                CheckResult(
                    name="auth_login",
                    ok=login_ok,
                    detail=f"HTTP {status} • token={'var' if token else 'yok'} • must_change={payload.get('user', {}).get('must_change_password')}",
                )
            )
            if login_ok:
                me_status, me_payload = fetch_json_with_headers(
                    base_url,
                    "/v2-api/auth/me",
                    timeout,
                    headers={"Authorization": f"Bearer {token}"},
                )
                me_ok = me_status == 200 and bool(me_payload.get("email"))
                results.append(
                    CheckResult(
                        name="auth_me",
                        ok=me_ok,
                        detail=f"HTTP {me_status} • user={me_payload.get('email', '-')}",
                    )
                )
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            results.append(CheckResult("auth_login", False, str(exc)))

    return results


def fetch_json_with_headers(base_url: str, path: str, timeout: int, headers: dict[str, str]) -> tuple[int, dict]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", **headers})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        payload = json.loads(response.read().decode("utf-8"))
        return status, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run basic pilot smoke checks against a deployed v2 frontend URL.")
    parser.add_argument("--base-url", required=True, help="Public frontend URL, e.g. https://crmcatkapinda-v2.onrender.com")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds")
    parser.add_argument("--identity", default=os.getenv("CK_V2_SMOKE_IDENTITY", ""), help="Optional login identity for end-to-end auth smoke")
    parser.add_argument("--password", default=os.getenv("CK_V2_SMOKE_PASSWORD", ""), help="Optional login password for end-to-end auth smoke")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    identity = args.identity.strip() or None
    password = args.password.strip() or None
    results = run_smoke_checks(base_url, args.timeout, identity=identity, password=password)

    print(f"v2 pilot smoke • {base_url}")
    print("-" * 72)
    failed = False
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"{status:>4}  {result.name:<18}  {result.detail}")
        failed = failed or not result.ok

    print("-" * 72)
    if failed:
        print("Pilot smoke check failed.")
        return 1

    print("Pilot smoke check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
