---
phase: implementation
title: Implementation Guide — Qwen3-Embedding + Qwen3-Reranker Migration
description: Technical implementation notes, files changed, and decisions made.
---

# Implementation Progress

## Task 1 — Dim động + mở rộng artifact model/repo (Done)

- **Mục tiêu:** Cho phép lưu trữ và đọc thông tin rerank trong artifact `.npz`, đồng thời hỗ trợ kiểm tra kích thước (dim) động thay vì hằng số 1024.
- **Tập tin thay đổi:**
  - [app/models/embedding_artifact.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/models/embedding_artifact.py):
    - Thêm hai trường mới `reranked_mcc_indices` và `rerank_scores` với giá trị mặc định là `np.array([])`.
  - [app/repositories/embedding_artifact_repository.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/repositories/embedding_artifact_repository.py):
    - Thêm hai key mới vào `_REQUIRED_KEYS`.
    - Cập nhật phương thức `write` để lưu các mảng rerank mới dưới dạng kiểu dữ liệu `np.int32` và `np.float32`.
    - Cập nhật phương thức `read` để:
      - Đọc `meta` trước và lấy `dim` động từ `meta["dim"]`.
      - Kiểm tra phiên bản artifact (`meta.get("artifact_version") == 2`), nếu không khớp ném lỗi "artifact version cũ — regenerate".
      - Ném lỗi chính xác "artifact thiếu rerank — regenerate bằng app.embed mới" nếu thiếu các mảng rerank.
      - Xác thực shape của `reranked_mcc_indices` phải khớp `(n_vsic, rerank_top_n)` và shape của `rerank_scores` phải khớp với `reranked_mcc_indices`.
- **Quyết định kỹ thuật:**
  - Vẫn giữ hằng số `EXPECTED_DIM = 1024` tại module level của repo để tránh lỗi import ở các kiểm thử cũ (sẽ được cập nhật ở Task 8).
  - Sử dụng fail-fast validation theo thứ tự: kiểm tra file -> nạp file -> kiểm tra thiếu key -> kiểm tra version -> kiểm tra dim động -> kiểm tra hình dạng mảng rerank -> kiểm tra length mismatch.

## Task 2 — Text-builder: instruction prefix + nới truncation (Done)

- **Mục tiêu:** Định cấu hình prefix instruction cho phía query (VSIC) tương thích với kiểu asymmetric của Qwen3-Embedding, đồng thời tăng giới hạn cắt (truncation) của mô tả MCC nhằm cải thiện chất lượng tìm kiếm và phân loại.
- **Tập tin thay đổi:**
  - [app/services/embed_text_builder.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/services/embed_text_builder.py):
    - Định nghĩa hằng số `QUERY_INSTRUCTION` chứa câu lệnh hướng dẫn kiểu Qwen3: `"Given a Vietnamese industry name, retrieve the most relevant Visa MCC merchant category"`.
    - Thêm hàm `build_vsic_query(vsic: dict) -> str` để sinh chuỗi truy vấn có định dạng: `Instruct: {QUERY_INSTRUCTION}\nQuery: {vsic['title']}`.
    - Chỉnh sửa `build_mcc_text` nới truncation cho description của MCC từ `500` lên `1000` ký tự.
    - Giữ nguyên hàm `build_vsic_text` cũ để đảm bảo khả năng tương thích.
  - [app/services/llm_prompts.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/services/llm_prompts.py):
    - Thay đổi giới hạn mô tả MCC trong prompt gửi cho LLM từ `200` lên `400` ký tự trong hàm `build_user_prompt`.

## Task 3 — RerankerClient protocol + Qwen3 clients (Colab-only) (Done)

- **Mục tiêu:** Thêm định nghĩa giao diện `RerankerClient` protocol cho tầng rerank trung gian và triển khai các client Qwen3 (Embedding & Reranker) sử dụng `sentence-transformers` được lazy-load để không làm nặng môi trường chạy local.
- **Tập tin thay đổi/tạo mới:**
  - [app/services/protocols.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/services/protocols.py):
    - Thêm định nghĩa interface `RerankerClient` với phương thức `rerank(query: str, documents: List[str]) -> List[float]`.
  - [app/repositories/qwen3_embedding_client.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/repositories/qwen3_embedding_client.py) (Tạo mới):
    - Triển khai `EmbeddingClient` bằng cách bọc quanh `sentence_transformers.SentenceTransformer`.
    - Sử dụng cơ chế property lazy-load để tránh import thư viện nặng khi không cần thiết.
    - Trả về danh sách vector nhúng float.
  - [app/repositories/qwen3_reranker_client.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/repositories/qwen3_reranker_client.py) (Tạo mới):
    - Triển khai `RerankerClient` bằng cách bọc quanh `sentence_transformers.CrossEncoder`.
    - Sử dụng property lazy-load tương tự.
    - Tính toán relevance scores và áp dụng sigmoid hàm số để chuẩn hoá về khoảng `[0.0, 1.0]`.

## Task 4 — Producer bake embed + rerank vào artifact (Done)

- **Mục tiêu:** Cập nhật controller của producer nhúng để tích hợp tầng Qwen3-Reranker, thực hiện tính toán và lọc từ cosine similarity (top-K) sang rerank relevance (top-N), giải phóng VRAM GPU sau mỗi giai đoạn và đóng gói kết quả thành artifact v2 hoàn chỉnh.
- **Tập tin thay đổi:**
  - [app/controllers/embed_controller.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/controllers/embed_controller.py):
    - Cập nhật constructor để nhận thêm: `reranker_model` (mặc định `None` để tương thích ngược), `rerank_top_n` (mặc định 20), và `cosine_top_k` (mặc định 100).
    - Cập nhật phương thức `execute` để tự động chọn client `Qwen3EmbeddingClient` nếu tên model bắt đầu bằng `"Qwen"`, ngược lại dùng `OllamaEmbeddingClient`.
    - Thêm cơ chế giải phóng VRAM GPU cho embedding client (xóa thuộc tính model, garbage collect và `torch.cuda.empty_cache()`) trước khi tải reranker model.
    - Triển khai tầng Rerank: Lấy top-K ứng viên cosine, chuẩn bị query/doc (áp dụng đúng instruction prefix cho query), và gọi `RerankerClient.rerank` để chấm điểm relevance. Sau đó sắp xếp giảm dần và lưu lại top-N indices cùng scores.
    - Hỗ trợ fallback sinh dummy rerank từ cosine nếu không cấu hình `reranker_model` (nhằm giữ tương thích ngược 100% với các unit test cũ trên local không có GPU/sentence-transformers).
    - Đóng gói metadata phong phú hơn vào `EmbeddingArtifact` (gồm `dim` động, `reranker_model`, `rerank_top_n`, `cosine_top_k`, `artifact_version=2`).

## Task 5 — Consumer: bỏ cosine local, tiêu thụ rerank từ artifact (Done)

- **Mục tiêu:** Tối ưu hóa consumer local bằng cách loại bỏ hoàn toàn tính toán cosine similarity và logic escalation phức tạp. Thay vào đó, tiêu thụ trực tiếp thứ tự đã rerank sẵn trong artifact v2 để gửi cho LLM.
- **Tập tin thay đổi:**
  - [app/services/map_vsic_to_mcc_use_case.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/services/map_vsic_to_mcc_use_case.py):
    - Loại bỏ hoàn toàn các thuộc tính và logic liên quan đến cosine local (`_mcc_matrix`, `_mcc_norms`, và phương thức `_rerank_with_escalation`).
    - Trong phương thức `execute()`, đọc trực tiếp `reranked_mcc_indices` và `rerank_scores` từ artifact ứng với mỗi VSIC `i`.
    - Sắp xếp và giới hạn ứng viên gửi cho LLM theo tham số `llm_n` (clamp theo `rerank_top_n` của artifact).
    - Triển khai fallback khi LLM trả về kết quả rỗng: tự động lấy top-3 ứng viên theo rerank score mà không gọi lại LLM.
    - Duy trì `LOW_SCORE_THRESHOLD = 0.5` dưới dạng warning-only, chỉ ghi log cảnh báo khi ứng viên top-1 có điểm score thấp hơn ngưỡng này.
    - Hỗ trợ tương thích ngược signature bằng cách chấp nhận tham số legacy `top_k` (tự động mapping sang `llm_n`).
    - Cập nhật `_parse_llm_response` để fallback sang rerank score thay vì cosine score cũ.
  - [app/controllers/mapping_controller.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/app/controllers/mapping_controller.py):
    - Đổi `DEFAULT_TOP_K` từ `60` sang `10` (phù hợp cho llm_n của pipeline mới).
    - Cập nhật help text cho CLI argument `--top-k`.
    - Bổ sung logic clamp giá trị `llm_n` để không vượt quá `rerank_top_n` của artifact nạp từ repository.
    - Gọi phương thức `use_case.execute` sử dụng `llm_n` thay vì `top_k`.

## Task 6 — CLI producer: args mới (Done)

- **Mục tiêu:** Cập nhật CLI subcommand `embed` để cho phép người dùng tùy chọn cấu hình các tham số cho Qwen3-Embedding và Qwen3-Reranker từ dòng lệnh.
- **Tập tin thay đổi:**
  - [main.py](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/main.py):
    - Thay đổi mặc định của `--embedding-model` thành `"Qwen/Qwen3-Embedding"`.
    - Bổ sung đối số `--reranker-model` với mặc định là `"Qwen/Qwen3-Reranker"`.
    - Bổ sung đối số `--rerank-top-n` với mặc định là `20`.
    - Bổ sung đối số `--cosine-top-k` với mặc định là `100`.
    - Cập nhật logic điều phối subcommand `embed` để in ra các tham số mới và truyền đầy đủ chúng xuống `EmbedController`.

## Task 7 — Deps + Colab notebooks (Done)

- **Mục tiêu:** Cập nhật các phụ thuộc (dependencies) cần thiết cho môi trường chạy GPU của Google Colab và cập nhật notebook Jupyter hướng dẫn nhúng/rerank sử dụng Qwen3.
- **Tập tin thay đổi/tạo mới:**
  - [colab/requirements-embed.txt](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/colab/requirements-embed.txt) (Tạo mới):
    - Định cấu hình các thư viện GPU in-process bao gồm: `torch>=2.0.0`, `transformers>=4.40.0`, `sentence-transformers>=3.0.0`, `accelerate>=0.26.0`, và các thư viện hỗ trợ `numpy`, `tqdm`, `loguru`, `pydantic`.
  - [colab/embed_vsic_mcc_colab.ipynb](file:///Users/tuanha/Work/projects/python/convert-vsic-to-mcc/mcc-lens/.worktrees/feature-qwen3-embedding-reranker-migration/colab/embed_vsic_mcc_colab.ipynb):
    - Cập nhật cell cài đặt thư viện để nạp `requirements-embed.txt`.
    - Cập nhật ghi chú và hướng dẫn: chạy nhúng in-process trên GPU thay vì Ollama model legacy.
    - Cập nhật dòng lệnh chạy nhúng chỉ định model nhúng Qwen3 và reranker Qwen3, cấu hình top-K=100 và top-N=20.
    - Cập nhật cell in thông tin artifact để hiển thị cả shape của `reranked_mcc_indices` và `rerank_scores`.
