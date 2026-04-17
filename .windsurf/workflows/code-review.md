---
auto_execution_mode: 0
description: Review code trước khi push dựa trên tài liệu thiết kế.
---

Thực hiện review code cục bộ **trước** khi push các thay đổi.

1. **Thu thập Ngữ cảnh** — Nếu chưa được cung cấp, hãy hỏi: mô tả tính năng/branch, danh sách file đã sửa đổi, tài liệu thiết kế liên quan (ví dụ: `docs/ai/design/feature-{name}.md`), các ràng buộc hoặc khu vực rủi ro đã biết, và các bài kiểm tra nào đã được chạy. Cũng review diff mới nhất qua `git status` và `git diff --stat`.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "code review checklist project conventions"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Hiểu Sự Phù hợp Thiết kế** — Đối với mỗi tài liệu thiết kế, tóm tắt ý định kiến trúc và các ràng buộc quan trọng.
4. **Review Từng File** — Đối với mỗi file đã sửa đổi: kiểm tra sự phù hợp với thiết kế/yêu cầu và đánh dấu các sai lệch, phát hiện các vấn đề logic/trường hợp biên/code dư thừa, đánh dấu các lo ngại bảo mật (xác thực đầu vào, secrets, auth, xử lý dữ liệu), kiểm tra xử lý lỗi/hiệu suất/quan sát, và xác định các bài kiểm tra bị thiếu hoặc lỗi thời.
5. **Các Mối quan tâm Chéo** — Xác nhận tính nhất quán của đặt tên và quy ước dự án. Xác nhận tài liệu/bình luận đã cập nhật nơi hành vi thay đổi. Xác định các bài kiểm tra bị thiếu (unit, integration, E2E). Kiểm tra các cập nhật cấu hình/migration cần thiết.
6. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu các phát hiện/checklist review bền vững bằng thực hiện luồng nghiệp vụ sau:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
7. **Tóm tắt Các Phát hiện** — Phân loại mỗi phát hiện là **blocking**, **important**, hoặc **nice-to-have** với: file, vấn đề, tác động, đề xuất, và tham chiếu thiết kế.
8. **Hướng dẫn Lệnh Tiếp theo** — Nếu các vấn đề blocking còn lại, quay lại `/execute-plan` (sửa code) hoặc `/writing-test` (khoảng trống bài kiểm tra); nếu sạch, tiếp tục với quy trình push/PR.
