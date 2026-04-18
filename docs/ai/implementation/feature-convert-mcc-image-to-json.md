---
phase: implementation
title: Implementation Guide - Convert MCC Image to JSON
description: Hướng dẫn triển khai pipeline Surya OCR → JSON cho ảnh MCC VISA, tuân thủ Clean Architecture của dự án.
---

# Implementation Guide

> **Cập nhật 2026-04-18:** Engine OCR đã chuyển hoàn toàn sang **Surya OCR**. Lab script `labs/mcc_extractor_surya.py` là tham khảo logic gốc.

## Development Setup

**Bắt đầu thế nào?**

- Prerequisites: Python 3.10+, `pip`, venv; ≥8GB RAM; ~2GB đĩa trống cho weights Surya; Internet lần đầu.
- Cài đặt:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- Biến môi trường (tuỳ chọn):
  - `HF_HOME=~/.cache/huggingface` — cache model.
  - `LOG_LEVEL=DEBUG` — xem chi tiết pipeline khi debug.

## Surya OCR Model Download

Surya weights tải tự động từ HuggingFace Hub khi gọi predictor lần đầu (~1-2GB, cache tại `~/.cache/huggingface/hub/`).

**Lưu ý:**

- Apple M1/M2: Surya chạy native trên **MPS** — không cần CUDA.
- `transformers` phải ở version `>=4.56.1,<5.0.0` (pin trong `requirements.txt`) — transformers 5.x có breaking change `pad_token_id`.
- Surya-ocr cần `requests` (transitively), đã thêm vào requirements.

## Code Structure

```
app/
├── models/
│   ├── mcc_entry.py                  # MCCEntry (pydantic) + SimilarMerchant (dataclass)
│   └── ocr_line.py                   # OCRLine (dataclass pixel bbox)
├── repositories/
│   ├── mcc_image_repository.py       # list_images() + read() -> PIL.Image
│   ├── mcc_json_repository.py        # ghi JSON theo schema {source, total_mcc_count, mcc_list}
│   └── checkpoint_repository.py      # resume state
├── services/
│   ├── protocols.py                  # OCRService, ColumnClassifier, EntryGrouper, EntryParser, TableParser, ...
│   ├── surya_ocr_service.py          # Surya wrapper: extract_lines() -> list[OCRLine]
│   ├── column_classifier.py          # x1/width -> "mcc"/"desc"/"included"/"similar"/"unknown"
│   ├── entry_grouper.py              # trigger entry mới khi gặp ^\d{4}$ ở cột mcc
│   ├── mcc_entry_parser.py           # raw dict -> MCCEntry (title/description/included/similar)
│   ├── mcc_table_parser_service.py   # orchestrator: classifier -> grouper -> parser
│   └── convert_mcc_images_use_case.py  # OCR -> parse -> dedup -> sort -> save
├── controllers/
│   └── mcc_convert_controller.py     # CLI -> Use Case (exit codes 0/1/2/3)
└── views/
    └── progress_bar_view.py          # tqdm wrapper
main.py                                # subcommand convert-mcc (--input-dir, --output, --resume)
```

## Implementation Notes

### Pipeline flow

```
PIL.Image
  └─> SuryaOCRService.extract_lines() -> list[OCRLine]            (pixel bbox, confidence)
        └─> MCCTableParserService.parse(lines, width, source_image)
              ├─> ColumnClassifier.classify() -> cột cho từng line
              ├─> EntryGrouper.group() -> list[RawEntry]
              └─> MCCEntryParser.parse() -> MCCEntry
        └─> Use Case: dedup (keep longer description) + sort by mcc
              └─> MCCJsonRepository.save() -> out/*.json
```

### Core Components

- **`SuryaOCRService`**: lazy-load `FoundationPredictor` + `RecognitionPredictor` + `DetectionPredictor`. Auto device (MPS → CPU). Gọi `recognition_predictor([image], det_predictor=detection_predictor)`, sort lines theo `(round(y1/15), x1)` để giữ order đọc tự nhiên.
- **`ColumnClassifier`**: pure function, ngưỡng cố định theo tỷ lệ `x1/image_width`: mcc 0–12%, desc 12–46%, included 46–64%, similar 64–100%.
- **`EntryGrouper`**: state machine — text ở cột `"mcc"` khớp `^\d{4}$` → flush entry cũ, tạo entry mới. Lines trước MCC đầu tiên bị bỏ qua.
- **`MCCEntryParser`**: dòng đầu `_desc_lines` → `title`; còn lại join space → `description`. `_similar_lines` parse regex `^(\d{4})\s*[–\-]\s*(.+)$`; dòng không khớp nối tiếp title của merchant pending (xử lý title bị cắt). `_included_lines` filter `len > 2`. `mcc == ""` → `unparsed=True`.
- **`MCCTableParserService`**: orchestrator tuần tự; inject được từng sub-component để test isolated.
- **`ConvertMCCImagesUseCase`**: gom entries, dedup theo `mcc` (giữ description dài hơn), sort theo `mcc` trước khi save. Checkpoint ghi sau mỗi ảnh khi `resume=True`.

### Patterns & Best Practices

- **Dependency Inversion**: Use Case chỉ biết Protocol (`OCRService`, `TableParser`, `*Repository`). Wiring concrete ở `main.py`.
- **Single Responsibility**: ColumnClassifier không biết entry là gì; Grouper không biết structure MCCEntry; Parser không biết layout ảnh.
- **Pure functions khi có thể**: Classifier, Grouper, Parser đều deterministic, dễ test.
- **Lazy loading**: Surya predictors load ở lần `extract_lines()` đầu tiên — test logic không chạm model.
- **Type hints + Google docstrings** toàn bộ public API.

## Integration Points

- **HuggingFace Hub**: `surya-ocr` tự xử lý download qua `transformers`; set `HF_HOME` để thay cache dir.
- **Filesystem**: input `assets/mcc-visa/`, output mặc định `out/mcc-visa.json`. Checkpoint ghi tại `<output_dir>/.mcc-convert-progress.json` khi `--resume`.
- **Logging**: `loguru` setup trong `main.py` theo `Config.LOG_LEVEL` / `Config.LOG_FILE`.
- Không có DB / external API.

## Error Handling

- Use Case bọc mỗi ảnh trong `try/except` → `logger.warning` + ghi vào `errors[]`, tiếp tục batch.
- Surya lỗi load model → raise lên Controller → exit code `2`.
- Lỗi IO ghi JSON → exit code `3`.
- Lỗi cấu hình CLI (thư mục không tồn tại) → exit code `1`.
- Batch hoàn tất (kể cả có ảnh skip) → exit code `0`.

## Performance Considerations

- Surya predictors load **một lần** cho toàn batch (lazy, ở ảnh đầu tiên).
- Apple Silicon MPS: ~40s/ảnh; CPU fallback sẽ chậm hơn ~3-5×.
- Dataset nhỏ (~5 ảnh VISA) → không cần cache kết quả trung gian.
- Nếu mở rộng nhiều ảnh: dùng `--resume` để tránh mất tiến độ khi crash.

## Security Notes

- Surya models từ HuggingFace (datalab-to). Pin version trong `requirements.txt` để tránh surprise.
- Không có secrets; không cần `.env` cho feature này.
- Validate input path trong Controller nếu mở rộng cho user input tùy ý.
- Output JSON ghi `ensure_ascii=False` → giữ nguyên unicode (tiếng Việt, en-dash).

## Surya OCR Output Format

`RecognitionPredictor(...)` trả về list `OCRResult`, mỗi cái có `text_lines: list[TextLine]`:

```python
predictions = recognition_predictor([image], det_predictor=detection_predictor)
rec = predictions[0]

for line in rec.text_lines:
    # line.text: str
    # line.bbox: [x1, y1, x2, y2] (pixel)
    # line.confidence: float | None
    pass
```

### Mapping sang OCRLine

```python
OCRLine(
    text=line.text.strip(),
    bbox=[float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
    confidence=float(line.confidence) if line.confidence is not None else 1.0,
)
```

Sort key `lambda l: (round(l.bbox[1] / 15), l.bbox[0])` để group lines cùng hàng (tolerance 15px y-axis) rồi sort trái→phải.

## Test Coverage

53 unit tests pass. Coverage theo layer:

| Layer | Coverage |
|---|---|
| `models/` | 100% |
| `services/` (parser + use case) | 96-100% |
| `repositories/mcc_json_repository` | 100% |
| `surya_ocr_service` | 0% (infrastructure, cần ML runtime) |
| `controllers/` | 0% (wrapper cho use case) |

Lệnh chạy test:
```bash
pytest tests/ -v                    # chạy toàn bộ
pytest tests/ --cov=app --cov-report=term  # với coverage
```
