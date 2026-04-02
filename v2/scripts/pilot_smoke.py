#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def fetch_text(base_url: str, path: str, timeout: int) -> tuple[int, str, str]:
    url = urllib.parse.urljoin(f"{base_url}/", path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.getcode()
        content_type = response.headers.get("Content-Type", "")
        payload = response.read().decode("utf-8", errors="replace")
        return status, content_type, payload


def run_smoke_checks(base_url: str, timeout: int) -> list[CheckResult]:
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
        missing_envs = payload.get("missing_env_vars", [])
        ok = (
            status == 200
            and payload.get("status") in {"ok", "degraded"}
            and module_count >= 8
            and bool(auth.get("email_login"))
            and bool(auth.get("phone_login"))
            and len(missing_envs) == 0
        )
        results.append(
            CheckResult(
                name="backend_pilot",
                ok=ok,
                detail=(
                    f"HTTP {status} • status={payload.get('status')} • "
                    f"modules={module_count} • sms={auth.get('sms_login')} • "
                    f"missing_envs={len(missing_envs)}"
                ),
            )
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(CheckResult("backend_pilot", False, str(exc)))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run basic pilot smoke checks against a deployed v2 frontend URL.")
    parser.add_argument("--base-url", required=True, help="Public frontend URL, e.g. https://crmcatkapinda-v2.onrender.com")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    results = run_smoke_checks(base_url, args.timeout)

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
