---
phase: implementation
title: Implementation Guide — Mapping VSIC to MCC
description: Hướng dẫn kỹ thuật triển khai pipeline mapping VSIC→MCC với Ollama + Qwen2.5:14b
---

# Implementation Guide

> File này sẽ được điền trong quá trình code (phase 3–5 của planning). Hiện chỉ ghi khung + các note quan trọng để dev tuân theo.

## Development Setup

**Prerequisites:**

- Python 3.8+, virtualenv đã kích hoạt.
- Ollama đang chạy: `ollama serve` (port 11434 mặc định).
- Models pulled:
  ```bash
  ollama pull qwen2.5:14b
  ollama pull bge-m3    # hoặc: ollama pull nomic-embed-text
  ```
- Khuyến nghị: `export OLLAMA_MAX_LOADED_MODELS=1` để tránh OOM trên M1 16GB.
- Cài deps mới: `pip install -r requirements.txt` (sau khi thêm `ollama`).

**Configuration:** Không thêm env var mới — dùng CLI flags. Host Ollama, tên model truyền qua `--ollama-host`, `--llm-model`, `--embedding-model`.

## Code Structure

```
app/
├── models/
│   └── mapping_entry.py              # MappingEntry, RankedMcc pydantic DTOs
├── services/
│   ├── protocols.py                   # EmbeddingClient, LLMClient, MappingCheckpointRepository
│   ├── map_vsic_to_mcc_use_case.py    # orchestration (2-stage retrieval)
│   ├── mcc_code_validator.py          # validate + fallback logic
│   ├── llm_prompts.py                # SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
│   └── ollama_health_check.py        # check_ollama_models() helper
├── repositories/
│   ├── ollama_llm_client.py           # OllamaLLMClient implementation
│   ├── ollama_embedding_client.py     # OllamaEmbeddingClient implementation
│   ├── simple_mapping_xlsx_repository.py  # Simple 3-column Excel output
│   ├── detail_mapping_xlsx_repository.py  # Detailed 14-column Excel output
│   └── mapping_checkpoint_repository.py  # JSON checkpoint with atomic write
├── controllers/
│   └── mapping_controller.py         # CLI orchestration + exit codes
└── views/
    └── progress_bar_view.py           # reused (tqdm)
```

## Implementation Notes

### Core flow

1. **Controller** (`MappingController.execute()`):
   - Health check Ollama với `check_ollama_models()`
   - Load VSIC và MCC từ JSON files
   - Wire dependencies (OllamaEmbeddingClient, OllamaLLMClient, etc.)
   - Call use case với progress bar (tqdm)
   - Write Excel outputs (simple + detailed)

2. **Use Case** (`MapVsicToMccUseCase.execute()`):
   - Precompute MCC embeddings (1 lần, batch all MCC)
   - Loop VSIC entries:
     - Skip nếu đã trong checkpoint (resume mode)
     - Embed VSIC title
     - Compute cosine similarity với tất cả MCC (numpy)
     - Khởi tạo `current_k = top_k` (mặc định 15)
     - Loop Adaptive Top-K (Escalation):
       - Lấy `current_k` candidates từ danh sách similarity đã sort
       - Build LLM prompt (song ngữ VSIC tiếng Việt + MCC tiếng Anh)
       - Call LLM for re-ranking
       - Parse JSON response
       - Nếu LLM trả về kết quả rỗng (fail) HOẶC (top-1 score < 0.5 VÀ chưa chạm trần):
         - Tăng `current_k` lên gấp đôi (vd: 15 → 30 → 60).
         - Giới hạn `current_k` không vượt quá `min(100, len(mcc_entries))` để tránh OOM/timeout.
         - Lặp lại việc gọi LLM với prompt mới.
       - Nếu có kết quả hợp lệ hoặc đã chạm trần `current_k`, thoát loop.
     - Validate MCC codes với `MccCodeValidator`
     - Save checkpoint atomically
     - Yield `MappingEntry`

3. **Repositories**:
   - `SimpleMappingXlsxRepository`: 3 cột (VSIC, MCC, Tên ngành)
   - `DetailMappingXlsxRepository`: 14 cột với top-3 MCC, score, comment
   - `MappingCheckpointRepository`: atomic write (tmp + os.replace)

### Patterns & Best Practices

- **DI via constructor:** tất cả service/controller nhận dependency qua `__init__`. Không có singleton global.
- **Protocol before impl:** thêm Protocol trong `protocols.py` trước, rồi mới tạo `OllamaLLMClient`.
- **Google-style docstring** + type hints bắt buộc (theo user rules).
- **Functions ≤ 20 dòng, ≤ 3 params** — tách helper nếu cần (ví dụ `_build_prompt`, `_parse_llm_json`).
- **Logging:** dùng `loguru.logger`, không `print`. DEBUG log raw prompt/response; INFO log tiến độ.

## Integration Points

- **Ollama HTTP:** qua `ollama` Python client (`ollama>=0.3.0`). Base URL cấu hình được; mặc định `http://localhost:11434`.
- **Cosine similarity:** dùng numpy (`np.dot`, `np.linalg.norm`) - đủ nhanh cho ~900 MCC vectors.
- **Excel output:** dùng `openpyxl` (đã có trong requirements).
- **Progress bar:** dùng `tqdm` (đã có trong requirements).
- **JSON input:** Controller load trực tiếp với `json.load()` (không dùng repository cũ).

## Error Handling

| Tình huống | Xử lý | Exit code |
|---|---|---|
| `FileNotFoundError` input | log error + return 1 | 1 |
| Ollama không response/unavailable | retry 3 lần, rồi raise RuntimeError | 2 |
| Model chưa pull | health check đầu run → raise RuntimeError với hướng dẫn `ollama pull` | 2 |
| LLM hallucinate MCC code | validator fallback top-1 embedding + log warning | 0 |
| IO write Excel | log + raise IOError → return 3 | 3 |
| Exception khác | log stacktrace → return 1 | 1 |

- **Retry:** dùng vòng for đơn giản `for attempt in range(3)` với `time.sleep(2 ** attempt)`. Không thêm thư viện retry.
- **Checkpoint flush** sau MỖI VSIC → crash chỉ mất tối đa 1 entry.

## Performance Considerations

- **Embedding batch:** gọi `ollama.embed(input=[...])` cho toàn bộ MCC list (903 entries) trong 1 call. Cho VSIC thì embed từng cái (vì loop tuần tự để kiểm soát checkpoint).
- **Cosine sim:** dùng numpy (`np.dot`, `np.linalg.norm`) - đủ nhanh cho ~900 MCC vectors, không cần FAISS.
- **Adaptive Top-K Escalation:** Giữ mặc định `top_k = 15` để tiết kiệm LLM token và tối ưu tốc độ. Chỉ tăng gấp đôi `top_k` (15 → 30 → 60) đối với các VSIC code khó (LLM không chọn được hoặc score embedding quá thấp), không tính lại embedding, chỉ tạo prompt mới chứa nhiều candidates hơn. Tránh gọi LLM vô ích bằng cách giới hạn max `current_k` (e.g. 100).
- **Prompt budget:** MCC description giới hạn 500 ký tự; prompt tổng < 2000 tokens → Qwen2.5:14b xử lý nhanh.
- **Không song song hoá:** Ollama M1 serial. Parallelize sẽ OOM.
- **Checkpoint:** atomic write (tmp + os.replace) đảm bảo không corrupt file.

## Security Notes

- 100% offline, không có network egress trừ lần đầu pull model qua `ollama pull`.
- Không có secret/API key.
- Không log payload PII (không có PII trong dataset này, nhưng log level DEBUG mới in full prompt).
- Input path validate (không path traversal vì là tool CLI cho dev, nhưng vẫn dùng `Path.resolve()` khi log).

## Actual Implementation Details

### Files Created/Modified

**New files:**
- `app/models/mapping_entry.py` - Pydantic DTOs (RankedMcc, MappingEntry)
- `app/services/llm_prompts.py` - SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, build_user_prompt()
- `app/services/mcc_code_validator.py` - MccCodeValidator.validate()
- `app/services/ollama_health_check.py` - check_ollama_models()
- `app/repositories/ollama_llm_client.py` - OllamaLLMClient.chat() với retry 3 lần
- `app/repositories/ollama_embedding_client.py` - OllamaEmbeddingClient.embed() với retry 3 lần
- `app/repositories/simple_mapping_xlsx_repository.py` - SimpleMappingXlsxRepository.write()
- `app/repositories/detail_mapping_xlsx_repository.py` - DetailMappingXlsxRepository.write()
- `app/repositories/mapping_checkpoint_repository.py` - MappingCheckpointRepository (atomic write)
- `app/controllers/mapping_controller.py` - MappingController.execute()

**Modified files:**
- `app/services/protocols.py` - Added EmbeddingClient, LLMClient, MappingCheckpointRepository protocols
- `requirements.txt` - Added `ollama>=0.3.0`
- `main.py` - Added `map-vsic-mcc` subcommand with all flags

### Key Design Decisions

1. **Type hints**: Sử dụng `typing.List` thay vì `list` builtin để tránh mypy warnings
2. **Protocol naming**: Import as alias (`MappingCheckpointRepository as MappingCheckpointRepo`) để tránh name conflict
3. **Optional template**: Detailed Excel output optional (skip nếu template_path=None)
4. **Progress bar**: Dùng `tqdm` trực tiếp thay vì reuse `ProgressBarView`
5. **Type ignore**: Thêm `# type: ignore[return]` cho methods có mypy false positives

### CLI Integration

Subcommand `map-vsic-mcc` với flags:
- `--vsic-input`: File VSIC JSON (default: `output/vsic-vn.json`)
- `--mcc-input`: File MCC JSON (default: `output/mcc-visa.json`)
- `--output`: Simple Excel output (default: `output/vsic-mcc-mapping.xlsx`)
- `--output-detail`: Detailed Excel output (default: `output/vsic-mcc-mapping-detail.xlsx`)
- `--top-k`: Số candidates cho LLM (default: 15)
- `--ollama-host`: Ollama URL (default: `http://localhost:11434`)
- `--llm-model`: LLM model (default: `qwen2.5:14b`)
- `--embedding-model`: Embedding model (default: `bge-m3`)
- `--template`: Excel template path (default: `assets/template/vsic_mcc_mapping_template.xlsx`)
- `--resume`: Resume từ checkpoint
- `--limit`: Giới hạn số lượng bản ghi VSIC cần xử lý (mới thêm ở Phase 5)

### Phase 5 Improvements (Refining & QA)

1. **Linting & Documentation**: Đã áp dụng `black` và `flake8` cho toàn bộ thư mục `app/` và `tests/`. Đã tạo file cấu hình `.flake8` để đồng bộ line-length (88).
2. **Type Safety**: Fix toàn bộ các cảnh báo `mypy` liên quan đến `Any` return, `numpy` floating types, và missing return statements trong `OllamaLLMClient`.
3. **CLI Flexibility**: Bổ sung flag `--limit` để hỗ trợ chạy thử nghiệm nhanh (smoke test) mà không cần xử lý toàn bộ dataset.
4. **Unit testing**: Hoàn thiện 63 unit tests bao phủ các edge cases (hallucination, recovery, checkpoint corruption).
