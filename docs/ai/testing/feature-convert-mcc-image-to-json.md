---
phase: testing
title: Testing Strategy - Convert MCC Image to JSON
description: Chiến lược kiểm thử cho pipeline Florence-2 → JSON, tập trung vào parser, use case và JSON repository; Florence-2 được mock trong unit test.
---

# Testing Strategy

## Test Coverage Goals
**Mức kiểm thử hướng tới:**

- Unit test coverage ≥ **80%** cho `app/services/mcc_parser_service.py`, `app/services/convert_mcc_images_use_case.py`, `app/repositories/mcc_json_repository.py` (mục tiêu lý tưởng 100% cho code mới/đổi).
- Integration test: 1 kịch bản end-to-end với **FakeVisionService** (không tải Florence-2) trên 2–3 ảnh mẫu.
- Smoke test thủ công: chạy thật CLI trên 5 ảnh `assets/mcc-visa/` (chỉ chạy khi máy có tài nguyên).
- Mọi acceptance criteria trong `docs/ai/requirements/feature-convert-mcc-image-to-json.md` phải có ít nhất một test đối chiếu.

## Unit Tests
**Các thành phần cần test:**

### MCCParserService (`tests/services/test_mcc_parser_service.py`)
- [ ] `parse_happy_path_single_mcc` — text chuẩn, 1 MCC → 1 entry đủ field.
- [ ] `parse_multiple_mcc_in_one_text` — text chứa 2+ MCC block → nhiều entry đúng thứ tự.
- [ ] `parse_missing_mcc_code_skips_entry` — không có 4-digit code → trả list rỗng + warning log.
- [ ] `parse_similar_merchants_split` — split đúng theo `,` và newline, strip whitespace.
- [ ] `parse_empty_similar_merchants` — không có section "Similar Merchants" → `similar_merchants = []`.
- [ ] `parse_noisy_text_graceful` — text rác, không crash.

### ConvertMCCImagesUseCase (`tests/services/test_convert_mcc_images_use_case.py`)
- [ ] `execute_batch_success` — 3 ảnh fake → ghi JSON chứa 3+ entry, progress được gọi đúng số lần.
- [ ] `execute_continues_on_image_failure` — ảnh 2 raise exception → ảnh 1, 3 vẫn được xử lý; log warning.
- [ ] `execute_deduplicates_by_mcc_code` — 2 ảnh trả về cùng `mcc_code` → output chỉ 1 entry.
- [ ] `execute_empty_input_dir` — không có ảnh → không ghi file hoặc ghi JSON rỗng (tuỳ quyết định).

### MCCJsonRepository (`tests/repositories/test_mcc_json_repository.py`)
- [ ] `save_creates_parent_dir` — output path có parent chưa tồn tại → được tạo.
- [ ] `save_utf8_non_ascii` — entry có tiếng Việt → ghi không escape ASCII (`ensure_ascii=False`).
- [ ] `save_overwrites_existing_file` — file đã tồn tại → bị ghi đè sạch.

### MCCImageRepository (`tests/repositories/test_mcc_image_repository.py`)
- [ ] `list_images_sorted` — trả danh sách đã sort, chỉ `.jpg/.jpeg/.png`.
- [ ] `list_images_missing_dir` — raise rõ ràng (FileNotFoundError).

### MCCEntry model (`tests/models/test_mcc_entry.py`)
- [ ] Validate các trường bắt buộc; `similar_merchants` mặc định `[]`.

## Integration Tests
**Test tương tác giữa thành phần:**

- [ ] `integration_pipeline_with_fake_vision` — Use Case + Parser + JsonRepo thật, Vision = FakeVisionService trả text fixture từ `tests/fixtures/florence2_outputs/*.txt`. Kiểm tra file JSON cuối khớp snapshot.
- [ ] `integration_cli_subcommand` — chạy `main.py convert-mcc` qua `subprocess` với fake service được inject (hoặc env var override); kiểm tra exit code = 0 và file JSON được tạo.
- [ ] `integration_error_reporting` — 1 ảnh gây parser trả rỗng → log có WARNING, exit code vẫn 0.

## End-to-End Tests
**Luồng người dùng thực:**

- [ ] **E2E-1 (manual, optional CI):** Chạy `python3 main.py convert-mcc --input-dir assets/mcc-visa --output out/mcc-visa.json` trên máy có Florence-2 → JSON hợp lệ, ≥ 90% ảnh có entry.
- [ ] **E2E-2:** Chạy với `--input-dir` rỗng → exit 0, log rõ ràng.
- [ ] **E2E-3 (regression):** Sau khi feature merged, chạy lại trên tập cũ → snapshot JSON không đổi (hoặc chỉ đổi field được dự kiến).

## Test Data
**Dữ liệu dùng cho test:**

- **Fixtures text giả lập output Florence-2:** `tests/fixtures/florence2_outputs/`:
  - `mcc_5411_grocery.txt` — 1 MCC đầy đủ.
  - `mcc_multiple.txt` — 3 MCC liên tiếp.
  - `mcc_noisy.txt` — header trang / chú thích không có MCC.
  - `mcc_missing_similar.txt` — không có similar merchants.
- **Ảnh test:** không cần bỏ ảnh thật vào test; dùng 1 ảnh nhỏ dummy để test `MCCImageRepository.list_images` (hoặc `tmp_path` fixture của pytest).
- **FakeVisionService**: class trong `tests/fakes/` đọc fixture theo tên file.

## Test Reporting & Coverage
**Báo cáo & ngưỡng:**

- Câu lệnh: `pytest --cov=app --cov-report=term-missing --cov-report=html tests/`
- Ngưỡng CI: fail nếu coverage toàn project < 80% hoặc coverage cho module `services/mcc_parser_service.py` < 90%.
- Ghi chú coverage gaps dự kiến: `florence2_vision_service.py` có thể < 50% vì cần GPU — được loại khỏi yêu cầu coverage hoặc test qua integration manual.
- Kết quả manual test smoke và snapshot JSON lưu ở PR description khi release.

## Manual Testing
**Cần con người kiểm tra:**

- [ ] Chạy CLI trên máy dev, quan sát progress bar cập nhật mượt.
- [ ] So khớp mẫu 3 MCC trong JSON với ảnh gốc (spot-check thủ công) để đánh giá chất lượng parse.
- [ ] Chạy trên CPU và (nếu có) GPU, so sánh thời gian.
- [ ] Terminal hỗ trợ Unicode hiển thị tên file tiếng Việt đúng.

## Performance Testing
**Kiểm định hiệu năng:**

- Đo thời gian xử lý mỗi ảnh (log `INFO`); ghi số liệu CPU vs GPU vào PR description.
- Không yêu cầu load test — dataset nhỏ (~vài chục ảnh).
- Benchmark tham khảo: ≤ 60s/ảnh CPU, ≤ 5s/ảnh GPU (không phải hard gate).

## Bug Tracking
**Quản lý issue:**

- Bug phát hiện trong QA được mở issue GitHub với label `feature:convert-mcc-image-to-json`.
- Mức độ: P0 (crash/mất data) — fix trước merge; P1 (parse sai 1 field) — fix trước release; P2 (cosmetic log) — backlog.
- Regression: giữ snapshot JSON của 5 ảnh VISA hiện tại, diff trong CI khi có thay đổi parser/Florence-2 config.
