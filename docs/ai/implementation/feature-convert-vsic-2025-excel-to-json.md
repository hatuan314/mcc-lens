---
phase: implementation
title: Implementation Guide — Convert VSIC 2025 Excel to JSON
description: Ghi chú triển khai convert-vsic-2025, nested schema, output/vsic-vn.json
---

# Implementation Guide

## Development Setup
**How do we get started?**

- Prerequisites and dependencies:
  - Dự án đã có môi trường Python; dùng `python3` cho mọi lệnh.
  - Dùng lại thư viện đọc Excel hiện tại của project.
- Environment setup steps:
  - Cài dependencies: `pip install -r requirements.txt`.
  - Kiểm tra file input tồn tại: `assets/vsic-vn/vsic-2025.xlsx`.
- Configuration needed:
  - Không cần thêm env var mới cho feature này.

## Code Structure
**How is the code organized?**

- Directory structure:
  - `app/repositories/` đọc dữ liệu xlsx.
  - `app/services/` parse/normalize dữ liệu.
  - `app/controllers/` điều phối luồng convert.
  - `app/views/` hiển thị/log kết quả CLI.
- Module organization:
  - Module riêng `Vsic2025*`; không sửa `VsicParserService` / `convert-vsic`.
- Naming conventions:
  - Giữ naming hiện có theo prefix `Vsic...`.

## Implementation Notes
**Key technical details to remember:**

### Core Features (Đã triển khai)
- ✅ Feature 1: CLI `convert-vsic-2025` (default → `output/vsic-vn.json`).
- ✅ Feature 2: Parse row cấp 4/5 từ cột D/E; gom `children_level5`.
- ✅ Feature 3: JSON nested tối thiểu; `map-vsic-mcc` chỉ đọc entry cấp 4.

### Files Created
| File | Purpose |
|------|---------|
| `app/models/vsic_2025_entry.py` | Pydantic models: `VsicLevel5Child`, `Vsic2025Entry`, `Vsic2025Output` |
| `app/repositories/vsic_2025_excel_repository.py` | Read Excel with header validation |
| `app/repositories/vsic_2025_json_repository.py` | Write nested JSON wrapper |
| `app/services/vsic_2025_row_normalizer.py` | Row type detection (level 4 vs 5) |
| `app/services/vsic_2025_parser_service.py` | Group level 5 into level 4 entries |
| `app/controllers/vsic_2025_controller.py` | Orchestration with exit codes |

### Key Implementation Detail
- Row vừa có Cấp 4 và Cấp 5: tạo entry cấp 4 và thêm child từ cùng row (`extra_level_5`).
- Code chuẩn hóa luôn là string, không zero-pad (giữ nguyên như Excel).
- Dữ liệu thật: 496 level-4 entries, 744 level-5 children tổng cộng.

### Patterns & Best Practices
- Design patterns being used:
  - Service + Repository + Protocol theo Clean Architecture.
- Code style guidelines:
  - Type hints đầy đủ, hàm nhỏ, dễ test.
- Common utilities/helpers:
  - Tách helper `normalize_row_2025` để unit test độc lập.

## Integration Points
**How do pieces connect?**

- API integration details:
  - CLI `convert-vsic` là điểm vào.
- Database connections:
  - Không dùng DB.
- Third-party service setup:
  - Không có third-party service.

## Error Handling
**How do we handle failures?**

- Error handling strategy:
  - Lỗi mở file/header không hợp lệ: fail fast với message rõ ràng.
  - Row lỗi dữ liệu: skip + warning.
- Logging approach:
  - Log số row parse thành công/thất bại.
- Retry/fallback mechanisms:
  - Không retry I/O; fail ngay để tránh output sai.

## Performance Considerations
**How do we keep it fast?**

- Optimization strategies:
  - Parse tuyến tính theo row, không build cấu trúc cây trung gian nặng.
- Caching approach:
  - Không cần cache.
- Query optimization:
  - Không áp dụng.
- Resource management:
  - Đọc workbook một lần, giải phóng object sau khi parse.

## Security Notes
**What security measures are in place?**

- Authentication/authorization:
  - Không áp dụng.
- Input validation:
  - Validate path input, validate header bắt buộc.
- Data encryption:
  - Không áp dụng cho file local.
- Secrets management:
  - Không dùng secrets mới.

