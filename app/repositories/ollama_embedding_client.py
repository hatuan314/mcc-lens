"""Ollama implementation of EmbeddingClient protocol."""

import time
from typing import List

from loguru import logger
from ollama import Client

from app.services.protocols import EmbeddingClient


class OllamaEmbeddingClient(EmbeddingClient):
    """Ollama-based embedding client."""

    def __init__(
        self, host: str = "http://localhost:11434", model: str = "bge-m3"
    ) -> None:
        """
        Initialize Ollama embedding client.

        Args:
            host: Ollama server URL.
            model: Embedding model name.
        """
        self.host = host
        self.model = model
        self.client = Client(host=host)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch of texts with retry and timeout.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        max_retries = 3

        if not texts:
            return []

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Embedding {len(texts)} texts with model {self.model} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                response = self.client.embed(
                    model=self.model,
                    input=texts,
                )

                # Handle both dict and object responses
                if isinstance(response, dict):
                    embeddings = response.get("embeddings", [])
                else:
                    embeddings = getattr(response, "embeddings", []) or []

                if len(embeddings) != len(texts):
                    raise ValueError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                    )

                return embeddings

            except Exception as e:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} embedding attempts failed")
                    raise RuntimeError(
                        f"Failed to generate embeddings after {max_retries} "
                        f"attempts: {e}"
                    ) from e
