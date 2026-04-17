---
auto_execution_mode: 0
description: So sánh triển khai với tài liệu thiết kế và yêu cầu để đảm bảo sự phù hợp.
---

So sánh triển khai hiện tại với thiết kế trong `docs/ai/design/` và yêu cầu trong `docs/ai/requirements/`.

1. Nếu chưa được cung cấp, hãy hỏi: mô tả tính năng/branch, danh sách file đã sửa đổi, tài liệu thiết kế liên quan, và bất kỳ ràng buộc hoặc giả định nào đã biết.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature implementation alignment>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. Đối với mỗi tài liệu thiết kế: tóm tắt các quyết định kiến trúc chính và ràng buộc, làm nổi bật các thành phần, interface, và luồng dữ liệu phải được tôn trọng.
4. So sánh từng file: xác nhận triển khai phù hợp với ý định thiết kế, ghi chú các sai lệch hoặc phần bị thiếu, đánh dấu các khoảng logic, trường hợp biên, hoặc vấn đề bảo mật, đề xuất các đơn giản hóa hoặc refactor, và xác định các bài kiểm tra hoặc cập nhật tài liệu bị thiếu.
5. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu các bài học/pattern phù hợp lặp lại bằng thực hiện luồng nghiệp vụ sau:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
6. Tóm tắt các phát hiện với các bước tiếp theo được đề xuất.
7. **Hướng dẫn Lệnh Tiếp theo** — Nếu tìm thấy các vấn đề thiết kế lớn, quay lại `/review-design` hoặc `/execute-plan`; nếu phù hợp, tiếp tục với `/writing-test`.
