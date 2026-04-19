---
phase: planning
title: Project Planning & Task Breakdown — Mapping VSIC to MCC
description: Phân rã công việc theo Clean Architecture, ưu tiên abstractions trước, implementation sau
---

# Project Planning & Task Breakdown

## Milestones

- [x] **M1 — Scaffolding & Abstractions:** Protocol + models + scaffolding repository/service empty, test import OK.
- [x] **M2 — Embedding pre-filter hoạt động:** Tính top-K MCC cho 1 VSIC sample bằng `OllamaEmbeddingClient`.
- [x] **M3 — End-to-end pipeline (no resume):** Chạy full 743 VSIC, xuất Excel đúng schema.
- [x] **M4 — Resume + progress bar + error handling:** Checkpoint, `--resume`, tqdm, exit codes.
- [x] **M5 — Tests + docs + quality gates:** Unit/integration tests, README cập nhật, `black/flake8/mypy` clean.

## Task Breakdown

### Phase 1: Foundation (M1)

- [x] **1.1** Cập nhật `requirements.txt`: thêm `ollama>=0.3.0`.
- [x] **1.2** Tạo `app/models/mapping_entry.py` — pydantic `RankedMcc` + `MappingEntry` DTO.
- [x] **1.3** Bổ sung `app/services/protocols.py`: `EmbeddingClient`, `LLMClient`, `MappingCheckpointRepository`.
- [x] **1.4** Tạo skeleton (pass-through) cho các module sẽ implement ở phase sau:
  - `app/services/map_vsic_to_mcc_use_case.py`
  - `app/services/mcc_code_validator.py`
  - `app/repositories/ollama_llm_client.py`
  - `app/repositories/ollama_embedding_client.py`
  - `app/repositories/simple_mapping_xlsx_repository.py`
  - `app/repositories/detail_mapping_xlsx_repository.py`
  - `app/repositories/mapping_checkpoint_repository.py`
  - `app/controllers/mapping_controller.py`

### Phase 2: Infrastructure Clients (M2)

- [x] **2.1** `OllamaEmbeddingClient.embed()` — dùng `ollama.embed`, batch input, retry 3 lần, timeout 60s.
- [x] **2.2** `OllamaLLMClient.chat()` — dùng `ollama.chat`, system+user prompt, `temperature=0.0`, timeout 180s.
- [x] **2.3** Health check helper: gọi `ollama.list()` trước khi bắt đầu; nếu model thiếu → raise với hướng dẫn `ollama pull <model>` (exit code 2).
- [x] **2.4** `MappingCheckpointRepository` — atomic write (`tmp + os.replace`), load gracefully nếu file chưa tồn tại.
- [x] **2.5** `SimpleMappingXlsxRepository.write()` — ghi file simple 3 cột (VSIC, MCC, Tên ngành) bằng `openpyxl`.
- [x] **2.6** `DetailMappingXlsxRepository.write()` — load template `assets/template/vsic_mcc_mapping_template.xlsx`, điền sheet "Mapping Result" (14 cột, top-3 ranks), giữ nguyên sheet "Hướng Dẫn" và "Thống Kê".

### Phase 3: Use Case Logic (M3)

- [x] **3.1** `MccCodeValidator` — validate MCC tồn tại trong danh sách; fallback top-1 embedding nếu LLM hallucinate.
- [x] **3.2** `MapVsicToMccUseCase`:
  - Precompute MCC embeddings 1 lần (concat `title + " — " + description[:500]`).
  - Loop VSIC: skip nếu đã trong checkpoint; embed → cosine sim → top-K → build LLM prompt → parse → validate → save checkpoint → yield progress.
- [x] **3.3** Prompt template (song ngữ):
  - System: "Bạn là chuyên gia phân loại ngành. Xếp hạng top-3 MCC phù hợp nhất cho ngành VSIC. Trả về JSON array [{mcc_code, comment}] theo thứ tự phù hợp nhất. comment là 1 câu ngắn giải thích tại sao. Nếu không có MCC nào phù hợp, trả về []."
  - User: VSIC title + top-K MCC candidates (code, title, description rút gọn).
  - Score trong output = cosine similarity từ embedding, thứ tự sắp xếp = thứ tự LLM chọn.

### Phase 4: CLI Integration (M4)

- [x] **4.1** `MappingController.execute()` — wire deps, gọi use case, xử lý exception → exit code.
- [x] **4.2** Cập nhật `main.py`: subcommand `map-vsic-mcc` với đầy đủ flags (xem design).
- [x] **4.3** Progress bar: sử dụng lại `ProgressBarView` nếu interface phù hợp, nếu không thì extend.
- [x] **4.4** Error handling end-to-end: `FileNotFoundError` → 1, Ollama lỗi → 2, IO error khi ghi Excel → 3.

### Phase 5: Quality Gates (M5)

- [x] **5.1** Unit tests:
  - `tests/services/test_map_vsic_to_mcc_use_case.py` (fake LLM + embedding clients).
  - `tests/services/test_mcc_code_validator.py`.
  - `tests/repositories/test_simple_mapping_xlsx_repository.py` (đọc lại xlsx, verify 3 cột).
  - `tests/repositories/test_detail_mapping_xlsx_repository.py` (verify 14 cột, 3 sheet giữ nguyên).
  - `tests/repositories/test_mapping_checkpoint_repository.py` (atomic write, resume).
  - `tests/controllers/test_mapping_controller.py` (exit codes).
- [x] **5.2** Integration smoke test: chạy full với 5 VSIC sample (monkey-patch Ollama client), verify Excel.
- [x] **5.3** `black app/ tests/`, `flake8 app/ tests/`, `mypy app/`.
- [x] **5.4** Cập nhật `README.md` — section `Map VSIC → MCC`, prerequisites Ollama + model pull.
- [x] **5.5** Điền `docs/ai/implementation/feature-mapping-vsic-mcc.md` và `docs/ai/testing/feature-mapping-vsic-mcc.md` trong khi code.

## Dependencies

- **Upstream features (must exist):**
  - `convert-vsic-excel-to-json` → sinh `output/vsic-vn.json`.
  - `convert-mcc-image-to-json` → sinh `output/mcc-visa.json`.
- **External:**
  - Ollama service running at `localhost:11434`.
  - Models pulled: `qwen2.5:14b` (~9GB), `bge-m3` hoặc `nomic-embed-text`.
- **Task ordering:** 1.x → 2.x → 3.x → 4.x → 5.x. Trong mỗi phase, test có thể viết song song với implement.

## Timeline & Estimates

| Phase | Effort | Dev days |
|---|---|---|
| 1 Foundation | S | 0.5 |
| 2 Infrastructure | M | 1.0 |
| 3 Use case | M | 1.0 |
| 4 CLI | S | 0.5 |
| 5 Tests + docs | M | 1.0 |
| **Total** | | **~4 dev days** |

Runtime ước lượng cho 1 lần chạy full: 2–3h trên M1 16GB.

## Risks & Mitigation

- **R1 — Qwen2.5:14b quá chậm trên M1 16GB (>30s/call):** Mitigation: giảm top-K xuống 5, rút description, hoặc thử `qwen2.5:7b`.
- **R2 — LLM hallucinate MCC code:** Mitigation: `MccCodeValidator` + fallback top-1 embedding. Test case bắt buộc.
- **R3 — Ollama chưa pull embedding model:** Mitigation: health check phase 2.3 → hướng dẫn command rõ ràng.
- **R4 — OOM khi load Qwen + embedding song song:** Mitigation: serialize gọi (1 Ollama process xử lý tuần tự); đặt `OLLAMA_MAX_LOADED_MODELS=1` trong README.
- **R5 — Schema `output/mcc-visa.json` thay đổi ở tương lai:** Mitigation: dùng pydantic parse với `extra=ignore`, fail-fast khi thiếu field bắt buộc.
- **R6 — Excel character encoding với tiếng Việt:** `openpyxl` hỗ trợ UTF-8 natively — đã verify qua feature convert-vsic.

## Resources Needed

- **Người:** 1 Python dev.
- **Máy:** MacBook Pro M1 16GB với Ollama + `qwen2.5:14b` + `bge-m3` đã pull.
- **Docs tham khảo:**
  - Ollama Python client: https://github.com/ollama/ollama-python
  - openpyxl docs.
  - `docs/ai/design/feature-convert-mcc-image-to-json.md` (pattern layering tương tự).
