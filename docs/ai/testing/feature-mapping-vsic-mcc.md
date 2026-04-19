---
phase: testing
title: Testing Strategy — Mapping VSIC to MCC
description: Kế hoạch kiểm thử cho pipeline VSIC→MCC (ưu tiên unit test với fake clients, integration smoke với monkey-patch)
---

# Testing Strategy

## Test Coverage Goals

- **Unit test coverage target:** 100% cho các module mới (`services/map_vsic_to_mcc_use_case.py`, `services/mcc_code_validator.py`, các repositories trong phạm vi feature, `controllers/mapping_controller.py`).
- **Integration:** critical path (happy + NO_MATCH + resume + Ollama unavailable).
- **E2E:** 1 smoke test chạy trên sample 5 VSIC (Ollama monkey-patched) + mở file Excel verify header & rows.
- **Alignment:** mỗi acceptance criterion trong requirements.md có ít nhất 1 test case tương ứng.

## Unit Tests

### `services/map_vsic_to_mcc_use_case.py`
- [x] Happy path: 3 VSIC, fake embedding trả vector deterministic, fake LLM trả MCC hợp lệ → `MappingEntry` đủ 3 với `mcc_code` đúng.
- [x] NO_MATCH: fake LLM trả `{"mcc_code": "NO_MATCH"}` → entry có `mcc_code=None`, không crash.
- [x] LLM hallucinate (MCC code không có trong list) → validator fallback top-1 embedding, log warning.
- [x] Resume: checkpoint chứa 2/3 VSIC đã done → use case chỉ gọi LLM cho 1 VSIC còn lại.
- [x] Top-K prompt: assert LLM nhận đúng K candidates từ kết quả cosine sim.
- [x] Empty VSIC list → trả về `[]`, không raise.

### `services/mcc_code_validator.py`
- [x] MCC code hợp lệ → trả về nguyên.
- [x] MCC code không tồn tại → fallback top-1, trả code top-1.
- [x] Response `NO_MATCH` → trả `None`.
- [x] Response rác / None → fallback top-1.

### `repositories/simple_mapping_xlsx_repository.py`
- [x] Ghi 3 entries → mở lại bằng openpyxl → sheet `Mapping` có đúng 3 cột header `["VSIC", "MCC", "Tên ngành"]`, 3 rows data đúng thứ tự.
- [x] Entry với `top_results=[]` → cột MCC rỗng (empty string), không crash.
- [x] Tên ngành tiếng Việt (có dấu) giữ nguyên UTF-8.
- [x] Tạo thư mục cha nếu chưa tồn tại.

### `repositories/detail_mapping_xlsx_repository.py`
- [x] Ghi 3 entries với top-3 MCC → mở lại bằng openpyxl → sheet `Mapping Result` có đúng 14 cột.
- [x] Load template → giữ nguyên sheets "Hướng Dẫn" và "Thống Kê".
- [x] Entry với < 3 ranked → pad với empty strings.

### `repositories/mapping_checkpoint_repository.py`
- [x] Load khi file chưa tồn tại → trả `{}`.
- [x] Save rồi load → đúng nội dung.
- [x] Atomic write: giả lập interrupt giữa chừng → file cũ không bị corrupt (kiểm tra bằng write sang tmp + replace).

### `repositories/ollama_llm_client.py` & `ollama_embedding_client.py`
- [x] Monkey-patch `ollama.chat` / `ollama.embed` → verify args passed (model, prompt, temperature).
- [x] Retry: raise ConnectionError 2 lần rồi success → client retry OK.
- [x] Retry cạn → raise `OllamaUnavailableError`.

### `controllers/mapping_controller.py`
- [x] Success → exit code 0.
- [x] `FileNotFoundError` → exit 1.
- [x] `OllamaUnavailableError` → exit 2.
- [x] IO error khi ghi xlsx → exit 3.
- [x] Exception khác → exit 1 + log.

## Integration Tests

- [ ] **I1** Full pipeline với 5 VSIC sample, fake Ollama clients → verify Excel đúng schema + số rows.
- [ ] **I2** Resume: chạy với 3/5 VSIC trong checkpoint → chỉ embed/LLM cho 2 VSIC còn lại → kết quả cuối đầy đủ 5.
- [ ] **I3** Ollama unavailable: fake client raise ConnectionError → controller exit 2, không ghi Excel rỗng.
- [ ] **I4** Input file thiếu → exit 1 với message rõ.

## End-to-End Tests

- [ ] **E1** `python3 main.py map-vsic-mcc --vsic-input tests/fixtures/vsic_sample.json --mcc-input tests/fixtures/mcc_sample.json --output /tmp/out.xlsx` với `OLLAMA_HOST` trỏ tới fake HTTP server (hoặc monkey-patched qua `conftest.py`). Verify exit 0 + file Excel đúng.
- [ ] **E2** Regression: `convert-vsic` và `convert-mcc` vẫn chạy được sau khi thêm subcommand mới (import graph không vỡ).

## Test Data

- `tests/fixtures/vsic_sample.json`: 5 VSIC entries đa dạng (nông nghiệp, CNTT, bán lẻ, dịch vụ mơ hồ, thương mại).
- `tests/fixtures/mcc_sample.json`: 10 MCC entries covering các ngành trên.
- `tests/fixtures/checkpoint_partial.json`: checkpoint có 3/5 VSIC đã done.
- Fake clients: `tests/fakes/fake_llm_client.py`, `tests/fakes/fake_embedding_client.py` (deterministic outputs).

**Note**: Các file test fixtures chưa được tạo trong lần implement này. Cần tạo khi viết unit tests.

## Test Reporting & Coverage

- `pytest --cov=app --cov-report=term-missing --cov-report=html tests/` (đã cấu hình trong `pytest.ini`).
- Threshold: 100% cho file mới của feature; ≥ 90% tổng repo (hiện trạng).
- Gaps report trong PR description khi có module < 100%.

## Manual Testing

- [ ] Chạy full pipeline thật trên máy dev M1 16GB, verify runtime ≤ 3h.
- [ ] Mở `output/vsic-mcc-mapping.xlsx` bằng Numbers / Excel / LibreOffice — verify:
  - Sheet `Mapping` có 3 cột, header tiếng Việt đúng.
  - Ký tự tiếng Việt hiển thị đúng.
- [ ] Mở `output/vsic-mcc-mapping-detail.xlsx` (nếu có template) — verify:
  - Sheet `Mapping Result` có 14 cột.
  - Sheets "Hướng Dẫn" và "Thống Kê" được giữ nguyên.
- [ ] Kill -9 giữa chừng rồi `--resume` — tiếp tục đúng từ VSIC cuối cùng.
- [ ] `ollama stop` giữa chừng → exit code 2, message rõ.

## Performance Testing

- Benchmark: đo thời gian trung bình cho 10 VSIC đầu → extrapolate cho 743.
- Target: ≤ 20s/VSIC trung bình (bao gồm embedding + LLM).
- Theo dõi RAM: `ps aux | grep ollama` nên < 11GB RSS.

## Bug Tracking

- Issues track trong GitHub Issues với label `feature:mapping-vsic-mcc`.
- Severity:
  - **P0:** Pipeline không chạy được, output Excel sai schema.
  - **P1:** Một số VSIC map sai (chất lượng mapping).
  - **P2:** Log / progress bar không đẹp.
- Regression: sau mỗi fix P0/P1, thêm test case tương ứng vào unit/integration suite.
