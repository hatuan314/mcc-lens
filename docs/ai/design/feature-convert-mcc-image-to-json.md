---
phase: design
title: System Design & Architecture - Convert MCC Image to JSON
description: Thiết kế pipeline CLI dùng Surya OCR để trích xuất ảnh MCC VISA thành JSON có cấu trúc, tuân thủ Clean Architecture. Thay thế giải pháp Florence-2 trước đó.
---

# System Design & Architecture

## Architecture Overview
**Cấu trúc hệ thống ở mức cao:**

```mermaid
graph TD
  CLI[CLI Entry<br/>main.py convert-mcc] --> Controller[MCCConvertController]
  Controller --> UseCase[ConvertMCCImagesUseCase]
  UseCase --> Repo[MCCImageRepository<br/>đọc assets/mcc-visa/*.jpg]
  UseCase -->|batch_size=8| BatchLoop[Batch Loop<br/>ceil(N/8) batches]
  BatchLoop -->|List[Image]| OCRSvc[SuryaOCRService<br/>extract_lines_batch → List[List[OCRLine]]]
  BatchLoop --> ParserSvc[MCCTableParserService<br/>OCRLine → MCCEntry list<br/>per-image]
  BatchLoop --> Checkpoint[CheckpointRepository<br/>mark_done per-image]
  BatchLoop --> Progress[ProgressBarView<br/>update per-image]
  UseCase --> Writer[MCCJsonRepository<br/>ghi JSON output]
  OCRSvc -.->|load weights| Surya[(Surya OCR<br/>RecognitionPredictor<br/>DetectionPredictor<br/>FoundationPredictor)]
```

### Thành phần và trách nhiệm
- **CLI Entry (`main.py`)**: Parse argparse, khởi động logging (loguru), gọi Controller.
- **Controller (`app/controllers/mcc_convert_controller.py`)**: Tiếp nhận tham số (`input_dir`, `output_path`, `resume`), điều phối Use Case, map exception thành exit code.
- **Use Case (`app/services/convert_mcc_images_use_case.py`)**: Orchestration thuần — chia danh sách ảnh thành batches `BATCH_SIZE=8`, skip batch nếu toàn bộ đã có checkpoint, gọi `ocr_service.extract_lines_batch(images)` → parse từng ảnh trong batch → checkpoint per-image → update progress bar. Dedup, sort, và gọi writer sau khi xử lý toàn bộ. Không biết chi tiết Surya.
- **Surya OCR Service (`app/services/surya_ocr_service.py`)**: Wrap `RecognitionPredictor`, `DetectionPredictor`, `FoundationPredictor` từ `surya-ocr`. Load model một lần, tái dùng toàn session. Implements `extract_lines_batch(images: List[Image]) -> List[List[OCRLine]]` — gọi `recognition_predictor(images_list, det_predictor=detection_predictor)` native batch API, parse kết quả thành `List[List[OCRLine]]` với pixel bbox `[x1, y1, x2, y2]`. Tự động chọn device (MPS trên Apple M1/M2, CPU fallback). Giữ lại `extract_lines(image)` như convenience method nhưng không expose qua Protocol.
- **MCC Table Parser Service (`app/services/mcc_table_parser_service.py`)**: Orchestrator parsing — nhận `list[OCRLine]` + `image_width`, lần lượt gọi 3 sub-component rồi trả `list[MCCEntry]`:
  1. **`ColumnClassifier`** (`app/services/column_classifier.py`): nhận `OCRLine` + `image_width` → trả tên cột (`mcc`/`desc`/`included`/`similar`/`unknown`) dựa vào x1 % cố định. Không có state — pure function, dễ unit test độc lập.
  2. **`EntryGrouper`** (`app/services/entry_grouper.py`): nhận `list[(OCRLine, col_name)]` → trả `list[RawEntry]` (dict gồm `mcc` + 3 list dòng theo cột). Trigger entry mới khi gặp 4-digit token ở cột `mcc`.
  3. **`MCCEntryParser`** (`app/services/mcc_entry_parser.py`): nhận `RawEntry` → `MCCEntry`. Dòng đầu `_desc_lines` → `title`; phần còn lại → `description`; nối tiếp title bị cắt trong `similar_merchants`; gán `_unparsed=True` khi `mcc=""`.
- **Repositories**:
  - `MCCImageRepository`: Liệt kê/đọc ảnh từ thư mục input, trả `PIL.Image`.
  - `MCCJsonRepository`: Ghi `list[MCCEntry]` đã sạch ra JSON (UTF-8, indent=2). Không thực hiện dedup/sort — Use Case đã xử lý trước khi gọi.
  - `CheckpointRepository`: Đọc/ghi/xóa `.mcc-convert-progress.json` — đặt cùng thư mục output. Ghi tên ảnh sau mỗi ảnh thành công; xóa khi pipeline hoàn thành.
- **Views**: `ProgressBarView` bọc `tqdm`; Use Case không import tqdm trực tiếp.

### Công nghệ & lý do chọn
| Thành phần | Công nghệ | Lý do |
|---|---|---|
| OCR Engine | `surya-ocr` (RecognitionPredictor, DetectionPredictor, FoundationPredictor) | Chạy local, miễn phí, native MPS trên Apple M1/M2; không cần GPU rời. |
| CLI | `argparse` (stdlib) | Tránh thêm dependency; đủ cho use case đơn giản. |
| Progress bar | `tqdm` | Gọn nhẹ, quen thuộc, tích hợp tốt terminal. |
| Logging | `loguru` | Đã có trong `requirements.txt`. |
| Image I/O | `Pillow` | Surya yêu cầu `PIL.Image`; đọc ảnh JPG. |
| Validation | `pydantic` | Dùng cho `MCCEntry` model; validate schema trước khi ghi JSON. |
| License | GPL-3.0 | Surya phát hành dưới GPL-3.0; sử dụng nội bộ/tooling không vi phạm. |

## Data Models
**Dữ liệu cần quản lý:**

### `OCRLine` (transfer object — `app/models/ocr_line.py`)
```python
@dataclass
class OCRLine:
    text: str
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 (pixel coordinates)
    confidence: float = 1.0
```

### `SimilarMerchant` (value object — `app/models/mcc_entry.py`)
```python
@dataclass
class SimilarMerchant:
    mcc: str    # "5995"
    title: str  # "Pet Shops, Pet Foods and Supplies Store"
```

### `MCCEntry` (domain model — `app/models/mcc_entry.py`)
```python
class MCCEntry(BaseModel):
    mcc: str                                     # "0742"; rỗng "" nếu không parse được
    title: str | None = None                     # dòng đầu cột description
    description: str | None = None               # phần còn lại cột description
    included_in_mcc: list[str] = []              # danh sách string từ cột included
    similar_merchants: list[SimilarMerchant] = []
    source_image: str                            # tên file ảnh nguồn (provenance)
    _unparsed: bool = False                      # True khi mcc = "" do parse thất bại
```

### Output JSON schema
Một file tổng `mcc-visa.json` chứa object wrapper với `mcc_list`:
```json
{
  "source": "Visa Merchant Data Standards Manual",
  "total_mcc_count": 2,
  "mcc_list": [
    {
      "mcc": "0742",
      "title": "Veterinary Services",
      "description": "Merchants classified with this MCC are...",
      "included_in_mcc": ["Animal Doctors", "Pet Hospitals", "Pet Clinics"],
      "similar_merchants": [
        {"mcc": "5995", "title": "Pet Shops, Pet Foods and Supplies Store"}
      ],
      "source_image": "visa-merchant-data-standards-manual-hình ảnh-01.jpg",
      "_unparsed": false
    },
    {
      "mcc": "",
      "title": null,
      "description": null,
      "included_in_mcc": [],
      "similar_merchants": [],
      "source_image": "visa-merchant-data-standards-manual-hình ảnh-28.jpg",
      "_unparsed": true
    }
  ]
}
```

### Luồng dữ liệu
1. `MCCImageRepository` liệt kê `*.jpg` trong `input_dir` → `list[Path]`, sort theo tên.
2. Nếu `--resume`: `CheckpointRepository` tải set ảnh đã xong.
3. Use Case chia danh sách paths thành batches `BATCH_SIZE=8` (`ceil(N/8)` batches; batch cuối có thể < 8 ảnh).
4. **Với mỗi batch:**
   a. Nếu tất cả ảnh trong batch đã có checkpoint → skip batch, cập nhật progress bar, tiếp batch kế.
   b. Load batch ảnh: `MCCImageRepository.read(path)` → `List[PIL.Image]`.
   c. `SuryaOCRService.extract_lines_batch(images)` → `List[List[OCRLine]]` (1 lần gọi native batch API). Nếu lỗi ở bước này → log error từng ảnh, không mark done, không crash pipeline.
   d. Với mỗi ảnh trong kết quả batch:
      - Nếu ảnh đã có checkpoint → cập nhật progress bar, skip.
      - `MCCTableParserService.parse(lines, image_width, source_image)` → `list[MCCEntry]`. Nếu parse lỗi → log warning, skip ảnh này (không mark done).
      - `CheckpointRepository.mark_done(filename)` (nếu `--resume`).
      - Cập nhật progress bar 1 tick.
5. Use Case gom tất cả entry → **dedup** (giữ entry có `description` dài hơn khi trùng MCC) → **sort** by `mcc` tăng dần.
6. `MCCJsonRepository.save(entries, output_path)` ghi JSON với danh sách đã sạch; `CheckpointRepository.clear()`.

> **Phân biệt 2 loại lỗi trong batch:**
> - **OCR-level** (Surya raise exception cho cả batch): log error từng ảnh, không ảnh nào được mark done.
> - **Parse-level** (OCR OK nhưng parse 1 ảnh thất bại): log warning cho ảnh lỗi, mark done 7 ảnh còn lại bình thường.

## API Design
**Không có API HTTP** — giao tiếp duy nhất là CLI.

### CLI interface
```
python3 main.py convert-mcc \
  --input-dir  assets/mcc-visa \    # default: assets/mcc-visa
  --output     out/mcc-visa.json \  # default: out/mcc-visa.json
  --resume                          # tiếp tục từ checkpoint (default: off)
```
Checkpoint file tự động đặt tại `<output-dir>/.mcc-convert-progress.json`.

> **Lưu ý**: Không có `--device` flag. Surya tự động chọn MPS (Apple M1/M2) hoặc CPU. Không cần `--y-threshold` vì column detection dùng % cố định.

### Internal interfaces (abstractions — Dependency Rule)
```python
class OCRService(Protocol):
    def extract_lines_batch(
        self, images: list["PIL.Image.Image"]
    ) -> list[list[OCRLine]]: ...
    # Note: extract_lines() exists in SuryaOCRService as convenience but is NOT
    # part of the Protocol — UseCase only calls extract_lines_batch.

class ColumnClassifier(Protocol):
    def classify(self, line: OCRLine, image_width: int) -> str: ...  # "mcc"|"desc"|"included"|"similar"|"unknown"

class EntryGrouper(Protocol):
    def group(self, classified: list[tuple[OCRLine, str]]) -> list[dict]: ...  # list[RawEntry]

class EntryParser(Protocol):
    def parse(self, raw: dict, source_image: str) -> MCCEntry: ...

class TableParser(Protocol):
    def parse(
        self,
        lines: list[OCRLine],
        image_width: int,
    ) -> list[MCCEntry]: ...

class ImageRepository(Protocol):
    def list_images(self, dir_path: Path) -> list[Path]: ...
    def read(self, path: Path) -> "PIL.Image.Image": ...

class JsonRepository(Protocol):
    def save(self, entries: list[MCCEntry], output: Path) -> None: ...

class CheckpointRepository(Protocol):
    def load(self) -> set[str]: ...
    def mark_done(self, filename: str) -> None: ...
    def clear(self) -> None: ...
```
Use Case phụ thuộc vào Protocol (D trong SOLID); implementation cụ thể được inject bởi Controller.

## Component Breakdown
**Các khối chính:**

- **Presentation layer**
  - `main.py` — subcommand `convert-mcc`, argparse.
  - `app/views/progress_bar_view.py` — wrap `tqdm`.
- **Controller layer**
  - `app/controllers/mcc_convert_controller.py`.
- **Use case / Service layer**
  - `app/services/convert_mcc_images_use_case.py` — orchestration, dedup, sort
  - `app/services/surya_ocr_service.py` — implements `OCRService`
  - `app/services/mcc_table_parser_service.py` — implements `TableParser`; gọi 3 sub-component bên dưới
  - `app/services/column_classifier.py` — implements `ColumnClassifier`
  - `app/services/entry_grouper.py` — implements `EntryGrouper`
  - `app/services/mcc_entry_parser.py` — implements `EntryParser`
  - `app/services/protocols.py` — tất cả Protocol definitions
- **Repository layer**
  - `app/repositories/mcc_image_repository.py`
  - `app/repositories/mcc_json_repository.py`
  - `app/repositories/checkpoint_repository.py`
- **Domain models**
  - `app/models/ocr_line.py` — `OCRLine` (dataclass)
  - `app/models/mcc_entry.py` — `MCCEntry` (pydantic), `SimilarMerchant` (dataclass)
- **Third-party**
  - `surya-ocr`: tải weights ~1–2GB từ HuggingFace lần đầu; cache local.

## Design Decisions
**Vì sao chọn cách này?**

1. **Surya thay Florence-2**: Surya chuyên biệt cho OCR (detection + recognition), không cần CUDA, native MPS trên Apple M1/M2. Florence-2 là VLM đa năng — overhead không cần thiết cho bài toán OCR thuần.
2. **Tách `SuryaOCRService` khỏi `MCCTableParserService`**: OCR là I/O-heavy và model-dependent; parsing là logic thuần. Tách giúp test parser với fixture mock, không cần load model thật.
3. **`MCCTableParserService` tách thành 3 sub-component (`ColumnClassifier`, `EntryGrouper`, `MCCEntryParser`)**: Mỗi sub-component có 1 trách nhiệm rõ ràng và có thể test độc lập bằng fixture nhỏ (không cần load model OCR). `MCCTableParserService` đóng vai trò orchestrator gọi tuần tự.
4. **Column detection dùng % cố định (không dynamic clustering)**: Layout bảng VISA nhất quán — 4 cột tỷ lệ x cố định. Fixed % đơn giản, predictable, dễ test, không cần numpy/DBSCAN.
5. **Tách `title` và `description` thay vì gộp `title_description`**: Downstream mapping cần title riêng để match merchant name; description riêng để tìm kiếm full-text. Tách ở tầng model tốt hơn là để downstream phải split.
6. **`similar_merchants: list[SimilarMerchant]` thay vì `list[str]`**: Structured data cho phép downstream tra cứu cross-reference theo MCC code mà không cần parse lại string.
7. **Dedup strategy: giữ `description` dài hơn**: Khi cùng MCC xuất hiện ở nhiều ảnh (trang bị split), entry với description đầy đủ hơn thường là trang chính. Không merge bằng `\n` để tránh duplicate content.
8. **Không có `visualize_results` trong V1**: Lab script (`labs/mcc_extractor_surya.py`) đủ để debug thủ công. Có thể thêm sau nếu cần.
9. **Batch processing với `extract_lines_batch` (2026-04-18)**: Dataset tăng lên 83 ảnh. Chọn mini-batch `batch_size=8` hardcode — tận dụng native Surya batch API `recognition_predictor(images_list, ...)`. `OCRService` Protocol thay `extract_lines(image)` bằng `extract_lines_batch(images)` vì Use Case chỉ cần batch call. `extract_lines()` giữ trong concrete class nhưng không cần trong Protocol (YAGNI). Batch skip nếu toàn bộ đã có checkpoint — tránh gọi OCR lãng phí. Phân biệt OCR-level error (toàn batch fail) vs parse-level error (1 ảnh fail) để đảm bảo checkpoint chính xác.
10. **Alternatives considered:**
   - Giữ Florence-2: bị loại vì cần CUDA/GPU hoặc chậm trên CPU; không native MPS.
   - Tesseract OCR: bbox pixel-perfect nhưng độ chính xác thấp hơn với ảnh scan nghiêng/nhiễu.
   - Dynamic clustering (DBSCAN) cho column detection: bị loại cho V1 — cần numpy, phức tạp hơn, chưa cần thiết với layout VISA nhất quán.
   - `click` cho CLI: bị loại để giảm dependency; argparse đủ dùng.

## Non-Functional Requirements
**Hiệu suất & chất lượng:**

- **Performance:**
  - Load 3 Surya predictor một lần trước vòng lặp batch; tái dùng toàn session.
  - Batch processing `batch_size=8`: ước tính ~3.5 phút trên Apple M1/M2 MPS (vs ~20 phút serial).
  - Target tổng ≤ 10 phút trên M1/M2 MPS, ≤ 30 phút trên CPU thuần túy.
  - `batch_size=8` hardcode (không expose CLI flag ở V1); mỗi batch ~64MB RAM — an toàn với 8GB RAM.
- **Scalability:**
  - Batch inference (`batch_size=8`) implemented trong V1 — tận dụng native Surya batch API.
  - Nếu dataset tăng tiếp (> 200 ảnh), có thể tăng `batch_size` hoặc thêm multiprocessing ở V2.
- **Security:**
  - Chỉ đọc ảnh local và ghi JSON local; không có network call ngoài lần đầu tải weights.
  - Pin phiên bản `surya-ocr`, `Pillow` trong `requirements.txt`.
- **Reliability:**
  - Exception trên 1 ảnh không crash toàn bộ pipeline; log `WARNING` kèm tên file, tiếp tục ảnh kế tiếp.
  - Validate `MCCEntry` qua pydantic trước khi ghi JSON (fail-fast nếu thiếu required field).
  - `--resume` + checkpoint đảm bảo idempotency khi pipeline bị ngắt giữa chừng.
- **Observability:**
  - Log (loguru): số ảnh input, số entry parse thành công/lỗi, tổng thời gian, device đang dùng (MPS/CPU).
  - Progress bar (`tqdm`): `Processing N/M [████░░] X%` cập nhật sau mỗi ảnh.
