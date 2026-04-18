---
phase: requirements
title: Requirements & Problem Understanding — Convert VSIC Excel to JSON
description: Chuyển đổi file vsic.xlsx chứa danh sách mã ngành VSIC của Việt Nam thành JSON có cấu trúc
---

# Requirements & Problem Understanding

## Problem Statement
**What problem are we solving?**

- File `assets/vsic-vn/vsic.xlsx` chứa danh sách đầy đủ các mã ngành VSIC (Vietnam Standard Industrial Classification) mà Việt Nam đang sử dụng.
- Dữ liệu hiện ở dạng Excel — không thể dùng trực tiếp trong các pipeline mapping VSIC ↔ MCC downstream.
- Cần một script CLI có thể đọc file xlsx, trích xuất dữ liệu có cấu trúc và xuất ra JSON chuẩn hoá.

**Người bị ảnh hưởng:** Developer/data engineer sử dụng MCC Lens để map mã ngành VSIC sang MCC.

**Workaround hiện tại:** Thủ công hoặc không có.

## Goals & Objectives
**What do we want to achieve?**

- **Primary:** Parse toàn bộ 743 entries từ `vsic.xlsx` và xuất ra flat JSON array với metadata `digits`.
- **Secondary:** Hỗ trợ tham số CLI `--input`; output mặc định là `output/vsic.json`.
- **Non-goals:**
  - Không mapping VSIC → MCC trong tính năng này.
  - Không lưu vào database.
  - Không hỗ trợ các định dạng Excel khác ngoài `.xlsx`.
  - Không suy luận ngược hierarchy (Section/Division/Group) từ code số.
  - Không hỗ trợ tiếng Anh (file chỉ có tiếng Việt).

## User Stories & Use Cases

- Là một developer, tôi muốn chạy một lệnh CLI để convert `vsic.xlsx` thành JSON, để có thể dùng dữ liệu VSIC trong các pipeline downstream.
- Là một data engineer, tôi muốn JSON đầu ra là flat array với trường `digits` (4 hoặc 5) để dễ filter theo cấp độ mã ngành.
- Là một developer, tôi muốn script bỏ qua các hàng trống/header thừa trong Excel, để JSON sạch không có dữ liệu rác.

**Edge cases:**
- Hàng trống giữa các section.
- Ô merged (merged cells) trong Excel.
- Mã code có thể là số hoặc chuỗi (ví dụ: `01`, `01.1`).

## Success Criteria

- [ ] Script đọc được `assets/vsic-vn/vsic.xlsx` không có lỗi.
- [ ] JSON đầu ra là flat array, mỗi entry có `code` (string), `title` (string), `digits` (int: 4 hoặc 5).
- [ ] Số lượng entries trong JSON == số rows hợp lệ trong xlsx (không đếm header, không đếm rows null).
- [ ] `code` luôn là string (ví dụ `"1110"`, không phải `1110`).
- [ ] Không có entry với `code` null hoặc rỗng trong JSON.
- [ ] Chạy CLI không truyền `--output` → tự xuất ra `output/vsic.json`.
- [ ] Có thể chạy: `python3 main.py convert-vsic --input assets/vsic-vn/vsic.xlsx`.

## Constraints & Assumptions

- **Technical:** Sử dụng `openpyxl` để đọc xlsx (không dùng pandas).
- **Architecture:** Tuân thủ Clean Architecture — repository đọc file, service parse, controller điều phối.
- **Confirmed structure:** xlsx có 2 cột (`Mã ngành nghề`, `Tên ngành`), 743 data rows, header ở row 1.
- **Confirmed:** Code là số nguyên trong xlsx → convert sang string khi parse.
- **Confirmed:** Chỉ tiếng Việt, không hierarchy suy luận, output mặc định `output/vsic.json`.

## Questions & Open Items

- Không còn câu hỏi mở. Tất cả đã được confirm.
