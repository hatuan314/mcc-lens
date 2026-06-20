---
phase: requirements
title: Requirements & Problem Understanding — Qwen3-Embedding + Qwen3-Reranker Migration
description: Thay bge-m3 bằng Qwen3-Embedding và thêm tầng Qwen3-Reranker (cross-encoder) vào pipeline VSIC→MCC; rerank precompute trên Colab, bake vào artifact .npz
source: docs/ai/design/2026-06-20-qwen3-embedding-reranker-migration-brainstorm.md
---

# Requirements & Problem Understanding

## Problem Statement

**Vấn đề đang giải:**

Pipeline VSIC→MCC hiện là **2 tầng**:
1. **Embedding cosine** (`bge-m3` via Ollama, 1024-dim) → top-K MCC candidates
2. **LLM re-rank** (WokuShop/Ollama chat) → top-3 + score + comment tiếng Việt

Hạn chế:
- `bge-m3` nhúng **đối xứng, không instruction** → bỏ phí khả năng asymmetric của các
  embedding model đời mới; chất lượng top-K Stage-1 còn nhiễu.
- Không có tầng **cross-encoder rerank** giữa cosine và LLM → LLM phải xử lý cả candidate
  rác (đắt + nhiễu), top-1 đôi khi sai.

**Mục tiêu:** thay `bge-m3` → **Qwen3-Embedding** (bắt đầu bản **4B**, đường nâng 8B mở sẵn)
và chèn **Qwen3-Reranker** (cross-encoder) làm tầng giữa, để cải thiện rõ rệt chất lượng map.

**Người bị ảnh hưởng:** developer chạy batch VSIC→MCC mapping.

**Quy mô data (đã đo):** 903 MCC, 495 VSIC. Khối lượng rerank ≈ `495 × top-100` ≈ ~50.000 cặp
(Stage-1 top-K=100 đầu vào reranker; bake top-N=20 vào artifact).

## Goals & Objectives

**Primary:**
- **Pipeline 3 tầng:** `embedding (cosine) → rerank (cross-encoder) → LLM (generative)`.
- Thay embedding `bge-m3` → `Qwen3-Embedding-4B` (chạy trên Colab/GPU qua sentence-transformers/HF).
- Thêm `Qwen3-Reranker-4B` chấm lại top-K candidates → top-N (~10–20).
- **Rerank precompute trên Colab, bake vào artifact `.npz`** → local không cần GPU, không
  cần tải reranker model. Giữ nguyên triết lý tách Colab (producer) / local (consumer).
- **Bỏ hard-code `EXPECTED_DIM = 1024`** → đọc dim động từ `meta["dim"]` → đổi 4B↔8B không
  cần sửa code consumer.
- **Giữ cột comment/nhận xét tiếng Việt** → tầng LLM generative (WokuShop) vẫn còn.

**Secondary:**
- **Instruction prefix** cho phía query (VSIC) theo chuẩn Qwen3 asymmetric — nguồn cải thiện
  lớn nhất so với bge-m3.
- Nới truncation description (Qwen3 context dài) để match tốt hơn.
- Re-calibrate `LOW_SCORE_THRESHOLD` theo phân phối điểm mới (cosine vs rerank vs LLM).

**Non-goals:**
- Không chạy reranker dưới local M1 (RAM sát trần, MPS chậm ~giờ cho 30k cặp).
- Không bỏ tầng LLM generative (vẫn cần comment).
- Không đổi cấu trúc Excel output (cột giữ nguyên).
- Không thêm UI / web API / streaming / async.
- Không hỗ trợ thay top-K động ở local sau khi đã bake (top-K đóng băng lúc bake — chấp nhận).

## User Stories & Use Cases

- Là **developer**, tôi muốn chạy `embed` trên Colab để nó nhúng (Qwen3-Embedding) **và**
  rerank (Qwen3-Reranker) toàn bộ work set, ghi một artifact `.npz` tự chứa.
- Là **developer**, tôi muốn chạy `map-vsic-mcc` dưới local M1 (không GPU) đọc artifact đã
  rerank sẵn → chỉ gọi WokuShop viết comment top-3.
- Là **developer**, tôi muốn đổi từ 4B lên 8B chỉ bằng đổi tên model + regenerate artifact,
  không sửa code consumer.

**Edge cases:**
- Artifact `bge-m3` cũ (dim 1024, không có mảng rerank) → consumer phải fail-fast rõ ràng
  (thiếu key rerank hoặc dim mismatch), không đọc nhầm.
- Entry NaN/zero-vector → giữ hành vi hiện tại (vector 0, xếp hạng thấp, ghi vào meta).
- Reranker trả điểm cho < N candidates → pad/cắt an toàn.
- VSIC mà tất cả rerank score thấp → vẫn đẩy top-N tốt nhất sang LLM (không bỏ trống).

## Success Criteria

- [ ] `python3 -m app.embed` trên Colab tạo artifact `.npz` chứa: vectors (Qwen3-Embedding) +
      `reranked_mcc_indices` + `rerank_scores` + meta (`dim`, `embedding_model`,
      `reranker_model`, `rerank_top_n`).
- [ ] `EmbeddingArtifactRepository.read` validate **dim động** theo `meta["dim"]` (không còn
      hằng số 1024), và validate sự tồn tại/khớp shape của 2 mảng rerank.
- [ ] `map-vsic-mcc` dưới local đọc artifact → dùng thứ tự rerank → WokuShop viết comment →
      xuất 2 Excel hợp lệ, **không cần Ollama/GPU/reranker model**.
- [ ] Đổi `--embedding-model` 4B→8B + regenerate → consumer chạy **0 dòng code sửa**.
- [ ] Instruction prefix áp dụng đúng phía VSIC (query), MCC (document) để raw.
- [ ] Smoke: 10–20 VSIC end-to-end (Colab embed+rerank → local map) cho kết quả top-1 hợp lý.
- [ ] So baseline bge-m3: top-1 đúng tăng rõ / số case escalation giảm (đo trên mẫu).
- [ ] Artifact cũ bge-m3 → consumer fail-fast với message rõ (không silently sai).
- [ ] Unit test: repository read/write mảng rerank, dim động; use-case tiêu thụ rerank;
      embed_text_builder instruction prefix.
- [ ] `colab/requirements-embed.txt` thêm deps GPU (torch, transformers, sentence-transformers);
      `pytest -q` xanh toàn bộ.

## Constraints & Assumptions

- **Runtime model nặng:** Qwen3-Embedding + Qwen3-Reranker chạy **vLLM/HF (sentence-transformers)
  trên GPU Colab** — KHÔNG qua Ollama (Ollama không có endpoint rerank cross-encoder sạch).
- **Native dim:** 0.6B→1024, 4B→2560, 8B→4096 (đều hỗ trợ MRL). Bắt đầu **4B (2560-dim)**.
- **VRAM Colab:** 4B embed + 4B rerank trên T4 16GB phải chạy **tuần tự** (không cùng lúc); 8B
  cần A100.
- **Local:** M1 16GB chỉ chạy phần nhẹ (đọc artifact + WokuShop). Không tải reranker.
- **Kiến trúc:** thêm `RerankerClient` protocol (Colab-only, trong `app/embed/`); mở rộng
  `EmbeddingArtifact` model + `EmbeddingArtifactRepository` (ở `app/shared/`). Consumer
  `map_vsic_to_mcc_use_case.py` tiêu thụ thứ tự rerank thay cho việc tự cosine top-K.
- **Reproducibility:** text-builder vẫn là single source of truth; instruction prefix thêm
  vào builder, dùng chung producer (embed + rerank).
- **Backward incompat:** artifact bge-m3 cũ không tương thích (dim + thiếu rerank) → bắt buộc
  regenerate; không resume checkpoint cũ.

## Questions & Open Items

- [x] Runtime: vLLM/HF GPU. → **Resolved**
- [x] Giữ comment → pipeline 3 tầng. → **Resolved**
- [x] Bắt đầu 4B, dim động để nâng 8B dễ. → **Resolved**
- [x] Thứ tự `embedding → rerank → LLM`. → **Resolved**
- [x] Rerank chạy Colab, bake vào `.npz`. → **Resolved**
- [x] `rerank_top_n` (N) bake = **20** (đủ dư cho LLM chọn top-3, file vẫn nhỏ: 495×20).
      → **Resolved**
- [x] Stage-1 top-K (đầu vào reranker) = **100** (tăng từ 60). Reranker chính xác hơn cosine
      → đưa nhiều candidate hơn để bắt thêm recall trước rerank; đổi lại GPU rerank ~50k cặp.
      → **Resolved**
- [x] **Bỏ logic escalation** (`LOW_SCORE_THRESHOLD` + vòng nhân-đôi top-K) ở consumer. Candidate
      đã được bake top-N cố định nên không thể nhân-đôi top-K động ở local; rerank đã lo recall.
      → **Resolved** (xem gap-3 bên dưới về việc còn dùng threshold để FLAG hay không).
- [x] Runtime embedding+rerank = **sentence-transformers in-process trên Colab**. Cần xác minh
      API Qwen3-Reranker trong sentence-transformers ở bước design. → **Resolved**
- [ ] Instruction task string cụ thể cho phía query (vd "Given a Vietnamese industry name,
      retrieve the most relevant Visa MCC category"). Đề xuất câu trên làm mặc định; chốt câu
      chữ ở bước design (chi tiết wording, không chặn requirements).

### Khoảng trống bổ sung cần giải quyết ở bước design

1. **Schema/shape mảng rerank chưa định nghĩa.** `reranked_mcc_indices` + `rerank_scores` phải
   là per-VSIC shape `(n_vsic, N)` (mỗi VSIC một danh sách MCC index đã rerank + điểm tương ứng).
   `EmbeddingArtifactRepository.read` phải validate shape này khớp `n_vsic` và `N == meta["rerank_top_n"]`.
2. **Versioning artifact.** Thêm `meta["artifact_version"]` (vd `2`) để consumer fail-fast rõ ràng
   với artifact bge-m3 cũ (v1), thay vì chỉ suy luận gián tiếp qua dim/missing-key.
3. **Giữ `LOW_SCORE_THRESHOLD` để FLAG?** Sau khi bỏ vòng escalation, cần quyết: còn dùng ngưỡng
   này để **gắn cờ cảnh báo** case điểm thấp (cột nhận xét) hay bỏ hẳn. Đề xuất: giữ để FLAG.
4. **Tiêu chí "top-1 đúng tăng rõ" cần đo được.** Định nghĩa baseline + kích thước mẫu có nhãn tay
   (vd 30–50 VSIC) + cách so sánh, để Success Criteria thành verifiable thật sự.
5. **Phạm vi instruction prefix trong `embed_text_builder`.** Chỉ `build_vsic_text` (query) nhận
   prefix; `build_mcc_text` (document) giữ raw. Prefix phải nằm trong builder để producer
   embed + rerank dùng chung, tránh lệch text.
6. **Sửa kèm message lỗi `embedding_artifact_repository.py`** (`python3 main.py embed`
   → `python3 -m app.embed`) cho khớp CLI hiện tại.
