---
description: Thêm bài kiểm tra cho một tính năng mới.
---

Review `docs/ai/testing/feature-{name}.md` và đảm bảo nó phản ánh template cơ bản trước khi viết bài kiểm tra.

1. **Thu thập Ngữ cảnh** — Nếu chưa được cung cấp, hãy hỏi: tên tính năng/branch, tóm tắt thay đổi (liên kết đến tài liệu thiết kế & yêu cầu), môi trường mục tiêu, các bộ kiểm tra hiện có, và bất kỳ bài kiểm tra flaky/chậm nào cần tránh.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<feature testing strategy>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Phân tích Template Kiểm tra** — Xác định các phần bắt buộc từ `docs/ai/testing/feature-{name}.md`. Xác nhận tiêu chí thành công và các trường hợp biên từ tài liệu yêu cầu & thiết kế. Lưu ý các mocks/stubs/fixtures có sẵn.
4. **Bài kiểm tra Unit (nhắm tới 100% phủ sóng)** — Đối với mỗi module/hàm: liệt kê các kịch bản hành vi (happy path, trường hợp biên, xử lý lỗi), tạo các trường hợp kiểm tra với các xác nhận sử dụng utilities/mocks hiện có, và làm nổi bật các nhánh bị thiếu ngăn chặn phủ sóng đầy đủ.
5. **Bài kiểm tra Integration** — Xác định các luồng chéo thành phần quan trọng. Định nghĩa các bước thiết lập/dỡ bỏ và các trường hợp kiểm tra cho các ranh giới tương tác, hợp đồng dữ liệu, và các chế độ lỗi.
6. **Chiến lược Phủ sóng** — Đề xuất các lệnh công cụ phủ sóng. Gọi ra các file/hàm vẫn cần phủ sóng và đề xuất các bài kiểm tra thêm nếu <100%.
7. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu các pattern kiểm tra tái sử dụng hoặc fixtures khó bằng thực hiện luồng nghiệp vụ sau:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
8. **Cập nhật Tài liệu** — Tóm tắt các bài kiểm tra đã thêm hoặc vẫn bị thiếu. Cập nhật `docs/ai/testing/feature-{name}.md` với liên kết đến các file kiểm tra và kết quả. Đánh dấu các bài kiểm tra bị trì hoãn như các nhiệm vụ theo dõi.
9. **Hướng dẫn Lệnh Tiếp theo** — Nếu các bài kiểm tra tiết lộ các vấn đề thiết kế, quay lại `/review-design`; nếu không tiếp tục với `/code-review`.
