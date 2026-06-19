---
phase: testing
title: Testing Strategy
description: Test plan for the 2-module split (embed producer + map consumer)
feature: embedding-cache
date: 2026-06-19
---

# Testing Strategy — Split Embedding & LLM Re-rank

## Test Coverage Goals

- 100% branch coverage of `EmbeddingArtifactRepository.read/write` (round-trip, missing, corrupt, dim mismatch, empty).
- `EmbedController`: artifact shapes correct; zero-vector recorded in meta + warning logged.
- `MapVsicToMccUseCase`: zero embedding calls; lookup matches artifact vectors; MCC prompt text sourced from artifact.
- `MappingController`: missing/corrupt artifact → non-zero exit; no embedding client constructed.
- All existing tests pass after the constructor-signature change (no regressions).

## Unit Tests

### `EmbeddingArtifactRepository` (`tests/test_embedding_artifact_repository.py`)

- [ ] **write → read round-trip**: vectors, codes, titles, descriptions, meta survive a save/load cycle unchanged
- [ ] **missing file**: `read()` raises `FileNotFoundError` with the "run embed" hint
- [ ] **corrupt file**: non-`.npz` bytes → `read()` raises `ValueError`
- [ ] **dim mismatch**: `meta.dim` != `vectors.shape[1]` → `ValueError`
- [ ] **empty arrays**: zero-length MCC or VSIC vectors → `ValueError`

### `EmbedController` (`tests/test_embed_controller.py`)

- [ ] **happy path**: produces artifact with `mcc (91, D)` and `vsic (N, D)`; meta has model, dim, sources, created_at
- [ ] **zero-vector handling**: when mock embedder raises `RuntimeError` for one text, that code is in `meta.zero_vector_codes`, artifact still written, warning logged
- [ ] **text building**: MCC text = `title — description[:500]` (HTML stripped); VSIC text = title

### `MapVsicToMccUseCase` (update existing use-case test file)

- [ ] **consumes artifact**: built from a synthetic `EmbeddingArtifact`; `execute()` makes **zero** embedding calls (no `embedding_client` exists)
- [ ] **lookup correctness**: per-VSIC vector used equals `artifact.vsic_vectors` for that code
- [ ] **MCC prompt text from artifact**: candidate dicts use `artifact.mcc_titles/descriptions`, not source JSON
- [ ] **escalation + parse**: existing top-K escalation and `_parse_llm_response` behavior unchanged (regression)

### `MappingController` (update `tests/test_mapping_controller.py`)

- [ ] **artifact missing**: `--embeddings` path absent → returns non-zero exit, logs actionable error
- [ ] **artifact corrupt**: repo raises `ValueError` → non-zero exit
- [ ] **no embedding client**: controller never constructs `OllamaEmbeddingClient`/`WokuShopEmbeddingClient`
- [ ] **WokuShop LLM health-check kept**; embedding health-check removed

## Integration Tests

- [ ] Full Module 2 run with a synthetic artifact (`tmp_path`) + mock LLM client: produces both Excel outputs with Ollama never touched
- [ ] `--resume` + artifact: checkpoint filters which VSICs hit the LLM pass; vectors always from artifact
- [ ] `--limit` + artifact: loop limited, artifact still full set, no `KeyError`

## Test Data

```python
import numpy as np

D = 16  # small dim for speed
artifact = EmbeddingArtifact(
    mcc_vectors=np.random.rand(3, D).astype(np.float32),
    mcc_codes=["0742", "5995", "7299"],
    mcc_titles=["Veterinary", "Pet Shops", "Misc Services"],
    mcc_descriptions=["...", "...", "..."],
    vsic_vectors=np.random.rand(2, D).astype(np.float32),
    vsic_codes=["0111", "0112"],
    vsic_titles=["Trồng lúa", "Trồng ngô"],
    meta={"embedding_model": "bge-m3", "dim": D, "zero_vector_codes": {"mcc": [], "vsic": []}},
)

class MockEmbeddingClient:
    def __init__(self, vectors, fail_indices=()):
        self.calls = 0; self._v = list(vectors); self._fail = set(fail_indices)
    def embed(self, texts):
        i = self.calls; self.calls += 1
        if i in self._fail:
            raise RuntimeError("simulated NaN")
        return [self._v[i]]
```

## Test Reporting & Coverage

```bash
pytest tests/ -v \
  --cov=app/repositories/embedding_artifact_repository \
  --cov=app/controllers/embed_controller \
  --cov=app/services/map_vsic_to_mcc_use_case \
  --cov-report=term-missing
```

Expected: all artifact read/write branches and the consumer-only loop covered.

## Manual Testing

```bash
# Module 1 (Colab, GPU + Ollama running)
python3 main.py embed \
  --mcc-input output/mcc-visa.json --vsic-input output/vsic-vn.json \
  --gdrive-output-dir /content/drive/MyDrive/projects/mcc-lens
# → verify output/embed-artifact.npz exists; check logs for zero-vector warnings

# Module 2 (local, Ollama STOPPED, WokuShop key set)
python3 main.py map-vsic-mcc --embeddings output/embed-artifact.npz --limit 5
# → verify both xlsx produced; no embedding/Ollama log lines

# Hard-fail check
python3 main.py map-vsic-mcc --embeddings output/does-not-exist.npz
# → expect non-zero exit + "Run `python3 main.py embed` on Colab first"
```

## Performance Testing

- Confirm Module 2 has no embedding phase: time from start to first VSIC LLM call is just artifact load (sub-second).

## Bug Tracking

- Regression risk: candidate-building now indexes `artifact.mcc_*` arrays — they must stay index-aligned with `mcc_codes`/`mcc_vectors`. Add a test asserting alignment.
- Monitor: `vsic_vec_map[vsic_code]` must never `KeyError` (artifact = full VSIC set); a `KeyError` indicates a real producer/consumer mismatch, not an expected path.
