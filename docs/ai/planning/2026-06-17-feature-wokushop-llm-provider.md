---
phase: planning
title: Planning — WokuShop LLM Provider
description: Task breakdown để implement WokuShopLLMClient + provider selection
---

# Planning — WokuShop LLM Provider

## Task Breakdown

### Task 1: Thêm env vars vào Config

**File:** `app/config.py`

- Thêm `LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")`
- Thêm `WOKUSHOP_API_KEY: Optional[str] = os.getenv("WOKUSHOP_API_KEY")`
- Thêm `WOKUSHOP_BASE_URL: str = os.getenv("WOKUSHOP_BASE_URL", "https://llm.wokushop.com/v1")`
- Thêm `WOKUSHOP_MODEL: str = os.getenv("WOKUSHOP_MODEL", "gpt-4o")`
- Bổ sung `validate()`: nếu `LLM_PROVIDER == "wokushop"` và `WOKUSHOP_API_KEY` trống → raise `ValueError`

**Verify:** `pytest tests/test_config.py` pass.

---

### Task 2: Implement WokuShopLLMClient

**File:** `app/repositories/wokushop_llm_client.py` (NEW)

- Import: `from openai import OpenAI`
- Class `WokuShopLLMClient` implements `LLMClient` protocol
- `__init__(api_key, base_url, model, timeout=120)`: init `OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)`
- `chat(system, user, *, temperature=0.0) -> str`:
  - Validate non-empty inputs
  - 3 retry với `time.sleep(2**attempt)` backoff
  - Call `client.chat.completions.create(model=..., messages=[...], response_format={"type":"json_object"}, temperature=temperature)`
  - Extract `response.choices[0].message.content`
  - Raise `RuntimeError` sau 3 lần thất bại
- `health_check() -> bool`: gọi `client.models.list()`, return `True`; except return `False`

**Verify:** `pytest tests/test_wokushop_llm_client.py` pass.

---

### Task 3: Extract check_ollama_embedding từ ollama_health_check

**File:** `app/services/ollama_health_check.py`

- Extract function `check_ollama_embedding(host: str, embedding_model: str) -> None` từ `check_ollama_models`
- `check_ollama_models` vẫn giữ nguyên signature và behavior (backward compatible)

**Verify:** `pytest tests/` (existing tests) không regression.

---

### Task 4: Update MappingController — provider selection

**File:** `app/controllers/mapping_controller.py`

- `__init__` thêm param `llm_provider: str = "ollama"` và 3 WokuShop params: `wokushop_api_key`, `wokushop_base_url`, `wokushop_model`
- `execute()`:
  - Import `WokuShopLLMClient` và `check_ollama_embedding`
  - Health check block: nếu `llm_provider == "wokushop"` → `check_ollama_embedding(...)` + `wokushop_client.health_check()` ; else → `check_ollama_models(...)` (unchanged)
  - DI block: nếu `llm_provider == "wokushop"` → `WokuShopLLMClient(...)` ; else → `OllamaLLMClient(...)` (unchanged)
  - Log provider đang dùng lúc startup

**Verify:** Manual smoke test với `LLM_PROVIDER=ollama` → pipeline chạy như cũ.

---

### Task 5: Update main.py — wire config vào controller

**File:** `main.py`

- Tìm chỗ khởi tạo `MappingController`
- Truyền thêm: `llm_provider=Config.LLM_PROVIDER`, `wokushop_api_key=Config.WOKUSHOP_API_KEY`, `wokushop_base_url=Config.WOKUSHOP_BASE_URL`, `wokushop_model=Config.WOKUSHOP_MODEL`

**Verify:** `python3 main.py map-vsic-mcc --help` không crash.

---

### Task 6: Thêm openai vào requirements.txt

**File:** `requirements.txt`

- Thêm `openai>=1.0.0`
- Chạy `pip install -r requirements.txt` để xác nhận cài được

**Verify:** `python3 -c "import openai; print(openai.__version__)"` không lỗi.

---

### Task 7: Viết unit tests cho WokuShopLLMClient

**File:** `tests/test_wokushop_llm_client.py` (NEW)

Tests:
1. `test_chat_success`: mock `openai.OpenAI`, verify trả về content string
2. `test_chat_retry_then_success`: mock 2 lần fail + 1 lần pass → verify retry logic
3. `test_chat_all_retries_fail`: mock 3 lần fail → verify `RuntimeError`
4. `test_chat_empty_input`: verify `ValueError` với inputs trống
5. `test_health_check_success`: mock `models.list()` → trả về `True`
6. `test_health_check_failure`: mock exception → trả về `False`
7. `test_config_validate_missing_key`: verify `Config.validate()` raise `ValueError` khi provider=wokushop và key trống

**Verify:** `pytest tests/test_wokushop_llm_client.py -v` tất cả pass.

---

### Task 8: Update .env.example

**File:** `.env.example`

- Thêm section WokuShop provider:
  ```
  # LLM Provider (ollama | wokushop)
  LLM_PROVIDER=ollama
  WOKUSHOP_API_KEY=
  WOKUSHOP_BASE_URL=https://llm.wokushop.com/v1
  WOKUSHOP_MODEL=gpt-4o
  ```

**Verify:** File tồn tại và không chứa API key thật.

---

### Task 9: Smoke test end-to-end với WokuShop

- Set `LLM_PROVIDER=wokushop` + `WOKUSHOP_API_KEY=<key thật>` trong `.env`
- Chạy: `python3 main.py map-vsic-mcc --limit 3`
- Verify: output Excel có 3 rows, JSON response parseable, không lỗi

---

## Task Order & Dependencies

```
Task 6 (requirements)
  ↓
Task 2 (WokuShopLLMClient) ← Task 1 (Config)
  ↓                                ↓
Task 3 (extract health check)   Task 5 (main.py) ← Task 4 (controller)
  ↓                                ↓
Task 4 (controller)             Task 9 (smoke test)
  ↓
Task 7 (unit tests)
Task 8 (.env.example)
```

Thứ tự thực hiện: 6 → 1 → 2 → 3 → 4 → 5 → 7 → 8 → 9

## Risks

| Risk | Mitigation |
|---|---|
| WokuShop endpoint không nhận `/v1` suffix | Thử `https://llm.wokushop.com` nếu smoke test fail |
| `json_object` mode không support qua proxy | Fallback: không set `response_format`, dùng `_parse_llm_response` tolerant |
| `openai` package conflict với version đang cài | Pin `openai>=1.0.0,<2.0.0` nếu cần |

## Status

- [x] Task 1 — Config env vars
- [x] Task 2 — WokuShopLLMClient
- [x] Task 3 — extract health check
- [x] Task 4 — MappingController update
- [x] Task 5 — main.py wiring
- [x] Task 6 — requirements.txt
- [x] Task 7 — unit tests
- [x] Task 8 — .env.example
- [x] Task 9 — smoke test
