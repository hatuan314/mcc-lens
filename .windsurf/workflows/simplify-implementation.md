---
auto_execution_mode: 0
description: Đơn giản hóa code hiện có để giảm độ phức tạp.
---

Giúp tôi đơn giản hóa một triển khai hiện có trong khi duy trì hoặc cải thiện chức năng của nó.

1. **Thu thập Ngữ cảnh** — Nếu chưa được cung cấp, hãy hỏi: file hoặc thành phần mục tiêu để đơn giản hóa, các điểm đau hiện tại (khó hiểu, duy trì, hoặc mở rộng?), lo ngại về hiệu suất hoặc khả năng mở rộng, ràng buộc (tương thích ngược, ổn định API, hạn hạn thời gian), và tài liệu thiết kế hoặc yêu cầu liên quan.
2. **Sử dụng Bộ Nhớ để Lấy Ngữ cảnh** — Thực hiện luồng nghiệp vụ sau để lấy ngữ cảnh:
   - Bước 1: Sử dụng `npx ai-devkit@latest memory search --query "<component simplification pattern>"` để lấy ngữ cảnh trong bộ nhớ của AI DevKit. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 2.
   - Bước 2: Sử dụng claude-mem mcp (mcp0_search) để lấy ngữ cảnh trong bộ nhớ claude-mem. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, chuyển sang bước 3.
   - Bước 3: Sử dụng memPalace mcp (mcp1_mempalace_search) để lấy ngữ cảnh trong bộ nhớ memPalace. Nếu có ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ. Nếu không có ngữ cảnh, scan toàn bộ code để lấy ngữ cảnh. Sau khi lấy được ngữ cảnh, kết thúc nhiệm vụ tìm kiếm bộ nhớ.
3. **Phân tích Độ phức tạp Hiện tại** — Đối với mỗi mục tiêu: xác định nguồn độ phức tạp (lồng sâu, trùng lặp, trừu tượng không rõ, liên kết chặt, over-engineering, giá trị magic), đánh giá nhận thức cho người bảo trì trong tương lai, và xác định các chặn khả năng mở rộng (điểm lỗi đơn lẻ, sync-where-async-needed, thiếu caching, thuật toán kém hiệu quả).
4. **Đề xuất Đơn giản hóa** — Ưu tiên tính dễ đọc hơn tính ngắn gọn; áp dụng kiểm tra 30 giây: thành viên nhóm mới có thể hiểu nhanh mỗi thay đổi không? Đối với mỗi vấn đề, đề xuất các cải tiến cụ thể (trích xuất, hợp nhất, làm phẳng, tách rời, loại bỏ code chết, thay thế bằng built-ins). Cung cấp các đoạn trước/sau.
5. **Ưu tiên & Lập kế hoạch** — Xếp hạng theo tác động so với rủi ro: (1) tác động cao, rủi ro thấp — làm trước, (2) tác động cao, rủi ro cao hơn — lập kế hoạch cẩn thận, (3) tác động thấp, rủi ro thấp — chiến thắng nhanh nếu thời gian cho phép, (4) tác động thấp, rủi ro cao — bỏ qua hoặc trì hoãn. Đối với mỗi thay đổi chỉ định mức rủi ro, yêu cầu kiểm tra, và nỗ lực. Tạo kế hoạch hành động được ưu tiên với thứ tự thực thi được đề xuất.
6. **Lưu Trữ Kiến thức Tái sử dụng** — Lưu các pattern đơn giản hóa tái sử dụng và sự đánh đổi bằng thực hiện luồng nghiệp vụ sau:
   - Bước 1: Sử dụng lệnh `npx ai-devkit@latest memory store ...` để lưu trữ trong bộ nhớ của AI DevKit.
   - Bước 2: Thực hiện lưu trữ trong bộ nhớ của claude-mem MCP (sử dụng các công cụ mcp0 thích hợp).
   - Bước 3: Thực hiện lưu trữ trong bộ nhớ của memPalace MCP (sử dụng các công cụ mcp1 thích hợp).
7. **Hướng dẫn Lệnh Tiếp theo** — Sau khi triển khai, chạy `/check-implementation` và `/writing-test`.
