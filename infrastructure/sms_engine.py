from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

import streamlit as st


SMS_PROVIDER_GENERIC_JSON = "generic_json"


def get_sms_config() -> dict[str, Any] | None:
    sms_secrets: dict[str, Any] = {}
    try:
        if hasattr(st, "secrets") and "sms" in st.secrets:
            raw_sms = st.secrets["sms"]
            if hasattr(raw_sms, "items"):
                sms_secrets = dict(raw_sms.items())
    except Exception:
        sms_secrets = {}

    provider = str(sms_secrets.get("provider", "") or os.getenv("SMS_PROVIDER", "") or "").strip().lower()
    api_url = str(sms_secrets.get("api_url", "") or os.getenv("SMS_API_URL", "") or "").strip()
    if not provider or not api_url:
        return None

    timeout_value = sms_secrets.get("timeout_seconds", os.getenv("SMS_TIMEOUT_SECONDS", "20"))
    try:
        timeout_seconds = int(timeout_value or 20)
    except Exception:
        timeout_seconds = 20

    return {
        "provider": provider,
        "api_url": api_url,
        "api_token": str(sms_secrets.get("api_token", "") or os.getenv("SMS_API_TOKEN", "") or ""),
        "auth_header": str(sms_secrets.get("auth_header", "") or os.getenv("SMS_AUTH_HEADER", "Authorization") or "Authorization").strip(),
        "token_prefix": str(sms_secrets.get("token_prefix", "") or os.getenv("SMS_TOKEN_PREFIX", "Bearer") or "Bearer").strip(),
        "sender": str(sms_secrets.get("sender", "") or os.getenv("SMS_SENDER", "CatKapinda") or "CatKapinda").strip(),
        "message_template": str(
            sms_secrets.get("message_template", "")
            or os.getenv(
                "SMS_MESSAGE_TEMPLATE",
                "Merhaba {full_name}, Cat Kapinda CRM giris kodunuz: {code}. Kod {minutes} dakika gecerlidir.",
            )
            or ""
        ).strip(),
        "timeout_seconds": timeout_seconds,
    }


def sms_delivery_enabled() -> bool:
    return get_sms_config() is not None


def send_phone_login_code_sms(phone: str, full_name: str, code: str, *, expires_in_minutes: int) -> None:
    sms_config = get_sms_config()
    if not sms_config:
        raise RuntimeError("SMS ile giriş kodu gönderimi için SMS ayarları henüz tanımlı değil.")

    if sms_config["provider"] != SMS_PROVIDER_GENERIC_JSON:
        raise RuntimeError("Tanımlı SMS sağlayıcısı bu sürümde desteklenmiyor.")

    message = sms_config["message_template"].format(
        full_name=(full_name or "ekip arkadasi").strip() or "ekip arkadasi",
        code=str(code or "").strip(),
        minutes=int(expires_in_minutes or 0),
    )
    payload = {
        "to": str(phone or "").strip(),
        "sender": sms_config["sender"],
        "message": message,
        "channel": "sms",
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    if sms_config["api_token"]:
        auth_value = sms_config["api_token"]
        if sms_config["token_prefix"]:
            auth_value = f"{sms_config['token_prefix']} {auth_value}"
        headers[sms_config["auth_header"]] = auth_value

    req = request.Request(
        sms_config["api_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=int(sms_config["timeout_seconds"])) as response:
            status_code = int(getattr(response, "status", 0) or 0)
            if status_code < 200 or status_code >= 300:
                raise RuntimeError("SMS sağlayıcısı giriş kodunu kabul etmedi.")
    except error.HTTPError as exc:
        raise RuntimeError("SMS sağlayıcısı giriş kodunu gönderemedi.") from exc
    except error.URLError as exc:
        raise RuntimeError("SMS sağlayıcısına ulaşılamadı.") from exc
    except Exception as exc:
        raise RuntimeError("SMS ile giriş kodu gönderilemedi.") from exc
