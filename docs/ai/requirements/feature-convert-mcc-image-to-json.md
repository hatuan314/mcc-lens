---
phase: requirements
title: Requirements & Problem Understanding - Convert MCC Image to JSON
description: Yêu cầu chuyển đổi ảnh danh mục MCC của VISA thành dữ liệu JSON có cấu trúc bằng Surya OCR, với CLI có thanh tiến trình. Thay thế giải pháp Florence-2 trước đó.
---

# Requirements & Problem Understanding

## Problem Statement
**Vấn đề chúng ta đang giải quyết là gì?**

- Tổ chức VISA cung cấp danh sách mã MCC (Merchant Category Code) dưới dạng tập ảnh (JPG) đặt tại `assets/mcc-visa/`. Dữ liệu này không thể truy vấn, tra cứu hay tích hợp vào các dịch vụ downstream (ví dụ: module chuyển đổi VSIC ↔ MCC) khi còn nằm ở dạng ảnh.
- **Ai bị ảnh hưởng:** Nhóm phát triển MCC Lens (người dùng chính) và các hệ thống nghiệp vụ cần dữ liệu MCC ở dạng có cấu trúc (service mapping VSIC ↔ MCC, tra cứu merchant, báo cáo).
- **Hiện trạng:** Dữ liệu tồn tại dưới dạng **83 file ảnh** scan trang sách `visa-merchant-data-standards-manual-hình ảnh-*.jpg` tại `assets/mcc-visa/`. Việc trích xuất thủ công tốn thời gian, dễ sai sót, và không scale khi có thêm tài liệu VISA phiên bản mới.

## Goals & Objectives
**Mục tiêu cần đạt:**

- **Mục tiêu chính (Primary):**
  1. Tự động trích xuất nội dung MCC từ ảnh tại `assets/mcc-visa/` thành JSON có cấu trúc.
  2. Sử dụng **Surya OCR** (`surya-ocr`) làm engine OCR với pipeline 2 bước: layout detection → OCR từng vùng.
  3. Mỗi bản ghi JSON gồm 6 field: `mcc`, `title`, `description`, `included_in_mcc`, `similar_merchants`, `source_image`.
  4. Cung cấp giao diện CLI hiển thị thanh tiến trình (progress bar) trong quá trình xử lý batch ảnh.
  5. **Batch OCR processing:** gom ảnh thành nhóm `batch_size=8` trước khi gọi Surya, tận dụng native batch API `recognition_predictor(images_list, ...)` để tối ưu throughput trên MPS/CPU. `batch_size` hardcode = 8 (không expose CLI flag ở V1).
- **Mục tiêu phụ (Secondary):**
  - Ghi log chi tiết quá trình xử lý (loguru) để truy vết lỗi OCR.
  - Hỗ trợ chạy lại (idempotent) — bỏ qua file đã xử lý thành công nếu người dùng yêu cầu.
  - Deduplication: giữ lại entry đầy đủ nhất khi cùng MCC code xuất hiện nhiều lần.
  - Có thể mở rộng cho nguồn ảnh MCC khác ngoài VISA (Mastercard, JCB…).
- **Không mục tiêu (Non-goals):**
  - Không chuẩn hóa / dịch MCC sang VSIC trong phạm vi tính năng này (được xử lý ở feature khác).
  - Không xây giao diện Web/REST API — chỉ CLI.
  - Không fine-tune lại Surya; dùng trọng số pretrained.
  - Không thiết kế database — output là một file JSON tổng hợp duy nhất.
  - Không hỗ trợ chế độ per-file output (mỗi ảnh một file) trong V1 — sẽ xem xét cho Mastercard/JCB ở version sau.

## User Stories & Use Cases
**Người dùng sẽ tương tác với giải pháp như thế nào?**

- **US-1:** Là một *developer MCC Lens*, tôi muốn chạy `python3 main.py convert-mcc` để tự động trích xuất toàn bộ ảnh MCC của VISA thành JSON, để tôi có dữ liệu có cấu trúc dùng cho các tính năng mapping.
- **US-2:** Là một *developer*, tôi muốn thấy progress bar (ví dụ: `Processing 12/83 [███░░░] 14%`) trong CLI, để biết tiến độ và ước lượng thời gian còn lại. Progress bar cập nhật **per-image** (sau khi mỗi ảnh trong batch được parse xong), không phải per-batch.
- **US-3:** Là một *developer*, tôi muốn cấu hình được thư mục input và đường dẫn output JSON qua tham số CLI, để có thể tái sử dụng pipeline cho các tập ảnh khác.
- **US-4:** Là một *developer*, khi một ảnh xử lý thất bại (Surya trả về kết quả không parse được), tôi muốn lỗi được log kèm tên file và pipeline tiếp tục chạy các ảnh còn lại (không abort toàn bộ).
- **US-5:** Là một *developer*, khi pipeline bị ngắt giữa chừng, tôi muốn chạy lại với flag `--resume` để tiếp tục từ ảnh chưa xử lý — tránh mất công xử lý lại từ đầu. Cơ chế: checkpoint file `.mcc-convert-progress.json` ghi danh sách ảnh đã xử lý thành công; file này bị xóa tự động khi pipeline hoàn thành.

### Luồng Batch Processing (chi tiết)
1. Đọc danh sách ảnh → chia thành các batch `batch_size=8`.
2. Mỗi batch: load `batch_size` ảnh vào RAM → gọi `ocr_service.extract_lines_batch(images)` → nhận `List[List[OCRLine]]`.
3. Với mỗi ảnh trong kết quả batch: parse table entries → ghi checkpoint (nếu `--resume`) → update progress bar.
4. Nếu ảnh trong batch lỗi khi parse: log warning, ghi error vào result, **các ảnh còn lại trong batch vẫn được mark done**.
5. OCR lỗi cho cả batch → log error cho từng ảnh trong batch, không mark done.

### Luồng Resume (chi tiết)
1. Lần chạy đầu (hoặc `--resume` không tìm thấy checkpoint): xử lý toàn bộ ảnh.
2. Mỗi ảnh thành công → tên file được append vào checkpoint (per-image, không phải per-batch).
3. Nếu bị ngắt: chạy lại với `--resume` → skip các ảnh đã có trong checkpoint.
4. Khi tất cả ảnh xong → xóa checkpoint, merge toàn bộ entry ghi vào JSON output.

### Edge cases cần cân nhắc (bao gồm batch mode)
- Ảnh chứa nhiều MCC (nhiều block) — cần tách thành nhiều bản ghi JSON.
- Ảnh chỉ chứa header / footer / trang mục lục không có MCC — phải bỏ qua, không tạo bản ghi lỗi.
- `included_in_mcc` có thể trống (list rỗng `[]`).
- `similar_merchants` là list các object `{"mcc": "XXXX", "title": "..."}` — có thể rỗng.
- Title của `similar_merchants` có thể bị cắt giữa chừng do xuống dòng → cần nối tiếp dòng kế.
- Ảnh bị nhiễu, nghiêng, chữ nhỏ khiến Surya trả về dòng text thiếu hoặc bị lỗi confidence thấp.
- Máy Apple M1/M2 — Surya native MPS; máy không có GPU fallback về CPU.
- **Batch cuối không đủ 8 ảnh** (83 mod 8 = 3 ảnh) — batch cuối có 3 ảnh, Surya phải xử lý bình thường.
- **Tất cả ảnh trong batch đã có trong checkpoint** — skip toàn bộ batch, không gọi OCR.
- **Một ảnh trong batch lỗi khi parse (sau OCR thành công)** — log lỗi, skip ảnh đó, mark 7 ảnh còn lại là done.

## Success Criteria
**Chúng ta biết là xong khi nào?**

- **Acceptance criteria:**
  - [ ] Chạy lệnh CLI convert-mcc thành công trên tất cả ảnh trong `assets/mcc-visa/` và sinh ra file JSON hợp lệ.
  - [ ] JSON output đúng schema: mỗi entry có đủ 6 field (`mcc`, `title`, `description`, `included_in_mcc`, `similar_merchants`, `source_image`).
  - [ ] `similar_merchants` là list các object `{"mcc": "XXXX", "title": "..."}`, không phải list string.
  - [ ] Entry không parse được `mcc` được giữ lại với `mcc = ""` và có field `_unparsed: true` — không bị loại bỏ.
  - [ ] Deduplication hoạt động đúng: cùng MCC code chỉ giữ entry có `description` dài hơn.
  - [ ] Progress bar hiển thị và cập nhật chính xác theo số ảnh đã xử lý.
  - [ ] Khi 1 ảnh lỗi, pipeline tiếp tục các ảnh khác và ghi log lỗi rõ ràng; các ảnh thành công trong cùng batch vẫn được mark done.
  - [ ] Flag `--resume` hoạt động đúng: bỏ qua ảnh đã có trong checkpoint, xóa checkpoint khi hoàn thành.
  - [ ] **Batch processing hoạt động đúng:** 83 ảnh được gom thành `ceil(83/8) = 11 batch`; mỗi batch gọi Surya 1 lần.
  - [ ] **Batch cuối (3 ảnh) được xử lý bình thường** như batch đầy đủ.
  - [ ] Có unit test cho service parsing Surya output (coverage ≥ 80%); batch logic được cover bởi test với `FakeOCRService.extract_lines_batch`.
- **Measurable outcomes:**
  - Tỷ lệ ảnh parse thành công ≥ 90% trên 83 ảnh VISA.
  - Thời gian xử lý tổng ≤ **10 phút** trên Apple M1/M2 MPS với batch_size=8 (so với ~20–30 phút nếu xử lý serial).
  - Thời gian xử lý tổng ≤ 30 phút trên CPU thuần túy.

## Constraints & Assumptions
**Giới hạn cần tuân thủ:**

- **Ràng buộc kỹ thuật:**
  - Python 3.10+; tuân thủ PEP 8, Type Hints, docstring Google, kiến trúc MVC/Clean Architecture theo `.claude/rules/python-standards.md`.
  - Engine OCR: **Surya OCR** (`surya-ocr`) với `RecognitionPredictor`, `DetectionPredictor`, `FoundationPredictor`; kích thước model ~1–2GB cần tải về lần đầu.
  - Hỗ trợ Apple M1/M2 (MPS) và CPU; không yêu cầu CUDA/GPU rời.
- **Ràng buộc nghiệp vụ:** Output JSON phải dùng được trực tiếp bởi các feature VSIC-to-MCC sau này.
- **Giả định:**
  - Người dùng có kết nối Internet lần đầu để tải weight Surya từ HuggingFace.
  - Các ảnh trong `assets/mcc-visa/` đã là ảnh rõ ràng, định dạng JPG.
  - Layout bảng MCC của VISA nhất quán: 4 cột cố định theo tỷ lệ x-coordinate — MCC ~0–12%, Description ~12–46%, Included ~46–64%, Similar ~64–100%.
  - Không cần lo ngại về bản quyền mô hình (Surya theo giấy phép GPL-3.0).

## Questions & Open Items
**Cần làm rõ thêm:**

- [x] Output JSON là **một file tổng** (`mcc-visa.json` chứa array) — chế độ per-file loại khỏi V1.
- [x] Entry thiếu `mcc_code`: giữ lại với `mcc_code = ""` và đánh dấu `_unparsed: true` để downstream phân biệt.
- [x] Provenance `source_image`: ghi lại tên file ảnh nguồn cho mỗi entry.
- [x] Resume: dùng checkpoint file (`.mcc-convert-progress.json`), bật bằng flag `--resume`, tự xóa khi hoàn thành.
- [x] **Surya OCR pipeline đã chốt:** `FoundationPredictor` → `RecognitionPredictor` + `DetectionPredictor`; gọi `recognition_predictor(images_list, det_predictor=detection_predictor)` với `images_list` là batch.
- [x] **Batch processing đã chốt (2026-04-18):** mini-batch `batch_size=8` hardcode; `OCRService` Protocol thêm method `extract_lines_batch(images) -> List[List[OCRLine]]`; checkpoint per-image sau mỗi batch; progress bar cập nhật per-image (8 tick sau mỗi batch); ảnh lỗi khi parse → skip + log, các ảnh còn lại trong batch vẫn được mark done.
- [x] **Column detection đã chốt:** fixed % của image width — mcc: 0–12%, desc: 12–46%, included: 46–64%, similar: 64–100%. Sắp xếp dòng theo `(round(y1 / 15), x1)`.
- [x] **Entry grouping:** mỗi entry MCC bắt đầu khi gặp token 4 chữ số ở cột `mcc`; các dòng sau được append vào cột tương ứng cho đến khi gặp MCC code tiếp theo.
- [x] **similar_merchants schema:** list của `{"mcc": "XXXX", "title": "..."}` — nối tiếp dòng kế nếu title bị cắt (không match pattern `^\d{4}\s*[–\-]`).
- [x] **Deduplication:** giữ entry có `description` dài hơn khi trùng MCC; sort kết quả theo `mcc` tăng dần.
- [x] **Không cần `visualize_results`** trong V1 — lab script đủ để debug thủ công; có thể thêm sau nếu cần.
