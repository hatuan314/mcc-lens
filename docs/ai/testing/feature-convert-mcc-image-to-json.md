---
phase: testing
title: Testing Strategy - Convert MCC Image to JSON
description: Chiến lược kiểm thử cho pipeline Surya OCR → JSON, tập trung vào parser sub-components, use case và repositories; SuryaOCRService được tách ra khỏi unit test (cần model thật).
---

# Testing Strategy

## Test Coverage Goals
**Mức kiểm thử hướng tới:**

- Unit test coverage ≥ **80%** cho toàn bộ `app/` (ngoại trừ `surya_ocr_service.py` cần model thật).
- 100% coverage cho tất cả parser sub-components: `column_classifier`, `entry_grouper`, `mcc_entry_parser`, `mcc_table_parser_service`.
- 100% coverage cho `convert_mcc_images_use_case`, `mcc_json_repository`, `mcc_image_repository`, `checkpoint_repository`, `mcc_convert_controller`.
- Mọi acceptance criteria trong `docs/ai/requirements/feature-convert-mcc-image-to-json.md` phải có ít nhất một test đối chiếu.

## Current Status (2026-04-18)
**Trạng thái thực tế:**

| Module | Coverage | Test File |
|---|---|---|
| `column_classifier.py` | ✅ 100% | `test_column_classifier.py` |
| `entry_grouper.py` | ✅ 100% | `test_entry_grouper.py` |
| `mcc_entry_parser.py` | ✅ 100% | `test_mcc_entry_parser.py` |
| `mcc_table_parser_service.py` | ✅ 100% | `test_mcc_table_parser_service.py` |
| `convert_mcc_images_use_case.py` | ✅ 100% | `test_convert_mcc_images_use_case.py` |
| `mcc_json_repository.py` | ✅ 100% | `test_mcc_json_repository.py` |
| `mcc_image_repository.py` | ✅ 100% | `test_mcc_image_repository.py` |
| `checkpoint_repository.py` | ✅ 100% | `test_checkpoint_repository.py` |
| `mcc_convert_controller.py` | ✅ 100% | `test_mcc_convert_controller.py` |
| `mcc_entry.py` + `ocr_line.py` | ✅ 100% | `test_models.py` |
| `progress_bar_view.py` | ✅ 100% | `test_progress_bar_view.py` |
| `surya_ocr_service.py` | ⚠️ 0% | (manual smoke test) |
| **TOTAL** | **89%** | |

## Unit Tests
**Các thành phần cần test:**

### ColumnClassifier (`tests/test_column_classifier.py`)
- [x] `test_classify_mcc/desc/included/similar` — happy path cho 4 cột.
- [x] `test_classify_boundaries` — boundary values tại các ngưỡng %, bao gồm giá trị ngay tại threshold.
- [x] `test_zero_width_returns_unknown` — image_width = 0 → "unknown".
- [x] `test_negative_width_returns_unknown` — image_width < 0 → "unknown".
- [x] `test_x1_exceeds_width_returns_unknown` — x1 > image_width → "unknown".

### EntryGrouper (`tests/test_entry_grouper.py`)
- [x] `test_single_entry_with_all_columns` — 1 entry đủ 3 cột.
- [x] `test_multiple_entries_split_on_mcc_code` — nhiều entry tách đúng tại 4-digit token.
- [x] `test_last_entry_is_not_lost` — entry cuối không bị bỏ sót.
- [x] `test_lines_before_first_mcc_are_ignored` — dòng trước MCC code đầu tiên bị bỏ qua.
- [x] `test_empty_input_returns_empty` — list rỗng → list rỗng.
- [x] `test_non_mcc_code_in_mcc_column_ignored` — text ở cột mcc không phải 4 digit bị bỏ qua.
- [x] `test_unknown_column_is_dropped` — cột "unknown" bị bỏ qua.

### MCCEntryParser (`tests/test_mcc_entry_parser.py`)
- [x] `test_parse_valid_entry_all_fields` — đầy đủ 6 field, title/description tách đúng.
- [x] `test_single_desc_line_has_no_description` — chỉ 1 dòng desc → description = None.
- [x] `test_no_desc_lines_title_and_description_none` — không có desc → cả 2 None.
- [x] `test_empty_mcc_marks_unparsed` — mcc="" → `_unparsed=True`.
- [x] `test_title_continuation_across_lines` — title similar merchant bị cắt được nối.
- [x] `test_multiple_merchants` — nhiều similar merchants parse đúng.
- [x] `test_en_dash_and_hyphen_both_supported` — cả `–` và `-` đều nhận dạng.
- [x] `test_continuation_without_pending_is_dropped` — dòng continuation không có pending bị bỏ.
- [x] `test_filter_short_lines` — `included_in_mcc` lọc dòng ≤ 2 ký tự.
- [x] `test_empty_included_list` — included trống → list rỗng.

### MCCTableParserService (`tests/test_mcc_table_parser_service.py`)
- [x] `test_full_pipeline_happy_path` — integration 3 sub-components với OCRLine fixture mẫu.
- [x] `test_multiple_entries` — nhiều entry trong cùng image.
- [x] `test_empty_lines_returns_empty` — không có OCRLine → list rỗng.
- [x] `test_lines_before_first_mcc_ignored` — dòng trước MCC đầu bị bỏ.
- [x] `test_default_source_image_empty` — source_image default là "".

### ConvertMCCImagesUseCase (`tests/test_convert_mcc_images_use_case.py`)
- [x] `test_dedup_keeps_longer_description` — dedup giữ entry có description dài hơn.
- [x] `test_sort_by_mcc` — sort ascending by MCC code.
- [x] `test_unparsed_entries_preserved` — entry `_unparsed=True` không bị loại bỏ.
- [x] `test_resume_skips_processed_files` — resume bỏ qua ảnh có trong checkpoint.
- [x] `test_mark_done_called_after_each_image` — checkpoint được mark sau mỗi ảnh thành công.
- [x] `test_checkpoint_cleared_on_success` — checkpoint bị xóa khi pipeline hoàn thành.
- [x] `test_resume_matches_nfd_filesystem_names_with_nfc_checkpoint` — regression NFC/NFD.
- [x] `test_checkpoint_not_touched_when_resume_false` — resume=False không gọi checkpoint.
- [x] `test_image_processing_error_is_captured_in_result` — exception per-image được ghi vào errors list.

### MCCJsonRepository (`tests/test_mcc_json_repository.py`)
- [x] `test_output_schema` — wrapper object đúng (source, total_mcc_count, mcc_list).
- [x] `test_entry_has_six_fields` — MCCEntry serialized đủ 6 field.
- [x] `test_similar_merchants_serialized_as_dict` — `similar_merchants` là list dict (không phải string).
- [x] `test_creates_parent_directory` — tạo thư mục cha nếu chưa tồn tại.
- [x] `test_utf8_encoding` — nội dung tiếng Việt không bị escape ASCII.
- [x] `test_empty_list` — list rỗng → ghi JSON hợp lệ.

### MCCImageRepository (`tests/test_mcc_image_repository.py`)
- [x] `test_list_images_returns_sorted_jpg_files` — sắp xếp đúng tên.
- [x] `test_list_images_filters_non_image_files` — lọc đúng extension.
- [x] `test_list_images_includes_all_supported_extensions` — tất cả 6 extension được hỗ trợ.
- [x] `test_list_images_raises_for_missing_directory` — FileNotFoundError khi thư mục không tồn tại.
- [x] `test_list_images_raises_for_file_path` — NotADirectoryError khi truyền vào file.
- [x] `test_list_images_empty_directory_returns_empty` — thư mục trống → list rỗng.
- [x] `test_read_returns_pil_image` — `read()` trả PIL.Image.
- [x] `test_read_converts_to_rgb` — mode RGBA được convert sang RGB.

### CheckpointRepository (`tests/test_checkpoint_repository.py`)
- [x] `test_load_returns_empty_when_file_missing` — file chưa tồn tại → set rỗng.
- [x] `test_load_returns_nfc_normalized_names` — tên NFD được load về NFC.
- [x] `test_load_ignores_non_string_entries` — phần tử không phải string bị bỏ qua.
- [x] `test_load_handles_invalid_json_gracefully` — JSON hỏng → set rỗng, không crash.
- [x] `test_load_handles_non_list_json` — JSON object thay vì array → set rỗng.
- [x] `test_mark_done_persists_to_file` — ghi file sau mỗi `mark_done`.
- [x] `test_mark_done_accumulates_multiple_files` — nhiều `mark_done` tích lũy đúng.
- [x] `test_mark_done_normalizes_nfc` — tên NFD được lưu về NFC.
- [x] `test_mark_done_creates_parent_directory` — tạo thư mục cha nếu chưa tồn tại.
- [x] `test_clear_deletes_checkpoint_file` — `clear()` xóa file.
- [x] `test_clear_when_file_missing_does_not_raise` — `clear()` không raise khi file không tồn tại.
- [x] `test_clear_empties_internal_state` — `clear()` làm sạch internal state.
- [x] `test_clear_oserror_does_not_raise` — OSError trong `unlink` được xử lý gracefully.
- [x] `test_persist_oserror_does_not_raise` — OSError trong `write_text` được xử lý gracefully.

### MCCConvertController (`tests/test_mcc_convert_controller.py`)
- [x] `test_success_returns_zero` — exit code 0 khi thành công.
- [x] `test_file_not_found_returns_one` — exit code 1 khi thư mục input không tồn tại.
- [x] `test_infrastructure_error_surya_returns_two` — exit code 2 khi "surya" trong error message.
- [x] `test_infrastructure_error_model_returns_two` — exit code 2 khi "model" trong error message.
- [x] `test_io_permission_error_returns_three` — exit code 3 khi "permission" trong error message.
- [x] `test_io_disk_error_returns_three` — exit code 3 khi "disk" trong error message.
- [x] `test_generic_exception_returns_one` — exit code 1 cho exception không phân loại được.
- [x] `test_success_with_errors_still_returns_zero` — per-image errors không làm tăng exit code.

### ProgressBarView (`tests/test_progress_bar_view.py`)
- [x] `test_context_manager_enters_and_exits` — context manager hoạt động.
- [x] `test_update/set_description/set_postfix_without_context_does_not_raise` — no-op khi chưa dùng context.
- [x] `test_set_description/set_postfix/update_increments_inside_context` — hoạt động đúng trong context.
- [x] `test_iterate_returns_iterable` — static method `iterate` wraps tqdm đúng.

## Integration Tests
**Test tương tác giữa thành phần:**

- [ ] `integration_pipeline_with_fake_ocr` — UseCase + TableParser + JsonRepo thật, OCR = FakeOCRService. Kiểm tra file JSON cuối khớp schema.
- [ ] `integration_cli_subcommand` — chạy `main.py convert-mcc` qua `subprocess` với injected fakes; kiểm tra exit code = 0 và file JSON được tạo.

## End-to-End Tests
**Luồng người dùng thực:**

- [ ] **E2E-1 (manual):** Chạy `python3 main.py convert-mcc --input-dir assets/mcc-visa --output out/mcc-visa.json` → JSON hợp lệ, ≥ 90% ảnh có entry.
- [ ] **E2E-2:** Chạy với `--input-dir` rỗng → exit 0, log rõ ràng.
- [ ] **E2E-3 (resume regression):** Seed 4 ảnh vào checkpoint → pipeline chỉ xử lý ảnh còn lại, clear checkpoint khi xong. *(Confirmed smoke run 2026-04-18)*

## Test Data
**Dữ liệu dùng cho test:**

- `pytest` `tmp_path` fixture cho tất cả file I/O (không cần fixtures directory tách biệt).
- `FakeOCRService`, `FakeTableParser`, `FakeImageRepository`, `InMemoryCheckpointRepository` — fakes cho ConvertMCCImagesUseCase.
- `Image.new("RGB", ...)` — ảnh placeholder cho MCCImageRepository.

## Excluded from Coverage
**Không yêu cầu coverage:**

- `app/services/surya_ocr_service.py` (0%) — cần load model Surya ~1-2GB từ HuggingFace; chỉ test thủ công khi smoke run.
- `app/config.py` line 42 — env var validation path.

## Test Reporting & Coverage
**Báo cáo & ngưỡng:**

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html tests/
```

- **Ngưỡng thực tế đạt được:** 89% tổng (loại `surya_ocr_service.py` → ~100% cho phần còn lại).
- **Mục tiêu CI:** fail nếu coverage < 80%.
- 95 tests, runtime < 1s.

## Manual Testing
**Cần con người kiểm tra:**

- [ ] Chạy CLI trên máy dev, quan sát progress bar cập nhật mượt.
- [ ] So khớp 3 MCC mẫu trong JSON với ảnh gốc (spot-check thủ công).
- [ ] Chạy trên CPU và Apple M1/M2 MPS, so sánh thời gian xử lý.
- [ ] Terminal hiển thị tên file tiếng Việt (NFD/NFC) đúng.

## Performance Testing
**Kiểm định hiệu năng:**

- Đo thời gian mỗi ảnh qua log `INFO`; benchmark tham khảo: ≤ 60s/ảnh CPU, nhanh hơn nhiều trên MPS.
- Không yêu cầu load test — dataset ~27 ảnh VISA.

## Bug Tracking
**Quản lý issue:**

- Bug phát hiện trong QA: mở issue GitHub với label `feature:convert-mcc-image-to-json`.
- P0 (crash/mất data) — fix trước merge; P1 (parse sai 1 field) — fix trước release; P2 (cosmetic log) — backlog.
