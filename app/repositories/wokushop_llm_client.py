"""WokuShop implementation of LLMClient protocol."""

import time

from loguru import logger
from openai import OpenAI

from app.services.protocols import LLMClient


class WokuShopLLMClient(LLMClient):
    """WokuShop-based LLM client for chat completion."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://llm.wokushop.com/v1",
        model: str = "gpt-4o",
        timeout: int = 120,
    ) -> None:
        """Initialize WokuShop LLM client.

        Args:
            api_key: WokuShop API Key.
            base_url: WokuShop API URL base.
            model: LLM model name.
            timeout: Request timeout in seconds.
        """
        if not api_key:
            raise ValueError("WOKUSHOP_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def chat(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        """Generate chat completion with retry and timeout.

        Args:
            system: System prompt.
            user: User prompt.
            temperature: Sampling temperature.

        Returns:
            LLM response string.

        Raises:
            ValueError: If system or user prompts are empty.
            RuntimeError: If all retry attempts fail.
        """
        max_retries = 3

        if not system or not user:
            raise ValueError("System and user prompts cannot be empty")

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"WokuShop LLM chat with model {self.model} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                # response_format json_object is only supported by OpenAI-compatible
                # models (gpt-*). Anthropic/Gemini models via Wokushop may reject it.
                is_openai_model = self.model.startswith(("gpt-", "o1", "o3"))
                kwargs = dict(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                )
                if is_openai_model:
                    kwargs["response_format"] = {"type": "json_object"}
                response = self.client.chat.completions.create(**kwargs)

                content = response.choices[0].message.content
                if content is None:
                    content = ""

                # Strip whitespace to check for empty response content
                if not content.strip():
                    raise ValueError("Empty response from LLM")

                return content

            except Exception as e:
                logger.warning(f"WokuShop LLM chat attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} WokuShop LLM chat attempts failed")
                    raise RuntimeError(
                        f"Failed to get LLM response after {max_retries} attempts: {e}"
                    ) from e

    def health_check(self) -> bool:
        """Check if WokuShop LLM endpoint is reachable and API key is valid.

        Returns:
            True if health check succeeds, False otherwise.
        """
        try:
            # Call models.list() as a lightweight endpoint connectivity test
            self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"WokuShop health check failed: {e}")
            return False
