---
auto_execution_mode: 0
description: Lưu trữ hướng dẫn tái sử dụng trong dịch vụ bộ nhớ kiến thức.
---

Giúp tôi lưu trữ nó trong dịch vụ bộ nhớ kiến thức.

1. **Nắm bắt Kiến thức** — Nếu chưa được cung cấp, hãy hỏi: một tiêu đề ngắn rõ ràng (5-12 từ), nội dung chi tiết (markdown, khuyến khích ví dụ), tags tùy chọn (từ khóa như "api", "testing"), và phạm vi tùy chọn (`global`, `project:<name>`, `repo:<name>`). Nếu mơ hồ, hãy hỏi thêm để làm cho nó cụ thể và có thể hành động.
2. **Tìm kiếm Trước khi Lưu** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<topic>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Xác thực Chất lượng** — Đảm bảo nó cụ thể và tái sử dụng được (không phải lời khuyên chung chung). Tránh lưu trữ secrets hoặc dữ liệu nhạy cảm.
4. **Lưu** — Gọi `memory.storeKnowledge` với tiêu đề, nội dung, tags, phạm vi. Nếu các công cụ MCP không khả dụng, sử dụng `npx ai-devkit@latest memory store` thay thế. Sau đó thực hiện luồng nghiệp vụ sau để lưu trữ:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
5. **Xác nhận** — Tóm tắt những gì đã được lưu và đề xuất truy xuất các mục bộ nhớ liên quan khi hữu ích.
6. **Hướng dẫn Lệnh Tiếp theo** — Tiếp tục với lệnh giai đoạn vòng đời hiện tại (`/execute-plan`, `/check-implementation`, `/writing-test`, v.v.) khi cần thiết.
