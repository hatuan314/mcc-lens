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

### Map VSIC to MCC

Sử dụng lệnh `map-vsic-mcc` để map mã VSIC sang MCC sử dụng **Ollama LLM** (2-stage retrieval):

```bash
# Cơ bản - sử dụng file mặc định
python3 main.py map-vsic-mcc

# Tùy chỉnh input/output
python3 main.py map-vsic-mcc \
  --vsic-input output/vsic-vn.json \
  --mcc-input output/mcc-visa.json \
  --output output/vsic-mcc-mapping.xlsx \
  --output-detail output/vsic-mcc-mapping-detail.xlsx

# Resume từ checkpoint
python3 main.py map-vsic-mcc --resume

# Tùy chỉnh models
python3 main.py map-vsic-mcc \
  --llm-model qwen2.5:14b \
  --embedding-model bge-m3 \
  --top-k 20
```

**Tham số:**

- `--vsic-input`: File JSON VSIC input (mặc định: `output/vsic-vn.json`)
- `--mcc-input`: File JSON MCC input (mặc định: `output/mcc-visa.json`)
- `--output, -o`: File Excel simple output (mặc định: `output/vsic-mcc-mapping.xlsx`)
- `--output-detail`: File Excel detailed output (mặc định: `output/vsic-mcc-mapping-detail.xlsx`)
- `--top-k`: Số lượng MCC candidates gửi đến LLM (mặc định: 60)
- `--ollama-host`: URL Ollama server (mặc định: `http://localhost:11434`)
- `--llm-model`: Tên model LLM (mặc định: `qwen2.5:14b`)
- `--embedding-model`: Tên model embedding (mặc định: `bge-m3`)
- `--template`: File Excel template cho detailed output
- `--resume`: Resume từ checkpoint, bỏ qua VSIC đã xử lý
- `--limit`: Giới hạn số lượng bản ghi VSIC cần xử lý (hữu ích cho việc test nhanh)

**Yêu cầu:**

- Ollama đang chạy: `ollama serve`
- Đã pull models: `ollama pull qwen2.5:14b` và `ollama pull bge-m3`
- RAM ≥ 16GB khuyến nghị cho LLM model lớn

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
