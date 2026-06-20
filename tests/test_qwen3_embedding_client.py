import sys
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

# Use shared mock for sentence_transformers to avoid conflicts in pytest process
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()
mock_sentence_transformers = sys.modules["sentence_transformers"]

from app.repositories.qwen3_embedding_client import Qwen3EmbeddingClient


def test_qwen3_embedding_client_lazy_load():
    # Reset mock before testing
    mock_sentence_transformers.SentenceTransformer.reset_mock()
    
    client = Qwen3EmbeddingClient(model_name="dummy-embedding")
    assert client._model is None
    
    # Access model property should trigger initialization
    model = client.model
    assert model is not None
    mock_sentence_transformers.SentenceTransformer.assert_called_once_with("dummy-embedding", trust_remote_code=True)
    assert client._model is not None


def test_qwen3_embedding_client_embed():
    mock_instance = MagicMock()
    # Encode returns a list of vectors (arrays)
    mock_instance.encode.return_value = [
        np.array([0.1, 0.2, 0.3]),
        np.array([0.4, 0.5, 0.6])
    ]
    mock_sentence_transformers.SentenceTransformer.return_value = mock_instance
    
    # Reset mock call history
    mock_sentence_transformers.SentenceTransformer.reset_mock()
    
    client = Qwen3EmbeddingClient(model_name="dummy-embedding-2")
    # Force loading new instance for test with reset mock
    client._model = None
    embeddings = client.embed(["text1", "text2"])
    
    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2, 0.3]
    assert embeddings[1] == [0.4, 0.5, 0.6]
    mock_instance.encode.assert_called_once_with(["text1", "text2"], normalize_embeddings=True)


def test_qwen3_embedding_client_empty_texts():
    client = Qwen3EmbeddingClient(model_name="dummy-embedding")
    assert client.embed([]) == []
