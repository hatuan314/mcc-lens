"""Tests for OllamaLLMClient."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.repositories.ollama_llm_client import OllamaLLMClient


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __call__(self, host, timeout):  # used as Client(host=..., timeout=...)
        return self

    def chat(self, model, messages, options, format):
        return self._response


def test_chat_success():
    """Successful chat should return content."""
    fake = _FakeClient(
        {"message": {"content": '[{"mcc_code": "1234", "comment": "test"}]'}}
    )
    with patch("app.repositories.ollama_llm_client.Client", return_value=fake):
        client = OllamaLLMClient()
        result = client.chat("system prompt", "user prompt")
        assert '[{"mcc_code": "1234", "comment": "test"}]' in result


def test_chat_empty_response_raises():
    """Empty response should raise RuntimeError after retries."""
    fake = _FakeClient({"message": {"content": ""}})
    with patch("app.repositories.ollama_llm_client.Client", return_value=fake):
        client = OllamaLLMClient()
        with pytest.raises(RuntimeError, match="Failed to get LLM response"):
            client.chat("system", "user")


def test_chat_empty_prompts_raises():
    """Empty system or user prompt should raise ValueError."""
    fake = _FakeClient({"message": {"content": "ok"}})
    with patch("app.repositories.ollama_llm_client.Client", return_value=fake):
        client = OllamaLLMClient()
        with pytest.raises(ValueError, match="cannot be empty"):
            client.chat("", "user")
        with pytest.raises(ValueError, match="cannot be empty"):
            client.chat("system", "")


def test_chat_retry_on_failure():
    """Should retry on failure and eventually raise after max retries."""
    call_count = 0

    class _FailingClient:
        def __call__(self, host, timeout):
            return self

        def chat(self, model, messages, options, format):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Temporary error")

    with patch(
        "app.repositories.ollama_llm_client.Client", return_value=_FailingClient()
    ):
        client = OllamaLLMClient()
        with pytest.raises(RuntimeError, match="Failed to get LLM response"):
            client.chat("system", "user")
        assert call_count == 3  # max_retries


def test_chat_custom_timeout():
    """Custom timeout should be passed to Client."""
    fake = _FakeClient({"message": {"content": "ok"}})
    with patch("app.repositories.ollama_llm_client.Client", return_value=fake) as mock:
        client = OllamaLLMClient(timeout=300)
        client.chat("system", "user")
        mock.assert_called_once_with(host="http://localhost:11434", timeout=300)


def test_chat_options_passed():
    """Options should include temperature and num_ctx."""
    captured = {}

    class _CaptureClient:
        def __call__(self, host, timeout):
            return self

        def chat(self, model, messages, options, format):
            captured["options"] = options
            return {"message": {"content": "ok"}}

    with patch(
        "app.repositories.ollama_llm_client.Client", return_value=_CaptureClient()
    ):
        client = OllamaLLMClient()
        client.chat("system", "user", temperature=0.5)
        assert captured["options"]["temperature"] == 0.5
        assert captured["options"]["num_ctx"] == 8192


def test_chat_format_json():
    """format=json should be passed to chat call."""
    captured = {}

    class _CaptureClient:
        def __call__(self, host, timeout):
            return self

        def chat(self, model, messages, options, format):
            captured["format"] = format
            return {"message": {"content": "ok"}}

    with patch(
        "app.repositories.ollama_llm_client.Client", return_value=_CaptureClient()
    ):
        client = OllamaLLMClient()
        client.chat("system", "user")
        assert captured["format"] == "json"
