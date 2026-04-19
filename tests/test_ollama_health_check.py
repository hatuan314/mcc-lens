"""Tests for ollama_health_check."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.ollama_health_check import check_ollama_models


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __call__(self, host):  # used as Client(host=...)
        return self

    def list(self):
        return self._response

    def embed(self, model, input):
        return {"embeddings": [[0.1, 0.2]]}

    def chat(self, model, messages, options):
        return {"message": {"content": "ok"}}


def _run_with_response(response) -> None:
    fake = _FakeClient(response)
    with patch("app.services.ollama_health_check.Client", return_value=fake):
        check_ollama_models(
            host="http://localhost:11434",
            llm_model="qwen2.5:14b",
            embedding_model="bge-m3",
        )


def test_check_ollama_models_passes_with_new_object_response():
    """New ollama client returns ListResponse with Model objects having `.model`."""
    response = SimpleNamespace(
        models=[
            SimpleNamespace(model="qwen2.5:14b"),
            SimpleNamespace(model="bge-m3:latest"),
            SimpleNamespace(model="gemma4:e4b"),
        ]
    )
    _run_with_response(response)


def test_check_ollama_models_passes_with_legacy_dict_response():
    """Legacy ollama client returned dict with `name` key."""
    response = {
        "models": [
            {"name": "qwen2.5:14b"},
            {"name": "bge-m3:latest"},
        ]
    }
    _run_with_response(response)


def test_check_ollama_models_raises_when_missing():
    response = SimpleNamespace(models=[SimpleNamespace(model="gemma4:e4b")])
    with pytest.raises(RuntimeError, match="Missing Ollama models"):
        _run_with_response(response)
