---
description: Review yêu cầu tính năng để đảm bảo tính đầy đủ.
---

Review `docs/ai/requirements/feature-{name}.md` và template cấp dự án `docs/ai/requirements/README.md` để đảm bảo sự phù hợp về cấu trúc và nội dung.

1. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature requirements>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
2. Tóm tắt:
   - Tuyên bố vấn đề cốt lõi và người dùng bị ảnh hưởng
   - Mục tiêu, không mục tiêu, và tiêu chí thành công
   - Các câu chuyện người dùng chính & các luồng quan trọng
   - Ràng buộc, giả định, câu hỏi mở
   - Bất kỳ phần bị thiếu hoặc sự lệch khỏi template
3. **Làm rõ và khám phá (lặp cho đến khi hội tụ)**:
   - **Đặt câu hỏi làm rõ** cho mỗi khoảng trống, mâu thuẫn, hoặc mơ hồ. Không chỉ liệt kê các vấn đề — tích cực đặt câu hỏi cụ thể để giải quyết chúng.
   - **Brainstorm và khám phá tùy chọn** — Đối với các quyết định chính, sự đánh đổi, hoặc khu vực có nhiều phương án khả thi, chủ động brainstorm các phương án thay thế. Trình bày các tùy chọn với ưu/nhược điểm và sự đánh đổi. Thách thức các giả định và đưa ra các phương án sáng tạo.
   - **Lặp lại** — Tiếp tục lặp cho đến khi người dùng hài lòng với phương pháp đã chọn và không còn câu hỏi mở.
4. **Lưu Trữ Kiến thức Tái sử dụng** — Nếu các quy ước yêu cầu tái sử dụng mới được đồng ý, thực hiện luồng nghiệp vụ sau để lưu trữ:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
5. **Hướng dẫn Lệnh Tiếp theo** — Nếu các yếu tố cơ bản bị thiếu, quay lại `/new-requirement`; nếu không tiếp tục với `/review-design`.
