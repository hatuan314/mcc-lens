"""Qwen3-Embedding client implementation of EmbeddingClient protocol."""

from typing import List
from loguru import logger
from app.services.protocols import EmbeddingClient


class Qwen3EmbeddingClient(EmbeddingClient):
    """Qwen3-Embedding client using sentence-transformers (GPU/Colab only)."""

    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding") -> None:
        """Initialize the embedding model client.

        Args:
            model_name: Hugging Face model path.
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the sentence-transformers model to avoid heavy imports under local."""
        if self._model is None:
            logger.info(f"Lazy loading Qwen3-Embedding model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, trust_remote_code=True)
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        logger.debug(f"Generating embeddings for {len(texts)} texts via {self.model_name}")
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        
        # Ensure return type is List[List[float]]
        return [list(map(float, emb)) for emb in embeddings]
