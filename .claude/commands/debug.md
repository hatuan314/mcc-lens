---
description: Debug một vấn đề với phân tích nguyên nhân gốc có cấu trúc trước khi thay đổi code.
---

Giúp tôi debug một vấn đề. Làm rõ kỳ vọng, xác định các khoảng trống, và đồng ý trên kế hoạch sửa trước khi thay đổi code.

1. **Thu thập Ngữ cảnh** — Nếu chưa được cung cấp, hãy hỏi: mô tả vấn đề (đang xảy ra gì so với nên xảy ra gì), thông báo lỗi/logs/screenshots, các thay đổi hoặc triển khai liên quan gần đây, và phạm vi tác động.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<issue symptoms or error>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Làm rõ Thực tế so với Kỳ vọng** — Nói lại hành vi quan sát so với kỳ vọng. Xác nhận các yêu cầu hoặc tài liệu liên quan định nghĩa kỳ vọng. Định nghĩa tiêu chí chấp nhận cho sửa lỗi.
4. **Tái tạo & Cô lập** — Xác định khả năng tái tạo (luôn, xen kẽ, cụ thể môi trường). Nắm bắt các bước tái tạo. Liệt kê các thành phần hoặc module bị nghi ngờ.
5. **Phân tích Các Nguyên nhân Tiềm năng** — Brainstorm các nguyên nhân gốc (dữ liệu, cấu hình, regression code, phụ thuộc bên ngoài). Thu thập bằng chứng hỗ trợ (logs, metrics, traces). Làm nổi bật các điều chưa biết cần điều tra.
6. **Giải quyết** — Trình bày các tùy chọn giải quyết (sửa nhanh, refactor, rollback, v.v.) với ưu/nhược điểm và rủi ro. Hỏi tùy chọn nào theo đuổi. Tóm tắt phương pháp đã chọn, công việc chuẩn bị, tiêu chí thành công, và các bước xác thực.
7. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu các pattern nguyên nhân gốc và sửa lỗi bằng thực hiện luồng nghiệp vụ sau:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
8. **Hướng dẫn Lệnh Tiếp theo** — Sau khi chọn đường dẫn sửa, tiếp tục với `/execute-plan`; khi đã triển khai, sử dụng `/check-implementation` và `/writing-test`.
