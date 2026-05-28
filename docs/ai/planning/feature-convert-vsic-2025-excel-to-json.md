---
phase: planning
title: Project Planning & Task Breakdown — Convert VSIC 2025 Excel to JSON
description: Kế hoạch triển khai parser format VSIC 2025 và giữ tương thích output cho downstream
---

# Project Planning & Task Breakdown

## Milestones
**What are the major checkpoints?**

- [x] Milestone 1: Xác nhận format đầu vào 2025 + chốt quy tắc nested (stakeholder decisions)
- [x] Milestone 2: Hoàn thành code parser/repository cho `vsic-2025.xlsx`
  - 6 files mới tạo, CLI `convert-vsic-2025` hoạt động
- [x] Milestone 3: Hoàn thành test (unit + integration) và verify output contract
  - Manual verification pass, 11/11 contract checks pass, regression tests pass

## Task Breakdown
**What specific work needs to be done?**

### Phase 1: Foundation
- [x] Task 1.1: Inspect workbook `vsic-2025.xlsx`, xác nhận header cột và các pattern.
  - Header: `Cấp 1..Cấp 5`, `Tên ngành` | 1067 data rows | 496 level-4 entries | 744 level-5 children
- [x] Task 1.2: Cập nhật requirement kỹ thuật trong code comments/docstring cho format mới.
- [x] Task 1.3: Thiết kế `normalize_row_2025` (xác định level 4 vs 5 từ cột D/E).

### Phase 2: Core Features
- [x] Task 2.1: Tạo `Vsic2025ExcelRepository` đọc cột `Cấp 1..5`, `Tên ngành` với header validation.
- [x] Task 2.2: Tạo `Vsic2025ParserService` — gom cấp 5 vào `children_level5` của cấp 4 hiện tại.
  - Xử lý inline child khi row có cả Cấp 4 và Cấp 5
- [x] Task 2.3: Tạo `Vsic2025JsonRepository` — ghi wrapper + nested schema (`output/vsic-vn.json`).
- [x] Task 2.4: Đăng ký CLI `convert-vsic-2025` trong `main.py`; không sửa `convert-vsic`.

### Phase 3: Integration & Polish
- [x] Task 3.1: Kiểm tra CLI `convert-vsic-2025` (default → `output/vsic-vn.json`).
  - Chạy thành công, tạo file JSON 496 entries + 744 children
- [x] Task 3.2: So sánh output với contract (11/11 checks pass).
- [x] Task 3.3: Cập nhật docs implementation/testing feature để bàn giao triển khai.

## Dependencies
**What needs to happen in what order?**

- Task 1.1 là blocker cho toàn bộ Phase 2.
- Task 2.1 và 2.2 phụ thuộc Task 1.3.
- Task 2.3 phụ thuộc 2.2 để xác nhận shape dữ liệu.
- Task 3.1/3.2 chỉ thực hiện sau khi 2.1–2.4 hoàn tất.
- External dependencies (APIs, services, etc.):
  - Không có external API.
- Team/resource dependencies:
  - Stakeholder đã chốt: command riêng, không detect chung.

## Timeline & Estimates
**When will things be done?**

- Estimated effort per task/phase:
  - Phase 1: 0.5 ngày
  - Phase 2: 1.0 ngày
  - Phase 3: 0.5 ngày
- Target dates for milestones:
  - M1: ngày 1 (buổi sáng)
  - M2: ngày 1 (cuối ngày)
  - M3: ngày 2 (buổi sáng)
- Buffer for unknowns:
  - +0.5 ngày cho edge cases dữ liệu (merged/blank rows không chuẩn).

## Risks & Mitigation
**What could go wrong?**

- Technical risks:
  - Dữ liệu row không nhất quán (nhiều cấp đồng thời có giá trị, hoặc thiếu title).
  - **Mitigation:** validate row chặt chẽ + log warning + test fixtures phủ các pattern.
- Resource risks:
  - Thiếu dữ liệu expected output chuẩn để đối chiếu.
  - **Mitigation:** dùng schema contract + snapshot từ output hiện tại làm baseline.
- Dependency risks:
  - ~~Quyết định detect format~~ → đã chốt command riêng; rủi ro giảm.

## Resources Needed
**What do we need to succeed?**

- Team members and roles:
  - 1 backend engineer triển khai parser/repository.
  - 1 reviewer xác nhận contract output.
- Tools and services:
  - `python3`, `pytest`, existing project env.
- Infrastructure:
  - File test fixture cho format 2025.
- Documentation/knowledge:
  - `docs/ai/requirements/feature-convert-vsic-2025-excel-to-json.md`
  - `docs/ai/design/feature-convert-vsic-2025-excel-to-json.md`

