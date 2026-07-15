"""Focused tests for OpenAI-compatible and DeepSeek model connections."""

import unittest
from types import SimpleNamespace

from app.services.model_gateway import (
    build_payload,
    completion_url,
    upstream_error_message,
    validate_model_config,
)


class ModelGatewayTests(unittest.TestCase):
    def test_deepseek_completion_url(self):
        self.assertEqual(
            completion_url("https://api.deepseek.com"),
            "https://api.deepseek.com/chat/completions",
        )
        self.assertEqual(
            completion_url("https://api.deepseek.com/v1/"),
            "https://api.deepseek.com/v1/chat/completions",
        )

    def test_stream_payload_avoids_optional_stream_options(self):
        payload = build_payload(
            {
                "model_name": "deepseek-chat",
                "context_count": 10,
                "temperature": 0.7,
                "top_p": 1,
                "max_tokens": 2048,
            },
            [{"role": "user", "content": "你好"}],
            stream=True,
        )
        self.assertTrue(payload["stream"])
        self.assertNotIn("stream_options", payload)

    def test_deepseek_requires_real_api_key(self):
        model = {"base_url": "https://api.deepseek.com", "api_key": ""}
        with self.assertRaisesRegex(ValueError, "需要 API Key"):
            validate_model_config(model)

        model["api_key"] = "https://api.deepseek.com"
        with self.assertRaisesRegex(ValueError, "不能填写 URL"):
            validate_model_config(model)

        model["api_key"] = "sk-valid-format-for-test"
        validate_model_config(model)

    def test_upstream_auth_error_is_actionable(self):
        error = SimpleNamespace(
            code=401,
            response=SimpleNamespace(
                body=b'{"error":{"message":"Authentication Fails"}}'
            ),
        )
        message = upstream_error_message(error)
        self.assertIn("鉴权失败", message)
        self.assertIn("HTTP 401", message)
        self.assertIn("Authentication Fails", message)


if __name__ == "__main__":
    unittest.main()
