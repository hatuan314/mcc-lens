# Quy tắc phát triển dự án Python (Vietnamese)

File này chứa các chỉ thị bắt buộc mà Claude phải tuân thủ khi làm việc trong dự án này.

## 1. Khởi động và Bối cảnh (Project Initialization)
- **Tự động kích hoạt:** Luôn đọc và áp dụng các quy tắc này ngay khi bắt đầu phiên làm việc hoặc khi mở dự án.
- **Phân tích bối cảnh:** Trước khi viết code, hãy kiểm tra cấu trúc thư mục hiện tại để đảm bảo tuân thủ kiến trúc đã định nghĩa.

## 2. Tiêu chuẩn Coding Style (Python Style)
- **PEP 8:** Tuân thủ tuyệt đối chuẩn PEP 8 (thụt lề 4 dấu cách, đặt tên biến/hàm kiểu snake_case, tên lớp kiểu PascalCase).
- **Type Hinting:** Luôn sử dụng Type Hints cho các đối số của hàm và giá trị trả về để tăng tính minh bạch.
- **Docstrings:** Viết docstrings theo chuẩn Google hoặc Sphinx cho tất cả các modules, classes và functions.
- **Python Version:** Luôn sử dụng `python3` thay vì `python` khi chạy lệnh terminal hoặc trong script shebang.
- **Dependency Management:** Luôn cập nhật file `requirements.txt` khi import thư viện mới vào dự án.

## 3. Clean Code & SOLID
- **Clean Code:** - Đặt tên có ý nghĩa, tránh viết tắt khó hiểu.
  - Hàm phải ngắn gọn, chỉ làm một việc duy nhất (Single Responsibility).
  - Hạn chế số lượng đối số truyền vào hàm (tối ưu là dưới 3).
- **SOLID Principles:**
  - **S:** Mỗi class chỉ đảm nhận một trách nhiệm duy nhất.
  - **O:** Ưu tiên mở rộng thông qua kế thừa/interface thay vì sửa đổi code cũ.
  - **L:** Đảm bảo các lớp con có thể thay thế lớp cha mà không làm hỏng logic.
  - **I:** Chia nhỏ các interfaces thay vì dùng một interface quá lớn.
  - **D:** Phụ thuộc vào trừu tượng (abstraction), không phụ thuộc vào cụ thể (concretion).

## 4. Kiến trúc (Clean Architecture & MVC)
- **Cấu trúc thư mục:** Phân chia dự án theo các lớp (layers):
  - `domain/`: Chứa entities và logic nghiệp vụ lõi (Business Logic).
  - `use_cases/`: Chứa các quy trình xử lý cụ thể của ứng dụng.
  - `infrastructure/`: Chứa code liên quan đến database, API bên thứ 3, v.v.
  - `presentation/` (hoặc `interfaces/`): Chứa Controllers và Views.
- **Mô hình MVC:**
  - **Model:** Định nghĩa cấu trúc dữ liệu và logic liên quan đến dữ liệu.
  - **View:** Giao diện người dùng hoặc định dạng dữ liệu trả về (JSON/HTML).
  - **Controller:** Tiếp nhận request, điều phối Use Cases và trả về kết quả cho View.
- **Luật phụ thuộc:** Code ở các lớp bên trong (Domain) không bao giờ được biết thông tin về các lớp bên ngoài (Infrastructure/API).

## 5. Quy trình thực hiện nhiệm vụ
1. **Suy nghĩ (Thinking):** Phân tích yêu cầu dựa trên SOLID và Clean Architecture.
2. **Lập kế hoạch:** Trình bày ngắn gọn các bước sẽ thực hiện trước khi viết code.
3. **Thực thi:** Viết code tuân thủ các chuẩn Python Style nêu trên.
4. **Kiểm tra:** Đảm bảo code mới không vi phạm cấu trúc MVC và các quy tắc Clean Code.