# Brainstorm — Migrate BGE-M3 → Qwen3-Embedding + Qwen3-Reranker

Date: 2026-06-20
Status: brainstorm summary (pre-plan)

## Problem statement

Thay embedding model `bge-m3` bằng **Qwen3-Embedding** và thêm **Qwen3-Reranker** vào
pipeline `map-vsic-mcc`, nhằm cải thiện rõ rệt chất lượng map VSIC→MCC. Câu hỏi gốc: các
config hiện tại có cần đổi để lợi ích thực sự xảy ra không?

Kết luận: **CÓ** — không chỉ đổi tên model. Có config bắt buộc đổi (nếu không sẽ hỏng),
config cần tinh chỉnh (nếu không lợi ích bị bỏ phí), và một thay đổi **kiến trúc**
(reranker là cross-encoder, không phải LLM chat → pipeline thành 3 tầng).

## Data scale (đã đo)

- MCC: **903** entries, VSIC: **495** entries (artifact hiện tại, dim 1024, model bge-m3).
- Khối lượng rerank = `495 VSIC × top-K(60)` ≈ **~30.000 cặp** (VSIC, MCC).
- Máy local: MacBook Pro M1, 16GB RAM (Apple Silicon, MPS).

## Inventory config hiện tại

| Config | Giá trị | Nơi |
|---|---|---|
| Embedding model | `bge-m3` | `embed/controller.py`, `ollama_embedding_client.py` |
| Vector dim (hard-coded, fail-fast) | `EXPECTED_DIM = 1024` | `shared/embedding_artifact_repository.py:14` |
| Embed text MCC | `title — description[:500]` (strip HTML) | `shared/embed_text_builder.py:28` |
| Embed text VSIC | raw `title`, không instruction prefix | `shared/embed_text_builder.py:37` |
| Stage-1 top-K | `DEFAULT_TOP_K = 60` | `controllers/mapping_controller.py:26` |
| Escalation threshold | `LOW_SCORE_THRESHOLD = 0.5` | `services/map_vsic_to_mcc_use_case.py:29` |
| Stage-2 | LLM chat (JSON top-3 + score + comment VI) | `services/llm_prompts.py`, `wokushop_llm_client.py` |
| Desc trong prompt | `[:200]` | `services/llm_prompts.py:42` |

## Quyết định đã chốt (qua brainstorm)

1. **Runtime model nặng:** vLLM/HF trên GPU (không qua Ollama cho reranker — Ollama không
   có endpoint rerank cross-encoder sạch).
2. **Giữ cột comment/nhận xét tiếng Việt** → vẫn cần 1 tầng LLM generative (WokuShop) →
   pipeline **3 tầng**.
3. **Bắt đầu với bản 4B**, đổi lên 8B sau nếu cần. Để đổi size dễ dàng (0 dòng code
   consumer), phải **bỏ hard-code dimension**: `EXPECTED_DIM` đọc từ `meta["dim"]` của
   artifact (producer đã ghi sẵn). Native dim: 0.6B→1024, 4B→2560, 8B→4096 (đều hỗ trợ MRL).
4. **Thứ tự pipeline đúng: `embedding → rerank → LLM`** (retrieve → rerank → generate).
   Reranker đứng TRƯỚC LLM để lọc rác cho tầng đắt nhất, không phải sau.
5. **Rerank chạy trên Colab, bake vào artifact `.npz`**: local không cần GPU, không cần
   tải reranker model — chỉ tiêu thụ kết quả đã rerank sẵn. Đúng triết lý tách Colab/local.

## Kiến trúc mới (3 tầng)

```
Stage 1  EMBEDDING (cosine)     — Qwen3-Embedding-4B vectors (từ .npz), top-K=60
Stage 2  RERANK (cross-encoder) — Qwen3-Reranker-4B chấm lại 60 cặp → top-N (~10)
Stage 3  LLM (generative)       — WokuShop chốt top-3 + viết comment tiếng Việt
```

Phân bổ chạy:
- **Colab (GPU, producer):** embed + rerank toàn bộ work set → ghi artifact mở rộng.
- **Local (consumer, không GPU):** đọc artifact (đã có thứ tự rerank) → WokuShop viết comment.

## Reranker output — định dạng

Reranker KHÔNG sửa/làm sạch vector embedding. Vector giữ nguyên. Reranker sinh **bảng xếp
hạng theo điểm relevance cho từng VSIC** (dữ liệu quan hệ VSIC↔MCC, khác hẳn vector).

Lưu bằng cách **mở rộng `embed-artifact.npz`**, thêm 2 mảng:
- `reranked_mcc_indices` (495 × N) — chỉ số MCC đã sắp xếp lại cho mỗi VSIC
- `rerank_scores` (495 × N) — điểm relevance tương ứng

Kích thước thêm ~5.000 số (495×10) → không đáng kể.

## Các config phải đổi

### Nhóm A — Bắt buộc (không đổi thì hỏng)
- `EXPECTED_DIM`: bỏ hard-code 1024 → đọc từ `meta["dim"]`. Regenerate toàn bộ artifact.
- Validate dimension theo dim động thay vì hằng số.

### Nhóm B — Tinh chỉnh để lợi ích thực sự xảy ra
- **Instruction prefix (quan trọng nhất):** Qwen3-Embedding train kiểu asymmetric — phía
  query (VSIC) cần prefix `"Instruct: {task}\nQuery: {text}"`, phía document (MCC) để raw.
  Sửa `embed_text_builder.py`. Đây là nguồn cải thiện lớn nhất của Qwen3 so với bge-m3,
  hiện đang bị bỏ phí (code nhúng đối xứng, không instruction).
- **Truncation:** bge-m3 context ngắn nên cắt 500/200 ký tự; Qwen3-Embedding context tới
  32k → nới description để match tốt hơn.
- **`LOW_SCORE_THRESHOLD`:** điểm phân phối khác sau khi đổi model + thêm reranker → đo lại,
  tránh escalation kích sai. Cần phân biệt rõ cosine score vs rerank score vs LLM score.

### Nhóm C — Kiến trúc
- Thêm `RerankerClient` protocol + implementation (sentence-transformers/vLLM) cho Colab.
- Mở rộng `EmbeddingArtifact` model + repository read/write cho 2 mảng rerank mới.
- Sửa `map_vsic_to_mcc_use_case.py`: chèn tầng tiêu thụ thứ tự rerank giữa cosine và LLM.
  Lưu ý `_rerank_with_escalation` hiện tại đặt tên "rerank" nhưng thực chất gọi LLM chat —
  dễ nhầm, cần phân định rõ tầng reranker thật (cross-encoder) là cái mới.

## Risks & tradeoffs

- **top-K đóng băng lúc bake:** đổi top-K = chạy lại Colab. Đổi lại local GPU-free.
- **VRAM Colab:** 4B embed + 4B rerank trên T4 16GB cần chạy tuần tự (không cùng lúc).
  8B thì T4 không đủ, cần A100. Bắt đầu 4B là hợp lý.
- **Local M1 16GB không nên chạy reranker 4B:** ~8GB fp16 sát trần RAM + MPS chậm
  (~2.5–8 tiếng cho 30k cặp). → đẩy lên Colab.
- **Artifact cũ bất tương thích:** dim đổi + có thêm mảng rerank → phải regenerate, không
  resume từ artifact bge-m3.

## Success metrics

- Tỉ lệ top-1 đúng (so với bộ mẫu vàng nếu có) tăng rõ rệt so với bge-m3 baseline.
- Số case phải escalation giảm (reranker lọc tốt hơn cosine).
- Pipeline chạy được end-to-end: Colab regen artifact (embed+rerank) → local map + comment.

## Next steps

1. Tạo plan chi tiết (tasks theo Nhóm A/B/C).
2. Xác minh khả dụng/định dạng Qwen3-Reranker-4B qua sentence-transformers/vLLM trên Colab.
3. Thử nghiệm 4B trước; chuẩn bị đường nâng 8B (dim động đã lo sẵn).
