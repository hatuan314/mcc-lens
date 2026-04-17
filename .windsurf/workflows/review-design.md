---
auto_execution_mode: 0
description: Review thiết kế tính năng để đảm bảo tính đầy đủ.
---

Review tài liệu thiết kế trong `docs/ai/design/feature-{name}.md` (và README cấp dự án nếu liên quan).

1. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature design architecture>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
2. Tóm tắt:
   - Tổng quan kiến trúc (đảm bảo sơ đồ mermaid có mặt và chính xác)
   - Các thành phần chính và trách nhiệm của chúng
   - Lựa chọn công nghệ và lý do
   - Mô hình dữ liệu và mối quan hệ
   - Hợp đồng API/interface (đầu vào, đầu ra, auth)
   - Các quyết định thiết kế chính và sự đánh đổi
   - Các yêu cầu phi chức năng phải được bảo tồn
3. **Làm rõ và khám phá (lặp cho đến khi hội tụ)**:
   - **Đặt câu hỏi làm rõ** cho mỗi khoảng trống, sự không nhất quán, hoặc sự không phù hợp giữa yêu cầu và thiết kế. Không chỉ liệt kê các vấn đề — tích cực đặt câu hỏi cụ thể để giải quyết chúng.
   - **Brainstorm và khám phá tùy chọn** — Đối với các quyết định kiến trúc chính, sự đánh đổi, hoặc khu vực có nhiều phương án khả thi, chủ động brainstorm các phương án thay thế. Trình bày các tùy chọn với ưu/nhược điểm và sự đánh đổi. Thách thức các giả định và đưa ra các phương án sáng tạo.
   - **Lặp lại** — Tiếp tục lặp cho đến khi người dùng hài lòng với phương pháp đã chọn và không còn câu hỏi mở.
4. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu trữ các pattern/ràng buộc thiết kế được chấp nhận bằng thực hiện luồng nghiệp vụ sau khi chúng sẽ giúp công việc trong tương lai:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
5. **Hướng dẫn Lệnh Tiếp theo** — Nếu tìm thấy các khoảng trống yêu cầu, quay lại `/review-requirements`; nếu thiết kế vững chắc, tiếp tục với `/execute-plan`.
