---
phase: testing
title: Testing Strategy — Convert VSIC 2025 Excel to JSON
description: Kế hoạch kiểm thử parser VSIC 2025 và đảm bảo output không phá vỡ contract downstream
---

# Testing Strategy

## Test Coverage Goals
**What level of testing do we aim for?**

- Unit test coverage target (default: 100% of new/changed code)
- Integration test scope (critical paths + error handling)
- End-to-end test scenarios (key user journeys)
- Alignment with requirements/design acceptance criteria

## Unit Tests
**What individual components need testing?**

### Component: vsic_2025_row_normalizer
- [x] Test case 1: Detect đúng level từ các cột `Cấp 1..5` (covers scenario / branch)
  - File: `tests/test_vsic_2025_row_normalizer.py::TestNormalizeRow2025`
  - 14 tests: row_with_cap4_only, row_with_cap5_only, row_with_both_cap4_and_cap5, etc.
- [x] Test case 2: Xử lý row thiếu code hoặc title (covers edge case / error handling)
  - Tests: row_without_cap4_or_cap5_returns_none, completely_empty_row, row_with_none_values
- [x] Additional coverage: Chuẩn hóa `code` luôn là string
  - File: `tests/test_vsic_2025_row_normalizer.py::TestNormalizeCode`
  - 12 tests: integer_value, float_whole_number, string_integer, etc.
- **Coverage: 91%** (missing: warning log branches at lines 67-68, 88-89)

### Component: vsic_2025_parser_service
- [x] Test case 1: Gom `children_level5` đúng vào cấp 4 gần nhất
  - File: `tests/test_vsic_2025_parser_service.py::TestParseRowsChildGrouping`
  - 4 tests: level_5_grouped_under_level_4, multiple_level_4_with_children, etc.
- [x] Test case 2: Xử lý row với cả Cấp 4 và Cấp 5 (inline child)
  - File: `tests/test_vsic_2025_parser_service.py::TestParseRowsInlineChild`
  - 3 tests: inline_level_5_child, inline_child_plus_subsequent_children, inline_child_uses_same_title
- [x] Additional coverage: Output không chứa `level`/`parent_code`/`description`
  - File: `tests/test_vsic_2025_parser_service.py::TestParseRowsOutputSchema`
  - 5 tests: no_level_field, no_parent_code_field, no_description_field, etc.
- **Coverage: 74%** (missing: unused private helper methods _extract_level_4_code, _extract_level_5_code, _extract_title)

### Component: vsic_2025_excel_repository
- [x] Test case: Header validation
  - File: `tests/test_vsic_2025_excel_repository.py::TestValidateHeaders`
  - 8 tests: valid_headers, minimum_required_headers, missing_cap4/cap5/ten_nganh, etc.
- [x] Test case: Read rows with mocked workbook
  - File: `tests/test_vsic_2025_excel_repository.py::TestReadRowsWithMockedWorkbook`
  - 5 tests: valid_data, empty_rows_skipped, workbook_closed, etc.
- **Coverage: 100%**

### Component: vsic_2025_json_repository
- [x] Test case: Write entries
  - File: `tests/test_vsic_2025_json_repository.py::TestWriteEntries`
  - 11 tests: creates_output_file, creates_parent_directories, source_field, total_vsic_count, etc.
- [x] Test case: Schema compliance
  - File: `tests/test_vsic_2025_json_repository.py::TestOutputSchemaCompliance`
  - 3 tests: no_extra_fields_in_entry, no_extra_fields_in_child, root_level_fields
- **Coverage: 100%**

### Component: vsic_2025_controller
- [x] Test case: Exit codes
  - File: `tests/test_vsic_2025_controller.py::TestVsic2025ControllerExitCodes`
  - 6 tests: success_returns_zero, file_not_found, value_error, io_error, etc.
- [x] Test case: Pipeline
  - File: `tests/test_vsic_2025_controller.py::TestVsic2025ControllerPipeline`
  - 5 tests: excel_repo_receives_path, parser_receives_rows, json_repo_receives_entries, etc.
- [x] Test case: Integration with real parser
  - File: `tests/test_vsic_2025_controller.py::TestVsic2025ControllerIntegration`
  - 2 tests: full_pipeline_with_sample_data, entry_with_inline_child
- **Coverage: 100%**

## Integration Tests
**How do we test component interactions?**

- [x] Integration scenario 1: Controller + repository + parser + json writer chạy full pipeline
  - File: `tests/test_vsic_2025_controller.py::TestVsic2025ControllerIntegration::test_full_pipeline_with_sample_data`
  - Verified: 496 entries, 744 children
- [x] Integration scenario 2: Input header sai -> trả lỗi rõ ràng
  - File: `tests/test_vsic_2025_excel_repository.py::TestReadRowsWithMockedWorkbook::test_invalid_headers_raises_value_error`
  - Verified: Raises `ValueError` with missing headers message
- [x] Integration scenario 3: Parse rows with inline children
  - File: `tests/test_vsic_2025_controller.py::TestVsic2025ControllerIntegration::test_entry_with_inline_child`
  - Verified: Inline level 5 child correctly attached
- [ ] Integration scenario 4 (failure mode): parse có row lỗi nhưng vẫn ghi output hợp lệ
  - TODO: Thêm test cho row lỗi xen kẽ

## End-to-End Tests
**What user flows need validation?**

- [x] User flow 1: `python3 main.py convert-vsic-2025` → `output/vsic-vn.json`
  - Verified: Exit code 0, file tạo thành công
- [x] User flow 2: chạy với `--output` custom path
  - Verified: `--output /tmp/test.json` ghi file đúng path
- [x] Critical path testing: so sánh schema output với contract
  - Verified: 11/11 contract checks pass (source, total_vsic_count, vsic_list structure)
- [x] Regression: `convert-vsic` với `vsic.xlsx` không đổi hành vi
  - Verified: 743 entries, output/vsic.json giữ nguyên format cũ
- [ ] Regression: `map-vsic-mcc` đọc output 2025
  - TODO: Test `map-vsic-mcc` với `output/vsic-vn.json` sau khi có file

## Test Data
**What data do we use for testing?**

- Test fixtures and mocks:
  - `FakeExcelRepository`: Mock Excel reader with configurable rows/errors
  - `FakeJsonRepository`: Mock JSON writer capturing saved entries
  - `FakeParserService`: Mock parser returning configurable entries
  - Mocked `openpyxl.load_workbook` for repository tests
- Seed data requirements:
  - Inline dictionaries mimic Excel rows with Cấp 4/5/Tên ngành
  - Sample entries with various child configurations
- Test database setup:
  - Không cần DB — file-based mocks only

## Test Reporting & Coverage
**How do we verify and communicate test results?**

- Coverage commands and thresholds (`npm run test -- --coverage`)
  - Dùng lệnh: `pytest tests/test_vsic_2025*.py --cov=app --cov-report=term-missing`
- Coverage summary (VSIC 2025 modules):
  | Module | Coverage | Missing |
  |--------|----------|---------|
  | `vsic_2025_controller.py` | 100% | — |
  | `vsic_2025_excel_repository.py` | 100% | — |
  | `vsic_2025_json_repository.py` | 100% | — |
  | `vsic_2025_entry.py` | 100% | — |
  | `vsic_2025_parser_service.py` | 74% | Private helper methods unused |
  | `vsic_2025_row_normalizer.py` | 91% | Warning log branches |
- Coverage gaps rationale:
  - `vsic_2025_parser_service.py`: Lines 95-112 are private helpers (`_extract_level_4_code`, etc.) not called by current implementation (logic moved to normalizer).
  - `vsic_2025_row_normalizer.py`: Lines 67-68, 88-89 are `logger.warning` calls for empty code after normalization — edge case not triggered in normal data.
- Links to test reports or dashboards
  - HTML coverage: `htmlcov/index.html`
- Manual testing outcomes and sign-off
  - Verified: `convert-vsic-2025` → 496 entries, 744 children, schema compliant

## Manual Testing
**What requires human validation?**

- UI/UX testing checklist (include accessibility)
  - Không áp dụng.
- Browser/device compatibility
  - Không áp dụng.
- Smoke tests after deployment
  - Chạy `convert-vsic-2025`; xác nhận `map-vsic-mcc` với `output/vsic-vn.json`.

## Performance Testing
**How do we validate performance?**

- Load testing scenarios
  - Parse file ~1,000 rows nhiều lần liên tiếp.
- Stress testing approach
  - Tăng kích thước fixture để kiểm tra tuyến tính thời gian xử lý.
- Performance benchmarks
  - Target < 3 giây cho dữ liệu thật trên máy dev.

## Bug Tracking
**How do we manage issues?**

- Issue tracking process
  - Log bug theo template issue của repo.
- Bug severity levels
  - Sai schema output được xem là critical.
- Regression testing strategy
  - Re-run test suite VSIC parser sau mỗi thay đổi parser/repository.

