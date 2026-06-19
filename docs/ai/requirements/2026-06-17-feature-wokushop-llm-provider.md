---
phase: requirements
title: Requirements & Problem Understanding — WokuShop LLM Provider
description: Thay thế Ollama/qwen2.5 re-ranker bằng WokuShop API (OpenAI-compatible) trong pipeline VSIC→MCC mapping
---

# Requirements & Problem Understanding

## Problem Statement

**What problem are we solving?**

Pipeline VSIC→MCC mapping hiện dùng 2-stage:
1. **Embedding retrieval** (`bge-m3` via Ollama) → top-K MCC candidates
2. **LLM re-rank** (`qwen2.5:14b` via Ollama) → chọn top-3, emit JSON

Vấn đề với `qwen2.5:14b` via Ollama:
- **Chất lượng mapping thấp**: Model 14B không đủ reasoning để handle Vietnamese input + strict JSON output ổn định.
- **Tốc độ chậm**: Inference trên M1 16GB mất vài giây/VSIC entry, total run >500 entries mất nhiều giờ.
- **GPU/infra cost**: GPU bị chiếm toàn bộ trong quá trình chạy; phát sinh NaN/GPU-corruption issues.

**Người bị ảnh hưởng:** Developer chạy batch VSIC→MCC mapping.

**Workaround hiện tại:** Chạy với qwen2.5:14b, chấp nhận chất lượng thấp và thời gian dài.

## Goals & Objectives

**Primary:**
- Thêm `WokuShopLLMClient` implement `LLMClient` protocol, dùng WokuShop API (`https://llm.wokushop.com/v1`) thay thế Ollama cho bước re-rank.
- Cấu hình provider qua env: `LLM_PROVIDER=wokushop` → dùng WokuShop; `LLM_PROVIDER=ollama` (default) → dùng Ollama như cũ.
- Default model: `gpt-4o` với `response_format={"type":"json_object"}`, `temperature=0`.
- Giữ nguyên `OllamaLLMClient` để fallback instant.

**Secondary:**
- Health-check khi provider=wokushop: dùng `models.list()` ping thay vì Ollama health endpoint.
- Config validation: fail-fast nếu `LLM_PROVIDER=wokushop` nhưng `WOKUSHOP_API_KEY` trống.

**Non-goals:**
- Không thay thế embedding (`bge-m3` vẫn dùng Ollama local).
- Không migrate `bge-m3` sang CPU.
- Không thay đổi use case / service logic.
- Không thêm UI / web API.
- Không thêm streaming hay async.

## User Stories & Use Cases

- Là **developer**, tôi muốn đặt `LLM_PROVIDER=wokushop` trong `.env` để pipeline dùng gpt-4o thay qwen2.5:14b, nhận kết quả chất lượng cao hơn mà không cần thay code.
- Là **developer**, tôi muốn giữ `LLM_PROVIDER=ollama` (hoặc không set) để pipeline hoạt động như cũ — không phá vỡ backward compatibility.
- Là **developer**, tôi muốn health-check lúc startup cho biết WokuShop có reachable không trước khi chạy cả batch.

**Edge cases:**
- `WOKUSHOP_API_KEY` không set mà `LLM_PROVIDER=wokushop` → fail-fast với error message rõ.
- WokuShop trả về non-JSON hoặc wrapped JSON → `_parse_llm_response` đã tolerant, giữ nguyên.
- Network error / timeout → retry 3 lần (giống pattern OllamaLLMClient hiện tại).
- Model không support `json_object` mode qua proxy → fallback về string parsing trong `_parse_llm_response`.

## Success Criteria

- [ ] `LLM_PROVIDER=wokushop WOKUSHOP_API_KEY=<key> python3 main.py map-vsic-mcc` chạy được end-to-end.
- [ ] Smoke test: 1 VSIC entry → WokuShop trả về JSON parseable bởi `_parse_llm_response`.
- [ ] Sample run: 10–20 VSIC entries hoàn thành, output Excel hợp lệ.
- [ ] Fallback: `LLM_PROVIDER=ollama` → pipeline dùng qwen2.5:14b như trước (không regression).
- [ ] Config fail-fast: thiếu `WOKUSHOP_API_KEY` với provider=wokushop → lỗi rõ ràng trước khi chạy batch.
- [ ] Health-check lúc startup hiển thị provider đang dùng và status (reachable/unreachable).
- [ ] API key không bao giờ được log ra.
- [ ] Unit test cho `WokuShopLLMClient` (mock HTTP).
- [ ] `requirements.txt` có `openai`.

## Constraints & Assumptions

- **Architecture**: `LLMClient` protocol đã tồn tại ở `app/services/protocols.py`. `WokuShopLLMClient` là concrete implementation trong `app/repositories/`.
- **Provider selection**: DI tại `app/controllers/mapping_controller.py` — chọn client theo `Config.LLM_PROVIDER`.
- **OpenAI SDK**: Dùng `openai` Python package với `base_url=https://llm.wokushop.com/v1`.
- **Config pattern**: Theo `app/config.py` hiện tại — thêm env vars: `LLM_PROVIDER`, `WOKUSHOP_API_KEY`, `WOKUSHOP_BASE_URL` (default `https://llm.wokushop.com/v1`), `WOKUSHOP_MODEL` (default `gpt-4o`).
- **Scale**: < 500 VSIC entries — token cost negligible, không cần optimize batch.
- **Data sensitivity**: Public industry-classification data → third-party proxy acceptable.
- **Assumption**: WokuShop API compatible với OpenAI SDK (`chat.completions.create`, `models.list`).
- **Assumption**: `_parse_llm_response` trong service đã handle JSON parsing đủ tolerant — không cần thay đổi.
- **Retry**: 3 lần retry với exponential backoff, giống OllamaLLMClient.

## Questions & Open Items

- [x] Scope: chỉ thay LLM re-rank, không thay embedding. → **Resolved**
- [x] Model mặc định: `gpt-4o`. → **Resolved**
- [x] API key: đã có → có thể smoke-test sau implement. → **Resolved**
- [ ] `WOKUSHOP_BASE_URL`: default `https://llm.wokushop.com/v1` — cần xác nhận đây là OpenAI-compatible endpoint đúng (có `/v1` suffix không?).
- [ ] Retry pattern: confirm số lần retry và delay từ `OllamaLLMClient` hiện tại để replicate đúng.
