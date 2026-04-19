"""Ollama implementation of LLMClient protocol."""

import time

from loguru import logger
from ollama import Client

from app.services.protocols import LLMClient


class OllamaLLMClient(LLMClient):
    """Ollama-based LLM client for chat completion."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        timeout: int = 180,
    ) -> None:
        """
        Initialize Ollama LLM client.

        Args:
            host: Ollama server URL.
            model: Model name to use.
            timeout: Request timeout in seconds.
        """
        self.host = host
        self.model = model
        self.timeout = timeout
        self.client = Client(host=host, timeout=timeout)

    def chat(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        """
        Generate chat completion with retry and timeout.

        Args:
            system: System prompt.
            user: User prompt.
            temperature: Sampling temperature.

        Returns:
            LLM response string.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        max_retries = 3

        if not system or not user:
            raise ValueError("System and user prompts cannot be empty")

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"LLM chat with model {self.model} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                response = self.client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    options={"temperature": temperature, "num_ctx": 8192},
                    format="json",
                )

                # Handle both dict and object responses
                if isinstance(response, dict):
                    content = response.get("message", {}).get("content", "")
                else:
                    content = (
                        getattr(getattr(response, "message", None), "content", "") or ""
                    )

                if not content:
                    raise ValueError("Empty response from LLM")

                return content

            except Exception as e:
                logger.warning(f"LLM chat attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} LLM chat attempts failed")
                    raise RuntimeError(
                        f"Failed to get LLM response after {max_retries} attempts: {e}"
                    ) from e
