"""Ollama implementation of EmbeddingClient protocol."""

import json
import time
from typing import List

from loguru import logger
from ollama import Client

from app.services.protocols import EmbeddingClient

# #region agent log helpers
import os as _os, time as _time

_DEBUG_LOG = "/Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.cursor/debug-c603c2.log"

def _dblog(msg: str, data: dict, hypothesis: str) -> None:
    entry = json.dumps({"sessionId": "c603c2", "timestamp": int(_time.time() * 1000), "location": "ollama_embedding_client.py", "message": msg, "data": data, "hypothesisId": hypothesis})
    with open(_DEBUG_LOG, "a") as _f:
        _f.write(entry + "\n")
# #endregion


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

        # #region agent log H-A/H-B: log batch content before sending to Ollama
        _dblog("embed_batch_start", {
            "n_texts": len(texts),
            "texts_preview": [{"idx": i, "len": len(t), "text": t[:120]} for i, t in enumerate(texts)],
            "has_empty": any(not t.strip() for t in texts),
            "has_null": any(t is None for t in texts),
        }, "H-A/H-B")
        # #endregion

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
                # #region agent log H-A/H-B/H-C: log failure details
                _dblog("embed_attempt_failed", {
                    "attempt": attempt + 1,
                    "error": str(e),
                    "texts_at_failure": [{"idx": i, "len": len(t), "text": t[:200]} for i, t in enumerate(texts)],
                }, "H-A/H-B/H-C")
                # #endregion
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
