---
phase: planning
title: Project Planning & Task Breakdown - Convert MCC Image to JSON
description: Phân rã công việc, thứ tự thực hiện và rủi ro cho tính năng convert ảnh MCC sang JSON bằng Florence-2.
---

# Project Planning & Task Breakdown

## Milestones
**Các cột mốc lớn:**

- [ ] **M1 — Foundation sẵn sàng:** dependencies Florence-2 cài được, model load thành công trên CPU.
- [ ] **M2 — Pipeline end-to-end:** chạy được trên 1 ảnh, sinh JSON đúng schema.
- [ ] **M3 — Batch + CLI hoàn chỉnh:** progress bar, error-resilient, chạy toàn bộ 5 ảnh VISA.
- [ ] **M4 — Test & tài liệu:** unit test ≥ 80% coverage phần parser/use case, README cập nhật.

## Task Breakdown
**Công việc cụ thể:**

### Phase 1: Foundation
- [ ] **1.1** Cập nhật `requirements.txt`: thêm `torch`, `transformers`, `pillow`, `tqdm`, `einops`, `timm` (Florence-2 yêu cầu `timm` & `einops`). Pin version.
- [ ] **1.2** Viết script/ghi chú cài đặt & tải weight Florence-2 large (`microsoft/Florence-2-large`) lần đầu.
- [ ] **1.3** Tạo domain model `app/models/mcc_entry.py` với pydantic `MCCEntry` (fields: `mcc`, `title_description`, `included`, `similar_merchants`, `source_image`, `_unparsed`) và dataclass `BBoxTextItem` (fields: `text`, `bbox: tuple[float,float,float,float]`).
- [ ] **1.4** Định nghĩa Protocol interfaces trong `app/services/protocols.py`: `VisionService` (`extract_regions`), `TableReconstructor` (`reconstruct`, `visualize_results`), `MCCParser` (`parse`), `ImageRepository`, `JsonRepository`, `CheckpointRepository`.

### Phase 2: Core Features
- [ ] **2.1** Implement `Florence2VisionService.extract_regions(image_path)`:
  - Load model/processor 1 lần (lazy singleton trong instance).
  - Chọn device auto (cuda > mps > cpu), hỗ trợ flag override.
  - Dùng task `<OCR_WITH_REGION>`, `max_new_tokens=3072`, `num_beams=3`.
  - Trả về `list[BBoxTextItem]` — parse chuỗi Florence-2 ra cặp `(text, bbox [y1,x1,y2,x2])`.
- [ ] **2.2** Implement `TableReconstructionService.reconstruct(regions, image_size)`:
  - **Row grouping**: nhóm bbox theo trục Y với ngưỡng `y_threshold_pct` (default 0.01), truyền qua constructor.
  - **Column assignment**: xác định 4 cột bằng dynamic clustering hoặc mốc X theo % (MCC ~10%, Title/Desc ~50%, Included ~75%, Similar ~90%).
  - **Multi-line merging**: gộp dòng tiếp theo (cột `mcc` trống) vào block của MCC hiện tại.
  - Trả về `list[dict[str, str]]` với keys: `mcc`, `title_description`, `included`, `similar_merchants`.
- [ ] **2.2b** Implement `TableReconstructionService.visualize_results(image_path, rows)`:
  - Vẽ bounding boxes + label hàng/cột lên ảnh bằng `PIL.ImageDraw`.
  - Trả về `PIL.Image` để lưu/hiển thị khi debug.
- [ ] **2.3** Implement `MCCParserService.parse(rows, source)`:
  - Validate `mcc` là 4 chữ số; entry không hợp lệ: `mcc=""`, `_unparsed=True`.
  - Tách `similar_merchants` theo dấu phẩy / newline thành `list[str]`.
  - Build `MCCEntry` cho mỗi row.
- [ ] **2.3** Implement `MCCImageRepository.list_images(dir)` — glob `*.jpg`/`*.jpeg`/`*.png`, sort ổn định.
- [ ] **2.4** Implement `MCCJsonRepository.save(entries, output_path)` — tạo thư mục cha nếu chưa có, ghi UTF-8 indent=2, `ensure_ascii=False`.
- [ ] **2.5** Implement `ConvertMCCImagesUseCase.execute(input_dir, output_path, device, y_threshold_pct, resume)` — orchestrate pipeline: vision → table reconstruction → parser → checkpoint. Dedup cuối batch theo `mcc`: merge `title_description` + `included` bằng `\n`, union `similar_merchants`; giữ nguyên tất cả entry `_unparsed=True`.

### Phase 3: Integration & Polish
- [ ] **3.1** `ProgressBarView` wrap `tqdm` (iterate / update / close).
- [ ] **3.2** `MCCConvertController` — nhận params, inject dependency, gọi Use Case, map exception → exit code.
- [ ] **3.3** Thêm subcommand `convert-mcc` vào `main.py` (argparse), wiring logging. Tham số: `--input-dir`, `--output`, `--device`, `--y-threshold` (default 0.01), `--resume`.
- [ ] **3.4** Error handling: try/except từng ảnh trong Use Case, log `WARNING`, không abort batch.
- [ ] **3.5** Chạy thử toàn bộ 5 ảnh trong `assets/mcc-visa/`, rà soát chất lượng parse.

### Phase 4: Test & Docs
- [ ] **4.1** Unit test `TableReconstructionService` với fixtures bbox mẫu: happy path, multi-line merging, cột lệch trục X, ảnh độ phân giải khác nhau.
- [ ] **4.2** Unit test `MCCParserService` với row fixtures: valid MCC, invalid MCC (→ `_unparsed`), `similar_merchants` nhiều format.
- [ ] **4.3** Unit test `ConvertMCCImagesUseCase` với `FakeVisionService` + `FakeTableReconstructor` (không gọi Florence-2).
- [ ] **4.4** Unit test `MCCJsonRepository` (tạo thư mục, UTF-8, dedup merge strategy).
- [ ] **4.5** Cập nhật `README.md`: hướng dẫn chạy `convert-mcc`, yêu cầu phần cứng, hint về model download, ví dụ `--y-threshold`.
- [ ] **4.6** (Optional) Ghi tài liệu Florence-2 `<OCR_WITH_REGION>` output format + ví dụ `visualize_results` vào `docs/ai/implementation/feature-convert-mcc-image-to-json.md`.

## Dependencies
**Thứ tự và ràng buộc:**

- 1.1 → 2.1 (cần thư viện cài trước khi code service).
- 1.3, 1.4 → 2.1/2.2/2.3/2.4/2.5 (models/interfaces trước implementations).
- 2.1 → 2.2 → 2.2b → 2.3 (pipeline tuần tự: vision → table → parser).
- 2.1 + 2.2 + 2.3 + 2.4 + 2.5 → 3.2 → 3.3 (Use Case cần các phụ thuộc sẵn sàng).
- 2.5 → 3.2 → 3.3 (controller/CLI đi sau use case).
- 3.1 có thể song song với 2.5.
- 4.x chạy sau khi code tương ứng xong; 4.1 có thể bắt đầu ngay sau 2.2.
- **Phụ thuộc ngoài:** HuggingFace Hub (download weights), băng thông mạng lần đầu (~1.5GB), phần cứng có RAM ≥ 8GB.

## Timeline & Estimates
**Khi nào xong (ước lượng lập trình viên đơn):**

| Phase | Effort ước lượng |
|---|---|
| Phase 1 — Foundation | 0.5 ngày |
| Phase 2 — Core Features | 1.5 ngày (rủi ro cao ở 2.1, 2.2) |
| Phase 3 — Integration & Polish | 0.5 ngày |
| Phase 4 — Test & Docs | 0.5 ngày |
| **Tổng** | **~3 ngày công** (buffer 0.5 ngày cho debug Florence-2 output) |

## Risks & Mitigation
**Rủi ro & cách giảm thiểu:**

- **R1 — Florence-2 `<OCR_WITH_REGION>` trả về bbox không đủ hoặc format không nhất quán** (rủi ro *cao*).
  - *Mitigation:* Task đã chốt (`<OCR_WITH_REGION>`, `max_new_tokens=3072`, `num_beams=3`). Log raw output Florence-2 cho mỗi ảnh. Dùng `visualize_results` để kiểm tra trực quan bbox. Viết parser phòng thủ cho cả trường hợp bbox thiếu column. Chấp nhận một số ảnh cần hậu xử lý thủ công.
- **R2 — Hạ tầng không có GPU, inference rất chậm** (trung bình).
  - *Mitigation:* Cho phép `--device cpu` + `torch.float32`. Tài liệu hóa thời gian dự kiến và khuyến nghị chạy trên máy có CUDA.
- **R3 — Kích thước model lớn, bandwidth/disk hạn chế** (thấp).
  - *Mitigation:* Tài liệu README hướng dẫn set `HF_HOME` để cache. Cân nhắc fallback sang `Florence-2-base` cho dev nếu cần (flag `--model-size base`).
- **R4 — Ảnh chất lượng kém khiến OCR thiếu MCC** (trung bình).
  - *Mitigation:* Log entry bị skip, xuất thêm report `errors.json` (liệt kê ảnh không parse được). Cho phép re-run riêng ảnh thất bại.
- **R5 — Phụ thuộc `transformers`/`torch` version xung đột** (thấp).
  - *Mitigation:* Pin version đã test; khuyến nghị venv sạch.

## Resources Needed
**Cần gì để thành công:**

- **Con người:** 1 lập trình viên Python.
- **Công cụ:** Python 3.10+, pip/venv, `pytest`, `black`, `flake8`, `mypy` (đã có trong project).
- **Hạ tầng:** Máy có ≥ 8GB RAM; khuyến nghị GPU ≥ 6GB VRAM cho tốc độ ổn.
- **Kiến thức:** Kinh nghiệm với HuggingFace `transformers`, PIL; hiểu quy ước Clean Architecture / MVC của dự án (`.claude/rules/python-standards.md`).
- **Dữ liệu:** Tập ảnh `assets/mcc-visa/*.jpg` đã có sẵn (5 file).
