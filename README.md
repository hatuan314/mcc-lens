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

Sử dụng lệnh `convert-mcc` để chuyển đổi ảnh MCC sang JSON:

```bash
# Cơ bản - sử dụng thư mục mặc định
python3 main.py convert-mcc

# Tùy chỉnh thư mục input/output
python3 main.py convert-mcc --input-dir path/to/images --output path/to/output.json

# Chọn device (auto/cuda/mps/cpu)
python3 main.py convert-mcc --device cuda

# Tùy chỉnh ngưỡng Y cho row grouping (mặc định 0.01)
python3 main.py convert-mcc --y-threshold 0.02

# Resume từ checkpoint
python3 main.py convert-mcc --resume
```

**Tham số:**

- `--input-dir, -i`: Thư mục chứa ảnh MCC (mặc định: `assets/mcc-visa`)
- `--output, -o`: Đường dẫn file JSON output (mặc định: `out/mcc-visa.json`)
- `--device, -d`: Device để chạy inference (auto/cuda/mps/cpu, mặc định: auto)
- `--y-threshold`: Ngưỡng trục Y cho row grouping theo % chiều cao ảnh (mặc định: 0.01)
- `--resume`: Resume từ checkpoint, bỏ qua ảnh đã xử lý

**Yêu cầu phần cứng:**

- RAM ≥ 8GB
- Khuyến nghị GPU ≥ 6GB VRAM cho tốc độ ổn định
- Lần chạy đầu cần kết nối Internet để tải Florence-2 model (~1.5GB)

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
