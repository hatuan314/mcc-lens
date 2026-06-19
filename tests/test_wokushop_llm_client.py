"""Tests for WokuShopLLMClient."""

import time
from unittest.mock import MagicMock, patch
import pytest
from app.repositories.wokushop_llm_client import WokuShopLLMClient


def test_chat_success():
    """Successful chat should return content."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '[{"mcc_code": "1234", "comment": "test"}]'
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client):
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        result = client.chat("system prompt", "user prompt")
        assert '[{"mcc_code": "1234", "comment": "test"}]' in result
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )


def test_chat_empty_response_raises():
    """Empty response should raise RuntimeError after retries."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client):
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        with pytest.raises(RuntimeError, match="Failed to get LLM response"):
            client.chat("system", "user")


def test_chat_empty_prompts_raises():
    """Empty system or user prompt should raise ValueError."""
    mock_client = MagicMock()
    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client):
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        with pytest.raises(ValueError, match="cannot be empty"):
            client.chat("", "user")
        with pytest.raises(ValueError, match="cannot be empty"):
            client.chat("system", "")


def test_chat_none_content_raises():
    """None content should be coerced to empty and raise RuntimeError after retries."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client), \
         patch("time.sleep"):
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        with pytest.raises(RuntimeError, match="Failed to get LLM response"):
            client.chat("system", "user")
        assert mock_client.chat.completions.create.call_count == 3


def test_chat_retry_then_success():
    """Should retry on failure and eventually succeed if an attempt succeeds."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "success content"
    
    # Lần 1, 2 fail, lần 3 success
    mock_client.chat.completions.create.side_effect = [
        Exception("API Error"),
        Exception("API Error"),
        mock_response
    ]

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client), \
         patch("time.sleep") as mock_sleep:
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        result = client.chat("system", "user")
        assert result == "success content"
        assert mock_client.chat.completions.create.call_count == 3
        # backoff wait times: 2**0 = 1s, 2**1 = 2s
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)


def test_chat_all_retries_fail():
    """Should retry 3 times and raise RuntimeError if all fail."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client), \
         patch("time.sleep") as mock_sleep:
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        with pytest.raises(RuntimeError, match="Failed to get LLM response"):
            client.chat("system", "user")
        assert mock_client.chat.completions.create.call_count == 3


def test_health_check_success():
    """health_check should return True when models.list() succeeds."""
    mock_client = MagicMock()
    mock_client.models.list.return_value = MagicMock()

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client):
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        assert client.health_check() is True
        mock_client.models.list.assert_called_once()


def test_health_check_failure():
    """health_check should return False when models.list() raises an exception."""
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("Connection error")

    with patch("app.repositories.wokushop_llm_client.OpenAI", return_value=mock_client):
        client = WokuShopLLMClient(api_key="test-key", base_url="https://llm.wokushop.com/v1", model="gpt-4o")
        assert client.health_check() is False
        mock_client.models.list.assert_called_once()
