---
phase: testing
title: Testing Strategy
description: Define testing approach, test cases, and quality assurance
---

# Testing Strategy

## Test Coverage Goals
**What level of testing do we aim for?**

- Unit test coverage target: >90% coverage on new/changed code. `wokushop_llm_client.py` at 98% (only the unreachable post-loop defensive `raise` on line 98 uncovered).
- Integration test scope: Verify dynamic provider selection, client retry backoffs, and fail-fast startup behavior.

## Unit Tests
**What individual components need testing?**

### Config validation (tests/test_config.py)
- [x] `test_config_wokushop_validation`: Verify `Config.validate()` raises `ValueError` if `LLM_PROVIDER="wokushop"` and `WOKUSHOP_API_KEY` is empty. Pass validation if key is provided.

### WokuShopLLMClient (tests/test_wokushop_llm_client.py)
- [x] `test_chat_success`: Verify standard json chat returns output string correctly.
- [x] `test_chat_empty_response_raises`: Raise `RuntimeError` if response content is empty.
- [x] `test_chat_none_content_raises`: Raise `RuntimeError` when `message.content` is `None` (coerced to empty, fails after retries).
- [x] `test_chat_empty_prompts_raises`: Raise `ValueError` if system or user prompts are empty strings.
- [x] `test_chat_retry_then_success`: Verify retry backoff structure succeeds on the 3rd attempt after 2 failures.
- [x] `test_chat_all_retries_fail`: Raise `RuntimeError` after 3 consecutive failures.
- [x] `test_health_check_success`: Return `True` when `models.list()` succeeds.
- [x] `test_health_check_failure`: Return `False` when `models.list()` raises an exception.

### Ollama embedding health check (tests/test_ollama_health_check.py)
- [x] `test_check_ollama_embedding_passes`: Verify health check succeeds when the embedding model is available.
- [x] `test_check_ollama_embedding_missing`: Raise `RuntimeError` when the embedding model is missing.

### MappingController wiring (tests/test_mapping_controller.py)
- [x] `test_wokushop_provider_success`: Verify MappingController instantiates WokuShop client and returns exit code 0.
- [x] `test_wokushop_provider_health_check_failure`: Return exit code 2 when WokuShop LLM health check fails.

## Smoke & Manual Testing
**What requires validation?**

- [x] CLI fail-fast validation check:
  `LLM_PROVIDER=wokushop python3 main.py map-vsic-mcc --limit 3` -> Verified exit code 1 due to `ValueError`.
- [x] CLI health check flow integration check:
  `LLM_PROVIDER=wokushop WOKUSHOP_API_KEY=test_key python3 main.py map-vsic-mcc --limit 3 --embedding-model qwen2.5:7b` -> Verified exit code 2 due to embedding capability failure check on LLM model.

## Test Reporting & Coverage
**How do we verify and communicate test results?**

- Coverage command: `pytest`
- Results: **321 tests passed** in ~17.60s. Global test coverage: **91%**.

## Performance Testing
**How do we validate performance?**

- Load testing scenarios
- Stress testing approach
- Performance benchmarks

## Bug Tracking
**How do we manage issues?**

- Issue tracking process
- Bug severity levels
- Regression testing strategy
