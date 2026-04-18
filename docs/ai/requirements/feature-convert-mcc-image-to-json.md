---
phase: requirements
title: Requirements & Problem Understanding - Convert MCC Image to JSON
description: Yêu cầu chuyển đổi ảnh danh mục MCC của VISA thành dữ liệu JSON có cấu trúc bằng mô hình Florence-2 large, với CLI có thanh tiến trình.
---

# Requirements & Problem Understanding

## Problem Statement
**Vấn đề chúng ta đang giải quyết là gì?**

- Tổ chức VISA cung cấp danh sách mã MCC (Merchant Category Code) dưới dạng tập ảnh (JPG) đặt tại `assets/mcc-visa/`. Dữ liệu này không thể truy vấn, tra cứu hay tích hợp vào các dịch vụ downstream (ví dụ: module chuyển đổi VSIC ↔ MCC) khi còn nằm ở dạng ảnh.
- **Ai bị ảnh hưởng:** Nhóm phát triển MCC Lens (người dùng chính) và các hệ thống nghiệp vụ cần dữ liệu MCC ở dạng có cấu trúc (service mapping VSIC ↔ MCC, tra cứu merchant, báo cáo).
- **Hiện trạng:** Dữ liệu tồn tại dưới dạng các file ảnh scan trang sách `visa-merchant-data-standards-manual-hình ảnh-*.jpg`. Việc trích xuất thủ công tốn thời gian, dễ sai sót, và không scale khi có thêm tài liệu VISA phiên bản mới.

## Goals & Objectives
**Mục tiêu cần đạt:**

- **Mục tiêu chính (Primary):**
  1. Tự động trích xuất nội dung MCC từ ảnh tại `assets/mcc-visa/` thành JSON có cấu trúc.
  2. Sử dụng mô hình **Florence-2 large** (`microsoft/Florence-2-large`) làm engine OCR / vision-language với task `<OCR_WITH_REGION>`, `max_new_tokens=3072`, `num_beams=3`.
  3. Mỗi bản ghi JSON gồm 5 field: `mcc`, `title_description`, `included`, `similar_merchants`, `source_image`.
  4. Cung cấp giao diện CLI hiển thị thanh tiến trình (progress bar) trong quá trình xử lý batch ảnh.
- **Mục tiêu phụ (Secondary):**
  - Ghi log chi tiết quá trình xử lý (loguru) để truy vết lỗi OCR.
  - Hỗ trợ chạy lại (idempotent) — bỏ qua file đã xử lý thành công nếu người dùng yêu cầu.
  - Có thể mở rộng cho nguồn ảnh MCC khác ngoài VISA (Mastercard, JCB…).
- **Không mục tiêu (Non-goals):**
  - Không chuẩn hóa / dịch MCC sang VSIC trong phạm vi tính năng này (được xử lý ở feature khác).
  - Không xây giao diện Web/REST API — chỉ CLI.
  - Không fine-tune lại Florence-2; dùng trọng số pretrained.
  - Không thiết kế database — output là một file JSON tổng hợp duy nhất.
  - Không hỗ trợ chế độ per-file output (mỗi ảnh một file) trong V1 — sẽ xem xét cho Mastercard/JCB ở version sau.

## User Stories & Use Cases
**Người dùng sẽ tương tác với giải pháp như thế nào?**

- **US-1:** Là một *developer MCC Lens*, tôi muốn chạy `python3 main.py convert-mcc` để tự động trích xuất toàn bộ ảnh MCC của VISA thành JSON, để tôi có dữ liệu có cấu trúc dùng cho các tính năng mapping.
- **US-2:** Là một *developer*, tôi muốn thấy progress bar (ví dụ: `Processing 12/27 [███░░░] 44%`) trong CLI, để biết tiến độ và ước lượng thời gian còn lại.
- **US-3:** Là một *developer*, tôi muốn cấu hình được thư mục input và đường dẫn output JSON qua tham số CLI, để có thể tái sử dụng pipeline cho các tập ảnh khác.
- **US-4:** Là một *developer*, khi một ảnh xử lý thất bại (Florence-2 trả về định dạng không parse được), tôi muốn lỗi được log kèm tên file và pipeline tiếp tục chạy các ảnh còn lại (không abort toàn bộ).
- **US-5:** Là một *developer*, khi pipeline bị ngắt giữa chừng, tôi muốn chạy lại với flag `--resume` để tiếp tục từ ảnh chưa xử lý — tránh mất công xử lý lại từ đầu. Cơ chế: checkpoint file `.mcc-convert-progress.json` ghi danh sách ảnh đã xử lý thành công; file này bị xóa tự động khi pipeline hoàn thành.

### Luồng Resume (chi tiết)
1. Lần chạy đầu (hoặc `--resume` không tìm thấy checkpoint): xử lý toàn bộ ảnh.
2. Mỗi ảnh thành công → tên file được append vào checkpoint.
3. Nếu bị ngắt: chạy lại với `--resume` → skip các ảnh đã có trong checkpoint.
4. Khi tất cả ảnh xong → xóa checkpoint, merge toàn bộ entry ghi vào JSON output.

### Edge cases cần cân nhắc
- Ảnh chứa nhiều MCC (nhiều block) — cần tách thành nhiều bản ghi JSON.
- Ảnh chỉ chứa header / footer / trang mục lục không có MCC — phải bỏ qua, không tạo bản ghi lỗi.
- `similar_merchants` có thể trống hoặc là một danh sách tên dài với dấu phẩy / xuống dòng.
- Ảnh bị nhiễu, nghiêng, chữ nhỏ khiến Florence-2 trả về output không đủ field.
- Máy không có GPU (CUDA) — cần fallback CPU (chấp nhận chậm).

## Success Criteria
**Chúng ta biết là xong khi nào?**

- **Acceptance criteria:**
  - [ ] Chạy lệnh CLI convert-mcc thành công trên tất cả 5 ảnh hiện có trong `assets/mcc-visa/` và sinh ra file JSON hợp lệ.
  - [ ] JSON output đúng schema: mỗi entry có đủ 5 field (`mcc`, `title_description`, `included`, `similar_merchants`, `source_image`).
  - [ ] Entry không parse được `mcc` được giữ lại với `mcc = ""` và có field `_unparsed: true` — không bị loại bỏ.
  - [ ] Progress bar hiển thị và cập nhật chính xác theo số ảnh đã xử lý.
  - [ ] Khi 1 ảnh lỗi, pipeline tiếp tục các ảnh khác và ghi log lỗi rõ ràng.
  - [ ] Flag `--resume` hoạt động đúng: bỏ qua ảnh đã có trong checkpoint, xóa checkpoint khi hoàn thành.
  - [ ] Có unit test cho service parsing Florence-2 output (coverage ≥ 80%).
- **Measurable outcomes:**
  - Tỷ lệ ảnh parse thành công ≥ 90% trên tập 5 ảnh mẫu VISA hiện có.
  - Thời gian xử lý trung bình ≤ 60 giây/ảnh trên CPU (mục tiêu tham khảo, không ràng buộc cứng).

## Constraints & Assumptions
**Giới hạn cần tuân thủ:**

- **Ràng buộc kỹ thuật:**
  - Python 3.10+; tuân thủ PEP 8, Type Hints, docstring Google, kiến trúc MVC/Clean Architecture theo `.claude/rules/python-standards.md`.
  - Mô hình Florence-2 large chạy qua `transformers` + `torch`; kích thước mô hình ~1.5GB cần tải về lần đầu.
  - Hỗ trợ cả CPU và GPU (ưu tiên GPU nếu có CUDA).
- **Ràng buộc nghiệp vụ:** Output JSON phải dùng được trực tiếp bởi các feature VSIC-to-MCC sau này.
- **Giả định:**
  - Người dùng có kết nối Internet lần đầu để tải weight Florence-2 từ HuggingFace.
  - Các ảnh trong `assets/mcc-visa/` đã là ảnh rõ ràng, định dạng JPG.
  - Không cần lo ngại về bản quyền mô hình (Florence-2 theo giấy phép MIT).

## Questions & Open Items
**Cần làm rõ thêm:**

- [x] Output JSON là **một file tổng** (`mcc-visa.json` chứa array) — chế độ per-file loại khỏi V1.
- [x] Entry thiếu `mcc_code`: giữ lại với `mcc_code = ""` và đánh dấu `_unparsed: true` để downstream phân biệt.
- [x] Provenance `source_image`: ghi lại tên file ảnh nguồn cho mỗi entry.
- [x] Resume: dùng checkpoint file (`.mcc-convert-progress.json`), bật bằng flag `--resume`, tự xóa khi hoàn thành.
- [x] **Florence-2 task đã chốt:** dùng `<OCR_WITH_REGION>`, `max_new_tokens=3072`, `num_beams=3`.
- [x] **Table reconstruction thresholds đã chốt:**
  - Row-grouping Y threshold: **relative** (% chiều cao ảnh), tham số `y_threshold_pct` ≈ 1.0–1.5%, dễ fine-tune.
  - Column assignment: **dynamic clustering** hoặc mốc X cố định theo % (layout VISA nhất quán: MCC ~10% trái, Description ~50%).
  - Multi-line merging: hàng mới khi cột `mcc` có giá trị; dòng tiếp theo khi cột `mcc` trống.
- [x] **Yêu cầu debug:** Implement hàm `visualize_results` dùng PIL/OpenCV để vẽ bounding boxes + label hàng/cột lên ảnh — phục vụ kiểm tra trực quan thuật toán nhóm hàng.
