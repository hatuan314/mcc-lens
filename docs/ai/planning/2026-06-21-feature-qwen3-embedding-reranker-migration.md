---
feature: qwen3-embedding-reranker-migration
status: completed
created: 2026-06-21
source: docs/ai/design/2026-06-21-feature-qwen3-embedding-reranker-migration.md
requirements: docs/ai/requirements/2026-06-21-feature-qwen3-embedding-reranker-migration.md
---

# Implementation Plan — Qwen3-Embedding + Qwen3-Reranker Migration

> Pipeline 3 tầng `embedding → rerank → LLM`. Producer (Colab/GPU) nhúng bằng
> Qwen3-Embedding-4B + rerank bằng Qwen3-Reranker-4B qua **sentence-transformers in-process**,
> bake `reranked_mcc_indices` + `rerank_scores` vào `.npz`. Consumer (local M1, không GPU)
> đọc thứ tự rerank trực tiếp từ artifact → WokuShop viết comment, **không tự tính cosine**.
> Dim đọc động từ `meta["dim"]`. Mọi test xanh.

## Quyết định đã chốt (không cần đọc lại requirements)

| # | Quyết định | Giá trị |
|---|---|---|
| 1 | Runtime embedding+rerank | sentence-transformers in-process Colab |
| 2 | Stage-1 top-K (cosine → reranker) | **100** (tăng từ 60, bỏ escalation) |
| 3 | bake_N (rerank → artifact) | **20** per VSIC |
| 4 | llm_N (artifact → LLM, consumer) | **10** default, clamp ≤ `meta["rerank_top_n"]` |
| 5 | Dim | Động từ `meta["dim"]`; 4B = 2560 |
| 6 | Escalation | **Bỏ** vòng nhân-đôi top-K |
| 7 | LOW_SCORE_THRESHOLD | Giữ **0.5** làm **warning-only** (log, không retry) |
| 8 | Score trong Excel | LLM score primary, fallback **rerank score** (bỏ cosine fallback) |
| 9 | Embed MCC desc truncation | `[:500]` → **`[:1000]`** |
| 10 | LLM prompt desc truncation | `[:200]` → **`[:400]`** |
| 11 | Consumer tính cosine | **Bỏ hoàn toàn** — đọc `reranked_mcc_indices` trực tiếp |
| 12 | Artifact versioning | Thêm `meta["artifact_version"] = 2`; v1 → fail-fast rõ |

## Pre-flight (đọc 1 lần)

Files sẽ đụng:
- **Producer:** `app/embed/controller.py`, `app/embed/protocols.py`,
  `app/embed/__main__.py`, `colab/requirements-embed.txt`
- **Shared:** `app/models/embedding_artifact.py`,
  `app/shared/embedding_artifact_repository.py`, `app/shared/embed_text_builder.py`
- **Consumer:** `app/services/map_vsic_to_mcc_use_case.py`,
  `app/controllers/mapping_controller.py`, `app/services/llm_prompts.py`
- **Tests:** `tests/test_embedding_artifact_repository.py`,
  `tests/test_embed_text_builder.py`, `tests/test_embed_controller.py`,
  `tests/test_map_vsic_to_mcc_use_case.py`
- **New:** `app/embed/qwen3_embedding_client.py`, `app/embed/qwen3_reranker_client.py`

Quy ước: file < 200 dòng, kebab-case, docstring Google, `python3`. Sau mỗi task có
I/O → `pytest -q`. Không commit `.env`.

**Thứ tự bắt buộc:** Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9.

---

## Task 1 — Dim động + mở rộng artifact model/repo

**Do:**
1. `app/models/embedding_artifact.py`: thêm 2 field mới với default rỗng để test cũ không vỡ:
   ```python
   reranked_mcc_indices: np.ndarray = field(default_factory=lambda: np.array([]))
   rerank_scores: np.ndarray = field(default_factory=lambda: np.array([]))
   ```
2. `app/shared/embedding_artifact_repository.py`:
   - Bỏ hard-code `EXPECTED_DIM = 1024`. Validate dim **động**:
     `dim = meta["dim"]` → assert `mcc_vectors.shape[1] == dim` và `vsic_vectors.shape[1] == dim`.
   - Thêm `"reranked_mcc_indices"`, `"rerank_scores"` vào `_REQUIRED_KEYS`.
   - `write`: lưu thêm `reranked_mcc_indices` (int32), `rerank_scores` (float32).
   - `read` validation (theo thứ tự fail-fast):
     - Thiếu key rerank → `ValueError("artifact thiếu rerank — regenerate bằng app.embed mới")`
     - `meta["artifact_version"] != 2` → `ValueError("artifact version cũ — regenerate")`
     - Shape `reranked_mcc_indices` không khớp `(n_vsic, rerank_top_n)` → `ValueError`
     - Shape `rerank_scores` không khớp `reranked_mcc_indices.shape` → `ValueError`

**Verify:**
- `read` artifact v2 (dim 2560 + rerank) → OK.
- `read` artifact cũ (v1, dim 1024, no rerank) → `ValueError` message rõ.
- `pytest -q tests/test_embedding_artifact_repository.py` xanh.

---

## Task 2 — Text-builder: instruction prefix + nới truncation

**Do:**
1. `app/shared/embed_text_builder.py`:
   - Thêm hằng số:
     ```python
     QUERY_INSTRUCTION = (
         "Given a Vietnamese industry name, "
         "retrieve the most relevant Visa MCC merchant category"
     )
     ```
   - Thêm hàm `build_vsic_query(vsic: dict) -> str`:
     ```python
     return f"Instruct: {QUERY_INSTRUCTION}\nQuery: {vsic['title']}"
     ```
     Dùng cho phía query (VSIC) khi embed **và** khi build rerank query.
   - Sửa `build_mcc_text`: `description[:500]` → `description[:1000]` (document side, không prefix).
   - Giữ `build_vsic_text` cũ (không xoá, dùng ở nơi khác nếu còn ref).
2. `app/services/llm_prompts.py`: `desc[:200]` → `desc[:400]` trong `build_user_prompt`.

**Verify:**
- `build_vsic_query({...})` bắt đầu bằng `"Instruct:"`.
- `build_mcc_text` không chứa `"Instruct:"`.
- `pytest -q tests/test_embed_text_builder.py` xanh.

---

## Task 3 — RerankerClient protocol + Qwen3 clients (Colab-only)

**Do:**
1. `app/embed/protocols.py`: thêm `RerankerClient(Protocol)`:
   ```python
   def rerank(self, query: str, documents: List[str]) -> List[float]: ...
   ```
   Không import torch/transformers ở module level.
2. Tạo `app/embed/qwen3_embedding_client.py` implement `EmbeddingClient`:
   - Lazy-import `sentence_transformers.SentenceTransformer` bên trong `__init__`.
   - `embed(texts)`: `model.encode(texts, normalize_embeddings=True)` → `List[List[float]]`.
   - Default model: `"Qwen/Qwen3-Embedding"` (4B).
3. Tạo `app/embed/qwen3_reranker_client.py` implement `RerankerClient`:
   - **Verify trước khi code** API Qwen3-Reranker trong sentence-transformers:
     nếu `CrossEncoder` hỗ trợ → dùng `CrossEncoder.predict([(query, doc)])`;
     nếu cần yes/no logit extraction → dùng HF tokenizer trực tiếp, bọc trong class.
   - Trả `List[float]` độ dài = `len(documents)`, giá trị 0–1.
   - Lazy-import. Default model: `"Qwen/Qwen3-Reranker"` (4B).
4. Giữ `OllamaEmbeddingClient` cũ không đổi (legacy, không xoá).

**Verify:**
- `python3 -c "import app.embed.protocols"` không kéo torch.
- Unit test mock: embedding client trả list độ dài = len(texts); reranker trả list độ dài = len(documents).
- Cả 2 file < 200 dòng.

---

## Task 4 — Producer bake embed + rerank vào artifact

**Do:**
1. `app/embed/controller.py`:
   - Thêm params `reranker_model: str`, `rerank_top_n: int = 20`, `cosine_top_k: int = 100`.
   - Chọn embedding client theo `embedding_model`: prefix `"Qwen"` → `Qwen3EmbeddingClient`,
     ngược lại → `OllamaEmbeddingClient` (legacy).
   - Sau khi có `mcc_vectors` + `vsic_vectors`, chạy precompute rerank:
     ```
     for i, vsic in enumerate(vsic_entries):
         # cosine top-K (numpy vectorized)
         sim = mcc_vectors @ vsic_vectors[i] / (mcc_norms * vsic_norm)
         top_k_idxs = argsort(sim)[-cosine_top_k:][::-1]
         # rerank
         docs = [build_mcc_text(mcc_entries[j]) for j in top_k_idxs]
         scores = reranker.rerank(build_vsic_query(vsic), docs)
         # sort desc, cắt top-N
         sorted_pairs = sorted(zip(scores, top_k_idxs), reverse=True)[:rerank_top_n]
         reranked_mcc_indices[i] = [idx for _, idx in sorted_pairs]
         rerank_scores[i] = [s for s, _ in sorted_pairs]
     ```
   - Tqdm: `"Reranking VSIC"` (495 iterations).
   - **VRAM:** unload embedding model trước khi load reranker (gọi `del model; torch.cuda.empty_cache()`).
   - `EmbeddingArtifact` bổ sung: `reranked_mcc_indices`, `rerank_scores`.
   - `meta` bổ sung: `artifact_version=2`, `reranker_model`, `rerank_top_n`, `cosine_top_k`.

**Verify:**
- Mock clients → artifact ghi ra có `reranked_mcc_indices.shape == (n_vsic, 20)`,
  `rerank_scores.shape == (n_vsic, 20)`.
- `pytest -q tests/test_embed_controller.py` xanh (cập nhật mock).

---

## Task 5 — Consumer: bỏ cosine local, tiêu thụ rerank từ artifact

**Do:**
1. `app/services/map_vsic_to_mcc_use_case.py`:
   - **Xoá toàn bộ** phần cosine: `_mcc_matrix`, `_mcc_norms`, `sim_scores`, `similarities`,
     `_rerank_with_escalation`. Consumer không tính cosine nữa.
   - **Xoá** `LOW_SCORE_THRESHOLD` dùng như trigger escalation. Giữ lại làm warning constant:
     ```python
     LOW_SCORE_THRESHOLD = 0.5  # warning only, không trigger retry
     ```
   - Logic mới trong `execute()` cho mỗi VSIC i:
     ```python
     idxs = self.artifact.reranked_mcc_indices[i][:llm_n]
     scores = self.artifact.rerank_scores[i][:llm_n]
     candidates = [
         {"mcc": mcc_codes[j], "title": ..., "description": ..., "score": float(scores[k])}
         for k, j in enumerate(idxs)
     ]
     llm_response = self.llm_client.chat(SYSTEM_PROMPT, build_user_prompt(...))
     ranked = self._parse_llm_response(llm_response, candidates)
     if not ranked:
         # fallback: top-3 theo rerank score, không gọi LLM lại
         ranked = [RankedMcc(mcc_code=..., mcc_title=..., score=float(scores[k]), comment="")
                   for k in range(min(3, len(idxs)))]
     if ranked and ranked[0].score < self.LOW_SCORE_THRESHOLD:
         logger.warning(f"VSIC '{vsic_code}': top-1 score thấp ({ranked[0].score:.2f}) — cần review")
     ```
   - `_parse_llm_response`: sửa fallback score — `original["score"]` (rerank score) thay vì
     cosine score (đã xoá). **LLM score primary, rerank score fallback** khi LLM không trả score.
   - Tham số `top_k` trong `execute()` đổi tên/nghĩa thành `llm_n` (số candidate gửi LLM).

2. `app/controllers/mapping_controller.py`:
   - `--top-k` help text → cập nhật: "số MCC candidates gửi LLM từ artifact rerank
     (default: 10, max: rerank_top_n trong artifact)".
   - `DEFAULT_TOP_K = 60` → `DEFAULT_LLM_N = 10`.
   - Clamp: `llm_n = min(args.top_k, artifact.meta["rerank_top_n"])` (đọc từ artifact sau load).
   - Không thêm bất kỳ embedding/reranker client nào ở consumer.

**Verify:**
- `grep -n "_mcc_matrix\|sim_scores\|cosine\|np.linalg\|_rerank_with_escalation" app/services/map_vsic_to_mcc_use_case.py` → 0 kết quả.
- `python3 main.py map-vsic-mcc --help` OK; không import torch/transformers.
- `pytest -q tests/test_map_vsic_to_mcc_use_case.py` xanh (fixture artifact có rerank).

---

## Task 6 — CLI producer: args mới

**Do:**
1. `app/embed/__main__.py`:
   - `--embedding-model` default → `"Qwen/Qwen3-Embedding"`.
   - Thêm `--reranker-model` (default `"Qwen/Qwen3-Reranker"`).
   - Thêm `--rerank-top-n` (default `20`, type int).
   - Thêm `--cosine-top-k` (default `100`, type int) — đầu vào reranker trên Colab.
   - Truyền xuống `EmbedController.__init__` + `execute`.
2. `EmbedController.__init__`: thêm params tương ứng.

**Verify:**
- `python3 -m app.embed --help` liệt kê đủ 4 args trên, không cần `.env`.

---

## Task 7 — Deps + Colab notebooks

**Do:**
1. `colab/requirements-embed.txt`: thêm:
   ```
   torch>=2.0.0
   transformers>=4.40.0
   sentence-transformers>=3.0.0
   accelerate>=0.26.0
   ```
   Giữ: `numpy`, `tqdm`, `loguru`, `python-dotenv`, `pydantic`.
   Xem xét bỏ `ollama` nếu không còn dùng embedding Ollama (chốt sau Task 3).
2. `colab/embed_vsic_mcc_colab.ipynb`:
   - Cập nhật cell cài deps → `requirements-embed.txt` mới.
   - Lệnh embed → `python3 -m app.embed --embedding-model Qwen/Qwen3-Embedding --reranker-model Qwen/Qwen3-Reranker --cosine-top-k 100 --rerank-top-n 20 ...`
   - Ghi chú rõ: unload embedding model trước khi rerank (VRAM T4).

**Verify:**
- Venv tạm + `pip install -r colab/requirements-embed.txt` → `python3 -m app.embed --help` OK.

---

## Task 8 — Tests

**Do:**
1. `test_embedding_artifact_repository.py`:
   - Case dim động 2560, artifact v2 có rerank → read OK.
   - Artifact v1 (dim 1024, no rerank keys) → `ValueError` message chứa "regenerate".
   - Shape mismatch `reranked_mcc_indices` → `ValueError`.
   - write → read roundtrip: shape giữ nguyên.
2. `test_embed_text_builder.py`:
   - `build_vsic_query` chứa `"Instruct:"` và `"Query:"`.
   - `build_mcc_text` không chứa `"Instruct:"`.
   - `build_mcc_text` truncate ở 1000 ký tự.
3. `test_embed_controller.py`:
   - Mock `Qwen3EmbeddingClient` + `Qwen3RerankerClient` → artifact có rerank đúng shape `(n_vsic, 20)`.
   - VRAM unload: mock `del model` được gọi giữa embed và rerank.
4. `test_map_vsic_to_mcc_use_case.py`:
   - Fixture artifact v2 có `reranked_mcc_indices` + `rerank_scores`.
   - Use-case build candidates từ indices → gọi LLM → ra top-3.
   - LLM trả rỗng → fallback top-3 theo rerank score (không gọi LLM lại).
   - top-1 score < 0.5 → logger.warning được gọi.
   - `_mcc_matrix` không tồn tại trong use-case (assert `AttributeError`).
5. `test_qwen3_reranker_client.py` (mới, mock model): trả `List[float]` độ dài = len(documents).
6. `test_qwen3_embedding_client.py` (mới, mock model): trả list độ dài = len(texts).

**Verify:**
- `pytest -q` xanh toàn bộ; coverage `app/` không giảm.

---

## Task 9 — Docs

**Do:**
1. `CLAUDE.md`:
   - Mục "2-module embedding split" → đổi thành "3-stage pipeline".
   - Ghi: Producer Colab = embed (Qwen3-Embedding, ST) + rerank (Qwen3-Reranker, ST, cosine top-100 → bake top-20).
   - Consumer local = đọc artifact rerank → llm_n=10 → WokuShop comment. Không GPU, không cosine.
   - Dim động từ `meta["dim"]`; 4B=2560.
2. `README.md`: mục Embed + map-vsic-mcc → model mới, args `--reranker-model/--rerank-top-n/--cosine-top-k`, ghi rõ local không cần GPU/reranker.
3. `app/shared/embedding_artifact_repository.py`: xoá comment `# bge-m3` khỏi dòng `EXPECTED_DIM` (hoặc xoá hằng nếu không còn dùng).

**Verify:**
- `grep -rn "EXPECTED_DIM = 1024" app/` → 0 kết quả.
- `grep -rn "bge-m3" README.md CLAUDE.md` → chỉ còn ở mục lịch sử/migration note.

---

## Definition of Done

- [x] Producer Colab tạo `.npz` v2: Qwen3 vectors (dim 2560) + `reranked_mcc_indices (495×20)` + `rerank_scores (495×20)` + meta đầy đủ.
- [x] `EmbeddingArtifactRepository` validate dim động + shape rerank; artifact v1 → fail-fast rõ.
- [x] Consumer local: không cosine, không numpy heavy compute — chỉ slice artifact + WokuShop → 2 Excel hợp lệ.
- [x] Đổi 4B→8B = đổi `--embedding-model` + regenerate, 0 dòng code consumer.
- [x] `build_vsic_query` có instruction prefix; `build_mcc_text` desc[:1000]; LLM prompt desc[:400].
- [x] Bỏ escalation; `LOW_SCORE_THRESHOLD` warning-only; LLM score primary, rerank score fallback.
- [x] `pytest -q` xanh; CLAUDE.md + README.md cập nhật.

## Rủi ro & lưu ý

- **VRAM T4:** unload embedding model (del + empty_cache) trước khi load reranker.
- **Qwen3-Reranker API:** verify sentence-transformers CrossEncoder vs logit extraction ở Task 3 trước khi viết production code.
- **bake_N đóng băng:** đổi `--rerank-top-n` hoặc `--cosine-top-k` = regenerate artifact (chấp nhận).
- **Artifact v1 bất tương thích:** phải regenerate, không resume checkpoint cũ.
- **llm_n clamp:** consumer đọc `meta["rerank_top_n"]` từ artifact để làm cận trên cho `--top-k`.
