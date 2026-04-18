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
