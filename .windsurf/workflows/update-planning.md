---
auto_execution_mode: 0
description: Cập nhật tài liệu lập kế hoạch để phản ánh tiến độ triển khai.
---

Giúp tôi hòa giải tiến độ triển khai hiện tại với tài liệu lập kế hoạch.

1. **Thu thập Ngữ cảnh** — Nếu chưa được cung cấp, hãy hỏi: tên tính năng/branch và trạng thái ngắn gọn, các nhiệm vụ đã hoàn thành kể từ lần cập nhật cuối, các nhiệm vụ mới được phát hiện, các blocker hoặc rủi ro hiện tại, và đường dẫn tài liệu kế hoạch (mặc định `docs/ai/planning/feature-{name}.md`).
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature planning updates>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Review & Hòa giải** — Tóm tắt các cột mốc hiện có, phân tích nhiệm vụ, và phụ thuộc từ tài liệu kế hoạch. Đối với mỗi nhiệm vụ đã lập kế hoạch: đánh dấu trạng thái (đã hoàn thành / đang tiến hành / bị chặn / chưa bắt đầu), ghi chú thay đổi phạm vi, ghi lại các blocker, xác định các nhiệm vụ bị bỏ qua hoặc thêm.
4. **Tạo Danh sách Nhiệm vụ Đã cập nhật** — Tạo một checklist được cập nhật được nhóm theo: Đã hoàn thành, Đang tiến hành, Bị chặn, Công việc Mới được Phát hiện — với ghi chú ngắn cho mỗi nhiệm vụ.
5. **Lưu Trữ Kiến thức Tái sử dụng** — Nếu các quy ước lập kế hoạch mới hoặc quy tắc xử lý rủi ro xuất hiện, thực hiện luồng nghiệp vụ sau để lưu trữ:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
6. **Các Bước Tiếp theo & Tóm tắt** — Đề xuất 2-3 nhiệm vụ có thể hành động tiếp theo và chuẩn bị một đoạn tóm tắt cho tài liệu kế hoạch.
7. **Hướng dẫn Lệnh Tiếp theo** — Quay lại `/execute-plan` cho công việc còn lại. Khi tất cả các nhiệm vụ triển khai hoàn thành, chạy `/check-implementation`.
