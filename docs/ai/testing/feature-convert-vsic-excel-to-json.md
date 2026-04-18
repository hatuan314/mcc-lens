---
phase: testing
title: Testing Strategy — Convert VSIC Excel to JSON
description: Kế hoạch kiểm thử cho tính năng convert VSIC xlsx → JSON
---

# Testing Strategy

## Test Coverage Goals

- Unit test coverage: 100% cho `VsicParserService` và `VsicEntry`.
- Integration: controller với FakeRepository.
- E2E: chạy thật với `assets/vsic-vn/vsic.xlsx`.

## Unit Tests

### VsicParserService
- [ ] `test_detect_level_section`: code `"A"` → `"section"`
- [ ] `test_detect_level_division`: code `"01"` → `"division"`
- [ ] `test_detect_level_group`: code `"01.1"` → `"group"`
- [ ] `test_detect_level_class`: code `"01.11"` → `"class"`
- [ ] `test_parse_assigns_parent_code_correctly`: division kế sau section có `parent_code` = section code
- [ ] `test_parse_skips_empty_rows`: rows không có code bị bỏ qua
- [ ] `test_parse_returns_flat_list`: output là list, không phải nested dict

### VsicExcelRepository
- [ ] `test_read_rows_returns_list_of_dicts`: dùng file xlsx fixture nhỏ
- [ ] `test_read_rows_file_not_found`: raise `FileNotFoundError`

### VsicEntry (Pydantic)
- [ ] `test_vsic_entry_valid`: tạo entry hợp lệ thành công
- [ ] `test_vsic_entry_invalid_level`: level không hợp lệ raise `ValidationError`

## Integration Tests

- [ ] Controller với `FakeVsicRepository` (trả rows cứng) + `FakeVsicJsonRepository` (capture output)
- [ ] Kiểm tra output JSON có đủ 4 level và parent_code đúng

## End-to-End Tests

- [ ] Chạy CLI: `python3 main.py convert-vsic --input assets/vsic-vn/vsic.xlsx --output /tmp/vsic_test.json`
- [ ] Kiểm tra `/tmp/vsic_test.json` không rỗng, có entries ở đủ 4 levels

## Test Data

- Fixture xlsx nhỏ (tạo bằng openpyxl trong conftest) với ~10 rows đại diện 4 levels.
- Fixture rows dict (không cần file thật) cho unit test parser.

## Test Reporting & Coverage

```bash
pytest tests/test_vsic_*.py --cov=app --cov-report=term-missing
```

- Target: ≥ 90% coverage trên các file mới.

## Manual Testing

- [ ] Chạy thật với `vsic.xlsx` và review JSON output bằng mắt — kiểm tra mã đầu tiên và cuối cùng mỗi section.
