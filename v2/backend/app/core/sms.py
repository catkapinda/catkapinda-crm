from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib import error, request


SMS_PROVIDER_GENERIC_JSON = "generic_json"
SMS_PROVIDER_NETGSM = "netgsm"


def get_sms_config() -> dict[str, Any] | None:
    provider = str(os.getenv("SMS_PROVIDER", "") or "").strip().lower()
    api_url = str(os.getenv("SMS_API_URL", "") or "").strip()
    if provider == SMS_PROVIDER_NETGSM and not api_url:
        api_url = "https://api.netgsm.com.tr/sms/rest/v2/send"
    if not provider or not api_url:
        return None

    timeout_text = str(os.getenv("SMS_TIMEOUT_SECONDS", "20") or "20")
    try:
        timeout_seconds = int(timeout_text)
    except Exception:
        timeout_seconds = 20

    config: dict[str, Any] = {
        "provider": provider,
        "api_url": api_url,
        "api_token": str(os.getenv("SMS_API_TOKEN", "") or ""),
        "auth_header": str(os.getenv("SMS_AUTH_HEADER", "Authorization") or "Authorization").strip(),
        "token_prefix": str(os.getenv("SMS_TOKEN_PREFIX", "Bearer") or "Bearer").strip(),
        "sender": str(os.getenv("SMS_SENDER", "CatKapinda") or "CatKapinda").strip(),
        "message_template": str(
            os.getenv(
                "SMS_MESSAGE_TEMPLATE",
                "Merhaba {full_name}, Cat Kapinda CRM giris kodunuz: {code}. Kod {minutes} dakika gecerlidir.",
            )
            or ""
        ).strip(),
        "timeout_seconds": timeout_seconds,
    }

    if provider == SMS_PROVIDER_NETGSM:
        config["username"] = str(os.getenv("SMS_NETGSM_USERNAME", "") or "").strip()
        config["password"] = str(os.getenv("SMS_NETGSM_PASSWORD", "") or "").strip()
        config["encoding"] = str(os.getenv("SMS_NETGSM_ENCODING", "TR") or "TR").strip() or "TR"
        config["iysfilter"] = str(os.getenv("SMS_NETGSM_IYSFILTER", "") or "").strip()
        config["partnercode"] = str(os.getenv("SMS_NETGSM_PARTNERCODE", "") or "").strip()
        if not config["username"] or not config["password"]:
            return None

    return config


def sms_delivery_enabled() -> bool:
    return get_sms_config() is not None


def send_phone_login_code_sms(phone: str, full_name: str, code: str, *, expires_in_minutes: int) -> None:
    sms_config = get_sms_config()
    if not sms_config:
        raise RuntimeError("SMS ile giriş kodu gönderimi için SMS ayarları henüz tanımlı değil.")

    message = sms_config["message_template"].format(
        full_name=(full_name or "ekip arkadasi").strip() or "ekip arkadasi",
        code=str(code or "").strip(),
        minutes=int(expires_in_minutes or 0),
    )

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    payload: dict[str, Any]

    if sms_config["provider"] == SMS_PROVIDER_GENERIC_JSON:
        payload = {
            "to": str(phone or "").strip(),
            "sender": sms_config["sender"],
            "message": message,
            "channel": "sms",
        }
        if sms_config["api_token"]:
            auth_value = sms_config["api_token"]
            if sms_config["token_prefix"]:
                auth_value = f"{sms_config['token_prefix']} {auth_value}"
            headers[sms_config["auth_header"]] = auth_value
    elif sms_config["provider"] == SMS_PROVIDER_NETGSM:
        basic_value = base64.b64encode(
            f"{sms_config['username']}:{sms_config['password']}".encode("utf-8")
        ).decode("ascii")
        headers["Authorization"] = f"Basic {basic_value}"
        payload = {
            "msgheader": sms_config["sender"],
            "messages": [
                {
                    "msg": message,
                    "no": str(phone or "").strip(),
                }
            ],
            "encoding": sms_config["encoding"],
            "iysfilter": sms_config["iysfilter"],
            "partnercode": sms_config["partnercode"],
        }
    else:
        raise RuntimeError("Tanımlı SMS sağlayıcısı bu sürümde desteklenmiyor.")

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
