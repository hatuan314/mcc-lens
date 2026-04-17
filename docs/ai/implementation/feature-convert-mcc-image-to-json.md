---
phase: implementation
title: Implementation Guide - Convert MCC Image to JSON
description: Hướng dẫn triển khai pipeline Florence-2 → JSON cho ảnh MCC VISA, tuân thủ Clean Architecture của dự án.
---

# Implementation Guide

## Development Setup
**Bắt đầu thế nào?**

- Prerequisites: Python 3.10+, `pip`, venv; ~4GB đĩa trống cho weight Florence-2; kết nối Internet lần đầu.
- Cài đặt:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- Biến môi trường (tuỳ chọn):
  - `HF_HOME=~/.cache/huggingface` — cache model.
  - `LOG_LEVEL=DEBUG` — xem output raw Florence-2 khi debug parser.

## Code Structure
**Cách tổ chức code:**

```
app/
├── models/
│   └── mcc_entry.py                     # MCCEntry (pydantic)
├── repositories/
│   ├── mcc_image_repository.py          # list ảnh input
│   └── mcc_json_repository.py           # ghi JSON output
├── services/
│   ├── interfaces.py                    # Protocol: VisionService, MCCParser, ...
│   ├── florence2_vision_service.py      # Florence-2 wrapper
│   ├── mcc_parser_service.py            # text -> list[MCCEntry]
│   └── convert_mcc_images_use_case.py   # orchestration
├── controllers/
│   └── mcc_convert_controller.py        # CLI -> Use Case
└── views/
    └── progress_bar_view.py             # tqdm wrapper
main.py                                   # subcommand convert-mcc
```

Quy ước đặt tên: `snake_case` cho module/hàm, `PascalCase` cho class; tuân thủ `.claude/rules/python-standards.md`.

## Implementation Notes
**Chi tiết kỹ thuật cần nhớ:**

### Core Features
- **Florence-2 Vision Service**: Dùng `AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)` + `AutoProcessor`. Gọi `generate` với `task_prompt` phù hợp (khởi điểm: `<OCR>`). Post-process qua `processor.post_process_generation(...)`. Load lazy (lần dùng đầu) để test không chạm model.
- **MCC Parser Service**: Heuristic regex:
  - `mcc_code`: `r"\b(\d{4})\b"` gần đầu block.
  - `title`: dòng IN HOA / title-case sau mã.
  - `description`: đoạn văn dài sau title.
  - `similar_merchants`: sau nhãn "Similar Merchants"/"Examples" — split theo `[,\n]`.
  - Trả `list[MCCEntry]`; entry thiếu `mcc_code` bị skip kèm log WARNING.
- **Use Case**: Vòng lặp `for path in image_repo.list_images(input_dir):` → `text = vision.extract_text(path)` → `entries += parser.parse(text, path.name)` → `progress.update(1)`. Kết thúc gọi `json_repo.save(dedup(entries), output_path)`.

### Patterns & Best Practices
- **Dependency Inversion**: Use Case chỉ phụ thuộc `Protocol` trong `services/interfaces.py`; implementations được inject từ Controller.
- **Single Responsibility**: Parser không biết về Florence-2; Vision service không biết về schema MCC.
- **Immutability**: `MCCEntry` là pydantic model (frozen=True nếu khả thi).
- **Hàm ngắn**: mỗi hàm ≤ ~30 dòng, ≤ 3 tham số; dùng dataclass/TypedDict cho group tham số dài nếu cần.
- **Type hints đầy đủ**, docstring Google style cho public API.

## Integration Points
**Các điểm kết nối:**

- **HuggingFace Hub**: `transformers` tự xử lý download; kiểm tra biến môi trường `HF_HOME` / proxy nếu cần.
- **Filesystem**: input `assets/mcc-visa/`, output mặc định `out/mcc-visa.json` (tạo thư mục nếu chưa có).
- **Logging**: reuse setup `loguru` trong `main.py`; service log theo logger module (`logger.bind(component="florence2")`).
- **Không có DB / external API**.

## Error Handling
**Xử lý lỗi:**

- Use Case bọc mỗi ảnh trong `try/except Exception as e:` → `logger.warning(f"Bỏ qua {path.name}: {e}")`, `continue`.
- Florence-2 lỗi load model → raise lên Controller → exit code `2` (lỗi hạ tầng).
- Parser không ra entry nào cho 1 ảnh → log `INFO` (không phải lỗi).
- Ghi JSON lỗi IO → raise lên Controller → exit code `3`.
- Exit code `0` nếu chạy xong (kể cả có ảnh skip); `1` cho lỗi cấu hình CLI.

## Performance Considerations
**Giữ tốc độ:**

- Load Florence-2 **một lần** cho toàn batch; không reload giữa ảnh.
- GPU: dùng `torch.float16` + `.to("cuda")`; CPU: `float32`.
- Không cache kết quả giữa các lần chạy — dataset nhỏ, không cần.
- Cho phép flag `--limit N` (optional future) để smoke test nhanh.

## Security Notes
**An toàn & bảo mật:**

- Model tải từ HuggingFace — dùng `trust_remote_code=True` bắt buộc cho Florence-2; chấp nhận rủi ro vì model chính thức của Microsoft. Pin `revision` nếu cần siết chặt.
- Không có secrets; không cần `.env` cho feature này.
- Validate đường dẫn input (không ra ngoài thư mục project) trong Controller để tránh path traversal.
- Output JSON ghi bằng `ensure_ascii=False` nhưng escape theo chuẩn JSON → an toàn.
