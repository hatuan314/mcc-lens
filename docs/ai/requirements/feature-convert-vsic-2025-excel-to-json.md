---
phase: requirements
title: Requirements & Problem Understanding — Convert VSIC 2025 Excel to JSON
description: Chuyển đổi vsic-2025.xlsx sang JSON nested (cấp 4 + children_level5) qua CLI riêng, output mặc định output/vsic-vn.json
---

# Requirements & Problem Understanding

## Problem Statement
**What problem are we solving?**

- File `assets/vsic-vn/vsic-2025.xlsx` chứa danh mục VSIC mới, nhưng cấu trúc khác file cũ: 6 cột (`Cấp 1..Cấp 5`, `Tên ngành`) thay vì 2 cột phẳng (`Mã ngành nghề`, `Tên ngành`).
- Pipeline `convert-vsic` hiện tại được thiết kế cho `vsic.xlsx`, không parse được file 2025.
- Cần command và parser riêng để convert `vsic-2025.xlsx` thành JSON dùng cho `map-vsic-mcc` và các job downstream.

**Who is affected by this problem?**

- Developer/data engineer vận hành pipeline mapping VSIC ↔ MCC.
- Nhóm tích hợp dữ liệu cần nguồn VSIC 2025 mà không phá luồng convert file cũ.

**What is the current situation/workaround?**

- Workaround hiện tại là xử lý thủ công hoặc sửa tạm parser — dễ sai, khó lặp lại, không đồng nhất output.

## Stakeholder Decisions (đã chốt)

| # | Chủ đề | Quyết định |
|---|--------|------------|
| 1 | Output schema | **Nested:** `vsic_list` = entry cấp 4, mỗi entry có `children_level5` |
| 2 | CLI | **Command tách riêng** `convert-vsic-2025` (không auto-detect trong `convert-vsic`) |
| 3 | Field trên JSON | **Tối thiểu:** cấp 4 = `code`, `title`, `children_level5`; cấp 5 con = `code`, `title` (không `level`, `parent_code`, `description`) |
| 3b | Downstream mapping | **`map-vsic-mcc` chỉ map mã cấp 4** (mỗi phần tử `vsic_list` = 1 dòng); không flatten/map `children_level5` |
| 4 | Output mặc định | `output/vsic-vn.json` |

## Goals & Objectives
**What do we want to achieve?**

- Primary goals:
  - Parse ổn định `assets/vsic-vn/vsic-2025.xlsx`.
  - Xuất JSON với wrapper `source`, `total_vsic_count`, `vsic_list` (nested cấp 4 + `children_level5`).
  - Gom đúng mã cấp 5 (cột E) vào entry cấp 4 cha (cột D).
- Secondary goals:
  - Tái sử dụng controller/service/repository pattern hiện có; logic 2025 tách biệt khỏi `convert-vsic`.
  - Dễ mở rộng khi format VSIC thay đổi.
- Non-goals (what's explicitly out of scope):
  - Không sửa `convert-vsic` / parser cho `vsic.xlsx`.
  - Không auto-detect format trong một command chung.
  - Không flatten `children_level5` cho `map-vsic-mcc` trong phạm vi feature này.
  - Không xử lý mapping VSIC → MCC trong feature này.
  - Không xuất cấp 1–3 ra `vsic_list`.
  - Không UI; chỉ CLI.
  - Chỉ `.xlsx`.

## User Stories & Use Cases
**How will users interact with the solution?**

- As a data engineer, I want to run `convert-vsic-2025` on `vsic-2025.xlsx` so that I get `output/vsic-vn.json` for mapping jobs.
- As a backend developer, I want cấp 5 nested under the correct cấp 4 parent so the JSON reflects the Excel hierarchy.
- As a maintainer, I want `map-vsic-mcc` to keep working without code changes — it reads only `code` and `title` from each top-level `vsic_list` item (cấp 4).

- Key workflows and scenarios:
  - `python3 main.py convert-vsic-2025` (mặc định input `assets/vsic-vn/vsic-2025.xlsx`, output `output/vsic-vn.json`).
  - Parse cấp 4 từ cột D; gom cấp 5 từ cột E (các hàng sau entry cấp 4 tương ứng).
  - `map-vsic-mcc --vsic-input output/vsic-vn.json` map theo số phần tử cấp 4 trong `vsic_list`.
- Edge cases to consider:
  - Nhiều ô trống ở các cột cấp trên cùng một row.
  - `Cấp 5` trống trên row cấp 4, nhưng các row sau có `Cấp 5` thuộc cấp 4 gần nhất.
  - Code là số trong Excel → chuẩn hóa thành string, không zero-pad.
  - Row header / row rỗng xen kẽ.
  - Cấp 4 không có con: `children_level5` là mảng rỗng `[]`.

## Output Contract
**JSON schema (canonical example)**

```json
{
  "source": "assets/vsic-vn/vsic-2025.xlsx",
  "total_vsic_count": 2,
  "vsic_list": [
    {
      "code": "0111",
      "title": "Trồng lúa",
      "children_level5": [
        { "code": "01110", "title": "Trồng lúa hạt" },
        { "code": "01119", "title": "Trồng lúa khác" }
      ]
    },
    {
      "code": "0112",
      "title": "Trồng ngô",
      "children_level5": []
    }
  ]
}
```

- `total_vsic_count` = số phần tử trong `vsic_list` (chỉ đếm entry cấp 4, không đếm `children_level5`).
- `children_level5` bắt buộc trên mỗi entry cấp 4 (có thể `[]`).
- `source` luôn bằng **input file path** thực tế được dùng khi chạy CLI (default `assets/vsic-vn/vsic-2025.xlsx`).

**Downstream (`map-vsic-mcc`)**

- Đọc `vsic_list` như danh sách phẳng các entry cấp 4.
- Chỉ dùng `code` và `title` của từng entry cấp 4; **bỏ qua** `children_level5`.
- Số dòng Excel mapping = `total_vsic_count` (không bao gồm mã cấp 5).

## Success Criteria
**How will we know when we're done?**

- Measurable outcomes:
  - `convert-vsic-2025` chạy thành công với `assets/vsic-vn/vsic-2025.xlsx`.
  - File `output/vsic-vn.json` (hoặc `--output` tùy chỉnh) parse được và khớp Output Contract.
  - `total_vsic_count` khớp `len(vsic_list)`.
- Acceptance criteria:
  - CLI: subcommand `convert-vsic-2025` với `--input` / `--output` (default như trên).
  - `vsic_list[*]`: chỉ `code`, `title`, `children_level5` (không field metadata thừa).
  - `children_level5[*]`: chỉ `code`, `title`.
  - `code` luôn string, giữ nguyên theo nguồn (không zero-pad).
  - Không tạo entry từ row trống/không hợp lệ.
  - `convert-vsic` cho `vsic.xlsx` không bị ảnh hưởng (regression test pass).
  - `map-vsic-mcc` với output mới không cần thay đổi code; map đúng số entry cấp 4.
- Performance benchmarks (if applicable):
  - Parse ~1k rows trong < 3 giây trên máy local.

## Constraints & Assumptions
**What limitations do we need to work within?**

- Technical constraints:
  - Clean Architecture; `python3` cho mọi lệnh.
  - Command riêng `convert-vsic-2025`; không format detection trong `convert-vsic`.
- Business constraints:
  - `map-vsic-mcc` contract giữ nguyên: một `vsic_list` item = một VSIC được map (cấp 4).
- Time/budget constraints:
  - Thay đổi tối thiểu trên luồng cũ; tập trung parser/repository/test cho 2025.
- Assumptions we're making:
  - Header cố định: `Cấp 1..Cấp 5`, `Tên ngành`.
  - Cấp 4 ở cột D, cấp 5 ở cột E; row cấp 5 thuộc cấp 4 gần nhất phía trên.
  - `Tên ngành` áp dụng cho cả cấp 4 và cấp 5 trên row tương ứng.

## Questions & Open Items
**What do we still need to clarify?**

- Unresolved questions:
  - Không còn (đã chốt trong Stakeholder Decisions).
- Items requiring stakeholder input:
  - Không còn.
- Research needed:
  - Soát đoạn cuối `vsic-2025.xlsx` để xác nhận quy luật “cấp 5 sau cấp 4” không bị phá vỡ (không chặn implement nếu unit test + sample đã pass).
