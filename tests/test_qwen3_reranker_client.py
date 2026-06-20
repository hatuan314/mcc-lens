import sys
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

# Use shared mock for sentence_transformers to avoid conflicts in pytest process
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()
mock_sentence_transformers = sys.modules["sentence_transformers"]

from app.repositories.qwen3_reranker_client import Qwen3RerankerClient


def test_qwen3_reranker_client_lazy_load():
    # Reset mock before testing
    mock_sentence_transformers.CrossEncoder.reset_mock()
    
    client = Qwen3RerankerClient(model_name="dummy-reranker")
    assert client._model is None
    
    # Access model property should trigger initialization
    model = client.model
    assert model is not None
    mock_sentence_transformers.CrossEncoder.assert_called_once_with("dummy-reranker", trust_remote_code=True)
    assert client._model is not None


def test_qwen3_reranker_client_rerank():
    mock_instance = MagicMock()
    # predict returns raw logits
    mock_instance.predict.return_value = np.array([0.0, 2.0, -2.0])
    mock_sentence_transformers.CrossEncoder.return_value = mock_instance
    
    # Reset mock call history
    mock_sentence_transformers.CrossEncoder.reset_mock()
    
    client = Qwen3RerankerClient(model_name="dummy-reranker-2")
    client._model = None
    scores = client.rerank("query text", ["doc1", "doc2", "doc3"])
    
    # Sigmoid calculation: 1.0 / (1.0 + exp(-logits))
    expected_scores = [
        1.0 / (1.0 + np.exp(0.0)),  # 0.5
        1.0 / (1.0 + np.exp(-2.0)), # ~0.880797
        1.0 / (1.0 + np.exp(2.0))   # ~0.1192029
    ]
    
    assert len(scores) == 3
    assert pytest.approx(scores[0]) == expected_scores[0]
    assert pytest.approx(scores[1]) == expected_scores[1]
    assert pytest.approx(scores[2]) == expected_scores[2]
    
    mock_instance.predict.assert_called_once_with([
        ("query text", "doc1"),
        ("query text", "doc2"),
        ("query text", "doc3")
    ])


def test_qwen3_reranker_client_rerank_scalar():
    mock_instance = MagicMock()
    mock_instance.predict.return_value = 0.0  # scalar logit
    mock_sentence_transformers.CrossEncoder.return_value = mock_instance
    
    client = Qwen3RerankerClient(model_name="dummy-reranker-3")
    client._model = None
    scores = client.rerank("query text", ["doc1"])
    
    assert len(scores) == 1
    assert pytest.approx(scores[0]) == 0.5


def test_qwen3_reranker_client_empty_docs():
    client = Qwen3RerankerClient(model_name="dummy-reranker")
    assert client.rerank("query text", []) == []
