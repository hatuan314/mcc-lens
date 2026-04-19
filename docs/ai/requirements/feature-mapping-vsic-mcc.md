---
phase: requirements
title: Requirements & Problem Understanding — Mapping VSIC to MCC
description: Sử dụng Ollama + Qwen2.5:14b để mapping mã ngành VSIC (Việt Nam) sang MCC (Visa) và xuất Excel
---

# Requirements & Problem Understanding

## Problem Statement
**What problem are we solving?**

- Việt Nam dùng hệ thống mã ngành **VSIC** (743 entries trong `output/vsic.json`, tiếng Việt).
- Tổ chức VISA dùng hệ thống **MCC** (903 entries trong `output/mcc-visa.json`, tiếng Anh) để phân loại merchant trong thanh toán thẻ.
- Hiện tại không có bảng mapping chính thức VSIC → MCC. Data engineer / business analyst phải tra tay, chậm và không nhất quán.
- Cần một pipeline offline chạy local (MacBook Pro M1 16GB) dùng **Ollama + Qwen2.5:14b** để gợi ý mapping và xuất ra Excel để review/sử dụng downstream.

**Người bị ảnh hưởng:** Data engineer / business analyst cần bảng tra cứu VSIC ↔ MCC cho các pipeline phân loại merchant theo chuẩn quốc tế.

**Workaround hiện tại:** Tra thủ công, không có bảng chuẩn.

## Goals & Objectives

- **Primary:**
  - Đọc `output/vsic-vn.json` (field `vsic_list`, mỗi entry có `code`, `title`) và `output/mcc-visa.json` (field `mcc_list`, mỗi entry có `mcc`, `title`, `description`).
  - Với mỗi mã VSIC, dùng 2-stage retrieval: embedding pre-filter (top-K) → Qwen2.5:14b re-rank qua Ollama.
  - Xuất **2 file Excel**:
    1. `output/vsic-mcc-mapping.xlsx` — 3 cột: `VSIC`, `MCC` (score cao nhất), `Tên ngành` (title tiếng Việt).
    2. `output/vsic-mcc-mapping-detail.xlsx` — dùng template `assets/template/vsic_mcc_mapping_template.xlsx`, gồm 3 sheet:
       - **Mapping Result**: `Mã VSIC`, `Tên Ngành (Tiếng Việt)`, cùng với top-3 MCC (`Mã MCC`, `Tên MCC`, `Score`, `Nhận xét`) cho mỗi rank.
       - **Hướng Dẫn**: giữ nguyên từ template (màu sắc rank 1/2/3).
       - **Thống Kê**: giữ nguyên công thức từ template.
- **Secondary:**
  - CLI subcommand `python3 main.py map-vsic-mcc` với `--vsic-input`, `--mcc-input`, `--output`, `--output-detail`, `--resume`, `--top-k` (default 15).
  - Checkpoint từng VSIC để có thể resume (quá trình có thể mất vài giờ trên M1 16GB).
  - CLI progress bar (`tqdm`) hiển thị tiến độ và ETA.
  - Khi VSIC có title mơ hồ và top-1 embedding score thấp (< threshold), in warning gợi ý user tăng `--top-k`.
- **Non-goals:**
  - Không fine-tune model, không training.
  - Không cung cấp UI web — chỉ CLI.
  - Không mapping ngược MCC → VSIC trong tính năng này.
  - Không gọi API cloud — 100% offline qua Ollama local.
  - Không dịch tên MCC sang tiếng Việt cho người dùng cuối (chỉ dùng nội bộ nếu cần nâng matching).
  - Không hỗ trợ chạy trên máy không có Ollama / không có model Qwen2.5:14b.
  - Không có sheet `_debug` ẩn trong Excel.

## User Stories & Use Cases

- Là **data engineer**, tôi muốn chạy 1 lệnh CLI để nhận file Excel mapping VSIC→MCC, để có bảng tra cứu dùng được ngay trong công việc.
- Là **business analyst**, tôi muốn file Excel có đúng 3 cột (VSIC, MCC, Tên ngành tiếng Việt) để mở bằng Excel/Google Sheets và review nhanh.
- Là **developer chạy pipeline dài**, tôi muốn có `--resume` để nếu máy bị tắt giữa chừng, lần chạy sau tiếp tục từ VSIC đã xử lý chứ không bắt đầu lại.
- Là **developer tối ưu chi phí**, tôi muốn pipeline không gửi toàn bộ 903 MCC cho mỗi prompt (sẽ quá dài cho Qwen2.5:14b), mà dùng pre-filter để chỉ gửi top-K ứng viên.

**Edge cases:**

- VSIC title mơ hồ / quá chung chung (ví dụ "Hoạt động khác chưa phân vào đâu") → cần cho phép LLM trả về "NO_MATCH" và xử lý gracefully (MCC để trống + ghi log).
- Ollama hoặc model chưa sẵn sàng → báo lỗi rõ ràng, không crash.
- File input thiếu / sai schema → fail-fast với message rõ.
- Mạng không cần, nhưng lần đầu chạy embedding model (nếu cần pull) cần internet.

## Success Criteria

- [ ] Chạy được: `python3 main.py map-vsic-mcc` không cần truyền flag (dùng default paths).
- [ ] File `output/vsic-mcc-mapping.xlsx` tồn tại, mở được bằng Excel/LibreOffice, có đúng 3 cột: `VSIC`, `MCC`, `Tên ngành`.
- [ ] File `output/vsic-mcc-mapping-detail.xlsx` tồn tại, theo đúng cấu trúc template (3 sheet: Mapping Result, Hướng Dẫn, Thống Kê).
- [ ] Sheet "Mapping Result" có 14 cột theo template: Mã VSIC, Tên Ngành, và 4 cột × 3 rank (Mã MCC, Tên MCC, Score, Nhận xét).
- [ ] Số lượng hàng data == số VSIC entries trong input (kể cả hàng NO_MATCH, MCC để rỗng).
- [ ] `VSIC` là `code` string từ `vsic_list` trong `vsic-vn.json` (ví dụ `"1110"`).
- [ ] `MCC` là string 4 ký tự (ví dụ `"5411"`) hoặc rỗng nếu không map được.
- [ ] `Tên ngành` là `title` tiếng Việt lấy từ field `title` trong vsic entry.
- [ ] Score là float [0, 1]; Nhận xét là string tóm tắt mức phù hợp.
- [ ] Có progress bar `tqdm` hiển thị trong terminal khi chạy.
- [ ] `--resume` hoạt động: chạy lại sau khi gián đoạn, các VSIC đã done được bỏ qua.
- [ ] Khi top-1 embedding score thấp (< ngưỡng cấu hình), in warning gợi ý tăng `--top-k`.
- [ ] Exit code 0 khi thành công, != 0 kèm message khi lỗi (Ollama unavailable / file not found / IO error).
- [ ] Tuân thủ Clean Architecture: `LLMClient` protocol + `OllamaLLMClient` impl, `EmbeddingClient` protocol + impl.
- [ ] Có unit test cho service mapping (mock LLM client) và repository (Excel writer).

## Constraints & Assumptions

- **Hardware:** MacBook Pro M1 16GB RAM. Qwen2.5:14b ~ 9GB RAM khi chạy → chỉ còn ~7GB cho OS + Python → cần cẩn thận batch size = 1.
- **Software:** Ollama đã cài sẵn, model `qwen2.5:14b` đã pull (giả định của user). Cần check health trước khi chạy.
- **Offline:** Toàn bộ inference chạy local qua Ollama HTTP API (`http://localhost:11434`).
- **Dependencies mới:** `ollama` (Python client), `openpyxl` (đã có), dùng `bge-m3` qua Ollama embeddings API cho pre-filter (user cần pull `bge-m3` trước lần chạy đầu tiên).
- **Architecture:** Tuân thủ Clean Architecture — repository đọc JSON / ghi Excel, service mapping, controller điều phối, view progress bar. Service phụ thuộc vào Protocol (`LLMClient`, `EmbeddingClient`), không phụ thuộc concrete.
- **Assumption:** `output/vsic-vn.json` và `output/mcc-visa.json` đã tồn tại và đúng schema (từ 2 feature đi trước).
- **Field sử dụng cho matching:**
  - VSIC: chỉ dùng `title` (tiếng Việt) làm input cho embedding và prompt LLM.
  - MCC: chỉ dùng `title` + `description` (tiếng Anh) làm input cho embedding và prompt LLM. Các field khác (`included_in_mcc`, `similar_merchants`, `source_image`) không dùng.
- **Assumption:** Chất lượng mapping chỉ cần "best effort" — không yêu cầu accuracy cố định vì không có ground truth.

## Questions & Open Items

- [x] Embedding model: dùng `bge-m3` qua Ollama. User cần `ollama pull bge-m3` trước khi chạy lần đầu. → **Resolved**
- [x] Top-K: default `--top-k 15`. Nếu top-1 embedding score < threshold, in warning gợi ý user tăng `--top-k`. → **Resolved**
- [x] Prompt Qwen: song ngữ (VSIC title tiếng Việt + top-K MCC tiếng Anh), yêu cầu Qwen trả về chỉ mã MCC 4 ký tự. → **Resolved**
- [x] Sheet `_debug` ẩn: không dùng. Score + top-3 đã có trong file detail. → **Resolved**
- [x] Hallucination handling: validate mã MCC Qwen trả về có trong danh sách MCC không. Nếu không hợp lệ → fallback top-1 embedding + log warning. → **Resolved**
- [x] Output format: 2 file Excel — simple (3 cột) và detail (theo template `assets/template/vsic_mcc_mapping_template.xlsx`). → **Resolved**
- [x] Giá trị `Nhận xét` cho mỗi rank: **do LLM (Qwen2.5:14b) sinh ra** — 1 câu ngắn giải thích tại sao MCC này phù hợp với VSIC. Được trả về cùng prompt re-rank, không tốn thêm lần gọi LLM riêng. → **Resolved**
