---
trigger: always_on
---

# Antigravity Project Rules - Python MVC & Clean Architecture

Tài liệu này định nghĩa các quy chuẩn bắt buộc để AI tuân thủ trong suốt quá trình phát triển dự án này.

## 1. Khởi tạo & Chế độ hoạt động (Execution)
- **Auto-run:** Cascade phải đọc file này ngay khi dự án được mở hoặc khi bắt đầu một Flow mới.
- **Context Awareness:** Luôn kiểm tra cấu trúc thư mục hiện tại để hiểu kiến trúc hệ thống trước khi thực hiện bất kỳ thay đổi nào.

## 2. Tiêu chuẩn Python (Python Style)
- **PEP 8:** Tuân thủ nghiêm ngặt chuẩn PEP 8.
- **Naming:** - Variables/Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Typing:** Sử dụng `typing` module (Type Hints) cho tất cả các định nghĩa hàm.
- **Documentation:** Sử dụng Docstrings chuẩn Google cho mọi public method và class.
- **Python Version:** Luôn sử dụng `python3` thay vì `python` khi chạy lệnh terminal hoặc trong script shebang.
- **Dependency Management:** Luôn cập nhật file `requirements.txt` khi import thư viện mới vào dự án.

## 3. Clean Code & SOLID Principles
- **Clean Code:**
  - "Don't Repeat Yourself" (DRY).
  - Hàm không quá 20 dòng, chỉ làm một nhiệm vụ duy nhất.
  - Tên biến phải mang tính mô tả (Self-documenting code).
- **SOLID:**
  - **S:** Tách biệt logic xử lý dữ liệu khỏi logic giao diện.
  - **O:** Sử dụng Abstract Base Classes (ABC) để cho phép mở rộng mà không sửa đổi code lõi.
  - **L:** Các lớp kế thừa không được thay đổi hành vi mong đợi của lớp cha.
  - **I:** Chia nhỏ interface để tránh các "fat interface".
  - **D:** Sử dụng Dependency Injection (DI) để giảm sự phụ thuộc giữa các module.

## 4. Kiến trúc Hệ thống (Clean Architecture & MVC)
Cascade phải duy trì cấu trúc thư mục theo mô hình sau:
- `app/`
  - `models/`: Định nghĩa Schema và Business Entities.
  - `views/`: Giao diện người dùng hoặc logic format dữ liệu (Schemas/Templates).
  - `controllers/`: Xử lý đầu vào và điều phối giữa Model và View.
  - `services/`: Chứa Business Logic cốt lõi (Domain Services).
  - `repositories/`: Logic truy vấn dữ liệu (Infrastructure layer).
- **Quy tắc phụ thuộc:** Logic nghiệp vụ (Domain/Service) không được phụ thuộc vào chi tiết kỹ thuật (Database/Framework).

## 5. Quy trình làm việc của Cascade
1. **Phân tích:** Trước khi code, AI phải giải thích phương án thiết kế dựa trên Clean Architecture.
2. **Kế hoạch (Plan):** Liệt kê các file sẽ tạo hoặc sửa đổi.
3. **Thực hiện (Step-by-step):** Code từng module, đảm bảo có unit test đi kèm nếu được yêu cầu.
4. **Kiểm chứng:** Tự động kiểm tra lỗi syntax và sự phù hợp với các file hiện có trong dự án.

