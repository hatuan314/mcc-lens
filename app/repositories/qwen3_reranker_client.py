"""Qwen3-Reranker client implementation of RerankerClient protocol."""

from typing import List
import numpy as np
from loguru import logger
from app.services.protocols import RerankerClient


class Qwen3RerankerClient(RerankerClient):
    """Qwen3-Reranker client using sentence-transformers (GPU/Colab only)."""

    def __init__(self, model_name: str = "Qwen/Qwen3-Reranker") -> None:
        """Initialize the reranker model client.

        Args:
            model_name: Hugging Face model path.
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the sentence-transformers CrossEncoder to avoid heavy imports under local."""
        if self._model is None:
            logger.info(f"Lazy loading Qwen3-Reranker model: {self.model_name}")
            from sentence_transformers import CrossEncoder
            # trust_remote_code=True is required for Qwen models
            self._model = CrossEncoder(self.model_name, trust_remote_code=True)
        return self._model

    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """Rank candidate documents for a query and return similarity scores (0.0-1.0).

        Args:
            query: Query string.
            documents: List of candidate document strings.

        Returns:
            List of relevance scores, same length as documents.
        """
        if not documents:
            return []

        logger.debug(f"Reranking {len(documents)} documents for query: '{query[:50]}...'")
        
        # CrossEncoder accepts list of (query, doc) pairs
        pairs = [(query, doc) for doc in documents]
        raw_scores = self.model.predict(pairs)

        # Convert potential scalar to array
        if isinstance(raw_scores, (int, float)):
            raw_scores = np.array([raw_scores])

        # Apply sigmoid to map raw logits to relevance probability range 0.0 - 1.0
        scores = 1.0 / (1.0 + np.exp(-raw_scores))
        
        return [float(s) for s in scores]
