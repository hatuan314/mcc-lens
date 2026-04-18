---
phase: implementation
title: Implementation Guide — Convert VSIC Excel to JSON
description: Ghi chú kỹ thuật khi triển khai pipeline VSIC xlsx → JSON
---

# Implementation Guide

## Development Setup

- Thêm `openpyxl` vào `requirements.txt` rồi `pip install -r requirements.txt`.
- Không cần biến môi trường đặc biệt.

## Code Structure

```
app/
├── models/vsic_entry.py              # VsicEntry Pydantic model
├── services/
│   ├── protocols.py                  # VsicRepository, VsicParser protocols (thêm vào)
│   └── vsic_parser_service.py        # VsicParserService
└── repositories/
    ├── vsic_excel_repository.py      # Đọc xlsx
    └── vsic_json_repository.py       # Ghi JSON
app/controllers/vsic_controller.py    # Điều phối
tests/
├── test_vsic_parser_service.py
├── test_vsic_excel_repository.py
└── test_vsic_controller.py
```

## Implementation Notes

### Level Detection Logic
```python
import re

def detect_level(code: str) -> str:
    if re.match(r'^[A-Z]$', code):          return "section"
    if re.match(r'^\d{2}$', code):          return "division"
    if re.match(r'^\d{2}\.\d$', code):      return "group"
    if re.match(r'^\d{2}\.\d{2}$', code):   return "class"
    return "unknown"
```

### openpyxl — xử lý merged cells
```python
# Cần unmerge để đọc giá trị đúng
ws = wb.active
# openpyxl tự fill giá trị vào ô đầu của merged range
# các ô còn lại trả về None — cần propagate xuống
```

### parent_code tracking
- Giữ stack theo level: khi gặp division, parent = section hiện tại; khi gặp group, parent = division hiện tại...

## Error Handling

- Row thiếu `code` hoặc `title`: log warning + bỏ qua.
- File không tồn tại: raise `FileNotFoundError` ở repository, controller catch + exit với message rõ ràng.

## Performance Considerations

- File xlsx nhỏ (~vài trăm dòng) — load toàn bộ vào memory, không cần streaming.
