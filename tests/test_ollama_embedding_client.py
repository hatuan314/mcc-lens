"""Tests for OllamaEmbeddingClient."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.repositories.ollama_embedding_client import OllamaEmbeddingClient


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __call__(self, host, timeout):  # used as Client(host=..., timeout=...)
        return self

    def embed(self, model, input):
        return self._response


def test_embed_empty_list():
    """Empty input should return empty list."""
    fake = _FakeClient({"embeddings": []})
    with patch("app.repositories.ollama_embedding_client.Client", return_value=fake):
        client = OllamaEmbeddingClient()
        result = client.embed([])
        assert result == []


def test_embed_single_text():
    """Single text should return single embedding."""
    fake = _FakeClient({"embeddings": [[0.1, 0.2, 0.3]]})
    with patch("app.repositories.ollama_embedding_client.Client", return_value=fake):
        client = OllamaEmbeddingClient()
        result = client.embed(["test"])
        assert result == [[0.1, 0.2, 0.3]]


def test_embed_batch():
    """Batch should return list of embeddings."""
    fake = _FakeClient({"embeddings": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]})
    with patch("app.repositories.ollama_embedding_client.Client", return_value=fake):
        client = OllamaEmbeddingClient()
        result = client.embed(["a", "b", "c"])
        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]


def test_embed_mismatch_length_raises():
    """If Ollama returns wrong number of embeddings, should raise after retries."""
    fake = _FakeClient({"embeddings": [[0.1, 0.2]]})  # 1 instead of 3
    with patch("app.repositories.ollama_embedding_client.Client", return_value=fake):
        client = OllamaEmbeddingClient()
        with pytest.raises(RuntimeError, match="Failed to generate embeddings"):
            client.embed(["a", "b", "c"])


def test_embed_retry_on_failure():
    """Should retry on failure and eventually raise after max retries."""
    call_count = 0

    class _FailingClient:
        def __call__(self, host, timeout):
            return self

        def embed(self, model, input):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Temporary error")

    with patch(
        "app.repositories.ollama_embedding_client.Client", return_value=_FailingClient()
    ):
        client = OllamaEmbeddingClient()
        with pytest.raises(RuntimeError, match="Failed to generate embeddings"):
            client.embed(["test"])
        assert call_count == 3  # max_retries
