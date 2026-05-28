---
phase: requirements
title: Requirements & Problem Understanding — Mapping VSIC VN to MCC on Colab
description: Chạy pipeline VSIC→MCC trên Google Colab GPU với Ollama + qwen3.5:9b và xuất kết quả lên Google Drive
---

# Requirements & Problem Understanding

## Problem Statement
**What problem are we solving?**

- Việt Nam dùng hệ thống mã ngành **VSIC** (đã chuẩn hoá thành `output/vsic-vn.json`, tiếng Việt).
- VISA dùng hệ thống **MCC** (đã chuẩn hoá thành `output/mcc-visa.json`, tiếng Anh).
- Hiện tại không có bảng mapping chính thức VSIC → MCC; tra thủ công chậm và không nhất quán.
- Cần chạy pipeline mapping trên **Google Colab GPU NVIDIA** để tận dụng tốc độ, dùng **Ollama + qwen3.5:9b**, và xuất kết quả lên **Google Drive** để chia sẻ/ dùng downstream.

**Người bị ảnh hưởng:** Data engineer / business analyst cần bảng VSIC ↔ MCC để phân loại merchant theo chuẩn quốc tế.

**Workaround hiện tại:** Tra tay hoặc chạy local máy cá nhân (không ổn định, chậm, khó chia sẻ).

## Goals & Objectives
**What do we want to achieve?**

- **Primary:**
  - Đọc `output/vsic-vn.json` (field `vsic_list`, mỗi entry có `code`, `title`) và `output/mcc-visa.json` (field `mcc_list`, mỗi entry có `mcc`, `title`, `description`).
  - Với mỗi mã VSIC, dùng 2-stage retrieval: embedding pre-filter (top-K) → **qwen3.5:9b** re-rank qua **Ollama**.
  - LLM đóng vai trò giám khảo, trả về điểm số (0.0–1.0) và nhận xét ngắn.
  - Xuất **2 file Excel** lên Google Drive:
    1. `projects/mcc-lens/vsic-mcc-mapping.xlsx` — 3 cột: `VSIC`, `MCC` (score cao nhất), `Tên ngành`.
    2. `projects/mcc-lens/vsic-mcc-mapping-detail.xlsx` — theo template `assets/template/vsic_mcc_mapping_template.xlsx`.
- **Secondary:**
  - CLI subcommand `python3 main.py map-vsic-mcc` vẫn giữ nguyên các flag hiện có, nhưng bổ sung cờ `--gdrive-output-dir` để tự động điều hướng tất cả output và checkpoint vào chung một thư mục trên Google Drive một cách tiện lợi.
  - Checkpoint theo VSIC để resume khi Colab runtime reset.
  - Progress bar `tqdm` và log rõ ràng trong Colab cell output.

- **Non-goals:**
  - Không fine-tune / training model.
  - Không UI web; chỉ CLI + notebook cell orchestration.
  - Không mapping ngược MCC → VSIC.
  - Không hỗ trợ runtime CPU-only (Colab không có GPU).
  - Không triển khai OAuth riêng; dùng `google.colab` mount Drive mặc định.

## User Stories & Use Cases
**How will users interact with the solution?**

- Là **data engineer**, tôi muốn chạy 1 lệnh CLI trong Colab để nhận file Excel mapping VSIC→MCC để dùng cho pipeline.
- Là **business analyst**, tôi muốn file Excel có đúng 3 cột (VSIC, MCC, Tên ngành) để review nhanh bằng Excel/Google Sheets.
- Là **developer chạy pipeline dài**, tôi muốn `--resume` để tiếp tục khi Colab runtime bị reset.
- Là **developer tối ưu chi phí**, tôi muốn pipeline chỉ gửi top-K MCC vào prompt thay vì toàn bộ danh sách.
- Là **developer chia sẻ dữ liệu**, tôi muốn kết quả được lưu lên Google Drive tại `projects/mcc-lens/` để chia sẻ với team.

**Edge cases:**

- VSIC title mơ hồ → LLM trả về "NO_MATCH" và pipeline vẫn chạy tiếp.
- Ollama chưa chạy / model chưa pull → báo lỗi rõ ràng.
- Google Drive chưa mount hoặc path không tồn tại → báo lỗi rõ.
- Colab runtime reset → resume từ checkpoint trên Drive.

## Success Criteria
**How will we know when we're done?**

- [ ] Chạy được: `python3 main.py map-vsic-mcc` trên Colab GPU.
- [ ] File `projects/mcc-lens/vsic-mcc-mapping.xlsx` tồn tại trên Google Drive, mở được bằng Excel/Sheets, đúng 3 cột.
- [ ] File `projects/mcc-lens/vsic-mcc-mapping-detail.xlsx` tồn tại và đúng cấu trúc template (3 sheet).
- [ ] Số lượng hàng data == số VSIC entries trong input.
- [ ] `VSIC` là `code` string trong `vsic_list`.
- [ ] `MCC` là string 4 ký tự hoặc rỗng nếu NO_MATCH.
- [ ] Score là float [0, 1] (làm tròn 2 chữ số), Nhận xét là string ngắn.
- [ ] `--resume` hoạt động sau khi Colab runtime reset.
- [ ] Khi top-1 embedding score thấp (< ngưỡng), in warning gợi ý tăng `--top-k`.
- [ ] Tuân thủ Clean Architecture: service phụ thuộc Protocols, không phụ thuộc concrete repo.

## Constraints & Assumptions
**What limitations do we need to work within?**

- **Runtime:** Google Colab với GPU NVIDIA (T4/L4/A100 tuỳ phiên).
- **Ollama:** cài và chạy trong Colab; model `qwen3.5:9b` + embedding model (mặc định `bge-m3`) đã pull.
- **Storage:** Google Drive phải được mount tại `/content/drive`.
- **Offline:** Không gọi API cloud; inference 100% local qua Ollama.
- **Architecture:** Tuân thủ Clean Architecture + MVC của project.
- **Assumption:** `output/vsic-vn.json` và `output/mcc-visa.json` đã tồn tại và đúng schema.

## Questions & Open Items
**What do we still need to clarify?**

- [x] Checkpoint nên lưu trong thư mục nào trên Google Drive? -> **Resolved**: Lưu mặc định tại `projects/mcc-lens/.mapping-progress.json` nếu dùng output dir mặc định.
- [x] Có cần thêm `--gdrive-output-dir` mặc định hay chỉ yêu cầu user truyền `--output` và `--output-detail`? -> **Resolved**: Thêm cờ `--gdrive-output-dir` để tự động ghép đường dẫn cho file mapping, detail mapping, và checkpoint.
- [x] Có cần notebook mẫu (`colab/`) cho thao tác mount Drive + start Ollama? -> **Resolved**: Tạo file `colab/mapping_vsic_mcc_colab.ipynb` có sẵn code setup.
