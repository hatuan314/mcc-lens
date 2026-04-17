---
auto_execution_mode: 0
description: Thực thi kế hoạch tính năng từng nhiệm vụ một.
---

Giúp tôi làm việc qua một kế hoạch tính năng từng nhiệm vụ một.

1. **Thu thập Ngữ cảnh** — Nếu chưa được cung cấp, hãy hỏi: tên tính năng (kebab-case, ví dụ: `user-authentication`), mô tả ngắn gọn tính năng/branch, đường dẫn tài liệu kế hoạch (mặc định `docs/ai/planning/feature-{name}.md`), và bất kỳ tài liệu hỗ trợ nào (thiết kế, yêu cầu, triển khai).
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature implementation plan>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Tải & Trình bày Kế hoạch** — Đọc tài liệu kế hoạch và phân tích danh sách nhiệm vụ (tiêu đề + checkboxes). Trình bày hàng đợi nhiệm vụ được sắp xếp theo nhóm phần, với trạng thái: `todo`, `in-progress`, `done`, `blocked`.
4. **Thực thi Nhiệm vụ Tương tác** — Đối với mỗi nhiệm vụ theo thứ tự: hiển thị ngữ cảnh và văn bản đầy đủ, tham chiếu tài liệu thiết kế/yêu cầu liên quan, đề xuất phác thảo các bước con trước khi bắt đầu, nhắc cập nhật trạng thái (`done`, `in-progress`, `blocked`, `skipped`) với ghi chú ngắn sau khi làm, và nếu bị chặn ghi lại blocker và chuyển đến danh sách "Blocked".
5. **Cập nhật Tài liệu Kế hoạch** — Sau mỗi nhiệm vụ hoàn thành hoặc thay đổi trạng thái, chạy `/update-planning` để giữ `docs/ai/planning/feature-{name}.md` chính xác.
6. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu hướng dẫn/quyết định triển khai tái sử dụng bằng thực hiện luồng nghiệp vụ sau:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
7. **Tóm tắt Phiên** — Tạo tóm tắt: Đã hoàn thành, Đang tiến hành (với các bước tiếp theo), Bị chặn (với các blocker), Bỏ qua/Trì hoãn, và Nhiệm vụ Mới.
8. **Hướng dẫn Lệnh Tiếp theo** — Tiếp tục `/execute-plan` cho đến khi hoàn thành kế hoạch; sau đó chạy `/check-implementation`.
