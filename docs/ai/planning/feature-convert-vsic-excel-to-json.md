---
phase: planning
title: Project Planning & Task Breakdown — Convert VSIC Excel to JSON
description: Phân chia tasks và thứ tự triển khai cho tính năng convert VSIC xlsx → JSON
---

# Project Planning & Task Breakdown

## Milestones

- [x] Milestone 1: Foundation — models + protocols + dependency
- [x] Milestone 2: Core pipeline — parser + repositories
- [x] Milestone 3: CLI integration + end-to-end test

## Task Breakdown

### Phase 1: Foundation
- [x] Task 1.1: Thêm `openpyxl` vào `requirements.txt`
- [x] Task 1.2: Tạo `app/models/vsic_entry.py` — Pydantic model `VsicEntry` (code, title, level, parent_code, description)
- [x] Task 1.3: Thêm `VsicRepository` và `VsicParser` protocols vào `app/services/protocols.py`

### Phase 2: Core Features (thứ tự bắt buộc)
- [x] Task 2.1: Tạo `app/repositories/vsic_excel_repository.py` — đọc rows từ xlsx bằng openpyxl
- [x] Task 2.2: Tạo `app/services/vsic_parser_service.py` — detect level từ code format, build flat list `VsicEntry`
- [x] Task 2.3: Tạo `app/repositories/vsic_json_repository.py` — ghi list VsicEntry ra JSON
- [x] Task 2.4: Tạo `app/controllers/vsic_controller.py` — wire repository + service + output

### Phase 3: CLI & Integration
- [x] Task 3.1: Đăng ký subcommand `convert-vsic` trong `main.py` với argparse (`--input`, `--output`)
- [x] Task 3.2: Kiểm tra end-to-end: chạy với file thật `assets/vsic-vn/vsic.xlsx`

### Phase 4: Tests
- [x] Task 4.1: Unit test `VsicParserService` với fixture rows (các cấp section/division/group/class)
- [x] Task 4.2: Unit test `VsicExcelRepository` với file xlsx mẫu nhỏ
- [x] Task 4.3: Integration test controller với FakeRepository

## Dependencies

- Task 1.2, 1.3 phải xong trước Phase 2
- Task 2.1, 2.2, 2.3 độc lập nhau nhưng phải xong trước 2.4
- Task 2.4 phải xong trước 3.1

## Timeline & Estimates

| Phase | Ước lượng |
|-------|-----------|
| Phase 1 | 30 phút |
| Phase 2 | 1–1.5 giờ |
| Phase 3 | 30 phút |
| Phase 4 | 1 giờ |

## Risks & Mitigation

| Rủi ro | Khả năng | Mitigation |
|--------|----------|------------|
| Cấu trúc cột xlsx không như dự đoán | Trung bình | Inspect file thực tế ở Task 2.1 trước khi code parser |
| Merged cells trong xlsx gây openpyxl đọc sai | Thấp | Dùng `data_only=True` + unmerge strategy |
| Level detection regex sai với mã đặc biệt | Thấp | Viết unit test với nhiều mẫu code |

## Resources Needed

- `openpyxl` library
- File `assets/vsic-vn/vsic.xlsx` (đã có)
- Template pytest fixtures cho xlsx test
