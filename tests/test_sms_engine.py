from __future__ import annotations

import base64
import json
import os
from unittest import TestCase
from unittest.mock import patch

from infrastructure.sms_engine import get_sms_config, send_phone_login_code_sms, sms_delivery_enabled


class _FakeResponse:
    def __init__(self, status: int = 200) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class SmsEngineTests(TestCase):
    def test_sms_delivery_enabled_for_netgsm_env_config(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SMS_PROVIDER": "netgsm",
                "SMS_API_URL": "https://api.netgsm.com.tr/sms/rest/v2/send",
                "SMS_NETGSM_USERNAME": "8508409717",
                "SMS_NETGSM_PASSWORD": "secret",
                "SMS_SENDER": "CATKAPINDA",
            },
            clear=True,
        ):
            config = get_sms_config()
            self.assertIsNotNone(config)
            self.assertTrue(sms_delivery_enabled())
            self.assertEqual(config["provider"], "netgsm")
            self.assertEqual(config["sender"], "CATKAPINDA")

    def test_send_phone_login_code_sms_builds_netgsm_request(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout: int = 0):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _FakeResponse(200)

        with patch.dict(
            os.environ,
            {
                "SMS_PROVIDER": "netgsm",
                "SMS_API_URL": "https://api.netgsm.com.tr/sms/rest/v2/send",
                "SMS_NETGSM_USERNAME": "8508409717",
                "SMS_NETGSM_PASSWORD": "secret",
                "SMS_SENDER": "CATKAPINDA",
            },
            clear=True,
        ), patch("infrastructure.sms_engine.request.urlopen", side_effect=fake_urlopen):
            send_phone_login_code_sms("5321234567", "Cihan", "123456", expires_in_minutes=10)

        auth_header = captured["headers"]["Authorization"]
        expected_basic = base64.b64encode(b"8508409717:secret").decode("ascii")
        self.assertEqual(auth_header, f"Basic {expected_basic}")
        self.assertEqual(captured["url"], "https://api.netgsm.com.tr/sms/rest/v2/send")
        self.assertEqual(captured["body"]["msgheader"], "CATKAPINDA")
        self.assertEqual(captured["body"]["messages"][0]["no"], "5321234567")
        self.assertIn("123456", captured["body"]["messages"][0]["msg"])
