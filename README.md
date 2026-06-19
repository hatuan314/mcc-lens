# MCC Lens

Dự án Python theo Clean Architecture với cấu trúc MVC.

## Cấu trúc dự án

```
mcc-lens/
├── app/
│   ├── models/          # Schema và Business Entities
│   ├── views/           # Giao diện người dùng hoặc format dữ liệu
│   ├── controllers/     # Xử lý đầu vào và điều phối
│   ├── services/        # Business Logic cốt lõi
│   └── repositories/    # Logic truy vấn dữ liệu
├── tests/               # Unit tests
├── requirements.txt     # Python dependencies
└── main.py             # Entry point
```

## Cài đặt

```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate  # macOS/Linux
# hoặc
venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
python3 main.py
```

### Convert MCC Images to JSON

Sử dụng lệnh `convert-mcc` để chuyển đổi ảnh MCC sang JSON bằng **Surya OCR**:

```bash
# Cơ bản - sử dụng thư mục mặc định
python3 main.py convert-mcc

# Tùy chỉnh thư mục input/output
python3 main.py convert-mcc --input-dir path/to/images --output path/to/output.json

# Resume từ checkpoint
python3 main.py convert-mcc --resume
```

**Tham số:**

- `--input-dir, -i`: Thư mục chứa ảnh MCC (mặc định: `assets/mcc-visa`)
- `--output, -o`: Đường dẫn file JSON output (mặc định: `out/mcc-visa.json`)
- `--resume`: Resume từ checkpoint, bỏ qua ảnh đã xử lý

**Schema JSON output:**

```json
{
  "source": "out/mcc-visa.json",
  "total_mcc_count": 91,
  "mcc_list": [
    {
      "mcc": "0742",
      "title": "Veterinary Services",
      "description": "...",
      "included_in_mcc": ["Pet Hospitals", "Pet Clinics"],
      "similar_merchants": [
        {"mcc": "5995", "title": "Pet Shops, Pet Foods and Supplies Store"}
      ],
      "source_image": "page-27.jpg",
      "unparsed": false
    }
  ]
}
```

**Yêu cầu phần cứng:**

- RAM ≥ 8GB
- Apple M1/M2 được khuyến nghị (Surya chạy native trên MPS, không cần CUDA)
- Lần chạy đầu cần kết nối Internet để tải Surya weights (~1-2GB) từ HuggingFace Hub
- Tốc độ tham khảo: ~40s/ảnh trên Apple Silicon MPS

### Convert VSIC Excel to JSON

Sử dụng lệnh `convert-vsic` để chuyển đổi file Excel VSIC sang JSON:

```bash
# Cơ bản - sử dụng file mặc định
python3 main.py convert-vsic

# Tùy chỉnh file input/output
python3 main.py convert-vsic --input path/to/vsic.xlsx --output path/to/vsic.json
```

**Tham số:**

- `--input, -i`: File Excel input (mặc định: `assets/vsic-vn/vsic.xlsx`)
- `--output, -o`: File JSON output (mặc định: `output/vsic.json`)

### Convert VSIC 2025 Excel to JSON

Sử dụng lệnh `convert-vsic-2025` để chuyển đổi file `vsic-2025.xlsx` sang JSON nested:

```bash
# Cơ bản - dùng input/output mặc định
python3 main.py convert-vsic-2025

# Tùy chỉnh file input/output
python3 main.py convert-vsic-2025 \
  --input assets/vsic-vn/vsic-2025.xlsx \
  --output output/vsic-vn.json
```

**Tham số:**

- `--input, -i`: File Excel input (mặc định: `assets/vsic-vn/vsic-2025.xlsx`)
- `--output, -o`: File JSON output (mặc định: `output/vsic-vn.json`)

**Schema JSON output (rút gọn):**

```json
{
  "source": "assets/vsic-vn/vsic-2025.xlsx",
  "total_vsic_count": 2,
  "vsic_list": [
    {
      "code": "0111",
      "title": "Trồng lúa",
      "children_level5": [
        { "code": "01110", "title": "Trồng lúa hạt" }
      ]
    }
  ]
}
```

Lưu ý: `source` luôn là **input file path** thực tế được dùng để convert.

### Embed (tạo artifact embedding)

Embedding và LLM re-rank được tách thành 2 lệnh dùng chung một file artifact `.npz`. Bước `embed` chạy trên **Colab/GPU** để nhúng toàn bộ MCC + VSIC qua Ollama `bge-m3`, tạo ra file artifact tự chứa (vectors + code + title + description + meta).

```bash
# Cơ bản
python3 main.py embed

# Tùy chỉnh + lưu lên Google Drive (Colab)
python3 main.py embed \
  --mcc-input output/mcc-visa.json \
  --vsic-input output/vsic-vn.json \
  --output output/embed-artifact.npz \
  --gdrive-output-dir /content/drive/MyDrive/projects/mcc-lens \
  --embedding-model bge-m3
```

**Tham số:**

- `--mcc-input`: File JSON MCC input (mặc định: `output/mcc-visa.json`)
- `--vsic-input`: File JSON VSIC input (mặc định: `output/vsic-vn.json`)
- `--output, -o`: File artifact `.npz` output (mặc định: `output/embed-artifact.npz`)
- `--gdrive-output-dir`: Thư mục Google Drive để ghi `embed-artifact.npz` (Colab)
- `--ollama-host`: URL Ollama server (mặc định: `http://localhost:11434`)
- `--embedding-model`: Model embedding qua Ollama (mặc định: `bge-m3`)

**Yêu cầu:** Ollama đang chạy và đã pull `bge-m3` (`ollama pull bge-m3`).

> **Lưu ý:** Entry bị lỗi NaN → `embed` vẫn ghi artifact với vector 0 cho entry đó và ghi `zero_vector_codes` vào meta (entry xếp hạng thấp). Sau khi tạo xong, tải `embed-artifact.npz` về thư mục `output/` local để chạy `map-vsic-mcc`.

### Map VSIC to MCC

Sử dụng lệnh `map-vsic-mcc` để map mã VSIC sang MCC. Lệnh này là **consumer-only**: đọc artifact `.npz` từ bước `embed`, KHÔNG tự nhúng embedding (Stage 1 cosine top-K trên vectors artifact, Stage 2 LLM re-rank). Hỗ trợ hai LLM provider: **Ollama** (local) và **WokuShop API**.

LLM provider được chọn qua biến môi trường `LLM_PROVIDER` trong file `.env`. Artifact thiếu/hỏng/sai dimension → hard-fail với exit code ≠ 0.

#### Provider: Ollama (mặc định)

```bash
# .env
LLM_PROVIDER=ollama
```

```bash
# Cơ bản - sử dụng file mặc định
python3 main.py map-vsic-mcc

# Tùy chỉnh artifact/output và model
python3 main.py map-vsic-mcc \
  --embeddings output/embed-artifact.npz \
  --output output/vsic-mcc-mapping.xlsx \
  --output-detail output/vsic-mcc-mapping-detail.xlsx \
  --llm-model qwen3.5:9b

# Chạy với Google Drive
python3 main.py map-vsic-mcc \
  --gdrive-output-dir /content/drive/MyDrive/projects/mcc-lens \
  --llm-model qwen3.5:9b \
  --resume
```

**Yêu cầu:** Đã có `embed-artifact.npz` (từ lệnh `embed`) và Ollama đang chạy với LLM model (embedding KHÔNG cần nữa):

```bash
ollama pull qwen3.5:9b
```

#### Provider: WokuShop API

```bash
# .env
LLM_PROVIDER=wokushop
WOKUSHOP_API_KEY=sk-your-api-key-here
WOKUSHOP_BASE_URL=https://llm.wokushop.com/v1
WOKUSHOP_MODEL=gpt-4o
```

```bash
# Cơ bản - WokuShop làm LLM, embedding lấy từ artifact (không cần Ollama)
python3 main.py map-vsic-mcc

# Tùy chỉnh artifact/output
python3 main.py map-vsic-mcc \
  --embeddings output/embed-artifact.npz \
  --output output/vsic-mcc-mapping.xlsx \
  --output-detail output/vsic-mcc-mapping-detail.xlsx \
  --resume
```

**Yêu cầu:** Chỉ cần `embed-artifact.npz` và `WOKUSHOP_API_KEY`. **Không cần Ollama** khi dùng WokuShop (embedding đã nằm sẵn trong artifact).

> **Lưu ý:** Khi dùng WokuShop, `--llm-model` bị bỏ qua. Model LLM được lấy từ `WOKUSHOP_MODEL` trong `.env`.

**Tham số CLI:**

- `--embeddings`: File artifact `.npz` từ lệnh `embed` (mặc định: `output/embed-artifact.npz`)
- `--output, -o`: File Excel simple output (mặc định: `output/vsic-mcc-mapping.xlsx`)
- `--output-detail`: File Excel detailed output (mặc định: `output/vsic-mcc-mapping-detail.xlsx`)
- `--gdrive-output-dir`: Thư mục gốc trên Google Drive để lưu output, checkpoint, và đọc artifact (Colab)
- `--top-k`: Số lượng MCC candidates gửi đến LLM (mặc định: 60)
- `--ollama-host`: URL Ollama server khi dùng Ollama LLM provider (mặc định: `http://localhost:11434`)
- `--llm-model`: Tên model LLM khi dùng Ollama provider (mặc định: `qwen3.5:9b`)
- `--template`: File Excel template cho detailed output
- `--resume`: Resume từ checkpoint, bỏ qua VSIC đã xử lý
- `--limit`: Giới hạn số lượng bản ghi VSIC cần xử lý

### Running on Google Colab

Pipeline được tách thành 2 notebook chạy lần lượt trên Google Colab với GPU:

**Bước 1 — Embed (`colab/embed_vsic_mcc_colab.ipynb`):**
- Mount Drive, clone code, cài deps tối thiểu (`colab/requirements-mapping.txt`).
- Cài Ollama, pull **chỉ `bge-m3`**.
- Chạy `embed` → ghi `embed-artifact.npz` lên Drive.

**Bước 2 — Map (`colab/mapping_vsic_mcc_colab.ipynb`):**
- Pull **chỉ `qwen3.5:9b`** (không cần `bge-m3` nữa).
- Đọc `embed-artifact.npz` từ Drive → chạy `map-vsic-mcc` → ghi Excel + checkpoint lên Drive.

> Hoặc tải `embed-artifact.npz` về máy local và chạy `map-vsic-mcc` local (với WokuShop thì không cần Ollama).

**Yêu cầu:**

- Ollama đang chạy: `ollama serve`
- Bước 1 (embed) cần `ollama pull bge-m3`; bước 2 (map) cần `ollama pull qwen3.5:9b`
- RAM ≥ 16GB khuyến nghị cho LLM model lớn ở bước 2

**Output:**

- **Simple Excel**: 3 cột (VSIC, MCC, Tên ngành) với top-1 MCC
- **Detailed Excel**: 14 cột với top-3 MCC, score, và nhận xét từ LLM

**Checkpoint:**

- File checkpoint: `output/.mapping-progress.json`
- Tự động lưu sau mỗi VSIC xử lý xong
- Sử dụng `--resume` để tiếp tục từ checkpoint

## Quy chuẩn code

- Tuân thủ PEP 8
- Sử dụng Type Hints
- Docstrings theo chuẩn Google
- Clean Architecture & SOLID principles

## Testing

```bash
# Chạy tests
pytest

# Chạy tests với coverage
pytest --cov=app tests/
```

## Code Quality

```bash
# Format code
black app/

# Check linting
flake8 app/

# Type checking
mypy app/
```
