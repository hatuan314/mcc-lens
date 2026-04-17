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
