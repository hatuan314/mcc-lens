---
phase: planning
title: Project Planning & Task Breakdown - Convert MCC Image to JSON
description: Phân rã công việc, thứ tự thực hiện và rủi ro cho tính năng convert ảnh MCC sang JSON bằng Surya OCR. Thay thế giải pháp Florence-2 trước đó.
---

# Project Planning & Task Breakdown

> **Cập nhật 2026-04-18:** Toàn bộ engine OCR chuyển từ Florence-2 sang Surya OCR.
> Code Florence-2 đã được implement (scaffolding tồn tại trong `app/`) nhưng cần thay thế hoàn toàn.
> Planning này phản ánh công việc cần làm cho Surya OCR theo thiết kế mới.

## Milestones
**Các cột mốc lớn:**

- [x] **M0 — Scaffolding Clean Architecture tồn tại:** cấu trúc thư mục `app/` theo MVC đã có, repositories, views, controller đã scaffold.
- [x] **M1 — Foundation Surya sẵn sàng:** `surya-ocr` cài được, 3 predictors load thành công, model/schema mới định nghĩa xong.
- [x] **M2 — Pipeline end-to-end:** chạy được trên 1 ảnh, sinh JSON đúng schema mới (6 fields).
- [x] **M3 — Batch + CLI hoàn chỉnh:** progress bar, error-resilient, `--resume` hoạt động, chạy toàn bộ ảnh VISA.
- [x] **M4 — Test & tài liệu:** unit test ≥ 80% coverage phần parser/use case, README cập nhật.
- [x] **M5 — Alignment fixes sau /check-implementation:** sửa contract checkpoint, đổi tên file checkpoint, đổi field JSON về `_unparsed`, xử lý NFD/NFC.
- [x] **M6 — Batch Processing (2026-04-18):** Dataset 83 ảnh. `extract_lines_batch` implement trong Protocol + SuryaOCRService. UseCase refactor sang mini-batch `batch_size=8`. Tests cập nhật (4 batch tests). Coverage 88%.

## Task Breakdown
**Công việc cụ thể:**

### Phase 1: Foundation (Migrate từ Florence-2 → Surya)

- [x] **1.1** Cập nhật `requirements.txt`: xóa/thay `torch`, `transformers`, `einops`, `timm` → thêm `surya-ocr`. Giữ `pillow`, `tqdm`, `loguru`, `pydantic`. Pin version.
- [x] **1.2** Cập nhật `CLAUDE.md`: thay mục "Florence-2 Setup" bằng hướng dẫn cài `surya-ocr` và tải weights Surya từ HuggingFace lần đầu.
- [x] **1.3** Rewrite `app/models/mcc_entry.py`:
  - Xóa `BBoxTextItem` (normalized) → thêm `OCRLine` vào `app/models/ocr_line.py` (pixel bbox `[x1,y1,x2,y2]`, confidence).
  - Thêm `SimilarMerchant` dataclass (`mcc: str`, `title: str`).
  - Cập nhật `MCCEntry`: đổi `title_description` → `title: str | None` + `description: str | None`; đổi `included: str` → `included_in_mcc: list[str]`; đổi `similar_merchants: list[str]` → `list[SimilarMerchant]`; đổi `unparsed: bool` → `_unparsed: bool`.
- [x] **1.4** Rewrite `app/services/protocols.py`: xóa `VisionService`, `TableReconstructor`, `MCCParser` cũ → thêm `OCRService`, `ColumnClassifier`, `EntryGrouper`, `EntryParser`, `TableParser`, `ImageRepository`, `JsonRepository`, `CheckpointRepository` theo thiết kế mới.

### Phase 2: Core Features (Surya Pipeline)

- [x] **2.1** Tạo `app/services/surya_ocr_service.py` — implements `OCRService`:
  - Lazy load `FoundationPredictor`, `RecognitionPredictor`, `DetectionPredictor` trong `__init__` (load 1 lần).
  - `extract_lines(image: PIL.Image) -> list[OCRLine]`: gọi `recognition_predictor([image], det_predictor=detection_predictor)`, parse `rec.text_lines` → `OCRLine` (pixel bbox), sort theo `(round(y1/15), x1)`.
  - Tự động chọn device (MPS → CPU); log device đang dùng.
- [x] **2.2** Tạo `app/services/column_classifier.py` — implements `ColumnClassifier`:
  - `classify(line: OCRLine, image_width: int) -> str`: trả `"mcc"/"desc"/"included"/"similar"/"unknown"` dựa vào `line.bbox[0]` (x1) / `image_width` với ngưỡng cố định (0–12%, 12–46%, 46–64%, 64–100%).
  - Pure function, không có state.
- [x] **2.3** Tạo `app/services/entry_grouper.py` — implements `EntryGrouper`:
  - `group(classified: list[tuple[OCRLine, str]]) -> list[dict]`: trả list `RawEntry` (dict gồm `mcc: str`, `_desc_lines: list[str]`, `_included_lines: list[str]`, `_similar_lines: list[str]`).
  - Trigger entry mới khi gặp text khớp `^\d{4}$` ở cột `"mcc"`.
- [x] **2.4** Tạo `app/services/mcc_entry_parser.py` — implements `EntryParser`:
  - `parse(raw: dict, source_image: str) -> MCCEntry`.
  - Dòng đầu `_desc_lines` → `title`; phần còn lại → `description`.
  - Parse `_similar_lines` thành `list[SimilarMerchant]` với nối tiếp title bị cắt (không match `^\d{4}\s*[–\-]`).
  - `_included_lines` filter dòng > 2 ký tự → `included_in_mcc: list[str]`.
  - Gán `_unparsed=True` khi `mcc=""`.
- [x] **2.5** Tạo `app/services/mcc_table_parser_service.py` — implements `TableParser`:
  - Orchestrator gọi tuần tự: `ColumnClassifier` → `EntryGrouper` → `MCCEntryParser`.
  - `parse(lines: list[OCRLine], image_width: int) -> list[MCCEntry]`.
- [x] **2.6** Rewrite `app/services/convert_mcc_images_use_case.py`:
  - Inject: `OCRService`, `TableParser`, `ImageRepository`, `JsonRepository`, `CheckpointRepository`, `ProgressBarView`.
  - `execute(input_dir, output_path, resume)` — không còn `device`/`y_threshold_pct`.
  - Gom tất cả entry → **dedup** (giữ `description` dài hơn khi trùng MCC) → **sort by `mcc`** → truyền vào `JsonRepository.save()`.
- [x] **2.7** Kiểm tra/cập nhật `app/repositories/mcc_image_repository.py` — đảm bảo `read(path) -> PIL.Image` tồn tại.
- [x] **2.8** Kiểm tra/cập nhật `app/repositories/mcc_json_repository.py` — schema output mới: `{"source": ..., "total_mcc_count": N, "mcc_list": [...]}` với `MCCEntry` schema mới (6 fields).
- [x] **2.9** Xóa file lỗi thời: `app/services/florence2_vision_service.py`, `app/services/table_reconstruction_service.py`.

### Phase 3: Integration & Polish

- [x] **3.1** Rewrite `app/controllers/mcc_convert_controller.py`:
  - Inject `SuryaOCRService` (thay Florence-2), `MCCTableParserService` và sub-components.
  - Xóa tham số `device`, `y_threshold_pct`.
  - Giữ exit code logic (0/1/2/3).
- [x] **3.2** Cập nhật `main.py` subcommand `convert-mcc`:
  - Xóa flags `--device`, `--y-threshold`.
  - Giữ `--input-dir`, `--output`, `--resume`.
  - Đảm bảo wiring logging loguru từ `Config`.
- [x] **3.3** Kiểm tra `app/views/progress_bar_view.py` — không thay đổi nếu interface tương thích.
- [x] **3.4** Chạy thử trên 1 ảnh sample, rà soát JSON output đúng schema mới.
- [x] **3.5** Chạy thử toàn bộ ảnh trong `assets/mcc-visa/`, rà soát chất lượng parse, tỷ lệ thành công ≥ 90%.

### Phase 4: Test & Docs

- [x] **4.1** Unit test `ColumnClassifier` (`tests/test_column_classifier.py`): happy path cho 4 cột, boundary values (x1 đúng ngưỡng), unknown column.
- [x] **4.2** Unit test `EntryGrouper` (`tests/test_entry_grouper.py`): 1 entry, nhiều entry, dòng trước MCC code đầu tiên bị bỏ qua, entry cuối không bị mất.
- [x] **4.3** Unit test `MCCEntryParser` (`tests/test_mcc_entry_parser.py`): valid MCC, invalid MCC (`_unparsed=True`), `similar_merchants` với title bị cắt, `included_in_mcc` lọc dòng ngắn.
- [x] **4.4** Unit test `MCCTableParserService` (`tests/test_mcc_table_parser_service.py`): integration của 3 sub-components với fixture OCRLine mẫu.
- [x] **4.5** Unit test `ConvertMCCImagesUseCase` với `FakeOCRService` + `FakeTableParser` — kiểm tra dedup, sort, checkpoint flow, resume.
- [x] **4.6** Unit test `MCCJsonRepository` — schema output mới, UTF-8, tạo thư mục cha.
- [x] **4.7** Cập nhật `README.md`: hướng dẫn chạy `convert-mcc`, yêu cầu cài `surya-ocr`, hint về model download lần đầu (~1-2GB).
- [x] **4.8** Cập nhật `docs/ai/implementation/feature-convert-mcc-image-to-json.md` với ghi chú implementation Surya OCR (nếu file tồn tại).

### Phase 5: Alignment fixes sau `/check-implementation`

- [x] **5.1** Sửa `CheckpointRepository` Protocol về đúng design: `load() → set[str]`, `mark_done(filename)`, `clear()`. Bỏ `exists/save(path, state)`.
- [x] **5.2** `ConvertMCCImagesUseCase` dùng API mới; Controller/`main.py` wire repo với filename chuẩn `.mcc-convert-progress.json`.
- [x] **5.3** Field output đổi về `_unparsed` qua pydantic `alias` + `by_alias=True` ở `MCCJsonRepository`.
- [x] **5.4** Normalize NFC cho tên file ở `CheckpointRepository` và use case để khớp macOS NFD filesystem.
- [x] **5.5** Tests: cập nhật fakes theo protocol mới, thêm regression NFC/NFD (56/56 pass).
- [x] **5.6** Smoke run `--resume` xác nhận: seed 4 ảnh → pipeline chỉ xử lý ảnh còn lại, clear checkpoint khi xong.

### Phase 6: Batch Processing (Quyết định 2026-04-18)

> **Ngữ cảnh:** Dataset tăng lên 83 ảnh. Chọn mini-batch `batch_size=8` với native Surya batch API để giảm thời gian xử lý từ ~20 phút → ~3.5 phút trên M1/M2 MPS.

- [x] **6.1** Update `app/services/protocols.py` — `OCRService` Protocol:
  - ✅ Xóa `extract_lines(image: Image) -> List[OCRLine]`
  - ✅ Thêm `extract_lines_batch(images: List[Image.Image]) -> List[List[OCRLine]]`
  - ✅ `extract_lines()` giữ trong SuryaOCRService nhưng không khai báo trong Protocol
- [x] **6.2** Update `app/services/surya_ocr_service.py`:
  - ✅ Thêm `extract_lines_batch(images: List[Image.Image]) -> List[List[OCRLine]]`
  - ✅ Gọi `self._recognition_predictor(images, det_predictor=self._detection_predictor)` — native batch
  - ✅ Parse `predictions` thành `List[List[OCRLine]]`
  - ✅ Giữ `extract_lines()` như convenience method (gọi batch internally)
- [x] **6.3** Refactor `app/services/convert_mcc_images_use_case.py` — `execute()`:
  - ✅ Hằng số `BATCH_SIZE = 8` class attribute
  - ✅ Chia `images` thành batches (helper method `_group_into_batches`)
  - ✅ Với mỗi batch: skip nếu tất cả đã checkpoint; load PIL images; gọi `extract_lines_batch`
  - ✅ Xử lý 2 loại lỗi: OCR-level (cả batch fail) vs parse-level (1 ảnh fail)
  - ✅ Checkpoint per-image + progress bar per-image
- [x] **6.4** Update `tests/test_convert_mcc_images_use_case.py`:
  - ✅ `FakeOCRService`: thay `extract_lines` → `extract_lines_batch`, track batch_calls
  - ✅ `FailingOCRService`: tương tự
  - ✅ `test_batch_skip_when_all_checkpointed` — batch skip khi tất cả checkpoint
  - ✅ `test_ocr_batch_error_marks_no_images_done` — OCR-level error: không mark done
  - ✅ `test_parse_error_in_batch_marks_others_done` — parse-level: entry vào JSON, checkpoint clear
  - ✅ `test_last_batch_partial` — batch cuối 1 ảnh xử lý đúng
- [x] **6.5** Update `docs/ai/testing/feature-convert-mcc-image-to-json.md`:
  - ✅ Thêm 4 batch test cases vào bảng ConvertMCCImagesUseCase
  - ✅ Coverage: 88% (down from 89%, SuryaOCRService not covered)

## Dependencies
**Thứ tự và ràng buộc:**

- 1.1 → 2.1 (surya-ocr cài trước khi implement service).
- 1.3, 1.4 → 2.1/2.2/2.3/2.4/2.5/2.6 (models/protocols trước implementations).
- 2.1 → 2.5/2.6 (OCR service cần có trước use case).
- 2.2 + 2.3 + 2.4 → 2.5 (sub-components trước orchestrator).
- 2.5 + 2.6 → 3.1 → 3.2 (controller/CLI sau use case).
- 2.9 (xóa Florence-2 files) nên làm sau khi 2.1/2.5/2.6 xong để tránh import error.
- 3.1 (progress bar check) song song được với 2.x.
- 4.1-4.4 có thể bắt đầu ngay sau sub-component tương ứng xong.
- **Phụ thuộc ngoài:** HuggingFace Hub (download Surya weights ~1–2GB), băng thông mạng lần đầu, RAM ≥ 8GB.

## Timeline & Estimates

| Phase | Effort ước lượng | Trạng thái | Hoàn thành |
|---|---|---|---|
| Phase 1 — Migration foundation | 0.5 ngày | ✅ Hoàn thành | 2026-04-17 |
| Phase 2 — Core pipeline Surya | 1 ngày | ✅ Hoàn thành | 2026-04-17 |
| Phase 3 — Integration & Polish | 0.5 ngày | ✅ Hoàn thành | 2026-04-17 |
| Phase 4 — Test & Docs | 0.5 ngày | ✅ Hoàn thành | 2026-04-17 |
| Phase 5 — Alignment fixes | 0.5 ngày | ✅ Hoàn thành | 2026-04-17 |
| Phase 6 — Batch Processing | 0.5 ngày | ✅ Hoàn thành | 2026-04-18 |
| **Tổng** | **~3.5 ngày công** | ✅ **6/6 DONE** | |

## Risks & Mitigation

- **R1 — `surya-ocr` API thay đổi giữa các phiên bản** (trung bình):
  - *Mitigation:* Pin version trong `requirements.txt`. Lab script `labs/mcc_extractor_surya.py` xác nhận API hiện tại hoạt động.
- **R2 — Tỷ lệ parse < 90% trên một số ảnh scan nghiêng/nhiễu** (trung bình):
  - *Mitigation:* Log chi tiết entry thất bại. Entry không parse được giữ lại với `_unparsed=True` (không mất data). Hậu xử lý thủ công các entry này nếu cần.
- **R3 — Import conflict giữa code Florence-2 cũ và Surya mới** (cao trong giai đoạn migration):
  - *Mitigation:* Thực hiện migration theo thứ tự: models → protocols → services mới → xóa services cũ → update use case → update controller. Không để 2 engine cùng tồn tại sau 2.9.
- **R4 — Test cũ (`test_models.py`) break khi schema MCCEntry thay đổi** (chắc chắn xảy ra):
  - *Mitigation:* Cập nhật `test_models.py` ngay sau khi hoàn thành task 1.3.
- **R5 — Surya chậm trên máy không có GPU** (thấp so với trước):
  - *Mitigation:* Surya native MPS trên Apple M1/M2 — đủ nhanh. Không cần CUDA. Ghi nhận benchmark trong docs.

## Resources Needed

- **Con người:** 1 lập trình viên Python.
- **Công cụ:** Python 3.10+, pip/venv, `pytest`, `black`, `flake8`, `mypy`.
- **Hạ tầng:** Máy có ≥ 8GB RAM; Apple M1/M2 được khuyến nghị (MPS native). Không yêu cầu GPU rời.
- **Dữ liệu:** Tập ảnh `assets/mcc-visa/*.jpg` đã có sẵn. Lab script `labs/mcc_extractor_surya.py` dùng để tham khảo logic.
