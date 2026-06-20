---
phase: implementation
title: Implementation Guide
description: Technical implementation notes, patterns, and code guidelines
---

# Implementation Guide

## Development Setup
**How do we get started?**

- Added `openai>=1.0.0` to [requirements.txt](file:///Users/tuanha15/Work/projects/Python/convert-vsic-to-mcc/mcc-lens/requirements.txt).
- Installed dependencies using `pip install -r requirements.txt`.

## Code Structure
**How is the code organized?**

- [requirements.txt](file:///Users/tuanha15/Work/projects/Python/convert-vsic-to-mcc/mcc-lens/requirements.txt): Added dependency `openai`.
- `app/config.py`: Add `LLM_PROVIDER`, `WOKUSHOP_API_KEY`, `WOKUSHOP_BASE_URL`, `WOKUSHOP_MODEL` config and validate.
- `app/repositories/wokushop_llm_client.py` (New): `WokuShopLLMClient` implementation.
- `app/services/ollama_health_check.py`: Extract `check_ollama_embedding`.
- `app/controllers/mapping_controller.py`: Implement provider selection and health checks.
- `main.py`: Pass provider settings from Config to controller.
- `tests/test_wokushop_llm_client.py` (New): Unit tests for Config validation and `WokuShopLLMClient`.

## Implementation Notes
**Key technical details to remember:**

### Core Features
- **Task 6 (Done)**: Installed `openai>=1.0.0` for integration with WokuShop LLM API. Verified package import and version `1.109.1`.
- **Task 1 (Done)**: Added WokuShop config variables and validation to Config class in `app/config.py`. Verified with unit test in `tests/test_config.py`.
- **Task 2 (Done)**: Implemented `WokuShopLLMClient` in `app/repositories/wokushop_llm_client.py` and wrote unit tests in `tests/test_wokushop_llm_client.py`.
- **Task 3 (Done)**: Extracted `check_ollama_embedding` from `check_ollama_models` in `app/services/ollama_health_check.py` to allow embedding checks only when using WokuShop provider. Verified backwards compatibility.
- **Task 4 (Done)**: Updated `MappingController` in `app/controllers/mapping_controller.py` to accept `llm_provider`, `wokushop_api_key`, `wokushop_base_url`, `wokushop_model`. Conducted dynamic DI and health check accordingly.
- **Task 5 (Done)**: Wired Config parameters into `MappingController` in `main.py`. Verified that executing `python3 main.py map-vsic-mcc --help` does not crash.
- **Task 7 (Done)**: Wrote comprehensive unit tests for `WokuShopLLMClient` and validation rules in `tests/test_wokushop_llm_client.py` and `tests/test_config.py`. All tests pass.
- **Task 8 (Done)**: Updated `.env.example` with default values and documentation for WokuShop integration.
- **Task 9 (Done)**: Conducted smoke tests validating:
  - Fail-fast config validation when `LLM_PROVIDER=wokushop` and `WOKUSHOP_API_KEY` is empty.
  - Fail-fast health check behavior detecting lack of embedding model/embedding support.
  - Verification of call flow sequence and proper exit codes (exit code 2 for health check failure, exit code 1 for ValueError).

### Patterns & Best Practices
- Implements `LLMClient` protocol.
- Follows existing Ollama client's retry pattern with exponential backoff.
- Dynamic dependency injection inside controller.

## Integration Points
- OpenAI SDK connected to `https://llm.wokushop.com/v1`.

## Error Handling
- Retry logic (3 attempts) with `time.sleep(2**attempt)` backoff.
- Custom ValueError on empty configuration.

## Performance Considerations
- Timeout limit set to 120s.

## Security Notes
- `WOKUSHOP_API_KEY` loaded from environment variables and never logged or exposed.

## Check Implementation (Phase 6 — 2026-06-17)

**Alignment:** Strong. All 8 design components shipped as designed (new client, config + validate, controller provider selection, `check_ollama_embedding` extraction, `main.py` wiring, `requirements.txt`, tests, `.env.example`).

**Verification evidence:** `python3 -m pytest tests/test_wokushop_llm_client.py tests/test_config.py tests/test_mapping_controller.py tests/test_ollama_health_check.py --no-cov -q` → **36 passed**. Retry pattern confirmed identical to `OllamaLLMClient` (3 attempts, `2**attempt` backoff).

**Deviations / follow-ups:**
- **[Low] Unused import** — `from typing import Optional` in `app/repositories/wokushop_llm_client.py:4` is never used (flake8 F401). Remove.
- **[Low] Type mismatch** — `WokuShopLLMClient.__init__(api_key: str)` receives `Optional[str]` from controller; runtime-safe (guaranteed by `Config.validate()`) but mypy would flag. Optionally narrow with an assert.
- **[Medium] Env reproducibility** — `openai` is installed in the active `pyenv` `python3` but NOT in the project `venv`. Per CLAUDE.md (`python3 main.py` from venv) provider=wokushop would raise `ModuleNotFoundError`. Run `pip install -r requirements.txt` inside `venv` before use.
- **[Low] Stale help text** — `main.py:119` help for `map-vsic-mcc` still reads "using Ollama LLM"; provider is now env-driven.
- **[Low] Client constructed twice** — `WokuShopLLMClient` is built once for health check and again for DI in `mapping_controller.execute`. Harmless; could reuse.
- **[Open] Real-call smoke test** — design's manual integration smoke-test (1 real WokuShop call) is not yet evidenced; success criteria for end-to-end run remain unchecked.

