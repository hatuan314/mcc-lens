---
phase: design
title: System Design & Architecture - Convert MCC Image to JSON
description: Thiết kế pipeline CLI dùng Florence-2 large để OCR ảnh MCC VISA và xuất JSON có cấu trúc, tuân thủ Clean Architecture.
---

# System Design & Architecture

## Architecture Overview
**Cấu trúc hệ thống ở mức cao:**

```mermaid
graph TD
  CLI[CLI Entry<br/>main.py convert-mcc] --> Controller[MCCConvertController]
  Controller --> UseCase[ConvertMCCImagesUseCase]
  UseCase --> Repo[MCCImageRepository<br/>đọc assets/mcc-visa/*.jpg]
  UseCase --> VisionSvc[Florence2VisionService<br/>OCR_WITH_REGION → list[BBoxTextItem]]
  UseCase --> TableSvc[TableReconstructionService<br/>BBoxTextItem → 4-col table]
  UseCase --> Parser[MCCParserService<br/>table rows → MCCEntry list]
  UseCase --> Writer[MCCJsonRepository<br/>ghi JSON output]
  UseCase --> Progress[ProgressBarView<br/>tqdm]
  UseCase --> Checkpoint[CheckpointRepository<br/>.mcc-convert-progress.json]
  VisionSvc -.->|load weights| HF[(HuggingFace Hub<br/>microsoft/Florence-2-large)]
```

### Thành phần và trách nhiệm
- **CLI Entry (`main.py`)**: Parse argparse, khởi động logging, gọi Controller.
- **Controller (`app/controllers/mcc_convert_controller.py`)**: Tiếp nhận tham số (input_dir, output_path, device, y_threshold_pct…), điều phối Use Case, map exception thành exit code.
- **Use Case (`app/services/convert_mcc_images_use_case.py`)**: Orchestration thuần — lặp qua từng ảnh, gọi vision service → table reconstruction → parser → writer, cập nhật progress. Không biết chi tiết Florence-2.
- **Florence-2 Vision Service (`app/services/florence2_vision_service.py`)**: Wrap `transformers.AutoModelForCausalLM` + `AutoProcessor`, chạy task `<OCR_WITH_REGION>` với `max_new_tokens=3072`, `num_beams=3`. Trả về `list[BBoxTextItem]` chứa text và tọa độ bbox `[y1, x1, y2, x2]` (normalized 0–1000).
- **Table Reconstruction Service (`app/services/table_reconstruction_service.py`)**: Nhận `list[BBoxTextItem]` + kích thước ảnh → tái dựng bảng 4 cột VISA. Gồm 3 thuật toán:
  1. **Row grouping**: nhóm bbox theo trục Y với ngưỡng `y_threshold_pct` (default 0.01 = 1% chiều cao ảnh).
  2. **Column assignment**: dynamic clustering hoặc mốc X theo % (MCC ~10% trái, Title/Desc ~50%, Included ~75%, Similar ~90%).
  3. **Multi-line merging**: phát hiện hàng MCC mới (cột `mcc` có giá trị) vs dòng tiếp theo (cột `mcc` trống) — gộp text lại.
  Expose thêm `visualize_results(image_path, rows) -> PIL.Image` để debug trực quan.
- **MCC Parser Service (`app/services/mcc_parser_service.py`)**: Nhận danh sách row đã tái dựng → validate 4-digit MCC → tạo `list[MCCEntry]`. Entry không hợp lệ: `mcc=""`, `_unparsed=True`.
- **Repositories**:
  - `MCCImageRepository`: Liệt kê/đọc ảnh từ thư mục input.
  - `MCCJsonRepository`: Ghi danh sách `MCCEntry` ra JSON (UTF-8, indent=2). Khi dedup: merge `title_description` + `included` từ tất cả entry cùng `mcc` (nối bằng `\n`).
  - `CheckpointRepository`: Đọc/ghi/xóa checkpoint file (`.mcc-convert-progress.json`) — đặt cùng thư mục với output JSON. Ghi thêm tên ảnh sau mỗi lần thành công; xóa toàn bộ khi pipeline hoàn thành.
- **Views**: `ProgressBarView` bọc `tqdm` để Use Case không phụ thuộc trực tiếp thư viện UI.

### Công nghệ & lý do chọn
| Thành phần | Công nghệ | Lý do |
|---|---|---|
| Vision-Language | `transformers` + `torch` + Florence-2 large | Yêu cầu bắt buộc của Order; Florence-2 hỗ trợ OCR và grounding mạnh, license MIT. |
| CLI | `argparse` (stdlib) | Tránh thêm dependency; đủ cho use case đơn giản. |
| Progress bar | `tqdm` | Gọn nhẹ, quen thuộc, tích hợp tốt terminal; `rich` là lựa chọn thay thế nếu cần UI đẹp hơn. |
| Logging | `loguru` | Đã có trong `requirements.txt`. |
| Image I/O | `Pillow` | Florence-2 processor yêu cầu PIL Image; dùng thêm cho `visualize_results`. |
| Validation | `pydantic` | Đã có; dùng cho `MCCEntry` model. |
| Clustering (optional) | `numpy` | Dùng cho DBSCAN-style row grouping nếu threshold tĩnh không đủ. |

## Data Models
**Dữ liệu cần quản lý:**

### `BBoxTextItem` (transfer object — `app/models/mcc_entry.py`)
```python
@dataclass
class BBoxTextItem:
    text: str
    bbox: tuple[float, float, float, float]  # y1, x1, y2, x2 (normalized 0–1000)
```

### `MCCEntry` (domain model — `app/models/mcc_entry.py`)
```python
class MCCEntry(BaseModel):
    mcc: str                          # "0742"; rỗng "" nếu không parse được
    title_description: str            # gộp cột "MCC Title/Description"
    included: str = ""                # cột "Included in this MCC"
    similar_merchants: list[str] = []
    source_image: str                 # tên file ảnh nguồn (provenance)
    _unparsed: bool = False           # True khi mcc = "" do parse thất bại
```

### Output JSON schema
- Một file tổng `mcc-visa.json` chứa `list[MCCEntry]` đã serialize.
```json
[
  {
    "mcc": "0742",
    "title_description": "Veterinary Services. Merchants classified with this MCC are...",
    "included": "Animal Doctors, Pet Hospitals, Pet Clinics",
    "similar_merchants": ["5995 - Pet Shops, Pet Foods and Supplies Store"],
    "source_image": "visa-merchant-data-standards-manual-hình ảnh-01.jpg",
    "_unparsed": false
  },
  {
    "mcc": "",
    "title_description": "",
    "included": "",
    "similar_merchants": [],
    "source_image": "visa-merchant-data-standards-manual-hình ảnh-28.jpg",
    "_unparsed": true
  }
]
```

### Luồng dữ liệu
1. Repository liệt kê file `*.jpg` trong `input_dir` → `list[Path]`.
2. Nếu `--resume`: CheckpointRepository tải danh sách ảnh đã xong → bỏ qua trong vòng lặp.
3. Use Case lặp qua mỗi path → VisionService trả về `list[BBoxTextItem]` (text + bbox).
4. TableReconstructionService nhận `list[BBoxTextItem]` + kích thước ảnh → trả về danh sách row (dict 4 cột).
5. MCCParserService chuyển row list thành `list[MCCEntry]` (entry không hợp lệ: `mcc=""`, `_unparsed=True`).
6. CheckpointRepository ghi tên ảnh vào checkpoint sau mỗi ảnh thành công.
7. Use Case gom tất cả entry; **dedup các entry `_unparsed=False` theo `mcc`** — khi trùng: merge `title_description` và `included` bằng `\n`, giữ nguyên `similar_merchants` (union); giữ nguyên tất cả entry `_unparsed=True`.
8. MCCJsonRepository ghi JSON; CheckpointRepository xóa checkpoint file.

## API Design
**Không có API HTTP** — giao tiếp duy nhất là CLI.

### CLI interface
```
python3 main.py convert-mcc \
  --input-dir    assets/mcc-visa \          # default: assets/mcc-visa
  --output       out/mcc-visa.json \        # default: out/mcc-visa.json
  --device       auto \                     # auto | cpu | cuda  (default: auto)
  --y-threshold  0.01 \                     # y_threshold_pct (default: 0.01 = 1%)
  --resume                                  # tiếp tục từ checkpoint (default: off)
```
Checkpoint file được đặt tự động tại `<output-dir>/.mcc-convert-progress.json`.

### Internal interfaces (abstractions — Dependency Rule)
```python
class VisionService(Protocol):
    def extract_regions(self, image_path: Path) -> list[BBoxTextItem]: ...

class TableReconstructor(Protocol):
    def reconstruct(
        self,
        regions: list[BBoxTextItem],
        image_size: tuple[int, int],   # (width, height) pixels
    ) -> list[dict[str, str]]: ...     # list of {mcc, title_description, included, similar_merchants}

    def visualize_results(
        self,
        image_path: Path,
        rows: list[dict[str, str]],
    ) -> "PIL.Image.Image": ...

class MCCParser(Protocol):
    def parse(self, rows: list[dict[str, str]], source: str) -> list[MCCEntry]: ...

class ImageRepository(Protocol):
    def list_images(self, dir_path: Path) -> list[Path]: ...

class JsonRepository(Protocol):
    def save(self, entries: list[MCCEntry], output: Path) -> None: ...

class CheckpointRepository(Protocol):
    def load(self) -> set[str]: ...           # trả về set tên file đã xong
    def mark_done(self, filename: str) -> None: ...
    def clear(self) -> None: ...
```
Use Case phụ thuộc vào các Protocol trên (D trong SOLID), implementation cụ thể nằm ở `services/` & `repositories/`.

## Component Breakdown
**Các khối chính:**

- **Presentation layer**
  - `main.py` — subcommand `convert-mcc`.
  - `app/views/progress_bar_view.py` — wrap tqdm.
- **Controller layer**
  - `app/controllers/mcc_convert_controller.py`.
- **Use case / Service layer**
  - `app/services/convert_mcc_images_use_case.py`
  - `app/services/florence2_vision_service.py` — implements `VisionService`
  - `app/services/table_reconstruction_service.py` — implements `TableReconstructor`
  - `app/services/mcc_parser_service.py` — implements `MCCParser`
  - `app/services/protocols.py` — định nghĩa tất cả Protocol
- **Repository layer**
  - `app/repositories/mcc_image_repository.py`
  - `app/repositories/mcc_json_repository.py`
  - `app/repositories/checkpoint_repository.py`
- **Domain models**
  - `app/models/mcc_entry.py` — `MCCEntry` (pydantic) + `BBoxTextItem` (dataclass)
- **Third-party**
  - HuggingFace Hub (download weights lần đầu).

## Design Decisions
**Vì sao chọn cách này?**

1. **Tách Florence-2 thành service riêng sau Protocol**: Tôn trọng Dependency Inversion — tương lai có thể swap sang model khác (Qwen-VL, GPT-4V) mà không đổi Use Case.
2. **Tách `TableReconstructionService` khỏi `MCCParserService`**: Hai concern độc lập — tái dựng bảng từ bbox (geometric) vs. validate business rule (MCC 4 chữ số). Tách giúp test riêng bằng fixture và tái dùng thuật toán cho Mastercard/JCB.
3. **`VisionService` trả `list[BBoxTextItem]` thay vì `str`**: `<OCR_WITH_REGION>` cung cấp tọa độ không gian — cần thiết cho table reconstruction. Trả `str` sẽ mất thông tin này.
4. **`y_threshold_pct` expose qua CLI**: Tài liệu VISA, Mastercard, NAPAS có mật độ dòng khác nhau. Parameterize cho phép benchmark nhiều ngưỡng (0.005, 0.01, 0.015) mà không sửa code.
5. **Dedup strategy: merge fields**: Khi cùng MCC xuất hiện ở nhiều ảnh (trang bị split), merge `title_description` + `included` bằng `\n`; không dùng last-wins để tránh mất data.
6. **Một file JSON tổng hợp**: Dễ consume cho feature mapping VSIC-to-MCC sau này. Chế độ per-file không thuộc V1 scope.
7. **Không abort khi 1 ảnh lỗi**: Pipeline log lỗi và tiếp tục — phù hợp yêu cầu và UX batch xử lý.
8. **`tqdm` thay vì `rich.progress`**: `tqdm` nhẹ hơn, không chiếm header/footer màn hình, đủ cho yêu cầu "loading bar".
9. **Alternatives considered:**
   - Dùng Tesseract OCR + LLM phụ parse: bị loại vì Order yêu cầu rõ Florence-2.
   - Dùng DBSCAN trên trục Y thay vì % threshold: là phương án nâng cao — implement sau nếu threshold tĩnh không đủ chính xác.
   - Dùng `click` cho CLI: bị loại để giảm dependency; argparse đủ dùng.

## Non-Functional Requirements
**Hiệu suất & chất lượng:**

- **Performance:**
  - Lazy-load Florence-2 (chỉ load khi bắt đầu batch); tái dùng instance cho toàn batch.
  - Cho phép half-precision (`torch.float16`) khi chạy CUDA để giảm VRAM.
- **Scalability:**
  - Hiện xử lý tuần tự; có thể mở rộng sang batch inference (nhiều ảnh/lần) nếu dataset tăng — không implement vòng đầu.
- **Security:**
  - Không có dữ liệu nhạy cảm; chỉ đọc ảnh local và ghi JSON local.
  - Pin phiên bản `transformers`, `torch` trong `requirements.txt` để tránh supply-chain drift.
- **Reliability:**
  - Exception trên 1 ảnh không làm crash toàn bộ; log `WARNING` kèm file name.
  - Trước khi ghi JSON, validate qua `MCCEntry` pydantic (fail-fast nếu thiếu field).
- **Observability:**
  - Log: số ảnh input, số entry parse thành công, số ảnh lỗi, tổng thời gian, device đang dùng.
  - `visualize_results` xuất ảnh debug với bbox + label hàng/cột để kiểm tra trực quan thuật toán.
