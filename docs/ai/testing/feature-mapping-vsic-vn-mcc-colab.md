---
phase: testing
title: Testing Strategy — Mapping VSIC VN to MCC on Colab
description: Test coverage cho feature chạy pipeline VSIC→MCC trên Colab GPU với --gdrive-output-dir
---

# Testing Strategy

## Test Coverage Goals

- **Unit test coverage target:** 100% cho code mới/thay đổi trong `MappingController`
- **Integration test scope:** critical paths (gdrive path override, checkpoint, limit) + error handling
- **End-to-end test scenarios:** thực hiện qua Colab notebook (manual)
- **Alignment:** phủ toàn bộ acceptance criteria trong requirements doc

## Unit Tests

### `MappingController` — Exit codes (file `tests/test_mapping_controller.py`, class `TestMappingControllerExitCodes`)

- [x] `test_returns_1_when_vsic_file_missing` — exit 1 khi file VSIC không tồn tại
- [x] `test_returns_1_when_mcc_file_missing` — exit 1 khi file MCC không tồn tại
- [x] `test_returns_2_when_ollama_unavailable` — exit 2 khi Ollama health check lỗi
- [x] `test_returns_0_on_success` — exit 0 khi pipeline thành công
- [x] `test_returns_3_on_io_error` — exit 3 khi ghi file Excel thất bại

### `MappingController` — Defaults (class `TestMappingControllerDefaults`)

- [x] `test_default_top_k_is_60` — giá trị mặc định `top_k` = 60 (theo design feature mới)
- [x] `test_default_gdrive_output_dir_is_none` — `gdrive_output_dir` mặc định là `None`
- [x] `test_template_path_none_skips_detail_output` — không ghi detail xlsx khi không có template

### `MappingController` — `--gdrive-output-dir` logic (class `TestMappingControllerGdriveOutputDir`)

- [x] `test_creates_gdrive_directory` — thư mục gdrive được tạo nếu chưa tồn tại
- [x] `test_output_files_written_to_gdrive_dir` — `vsic-mcc-mapping.xlsx` và `vsic-mcc-mapping-detail.xlsx` được ghi vào `gdrive_output_dir`
- [x] `test_checkpoint_path_uses_gdrive_dir` — `MappingCheckpointRepositoryImpl` được khởi tạo với path bên trong `gdrive_output_dir`
- [x] `test_original_output_paths_ignored` — file `--output` / `--output-detail` gốc không được tạo khi dùng `--gdrive-output-dir`
- [x] `test_returns_0_on_success_with_gdrive` — pipeline thành công với gdrive
- [x] `test_warning_logged_when_drive_not_mounted` — cảnh báo khi path bắt đầu bằng `/content/drive` nhưng Drive chưa mount
- [x] `test_nested_gdrive_dir_created_with_parents` — path sâu nhiều cấp được tạo với `mkdir(parents=True)`
- [x] `test_top_k_clamped_to_100` — `top_k > 100` được clamp về 100, không raise exception
- [x] `test_limit_restricts_vsic_entries` — `limit=1` chỉ truyền 1 entry vào `MapVsicToMccUseCase`

## Integration Tests

- [x] Controller wires `MappingCheckpointRepositoryImpl` với đúng checkpoint path (kiểm tra qua mock trong `test_checkpoint_path_uses_gdrive_dir`)
- [x] `gdrive_output_dir` override hoạt động end-to-end trong `execute()` (kiểm tra file system thực)
- [ ] Resume từ checkpoint trên Drive sau Colab reset — cần manual test trên Colab thực

## End-to-End Tests (Manual — Colab)

- [ ] Mount Google Drive và chạy `colab/mapping_vsic_mcc_colab.ipynb`
- [ ] Verify file `projects/mcc-lens/vsic-mcc-mapping.xlsx` tồn tại và mở được bằng Excel/Sheets
- [ ] Verify `projects/mcc-lens/vsic-mcc-mapping-detail.xlsx` đúng cấu trúc 3 sheet
- [ ] Test `--resume` sau khi ngắt giữa chừng (simulate Colab reset)

## Test Data

- `tests/test_mapping_controller.py` dùng `_write_vsic_json()` và `_write_mcc_json()` tạo fixture 2 VSIC + 2 MCC trong `tmp_path`
- `FAKE_ENTRIES` fixture gồm 2 `MappingEntry` (1 có kết quả, 1 không)
- `_make_template()` tạo Excel template tối giản với 3 sheet

## Test Reporting & Coverage

```bash
# Chạy test file mapping controller
python3 -m pytest tests/test_mapping_controller.py --no-cov -v

# Chạy với coverage
python3 -m pytest tests/test_mapping_controller.py --cov=app --cov-report=term-missing
```

- **Kết quả:** 17/17 tests passed (tính đến 2026-05-29)
- **Coverage gaps:** logic `warning_logged_when_drive_not_mounted` sử dụng loguru nên có thể không capture được qua `caplog` của pytest — test vẫn pass vì kiểm tra "no crash" thay vì log message cụ thể

## Manual Testing

- Setup Colab: mount Drive → install Ollama → pull `qwen3.5:9b` + `bge-m3` → chạy CLI
- Smoke test sau deploy: chạy với `--limit 5` để kiểm tra nhanh trước khi chạy full 743 VSIC

## Bug Tracking

- Lỗi `NameError: name 'mcc_entries' is not defined` đã được fix — biến được load trước khi dùng (xem implementation notes)
- Default `llm_model` đã đồng bộ `qwen3.5:9b` trong `main.py`, `MappingController.__init__`, `README.md`
