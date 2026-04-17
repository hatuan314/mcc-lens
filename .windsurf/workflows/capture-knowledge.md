---
auto_execution_mode: 0
description: Tài liệu hóa một điểm nhập code trong tài liệu kiến thức.
---

Hướng dẫn tôi tạo sự hiểu có cấu trúc về một điểm nhập code và lưu nó vào tài liệu kiến thức.

1. **Thu thập & Xác thực Điểm Nhập** — Nếu chưa được cung cấp, hãy hỏi: điểm nhập (file, thư mục, hàm, API), tại sao nó quan trọng (tính năng, bug, điều tra), và độ sâu mong muốn hoặc các khu vực tập trung. Xác nhận điểm nhập tồn tại; nếu mơ hồ hoặc không tìm thấy, làm rõ hoặc đề xuất các phương án thay thế.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<entry point or subsystem>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Thu thập Ngữ cảnh Nguồn** — Đọc file/module chính và tóm tắt mục đích, exports, các pattern chính. Đối với thư mục: liệt kê cấu trúc, làm nổi bật các module chính. Đối với hàm/API: nắm bắt signature, tham số, giá trị trả về, xử lý lỗi. Trích xuất các đoạn mã quan trọng (tránh các đoạn lớn).
4. **Phân tích Phụ thuộc** — Xây dựng view phụ thuộc lên đến độ sâu 3, theo dõi các node đã truy cập để tránh vòng lặp. Phân loại: imports, lời gọi hàm, services, packages bên ngoài. Lưu ý các hệ thống bên ngoài hoặc code được tạo để loại trừ.
5. **Tổng hợp Giải thích** — Soạn thảo tổng quan (mục đích, ngôn ngữ, hành vi cấp cao). Chi tiết logic cốt lõi, luồng thực thi, các pattern chính. Làm nổi bật xử lý lỗi, hiệu suất, các cân nhắc bảo mật. Xác định các cải tiến hoặc rủi ro tiềm năng.
6. **Tạo Tài liệu** — Chuẩn hóa tên thành kebab-case (`calculateTotalPrice` → `calculate-total-price`). Tạo `docs/ai/implementation/knowledge-{name}.md` với các phần: Tổng quan, Chi tiết Triển khai, Phụ thuộc, Sơ đồ Trực quan, Các Góc nhìn Thêm, Metadata, Các Bước Tiếp theo. Bao gồm sơ đồ mermaid khi chúng làm rõ các luồng hoặc mối quan hệ. Thêm metadata (ngày phân tích, độ sâu, các file đã chạm tới).
7. **Lưu Trữ Kiến thức Tái sử dụng** — Nếu các góc nhìn nên tồn tại qua các phiên, thực hiện luồng nghiệp vụ sau để lưu trữ:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
8. **Xem xét & Hành động Tiếp theo** — Tóm tắt các góc nhìn chính và các câu hỏi mở. Đề xuất các khu vực liên quan để đi sâu hơn, xác nhận đường dẫn file, và đề xuất `/remember` cho các quy tắc tồn tại lâu dài.
