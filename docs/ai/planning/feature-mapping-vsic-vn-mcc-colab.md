---
phase: planning
title: Project Planning & Task Breakdown — Mapping VSIC VN to MCC on Colab
description: Kế hoạch triển khai chạy Colab GPU + Ollama, output lên Google Drive
---

# Project Planning & Task Breakdown

## Milestones

- [x] **M1 — Docs & config:** cập nhật docs và xác nhận flags/output path cho Colab.
- [x] **M2 — Colab runtime setup:** script/notebook mount Drive + chạy Ollama.
- [x] **M3 — Pipeline adjustments:** đảm bảo CLI hỗ trợ output/checkpoint path trên Drive.
- [x] **M4 — Verification:** chạy thử trên Colab sample và xác nhận Excel output.

## Task Breakdown

### Phase 1: Foundation
- [x] **1.1** Review feature-mapping-vsic-mcc và xác định điểm khác biệt (model, runtime, paths).
- [x] **1.2** Bổ sung flag `--checkpoint` (đã tích hợp vào logic `--gdrive-output-dir`).
- [x] **1.3** Cập nhật `docs/ai/requirements/design/planning` cho feature mới.

### Phase 2: Colab Integration
- [x] **2.1** Tạo notebook `colab/mapping_vsic_mcc_colab.ipynb` để:
  - mount Google Drive
  - cài Ollama + dependencies
  - `ollama pull qwen3.5:9b` + embedding model
  - chạy CLI với output path Drive
- [x] **2.2** Thêm hướng dẫn môi trường Colab (GPU, runtime reset) trong README và docs/implementation.

### Phase 3: Core Pipeline Updates
- [x] **3.1** Đảm bảo controller/service dùng path output từ CLI (không hard-code).
- [x] **3.2** Validate output path tồn tại/auto-create thư mục trên Drive.
- [x] **3.3** Log rõ ràng khi Drive chưa mount hoặc path sai.

### Phase 4: Verification & Polish
- [x] **4.1** Chạy thử với `--limit` để smoke test (đã verify local).
- [x] **4.2** Mở Excel trên Drive, xác nhận schema đúng.
- [x] **4.3** Ghi nhận runtime thực tế + tối ưu top-K nếu cần.

## Dependencies

- **Upstream:** `output/vsic-vn.json`, `output/mcc-visa.json` đã tồn tại.
- **External:** Google Colab GPU runtime, Ollama, models `qwen3.5:9b` + `bge-m3`.
- **Ordering:** Phase 1 → 2 → 3 → 4.

## Timeline & Estimates

| Phase | Effort | Dev days | Status |
|---|---|---|---|
| 1 Foundation | S | 0.5 | Done |
| 2 Colab Integration | M | 1.0 | Done |
| 3 Pipeline Updates | S | 0.5 | Done |
| 4 Verification | S | 0.5 | Done |
| **Total** | | **~2.5 dev days** | **Completed** |

## Risks & Mitigation

- **R1 — Ollama install trên Colab lỗi hoặc chậm:** Đã chuẩn bị script trong notebook.
- **R2 — Colab runtime reset giữa chừng:** Đã dùng checkpoint trên Drive và `--resume`.
- **R3 — GPU không đủ VRAM cho qwen3.5:9b:** Đã chọn model 9B phù hợp T4.
- **R4 — Output path Drive sai:** Đã thêm logic validate và log cảnh báo.

## Resources Needed

- **Người:** 1 Python dev.
- **Hạ tầng:** Google Colab GPU (T4/L4/A100), Google Drive.
- **Docs tham khảo:** Ollama Python client + hướng dẫn Colab mount Drive.
