"""Health check utility for Ollama service and models."""

from loguru import logger
from ollama import Client


def check_ollama_models(
    host: str = "http://localhost:11434",
    llm_model: str = "qwen2.5:14b",
    embedding_model: str = "bge-m3",
) -> None:
    """
    Check Ollama service availability and required models.

    Args:
        host: Ollama server URL.
        llm_model: Required LLM model name.
        embedding_model: Required embedding model name.

    Raises:
        RuntimeError: If Ollama service unavailable or models missing.
    """
    try:
        client = Client(host=host)
        logger.info(f"Checking Ollama service at {host}...")

        models_response = client.list()
        raw_models = (
            models_response.get("models", [])
            if isinstance(models_response, dict)
            else getattr(models_response, "models", [])
        )

        def _model_name(m: object) -> str:
            if isinstance(m, dict):
                return m.get("model") or m.get("name") or ""
            return getattr(m, "model", None) or getattr(m, "name", "") or ""

        available_models = {
            _model_name(model).split(":")[0]
            for model in raw_models
            if _model_name(model)
        }
        logger.info(f"Available models: {available_models}")

        missing_models = []
        llm_model_base = llm_model.split(":")[0]
        embedding_model_base = embedding_model.split(":")[0]

        if llm_model_base not in available_models:
            missing_models.append(llm_model)
        if embedding_model_base not in available_models:
            missing_models.append(embedding_model)

        if missing_models:
            error_msg = f"Missing Ollama models: {', '.join(missing_models)}. "
            error_msg += "Please pull them with:\n"
            for model in missing_models:
                error_msg += f"  ollama pull {model}\n"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Preflight: test embed and chat with small inputs
        logger.info("Preflight: testing embed and chat...")
        try:
            client.embed(model=embedding_model, input=["test"])
            logger.debug("Embed preflight passed")
        except Exception as e:
            logger.error(f"Embed preflight failed: {e}")
            raise RuntimeError(f"Ollama embed failed: {e}") from e

        try:
            client.chat(
                model=llm_model,
                messages=[{"role": "user", "content": "test"}],
                options={"num_ctx": 512},
            )
            logger.debug("Chat preflight passed")
        except Exception as e:
            logger.error(f"Chat preflight failed: {e}")
            raise RuntimeError(f"Ollama chat failed: {e}") from e

        logger.info("Ollama health check passed.")

    except Exception as e:
        if "connect" in str(e).lower() or "connection" in str(e).lower():
            error_msg = f"Cannot connect to Ollama at {host}. "
            error_msg += "Please ensure Ollama is running: 'ollama serve'"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        raise
