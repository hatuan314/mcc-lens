---
auto_execution_mode: 0
description: Tạo khung tài liệu tính năng từ yêu cầu đến lập kế hoạch.
---

Hướng dẫn tôi thêm một tính năng mới, từ tài liệu hóa yêu cầu đến sẵn sàng triển khai.

1. **Nắm bắt Yêu cầu** — Nếu chưa được cung cấp, hãy hỏi: tên tính năng (kebab-case, ví dụ: `user-authentication`), vấn đề nó giải quyết và ai sẽ sử dụng nó, và các câu chuyện người dùng chính.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature/topic>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Tạo Cấu trúc Tài liệu Tính năng** — Sao chép nội dung của mỗi template (giữ nguyên YAML frontmatter và tiêu đề phần) vào các file cụ thể tính năng:
   - `docs/ai/requirements/README.md` → `docs/ai/requirements/feature-{name}.md`
   - `docs/ai/design/README.md` → `docs/ai/design/feature-{name}.md`
   - `docs/ai/planning/README.md` → `docs/ai/planning/feature-{name}.md`
   - `docs/ai/implementation/README.md` → `docs/ai/implementation/feature-{name}.md`
   - `docs/ai/testing/README.md` → `docs/ai/testing/feature-{name}.md`
4. **Giai đoạn Yêu cầu** — Điền vào `docs/ai/requirements/feature-{name}.md`: tuyên bố vấn đề, mục tiêu/không mục tiêu, câu chuyện người dùng, tiêu chí thành công, ràng buộc, câu hỏi mở.
5. **Giai đoạn Thiết kế** — Điền vào `docs/ai/design/feature-{name}.md`: thay đổi kiến trúc, mô hình dữ liệu, API/interface, thành phần, quyết định thiết kế, các cân nhắc bảo mật và hiệu suất.
6. **Giai đoạn Lập kế hoạch** — Điền vào `docs/ai/planning/feature-{name}.md`: phân tích nhiệm vụ với các nhiệm vụ con, phụ thuộc, ước lượng nỗ lực, thứ tự triển khai, rủi ro.
7. **Lưu Trữ Kiến thức Tái sử dụng** — Khi các quy ước hoặc quyết định quan trọng được hoàn tất, thực hiện luồng nghiệp vụ sau để lưu trữ:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store --title "<title>" --content "<knowledge>" --tags "<tags>"` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
8. **Hướng dẫn Lệnh Tiếp theo** — Chạy `/review-requirements` trước, sau đó `/review-design`. Nếu cả hai đều đạt, tiếp tục với `/execute-plan`.
